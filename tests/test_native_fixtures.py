"""Native-language fixture contribution and reviewer-attestation gates."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from humorvibes.errors import IntegrationError
from humorvibes.native_fixtures import validate_native_fixture_bundle


ROOT = Path(__file__).resolve().parents[1]


def _bundle() -> dict:
    fixtures = []
    for index in range(20):
        fixtures.append(
            {
                "fixture_id": f"positive-{index:02d}",
                "text": f"O que é, o que é? Pergunta verificada número {index}.",
                "expected_match": True,
                "rationale": "Contains the reviewed riddle opener in an affirmative example.",
                "source_ref": f"project-controlled-positive-{index:02d}",
                "permission_confirmed": True,
            }
        )
        fixtures.append(
            {
                "fixture_id": f"negative-{index:02d}",
                "text": f"Quando é a pergunta de contraste número {index}?",
                "expected_match": False,
                "rationale": "Question-shaped hard negative without the reviewed riddle opener.",
                "source_ref": f"project-controlled-negative-{index:02d}",
                "permission_confirmed": True,
            }
        )
    return {
        "schema_version": "1.0",
        "language": "pt",
        "locale": "pt-BR",
        "form_id": "pt_o_que_e",
        "rule_pattern": r"\bo que é,? o que é\b",
        "rule_note": "Portuguese riddle opener; fixture content here tests only the contract.",
        "source_snapshot": {
            "source_url": "https://github.com/aidonerightcorp/humorvibes-jestry",
            "source_revision": "test-contract-v1",
            "retrieved_at": "2026-07-27",
            "license_id": "CC0-1.0",
            "license_evidence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "redistribution_permission_confirmed": True,
            "source_digest": hashlib.sha256(b"test-native-fixtures").hexdigest(),
        },
        "review": {
            "status": "human_reviewed",
            "reviewer_id": "reviewer-contract-test",
            "fluency_basis": "Test-only fluent-review attestation string for schema validation.",
            "conflicts": "None declared for the contract test.",
            "reviewed_at": "2026-07-27",
            "machine_translation_used_for_acceptance": False,
            "consent_to_publish_attestation": True,
        },
        "fixtures": fixtures,
        "coverage": {
            "corpus_rows": 100,
            "matches_before": 0,
            "matches_after": 24,
            "reviewed_match_sample": 20,
            "false_positives_in_sample": 1,
            "corpus_digest": hashlib.sha256(b"test-language-corpus").hexdigest(),
        },
        "aligned_pair_consistency": {
            "applicable": False,
            "pairs_reviewed": 0,
            "mechanism_consistent": 0,
            "notes": "No aligned phrase pairs are part of this contract test.",
        },
    }


def test_native_fixture_contract_accepts_one_complete_language_and_emits_no_text() -> None:
    receipt = validate_native_fixture_bundle(_bundle())
    assert receipt["claim_gate"]["fixture_ready_for_taxonomy_pr"] is True
    assert receipt["fixtures"]["positives"] == 20
    assert receipt["fixtures"]["hard_negatives"] == 20
    assert receipt["review"]["machine_translation_accepted_the_fixture"] is False
    assert receipt["truth_boundary"]["attestation_identity_independently_verified"] is False
    assert "O que é" not in json.dumps(receipt, ensure_ascii=False)


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda value: value["review"].update(status="model_reviewed"),
            "native_human_review_missing",
        ),
        (
            lambda value: value["review"].update(machine_translation_used_for_acceptance=True),
            "machine_translation_cannot_accept_native_fixture",
        ),
        (
            lambda value: value["source_snapshot"].update(license_id="research-only"),
            "native_fixture_not_redistributable",
        ),
        (
            lambda value: value.update(fixtures=value["fixtures"][:-2]),
            "native_fixture_arm_too_small",
        ),
        (
            lambda value: value["fixtures"][0].update(expected_match=False),
            "native_fixture_rule_mismatch",
        ),
        (
            lambda value: value["review"].update(email="reviewer@example.invalid"),
            "native_review_identity_forbidden",
        ),
    ],
)
def test_native_fixture_contract_fails_closed(mutate, code: str) -> None:
    value = _bundle()
    mutate(value)
    with pytest.raises(IntegrationError) as observed:
        validate_native_fixture_bundle(value)
    assert observed.value.code == code


def test_native_fixture_cli_writes_body_free_receipt(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(_bundle(), ensure_ascii=False), encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "humorvibes.cli",
            "native-fixture-validate",
            str(bundle),
            "--out",
            str(receipt_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == json.loads(receipt_path.read_text(encoding="utf-8"))


def test_alignment_and_coverage_counts_are_checked() -> None:
    bad_alignment = _bundle()
    bad_alignment["aligned_pair_consistency"].update(
        applicable=True, pairs_reviewed=2, mechanism_consistent=3
    )
    with pytest.raises(IntegrationError) as observed:
        validate_native_fixture_bundle(bad_alignment)
    assert observed.value.code == "invalid_native_alignment_review"

    bad_coverage = copy.deepcopy(_bundle())
    bad_coverage["coverage"]["reviewed_match_sample"] = 5
    with pytest.raises(IntegrationError) as observed:
        validate_native_fixture_bundle(bad_coverage)
    assert observed.value.code == "native_false_positive_review_too_small"
