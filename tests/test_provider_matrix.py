"""No-network provider-matrix execution and fail-closed spec tests."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from humorvibes.embeddings import EmbeddingResult
from humorvibes.errors import IntegrationError
from humorvibes.open_controls import iter_rows, retrieval_rows
from humorvibes.provider_matrix import run_provider_matrix, validate_provider_matrix_spec
from humorvibes.retrieval_benchmark import build_hard_retrieval_rows, write_retrieval_dataset


class FakeSemanticRegistry:
    def __init__(self, settings) -> None:
        self.settings = settings

    def probe(self, model_id: str):
        return {"ok": True, "provider": "fake-semantic", "model_id": model_id, "dimensions": 3}

    def embed(self, texts: list[str], *, model_id: str):
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [1.0 + digest[index] / 255.0 for index in range(3)]
            norm = math.sqrt(sum(value * value for value in vector))
            vectors.append([value / norm for value in vector])
        return EmbeddingResult(
            model_id=model_id,
            provider="fake-semantic",
            remote_model="fixture-model",
            vectors=vectors,
            dimensions=3,
            normalized=True,
        )


def _spec(expected_digest: str) -> dict:
    base = {
        "backend": "ollama",
        "base_url": "http://127.0.0.1:11434",
        "api_key_env": "MATRIX_TEST_KEY",
        "remote_model": "fixture-model",
        "model_digest": "a" * 64,
        "model_license": "Apache-2.0",
        "server_implementation": "no-network-fixture",
        "server_version": "1.2.3",
        "server_artifact": "fixture:no-network",
        "request_schema": "ollama:/api/embed:v1",
        "hardware_class": "test-cpu",
        "timeout_seconds": 10,
        "batch_size": 16,
    }
    return {
        "receipt_type": "humorvibes_provider_matrix_spec",
        "spec_version": 1,
        "hardware_class": "test-cpu",
        "benchmarks": [
            {
                "benchmark_id": "hard-fixture",
                "root": "hard",
                "expected_digest": expected_digest,
            }
        ],
        "runs": [
            {**base, "run_id": "fake-success", "expected_dimensions": 3},
            {**base, "run_id": "fake-dimension-failure", "expected_dimensions": 4},
        ],
    }


def test_no_network_matrix_preserves_success_failure_and_secret_boundary(tmp_path: Path) -> None:
    rows = list(iter_rows(families=60, configs=1, variants=2))
    docs, queries, qrels = retrieval_rows(rows)
    dataset = build_hard_retrieval_rows(docs, queries, qrels)
    write_retrieval_dataset(tmp_path / "hard", dataset)
    spec = _spec(dataset["manifest"]["content_digest"])
    receipt = run_provider_matrix(
        spec,
        spec_dir=tmp_path,
        environment={"MATRIX_TEST_KEY": "must-never-be-serialized"},
        registry_factory=lambda _run, settings: FakeSemanticRegistry(settings),
        readiness_probe=lambda _run, _settings: {
            "checked": True,
            "reachable": True,
            "method": "no-network-fixture",
        },
    )
    assert receipt["ok"] is True
    assert receipt["summary"]["quality_validated_runs"] == 1
    assert receipt["summary"]["quality_failed_or_incomplete_runs"] == 1
    success, failure = receipt["runs"]
    assert success["quality_benchmarks"]["hard-fixture"]["overall"]["nDCG@10"] >= 0
    assert failure["failure"]["stage"] == "dimension_gate"
    assert receipt["secret_scan"] == {"configured_secret_count": 2, "secrets_absent": True}
    assert "must-never-be-serialized" not in str(receipt)


def test_spec_rejects_embedded_secrets_and_escaping_benchmark_paths() -> None:
    spec = _spec("b" * 64)
    spec["runs"][0]["api_key"] = "forbidden"
    with pytest.raises(IntegrationError) as secret:
        validate_provider_matrix_spec(spec)
    assert secret.value.code == "provider_matrix_secret_in_spec"

    spec = _spec("b" * 64)
    spec["benchmarks"][0]["root"] = "../outside"
    with pytest.raises(IntegrationError) as path:
        validate_provider_matrix_spec(spec)
    assert path.value.code == "invalid_provider_matrix_spec"
