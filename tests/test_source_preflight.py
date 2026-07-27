"""Offline-first source-spec preflight and deny-first release gates."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import source_spec_preflight as preflight


ROOT = Path(__file__).resolve().parents[1]


def _inputs() -> tuple[dict, dict, list[dict]]:
    spec = json.loads(preflight.DEFAULT_SPEC.read_text(encoding="utf-8"))
    fixture = json.loads(preflight.DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    expected = json.loads(preflight.DEFAULT_EXPECTED.read_text(encoding="utf-8"))
    return spec, fixture, expected


def test_default_fixture_preflight_is_deterministic_export_eligible_and_body_free() -> None:
    first = preflight.execute()
    second = preflight.execute()
    assert first == second
    assert first["ok"] is True
    assert first["mode"] == "fixture"
    assert first["parser"]["expected_fixture_match"] is True
    assert first["release_decision"] == {
        "export_eligible": True,
        "policy": "deny-first: explicit redistributable class plus matching live/fixture license and repository evidence",
        "failed_gates": [],
    }
    assert first["safety"]["writes_corpus"] is False
    rendered = json.dumps(first)
    assert "What do you call a turtle" not in rendered


def test_schema_drift_empty_response_and_duplicate_ids_fail_closed() -> None:
    spec, fixture, expected = _inputs()
    drifted = copy.deepcopy(fixture)
    drifted["first_rows"]["features"] = [drifted["first_rows"]["features"][0]]
    with pytest.raises(preflight.PreflightError) as observed:
        preflight.run_preflight(spec, drifted, mode="fixture", expected_normalized=expected)
    assert observed.value.code == "source_schema_drift"

    empty = copy.deepcopy(fixture)
    empty["first_rows"]["rows"] = []
    with pytest.raises(preflight.PreflightError) as observed:
        preflight.run_preflight(spec, empty, mode="fixture", expected_normalized=expected)
    assert observed.value.code == "empty_upstream_response"

    duplicate = copy.deepcopy(fixture)
    duplicate["first_rows"]["rows"][1]["row_idx"] = 0
    with pytest.raises(preflight.PreflightError) as observed:
        preflight.run_preflight(spec, duplicate, mode="fixture", expected_normalized=expected)
    assert observed.value.code == "duplicate_upstream_row_id"


def test_invalid_json_encoding_and_missing_license_fail_closed() -> None:
    with pytest.raises(preflight.PreflightError) as observed:
        preflight._load_json_bytes(b"{not-json", source="test")
    assert observed.value.code == "invalid_upstream_json"
    with pytest.raises(preflight.PreflightError) as observed:
        preflight._load_json_bytes(b'\xff{"rows":[]}', source="test")
    assert observed.value.code == "invalid_upstream_encoding"

    spec, _fixture, _expected = _inputs()
    spec["license"] = ""
    with pytest.raises(preflight.PreflightError) as observed:
        preflight.validate_source_spec(spec)
    assert observed.value.code == "invalid_source_spec_field"


def test_explicit_research_only_source_can_parse_but_cannot_export() -> None:
    spec, fixture, expected = _inputs()
    spec["license"] = "research use only; do not redistribute"
    spec["license_id"] = "research-only"
    fixture["dataset_metadata"]["cardData"]["license"] = "research-only"
    for row in expected:
        row["license"] = spec["license"]
    receipt = preflight.run_preflight(
        spec, fixture, mode="fixture", expected_normalized=expected
    )
    assert receipt["ok"] is True
    assert receipt["license_evidence"]["licence_class"] == "research_only"
    assert receipt["release_decision"]["export_eligible"] is False
    assert receipt["release_decision"]["failed_gates"] == [
        "explicit_redistribution_grant"
    ]


def test_revision_drift_is_visible_and_blocks_export() -> None:
    spec, fixture, expected = _inputs()
    fixture["dataset_metadata"]["sha"] = "f" * 40
    receipt = preflight.run_preflight(
        spec, fixture, mode="fixture", expected_normalized=expected
    )
    assert receipt["license_evidence"]["revision_matches"] is False
    assert receipt["release_decision"]["export_eligible"] is False
    assert receipt["release_decision"]["failed_gates"] == ["revision_matches"]


def test_live_mode_is_bounded_and_uses_no_fixture_expectation(monkeypatch: pytest.MonkeyPatch) -> None:
    spec, fixture, _expected = _inputs()
    calls: list[str] = []

    def fake_fetch(url: str, *, timeout: float, maximum_bytes: int = 2_000_000):
        calls.append(url)
        value = fixture["dataset_metadata"] if "/api/datasets/" in url else fixture["first_rows"]
        raw = json.dumps(value).encode("utf-8")
        return raw, {
            "url": url,
            "status": 200,
            "content_type": "application/json",
            "bytes": len(raw),
            "sha256": "0" * 64,
        }

    monkeypatch.setattr(preflight, "_bounded_fetch", fake_fetch)
    payload, observations = preflight._live_payload(spec, timeout=2.0, limit=2)
    receipt = preflight.run_preflight(
        spec, payload, mode="live", network_observations=observations
    )
    assert len(calls) == 2
    assert all(url.startswith("https://") for url in calls)
    assert receipt["observed_response"]["input_rows"] == 2
    assert receipt["parser"]["expected_fixture_checked"] is False
    assert receipt["safety"]["maximum_live_rows"] == 2


def test_cli_defaults_to_offline_fixture_and_writes_only_the_requested_receipt(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    completed = subprocess.run(
        [sys.executable, "source_spec_preflight.py", "--out", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    printed = json.loads(completed.stdout)
    assert printed == json.loads(output.read_text(encoding="utf-8"))
    assert printed["mode"] == "fixture"
    assert printed["safety"]["network_disabled_by_default"] is True
