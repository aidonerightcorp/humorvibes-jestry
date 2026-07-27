#!/usr/bin/env python3
"""Fail-closed semantic verification for a downloaded Open Controls release.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from humorvibes.open_controls import (
    COUNTERFACTUAL_ARMS,
    DATASET_ID,
    AuditAccumulator,
    read_jsonl_rows,
    validate_manifest,
)
from humorvibes.retrieval_benchmark import (
    build_hard_retrieval_rows,
    evaluate_retrieval,
    load_retrieval_dataset,
)


def verify(root: Path) -> dict[str, Any]:
    required = {
        "open_controls.jsonl",
        "open-controls-row.schema.json",
        "human-rating.schema.json",
        "human-contribution.schema.json",
        "model-candidate.schema.json",
        "retrieval_documents.jsonl",
        "retrieval_queries.jsonl",
        "retrieval_qrels.jsonl",
        "audit.json",
        "reference_overlap.json",
        "release_summary.json",
        "provenance.json",
        "LICENSE-DATA.txt",
        "DATASET_CARD.md",
        "README.md",
        "manifest.json",
        "release-metadata.json",
    }
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        return {"ok": False, "error": "missing_required_files", "missing": missing}
    summary = json.loads((root / "release_summary.json").read_text(encoding="utf-8"))
    hard_enabled = summary.get("hard_retrieval", {}).get("enabled") is True
    hard_required = {
        "hard_retrieval_documents.jsonl",
        "hard_retrieval_queries.jsonl",
        "hard_retrieval_qrels.jsonl",
        "hard_retrieval_negatives.jsonl",
        "hard_retrieval_manifest.json",
        "hard_retrieval_tfidf_baseline.json",
        "hard_retrieval_hash_128_baseline.json",
    }
    missing_hard = sorted(name for name in hard_required if not (root / name).is_file())
    if hard_enabled and missing_hard:
        return {"ok": False, "error": "missing_hard_retrieval_files", "missing": missing_hard}
    if not hard_enabled and len(summary.get("hard_retrieval", {})) < 2:
        return {"ok": False, "error": "missing_hard_retrieval_status"}
    manifest = validate_manifest(root)
    if not manifest["ok"]:
        return {"ok": False, "error": "manifest_failed", "manifest": manifest}

    published_audit = json.loads((root / "audit.json").read_text(encoding="utf-8"))
    reference = json.loads((root / "reference_overlap.json").read_text(encoding="utf-8"))
    metadata = json.loads((root / "release-metadata.json").read_text(encoding="utf-8"))
    provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))

    accumulator = AuditAccumulator()
    for row in read_jsonl_rows(root / "open_controls.jsonl"):
        accumulator.add(row)
    recomputed = accumulator.report()

    documents = list(read_jsonl_rows(root / "retrieval_documents.jsonl"))
    queries = list(read_jsonl_rows(root / "retrieval_queries.jsonl"))
    qrels = list(read_jsonl_rows(root / "retrieval_qrels.jsonl"))
    document_ids = {row.get("document_id") for row in documents}
    query_ids = {row.get("query_id") for row in queries}
    retrieval_ok = (
        len(documents) == len(queries) == len(qrels) == summary.get("families")
        and len(document_ids) == len(documents)
        and len(query_ids) == len(queries)
        and all(row.get("document_id") in document_ids and row.get("query_id") in query_ids for row in qrels)
    )
    hard_summary = summary.get("hard_retrieval", {})
    hard_contract_ok = True
    hard_baselines_ok = True
    hard_summary_ok = hard_summary.get("enabled") is False and bool(hard_summary.get("reason"))
    hard_receipt: dict[str, Any] = {"enabled": False, "reason": hard_summary.get("reason")}
    if hard_enabled:
        hard_retrieval = load_retrieval_dataset(root)
        recomputed_hard = build_hard_retrieval_rows(documents, queries, qrels)
        hard_contract_ok = hard_retrieval == recomputed_hard
        published_hard_tfidf = json.loads(
            (root / "hard_retrieval_tfidf_baseline.json").read_text(encoding="utf-8")
        )
        published_hard_hash = json.loads(
            (root / "hard_retrieval_hash_128_baseline.json").read_text(encoding="utf-8")
        )
        recomputed_hard_tfidf = evaluate_retrieval(
            hard_retrieval, model_id="lexical:tfidf", record_duration=False
        )
        recomputed_hard_hash = evaluate_retrieval(
            hard_retrieval, model_id="hash:128", record_duration=False
        )
        hard_baselines_ok = (
            published_hard_tfidf == recomputed_hard_tfidf
            and published_hard_hash == recomputed_hard_hash
        )
        hard_summary_ok = (
            hard_summary.get("content_digest")
            == hard_retrieval["manifest"].get("content_digest")
            and hard_summary.get("queries") == len(hard_retrieval["queries"])
            and hard_summary.get("entity_or_pivot_leaks") == 0
            and hard_summary.get("tfidf_overall_mrr")
            == published_hard_tfidf["overall"]["MRR"]
            and hard_summary.get("hash_128_overall_mrr")
            == published_hard_hash["overall"]["MRR"]
        )
        hard_receipt = {
            "enabled": True,
            "benchmark_digest": hard_retrieval["manifest"]["content_digest"],
            "maximum_content_token_jaccard": hard_retrieval["manifest"]["leakage_audit"][
                "maximum_content_token_jaccard_to_relevant_document"
            ],
            "tfidf_overall_mrr": published_hard_tfidf["overall"]["MRR"],
            "hash_128_overall_mrr": published_hard_hash["overall"]["MRR"],
        }

    checks = {
        "manifest": manifest["ok"],
        "dataset_id": summary.get("dataset_id") == DATASET_ID == provenance.get("dataset_id"),
        "row_count": accumulator.rows == summary.get("rows") == published_audit.get("rows"),
        "semantic_audit": recomputed["ok"],
        "published_audit_matches": recomputed == published_audit,
        "reference_overlap_gate": reference.get("ok") is True,
        "retrieval_contract": retrieval_ok,
        "hard_retrieval_contract": hard_contract_ok,
        "hard_retrieval_baselines": hard_baselines_ok,
        "hard_retrieval_summary": hard_summary_ok,
        "counterfactual_arms": set(recomputed["counts"]["counterfactual_arms"]) == set(COUNTERFACTUAL_ARMS),
        "public_kaggle_metadata": metadata.get("id") == f"taylorsamarel/{DATASET_ID}" and metadata.get("isPrivate", False) is False,
        "truth_boundary": summary.get("human_authored_rows") == 0 and summary.get("human_rated_rows") == 0,
        "no_model_calls": provenance.get("generator_used_llm_calls") is False and provenance.get("generator_made_network_calls") is False,
    }
    return {
        "ok": all(checks.values()),
        "dataset_id": DATASET_ID,
        "rows": accumulator.rows,
        "files_verified": manifest["files"],
        "checks": checks,
        "surface_only_arm_accuracy": recomputed["adversarial"]["surface_only_arm_accuracy"],
        "hard_retrieval": hard_receipt,
        "allowed_claim": "downloaded bytes reproduce the deterministic synthetic-control release contract",
        "forbidden_claim": "this verification does not establish human funniness, safety, originality worldwide, or a brain mechanism",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("kaggle_open_controls"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    receipt = verify(args.root)
    rendered = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
