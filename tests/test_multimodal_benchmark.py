"""Rights, leakage, grouping, comparability, and CLI tests for multimodal work."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from humorvibes.errors import IntegrationError
from humorvibes.multimodal_benchmark import (
    build_synthetic_multimodal_fixture,
    evaluate_multimodal_fixture,
    validate_multimodal_fixture,
    write_multimodal_fixture,
)


ROOT = Path(__file__).resolve().parents[1]


def _write_fixture(tmp_path: Path, *, contests: int = 20) -> Path:
    target = tmp_path / "multimodal"
    write_multimodal_fixture(
        target,
        build_synthetic_multimodal_fixture(contests=contests),
    )
    return target


def test_procedural_fixture_is_deterministic_rights_safe_and_grouped() -> None:
    first = build_synthetic_multimodal_fixture(contests=20)
    second = build_synthetic_multimodal_fixture(contests=20)
    assert first == second
    manifest = first["manifest"]
    assert manifest["counts"] == {
        "contests": 20,
        "captions": 400,
        "captions_per_contest": 20,
    }
    assert manifest["contest_splits"] == {"test": 2, "train": 16, "validation": 2}
    assert {row["license_spdx"] for row in manifest["images"]} == {"CC0-1.0"}
    assert manifest["truth_boundary"]["human_ratings"] == 0
    assert manifest["truth_boundary"]["copyrighted_cartoon_images"] == 0


def test_three_arms_use_identical_held_out_rows_and_do_not_upgrade_claims(tmp_path: Path) -> None:
    target = _write_fixture(tmp_path)
    receipt = evaluate_multimodal_fixture(target)
    assert receipt["status"] == "VERIFIED_SYNTHETIC_MULTIMODAL_CONTRACT"
    assert set(receipt["arms"]) == {"text_only", "image_only", "fusion"}
    assert len({row["evaluated_row_digest"] for row in receipt["arms"].values()}) == 1
    assert receipt["fixture_validation"]["exact_image_duplicates"] == 0
    assert receipt["fixture_validation"]["contest_group_split_crossings"] == 0
    assert receipt["arms"]["fusion"]["metrics"]["median_within_contest_spearman"] > receipt["arms"]["text_only"]["metrics"]["median_within_contest_spearman"]
    assert receipt["arms"]["image_only"]["metrics"]["median_within_contest_spearman"] == 0.0
    assert receipt["truth_boundary"]["claim_ready_for_multimodal_humor"] is False
    requirements = receipt["real_data_reporting_requirements"]
    assert requirements["text_only_bound_applies_to"] == ["text_only"]
    assert requirements["real_bounds_apply_to_this_synthetic_fixture"] is False


def test_exact_duplicate_image_fails_closed(tmp_path: Path) -> None:
    target = _write_fixture(tmp_path)
    manifest_path = target / "multimodal_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first, second = manifest["images"][:2]
    source = target / first["image_path"]
    destination = target / second["image_path"]
    destination.write_bytes(source.read_bytes())
    second["image_sha256"] = first["image_sha256"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(IntegrationError) as observed:
        validate_multimodal_fixture(target)
    assert observed.value.code == "multimodal_exact_image_leakage"


def test_contest_split_crossing_fails_closed(tmp_path: Path) -> None:
    target = _write_fixture(tmp_path)
    rows_path = target / "caption_candidates.jsonl"
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["split"] = "validation" if rows[0]["split"] != "validation" else "test"
    rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(IntegrationError) as observed:
        validate_multimodal_fixture(target)
    assert observed.value.code == "multimodal_group_split_leakage"


def test_multimodal_cli_executes_end_to_end(tmp_path: Path) -> None:
    target = tmp_path / "cli-fixture"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "humorvibes.cli",
            "multimodal-fixture",
            "--out-dir",
            str(target),
            "--contests",
            "20",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout = json.loads(completed.stdout)
    receipt = json.loads((target / "benchmark_receipt.json").read_text(encoding="utf-8"))
    assert stdout == receipt
    assert len(list((target / "images").glob("*.svg"))) == 20
    rerun = subprocess.run(
        [
            sys.executable,
            "-m",
            "humorvibes.cli",
            "multimodal-benchmark",
            "--root",
            str(target),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(rerun.stdout) == receipt
