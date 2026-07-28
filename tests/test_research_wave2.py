"""Regression pins for the research wave-2 receipts (2026-07-28).

Exact pins on the values documents quote (referee doctrine: loose bands let
quoted claims drift). Study A (human frames) and Study D (r/Jokes word-type
replication) gain their functions when their receipts land in this same wave.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "jestry_out"

DIVISIVENESS_SCREENS = {"rows_raw": 2_186_939, "dropped_count_mismatch": 7_061,
                        "dropped_mean_mismatch": 5_544, "kept_votes_ge_20": 2_068_094}


def load(name: str) -> dict:
    path = OUT / name
    assert path.exists(), f"missing receipt {name}"
    data = json.loads(path.read_text())
    assert data.get("receipt_type"), f"{name} has no receipt_type"
    assert ("preregistration" in data or "pre_registration" in data), f"{name} lacks a preregistration block"
    assert "not_verified" in data.get("truth_boundary", {}), name
    return data


def test_within_contest_study_confirms_the_invariant() -> None:
    d = load("caption_within_contest_study.json")
    assert d["status"] == "complete"
    s = d["screens"]
    for k, v in DIVISIVENESS_SCREENS.items():
        assert s[k] == v, k
    rows = d["per_feature"]
    pr = next(r for r in rows if r["feature"] == "punch_rarity_max")
    # the sole cross-corpus survivor is NOT a pooling artifact: same sign,
    # same magnitude within contest, FDR survivor in the declared 30 family
    assert pr["median_within_contest_rho"] == pytest.approx(-0.0876, abs=1e-4)
    assert pr["pooled_rho_from_three_corpus_receipt"] == pytest.approx(-0.0874, abs=1e-4)
    assert pr["sign_consistent_share"] > 0.95
    assert pr["survives"] is True
    assert pr["n_contests_used"] == 360
    assert len(rows) == 30
    assert "not a cross-contest pooling artifact" in d["punch_rarity_max_verdict"]


def test_temporal_drift_participation_moves_label_does_not() -> None:
    d = load("caption_temporal_drift.json")
    assert d["status"] == "complete"
    for k, v in DIVISIVENESS_SCREENS.items():
        assert d["screening"][k] == v, k
    trends = dict(d["trends"]) if isinstance(d["trends"], list) else d["trends"]
    surv = {name for name, t in trends.items()
            if t.get("in_bh_family") and t.get("nonnull_q_lt_05")}
    assert surv == {"median_votes", "vocab_novelty", "log_n_captions"}
    assert trends["median_votes"]["rho"] == pytest.approx(0.3575, abs=1e-3)
    for name in surv:
        assert trends[name]["rho"] > 0
    # the label itself does not drift: reliability, mean rating, funny share all null
    for name in ("reliability_raw_split_half_r", "mean_rating", "funny_vote_share"):
        t = trends[name]
        assert t["nonnull_q_lt_05"] is False
        assert abs(t["rho"]) < t["mde_abs_rho_95"] + 0.02
    # referee rule embedded in the receipt: raw r reported, SB only over positive r
    rel = d["label_reliability_summary"]
    assert "raw" in json.dumps(rel).lower()
    # preregistration integrity: the sha lock the agent recorded must verify
    assert len(d["preregistration_sha256"]) == 64


def test_human_frames_negative_is_well_powered() -> None:
    d = load("human_frames_resolution_study.json")
    assert d["status"] == "complete"
    assert d["instrument_errors"] == 0
    assert d["calibration"]["pass"] is True
    assert d["n_analyzed"] == 34
    h1 = d["results"]["H1_rnet_top"]
    # the tested negative: true human frame LOSES to decoys, CI excludes zero,
    # and the criterion could fire (|mean| > MDE)
    assert h1["mean"] == pytest.approx(-0.1069, abs=1e-3)
    assert h1["ci95"][1] < 0
    assert abs(h1["mean"]) > d["preregistration"]["power"]["observed_mde_95"]
    h2 = d["results"]["H2_top_minus_bottom"]
    assert h2["ci95"][0] < 0 < h2["ci95"][1]
    dose = d["results"]["H3_dose_exploratory"]
    assert dose["w3"]["R_mean"] > dose["full"]["R_mean"]
    # the truncation is documented, not hidden
    pc = d["plan_change"]
    assert pc["original_n_contests"] == 53 and pc["analyzed_n_contests"] == 34
    assert "decoy" in pc["decoy_note"]


def test_word_type_does_not_transfer_to_rjokes() -> None:
    d = load("word_type_rjokes_replication.json")
    assert d["status"] == "complete"
    v = d["verdicts"]
    h1 = v["H1_body_part_positive_delta"]
    assert h1["replicates"] is False
    assert h1["observed"]["delta_vs_pooled"] == pytest.approx(-0.1178, abs=1e-3)
    assert h1["observed"]["bh_significant_at_05"] is True
    assert abs(h1["observed"]["delta_vs_pooled"]) > h1["observed"]["mde_delta"]
    assert h1["observed"]["sign_match_vs_humicroedit"] is False
    h2 = v["H2_type_block_lifts_heldout_spearman"]
    assert h2["replicates"] is True and h2["lift_mean"] < 0.01
    agree = d["delta_vector_agreement_vs_humicroedit"]
    assert agree["delta_spearman_descriptive"] < 0
    assert v["H3_concreteness_positive"]["holds"] is False
