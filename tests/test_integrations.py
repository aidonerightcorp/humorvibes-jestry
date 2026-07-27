"""Adversarial contracts for authenticated LLM and embedding integrations."""

from __future__ import annotations

import io
import json
import math
import urllib.error
from dataclasses import replace

import pytest

from humorvibes.config import Settings
from humorvibes.client import HumorVibesClient
from humorvibes.embeddings import (
    EmbeddingRegistry,
    HashEmbeddingBackend,
    OllamaEmbeddingBackend,
    OpenAIEmbeddingBackend,
    cosine_similarity,
    validate_vectors,
)
from humorvibes.errors import IntegrationError
from humorvibes.http import JsonHttpClient, normalize_base_url
from humorvibes.llm import LLMRegistry, OllamaLLM, OpenAICompatibleLLM
from humorvibes.signal_providers import (
    OllamaSignalProvider,
    OpenAICompatibleSignalProvider,
    get_signal_provider,
)


class FakeResponse:
    def __init__(self, payload: object, *, headers: dict[str, str] | None = None) -> None:
        self.raw = json.dumps(payload).encode("utf-8")
        self.headers = headers or {"Content-Length": str(len(self.raw))}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit: int = -1) -> bytes:
        return self.raw if limit < 0 else self.raw[:limit]


class FakeOpener:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class StubJsonClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict | None]] = []

    def request(self, path: str, *, payload=None, **_):
        self.calls.append((path, payload))
        return self.responses.pop(0)


class StubGenerationClient:
    def __init__(self, result=None, error: IntegrationError | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = []

    def generate(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return self.result


def settings(**changes) -> Settings:
    return replace(Settings.from_env({}), **changes)


def test_ollama_key_selects_cloud_and_never_appears_in_public_config() -> None:
    runtime = Settings.from_env({"OLLAMA_API_KEY": "super-secret", "GEMMA_MODEL": "gemma4"})
    assert runtime.ollama_host == "https://ollama.com"
    assert runtime.default_llm == "ollama:gemma4"
    rendered = json.dumps(runtime.public_summary())
    assert "super-secret" not in rendered
    assert runtime.public_summary()["ollama_key_configured"] is True


def test_remote_client_mirrors_api_contract_without_exposing_its_key() -> None:
    stub = StubJsonClient([
        {"ok": True},
        {"model_id": "hash:128", "count": 2},
        {"cosine_similarity": [[1.0]]},
    ])
    client = HumorVibesClient(
        "https://api.example.test",
        api_key="client-secret",
        transport=stub,
    )
    assert client.live() == {"ok": True}
    assert client.embed(["one", "two"])["count"] == 2
    assert client.similarity(["same"], ["same"])["cosine_similarity"] == [[1.0]]
    assert "client-secret" not in repr(client)
    assert "auth_configured=True" in repr(client)
    assert stub.calls == [
        ("/health/live", None),
        ("/v1/embed", {
            "texts": ["one", "two"],
            "model_id": None,
            "dimensions": None,
        }),
        ("/v1/similarity", {
            "left": ["same"],
            "right": ["same"],
            "model_id": None,
            "dimensions": None,
        }),
    ]


def test_remote_client_environment_keeps_url_and_key_operator_scoped() -> None:
    client = HumorVibesClient.from_env({
        "HUMORVIBES_URL": "https://humor.example.test",
        "HUMORVIBES_API_KEY": "environment-secret",
    })
    assert client.base_url == "https://humor.example.test"
    assert client.auth_configured is True
    assert "environment-secret" not in repr(client)


def test_remote_client_discovers_study_template_without_uploading_rows() -> None:
    stub = StubJsonClient([
        {"privacy_boundary": {"analysis_upload_endpoint": False}},
    ])
    client = HumorVibesClient(transport=stub)
    assert client.study_template()["privacy_boundary"]["analysis_upload_endpoint"] is False
    assert stub.calls == [("/v1/research/study-template", None)]


def test_remote_client_exposes_bounded_open_controls_contract() -> None:
    stub = StubJsonClient([
        {"maximum_rows": 120_000},
        {"count": 2, "rows": []},
    ])
    client = HumorVibesClient(transport=stub)
    assert client.open_controls_metadata()["maximum_rows"] == 120_000
    assert client.open_controls_sample(count=2, arm="surprising_resolved", split="test")["count"] == 2
    assert stub.calls == [
        ("/v1/open-controls/metadata", None),
        ("/v1/open-controls/sample", {
            "count": 2,
            "seed": 20_260_727,
            "arm": "surprising_resolved",
            "split": "test",
        }),
    ]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:pass@example.com",
        "https://example.com?next=http://internal",
        "https://example.com/v1/../admin",
        "http://public.example.com",
    ],
)
def test_transport_rejects_unsafe_base_urls(url: str) -> None:
    with pytest.raises(IntegrationError):
        normalize_base_url(url)


