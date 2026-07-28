"""Regression tests for the post-closeout wave-1 receipts, figures, and docs.

Network-free and corpus-free: everything asserted here reads committed files.
If a study is rerun and a number legitimately moves, the receipt, these pins,
and the documents quoting the number must change together — that coupling is
the point (evidence rule 8 in CLAUDE_CODE_HANDOFF.md).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "jestry_out"


def load(name: str) -> dict:
    path = OUT / name
    assert path.exists(), f"missing receipt {name}"
    data = json.loads(path.read_text())
    assert data.get("receipt_type"), f"{name} has no receipt_type"
    return data


def test_declared_style_receipt_pins() -> None:
    d = load("declared_style_study.json")
    assert d["status"] == "complete"
    assert d["instrument_errors"] == 0
    cal = d["calibration"]
    assert cal["pass"] is True
    assert cal["measured"]["tokens"] == 10
    assert abs(cal["measured"]["S"] - 3.19) <= cal["tolerance"]
    f = d["findings"]
    assert f["groups_strictly_above_control"] == 0
    assert f["groups_strictly_below_control"] == 0
    assert 0.05 < f["any_difference_permutation_p"] < 1.0
    assert len(d["groups"]) == 7
    for stats in d["groups"].values():
        assert stats["n"] == 12
        lo, hi = stats["ci95"]
        assert lo < stats["mean_S"] < hi
        # aggregates + hashes only — reddit text must never enter this receipt
        assert all(len(h) == 16 for h in stats["item_hashes"])
    assert "not_verified" in d["truth_boundary"]
    text = json.dumps(d)
    assert "[deleted]" not in text and "[removed]" not in text


def test_divisiveness_receipt_pins() -> None:
    d = load("divisiveness_study.json")
    assert d["status"] == "complete"
    s = d["screening"]
    assert s["rows_raw"] == 2_186_939
    assert s["dropped_count_mismatch"] == 7_061
    overall = d["label_reliability"]["overall"]
    # divisiveness is a real label, but LESS reliable than the mean —
    # the honest ordering this study exists to record
    assert overall["conflict"]["median_spearman_brown"] > 0.4
    assert overall["mean"]["median_spearman_brown"] > overall["conflict"]["median_spearman_brown"]
    ratios = d["predicted_over_ceiling"]
    for key in ("mean", "conflict", "entropy"):
        assert 0.05 < ratios[key] < 0.5, "predictability should stay far below ceiling"
    assert "not_verified" in d["truth_boundary"]


def test_demographic_norms_receipt_pins() -> None:
    d = load("demographic_norms_study.json")
    agree = d["cross_dataset_overall_agreement"]
    assert agree["shared_words"] > 4_000
    assert 0.35 < agree["spearman_mean_vs_p_funny"] < 0.5
    gaps = d["engelthaler_gaps"]
    assert gaps["sex"]["words_tested"] == 4_997
    assert gaps["sex"]["significant_q05"] <= 20
    assert gaps["age"]["significant_q05"] == 0
    # the implication must state the mostly-null outcome, not the hyped one
    imp = d["persona_b_implication"]
    assert "WEAK" in imp or "weak" in imp
    assert "mostly" in imp.lower()


def test_ported_word_type_receipt() -> None:
    d = load("word_type_study.json")
    assert d["n_rows"] == 9_652
    lift = d["predictive_lift"]
    assert abs(lift["structural_only"]["held_out_spearman"] - 0.1137) < 1e-9
    assert abs(lift["structural_plus_type"]["held_out_spearman"] - 0.2296) < 1e-9
    body = next(c for c in d["by_semantic_category"] if c["label"] == "body part")
    assert abs(body["delta_vs_pooled"] - 0.2046) < 1e-9
    assert body["perm_p"] <= 0.001


def test_ported_three_corpus_receipt() -> None:
    d = load("three_corpus_study.json")
    survivors = d["consistent_across_all_corpora"]
    assert len(survivors) == 1
    s = survivors[0]
    assert s["feature"] == "punch_rarity_max"
    assert s["all_survive_fdr"] is True
    # the sign is the finding: negative in every corpus
    assert all(v < 0 for v in s["rho"].values())


def test_wave1_figures_exist_and_receipted() -> None:
    d = load("wave1_figures_receipt.json")
    figdir = ROOT / "docs" / "figures"
    for name, min_bytes in (
        ("caption-ceiling-waterfall.svg", 10_000),
        ("cross-corpus-transfer.svg", 10_000),
        ("genome-atlas-languages.png", 100_000),
    ):
        path = figdir / name
        assert path.exists() and path.stat().st_size > min_bytes, name
    assert d["atlas"]["points"] == 23_779
    assert len(d["atlas"]["embeddings_sha256"]) == 64
    # figure values come from receipts, not hand-typed
    ceil = load("caption_ceiling.json")["headline"]["median_ceiling"]
    assert abs(d["waterfall"]["ceiling"] - ceil) < 1e-12


def test_notebook_refresh_receipt() -> None:
    d = load("notebook_refresh_publication.json")
    k = d["kernels"]
    assert k["wave2"]["terminal_status"] == "COMPLETE"
    assert k["wave2"]["in_run_instrument"]["agreement"] is True
    assert k["wave2"]["in_run_form_study"]["strictly_above_control"] == 0
    assert k["open_controls"]["terminal_status"] == "COMPLETE"
    assert k["ceiling_demo"]["terminal_status"] == "COMPLETE"
    assert d["source_tag"]["name"] == "humor-genome-wave2-v10"


def test_thesis_doc_quotes_canonical_numbers() -> None:
    text = (ROOT / "docs" / "THESIS_AND_EVIDENCE.md").read_text()
    for needle in (
        "0.8262",
        "punch_rarity_max",
        "0.1555",
        "ρ = 0.033",
        "0/7",
        "surprise-reduction engine",
        "supersedes no",
    ):
        assert needle in text, f"THESIS_AND_EVIDENCE.md lost canonical marker: {needle}"
