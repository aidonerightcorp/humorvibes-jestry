"""Validated embedding backends and an exact-model registry."""

from __future__ import annotations

import hashlib
import math
import re
import threading
from dataclasses import asdict, dataclass
from typing import Any

from .config import Settings
from .errors import IntegrationError
from .http import JsonHttpClient, base_url_is_internal

TOKEN_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)


@dataclass(frozen=True)
class EmbeddingModelSpec:
    model_id: str
    provider: str
    remote_model: str
    semantic: bool
    local: bool
    key_configured: bool
    configured_dimensions: int | None = None


@dataclass
class EmbeddingResult:
    model_id: str
    provider: str
    remote_model: str
    vectors: list[list[float]]
    dimensions: int
    normalized: bool

    def public(self, *, include_vectors: bool = True) -> dict[str, Any]:
        payload = {
            "model_id": self.model_id,
            "provider": self.provider,
            "remote_model": self.remote_model,
            "dimensions": self.dimensions,
            "normalized": self.normalized,
            "count": len(self.vectors),
            "validated": True,
        }
        if include_vectors:
            payload["vectors"] = self.vectors
        return payload


class HashEmbeddingBackend:
    provider = "hash"

    def __init__(self, dimensions: int = 128) -> None:
        if not 16 <= dimensions <= 4096:
            raise IntegrationError("invalid_dimensions", "Hash dimensions must be between 16 and 4096.", 500)
        self.dimensions = dimensions
        self.model_id = f"hash:{dimensions}"

    def embed(self, texts: list[str], *, dimensions: int | None = None) -> EmbeddingResult:
        dims = dimensions or self.dimensions
        if dims != self.dimensions:
            raise IntegrationError("unsupported_dimensions", "This hash model has fixed dimensions.", 422)
        vectors = [_hash_embedding(text, dims) for text in texts]
        vectors, actual, normalized = validate_vectors(vectors, len(texts))
        return EmbeddingResult(self.model_id, self.provider, self.model_id, vectors, actual, normalized)

    def probe(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.provider, "dimensions": self.dimensions}


