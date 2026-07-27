"""Capability-scoped LLM integrations with explicit model allowlists."""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass
from typing import Any

from .config import Settings
from .errors import IntegrationError
from .http import JsonHttpClient, base_url_is_internal


@dataclass(frozen=True)
class LLMModelSpec:
    model_id: str
    provider: str
    remote_model: str
    key_configured: bool
    local: bool
    supports_json: bool
    supports_thinking: bool
    measured_logprobs: bool = False


@dataclass
class GenerationResult:
    model_id: str
    provider: str
    remote_model: str
    text: str
    prompt_tokens: int | None
    output_tokens: int | None
    finish_reason: str
    wall_ms: int
    thinking_enabled: bool

    def public(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["output_sha256"] = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        return payload


class OllamaLLM:
    provider = "ollama"

    def __init__(self, settings: Settings, *, client: JsonHttpClient | None = None) -> None:
        self.settings = settings
        self.client = client or JsonHttpClient(
            settings.ollama_host,
            api_key=settings.ollama_api_key,
            timeout=settings.request_timeout_seconds,
            max_response_bytes=settings.max_response_bytes,
            allow_insecure_remote=settings.allow_insecure_remote,
        )

    def raw_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.client.request("/api/generate", payload=payload)

    def generate(
        self,
        model_id: str,
        remote_model: str,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        think: bool,
        system: str = "",
    ) -> GenerationResult:
        payload: dict[str, Any] = {
            "model": remote_model,
            "prompt": prompt,
            "stream": False,
            "think": think,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        started = time.monotonic()
        data = self.raw_generate(payload)
        text = data.get("response")
        if not isinstance(text, str) or not text.strip():
            raise IntegrationError("invalid_generation_shape", "Ollama response is missing string field 'response'.", 502)
        return GenerationResult(
            model_id=model_id,
            provider=self.provider,
            remote_model=remote_model,
            text=text.strip(),
            prompt_tokens=_optional_int(data.get("prompt_eval_count")),
            output_tokens=_optional_int(data.get("eval_count")),
            finish_reason=str(data.get("done_reason", "")),
            wall_ms=round((time.monotonic() - started) * 1000),
            thinking_enabled=think,
        )

    def probe(self) -> dict[str, Any]:
        try:
            data = self.client.request("/api/version")
            return {"ok": True, "provider": self.provider, "version": str(data.get("version", "unknown"))}
        except IntegrationError as exc:
            return {"ok": False, "provider": self.provider, "error": exc.public()}


class OpenAICompatibleLLM:
    provider = "openai-compatible"

    def __init__(self, settings: Settings, *, client: JsonHttpClient | None = None) -> None:
        self.settings = settings
        self.client = client or JsonHttpClient(
            settings.openai_base_url,
            api_key=settings.openai_api_key,
            timeout=settings.request_timeout_seconds,
            max_response_bytes=settings.max_response_bytes,
            allow_insecure_remote=settings.allow_insecure_remote,
        )

    def generate(
        self,
        model_id: str,
        remote_model: str,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        think: bool,
        system: str = "",
    ) -> GenerationResult:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": remote_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        data = self.client.request("/chat/completions", payload=payload)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise IntegrationError("invalid_generation_shape", "OpenAI-compatible response has no message content.", 502) from None
        text = _content_text(content)
        if not text.strip():
            raise IntegrationError("invalid_generation_shape", "OpenAI-compatible response content is empty.", 502)
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return GenerationResult(
            model_id=model_id,
            provider=self.provider,
            remote_model=remote_model,
            text=text.strip(),
            prompt_tokens=_optional_int(usage.get("prompt_tokens")),
            output_tokens=_optional_int(usage.get("completion_tokens")),
            finish_reason=str(choice.get("finish_reason", "")),
            wall_ms=round((time.monotonic() - started) * 1000),
            thinking_enabled=think,
        )

    def probe(self) -> dict[str, Any]:
        try:
            data = self.client.request("/models")
            rows = data.get("data", [])
            return {"ok": isinstance(rows, list), "provider": self.provider, "models_visible": len(rows) if isinstance(rows, list) else 0}
        except IntegrationError as exc:
            return {"ok": False, "provider": self.provider, "error": exc.public()}


class LLMRegistry:
    """Exact model IDs prevent callers from turning the API into an arbitrary proxy."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        ollama: OllamaLLM | None = None,
        openai: OpenAICompatibleLLM | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self._ollama = ollama or OllamaLLM(self.settings)
        self._openai = openai or OpenAICompatibleLLM(self.settings)
        self._models: dict[str, tuple[LLMModelSpec, Any]] = {}
        for model in self.settings.ollama_models:
            model_id = f"ollama:{model}"
            self._models[model_id] = (
                LLMModelSpec(
                    model_id=model_id,
                    provider="ollama",
                    remote_model=model,
                    key_configured=bool(self.settings.ollama_api_key),
                    local=base_url_is_internal(self.settings.ollama_host),
                    supports_json=True,
                    supports_thinking=True,
                ),
                self._ollama,
            )
        for model in self.settings.openai_models:
            model_id = f"openai:{model}"
            self._models[model_id] = (
                LLMModelSpec(
                    model_id=model_id,
                    provider="openai-compatible",
                    remote_model=model,
                    key_configured=bool(self.settings.openai_api_key),
                    local=base_url_is_internal(self.settings.openai_base_url),
                    supports_json=True,
                    supports_thinking=False,
                ),
                self._openai,
            )

    def generate(
        self,
        prompt: str,
        *,
        model_id: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 512,
        json_mode: bool = False,
        think: bool = False,
        system: str = "",
    ) -> GenerationResult:
        if not prompt.strip():
            raise IntegrationError("empty_prompt", "Prompt must not be empty.", 422)
        if len(prompt) > self.settings.max_prompt_chars or len(system) > self.settings.max_prompt_chars:
            raise IntegrationError("prompt_too_large", "Prompt exceeds the configured character limit.", 413)
        if not 0.0 <= temperature <= 2.0:
            raise IntegrationError("invalid_temperature", "Temperature must be between 0 and 2.", 422)
        if not 1 <= max_tokens <= 4096:
            raise IntegrationError("invalid_max_tokens", "max_tokens must be between 1 and 4096.", 422)
        selected = model_id or self.settings.default_llm
        if selected == "offline":
            raise IntegrationError(
                "llm_not_configured",
                "No live LLM is configured. Select an allowlisted Ollama or OpenAI-compatible model.",
                503,
            )
        row = self._models.get(selected)
        if row is None:
            raise IntegrationError(
                "unknown_llm_model",
                "Requested model is not in the server allowlist.",
                400,
                detail={"model_id": selected},
            )
        spec, client = row
        return client.generate(
            spec.model_id,
            spec.remote_model,
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            think=think,
            system=system,
        )

    def capabilities(self) -> list[dict[str, Any]]:
        return [asdict(spec) for spec, _ in self._models.values()]

    def probe_default(self) -> dict[str, Any]:
        selected = self.settings.default_llm
        if selected == "offline":
            return {"ok": True, "provider": "offline", "note": "generation disabled by configuration"}
        row = self._models.get(selected)
        if row is None:
            return {"ok": False, "provider": "unknown", "error": {"code": "unknown_llm_model"}}
        return row[1].probe()


def _optional_int(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"} and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "".join(parts)
    raise IntegrationError("invalid_generation_shape", "Message content is not supported text.", 502)
