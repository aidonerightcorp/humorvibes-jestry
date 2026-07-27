"""Observability is optional, low cardinality, and body/secret free."""

from __future__ import annotations

from humorvibes.config import Settings
from humorvibes.observability import Metrics, StatsDSink, Telemetry


class FakeSocket:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[tuple[bytes, tuple[str, int]]] = []

    def sendto(self, body: bytes, target: tuple[str, int]) -> None:
        if self.fail:
            raise OSError("fixture send failure")
        self.messages.append((body, target))


def test_statsd_sink_has_bounded_metric_names_and_no_content() -> None:
    sock = FakeSocket()
    sink = StatsDSink("collector", 8125, "humor vibes;unsafe", sock=sock)
    sink.record(503, 12.3456)
    rendered = sock.messages[0][0].decode("ascii")
    assert sock.messages[0][1] == ("collector", 8125)
    assert "humor_vibes_unsafe.requests_total:1|c" in rendered
    assert "responses_5xx_total:1|c" in rendered
    assert "request_duration_ms:12.346|ms" in rendered
    assert "errors_total:1|c" in rendered
    assert "prompt" not in rendered and "authorization" not in rendered


def test_statsd_failure_is_best_effort_and_visible_locally() -> None:
    sink = StatsDSink("collector", 8125, "humorvibes", sock=FakeSocket(fail=True))
    sink.record(200, 1.0)
    assert sink.send_failures == 1


def test_default_metrics_and_telemetry_make_no_network_calls() -> None:
    settings = Settings.from_env({})
    metrics = Metrics(settings)
    metrics.record(200, 3.2)
    metrics.record(429, 1.1)
    rendered = metrics.text()
    assert "humorvibes_requests_total 2" in rendered
    assert "humorvibes_errors_total 1" in rendered
    assert "statsd_send_failures" not in rendered
    span = Telemetry(settings).start_request("POST")
    assert span.trace_id == ""
    span.finish(200, 4.0)


def test_public_settings_expose_flags_but_not_collector_addresses_or_keys() -> None:
    secret_endpoint = "https://collector.example.test/v1/traces"
    settings = Settings.from_env(
        {
            "HUMORVIBES_STATSD_HOST": "statsd.internal",
            "HUMORVIBES_OTEL_TRACES_ENDPOINT": secret_endpoint,
            "OTEL_EXPORTER_OTLP_TRACES_HEADERS": "authorization=secret-value",
        }
    )
    summary = settings.public_summary()
    assert summary["observability"]["statsd_configured"] is True
    assert summary["observability"]["otel_traces_configured"] is True
    assert summary["observability"]["records_request_or_response_bodies"] is False
    rendered = str(summary)
    assert secret_endpoint not in rendered and "secret-value" not in rendered
