"""Hard retrieval construction, leakage, and provider-neutral evaluation."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from humorvibes.errors import IntegrationError
from humorvibes.open_controls import iter_rows, retrieval_rows
from humorvibes.retrieval_benchmark import (
    build_hard_retrieval_rows,
    evaluate_retrieval,
    load_retrieval_dataset,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def hard_dataset() -> dict:
    rows = list(iter_rows(families=60, configs=1, variants=2))
    documents, queries, qrels = retrieval_rows(rows)
    return build_hard_retrieval_rows(documents, queries, qrels)


def test_hard_queries_are_deterministic_masked_and_family_disjoint(
    hard_dataset: dict,
) -> None:
    manifest = hard_dataset["manifest"]
    assert manifest["counts"] == {
        "documents": 60,
        "queries": 60,
        "qrels": 60,
        "hard_negative_rows": 60,
    }
    assert manifest["leakage_audit"]["entity_or_pivot_leaks"] == 0
    assert manifest["leakage_audit"]["template_family_crosses_splits"] is False
    assert (
        manifest["leakage_audit"]["maximum_content_token_jaccard_to_relevant_document"]
        < 0.35
    )
    assert {row["query_contract"] for row in hard_dataset["queries"]} == {
        "masked_entity_and_pivots_semantic_frame_v1"
    }


def test_hard_negatives_stay_in_pool_and_differ_from_qrel(
    hard_dataset: dict,
) -> None:
    relevant = {row["query_id"]: row["document_id"] for row in hard_dataset["qrels"]}
    documents = {row["document_id"]: row for row in hard_dataset["documents"]}
    queries = {row["query_id"]: row for row in hard_dataset["queries"]}
    for row in hard_dataset["hard_negatives"]:
        query = queries[row["query_id"]]
        family = documents[row["same_frame_different_context_document_id"]]
        context = documents[row["same_context_different_frame_document_id"]]
        assert family["document_id"] != relevant[row["query_id"]]
        assert context["document_id"] != relevant[row["query_id"]]
        assert family["split"] == context["split"] == query["split"]
        assert family["template_family_id"] == query["template_family_id"]
        assert context["situation_key"] == query["situation_key"]


@pytest.mark.parametrize("model_id", ["lexical:tfidf", "hash:128"])
def test_evaluator_runs_two_distinct_offline_models(
    hard_dataset: dict, model_id: str
) -> None:
    receipt = evaluate_retrieval(hard_dataset, model_id=model_id)
    assert receipt["model"]["model_id"] == model_id
    assert receipt["overall"]["queries"] == 60
    assert 0.0 <= receipt["overall"]["MRR"] <= 1.0
    assert set(receipt["metrics_by_split"]) == {"train", "validation", "test"}
    assert receipt["overall"]["nDCG@10"] >= 0.0
    assert set(receipt["overall"]["bootstrap_95pct_ci"]) == {
        "MRR", "Recall@1", "Recall@5", "Recall@10", "nDCG@10"
    }
    assert receipt["failure_slices"]["not_ranked_first"]["rate"] >= 0.0
    assert receipt["frozen_input_digests"]["queries"]
    assert receipt["truth_boundary"]["qrels_are_human_judgments"] is False


def test_invalid_qrel_fails_closed(hard_dataset: dict) -> None:
    broken = copy.deepcopy(hard_dataset)
    broken["qrels"][0]["document_id"] = "unknown-document"
    with pytest.raises(IntegrationError) as observed:
        evaluate_retrieval(broken)
    assert observed.value.code == "invalid_retrieval_qrel"


def test_clock_free_embedding_receipt_is_byte_recomputable(hard_dataset: dict) -> None:
    first = evaluate_retrieval(
        hard_dataset, model_id="hash:128", record_duration=False
    )
    second = evaluate_retrieval(
        hard_dataset, model_id="hash:128", record_duration=False
    )
    assert first == second
    assert "duration_seconds" not in first
    assert "performance" not in first["model"]


def test_cli_build_and_benchmark_execute_end_to_end(tmp_path: Path) -> None:
    rows = list(iter_rows(families=60, configs=1, variants=2))
    documents, queries, qrels = retrieval_rows(rows)
    source = tmp_path / "source"
    source.mkdir()
    for name, values in (
        ("retrieval_documents.jsonl", documents),
        ("retrieval_queries.jsonl", queries),
        ("retrieval_qrels.jsonl", qrels),
    ):
        (source / name).write_text(
            "".join(json.dumps(row) + "\n" for row in values), encoding="utf-8"
        )
    target = tmp_path / "hard"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "humorvibes.cli",
            "retrieval-hard-build",
            "--release-root",
            str(source),
            "--out-dir",
            str(target),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    receipt_path = tmp_path / "receipt.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "humorvibes.cli",
            "retrieval-benchmark",
            "--root",
            str(target),
            "--model",
            "hash:128",
            "--out",
            str(receipt_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == json.loads(receipt_path.read_text())
    assert load_retrieval_dataset(target)["manifest"]["counts"]["queries"] == 60
