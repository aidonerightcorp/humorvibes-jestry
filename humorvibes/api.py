"""FastAPI application factory for HumorVibes integrations."""

from __future__ import annotations

import hmac
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Annotated, Any

from . import __version__
from .config import Settings
from .errors import IntegrationError
from .service import HumorVibesService

try:
    from fastapi import Depends, FastAPI, Header, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, PlainTextResponse
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as exc:  # pragma: no cover - exercised by the console error path
    raise RuntimeError("Install the API dependencies with: pip install 'humorvibes-research[api]'") from exc


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


class GenerateRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=200_000)
    system: str = Field(default="", max_length=200_000)
    model_id: str | None = Field(default=None, max_length=256)
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    json_mode: bool = False
    think: bool = False


class HumorGenerateRequest(StrictModel):
    topic: str = Field(min_length=1, max_length=20_000)
    format: str = Field(default="one_liner", min_length=1, max_length=64)
    audience: str = Field(default="", max_length=10_000)
    preferences: str = Field(default="", max_length=10_000)
    count: int = Field(default=4, ge=1, le=12)
    model_id: str | None = Field(default=None, max_length=256)
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    think: bool = False


class JudgeRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=200_000)
    model_id: str | None = Field(default=None, max_length=256)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class EmbedRequest(StrictModel):
    texts: list[str] = Field(min_length=1, max_length=512)
    model_id: str | None = Field(default=None, max_length=256)
    dimensions: int | None = Field(default=None, ge=1, le=65_536)


class SimilarityRequest(StrictModel):
    left: list[str] = Field(min_length=1, max_length=32)
    right: list[str] = Field(min_length=1, max_length=32)
    model_id: str | None = Field(default=None, max_length=256)
    dimensions: int | None = Field(default=None, ge=1, le=65_536)


class SignalsRequest(StrictModel):
    setup: str = Field(min_length=1, max_length=100_000)
    punchline: str = Field(min_length=1, max_length=100_000)
    frame_hint: str = Field(default="", max_length=100_000)
    personas: list[str] = Field(default_factory=list, max_length=32)


class OpenControlsSampleRequest(StrictModel):
    count: int = Field(default=8, ge=1, le=64)
    seed: int = Field(default=20_260_727)
    arm: str | None = Field(default=None, max_length=64)
    split: str | None = Field(default=None, max_length=16)


class _RateLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


class _Metrics:
    def __init__(self) -> None:
        self.started = time.time()
        self.requests = 0
        self.errors = 0
        self.by_status: dict[int, int] = defaultdict(int)
        self._lock = threading.Lock()

    def record(self, status: int) -> None:
        with self._lock:
            self.requests += 1
            self.by_status[status] += 1
            if status >= 400:
                self.errors += 1

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
            return "\n".join(lines) + "\n"


