"""Typed, dependency-free client for the HumorVibes HTTP API."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

from .http import JsonHttpClient


class HumorVibesClient:
    """Call one configured HumorVibes service without accepting per-request hosts.

    The client uses the same bounded, no-redirect JSON transport as the provider
    integrations. API keys are sent only as Bearer headers and never appear in
    ``repr(client)``.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        *,
        api_key: str = "",
        timeout: float = 30.0,
        max_response_bytes: int = 10_000_000,
        allow_insecure_remote: bool = False,
        transport: Any = None,
    ) -> None:
        self._transport = transport or JsonHttpClient(
            base_url,
            api_key=api_key,
            timeout=timeout,
            max_response_bytes=max_response_bytes,
            allow_insecure_remote=allow_insecure_remote,
        )
        self.base_url = getattr(self._transport, "base_url", base_url.rstrip("/"))
        self.auth_configured = bool(api_key)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> HumorVibesClient:
        env = dict(os.environ if environ is None else environ)
        return cls(
            env.get("HUMORVIBES_URL", "http://127.0.0.1:8080"),
            api_key=env.get("HUMORVIBES_API_KEY", ""),
        )

    def __repr__(self) -> str:
        return (
            f"HumorVibesClient(base_url={self.base_url!r}, "
            f"auth_configured={self.auth_configured})"
        )

    def live(self) -> dict[str, Any]:
        return self._transport.request("/health/live")

    def ready(self) -> dict[str, Any]:
        return self._transport.request("/health/ready")

    def version(self) -> dict[str, Any]:
        return self._transport.request("/version")

    def capabilities(self) -> dict[str, Any]:
        return self._transport.request("/v1/capabilities")

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        model_id: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 512,
        json_mode: bool = False,
        think: bool = False,
    ) -> dict[str, Any]:
        return self._transport.request(
            "/v1/generate",
            payload={
                "prompt": prompt,
                "system": system,
                "model_id": model_id,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "json_mode": json_mode,
                "think": think,
            },
        )

    def generate_humor(
        self,
        topic: str,
        *,
        format: str = "one_liner",
        audience: str = "",
        preferences: str = "",
        count: int = 4,
        model_id: str | None = None,
        temperature: float = 0.8,
        think: bool = False,
    ) -> dict[str, Any]:
        return self._transport.request(
            "/v1/humor/generate",
            payload={
                "topic": topic,
                "format": format,
                "audience": audience,
                "preferences": preferences,
                "count": count,
                "model_id": model_id,
                "temperature": temperature,
                "think": think,
            },
        )

    def judge(
        self,
        prompt: str,
        *,
        model_id: str | None = None,
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        return self._transport.request(
            "/v1/judge",
            payload={
                "prompt": prompt,
                "model_id": model_id,
                "max_tokens": max_tokens,
            },
        )

    def embed(
        self,
        texts: Sequence[str],
        *,
        model_id: str | None = None,
        dimensions: int | None = None,
    ) -> dict[str, Any]:
        return self._transport.request(
            "/v1/embed",
            payload={
                "texts": list(texts),
                "model_id": model_id,
                "dimensions": dimensions,
            },
        )

    def similarity(
        self,
        left: Sequence[str],
        right: Sequence[str],
        *,
        model_id: str | None = None,
        dimensions: int | None = None,
    ) -> dict[str, Any]:
        return self._transport.request(
            "/v1/similarity",
            payload={
                "left": list(left),
                "right": list(right),
                "model_id": model_id,
                "dimensions": dimensions,
            },
        )

    def signals(
        self,
        setup: str,
        punchline: str,
        *,
        frame_hint: str = "",
        personas: Sequence[str] = (),
    ) -> dict[str, Any]:
        return self._transport.request(
            "/v1/signals",
            payload={
                "setup": setup,
                "punchline": punchline,
                "frame_hint": frame_hint,
                "personas": list(personas),
            },
        )
