from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import build_open_controls as builder
from humorvibes.open_controls import (
    COUNTERFACTUAL_ARMS,
    DATA_LICENSE,
    DEFAULT_SEED,
    MAX_CONFIGS,
    MAX_FAMILIES,
    MAX_VARIANTS,
    AuditAccumulator,
    audit_reference_overlap,
    audit_rows,
    generation_contract,
    human_contribution_schema,
    human_rating_schema,
    iter_rows,
    model_candidate_schema,
    retrieval_rows,
    row_schema,
    sample_rows,
    validate_human_contributions,
    validate_human_ratings,
    validate_manifest,
    validate_model_candidates,
)
from humorvibes.service import HumorVibesService
from verify_open_controls_release import verify


ROOT = Path(__file__).resolve().parents[1]


def _rows(**kwargs):
    return list(iter_rows(generator_commit="a" * 40, **kwargs))


def test_generation_contract_is_explicit_about_scale_licence_and_truth() -> None:
    contract = generation_contract()
    assert contract["maximum_rows"] == 120_000
    assert contract["maximum_rows"] == MAX_FAMILIES * MAX_CONFIGS * len(COUNTERFACTUAL_ARMS) * MAX_VARIANTS
    assert contract["license_spdx"] == DATA_LICENSE == "CC0-1.0"
    assert contract["data_origin"] == "procedural"
    assert contract["truth_boundary"] == {
        "human_authored": False,
        "human_rated": False,
        "funniness_ground_truth": False,
        "intended_mechanism_is_observed_effect": False,
        "allowed_claim": "deterministic project-controlled counterfactual text",
    }
    assert len(contract["generator_source_sha256"]) == 64


