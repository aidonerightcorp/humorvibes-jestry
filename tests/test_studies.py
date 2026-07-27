"""Contracts for the privacy-minimized real-world study workbench."""

from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from humorvibes.errors import IntegrationError
from humorvibes.studies import (
    analyze_study,
    default_study_protocol,
    study_template,
    synthetic_study_bundle,
    validate_study_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def error_code(action) -> str:
    with pytest.raises(IntegrationError) as observed:
        action()
    return observed.value.code


def human_fixture() -> tuple[dict, dict]:
    synthetic_protocol = default_study_protocol()
    bundle = synthetic_study_bundle(synthetic_protocol)
    protocol = default_study_protocol(data_origin="human_observed")
    protocol.update({
        "preregistered": True,
        "preregistration_uri": "https://example.org/preregistrations/frozen-record",
        "minimum_writers": 6,
        "minimum_premises": 12,
        "minimum_audiences": 8,
        "minimum_ratings": 192,
    })
    bundle["data_origin"] = "human_observed"
    return protocol, bundle


def test_template_exposes_privacy_and_truth_boundaries() -> None:
    template = study_template()
    assert template["schema_version"] == "1.0"
    assert template["privacy_boundary"]["analysis_upload_endpoint"] is False
    assert template["truth_boundary"]["synthetic_fixture_can_authorize_claim"] is False
    assert "raw joke text" in template["privacy_boundary"]["rejected"]


def test_synthetic_demo_is_deterministic_and_never_claim_ready() -> None:
    protocol = default_study_protocol()
    first = analyze_study(protocol, synthetic_study_bundle(protocol))
    second = analyze_study(protocol, synthetic_study_bundle(protocol))
    assert first == second
    assert first["estimate"] == pytest.approx(0.45)
    assert first["confidence_interval_95"] == pytest.approx([0.45, 0.45])
    assert first["evidence_level"] == "L1_OFFLINE_CONTRACT"
    assert first["claim_gate"]["claim_ready"] is False
    assert "human_observed" in first["claim_gate"]["failed"]
    assert first["units"]["writers"] == 6
    assert first["bootstrap"]["independent_unit"] == "writer"


def test_qualified_human_fixture_passes_only_the_bounded_gate() -> None:
    protocol, bundle = human_fixture()
    receipt = analyze_study(protocol, bundle)
    assert receipt["claim_gate"]["claim_ready"] is True
    assert receipt["evidence_level"] == "L3_PREREGISTERED_HELD_OUT"
    assert receipt["truth_boundary"]["universal_funniness_claim_authorized"] is False
    assert "population and context" in receipt["allowed_claim"]


def test_row_order_cannot_change_analysis_or_digest() -> None:
    protocol = default_study_protocol()
    first_bundle = synthetic_study_bundle(protocol)
    second_bundle = copy.deepcopy(first_bundle)
    second_bundle["materials"].reverse()
    second_bundle["audience_responses"].reverse()
    assert analyze_study(protocol, first_bundle) == analyze_study(protocol, second_bundle)


def test_raw_material_identity_and_unknown_fields_fail_closed() -> None:
    protocol = default_study_protocol()
    raw_text = synthetic_study_bundle(protocol)
    raw_text["materials"][0]["raw_text"] = "material must stay outside the analysis export"
    assert error_code(lambda: validate_study_bundle(protocol, raw_text)) == "forbidden_study_field"

    identity = synthetic_study_bundle(protocol)
    identity["audience_responses"][0]["email"] = "private@example.org"
    assert error_code(lambda: validate_study_bundle(protocol, identity)) == "forbidden_study_field"

    unknown = synthetic_study_bundle(protocol)
    unknown["materials"][0]["favorite_color"] = "blue"
    assert error_code(lambda: validate_study_bundle(protocol, unknown)) == "unknown_study_field"


def test_duplicate_ids_nonfinite_values_and_unknown_references_fail_closed() -> None:
    protocol = default_study_protocol()
    duplicate = synthetic_study_bundle(protocol)
    duplicate["audience_responses"][1]["response_id"] = duplicate["audience_responses"][0]["response_id"]
    assert error_code(lambda: validate_study_bundle(protocol, duplicate)) == "duplicate_response_id"

    nonfinite = synthetic_study_bundle(protocol)
    nonfinite["audience_responses"][0]["rating"] = math.nan
    assert error_code(lambda: validate_study_bundle(protocol, nonfinite)) == "invalid_study_value"

    unknown = synthetic_study_bundle(protocol)
    unknown["audience_responses"][0]["material_id"] = "not-in-materials"
    assert error_code(lambda: validate_study_bundle(protocol, unknown)) == "unknown_material_reference"


def test_consent_holdout_permission_and_complete_pairs_are_hard_gates() -> None:
    protocol = default_study_protocol()
    no_consent = synthetic_study_bundle(protocol)
    no_consent["audience_responses"][0]["consent_confirmed"] = False
    assert error_code(lambda: validate_study_bundle(protocol, no_consent)) == "audience_consent_missing"

    not_held_out = synthetic_study_bundle(protocol)
    not_held_out["audience_responses"][0]["held_out"] = False
    assert error_code(lambda: validate_study_bundle(protocol, not_held_out)) == "audience_not_held_out"

    no_permission = synthetic_study_bundle(protocol)
    no_permission["materials"][0]["permission_confirmed"] = False
    assert error_code(lambda: validate_study_bundle(protocol, no_permission)) == "material_permission_missing"

    incomplete = synthetic_study_bundle(protocol)
    removed_id = incomplete["materials"].pop(0)["material_id"]
    incomplete["audience_responses"] = [
        row for row in incomplete["audience_responses"] if row["material_id"] != removed_id
    ]
    assert error_code(lambda: validate_study_bundle(protocol, incomplete)) == "incomplete_paired_block"


def test_preregistration_sample_and_effect_gates_cannot_be_bypassed() -> None:
    protocol, bundle = human_fixture()
    protocol["preregistered"] = False
    protocol["preregistration_uri"] = ""
    receipt = analyze_study(protocol, bundle)
    assert receipt["claim_gate"]["claim_ready"] is False
    assert receipt["evidence_level"] == "L2_HUMAN_PILOT"

    protocol, bundle = human_fixture()
    protocol["minimum_writers"] = 7
    receipt = analyze_study(protocol, bundle)
    assert receipt["claim_gate"]["claim_ready"] is False
    assert receipt["claim_gate"]["checks"]["minimum_writers"] is False

    protocol, bundle = human_fixture()
    protocol["minimally_important_difference"] = 0.5
    receipt = analyze_study(protocol, bundle)
    assert receipt["claim_gate"]["claim_ready"] is False
    assert receipt["claim_gate"]["checks"]["lower_interval_exceeds_minimum_effect"] is False


def test_repeated_ratings_do_not_become_independent_units() -> None:
    protocol = default_study_protocol()
    bundle = synthetic_study_bundle(protocol)
    receipt = analyze_study(protocol, bundle)
    assert receipt["units"]["ratings"] == 192
    assert receipt["units"]["materials"] == 24
    assert receipt["units"]["writers"] == 6
    assert receipt["bootstrap"]["independent_unit"] == "writer"
    assert receipt["truth_boundary"]["ratings_are_aggregated_before_writer_cluster_bootstrap"] is True


def test_direct_example_and_cli_demo_execute_end_to_end(tmp_path: Path) -> None:
    example = subprocess.run(
        [sys.executable, "examples/writer_study_demo.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(example.stdout)["claim_gate"]["claim_ready"] is False

    output = tmp_path / "receipt.json"
    cli = subprocess.run(
        [sys.executable, "-m", "humorvibes.cli", "study-demo", "--out", str(output)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert json.loads(cli.stdout) == json.loads(output.read_text(encoding="utf-8"))

