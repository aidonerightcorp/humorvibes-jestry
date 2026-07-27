"""Adversarial tests for the human multimodal evidence boundary."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from humorvibes.errors import IntegrationError
from humorvibes.human_multimodal import (
    _dhash64,
    evaluate_human_multimodal_bundle,
    human_multimodal_content_digest,
    validate_human_multimodal_bundle,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _image_bytes(index: int) -> bytes:
    pixels = bytes(
        hashlib.sha256(f"human-mm-test-{index}-{position}".encode()).digest()[0]
        for position in range(9 * 8)
    )
    return b"P5\n9 8\n255\n" + pixels


def _write_bundle(tmp_path: Path) -> Path:
    root = tmp_path / "human-multimodal"
    (root / "images").mkdir(parents=True)
    (root / "evidence").mkdir()
    source = root / "evidence" / "source-snapshot.json"
    protocol = root / "evidence" / "rating-protocol.md"
    consent = root / "evidence" / "consent-and-license.md"
    rights_evidence = root / "evidence" / "rights-review.md"
    source.write_text('{"frozen":"test-only-cohort"}\n', encoding="utf-8")
    protocol.write_text("Test protocol fixture; no real people or claims.\n", encoding="utf-8")
    consent.write_text("Test-only consent contract fixture.\n", encoding="utf-8")
    rights_evidence.write_text("Test-only rights contract fixture.\n", encoding="utf-8")

    feature_names = {
        "text_only": ["text_length", "variant"],
        "image_only": ["scene_index", "scene_parity"],
        "fusion": ["text_length", "variant", "scene_index", "interaction"],
    }
    feature_provenance = {
        arm: {
            "provider": "test-only-deterministic",
            "model": f"fixture-{arm}",
            "revision": "1",
            "preprocessing": "declared scalar fixture features",
            "dimensions": len(names),
            "executed": True,
        }
        for arm, names in feature_names.items()
    }
    splits = ["train", "train", "validation", "validation", "test", "test"]
    images: list[dict[str, object]] = []
    rights: list[dict[str, object]] = []
    captions: list[dict[str, object]] = []
    evidence_sha = _sha(rights_evidence)
    for index, split in enumerate(splits):
        contest_id = f"test-contest-{index + 1:02d}"
        asset_id = f"test-image-{index + 1:02d}"
        image_path = root / "images" / f"{contest_id}.pgm"
        payload = _image_bytes(index)
        image_path.write_bytes(payload)
        image_sha = hashlib.sha256(payload).hexdigest()
        images.append(
            {
                "contest_id": contest_id,
                "split": split,
                "canonical_scene_group_id": f"test-scene-{index + 1:02d}",
                "rights_asset_id": asset_id,
                "image_path": f"images/{contest_id}.pgm",
                "image_sha256": image_sha,
                "perceptual_hash_algorithm": "dhash-64-v1",
                "perceptual_hash": _dhash64(payload),
            }
        )
        rights.append(
            {
                "asset_id": asset_id,
                "asset_type": "image",
                "contest_id": contest_id,
                "asset_sha256": image_sha,
                "rights_basis": "creator_permission",
                "license_spdx": "CC-BY-4.0",
                "source_url": f"https://example.invalid/test-assets/{asset_id}",
                "redistribution_allowed": True,
                "research_allowed": True,
                "derivatives_allowed": True,
                "evidence_path": "evidence/rights-review.md",
                "evidence_sha256": evidence_sha,
            }
        )
        for variant in range(5):
            text = f"Test-only caption {variant} for scene {index}."
            captions.append(
                {
                    "row_id": f"test-row-{index:02d}-{variant:02d}",
                    "contest_id": contest_id,
                    "split": split,
                    "caption": text,
                    "caption_rights_id": "test-caption-cohort",
                    "target": 1.0 + variant + (index % 2) * variant * 0.25,
                    "target_origin": "human_observed",
                    "target_standard_error": 0.2,
                    "rating_count": 5,
                    "caption_strategy": "test-only",
                    "repeated_caption": variant == 0,
                    "features": {
                        "text_only": [len(text) / 100.0, variant / 4.0],
                        "image_only": [index / 5.0, float(index % 2)],
                        "fusion": [
                            len(text) / 100.0,
                            variant / 4.0,
                            index / 5.0,
                            (index % 2) * variant / 4.0,
                        ],
                    },
                }
            )
    rights.append(
        {
            "asset_id": "test-caption-cohort",
            "asset_type": "caption_cohort",
            "rights_basis": "creator_permission",
            "license_spdx": "CC-BY-4.0",
            "source_url": "https://example.invalid/test-assets/caption-cohort",
            "redistribution_allowed": True,
            "research_allowed": True,
            "derivatives_allowed": True,
            "evidence_path": "evidence/consent-and-license.md",
            "evidence_sha256": _sha(consent),
        }
    )
    manifest: dict[str, object] = {
        "receipt_type": "humorvibes_human_multimodal_manifest",
        "schema_version": 1,
        "cohort_id": "test-only-human-contract-fixture",
        "data_origin": "human_observed",
        "source_snapshot": {
            "source_url": "https://example.invalid/test-assets",
            "immutable_revision": "test-revision-1",
            "retrieved_at": "2026-07-27T00:00:00Z",
            "snapshot_path": "evidence/source-snapshot.json",
            "snapshot_sha256": _sha(source),
        },
        "label_protocol": {
            "human_observed": True,
            "target_unit": "mean_funniness_rating_per_caption",
            "scale": [1, 10],
            "minimum_raters_per_caption": 5,
            "audience_population": "test fixture declaration only",
            "collection_started": "2026-07-01",
            "collection_ended": "2026-07-02",
            "aggregation": "arithmetic mean after frozen exclusions",
            "protocol_evidence_path": "evidence/rating-protocol.md",
            "protocol_evidence_sha256": _sha(protocol),
            "consent_evidence_path": "evidence/consent-and-license.md",
            "consent_evidence_sha256": _sha(consent),
        },
        "near_duplicate_hamming_threshold": 0,
        "minimum_captions_per_contest": 5,
        "feature_names": feature_names,
        "feature_provenance": feature_provenance,
        "images": images,
    }
    manifest["content_digest"] = human_multimodal_content_digest(
        images=images, captions=captions, rights=rights
    )
    (root / "human_multimodal_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_jsonl(root / "caption_candidates.jsonl", captions)
    _write_jsonl(root / "rights_ledger.jsonl", rights)
    return root


def test_human_bundle_preflight_and_evaluation_keep_external_gate_closed(tmp_path: Path) -> None:
    root = _write_bundle(tmp_path)
    preflight = validate_human_multimodal_bundle(root)
    benchmark = evaluate_human_multimodal_bundle(root)
    assert preflight["status"] == "MACHINE_VALIDATED_EXTERNAL_REVIEW_REQUIRED"
    assert preflight["counts"]["captions"] == 30
    assert preflight["checks"]["image_perceptual_hashes"] == 6
    assert preflight["truth_boundary"]["claim_ready_for_multimodal_humor"] is False
    assert set(benchmark["arms"]) == {"text_only", "image_only", "fusion"}
    assert len({arm["evaluated_row_digest"] for arm in benchmark["arms"].values()}) == 1
    assert benchmark["reference_bounds"]["text_only_bound_applies_to"] == ["text_only"]


def test_synthetic_target_cannot_enter_human_lane(tmp_path: Path) -> None:
    root = _write_bundle(tmp_path)
    path = root / "caption_candidates.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["target_origin"] = "model_score"
    _write_jsonl(path, rows)
    with pytest.raises(IntegrationError) as observed:
        validate_human_multimodal_bundle(root)
    assert observed.value.code == "invalid_human_multimodal_target"


def test_dataset_level_license_cannot_replace_asset_evidence(tmp_path: Path) -> None:
    root = _write_bundle(tmp_path)
    path = root / "rights_ledger.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["license_spdx"] = "NOASSERTION"
    _write_jsonl(path, rows)
    with pytest.raises(IntegrationError) as observed:
        validate_human_multimodal_bundle(root)
    assert observed.value.code == "invalid_multimodal_rights"


def test_direct_identity_and_image_tampering_fail_closed(tmp_path: Path) -> None:
    root = _write_bundle(tmp_path)
    captions_path = root / "caption_candidates.jsonl"
    rows = [json.loads(line) for line in captions_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["email"] = "must-not-enter@example.invalid"
    _write_jsonl(captions_path, rows)
    with pytest.raises(IntegrationError) as identity:
        validate_human_multimodal_bundle(root)
    assert identity.value.code == "human_multimodal_direct_identity"

    root = _write_bundle(tmp_path / "second")
    image = next((root / "images").glob("*.pgm"))
    image.write_bytes(image.read_bytes() + b"tampered")
    with pytest.raises(IntegrationError) as tampering:
        validate_human_multimodal_bundle(root)
    assert tampering.value.code == "human_multimodal_image_hash_mismatch"


def test_human_multimodal_cli_contract_validate_and_benchmark(tmp_path: Path) -> None:
    root = _write_bundle(tmp_path)
    contract = subprocess.run(
        [sys.executable, "-m", "humorvibes.cli", "multimodal-human-contract"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(contract.stdout)["truth_boundary"]["external_rights_and_research_review_required"] is True
    for command in ("multimodal-human-validate", "multimodal-human-benchmark"):
        completed = subprocess.run(
            [sys.executable, "-m", "humorvibes.cli", command, "--root", str(root)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert json.loads(completed.stdout)["truth_boundary"]["claim_ready_for_multimodal_humor"] is False

