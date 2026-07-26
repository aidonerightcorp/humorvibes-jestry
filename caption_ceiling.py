#!/usr/bin/env python3
"""How well can ANY model score on this corpus? The label's own reliability.

Every prediction number in this project has been reported against an implicit
ceiling of 1.0. That ceiling is wrong. A caption's published funniness is a mean
over a finite number of crowd votes, so it carries sampling error, and no
predictor — perfect or otherwise — can correlate with a noisy measurement better
than a second independent measurement of the same thing does.

The caption corpus is the first one here that can measure this, because it ships
the raw vote breakdown per caption (not_funny / somewhat_funny / funny) rather
than only a mean. Two independent estimates:

* **SPLIT-HALF (non-parametric).** Deal each caption's own votes into two
  disjoint halves at random and average each half. Two honest measurements of
  the same caption from the same rater pool. Their Spearman across the captions
  of one contest IS the reliability of a half-length label; Spearman-Brown
  restores it to full length. Nothing is assumed about the vote distribution.
* **ANALYTIC (parametric).** The sampling variance of each caption's mean under
  a multinomial with the observed proportions, divided by the observed spread of
  means within the contest. Different assumptions entirely, so agreement between
  the two is evidence and disagreement is a warning.

From reliability r, a perfect predictor of the true funniness correlates with
the published mean at about sqrt(r) — the classical attenuation bound. It is
stated as an approximation here because it is derived for Pearson correlation
and this project reports Spearman.

Everything is computed WITHIN contest. The drawing changes between contests, and
so does the vote scale, so a pooled correlation partly measures which contest a
caption came from — which is not what anyone means by predicting funniness.

    python3 caption_ceiling.py                    # full run
    python3 caption_ceiling.py --max-contests 20  # quick pass
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import caption_corpus as cc
from humor_features import spearman

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
MIN_VOTES = 20          # 95% of the corpus clears this
MIN_CAPTIONS = 200      # per contest, after filtering


def clean(df):
    """Keep only rows whose counts and published mean tell the same story.

    Measured 2026-07-26: 27,829 rows (1.3%) carry a mean that its own vote
    counts cannot produce, and 7,061 have a `votes` field disagreeing with the
    sum of the counts — the count vector and the mean column were written from
    different snapshots of a live contest. Since this study resamples the COUNTS,
    a row whose mean does not follow from them is not usable, in either
    direction: it would corrupt the split-half arm and the analytic arm alike.
    """
    C = cc.counts_matrix(df)
    tot = C.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        recomputed = (C * cc.SCALE).sum(axis=1) / np.where(tot > 0, tot, np.nan)
    ok = (np.abs(tot - df["votes"].to_numpy()) < 0.5)
    ok &= np.isfinite(recomputed)
    ok &= np.abs(recomputed - df["mean_harvest"].to_numpy()) < 1e-6
    ok &= tot >= MIN_VOTES
    return df[ok].copy(), int((~ok).sum())


def split_half(C: np.ndarray, rng: np.random.Generator):
    """Deal each caption's votes into two disjoint halves (multivariate
    hypergeometric), and return the two half-means."""
    n1, n2, n3 = C[:, 0].astype(np.int64), C[:, 1].astype(np.int64), C[:, 2].astype(np.int64)
    n = n1 + n2 + n3
    h = n // 2
    a1 = rng.hypergeometric(np.maximum(n1, 0), np.maximum(n - n1, 0), h)
    rem_good = np.maximum(n2, 0)
    rem_bad = np.maximum(n - n1 - n2, 0)
    take = h - a1
    a2 = np.zeros_like(a1)
    m = (take > 0) & ((rem_good + rem_bad) > 0)
    a2[m] = rng.hypergeometric(rem_good[m], rem_bad[m], np.minimum(take[m], (rem_good + rem_bad)[m]))
    a3 = h - a1 - a2
    b1, b2, b3 = n1 - a1, n2 - a2, n3 - a3
    nb = n - h
    mean_a = (a1 + 2 * a2 + 3 * a3) / np.where(h > 0, h, 1)
    mean_b = (b1 + 2 * b2 + 3 * b3) / np.where(nb > 0, nb, 1)
    keep = (h > 0) & (nb > 0)
    return mean_a, mean_b, keep


def analytic_reliability(C: np.ndarray) -> tuple[float, float]:
    """(mean sampling variance, variance of the observed means) for one contest."""
    n = C.sum(axis=1)
    p = C / n[:, None]
    ex = (p * cc.SCALE).sum(axis=1)
    ex2 = (p * cc.SCALE ** 2).sum(axis=1)
    var_i = np.maximum(ex2 - ex ** 2, 0.0) / n          # sampling var of each mean
    return float(np.mean(var_i)), float(np.var(ex, ddof=1))


def spearman_brown(r: float, factor: float = 2.0) -> float:
    if r <= -1:
        return r
    return factor * r / (1 + (factor - 1) * r)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-contests", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260726)
    a = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(a.seed)

    df = cc.load()
    df, dropped = clean(df)
    print(f"usable captions {len(df):,} (dropped {dropped:,} for vote/mean "
          f"inconsistency or < {MIN_VOTES} votes)")

    groups = [(c, g) for c, g in df.groupby("contest", observed=True) if len(g) >= MIN_CAPTIONS]
    if a.max_contests:
        groups = groups[:a.max_contests]
    print(f"contests used: {len(groups)}")

    rows = []
    for contest, g in groups:
        C = cc.counts_matrix(g)
        ma, mb, keep = split_half(C, rng)
        if keep.sum() < MIN_CAPTIONS:
            continue
        r_half = spearman(list(ma[keep]), list(mb[keep]))
        r_full = spearman_brown(r_half)
        # The analytic estimate is a variance ratio, i.e. Pearson-scaled, so a
        # gap against the rank-based split-half is expected rather than a fault
        # in either. Computing the split-half BOTH ways settles which it is.
        p_half = float(np.corrcoef(ma[keep], mb[keep])[0, 1])
        p_full = spearman_brown(p_half)
        var_e, var_o = analytic_reliability(C[keep])
        rel_analytic = max(0.0, 1.0 - var_e / var_o) if var_o > 0 else float("nan")
        rows.append({
            "contest": str(contest), "n_captions": int(keep.sum()),
            "median_votes": float(np.median(C[keep].sum(axis=1))),
            "split_half_spearman": r_half,
            "reliability_split_half": r_full,
            "reliability_split_half_pearson": p_full,
            "reliability_analytic": rel_analytic,
            "ceiling_split_half": float(np.sqrt(max(r_full, 0.0))),
            "ceiling_analytic": float(np.sqrt(max(rel_analytic, 0.0))),
        })

    rel_sh = np.array([r["reliability_split_half"] for r in rows])
    rel_sp = np.array([r["reliability_split_half_pearson"] for r in rows])
    rel_an = np.array([r["reliability_analytic"] for r in rows])
    ceil_sh = np.array([r["ceiling_split_half"] for r in rows])
    votes_med = np.array([r["median_votes"] for r in rows])

    print(f"\n{'':<26}{'median':>9}{'p10':>9}{'p90':>9}")
    for name, arr in (("reliability sh (rank)", rel_sh),
                      ("reliability sh (value)", rel_sp),
                      ("reliability analytic", rel_an),
                      ("CEILING on spearman", ceil_sh)):
        print(f"{name:<26}{np.median(arr):>9.3f}{np.percentile(arr, 10):>9.3f}"
              f"{np.percentile(arr, 90):>9.3f}")
    agree = float(np.median(np.abs(rel_sh - rel_an)))
    agree_like = float(np.median(np.abs(rel_sp - rel_an)))
    print(f"\nrank split-half vs analytic differ by a median of {agree:.3f}; "
          f"comparing like with like (value split-half vs analytic, both "
          f"Pearson-scaled) the gap is {agree_like:.3f}")

    # how the ceiling moves with vote count — the actionable part: it says how
    # many votes a future rated corpus needs before a model can be judged.
    bins = [(20, 50), (50, 100), (100, 200), (200, 10 ** 9)]
    by_votes = []
    for lo, hi in bins:
        m = (votes_med >= lo) & (votes_med < hi)
        if m.sum() < 3:
            continue
        by_votes.append({"median_votes_lo": lo, "median_votes_hi": hi,
                         "contests": int(m.sum()),
                         "reliability": float(np.median(rel_sh[m])),
                         "ceiling": float(np.median(ceil_sh[m]))})
    print(f"\n{'votes/caption':<18}{'contests':>9}{'reliability':>13}{'ceiling':>9}")
    for b in by_votes:
        lab = f"{b['median_votes_lo']}-{b['median_votes_hi'] if b['median_votes_hi'] < 10**9 else '+'}"
        print(f"{lab:<18}{b['contests']:>9}{b['reliability']:>13.3f}{b['ceiling']:>9.3f}")

    report = {
        "receipt_type": "caption_label_ceiling",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": "what is the highest spearman any predictor can reach against "
                    "this corpus's published funniness, given the label is a mean "
                    "over a finite vote sample?",
        "protocol": {
            "scope": "within contest; the drawing and the vote scale are held fixed",
            "min_votes_per_caption": MIN_VOTES,
            "min_captions_per_contest": MIN_CAPTIONS,
            "split_half": "votes dealt into two disjoint halves per caption "
                          "(multivariate hypergeometric), Spearman across captions, "
                          "Spearman-Brown to full length",
            "analytic": "multinomial sampling variance of each caption mean over the "
                        "observed within-contest variance of means",
            "ceiling": "sqrt(reliability) — the classical attenuation bound, derived "
                       "for Pearson and applied here to Spearman as an approximation",
            "seed": a.seed,
        },
        "n_captions_used": int(len(df)),
        "n_captions_dropped": dropped,
        "n_contests": len(rows),
        "headline": {
            "median_reliability_split_half": float(np.median(rel_sh)),
            "median_reliability_analytic": float(np.median(rel_an)),
            "median_ceiling": float(np.median(ceil_sh)),
            "p10_ceiling": float(np.percentile(ceil_sh, 10)),
            "p90_ceiling": float(np.percentile(ceil_sh, 90)),
            "median_abs_disagreement_between_estimators": agree,
        },
        "by_vote_count": by_votes,
        "per_contest": rows,
        "runtime_s": round(time.time() - t0, 1),
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "caption_ceiling.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nreceipt -> jestry_out/caption_ceiling.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