class OllamaEmbeddingBackend:
    provider = "ollama"

    def __init__(
        self,
        settings: Settings,
        model: str,
        *,
        client: JsonHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self.model = model
        self.model_id = f"ollama:{model}"
        self.client = client or JsonHttpClient(
            settings.ollama_host,
            api_key=settings.ollama_api_key,
            timeout=settings.request_timeout_seconds,
            max_response_bytes=settings.max_response_bytes,
            allow_insecure_remote=settings.allow_insecure_remote,
        )
        self._observed_dimensions: int | None = None

    def embed(self, texts: list[str], *, dimensions: int | None = None) -> EmbeddingResult:
        payload: dict[str, Any] = {"model": self.model, "input": texts, "truncate": False}
        if dimensions is not None:
            payload["dimensions"] = dimensions
        data = self.client.request("/api/embed", payload=payload)
        vectors, actual, normalized = validate_vectors(data.get("embeddings"), len(texts))
        self._bind_dimensions(actual)
        return EmbeddingResult(self.model_id, self.provider, self.model, vectors, actual, normalized)

    def _bind_dimensions(self, value: int) -> None:
        if self._observed_dimensions is not None and self._observed_dimensions != value:
            raise IntegrationError(
                "embedding_dimension_changed",
                "Embedding dimensions changed for the same configured model.",
                502,
                detail={"expected": self._observed_dimensions, "observed": value},
            )
        self._observed_dimensions = value

    def probe(self) -> dict[str, Any]:
        try:
            result = self.embed(["HumorVibes capability probe."])
            return {"ok": True, "provider": self.provider, "model_id": self.model_id, "dimensions": result.dimensions}
        except IntegrationError as exc:
            return {"ok": False, "provider": self.provider, "model_id": self.model_id, "error": exc.public()}


class OpenAIEmbeddingBackend:
    provider = "openai-compatible"

    def __init__(
        self,
        settings: Settings,
        model: str,
        *,
        client: JsonHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self.model = model
        self.model_id = f"openai:{model}"
        self.client = client or JsonHttpClient(
            settings.openai_base_url,
            api_key=settings.openai_api_key,
            timeout=settings.request_timeout_seconds,
            max_response_bytes=settings.max_response_bytes,
            allow_insecure_remote=settings.allow_insecure_remote,
        )
        self._observed_dimensions: int | None = None

    def embed(self, texts: list[str], *, dimensions: int | None = None) -> EmbeddingResult:
        payload: dict[str, Any] = {"model": self.model, "input": texts, "encoding_format": "float"}
        if dimensions is not None:
            payload["dimensions"] = dimensions
        data = self.client.request("/embeddings", payload=payload)
        rows = data.get("data")
        if not isinstance(rows, list):
            raise IntegrationError("invalid_embedding_shape", "Embedding response has no data array.", 502)
        ordered: list[Any] = [None] * len(rows)
        for fallback_index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise IntegrationError("invalid_embedding_shape", "Embedding data rows must be objects.", 502)
            index = row.get("index", fallback_index)
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or index < 0
                or index >= len(rows)
                or ordered[index] is not None
            ):
                raise IntegrationError("invalid_embedding_indices", "Embedding response indices are invalid.", 502)
            ordered[index] = row.get("embedding")
        vectors, actual, normalized = validate_vectors(ordered, len(texts))
        if self._observed_dimensions is not None and self._observed_dimensions != actual:
            raise IntegrationError("embedding_dimension_changed", "Embedding dimensions changed for the same configured model.", 502)
        self._observed_dimensions = actual
        return EmbeddingResult(self.model_id, self.provider, self.model, vectors, actual, normalized)

    def probe(self) -> dict[str, Any]:
        try:
            result = self.embed(["HumorVibes capability probe."])
            return {"ok": True, "provider": self.provider, "model_id": self.model_id, "dimensions": result.dimensions}
        except IntegrationError as exc:
            return {"ok": False, "provider": self.provider, "model_id": self.model_id, "error": exc.public()}


class SentenceTransformerEmbeddingBackend:
    provider = "sentence-transformers"

    def __init__(self, model: str) -> None:
        self.model = model
        self.model_id = f"sentence-transformers:{model}"
        self._instance: Any = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        with self._lock:
            if self._instance is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError:
                    raise IntegrationError(
                        "optional_dependency_missing",
                        "Install humorvibes-research[local-embeddings] for sentence-transformers models.",
                        503,
                    ) from None
                self._instance = SentenceTransformer(self.model)
        return self._instance

    def embed(self, texts: list[str], *, dimensions: int | None = None) -> EmbeddingResult:
        if dimensions is not None:
            raise IntegrationError("unsupported_dimensions", "Sentence-transformers dimensions are model-defined.", 422)
        raw = self._load().encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        vectors, actual, normalized = validate_vectors(raw.tolist(), len(texts))
        return EmbeddingResult(self.model_id, self.provider, self.model, vectors, actual, normalized)

    def probe(self) -> dict[str, Any]:
        try:
            result = self.embed(["HumorVibes capability probe."])
            return {"ok": True, "provider": self.provider, "model_id": self.model_id, "dimensions": result.dimensions}
        except IntegrationError as exc:
            return {"ok": False, "provider": self.provider, "model_id": self.model_id, "error": exc.public()}


class EmbeddingRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._models: dict[str, tuple[EmbeddingModelSpec, Any]] = {}
        hash_backend = HashEmbeddingBackend(128)
        self._register(
            EmbeddingModelSpec(hash_backend.model_id, "hash", hash_backend.model_id, False, True, False, 128),
            hash_backend,
        )
        for model in self.settings.ollama_embedding_models:
            backend = OllamaEmbeddingBackend(self.settings, model)
            self._register(
                EmbeddingModelSpec(
                    backend.model_id,
                    "ollama",
                    model,
                    True,
                    base_url_is_internal(self.settings.ollama_host),
                    bool(self.settings.ollama_api_key),
                ),
                backend,
            )
        for model in self.settings.openai_embedding_models:
            backend = OpenAIEmbeddingBackend(self.settings, model)
            self._register(
                EmbeddingModelSpec(
                    backend.model_id,
                    "openai-compatible",
                    model,
                    True,
                    base_url_is_internal(self.settings.openai_base_url),
                    bool(self.settings.openai_api_key),
                ),
                backend,
            )
        for model in self.settings.sentence_transformer_models:
            backend = SentenceTransformerEmbeddingBackend(model)
            self._register(EmbeddingModelSpec(backend.model_id, backend.provider, model, True, True, False), backend)

    def _register(self, spec: EmbeddingModelSpec, backend: Any) -> None:
        if spec.model_id in self._models:
            raise IntegrationError("duplicate_model_id", "Duplicate embedding model ID in configuration.", 500)
        self._models[spec.model_id] = (spec, backend)

    def embed(
        self,
        texts: list[str],
        *,
        model_id: str | None = None,
        dimensions: int | None = None,
    ) -> EmbeddingResult:
        self._validate_inputs(texts)
        selected = model_id or self.settings.default_embedding
        row = self._models.get(selected)
        if row is None:
            raise IntegrationError(
                "unknown_embedding_model",
                "Requested embedding model is not in the server allowlist.",
                400,
                detail={"model_id": selected},
            )
        return row[1].embed(texts, dimensions=dimensions)

    def _validate_inputs(self, texts: list[str]) -> None:
        if not texts:
            raise IntegrationError("empty_embedding_batch", "At least one text is required.", 422)
        if len(texts) > self.settings.max_batch_items:
            raise IntegrationError("embedding_batch_too_large", "Embedding batch exceeds the item limit.", 413)
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise IntegrationError("invalid_embedding_text", "Embedding texts must be non-empty strings.", 422)
        if any(len(text) > self.settings.max_text_chars for text in texts):
            raise IntegrationError("embedding_text_too_large", "An embedding text exceeds the character limit.", 413)
        if sum(len(text) for text in texts) > self.settings.max_batch_chars:
            raise IntegrationError("embedding_batch_too_large", "Embedding batch exceeds the character limit.", 413)

    def capabilities(self) -> list[dict[str, Any]]:
        return [asdict(spec) for spec, _ in self._models.values()]

    def probe(self, model_id: str | None = None) -> dict[str, Any]:
        selected = model_id or self.settings.default_embedding
        row = self._models.get(selected)
        if row is None:
            return {"ok": False, "error": {"code": "unknown_embedding_model"}, "model_id": selected}
        return row[1].probe()


def validate_vectors(raw: Any, expected_count: int) -> tuple[list[list[float]], int, bool]:
    if not isinstance(raw, list) or len(raw) != expected_count:
        raise IntegrationError(
            "embedding_count_mismatch",
            "Embedding response count does not match the request.",
            502,
            detail={"expected": expected_count, "observed": len(raw) if isinstance(raw, list) else None},
        )
    vectors: list[list[float]] = []
    dimensions: int | None = None
    normalized = True
    for row in raw:
        if not isinstance(row, list) or not row:
            raise IntegrationError("invalid_embedding_vector", "Embedding vectors must be non-empty arrays.", 502)
        vector: list[float] = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise IntegrationError("invalid_embedding_value", "Embedding vectors must contain only numbers.", 502)
            number = float(value)
            if not math.isfinite(number):
                raise IntegrationError("nonfinite_embedding_value", "Embedding vectors contain a non-finite number.", 502)
            vector.append(number)
        if dimensions is None:
            dimensions = len(vector)
            if not 1 <= dimensions <= 65_536:
                raise IntegrationError("invalid_embedding_dimensions", "Embedding dimensions are outside the supported range.", 502)
        elif len(vector) != dimensions:
            raise IntegrationError("embedding_dimension_mismatch", "Embedding vectors have inconsistent dimensions.", 502)
        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 1e-12:
            raise IntegrationError("zero_embedding_vector", "Embedding response contains a zero vector.", 502)
        normalized = normalized and abs(norm - 1.0) <= 1e-3
        vectors.append(vector)
    return vectors, int(dimensions or 0), normalized


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        raise IntegrationError("embedding_dimension_mismatch", "Cosine inputs must have equal non-zero dimensions.", 422)
    if any(not math.isfinite(value) for value in left + right):
        raise IntegrationError("nonfinite_embedding_value", "Cosine inputs contain a non-finite number.", 422)
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        raise IntegrationError("zero_embedding_vector", "Cosine inputs must not be zero vectors.", 422)
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _hash_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for match in TOKEN_RE.finditer(text.lower()):
        token = match.group(0)
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        bucket = int.from_bytes(digest[:8], "little") % dimensions
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        vector[bucket] += sign * (1.0 + min(len(token), 16) / 16.0)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 1e-12:
        raise IntegrationError("empty_embedding_tokens", "Text contains no embeddable tokens.", 422)
    return [value / norm for value in vector]
