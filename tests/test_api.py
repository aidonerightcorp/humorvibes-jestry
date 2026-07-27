"""HTTP boundary tests for app, container, and cluster integration."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

import humorvibes.api as api_module
from humorvibes.api import _BodyLimitMiddleware, create_app
from humorvibes.config import Settings
from humorvibes.openapi import openapi_schema
from humorvibes.service import HumorVibesService


def runtime(**changes) -> Settings:
    return replace(Settings.from_env({}), **changes)


def client(settings: Settings | None = None, service: HumorVibesService | None = None) -> TestClient:
    return TestClient(create_app(settings or runtime(), service), raise_server_exceptions=False)


def auth() -> dict[str, str]:
    return {"Authorization": "Bearer inbound-secret"}


def test_liveness_readiness_version_and_openapi_are_available() -> None:
    with client() as api:
        assert api.get("/health/live").json()["ok"] is True
        ready = api.get("/health/ready")
        assert ready.status_code == 200 and ready.json()["ok"] is True
        assert api.get("/version").json()["version"] == "0.4.0"
        schema = api.get("/openapi.json").json()
        assert schema["info"]["title"] == "HumorVibes Integration API"
        assert "/v1/embed" in schema["paths"]


def test_standalone_server_defaults_to_loopback(monkeypatch) -> None:
    observed = {}
    monkeypatch.delenv("HUMORVIBES_HOST", raising=False)
    monkeypatch.delenv("HUMORVIBES_PORT", raising=False)
    monkeypatch.setattr(
        "uvicorn.run",
        lambda app, **kwargs: observed.update({"app": app, **kwargs}),
    )
    api_module.run()
    assert observed["app"] == "humorvibes.api:app"
    assert observed["host"] == "127.0.0.1"
    assert observed["port"] == 8080
    assert observed["proxy_headers"] is False


def test_checked_in_openapi_contract_matches_the_runtime_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    checked_in = json.loads((root / "docs/openapi.json").read_text(encoding="utf-8"))
    assert checked_in == openapi_schema()
    assert checked_in["info"]["version"] == "0.4.0"
    assert "/v1/generate" in checked_in["paths"]
    assert "/v1/embed" in checked_in["paths"]
    assert "OLLAMA_API_KEY" not in json.dumps(checked_in)


def test_api_key_protects_v1_and_metrics_but_not_health() -> None:
    with client(runtime(api_key="inbound-secret")) as api:
        assert api.get("/health/live").status_code == 200
        missing = api.get("/v1/capabilities")
        assert missing.status_code == 401
        assert missing.headers["www-authenticate"] == "Bearer"
        assert api.get("/v1/capabilities", headers={"Authorization": "Basic nope"}).status_code == 401
        assert api.get("/v1/capabilities", headers=auth()).status_code == 200
        assert api.get("/metrics").status_code == 401
        assert api.get("/metrics", headers=auth()).status_code == 200


def test_capabilities_are_secret_free_and_truth_scoped() -> None:
    settings = runtime(api_key="inbound-secret", ollama_api_key="upstream-secret")
    with client(settings) as api:
        response = api.get("/v1/capabilities", headers=auth())
    rendered = response.text
    assert response.status_code == 200
    assert "inbound-secret" not in rendered and "upstream-secret" not in rendered
    payload = response.json()
    assert payload["settings"]["api_auth_required"] is True
    assert payload["settings"]["ollama_key_configured"] is True
    assert payload["truth_boundary"]["generation_is_not_human_validation"] is True
    assert payload["truth_boundary"]["audience_traits_must_not_be_inferred"] is True
    assert payload["truth_boundary"]["personalization_requires_opt_in_data"] is True
    assert payload["product_use_cases"]["creative_assistance"]["status"] == (
        "available_with_human_selection"
    )
    assert payload["product_use_cases"]["creative_assistance"]["claim_gate"] == (
        "blind_or_live_human_response"
    )
    assert payload["product_use_cases"]["audience_personalization"]["status"] == (
        "experimental_requires_opt_in_data"
    )


def test_hash_embedding_and_similarity_work_without_network_or_model() -> None:
    with client() as api:
        embedded = api.post("/v1/embed", json={"texts": ["same words", "same words"]})
        assert embedded.status_code == 200
        body = embedded.json()
        assert body["model_id"] == "hash:128"
        assert body["count"] == 2 and body["dimensions"] == 128
        assert body["validated"] is True

        compared = api.post(
            "/v1/similarity",
            json={"left": ["same words"], "right": ["same words", "different tokens"]},
        )
        assert compared.status_code == 200
        matrix = compared.json()["cosine_similarity"]
        assert matrix[0][0] == 1.0
        assert len(matrix) == 1 and len(matrix[0]) == 2


def test_offline_generation_fails_explicitly_and_signals_name_the_boundary() -> None:
    with client() as api:
        generated = api.post("/v1/generate", json={"prompt": "do not invent a fallback"})
        assert generated.status_code == 503
        assert generated.json()["error"]["code"] == "llm_not_configured"

        signals = api.post(
            "/v1/signals",
            json={"setup": "A setup establishes a frame.", "punchline": "Then the frame turns."},
        )
        assert signals.status_code == 200
        body = signals.json()
        assert body["truth_boundary"]["teacher_forced_logprobs_measured"] is False
        assert body["truth_boundary"]["surprisal_is_not_funniness"] is True


def test_validation_errors_do_not_echo_inputs_or_accept_runtime_overrides() -> None:
    attack = "PROMPT-MUST-NOT-BE-ECHOED"
    with client() as api:
        response = api.post(
            "/v1/generate",
            json={"prompt": attack, "host": "http://169.254.169.254"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert attack not in response.text
    assert "169.254.169.254" not in response.text

    with client() as api:
        boolean_integer = api.post(
            "/v1/generate",
            json={"prompt": "strict types", "max_tokens": True},
        )
    assert boolean_integer.status_code == 422
    assert boolean_integer.json()["error"]["code"] == "invalid_request"


def test_request_id_headers_are_validated_and_security_headers_are_set() -> None:
    with client() as api:
        good = api.get("/health/live", headers={"X-Request-ID": "caller-123"})
        assert good.headers["x-request-id"] == "caller-123"
        assert good.headers["x-content-type-options"] == "nosniff"
        assert good.headers["cache-control"] == "no-store"

        bad = api.get("/health/live", headers={"X-Request-ID": "bad id\nvalue"})
        observed = bad.headers["x-request-id"]
        assert observed != "bad id\nvalue"
        assert len(observed) == 32


def test_content_length_and_chunked_bodies_are_bounded() -> None:
    small_runtime = runtime(max_request_bytes=128)
    with client(small_runtime) as api:
        response = api.post("/v1/generate", content=b"x" * 129, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"

    sent: list[dict] = []
    inbound = iter([
        {"type": "http.request", "body": b"a" * 80, "more_body": True},
        {"type": "http.request", "body": b"b" * 80, "more_body": False},
    ])

    async def receive() -> dict:
        return next(inbound)

    async def send(message: dict) -> None:
        sent.append(message)

    async def downstream(scope, receive, send):
        raise AssertionError("oversized body reached downstream")

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/generate",
        "headers": [],
        "state": {"request_id": "chunked"},
    }
    asyncio.run(_BodyLimitMiddleware(downstream, 128)(scope, receive, send))
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    assert start["status"] == 413
    assert json.loads(body)["error"]["code"] == "request_too_large"


def test_per_process_rate_limit_and_prometheus_metrics() -> None:
    with client(runtime(rate_limit_per_minute=1)) as api:
        assert api.get("/v1/capabilities").status_code == 200
        limited = api.get("/v1/capabilities")
        assert limited.status_code == 429
        assert limited.headers["retry-after"] == "60"
        metrics = api.get("/metrics")
    assert metrics.status_code == 200
    assert "humorvibes_requests_total" in metrics.text
    assert 'humorvibes_responses_total{status="429"} 1' in metrics.text


class _ExplodingService(HumorVibesService):
    def capabilities(self):
        raise RuntimeError("internal-secret-must-not-leak")


def test_internal_exceptions_are_sanitized() -> None:
    with client(service=_ExplodingService(runtime())) as api:
        response = api.get("/v1/capabilities")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "internal-secret-must-not-leak" not in response.text
