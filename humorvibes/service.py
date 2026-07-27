"""Application-facing SDK over integrations and the existing research core."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from formats import FORMATS, format_generation_prompt, list_formats
from humor_mesh import extract_candidates, extract_json_object

from . import __version__
from .config import Settings
from .embeddings import EmbeddingRegistry, cosine_similarity
from .errors import IntegrationError
from .llm import LLMRegistry


class HumorVibesService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llms: LLMRegistry | None = None,
        embeddings: EmbeddingRegistry | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.llms = llms or LLMRegistry(self.settings)
        self.embeddings = embeddings or EmbeddingRegistry(self.settings)
        self._signal_provider: Any = None

    def capabilities(self) -> dict[str, Any]:
        return {
            "version": __version__,
            "settings": self.settings.public_summary(),
            "llm_models": self.llms.capabilities(),
            "embedding_models": self.embeddings.capabilities(),
            "humor_formats": list_formats(),
            "truth_boundary": {
                "generation_is_not_human_validation": True,
                "embedding_similarity_is_not_proof_of_novelty": True,
                "offline_signals_are_not_measured": True,
                "canonical_kaggle_measurement_is_immutable": True,
            },
        }

    def generate(
        self,
        prompt: str,
        *,
        model_id: str | None = None,
        system: str = "",
        temperature: float = 0.8,
        max_tokens: int = 512,
        json_mode: bool = False,
        think: bool = False,
    ) -> dict[str, Any]:
        result = self.llms.generate(
            prompt,
            model_id=model_id,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            think=think,
        )
        payload = result.public()
        payload["text"] = result.text
        payload["truth_boundary"] = {
            "generation_executed": True,
            "teacher_forced_logprobs_measured": False,
            "model_output_is_not_human_laughter": True,
        }
        return payload

    def generate_humor(
        self,
        topic: str,
        *,
        format_key: str = "one_liner",
        audience: str = "",
        preferences: str = "",
        count: int = 4,
        model_id: str | None = None,
        temperature: float = 0.8,
        think: bool = False,
    ) -> dict[str, Any]:
        if format_key not in FORMATS:
            raise IntegrationError(
                "unknown_humor_format",
                "Requested humor format is not supported.",
                400,
                detail={"format": format_key},
            )
        if not topic.strip():
            raise IntegrationError("empty_topic", "Topic must not be empty.", 422)
        if not 1 <= count <= 12:
            raise IntegrationError("invalid_candidate_count", "Candidate count must be between 1 and 12.", 422)
        prompt = format_generation_prompt(
            FORMATS[format_key],
            topic.strip(),
            audience.strip(),
            preferences.strip(),
            count=count,
        )
        result = self.llms.generate(
            prompt,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max(420, min(2048, count * 180)),
            think=think,
        )
        candidates = extract_candidates(result.text, limit=count)
        return {
            **result.public(),
            "format": format_key,
            "requested_candidates": count,
            "parsed_candidates": candidates,
            "candidate_count": len(candidates),
            "candidate_count_matches": len(candidates) == count,
            "truth_boundary": {
                "generation_executed": True,
                "teacher_forced_logprobs_measured": False,
                "model_output_is_not_human_laughter": True,
            },
        }

    def judge_json(
        self,
        prompt: str,
        *,
        model_id: str | None = None,
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        result = self.llms.generate(
            prompt,
            model_id=model_id,
            temperature=0.2,
            max_tokens=max_tokens,
            json_mode=True,
            think=False,
        )
        parsed = extract_json_object(result.text)
        if parsed is None:
            raise IntegrationError("unparseable_model_json", "Model did not return a JSON object.", 502)
        return {
            **result.public(),
            "result": parsed,
            "truth_boundary": {"model_judgment_is_not_human_judgment": True},
        }

    def embed(
        self,
        texts: list[str],
        *,
        model_id: str | None = None,
        dimensions: int | None = None,
    ) -> dict[str, Any]:
        result = self.embeddings.embed(texts, model_id=model_id, dimensions=dimensions)
        return result.public(include_vectors=True)

    def similarity(
        self,
        left: list[str],
        right: list[str],
        *,
        model_id: str | None = None,
        dimensions: int | None = None,
    ) -> dict[str, Any]:
        if len(left) > 32 or len(right) > 32:
            raise IntegrationError("similarity_matrix_too_large", "Similarity sides are limited to 32 texts each.", 413)
        joined = left + right
        result = self.embeddings.embed(joined, model_id=model_id, dimensions=dimensions)
        split = len(left)
        left_vectors = result.vectors[:split]
        right_vectors = result.vectors[split:]
        matrix = [
            [round(cosine_similarity(a, b), 6) for b in right_vectors]
            for a in left_vectors
        ]
        return {
            "model_id": result.model_id,
            "provider": result.provider,
            "dimensions": result.dimensions,
            "left_count": len(left),
            "right_count": len(right),
            "cosine_similarity": matrix,
            "truth_boundary": {"similarity_is_not_proof_of_novelty_or_equivalence": True},
        }

    def signals(
        self,
        setup: str,
        punchline: str,
        *,
        frame_hint: str = "",
        personas: list[str] | None = None,
    ) -> dict[str, Any]:
        if not setup.strip() or not punchline.strip():
            raise IntegrationError("invalid_joke_parts", "Setup and punchline must both be non-empty.", 422)
        if len(setup) + len(punchline) + len(frame_hint) > self.settings.max_prompt_chars:
            raise IntegrationError("prompt_too_large", "Signal input exceeds the configured character limit.", 413)
        if self._signal_provider is None:
            from .signal_providers import get_signal_provider

            self._signal_provider = get_signal_provider(self.settings.signal_provider, self.settings)
        from mesh_signals import compute_signals

        result = compute_signals(
            self._signal_provider,
            setup,
            punchline,
            frame_hint=frame_hint or None,
            personas=personas or [],
        )
        payload = result.to_dict()
        payload["provider"] = self._signal_provider.name
        payload["truth_boundary"] = {
            "teacher_forced_logprobs_measured": bool(result.measured),
            "surprisal_is_not_funniness": True,
            "model_judgment_is_not_human_laughter": True,
        }
        return payload

    def ready(self, *, live: bool | None = None) -> dict[str, Any]:
        should_probe = self.settings.strict_readiness if live is None else live
        checks: dict[str, Any] = {
            "process": {"ok": True},
            "configuration": {
                "ok": self.settings.default_llm == "offline" or any(
                    row["model_id"] == self.settings.default_llm for row in self.llms.capabilities()
                ),
            },
        }
        checks["embedding_configuration"] = {
            "ok": any(row["model_id"] == self.settings.default_embedding for row in self.embeddings.capabilities())
        }
        if should_probe:
            checks["llm"] = self.llms.probe_default()
            checks["embedding"] = self.embeddings.probe()
        ok = all(bool(value.get("ok")) for value in checks.values())
        return {"ok": ok, "checks": checks, "live_probe": should_probe}

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def compact_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