class _BodyLimitMiddleware:
    """Bound chunked and fixed-length bodies before Pydantic parses them."""

    def __init__(self, app: Any, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        messages: list[dict[str, Any]] = []
        total = 0
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                return
            if message.get("type") != "http.request":
                continue
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                request_id = scope.get("state", {}).get("request_id", "")
                response = JSONResponse(
                    {
                        "error": {
                            "code": "request_too_large",
                            "message": "Request body exceeds the configured limit.",
                            "retryable": False,
                        },
                        "request_id": request_id,
                    },
                    status_code=413,
                )
                await response(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        position = 0

        async def replay() -> dict[str, Any]:
            nonlocal position
            if position < len(messages):
                message = messages[position]
                position += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay, send)


def create_app(
    settings: Settings | None = None,
    service: HumorVibesService | None = None,
) -> FastAPI:
    runtime_settings = settings or Settings.from_env()
    runtime_service = service or HumorVibesService(runtime_settings)
    limiter = _RateLimiter(runtime_settings.rate_limit_per_minute)
    metrics = _Metrics()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(
        title="HumorVibes Integration API",
        summary="Deployable LLM, embedding, and humor-research integration surface",
        description=(
            "This API exposes generation, validated embeddings, similarity, and explicitly scoped "
            "HumorVibes signals. Model output is not human funniness evidence."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.service = runtime_service
    app.state.metrics = metrics

    if runtime_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(runtime_settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
    app.add_middleware(_BodyLimitMiddleware, max_bytes=runtime_settings.max_request_bytes)

    @app.middleware("http")
    async def request_boundary(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "")
        if not request_id or len(request_id) > 128 or not all(ch.isalnum() or ch in "-_." for ch in request_id):
            request_id = uuid.uuid4().hex
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                too_large = int(content_length) > runtime_settings.max_request_bytes
            except ValueError:
                too_large = True
            if too_large:
                response = JSONResponse(
                    {"error": {"code": "request_too_large", "message": "Request body exceeds the configured limit.", "retryable": False}, "request_id": request_id},
                    status_code=413,
                )
                response.headers["X-Request-ID"] = request_id
                metrics.record(413)
                return response
        client_key = request.client.host if request.client else "unknown"
        if request.url.path.startswith("/v1/") and not limiter.allow(client_key):
            response = JSONResponse(
                {"error": {"code": "rate_limit_exceeded", "message": "Per-process request limit exceeded.", "retryable": True}, "request_id": request_id},
                status_code=429,
            )
            response.headers["Retry-After"] = "60"
            response.headers["X-Request-ID"] = request_id
            metrics.record(429)
            return response
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        metrics.record(response.status_code)
        return response

    def require_api_key(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        expected = runtime_settings.api_key
        if not expected:
            return
        supplied = ""
        if authorization and authorization.startswith("Bearer "):
            supplied = authorization[7:]
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise IntegrationError("unauthorized", "A valid Bearer API key is required.", 401)

    auth = [Depends(require_api_key)]

    @app.exception_handler(IntegrationError)
    async def integration_error(request: Request, exc: IntegrationError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            {"error": exc.public(), "request_id": getattr(request.state, "request_id", "")},
            status_code=exc.status_code,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {"location": [str(part) for part in row.get("loc", ())], "type": str(row.get("type", "invalid"))}
            for row in exc.errors()[:20]
        ]
        return JSONResponse(
            {
                "error": {
                    "code": "invalid_request",
                    "message": "Request validation failed.",
                    "retryable": False,
                    "detail": {"errors": errors},
                },
                "request_id": getattr(request.state, "request_id", ""),
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, _: Exception):
        return JSONResponse(
            {"error": {"code": "internal_error", "message": "Internal server error.", "retryable": False}, "request_id": getattr(request.state, "request_id", "")},
            status_code=500,
        )

    @app.get("/health/live", tags=["operations"])
    def live() -> dict[str, Any]:
        return {"ok": True, "version": __version__}

    @app.get("/health/ready", tags=["operations"])
    def ready() -> JSONResponse:
        result = runtime_service.ready()
        return JSONResponse(result, status_code=200 if result["ok"] else 503)

    @app.get("/version", tags=["operations"])
    def version() -> dict[str, str]:
        return {"name": "humorvibes-research", "version": __version__}

    @app.get("/metrics", response_class=PlainTextResponse, dependencies=auth, tags=["operations"])
    def prometheus_metrics() -> str:
        return metrics.text()

    @app.get("/v1/capabilities", dependencies=auth, tags=["integrations"])
    def capabilities() -> dict[str, Any]:
        return runtime_service.capabilities()

    @app.post("/v1/generate", dependencies=auth, tags=["integrations"])
    def generate(payload: GenerateRequest) -> dict[str, Any]:
        return runtime_service.generate(**payload.model_dump())

    @app.post("/v1/humor/generate", dependencies=auth, tags=["humor"])
    def humor_generate(payload: HumorGenerateRequest) -> dict[str, Any]:
        values = payload.model_dump()
        values["format_key"] = values.pop("format")
        return runtime_service.generate_humor(**values)

    @app.post("/v1/judge", dependencies=auth, tags=["integrations"])
    def judge(payload: JudgeRequest) -> dict[str, Any]:
        return runtime_service.judge_json(**payload.model_dump())

    @app.post("/v1/embed", dependencies=auth, tags=["embeddings"])
    def embed(payload: EmbedRequest) -> dict[str, Any]:
        return runtime_service.embed(**payload.model_dump())

    @app.post("/v1/similarity", dependencies=auth, tags=["embeddings"])
    def similarity(payload: SimilarityRequest) -> dict[str, Any]:
        return runtime_service.similarity(**payload.model_dump())

    @app.post("/v1/signals", dependencies=auth, tags=["research"])
    def signals(payload: SignalsRequest) -> dict[str, Any]:
        return runtime_service.signals(**payload.model_dump())

    @app.get("/v1/research/study-template", dependencies=auth, tags=["research"])
    def research_study_template() -> dict[str, Any]:
        """Discover the local analyzer contract; human study rows are not uploaded here."""

        return runtime_service.study_template()

    @app.get("/v1/open-controls/metadata", dependencies=auth, tags=["open-controls"])
    def open_controls_metadata() -> dict[str, Any]:
        return runtime_service.open_controls_metadata()

    @app.post("/v1/open-controls/sample", dependencies=auth, tags=["open-controls"])
    def open_controls_sample(payload: OpenControlsSampleRequest) -> dict[str, Any]:
        return runtime_service.open_controls_sample(**payload.model_dump())

    return app


app = create_app()


def run() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install the API dependencies with: pip install 'humorvibes-research[api]'") from exc
    uvicorn.run(
        "humorvibes.api:app",
        host=os.environ.get("HUMORVIBES_HOST", "127.0.0.1"),
        port=int(os.environ.get("HUMORVIBES_PORT", "8080")),
        proxy_headers=False,
    )


if __name__ == "__main__":
    run()
