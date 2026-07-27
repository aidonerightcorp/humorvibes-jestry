"""Environment-backed runtime settings with secret-safe public summaries."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


def _csv(value: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    rows = tuple(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))
    return rows or default


def _bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(value: str, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, parsed))


def _bounded_float(value: str, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, parsed))


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    ollama_api_key: str
    ollama_models: tuple[str, ...]
    ollama_embedding_models: tuple[str, ...]
    openai_base_url: str
    openai_api_key: str
    openai_models: tuple[str, ...]
    openai_embedding_models: tuple[str, ...]
    sentence_transformer_models: tuple[str, ...]
    default_llm: str
    default_embedding: str
    signal_provider: str
    request_timeout_seconds: float
    api_key: str
    cors_origins: tuple[str, ...]
    max_prompt_chars: int
    max_text_chars: int
    max_batch_items: int
    max_batch_chars: int
    max_response_bytes: int
    max_request_bytes: int
    rate_limit_per_minute: int
    strict_readiness: bool
    allow_insecure_remote: bool

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = dict(os.environ if environ is None else environ)
        ollama_key = env.get("OLLAMA_API_KEY") or env.get("OLLAMA_CLOUD_API_KEY", "")
        ollama_host = env.get("OLLAMA_HOST", "").strip()
        if not ollama_host:
            ollama_host = "https://ollama.com" if ollama_key else "http://127.0.0.1:11434"
        ollama_models = _csv(
            env.get("HUMORVIBES_OLLAMA_MODELS", ""),
            (env.get("GEMMA_MODEL", "gemma3:4b"),),
        )
        ollama_embedding_models = _csv(
            env.get("HUMORVIBES_OLLAMA_EMBED_MODELS", ""),
            (
                "embeddinggemma",
                "qwen3-embedding",
                "all-minilm",
                "nomic-embed-text",
                "mxbai-embed-large",
                "bge-m3",
            ),
        )
        openai_key = env.get("HUMORVIBES_OPENAI_API_KEY") or env.get("OPENAI_API_KEY", "")
        openai_models = _csv(env.get("HUMORVIBES_OPENAI_MODELS", ""))
        openai_embedding_models = _csv(env.get("HUMORVIBES_OPENAI_EMBED_MODELS", ""))
        sentence_models = _csv(env.get("HUMORVIBES_SENTENCE_TRANSFORMER_MODELS", ""))

        inferred_llm = f"ollama:{ollama_models[0]}" if (
            ollama_key or env.get("OLLAMA_HOST") or env.get("GEMMA_PROVIDER", "").lower() == "ollama"
        ) else "offline"
        return cls(
            ollama_host=ollama_host,
            ollama_api_key=ollama_key,
            ollama_models=ollama_models,
            ollama_embedding_models=ollama_embedding_models,
            openai_base_url=env.get("HUMORVIBES_OPENAI_BASE_URL", env.get("OPENAI_BASE_URL", "https://api.openai.com/v1")),
            openai_api_key=openai_key,
            openai_models=openai_models,
            openai_embedding_models=openai_embedding_models,
            sentence_transformer_models=sentence_models,
            default_llm=env.get("HUMORVIBES_LLM_DEFAULT", inferred_llm).strip(),
            default_embedding=env.get("HUMORVIBES_EMBEDDING_DEFAULT", "hash:128").strip(),
            signal_provider=env.get("HUMORVIBES_SIGNAL_PROVIDER", "offline").strip().lower(),
            request_timeout_seconds=_bounded_float(env.get("HUMORVIBES_REQUEST_TIMEOUT", ""), 120.0, 1.0, 300.0),
            api_key=env.get("HUMORVIBES_API_KEY", ""),
            cors_origins=_csv(env.get("HUMORVIBES_CORS_ORIGINS", "")),
            max_prompt_chars=_bounded_int(env.get("HUMORVIBES_MAX_PROMPT_CHARS", ""), 20_000, 128, 200_000),
            max_text_chars=_bounded_int(env.get("HUMORVIBES_MAX_TEXT_CHARS", ""), 32_000, 32, 200_000),
            max_batch_items=_bounded_int(env.get("HUMORVIBES_MAX_BATCH_ITEMS", ""), 64, 1, 512),
            max_batch_chars=_bounded_int(env.get("HUMORVIBES_MAX_BATCH_CHARS", ""), 256_000, 128, 2_000_000),
            max_response_bytes=_bounded_int(env.get("HUMORVIBES_MAX_RESPONSE_BYTES", ""), 10_000_000, 1024, 100_000_000),
            max_request_bytes=_bounded_int(env.get("HUMORVIBES_MAX_REQUEST_BYTES", ""), 1_000_000, 1024, 20_000_000),
            rate_limit_per_minute=_bounded_int(env.get("HUMORVIBES_RATE_LIMIT_PER_MINUTE", ""), 0, 0, 100_000),
            strict_readiness=_bool(env.get("HUMORVIBES_STRICT_READINESS", "")),
            allow_insecure_remote=_bool(env.get("HUMORVIBES_ALLOW_INSECURE_REMOTE", "")),
        )

    def public_summary(self) -> dict[str, object]:
        return {
            "default_llm": self.default_llm,
            "default_embedding": self.default_embedding,
            "signal_provider": self.signal_provider,
            "ollama_key_configured": bool(self.ollama_api_key),
            "openai_key_configured": bool(self.openai_api_key),
            "api_auth_required": bool(self.api_key),
            "cors_origins_configured": len(self.cors_origins),
            "strict_readiness": self.strict_readiness,
            "limits": {
                "prompt_chars": self.max_prompt_chars,
                "text_chars": self.max_text_chars,
                "batch_items": self.max_batch_items,
                "batch_chars": self.max_batch_chars,
                "request_bytes": self.max_request_bytes,
            },
        }
