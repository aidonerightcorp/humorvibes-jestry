"""Determinism, rights, balance, and truth-boundary tests for cross-language retrieval."""

from __future__ import annotations

import copy

import pytest

from humorvibes.crosslingual_retrieval import (
    LANGUAGES,
    SOURCE_NAME,
    build_crosslingual_retrieval,
)
from humorvibes.errors import IntegrationError
from humorvibes.retrieval_benchmark import evaluate_retrieval


def _rows(per_language: int = 24) -> list[dict[str, str]]:
    return [
        {
            "language": language,
            "licence_class": "redistributable",
            "license": "Public domain (Project Gutenberg)",
            "source": SOURCE_NAME,
            "text": f"{language} historical proverb number {index}",
            "translation_en": f"English rendering for {language} proverb number {index}",
        }
        for language in LANGUAGES
        for index in range(per_language)
    ]


def test_balanced_crosslingual_fixture_is_deterministic_and_language_sliced() -> None:
    first = build_crosslingual_retrieval(
        _rows(), source_snapshot_sha256="a" * 64, pairs_per_language=20
    )
    second = build_crosslingual_retrieval(
        reversed(_rows()), source_snapshot_sha256="a" * 64, pairs_per_language=20
    )
    assert first == second
    assert first["manifest"]["counts"]["by_source_language"] == {
        language: 20 for language in LANGUAGES
    }
    assert first["manifest"]["truth_boundary"]["modern_native_review"] is False
    receipt = evaluate_retrieval(first, model_id="hash:128", record_duration=False)
    assert set(receipt["metrics_by_language"]) == set(LANGUAGES)
    assert "nDCG@10" in receipt["overall"]
    assert set(receipt["overall"]["bootstrap_95pct_ci"]) == {
        "MRR",
        "Recall@1",
        "Recall@5",
        "Recall@10",
        "nDCG@10",
    }
    assert receipt["failure_slices"]["rank_above_10"]["queries"] >= 0


def test_missing_language_and_rights_drift_fail_closed() -> None:
    missing = [row for row in _rows() if row["language"] != LANGUAGES[-1]]
    with pytest.raises(IntegrationError) as insufficient:
        build_crosslingual_retrieval(
            missing, source_snapshot_sha256="b" * 64, pairs_per_language=20
        )
    assert insufficient.value.code == "insufficient_crosslingual_pairs"

    drift = copy.deepcopy(_rows())
    drift[0]["licence_class"] = "research_only"
    with pytest.raises(IntegrationError) as rights:
        build_crosslingual_retrieval(
            drift, source_snapshot_sha256="b" * 64, pairs_per_language=20
        )
    assert rights.value.code == "invalid_crosslingual_rights"
