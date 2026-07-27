"""Authenticated generation adapters over the immutable signal instrument."""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Any

from humor_mesh import extract_json_object
from mesh_signals import OfflineStub

from .config import Settings
from .errors import IntegrationError
from .llm import OllamaLLM, OpenAICompatibleLLM


class OllamaSignalProvider:
    """Ollama generation/judging plus explicitly unmeasured heuristic NLL."""

    name = "ollama"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        model: str | None = None,
        host: str | None = None,
        api_key: str | None = None,
        client: Any = None,
    ) -> None:
        base = settings or Settings.from_env()
        self.model = model or os.environ.get("GEMMA_MODEL") or base.ollama_models[0]
        self.host = (host or base.ollama_host).rstrip("/")
        self.think = os.environ.get("GEMMA_THINK", "0").strip().lower() in {"1", "true", "yes", "on"}
        runtime = replace(
            base,
            ollama_host=self.host,
            ollama_api_key=base.ollama_api_key if api_key is None else api_key,
            ollama_models=(self.model,),
        )
        self.api_key_configured = bool(runtime.ollama_api_key)
        self.last_error = ""
        self._client = client or OllamaLLM(runtime)

    def nll_tokens(self, context: str, continuation: str):
        return OfflineStub().nll_tokens(context, continuation)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        try:
            self.last_error = ""
            return self._client.generate(
                f"ollama:{self.model}",
                self.model,
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=False,
                think=self.think,
            ).text
        except IntegrationError as exc:
            self.last_error = exc.code
            return ""

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return extract_json_object(self.generate(prompt, temperature=0.2, max_tokens=320))


class OpenAICompatibleSignalProvider:
    """OpenAI-compatible generation/judging plus unmeasured heuristic NLL."""

    name = "openai-compat"

    def __init__(self, settings: Settings | None = None, *, client: Any = None) -> None:
        base = settings or Settings.from_env()
        legacy_base = os.environ.get("GEMMA_OPENAI_BASE_URL", "").strip()
        legacy_model = os.environ.get("GEMMA_OPENAI_MODEL", "").strip()
        self.base = (legacy_base or base.openai_base_url).rstrip("/")
        self.model = legacy_model or (base.openai_models[0] if base.openai_models else "google/gemma-2-9b-it")
        key = base.openai_api_key
        for key_env in (
            os.environ.get("GEMMA_OPENAI_KEY_ENV", ""),
            "NVIDIA_API_KEY",
            "ADVISOR_LLM_API_KEY",
            "MISTRAL_API_KEY",
            "OPENAI_API_KEY",
        ):
            if not key and key_env and os.environ.get(key_env):
                key = os.environ[key_env]
        runtime = replace(
            base,
            openai_base_url=self.base,
            openai_api_key=key,
            openai_models=(self.model,),
        )
        self.key_configured = bool(key)
        self.last_error = ""
        self._client = client or OpenAICompatibleLLM(runtime)

    def nll_tokens(self, context: str, continuation: str):
        return OfflineStub().nll_tokens(context, continuation)

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        try:
            self.last_error = ""
            return self._client.generate(
                f"openai:{self.model}",
                self.model,
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=False,
                think=False,
            ).text
        except IntegrationError as exc:
            self.last_error = exc.code
            return ""

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return extract_json_object(self.generate(prompt, temperature=0.2, max_tokens=320))


def get_signal_provider(kind: str | None = None, settings: Settings | None = None):
    """Extend the pinned resolver without changing its published source hash."""

    selected = (kind or os.environ.get("GEMMA_PROVIDER", "")).strip().lower()
    if selected in {"ollama", "ollama-cloud"}:
        return OllamaSignalProvider(settings)
    if selected in {"openai", "openai-compat", "nvidia", "mistral"}:
        return OpenAICompatibleSignalProvider(settings)
    from mesh_signals import get_provider as pinned_get_provider

    return pinned_get_provider(kind)