def test_rows_are_deterministic_balanced_and_matched() -> None:
    first = _rows(families=12, configs=3, variants=2)
    second = _rows(families=12, configs=3, variants=2)
    assert first == second
    assert len(first) == 12 * 3 * 4 * 2
    assert len({row["item_id"] for row in first}) == len(first)
    assert len({row["text"] for row in first}) == len(first)
    group = [row for row in first if row["configuration_id"] == first[0]["configuration_id"] and row["surface_variant"] == 0]
    assert {row["counterfactual_arm"] for row in group} == set(COUNTERFACTUAL_ARMS)
    assert len({row["setup"] for row in group}) == 1
    assert len({row["split"] for row in group}) == 1
    assert all(row["human_authored"] is False and row["human_rated"] is False for row in group)
    assert all(row["funniness_label"] is None and row["synthetic"] is True for row in group)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"families": 0}, "families"),
        ({"families": 301}, "families"),
        ({"configs": 0}, "configs"),
        ({"variants": 3}, "variants"),
        ({"seed": True}, "seed"),
        ({"arms": []}, "arms"),
        ({"arms": ["not-an-arm"]}, "unknown"),
    ],
)
def test_invalid_generation_contracts_fail_closed(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        list(iter_rows(**kwargs))


def test_full_120k_release_shape_passes_streaming_adversarial_audit() -> None:
    report, accumulator = audit_rows(iter_rows(generator_commit="b" * 40))
    assert report["ok"] is True
    assert report["rows"] == 120_000
    assert report["counts"]["premise_families"] == 300
    assert report["counts"]["template_families"] == 30
    assert report["counts"]["counterfactual_arms"] == {arm: 30_000 for arm in sorted(COUNTERFACTUAL_ARMS)}
    assert report["counts"]["surface_variants"] == {"0": 60_000, "1": 60_000}
    assert report["counts"]["splits"] == {"test": 12_000, "train": 96_000, "validation": 12_000}
    assert 0.25 <= report["adversarial"]["surface_only_arm_accuracy"] < 0.80
    assert len(accumulator.prototype_rows) == 1_200


def test_audit_detects_truth_duplicate_and_split_tampering() -> None:
    rows = _rows(families=2, configs=1, variants=1)
    rows[1]["item_id"] = rows[0]["item_id"]
    rows[2]["text"] = rows[0]["text"]
    rows[3]["human_rated"] = True
    rows[4]["split"] = "test" if rows[4]["split"] != "test" else "train"
    report, _ = audit_rows(rows)
    assert report["ok"] is False
    assert report["violations"]["duplicate_item_ids"] == 1
    assert report["violations"]["duplicate_normalized_texts"] == 1
    assert report["violations"]["truth_boundary_errors"] == 1
    assert report["checks"]["template_split_isolation"] is False


def test_reference_overlap_reports_matches_without_copying_reference_text(tmp_path: Path) -> None:
    rows = _rows(families=1, configs=1, variants=1)
    accumulator = AuditAccumulator()
    for row in rows:
        accumulator.add(row)
    reference = tmp_path / "reference.jsonl"
    reference.write_text(json.dumps({"text": rows[0]["text"], "source": "fixture"}) + "\n", encoding="utf-8")
    receipt = audit_reference_overlap(accumulator.prototype_rows, [reference])
    assert receipt["ok"] is False
    assert receipt["exact_matches"] == 1
    assert receipt["reference_rows_scanned"] == 1
    assert "text" not in receipt["examples_capped"][0]


def test_retrieval_contract_supports_one_or_two_surface_variants() -> None:
    for variants in (1, 2):
        documents, queries, qrels = retrieval_rows(_rows(families=12, configs=1, variants=variants))
        assert len(documents) == len(queries) == len(qrels) == 12
        assert {row["document_id"] for row in documents} == {row["document_id"] for row in qrels}
        assert {row["query_id"] for row in queries} == {row["query_id"] for row in qrels}
        assert all(row["relevance"] == 2 for row in qrels)


def _valid_rating(item_id: str) -> dict[str, object]:
    return {
        "rating_id": "rating_0001",
        "item_id": item_id,
        "protocol_id": "protocol_v1",
        "rater_key": "rater_ab12cd34",
        "locale": "en-US",
        "audience_context": "blinded online pilot",
        "familiarity": 1,
        "expectedness": 3,
        "surprise": 5,
        "resolution": 4,
        "funniness": 2,
        "offensiveness": 1,
        "comprehensibility": 6,
        "consent_version": "v1",
        "collected_at_utc": "2026-07-27T15:00:00Z",
        "data_origin": "human_observed",
    }


def test_human_rating_validator_accepts_contract_and_rejects_pii_scales_and_unknown_items(tmp_path: Path) -> None:
    item_id = _rows(families=1, configs=1, variants=1)[0]["item_id"]
    path = tmp_path / "ratings.jsonl"
    path.write_text(json.dumps(_valid_rating(item_id)) + "\n", encoding="utf-8")
    assert validate_human_ratings(path, known_item_ids={item_id})["ok"] is True

    invalid = _valid_rating(item_id)
    invalid["email"] = "person@example.com"
    invalid["funniness"] = 8
    invalid["item_id"] = "oc_" + "f" * 24
    invalid["collected_at_utc"] = "2026-07-27T15:00:00"
    path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
    receipt = validate_human_ratings(path, known_item_ids={item_id})
    assert receipt["ok"] is False
    reasons = receipt["errors"][0]["reasons"]
    assert "direct_identity_field_forbidden" in reasons
    assert "funniness_must_be_integer_1_to_7" in reasons
    assert "unknown_item_id" in reasons
    assert "collected_at_utc_must_be_timezone_aware" in reasons


def test_human_contribution_validator_requires_authorship_cc0_and_no_identity(tmp_path: Path) -> None:
    valid = {
        "contribution_id": "contrib_0001",
        "text": "A project-controlled original contribution.",
        "contributor_key": "author_ab12cd34",
        "language": "en",
        "authorship_attestation": True,
        "cc0_affirmation": True,
        "consent_version": "v1",
        "submitted_at_utc": "2026-07-27T16:00:00+00:00",
        "data_origin": "human_original",
        "human_authored": True,
    }
    path = tmp_path / "contributions.jsonl"
    path.write_text(json.dumps(valid) + "\n", encoding="utf-8")
    assert validate_human_contributions(path)["ok"] is True
    valid["authorship_attestation"] = False
    valid["name"] = "Direct Identity"
    path.write_text(json.dumps(valid) + "\n", encoding="utf-8")
    receipt = validate_human_contributions(path)
    assert receipt["ok"] is False
    assert "authorship_and_cc0_affirmations_required" in receipt["errors"][0]["reasons"]
    assert "direct_identity_field_forbidden" in receipt["errors"][0]["reasons"]


def test_all_schemas_have_strict_origin_and_no_placeholder_examples() -> None:
    assert row_schema()["additionalProperties"] is False
    assert human_rating_schema()["properties"]["data_origin"]["const"] == "human_observed"
    assert human_contribution_schema()["properties"]["cc0_affirmation"]["const"] is True
    candidate = model_candidate_schema()
    assert candidate["properties"]["release_status"]["const"] == "quarantined"
    assert candidate["properties"]["human_authored"]["const"] is False


def test_model_candidate_validator_preserves_provenance_and_quarantine(tmp_path: Path) -> None:
    valid = {
        "candidate_id": "candidate_0001",
        "text": "A quarantined model candidate.",
        "provider": "ollama",
        "model_id": "gemma3:4b",
        "model_version": "sha256:abc123",
        "prompt_sha256": "d" * 64,
        "generation_parameters": {"temperature": 0.7, "seed": 42},
        "generated_at_utc": "2026-07-27T17:00:00Z",
        "data_origin": "model_generated_candidate",
        "human_authored": False,
        "release_status": "quarantined",
    }
    path = tmp_path / "model.jsonl"
    path.write_text(json.dumps(valid) + "\n", encoding="utf-8")
    receipt = validate_model_candidates(path)
    assert receipt["ok"] is True and receipt["release_status"] == "quarantined"

    valid["generation_parameters"] = {"api_key": "must-not-ship"}
    valid["release_status"] = "public"
    valid["human_authored"] = True
    path.write_text(json.dumps(valid) + "\n", encoding="utf-8")
    receipt = validate_model_candidates(path)
    assert receipt["ok"] is False
    reasons = receipt["errors"][0]["reasons"]
    assert "generation_parameters_must_not_contain_secrets" in reasons
    assert "release_status_must_be_quarantined" in reasons
    assert "human_authored_must_be_false" in reasons


def test_sample_api_is_bounded_deterministic_and_model_free() -> None:
    first = sample_rows(4, seed=DEFAULT_SEED, arm="surprising_resolved", split="test")
    assert first == sample_rows(4, seed=DEFAULT_SEED, arm="surprising_resolved", split="test")
    assert len(first) == 4
    assert all(row["counterfactual_arm"] == "surprising_resolved" and row["split"] == "test" for row in first)
    with pytest.raises(ValueError, match="between 1 and 64"):
        sample_rows(65)

    service = HumorVibesService()
    payload = service.open_controls_sample(count=3, arm="expected_literal", split="validation")
    assert payload["count"] == 3
    assert payload["truth_boundary"]["model_generated"] is False
    assert service.open_controls_metadata()["maximum_rows"] == 120_000


def test_small_release_build_and_independent_verifier(tmp_path: Path) -> None:
    out = tmp_path / "release"
    receipt = builder.build(
        out_dir=out,
        families=12,
        configs=3,
        variants=2,
        seed=DEFAULT_SEED,
        generator_commit="c" * 40,
        metadata_template=ROOT / "open_controls_dataset" / "dataset-metadata.json",
        parquet=False,
    )
    assert receipt["ok"] is True and receipt["rows"] == 288
    assert validate_manifest(out)["ok"] is True
    verified = verify(out)
    assert verified["ok"] is True
    assert verified["rows"] == 288
    assert verified["checks"]["published_audit_matches"] is True

    # Kaggle consumes its reserved upload-control file. A fresh download must
    # remain independently verifiable without that non-payload file.
    (out / "dataset-metadata.json").unlink()
    verified_download = verify(out)
    assert verified_download["ok"] is True
    assert verified_download["checks"]["public_kaggle_metadata"] is True

    with (out / "DATASET_CARD.md").open("a", encoding="utf-8") as fh:
        fh.write("tampered\n")
    assert verify(out)["ok"] is False


def test_notebook_builder_is_deterministic_and_every_code_cell_compiles(tmp_path: Path) -> None:
    subprocess.run([sys.executable, "open_controls_notebook/build_open_controls_notebook.py"], cwd=ROOT, check=True)
    path = ROOT / "open_controls_notebook" / "humor_genome_open_controls.ipynb"
    first = path.read_bytes()
    subprocess.run([sys.executable, "open_controls_notebook/build_open_controls_notebook.py"], cwd=ROOT, check=True)
    assert path.read_bytes() == first
    notebook = json.loads(first)
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 12
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), str(path), "exec")
    markdown = "\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown")
    assert "Executive summary" in markdown
    assert "What can it not conclude?" in markdown
    assert "Human-response" not in markdown or "human" in markdown.lower()


