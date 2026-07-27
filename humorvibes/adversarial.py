"""Deterministic, network-free security and integration contract audit."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from .config import Settings
from .embeddings import (
    EmbeddingRegistry,
    HashEmbeddingBackend,
    cosine_similarity,
    validate_vectors,
)
from .errors import IntegrationError
from .http import JsonHttpClient, normalize_base_url
from .llm import LLMRegistry
from .studies import analyze_study, default_study_protocol, synthetic_study_bundle, validate_study_bundle


@dataclass(frozen=True)
class AuditCheck:
    name: str
    passed: bool
    evidence: str


def _expect_error(name: str, code: str, action: Callable[[], Any]) -> AuditCheck:
    try:
        action()
    except IntegrationError as exc:
        return AuditCheck(name, exc.code == code, f"observed={exc.code}; expected={code}")
    except Exception as exc:  # pragma: no cover - defensive receipt path
        return AuditCheck(name, False, f"unexpected={type(exc).__name__}")
    return AuditCheck(name, False, "no error raised")


def run_adversarial_suite() -> dict[str, Any]:
    """Exercise fail-closed boundaries without network access or model downloads."""

    secret = "audit-secret-never-publish"
    runtime = Settings.from_env({"OLLAMA_API_KEY": secret, "GEMMA_MODEL": "gemma4"})
    public_settings = json.dumps(runtime.public_summary(), sort_keys=True)
    checks = [
        AuditCheck(
            "secrets_absent_from_public_settings",
            secret not in public_settings,
            "public summary exposes only configured=true/false",
        ),
        AuditCheck(
            "ollama_key_selects_tls_cloud_endpoint",
            runtime.ollama_host == "https://ollama.com",
            f"host={runtime.ollama_host}",
        ),
        AuditCheck(
            "ollama_key_is_not_reused_as_openai_credential",
            not runtime.openai_api_key,
            "provider credentials remain separately scoped",
        ),
        _expect_error(
            "base_url_rejects_embedded_credentials",
            "invalid_base_url",
            lambda: normalize_base_url("https://user:pass@example.com"),
        ),
        _expect_error(
            "base_url_rejects_public_plain_http",
            "insecure_remote_url",
            lambda: normalize_base_url("http://public.example.com"),
        ),
        _expect_error(
            "base_url_rejects_path_traversal",
            "invalid_base_url",
            lambda: normalize_base_url("https://example.com/v1/../private"),
        ),
        _expect_error(
            "endpoint_rejects_query_injection",
            "invalid_endpoint",
            lambda: JsonHttpClient("https://example.com").request("/models?target=internal"),
        ),
        _expect_error(
            "embedding_count_mismatch_fails_closed",
            "embedding_count_mismatch",
            lambda: validate_vectors([[1.0, 0.0]], 2),
        ),
        _expect_error(
            "embedding_dimension_drift_fails_closed",
            "embedding_dimension_mismatch",
            lambda: validate_vectors([[1.0, 0.0], [1.0]], 2),
        ),
        _expect_error(
            "embedding_nan_fails_closed",
            "nonfinite_embedding_value",
            lambda: validate_vectors([[1.0, math.nan]], 1),
        ),
        _expect_error(
            "embedding_boolean_fails_closed",
            "invalid_embedding_value",
            lambda: validate_vectors([[True, 0.0]], 1),
        ),
        _expect_error(
            "embedding_zero_vector_fails_closed",
            "zero_embedding_vector",
            lambda: validate_vectors([[0.0, 0.0]], 1),
        ),
        _expect_error(
            "cosine_dimension_mismatch_fails_closed",
            "embedding_dimension_mismatch",
            lambda: cosine_similarity([1.0], [1.0, 0.0]),
        ),
        _expect_error(
            "llm_model_allowlist_fails_closed",
            "unknown_llm_model",
            lambda: LLMRegistry(Settings.from_env({})).generate("hello", model_id="ollama:unlisted"),
        ),
        _expect_error(
            "embedding_model_allowlist_fails_closed",
            "unknown_embedding_model",
            lambda: EmbeddingRegistry(Settings.from_env({})).embed(["hello"], model_id="ollama:unlisted"),
        ),
    ]

    hash_backend = HashEmbeddingBackend(128)
    first = hash_backend.embed(["一箭双雕", "same text"])
    second = hash_backend.embed(["一箭双雕", "same text"])
    checks.append(AuditCheck(
        "offline_hash_embedding_is_deterministic_and_unicode_aware",
        first.vectors == second.vectors and first.dimensions == 128,
        "two repeated multilingual batches matched exactly",
    ))

    protocol = default_study_protocol()
    synthetic_receipt = analyze_study(protocol, synthetic_study_bundle(protocol))
    checks.append(AuditCheck(
        "synthetic_positive_effect_cannot_authorize_human_claim",
        synthetic_receipt["estimate"] > 0.25
        and synthetic_receipt["claim_gate"]["claim_ready"] is False,
        "positive synthetic fixture remained L1_OFFLINE_CONTRACT",
    ))

    raw_text_bundle = synthetic_study_bundle(protocol)
    raw_text_bundle["materials"][0]["raw_text"] = "must-not-enter-analysis"
    checks.append(_expect_error(
        "study_export_rejects_raw_material",
        "forbidden_study_field",
        lambda: validate_study_bundle(protocol, raw_text_bundle),
    ))

    duplicate_bundle = synthetic_study_bundle(protocol)
    duplicate_bundle["audience_responses"][1]["response_id"] = duplicate_bundle["audience_responses"][0]["response_id"]
    checks.append(_expect_error(
        "study_export_rejects_duplicate_responses",
        "duplicate_response_id",
        lambda: validate_study_bundle(protocol, duplicate_bundle),
    ))

    nonfinite_bundle = synthetic_study_bundle(protocol)
    nonfinite_bundle["audience_responses"][0]["rating"] = math.nan
    checks.append(_expect_error(
        "study_export_rejects_nonfinite_ratings",
        "invalid_study_value",
        lambda: validate_study_bundle(protocol, nonfinite_bundle),
    ))

    incomplete_bundle = synthetic_study_bundle(protocol)
    removed_material = incomplete_bundle["materials"].pop(0)["material_id"]
    incomplete_bundle["audience_responses"] = [
        row for row in incomplete_bundle["audience_responses"] if row["material_id"] != removed_material
    ]
    checks.append(_expect_error(
        "study_export_rejects_incomplete_paired_blocks",
        "incomplete_paired_block",
        lambda: validate_study_bundle(protocol, incomplete_bundle),
    ))

    passed = sum(check.passed for check in checks)
    return {
        "receipt_type": "humorvibes_adversarial_integration_audit",
        "receipt_version": 1,
        "network_calls": 0,
        "model_downloads": 0,
        "passed": passed,
        "total": len(checks),
        "ok": passed == len(checks),
        "checks": [asdict(check) for check in checks],
        "scope": {
            "covered": [
                "secret exposure",
                "URL and endpoint validation",
                "model allowlists",
                "embedding response corruption",
                "cosine preconditions",
                "deterministic offline embeddings",
                "synthetic-evidence claim gates",
                "study schema, privacy, finiteness, uniqueness, and paired-design validation",
            ],
            "not_covered": [
                "live provider availability",
                "model quality",
                "human funniness",
                "human-study recruitment, consent operations, and external replication",
                "cluster-level denial-of-service",
            ],
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_adversarial_suite(), indent=2, ensure_ascii=False, sort_keys=True))
