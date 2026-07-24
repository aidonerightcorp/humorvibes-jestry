from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
HARVEST = ROOT / "research_out" / "kaggle" / "humorvibes-ablation-court"


def _json(name: str) -> dict:
    return json.loads((HARVEST / name).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_harvest_receipts_and_source_hashes_are_self_consistent() -> None:
    summary = _json("ablation_summary.json")
    runtime = _json("runtime_receipt.json")
    harvest = _json("harvest_receipt.json")

    assert summary["status"] == runtime["status"] == "complete"
    assert summary["external_submission_made"] is False
    assert runtime["external_submission_made"] is False
    assert harvest["external_submission_made"] is False
    assert runtime["kernel_private_at_run"] is True
    assert harvest["kernel_private"] is True
    assert harvest["source_cells_match"] is True

    assert runtime["model"]["true_teacher_forced_logprobs"] is True
    assert runtime["model"]["provider_name"] == "transformers"
    assert runtime["model"]["model_source"] == "google/gemma-2/transformers/gemma-2-2b-it/2"
    assert runtime["model"]["mesh_signals_sha256"] == _sha(ROOT / "mesh_signals.py")
    assert runtime["model"]["humor_mesh_sha256"] == _sha(ROOT / "humor_mesh.py")

    for name, evidence in runtime["outputs"].items():
        path = HARVEST / name
        assert path.stat().st_size == evidence["bytes"]
        assert _sha(path) == evidence["sha256"]
    for name, evidence in harvest["outputs"].items():
        path = HARVEST / name
        assert path.stat().st_size == evidence["bytes"]
        assert _sha(path) == evidence["sha256"]


def test_raw_rows_replay_the_predeclared_fixed_score_result() -> None:
    summary = _json("ablation_summary.json")
    rows = [json.loads(line) for line in (HARVEST / "ablation_rows.jsonl").read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 200
    assert Counter(row["variant"] for row in rows) == {
        "human_edit": 120,
        "original_headline": 40,
        "shuffled_edit": 40,
    }
    assert all(row["error"] is None for row in rows)
    assert all(row["gemma_logprobs_measured"] is True for row in rows)
    assert all(row["bad_surprise_measured"] is True for row in rows)

    controls: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["control_set"]:
            controls[row["id"]].add(row["variant"])
    assert len(controls) == 40
    assert all(variants == {"human_edit", "original_headline", "shuffled_edit"} for variants in controls.values())

    human = [row for row in rows if row["variant"] == "human_edit"]
    weights = summary["metric"]["fixed_weights"]
    fixed = np.asarray([
        100.0 * sum(weights[name] * row[f"{name}_score"] for name in ("S", "R", "E", "B"))
        for row in human
    ])
    grades = np.asarray([row["grade"] for row in human])
    replay = float(spearmanr(fixed, grades).statistic)
    reported = summary["metric"]["ablation"]["full_SREB"]["spearman"]
    assert np.isclose(replay, reported, atol=1e-12)
    assert summary["sample"] == {
        "bad_surprise_judge_coverage_on_human": 1.0,
        "completion_rate": 1.0,
        "control_sets": 40,
        "human_rows": 120,
        "measurement_jobs": 200,
        "successful_jobs": 200,
    }
