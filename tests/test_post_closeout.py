"""Regression tests for the post-closeout wave-1 receipts, figures, and docs.

Network-free and corpus-free: everything asserted here reads committed files.
Pins are EXACT where documents quote exact numbers (2026-07-28 referee round:
loose bands let quoted claims drift silently). If a study is rerun and a number
legitimately moves, the receipt, these pins, and every document quoting the
number must change together — that coupling is the point.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    # docs quote p = 0.45; the study is seeded and deterministic
    assert f["any_difference_among_styles_permutation_p"] == pytest.approx(0.44988)
    assert "control is not part" in f["permutation_note"]

    # the power analysis is the finding (referee round): the criterion could
    # not have fired, and the receipt must keep saying so
    crit = f["separation_criterion"]
    assert crit["could_have_fired_at_this_n"] is False
    assert crit["largest_observed_group_ci_low"] < crit["requires_group_ci_low_above"]
    assert "underpowered" in d["verdict"].lower()
    assert f["length_confound"]["pearson_mean_tokens_vs_mean_S_across_groups"] == pytest.approx(-0.631)

    # screening must show pre-filter counts, not survivors only
    s = d["screening"]
    assert s["candidates_after_screen_all_styles"]["legal"] == 10
    assert s["candidates_after_screen_all_styles"]["medical"] == 9
    assert set(s["styles_dropped_below_threshold"]) == {"legal", "medical"}
    assert len(d["groups"]) == 7
    for stats in d["groups"].values():
        assert stats["n"] == 12
        assert all(len(h) == 16 for h in stats["item_hashes"])
    text = json.dumps(d)
    assert "[deleted]" not in text and "[removed]" not in text


def test_divisiveness_receipt_pins() -> None:
    d = load("divisiveness_study.json")
    assert d["status"] == "complete"
    s = d["screening"]
    assert s["rows_raw"] == 2_186_939
    assert s["dropped_count_mismatch"] == 7_061
    assert s["dropped_mean_mismatch"] == 5_544
    assert s["kept_votes_ge_20"] == 2_068_094

    overall = d["label_reliability"]["overall"]
    # docs quote ~0.51 (conflict) vs ~0.67 (mean); SB only over positive-r
    assert overall["conflict"]["median_spearman_brown"] == pytest.approx(0.512, abs=1e-4)
    assert overall["mean"]["median_spearman_brown"] == pytest.approx(0.6686, abs=1e-4)
    assert overall["mean"]["median_raw_split_half"] is not None
    for which in ("mean", "conflict", "entropy"):
        assert overall[which]["estimable"] is True

    # referee round: SB is invalid for non-positive r — the 40-80 bin must be
    # marked not estimable, never published as a negative "reliability"
    low_bin = d["label_reliability"]["by_vote_bin"]["40-80"]
    for which in ("mean", "conflict", "entropy"):
        assert low_bin[which]["estimable"] is False
        assert low_bin[which]["median_spearman_brown"] is None

    # vote bins are outcome strata; the coupling that makes them so is receipted
    assert d["votes_mean_within_contest_spearman_median"] > 0.9
    assert "vote_bins_are_outcome_strata" in d["reliability_caveats"]
    assert "disjoint_split_downward_bias" in d["reliability_caveats"]

    ratios = d["predicted_over_ceiling"]
    assert ratios["mean"] == pytest.approx(0.1855, abs=1e-4)
    assert ratios["conflict"] == pytest.approx(0.1732, abs=1e-4)
    assert "population" in d["predicted_over_ceiling_note"]
    assert "not_verified" in d["truth_boundary"]


def test_demographic_norms_receipt_pins() -> None:
    d = load("demographic_norms_study.json")
    agree = d["cross_dataset_overall_agreement"]
    assert agree["shared_words"] == 4_739
    assert agree["spearman_mean_vs_p_funny"] == pytest.approx(0.4141, abs=1e-4)

    gaps = d["engelthaler_gaps"]
    # referee round: Welch t, not normal z — docs quote 2/4,997 and 0/4,997
    assert gaps["sex"]["test"].startswith("Welch")
    assert gaps["sex"]["significant_q05"] == 2
    assert gaps["age"]["significant_q05"] == 0
    assert gaps["sex"]["implied_per_word_gap_reliability"] < 0.1
    assert gaps["age"]["implied_per_word_gap_reliability"] == 0.0
    # ranked word lists are reliability-zero noise and must never come back
    assert "top_positive" not in gaps["sex"] and "top_negative" not in gaps["sex"]

    cross = d["cross_dataset_gap_agreement"]
    for gap in ("sex_gap", "age_gap"):
        assert "no attainable measurement" in cross[gap]["measurement_verdict"]
        assert "attenuation_ceiling" in cross[gap]
    assert "direction_note" in cross["age_gap"]

    hyp = d["hand_coded_dimension_gap_tests"]
    assert hyp["bh_family_size"] == 12
    top = hyp["rows"][0]
    assert (top["dimension"], top["target"]) == ("sexc", "age_gap")
    assert top["q_bh"] < 0.01
    imp = d["persona_b_implication"]
    assert "NOT DETECTABLE" in imp.upper()


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
    # referee round: the atlas is a corpus map, and says so; no operator paths
    assert "caveat" in d["atlas"]
    assert "/home/" not in json.dumps(d)
    # every displayed value is cross-checked against its source receipt
    ceil = load("caption_ceiling.json")["headline"]["median_ceiling"]
    bound = load("caption_portability.json")["results"]["text_only_predictor_bound"]
    model = load("caption_model.json")["results"]["within_contest_median_spearman"]
    assert abs(d["waterfall"]["ceiling"] - ceil) < 1e-12
    assert abs(d["waterfall"]["bound"] - bound) < 1e-12
    assert abs(d["waterfall"]["model"] - model) < 1e-12


def test_notebook_refresh_receipt() -> None:
    d = load("notebook_refresh_publication.json")
    k = d["kernels"]
    assert k["wave2"]["terminal_status"] == "COMPLETE"
    assert k["wave2"]["in_run_instrument"]["agreement"] is True
    assert k["wave2"]["in_run_form_study"]["strictly_above_control"] == 0
    assert k["open_controls"]["terminal_status"] == "COMPLETE"
    assert k["ceiling_demo"]["terminal_status"] == "COMPLETE"
    assert k["ceiling_demo"]["version_pushed"] >= 4
    assert k["ceiling_demo"]["served_source_matches_committed_cells"] is True
    assert d["source_tag"]["name"] == "humor-genome-wave2-v10"


def test_thesis_doc_matches_receipts() -> None:
    """The scoreboard's quoted values must exist AND match the receipts —
    a substring check alone lets a rerun leave the doc stale."""
    text = (ROOT / "docs" / "THESIS_AND_EVIDENCE.md").read_text()
    for needle in (
        "0.8262",
        "punch_rarity_max",
        "0.1555",
        "ρ = 0.033",
        "0/7",
        "Underpowered — separation not established",
        "Not detectable at these per-word n",
        "2/4,997",
        "surprise-reduction engine",
        "supersedes no",
    ):
        assert needle in text, f"THESIS_AND_EVIDENCE.md lost canonical marker: {needle}"
    declared = load("declared_style_study.json")
    p = declared["findings"]["any_difference_among_styles_permutation_p"]
    assert f"p = {round(p, 2)}" in text
    demo = load("demographic_norms_study.json")
    assert f"{demo['engelthaler_gaps']['sex']['significant_q05']}/4,997" in text
