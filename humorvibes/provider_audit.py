"""Provider compatibility receipts with configured/reachable/executed/quality gates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .embeddings import EmbeddingRegistry
from .errors import IntegrationError
from .llm import LLMRegistry


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_error(exc: IntegrationError) -> dict[str, Any]:
    public = exc.public()
    return {
        "code": public["code"],
        "retryable": bool(public.get("retryable", False)),
        "upstream_status": (public.get("detail") or {}).get("upstream_status"),
    }


def _secret_scan(receipt: dict[str, Any], settings: Settings) -> dict[str, Any]:
    serialized = json.dumps(receipt, sort_keys=True, ensure_ascii=False)
    configured = [
        value
        for value in (settings.ollama_api_key, settings.openai_api_key, settings.api_key)
        if value
    ]
    return {
        "configured_secret_count": len(configured),
        "secrets_absent": all(value not in serialized for value in configured),
    }


def audit_providers(
    settings: Settings | None = None,
    *,
    live: bool = False,
    llms: LLMRegistry | None = None,
    embeddings: EmbeddingRegistry | None = None,
) -> dict[str, Any]:
    """Audit every exact allowlisted model without conflating availability and quality."""

    runtime = settings or Settings.from_env()
    llm_registry = llms or LLMRegistry(runtime)
    embedding_registry = embeddings or EmbeddingRegistry(runtime)
    llm_rows: list[dict[str, Any]] = []
    for capability in llm_registry.capabilities():
        model_id = str(capability["model_id"])
        row: dict[str, Any] = {
            **capability,
            "configured": True,
            "provider_reachable": None,
            "operation_executed": False,
            "quality_validated": False,
        }
        if live:
            probe = llm_registry.probe(model_id)
            row["provider_probe"] = probe
            row["provider_reachable"] = bool(probe.get("ok"))
            try:
                result = llm_registry.generate(
                    "Compatibility probe: reply with the single token OK.",
                    model_id=model_id,
                    temperature=0.0,
                    max_tokens=8,
                    think=False,
                )
                row.update(
                    {
                        "operation_executed": True,
                        "output_sha256": hashlib.sha256(result.text.encode("utf-8")).hexdigest(),
                        "output_tokens": result.output_tokens,
                        "finish_reason": result.finish_reason,
                    }
                )
            except IntegrationError as exc:
                row["operation_error"] = _safe_error(exc)
        llm_rows.append(row)

    embedding_rows: list[dict[str, Any]] = []
    for capability in embedding_registry.capabilities():
        model_id = str(capability["model_id"])
        row = {
            **capability,
            "configured": True,
            "provider_reachable": None,
            "operation_executed": False,
            "quality_validated": False,
        }
        should_execute = live or capability.get("provider") == "hash"
        if should_execute:
            probe = embedding_registry.probe(model_id)
            row["provider_probe"] = probe
            row["provider_reachable"] = bool(probe.get("ok"))
            if probe.get("ok"):
                row["operation_executed"] = True
                row["observed_dimensions"] = probe.get("dimensions")
            elif isinstance(probe.get("error"), dict):
                error = probe["error"]
                row["operation_error"] = {
                    "code": error.get("code"),
                    "retryable": bool(error.get("retryable", False)),
                    "upstream_status": (error.get("detail") or {}).get("upstream_status"),
                }
        embedding_rows.append(row)

    executed = sum(row["operation_executed"] for row in [*llm_rows, *embedding_rows])
    configured = len(llm_rows) + len(embedding_rows)
    receipt: dict[str, Any] = {
        "receipt_type": "humorvibes_provider_compatibility_audit",
        "receipt_version": 1,
        "generated_at": _utc_now(),
        "mode": {
            "live": live,
            "generation_probe_max_tokens": 8 if live else 0,
            "quality_benchmark_executed": False,
        },
        "configuration": runtime.public_summary(),
        "llm_models": llm_rows,
        "embedding_models": embedding_rows,
        "summary": {
            "models_configured": configured,
            "operations_executed": executed,
            "operations_failed_or_not_probed": configured - executed,
            "quality_validated_models": 0,
        },
        "truth_boundary": {
            "configured_is_reachable": False,
            "reachable_is_operation_compatible": False,
            "operation_compatible_is_quality_validated": False,
            "provider_quality_or_human_funniness_established": False,
        },
    }
    receipt["secret_scan"] = _secret_scan(receipt, runtime)
    receipt["ok"] = receipt["secret_scan"]["secrets_absent"] and (
        not live or executed > 0
    )
    return receipt


def write_provider_audit(path: Path, receipt: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
