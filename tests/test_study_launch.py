"""Prospective planning, randomization, and launch-pack truth boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from humorvibes.errors import IntegrationError
from humorvibes.studies import default_study_protocol
from humorvibes.study_launch import (
    build_launch_pack,
    create_assignment_key,
    deterministic_randomization,
    prospective_precision_plan,
    read_assignment_key,
    write_launch_pack,
)


ROOT = Path(__file__).resolve().parents[1]
KEY = "test-only-randomization-key-00000000000000000000000000000000"


def test_precision_plan_is_deterministic_and_scales_with_uncertainty() -> None:
    base = prospective_precision_plan()
    assert base == prospective_precision_plan()
    noisier = prospective_precision_plan(between_writer_sd=0.9)
    smaller_effect = prospective_precision_plan(target_effect=0.125)
    assert noisier["planned_counts"]["writers_to_recruit"] > base["planned_counts"]["writers_to_recruit"]
    assert smaller_effect["planned_counts"]["writers_to_recruit"] > base["planned_counts"]["writers_to_recruit"]
    assert base["truth_boundary"]["prospective_not_observed_power"] is True


def test_randomization_is_balanced_blinded_and_reproducible() -> None:
    first = deterministic_randomization(
        writer_count=11, premises_per_writer=3, seed=42, assignment_key=KEY
    )
    second = deterministic_randomization(
        writer_count=11, premises_per_writer=3, seed=42, assignment_key=KEY
    )
    assert first == second
    assert first["counts"]["blocks"] == 33
    assert abs(first["balance"]["control_first_blocks"] - first["balance"]["assisted_first_blocks"]) <= 1
    assert abs(first["balance"]["panel_01_control_blocks"] - first["balance"]["panel_01_assisted_blocks"]) <= 1
    blinded = json.dumps(
        {
            "writing": first["blinded_writing_schedule"],
            "audience": first["blinded_audience_schedule"],
        }
    )
    assert "condition" not in blinded
    panels_by_block: dict[str, set[str]] = {}
    for row in first["blinded_audience_schedule"]:
        panels_by_block.setdefault(row["block_id"], set()).add(row["blind_material_id"])
    assert all(len(materials) == 2 for materials in panels_by_block.values())


def test_launch_pack_updates_unregistered_minima_but_never_claims_observations(tmp_path: Path) -> None:
    protocol = default_study_protocol(data_origin="human_observed")
    pack = build_launch_pack(protocol, assignment_key=KEY)
    receipt = pack["launch_receipt"]
    assert receipt["status"] == "READY_FOR_EXTERNAL_ETHICS_AND_REGISTRATION"
    assert receipt["claim_gate"]["claim_ready"] is False
    assert receipt["external_gates"]["observations_collected"] is False
    assert pack["protocol"]["minimum_writers"] >= protocol["minimum_writers"]
    assert "not registered" in pack["preregistration_markdown"]
    write_launch_pack(tmp_path, pack)
    assert (tmp_path / "restricted_assignment_map.json").is_file()
    assert (tmp_path / "blinded_audience_schedule.json").is_file()
    assert json.loads((tmp_path / "launch_receipt.json").read_text())["claim_gate"]["claim_ready"] is False
    with pytest.raises(IntegrationError, match="Refusing to overwrite"):
        write_launch_pack(tmp_path, pack)


def test_cli_writes_complete_launch_pack(tmp_path: Path) -> None:
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(
        json.dumps(default_study_protocol(data_origin="human_observed")), encoding="utf-8"
    )
    output = tmp_path / "launch"
    key_path = tmp_path / "restricted" / "assignment.key"
    key_receipt = create_assignment_key(key_path)
    assert key_receipt["secret_printed"] is False
    assert key_path.stat().st_mode & 0o777 == 0o600
    assert read_assignment_key(key_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "humorvibes.cli",
            "study-launch",
            "--protocol",
            str(protocol_path),
            "--out-dir",
            str(output),
            "--assignment-key-file",
            str(key_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(completed.stdout)
    assert receipt == json.loads((output / "launch_receipt.json").read_text())
    assert {path.name for path in output.iterdir()} == {
        "protocol.json",
        "precision_plan.json",
        "restricted_assignment_map.json",
        "blinded_writing_schedule.json",
        "blinded_audience_schedule.json",
        "launch_receipt.json",
        "PREREGISTRATION_DRAFT.md",
        "OPERATIONS.md",
    }