def test_transport_allows_local_container_and_tls_hosts() -> None:
    assert normalize_base_url("http://127.0.0.1:11434/") == "http://127.0.0.1:11434"
    assert normalize_base_url("http://ollama:11434") == "http://ollama:11434"
    assert normalize_base_url("http://ollama.default.svc:11434") == "http://ollama.default.svc:11434"
    assert normalize_base_url("https://ollama.com") == "https://ollama.com"
    assert normalize_base_url("http://[::1]:11434") == "http://[::1]:11434"


def test_json_transport_adds_bearer_key_and_does_not_put_it_in_url() -> None:
    opener = FakeOpener(FakeResponse({"ok": True}))
    client = JsonHttpClient("https://ollama.com", api_key="key-value", opener=opener)
    assert client.request("/api/version") == {"ok": True}
    request = opener.requests[0][0]
    headers = dict(request.header_items())
    assert headers["Authorization"] == "Bearer key-value"
    assert headers["User-agent"] == "HumorVibes/0.7.1"
    assert "key-value" not in request.full_url


def test_json_transport_redacts_key_from_upstream_error() -> None:
    body = io.BytesIO(b'{"error":"token secret-key is invalid"}')
    error = urllib.error.HTTPError("https://ollama.com/api/generate", 401, "bad", {}, body)
    client = JsonHttpClient(
        "https://ollama.com", api_key="secret-key", opener=FakeOpener(error)
    )
    with pytest.raises(IntegrationError) as caught:
        client.request("/api/generate", payload={"model": "gemma4"})
    assert "secret-key" not in caught.value.message
    assert "[REDACTED]" in caught.value.message
    assert caught.value.detail == {"upstream_status": 401}


def test_json_transport_rejects_oversized_and_non_object_responses() -> None:
    client = JsonHttpClient(
        "http://localhost:11434",
        max_response_bytes=10,
        opener=FakeOpener(FakeResponse({"long": "response"}, headers={})),
    )
    with pytest.raises(IntegrationError, match="configured limit"):
        client.request("/api/version")
    client = JsonHttpClient(
        "http://localhost:11434", opener=FakeOpener(FakeResponse([1, 2, 3]))
    )
    with pytest.raises(IntegrationError) as caught:
        client.request("/api/version")
    assert caught.value.code == "invalid_upstream_shape"


def test_json_transport_rejects_invalid_length_and_endpoint_traversal() -> None:
    client = JsonHttpClient(
        "http://localhost:11434",
        opener=FakeOpener(FakeResponse({"ok": True}, headers={"Content-Length": "not-an-int"})),
    )
    with pytest.raises(IntegrationError) as caught:
        client.request("/api/version")
    assert caught.value.code == "invalid_upstream_headers"
    with pytest.raises(IntegrationError) as caught:
        client.request("/api/../private")
    assert caught.value.code == "invalid_endpoint"


def test_ollama_generation_uses_native_contract_auth_and_usage() -> None:
    stub = StubJsonClient([{
        "response": "complete answer",
        "prompt_eval_count": 12,
        "eval_count": 5,
        "done_reason": "stop",
    }])
    client = OllamaLLM(settings(), client=stub)
    result = client.generate(
        "ollama:gemma4", "gemma4", "prompt",
        temperature=0.4, max_tokens=99, json_mode=True, think=False,
    )
    assert result.text == "complete answer"
    assert result.prompt_tokens == 12 and result.output_tokens == 5
    path, payload = stub.calls[0]
    assert path == "/api/generate"
    assert payload["format"] == "json"
    assert payload["think"] is False
    assert payload["options"]["num_predict"] == 99


