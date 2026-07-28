"""Caption divisiveness study: is the SHAPE of disagreement a better-behaved
target than the mean?

Every prior model in this project predicted the New Yorker caption MEAN rating.
The raw label is a 3-bin vote histogram (not_funny / somewhat / funny), and the
histogram's shape — how strongly a caption splits the room — has never been
used. This study asks two bounded questions on the certified caption index:

1. RELIABILITY — using each caption's own votes (multivariate hypergeometric
   split-half, Spearman–Brown corrected, the same estimator family as the
   published label-ceiling study): how reproducible is a divisiveness statistic
   compared with the mean at matched vote counts? This is the label ceiling for
   the new target.
2. PREDICTABILITY — with whole contests held out (GroupKFold), how well do
   cheap text features predict divisiveness vs the mean?

Divisiveness here is pole conflict ``C = 2*sqrt(p_nf * p_f)`` — 0 when either
pole is empty, 1 when the room splits evenly between "not funny" and "funny".
Normalized 3-bin entropy is reported as a secondary definition.

Truth boundary: this measures rating polarization inside one publication's
caption-contest crowd. It is not offensiveness, not moderation risk, and not a
general "controversy" construct. Caption text is research-only and never enters
the receipt.

Known data-integrity screen (documented 2026-07-26): a slice of rows publishes
a mean their own vote counts cannot produce, or votes != nf+sf+f — those rows
are dropped and counted, never averaged over.

Usage:
    python3 divisiveness_study.py \
        --data-root /path/to/build-with-gemma-humor-genome-nyc \
        --out jestry_out/divisiveness_study.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold

VOTE_BINS = [(40, 80), (80, 160), (160, 100_000)]


def conflict(nf: np.ndarray, f: np.ndarray, votes: np.ndarray) -> np.ndarray:
    p_nf = nf / votes
    p_f = f / votes
    return 2.0 * np.sqrt(p_nf * p_f)


def entropy3(nf: np.ndarray, sf: np.ndarray, f: np.ndarray, votes: np.ndarray) -> np.ndarray:
    out = np.zeros_like(votes, dtype=np.float64)
    for arr in (nf, sf, f):
        p = arr / votes
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(p > 0, p * np.log(p), 0.0)
        out -= term
    return out / np.log(3.0)


def stat_from_counts(counts: np.ndarray, which: str) -> float:
    v = counts.sum()
    if v == 0:
        return 0.0
    nf, sf, f = counts.astype(np.float64)
    if which == "mean":
        return float((1 * nf + 2 * sf + 3 * f) / v)
    if which == "conflict":
        return float(2.0 * np.sqrt((nf / v) * (f / v)))
    if which == "entropy":
        h = 0.0
        for c in (nf, sf, f):
            p = c / v
            if p > 0:
                h -= p * np.log(p)
        return float(h / np.log(3.0))
    raise ValueError(which)


def split_half_reliability(df: pd.DataFrame, rng: np.random.Generator,
                           sample_cap: int, min_per_contest: int) -> dict:
    elig = df[df["votes"] >= 40]
    if len(elig) > sample_cap:
        elig = elig.sample(n=sample_cap, random_state=int(rng.integers(0, 2**31)))
    halves: dict[str, list] = {"mean": [], "conflict": [], "entropy": []}
    contests, bins = [], []
    counts_mat = elig[["nf", "sf", "f"]].to_numpy(dtype=np.int64)
    votes = elig["votes"].to_numpy(dtype=np.int64)
    contest_arr = elig["contest"].to_numpy()
    for i in range(len(elig)):
        total = counts_mat[i]
        half_n = int(votes[i] // 2)
        a = rng.multivariate_hypergeometric(total, half_n)
        b = total - a
        row = {}
        for which in halves:
            row[which] = (stat_from_counts(a, which), stat_from_counts(b, which))
        for which, pair in row.items():
            halves[which].append(pair)
        contests.append(contest_arr[i])
        v = votes[i]
        bins.append(next((idx for idx, (lo, hi) in enumerate(VOTE_BINS) if lo <= v < hi),
                         len(VOTE_BINS) - 1))
    frame = pd.DataFrame({
        "contest": contests, "bin": bins,
        **{f"{w}_a": [p[0] for p in halves[w]] for w in halves},
        **{f"{w}_b": [p[1] for p in halves[w]] for w in halves},
    })

    def summarize(sub: pd.DataFrame) -> dict:
        """Per-contest split-half r, Spearman-Brown ONLY where r > 0.

        SB (2r/(1+r)) is a reliability correction for parallel halves and is
        meaningless (and explosively wrong) for r <= 0 — applying it to the
        low-vote bins produced sign-flipped, magnitude-amplified artifacts
        (referee finding, 2026-07-28). Raw medians are always reported; SB is
        reported only over the positive-r contests, and a bin whose raw median
        is not positive is marked not estimable. The complementary (disjoint)
        split is also biased DOWNWARD relative to independent half-samples
        under range restriction; that bias note travels with the receipt.
        """
        out = {}
        for which in ("mean", "conflict", "entropy"):
            raw = []
            for _, grp in sub.groupby("contest"):
                if len(grp) < min_per_contest:
                    continue
                r = spearmanr(grp[f"{which}_a"], grp[f"{which}_b"]).statistic
                if np.isfinite(r):
                    raw.append(float(r))
            pos = [r for r in raw if r > 0]
            med_raw = float(np.median(raw)) if raw else None
            estimable = bool(med_raw is not None and med_raw > 0)
            out[which] = {
                "median_raw_split_half": round(med_raw, 4) if med_raw is not None else None,
                "median_spearman_brown": (
                    round(float(np.median([2 * r / (1 + r) for r in pos])), 4)
                    if estimable and pos else None),
                "iqr_raw": [round(float(np.percentile(raw, 25)), 4),
                            round(float(np.percentile(raw, 75)), 4)] if raw else None,
                "contests": len(raw),
                "contests_negative_r": len(raw) - len(pos),
                "estimable": estimable,
            }
            if not estimable:
                out[which]["note"] = ("not estimable at this vote count: the raw "
                                       "split-half median is <= 0 (outcome-conditioned "
                                       "stratum + disjoint-split downward bias), so no "
                                       "Spearman-Brown value is reported")
        return out

    result = {"overall": summarize(frame), "by_vote_bin": {}}
    for idx, (lo, hi) in enumerate(VOTE_BINS):
        sub = frame[frame["bin"] == idx]
        label = f"{lo}-{hi if hi < 100_000 else 'plus'}"
        result["by_vote_bin"][label] = {"captions": int(len(sub)), **summarize(sub)}
    result["captions_sampled"] = int(len(frame))
    return result


def heldout_predictability(df: pd.DataFrame, rng: np.random.Generator,
                           per_contest_cap: int, total_cap: int,
                           min_contest_rows: int) -> dict:
    sizes = df.groupby("contest").size()
    keep_contests = sizes[sizes >= min_contest_rows].index
    work = df[df["contest"].isin(keep_contests)]
    # pandas 3.x excludes the grouping column from groupby.apply results, so
    # sample per contest explicitly and keep every column.
    parts = []
    for _, grp in work.groupby("contest", sort=True):
        take = min(len(grp), per_contest_cap)
        parts.append(grp.sample(n=take, random_state=int(rng.integers(0, 2**31))))
    work = pd.concat(parts, ignore_index=True)
    if len(work) > total_cap:
        work = work.sample(n=total_cap, random_state=int(rng.integers(0, 2**31)))
    work = work.reset_index(drop=True)

    texts = work["text"].fillna("").astype(str).to_numpy()
    groups = work["contest"].to_numpy()
    vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                            n_features=2**18, alternate_sign=False, norm="l2")
    X = vec.transform(texts)
    lengths_raw = np.column_stack([
        [len(t) for t in texts],
        [t.count(" ") + 1 for t in texts],
        [t.count('"') + t.count("'") for t in texts],
    ]).astype(np.float64)

    targets = {
        "mean": work["mean_exact"].to_numpy(),
        "conflict": work["conflict"].to_numpy(),
        "entropy": work["entropy"].to_numpy(),
    }
    out: dict[str, dict] = {}
    gkf = GroupKFold(n_splits=5)
    for name, y in targets.items():
        per_contest_r: dict[str, list[float]] = {"text": [], "length_only": []}
        for tr, te in gkf.split(X, y, groups):
            # standardize length features on the TRAIN fold only (no test leakage)
            mu, sd = lengths_raw[tr].mean(axis=0), lengths_raw[tr].std(axis=0) + 1e-9
            len_tr = (lengths_raw[tr] - mu) / sd
            len_te = (lengths_raw[te] - mu) / sd
            for feat_name, model, Xtr, Xte in (
                ("text", Ridge(alpha=2.0, solver="sparse_cg"), X[tr], X[te]),
                ("length_only", Ridge(alpha=2.0), len_tr, len_te),
            ):
                model.fit(Xtr, y[tr])
                pred = model.predict(Xte)
                fold = pd.DataFrame({"contest": groups[te], "y": y[te], "p": pred})
                for _, grp in fold.groupby("contest"):
                    if len(grp) < 50:
                        continue
                    r = spearmanr(grp["y"], grp["p"]).statistic
                    if np.isfinite(r):
                        per_contest_r[feat_name].append(float(r))
        out[name] = {
            feat: {
                "median_within_contest_spearman": round(float(np.median(rs)), 4) if rs else None,
                "iqr": [round(float(np.percentile(rs, 25)), 4),
                        round(float(np.percentile(rs, 75)), 4)] if rs else None,
                "contest_folds": len(rs),
            }
            for feat, rs in per_contest_r.items()
        }
    out["rows_used"] = int(len(work))
    out["contests_used"] = int(work["contest"].nunique())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=".")
    ap.add_argument("--out", default="jestry_out/divisiveness_study.json")
    ap.add_argument("--seed", type=int, default=20260727)
    ap.add_argument("--reliability-cap", type=int, default=150_000)
    ap.add_argument("--per-contest-cap", type=int, default=1_200)
    ap.add_argument("--total-cap", type=int, default=240_000)
    args = ap.parse_args()

    parquet = Path(args.data_root) / "data_cache" / "caption_index.parquet"
    if not parquet.exists():
        raise SystemExit(f"missing {parquet} — build it with caption_corpus.py first")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    df = pd.read_parquet(parquet, columns=["contest", "text", "votes", "nf", "sf", "f",
                                           "mean_harvest"])
    n_raw = len(df)
    for col in ("votes", "nf", "sf", "f"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["votes", "nf", "sf", "f", "text"])
    df = df[(df["votes"] > 0) & (df["nf"] >= 0) & (df["sf"] >= 0) & (df["f"] >= 0)]
    consistent_counts = df["votes"] == df["nf"] + df["sf"] + df["f"]
    n_count_mismatch = int((~consistent_counts).sum())
    df = df[consistent_counts]
    df["mean_exact"] = (1 * df["nf"] + 2 * df["sf"] + 3 * df["f"]) / df["votes"]
    mean_ok = (df["mean_harvest"].isna()) | ((df["mean_exact"] - df["mean_harvest"]).abs() <= 0.02)
    n_mean_mismatch = int((~mean_ok).sum())
    df = df[mean_ok]
    df = df[df["votes"] >= 20]
    n_screened = len(df)
    df["conflict"] = conflict(df["nf"].to_numpy(), df["f"].to_numpy(),
                              df["votes"].to_numpy())
    df["entropy"] = entropy3(df["nf"].to_numpy(), df["sf"].to_numpy(),
                             df["f"].to_numpy(), df["votes"].to_numpy())

    print(f"rows raw={n_raw} kept={n_screened} count_mismatch={n_count_mismatch} "
          f"mean_mismatch={n_mean_mismatch}", flush=True)
    # (referee finding) vote count is a near-deterministic within-contest rank
    # proxy for the mean, so vote bins are strata OF THE OUTCOME, not neutral
    # noise-matched groups. Measure and receipt the coupling.
    couple = []
    for _, grp in df.groupby("contest"):
        if len(grp) >= 200:
            r = spearmanr(grp["votes"], grp["mean_exact"]).statistic
            if np.isfinite(r):
                couple.append(float(r))
    votes_mean_coupling = round(float(np.median(couple)), 4) if couple else None
    print(f"votes<->mean within-contest coupling (median spearman): "
          f"{votes_mean_coupling}", flush=True)
    print("reliability pass...", flush=True)
    reliability = split_half_reliability(df, rng, args.reliability_cap, min_per_contest=50)
    print("predictability pass...", flush=True)
    predictability = heldout_predictability(df, rng, args.per_contest_cap,
                                            args.total_cap, min_contest_rows=200)

    def ratio(pred_block: dict, rel_block: dict) -> float | None:
        p = pred_block.get("text", {}).get("median_within_contest_spearman")
        c = rel_block.get("median_spearman_brown")
        return round(p / c, 4) if p is not None and c else None

    receipt = {
        "receipt_type": "caption_divisiveness_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "source": "nextml caption-contest 3-bin vote histograms via data_cache/caption_index.parquet",
        "definitions": {
            "conflict": "C = 2*sqrt(p_not_funny * p_funny); 0 = a pole is empty, "
                        "1 = even split between opposite poles",
            "ridge_caveat": "Ridge(alpha=2.0) untuned and shared across feature sets; "
                            "the text-vs-mean comparison is conditional on that choice",
            "entropy": "3-bin Shannon entropy / log(3)",
            "mean": "(1*nf + 2*sf + 3*f) / votes",
        },
        "screening": {
            "rows_raw": n_raw,
            "dropped_count_mismatch": n_count_mismatch,
            "dropped_mean_mismatch": n_mean_mismatch,
            "kept_votes_ge_20": n_screened,
        },
        "seed": args.seed,
        "votes_mean_within_contest_spearman_median": votes_mean_coupling,
        "reliability_caveats": {
            "vote_bins_are_outcome_strata": "vote count within a contest is a "
                "near-deterministic rank proxy for the mean, so per-bin cells "
                "condition on the outcome; the OVERALL row is the quotable one",
            "disjoint_split_downward_bias": "complementary vote-dealing biases "
                "split-half r downward vs independent half-samples under range "
                "restriction; SB values are conservative where reported and "
                "withheld where raw r <= 0",
        },
        "label_reliability": reliability,
        "heldout_predictability": predictability,
        "predicted_over_ceiling_note": "numerator population votes>=20, denominator "
            "reliability population votes>=40 (documented mismatch, ~6.8% of numerator "
            "rows outside denominator population); the ratio is the noise-ceiling "
            "convention on the rho scale, not a variance share",
        "predicted_over_ceiling": {
            which: ratio(predictability.get(which, {}), reliability["overall"].get(which, {}))
            for which in ("mean", "conflict", "entropy")
        },
        "truth_boundary": {
            "verified": "split-half reliability and contest-held-out text predictability of "
                        "three statistics of one publication's caption-vote histograms",
            "not_verified": "offensiveness, moderation risk, general controversy, funniness, "
                            "or behavior of any other audience",
        },
        "data_note": "Caption text is research-only and does not appear in this receipt.",
    }
    Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
