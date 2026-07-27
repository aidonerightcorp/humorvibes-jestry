"""Low-cardinality metrics and opt-in body-free OpenTelemetry spans."""

from __future__ import annotations

import socket
import threading
import time
from collections import defaultdict
from typing import Any

from .config import Settings
from .errors import IntegrationError
from .http import normalize_base_url


def _metric_prefix(value: str) -> str:
    rendered = "".join(character if character.isalnum() or character in "_." else "_" for character in value)
    return rendered.strip(".")[:100] or "humorvibes"


class StatsDSink:
    """Best-effort UDP StatsD output containing no paths, prompts, keys, or user IDs."""

    def __init__(self, host: str, port: int, prefix: str, *, sock: Any = None) -> None:
        self.host = host
        self.port = port
        self.prefix = _metric_prefix(prefix)
        self._socket = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_failures = 0

    def record(self, status: int, elapsed_ms: float) -> None:
        status_class = f"{max(0, status) // 100}xx"
        lines = [
            f"{self.prefix}.requests_total:1|c",
            f"{self.prefix}.responses_{status_class}_total:1|c",
            f"{self.prefix}.request_duration_ms:{max(0.0, elapsed_ms):.3f}|ms",
        ]
        if status >= 400:
            lines.append(f"{self.prefix}.errors_total:1|c")
        try:
            self._socket.sendto("\n".join(lines).encode("ascii"), (self.host, self.port))
        except OSError:
            self.send_failures += 1


class Metrics:
    def __init__(self, settings: Settings) -> None:
        self.started = time.time()
        self.requests = 0
        self.errors = 0
        self.by_status: dict[int, int] = defaultdict(int)
        self._lock = threading.Lock()
        self._statsd = (
            StatsDSink(settings.statsd_host, settings.statsd_port, settings.statsd_prefix)
            if settings.statsd_host
            else None
        )

    def record(self, status: int, elapsed_ms: float = 0.0) -> None:
        with self._lock:
            self.requests += 1
            self.by_status[status] += 1
            if status >= 400:
                self.errors += 1
        if self._statsd is not None:
            self._statsd.record(status, elapsed_ms)

    def text(self) -> str:
        with self._lock:
            lines = [
                "# HELP humorvibes_requests_total HTTP requests handled.",
                "# TYPE humorvibes_requests_total counter",
                f"humorvibes_requests_total {self.requests}",
                "# HELP humorvibes_errors_total HTTP responses with status >= 400.",
                "# TYPE humorvibes_errors_total counter",
                f"humorvibes_errors_total {self.errors}",
                "# HELP humorvibes_uptime_seconds Process uptime.",
                "# TYPE humorvibes_uptime_seconds gauge",
                f"humorvibes_uptime_seconds {max(0, int(time.time() - self.started))}",
            ]
            for status, count in sorted(self.by_status.items()):
                lines.append(f'humorvibes_responses_total{{status="{status}"}} {count}')
            if self._statsd is not None:
                lines.extend(
                    [
                        "# HELP humorvibes_statsd_send_failures_total Best-effort StatsD send failures.",
                        "# TYPE humorvibes_statsd_send_failures_total counter",
                        f"humorvibes_statsd_send_failures_total {self._statsd.send_failures}",
                    ]
                )
            return "\n".join(lines) + "\n"


class RequestSpan:
    def __init__(self, span: Any = None) -> None:
        self._span = span
        context = span.get_span_context() if span is not None else None
        self.trace_id = f"{context.trace_id:032x}" if context is not None and context.is_valid else ""

    def finish(self, status: int, elapsed_ms: float, route: str = "_unmatched") -> None:
        if self._span is None:
            return
        self._span.set_attribute("http.route", route)
        self._span.set_attribute("http.response.status_code", status)
        self._span.set_attribute("http.server.request.duration_ms", round(max(0.0, elapsed_ms), 3))
        if status >= 500:
            try:
                from opentelemetry.trace import Status, StatusCode

                self._span.set_status(Status(StatusCode.ERROR))
            except ImportError:  # pragma: no cover - exporter dependencies disappeared at runtime
                pass
        self._span.end()


class Telemetry:
    """Own one optional tracer provider; spans intentionally omit all content fields."""

    def __init__(self, settings: Settings) -> None:
        self._provider: Any = None
        self._tracer: Any = None
        if not settings.otel_traces_endpoint:
            return
        endpoint = normalize_base_url(
            settings.otel_traces_endpoint,
            allow_insecure_remote=settings.allow_insecure_remote,
        )
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
        except ImportError:
            raise IntegrationError(
                "telemetry_dependency_missing",
                "Install humorvibes-research[telemetry] before enabling OTLP traces.",
                500,
            ) from None
        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.otel_service_name}),
            sampler=ParentBased(TraceIdRatioBased(settings.otel_sample_ratio)),
        )
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        self._provider = provider
        self._tracer = provider.get_tracer("humorvibes.api")

    def start_request(
        self, method: str, headers: dict[str, str] | None = None
    ) -> RequestSpan:
        if self._tracer is None:
            return RequestSpan()
        from opentelemetry.propagate import extract
        from opentelemetry.trace import SpanKind

        context = extract(headers or {})
        span = self._tracer.start_span(
            "http.server.request", context=context, kind=SpanKind.SERVER
        )
        span.set_attribute("http.request.method", method)
        span.set_attribute("humorvibes.records_body", False)
        return RequestSpan(span)

    def shutdown(self) -> None:
        if self._provider is not None:
            self._provider.shutdown()
