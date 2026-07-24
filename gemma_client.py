"""Minimal Gemma client helpers.

Default provider is Ollama because it is simple to run locally:
  GEMMA_PROVIDER=ollama GEMMA_MODEL=gemma3:4b streamlit run app.py
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_prompt(name: str) -> str:
    return (ROOT / "prompts" / name).read_text(encoding="utf-8")


class GemmaClient:
    def __init__(self) -> None:
        self.provider = os.environ.get("GEMMA_PROVIDER", "offline").strip().lower()
        self.model = os.environ.get("GEMMA_MODEL", "gemma3:4b")
        self.ollama_host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self.think = os.environ.get("GEMMA_THINK", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }
        self._tf = None
        if self.provider == "transformers":
            try:
                from mesh_signals import TransformersProvider

                self._tf = TransformersProvider()
            except Exception:
                self._tf = None
                self.provider = "offline"

    def available(self) -> bool:
        return self.provider == "ollama" or self._tf is not None

    def generate(self, prompt: str, *, temperature: float = 0.7) -> str | None:
        if self._tf is not None:
            out = self._tf.generate(prompt, temperature=temperature, max_tokens=420)
            return out or None
        if self.provider != "ollama":
            return None
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self.think,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": 720},
        }
        req = urllib.request.Request(
            f"{self.ollama_host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None
        return str(data.get("response", "")).strip()