def test_generation_malformed_response_fails_without_silent_fallback() -> None:
    client = OllamaLLM(settings(), client=StubJsonClient([{"done": True}]))
    with pytest.raises(IntegrationError) as caught:
        client.generate(
            "ollama:gemma4", "gemma4", "prompt",
            temperature=0.4, max_tokens=99, json_mode=False, think=False,
        )
    assert caught.value.code == "invalid_generation_shape"

    empty = OllamaLLM(settings(), client=StubJsonClient([{"response": "   "}]))
    with pytest.raises(IntegrationError) as caught:
        empty.generate(
            "ollama:gemma4", "gemma4", "prompt",
            temperature=0.4, max_tokens=99, json_mode=False, think=False,
        )
    assert caught.value.code == "invalid_generation_shape"


def test_openai_compatible_accepts_text_parts_but_rejects_missing_content() -> None:
    stub = StubJsonClient([{
        "choices": [{"message": {"content": [
            {"type": "text", "text": "part one"},
            {"type": "text", "text": " plus two"},
        ]}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 4},
    }])
    client = OpenAICompatibleLLM(settings(), client=stub)
    result = client.generate(
        "openai:test", "test", "prompt",
        temperature=0.2, max_tokens=10, json_mode=False, think=False,
    )
    assert result.text == "part one plus two"

    broken = OpenAICompatibleLLM(settings(), client=StubJsonClient([{"choices": []}]))
    with pytest.raises(IntegrationError) as caught:
        broken.generate(
            "openai:test", "test", "prompt",
            temperature=0.2, max_tokens=10, json_mode=False, think=False,
        )
    assert caught.value.code == "invalid_generation_shape"


def test_llm_registry_enforces_exact_allowlist_and_offline_is_not_fake_generation() -> None:
    registry = LLMRegistry(settings(default_llm="offline"))
    with pytest.raises(IntegrationError) as caught:
        registry.generate("hello")
    assert caught.value.code == "llm_not_configured"
    with pytest.raises(IntegrationError) as caught:
        registry.generate("hello", model_id="ollama:unlisted")
    assert caught.value.code == "unknown_llm_model"


def test_extension_signal_provider_supports_ollama_key_without_mutating_instrument() -> None:
    from types import SimpleNamespace

    stub = StubGenerationClient(SimpleNamespace(text='{"collision": 0}'))
    runtime = Settings.from_env({"OLLAMA_API_KEY": "signal-secret", "GEMMA_MODEL": "gemma4"})
    provider = OllamaSignalProvider(runtime, client=stub)
    assert provider.api_key_configured is True
    assert provider.host == "https://ollama.com"
    assert provider.generate("prompt", max_tokens=20) == '{"collision": 0}'
    assert provider.judge_json("judge") == {"collision": 0}
    assert provider.nll_tokens("setup", "punchline").measured is False
    assert get_signal_provider("ollama", runtime).api_key_configured is True


def test_openai_signal_provider_never_reuses_an_ollama_key(monkeypatch) -> None:
    for name in (
        "GEMMA_OPENAI_KEY_ENV",
        "NVIDIA_API_KEY",
        "ADVISOR_LLM_API_KEY",
        "MISTRAL_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    runtime = Settings.from_env({"OLLAMA_API_KEY": "ollama-only-secret"})
    provider = OpenAICompatibleSignalProvider(
        runtime,
        client=StubGenerationClient(),
    )
    assert provider.key_configured is False


def test_extension_signal_provider_fails_without_secret_or_error_reflection() -> None:
    failure = IntegrationError("upstream_unreachable", "contains-secret", 503)
    provider = OllamaSignalProvider(settings(), client=StubGenerationClient(error=failure))
    assert provider.generate("prompt") == ""
    assert provider.last_error == "upstream_unreachable"


@pytest.mark.parametrize(
    "vectors,code",
    [
        ([[1.0, 0.0]], "embedding_count_mismatch"),
        ([[1.0, 0.0], [1.0]], "embedding_dimension_mismatch"),
        ([[1.0, math.nan], [1.0, 0.0]], "nonfinite_embedding_value"),
        ([[0.0, 0.0], [1.0, 0.0]], "zero_embedding_vector"),
        ([[True, 0.0], [1.0, 0.0]], "invalid_embedding_value"),
    ],
)
def test_embedding_vector_adversaries_fail_closed(vectors, code: str) -> None:
    with pytest.raises(IntegrationError) as caught:
        validate_vectors(vectors, 2)
    assert caught.value.code == code


def test_ollama_embedding_uses_batch_endpoint_and_binds_dimensions() -> None:
    stub = StubJsonClient([
        {"embeddings": [[1.0, 0.0], [0.0, 1.0]]},
        {"embeddings": [[1.0, 0.0, 0.0]]},
    ])
    backend = OllamaEmbeddingBackend(settings(), "embeddinggemma", client=stub)
    result = backend.embed(["one", "two"])
    assert result.dimensions == 2
    assert len(result.vectors) == 2
    assert stub.calls[0][0] == "/api/embed"
    assert stub.calls[0][1]["truncate"] is False
    with pytest.raises(IntegrationError) as caught:
        backend.embed(["three"])
    assert caught.value.code == "embedding_dimension_changed"


def test_openai_embedding_reorders_indices_and_rejects_duplicates() -> None:
    stub = StubJsonClient([{"data": [
        {"index": 1, "embedding": [0.0, 1.0]},
        {"index": 0, "embedding": [1.0, 0.0]},
    ]}])
    result = OpenAIEmbeddingBackend(settings(), "embed-test", client=stub).embed(["a", "b"])
    assert result.vectors == [[1.0, 0.0], [0.0, 1.0]]

    duplicate = StubJsonClient([{"data": [
        {"index": 0, "embedding": [1.0, 0.0]},
        {"index": 0, "embedding": [0.0, 1.0]},
    ]}])
    with pytest.raises(IntegrationError) as caught:
        OpenAIEmbeddingBackend(settings(), "embed-test", client=duplicate).embed(["a", "b"])
    assert caught.value.code == "invalid_embedding_indices"

    boolean = StubJsonClient([{"data": [{"index": True, "embedding": [1.0, 0.0]}]}])
    with pytest.raises(IntegrationError) as caught:
        OpenAIEmbeddingBackend(settings(), "embed-test", client=boolean).embed(["a"])
    assert caught.value.code == "invalid_embedding_indices"


def test_embedding_registry_supports_multiple_models_without_cross_model_fallback() -> None:
    runtime = settings(
        ollama_embedding_models=("embeddinggemma", "qwen3-embedding", "all-minilm"),
        default_embedding="hash:128",
    )
    registry = EmbeddingRegistry(runtime)
    model_ids = {row["model_id"] for row in registry.capabilities()}
    assert {"hash:128", "ollama:embeddinggemma", "ollama:qwen3-embedding", "ollama:all-minilm"}.issubset(model_ids)
    result = registry.embed(["same words", "same words"])
    assert result.model_id == "hash:128" and result.dimensions == 128
    with pytest.raises(IntegrationError) as caught:
        registry.embed(["text"], model_id="ollama:not-allowlisted")
    assert caught.value.code == "unknown_embedding_model"


def test_capabilities_distinguish_internal_and_remote_provider_locations() -> None:
    local_registry = LLMRegistry(settings(ollama_host="http://ollama:11434"))
    assert next(row for row in local_registry.capabilities() if row["provider"] == "ollama")["local"] is True
    remote_registry = EmbeddingRegistry(settings(ollama_host="https://models.example.com"))
    assert next(row for row in remote_registry.capabilities() if row["provider"] == "ollama")["local"] is False


def test_cosine_rejects_mismatched_nonfinite_and_zero_vectors() -> None:
    with pytest.raises(IntegrationError):
        cosine_similarity([1.0], [1.0, 2.0])
    with pytest.raises(IntegrationError):
        cosine_similarity([math.inf], [1.0])
    with pytest.raises(IntegrationError):
        cosine_similarity([0.0, 0.0], [1.0, 0.0])
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_hash_backend_is_deterministic_unicode_aware_and_explicitly_nonsemantic() -> None:
    backend = HashEmbeddingBackend(128)
    first = backend.embed(["一箭双雕", "same text"])
    second = backend.embed(["一箭双雕", "same text"])
    assert first.vectors == second.vectors
    assert first.model_id == "hash:128"