def test_public_metadata_licences_and_docs_are_present() -> None:
    metadata = json.loads((ROOT / "open_controls_dataset" / "dataset-metadata.json").read_text(encoding="utf-8"))
    kernel = json.loads((ROOT / "open_controls_notebook" / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "taylorsamarel/humor-genome-open-controls"
    assert metadata["licenses"] == [{"name": "CC0-1.0"}]
    assert metadata["isPrivate"] is False
    assert kernel["is_private"] is False and kernel["enable_internet"] is False
    assert kernel["dataset_sources"] == [metadata["id"]]
    assert (ROOT / "LICENSE").is_file()
    assert "Apache License" in (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "CC0-1.0" in (ROOT / "LICENSE-DATA-OPEN-CONTROLS").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "OPEN_CONTROLS.md").is_file()
    assert (ROOT / "docs" / "figures" / "open-controls-evidence-lanes.svg").is_file()


def test_committed_sample_is_rebuildable_complete_and_audited() -> None:
    path = ROOT / "open_controls_dataset" / "sample_open_controls.jsonl"
    before = path.read_bytes()
    subprocess.run([sys.executable, "open_controls_dataset/build_sample.py"], cwd=ROOT, check=True)
    assert path.read_bytes() == before
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 32
    assert {row["counterfactual_arm"] for row in rows} == set(COUNTERFACTUAL_ARMS)
    assert {row["surface_variant"] for row in rows} == {0, 1}
    report, _ = audit_rows(rows)
    assert report["ok"] is True
