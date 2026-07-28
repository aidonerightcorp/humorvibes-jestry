"""Caption temporal drift study: does the caption-contest SYSTEM drift over time?

EXPLORATORY / DESCRIPTIVE. Contest number orders time across 360+ New Yorker
caption contests (nextml harvest, contests ~510-895). This study asks only
whether per-contest statistics of the SYSTEM — participation, caption surface
form, vote-allocation behavior, and label reliability — trend with contest
number. It makes NO causal claims and says NOTHING about topicality or
"current events": the corpus has no dated topical labels, so the maintainer's
original question ("is joking about something old better?") is out of reach;
this is its one cheap honest arm (does anything drift at all?).

Protocol is pre-registered inside the script: the receipt is first written
with status="preregistered" (measures, family, seed, MDE, exploratory label)
BEFORE any measure or trend is computed, and the final receipt embeds the
byte-identical preregistration block plus its sha256.

Integrity screens are the ones documented in divisiveness_study.py
(2026-07-26): votes == nf+sf+f, recomputed mean within 0.02 of the published
mean, votes >= 20; drops are counted in the receipt, never averaged over.

Referee rule (2026-07-28, binding): split-half label reliability is reported
as the RAW Spearman r. Spearman-Brown 2r/(1+r) is applied ONLY where r > 0
and never reported for r <= 0 — a prior wave published sign-flipped,
magnitude-amplified artifacts by correcting negative r. The temporal trend
uses raw r exclusively.

Usage:
    python3 caption_temporal_drift.py \
        --data-root /path/to/build-with-gemma-humor-genome-nyc \
        --out jestry_out/caption_temporal_drift.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

SEED = 20260728
MIN_CAPTIONS_PER_CONTEST = 200
RELIABILITY_MIN_VOTES = 40
RELIABILITY_MIN_CAPTIONS = 50
RELIABILITY_CAP_PER_CONTEST = 400
RELIABILITY_SPLITS = 5
TOP_WORDS = 200
NOVELTY_WINDOW = 10
ROLLING_WINDOW = 20
ROLLING_MIN_PERIODS = 15
FAMILY = [
    "reliability_raw_split_half_r",
    "log_n_captions",
    "median_votes",
    "median_caption_length_chars",
    "vocab_novelty",
    "mean_rating",
    "funny_vote_share",
]
SENSITIVITY = ["median_caption_length_words"]

STOPWORDS = frozenset("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for from
further get got had hadn't has hasn't have haven't having he he'd he'll he's
her here here's hers herself him himself his how how's i i'd i'll i'm i've if
in into is isn't it it's its itself just let's like me more most mustn't my
myself no nor not now of off on once only or other ought our ours ourselves
out over own said same say says shan't she she'd she'll she's should
shouldn't so some such than that that's the their theirs them themselves then
there there's these they they'd they'll they're they've this those through to
too under until up very was wasn't we we'd we'll we're we've were weren't
what what's when when's where where's which while who who's whom why why's
with won't would wouldn't you you'd you'll you're you've your yours yourself
yourselves
""".split())

TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


def load_and_screen(parquet: Path) -> tuple[pd.DataFrame, dict]:
    df = pd.read_parquet(parquet, columns=["contest", "text", "votes", "nf",
                                           "sf", "f", "mean_harvest"])
    n_raw = len(df)
    for col in ("votes", "nf", "sf", "f"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["votes", "nf", "sf", "f", "text"])
    df = df[(df["votes"] > 0) & (df["nf"] >= 0) & (df["sf"] >= 0) & (df["f"] >= 0)]
    consistent = df["votes"] == df["nf"] + df["sf"] + df["f"]
    n_count_mismatch = int((~consistent).sum())
    df = df[consistent]
    df["mean_exact"] = (1 * df["nf"] + 2 * df["sf"] + 3 * df["f"]) / df["votes"]
    mean_ok = (df["mean_harvest"].isna()) | ((df["mean_exact"] - df["mean_harvest"]).abs() <= 0.02)
    n_mean_mismatch = int((~mean_ok).sum())
    df = df[mean_ok]
    df = df[df["votes"] >= 20]
    # contest number = leading integer of the harvest contest id ("831" and
    # "831.csv" are disjoint harvest slices of the same contest -> merged)
    nums = df["contest"].astype(str).str.extract(r"^(\d+)", expand=False)
    n_unparsable = int(nums.isna().sum())
    df = df[nums.notna()].copy()
    df["contest_num"] = nums[nums.notna()].astype(int)
    screening = {
        "rows_raw": n_raw,
        "dropped_count_mismatch": n_count_mismatch,
        "dropped_mean_mismatch": n_mean_mismatch,
        "dropped_unparsable_contest_id": n_unparsable,
        "kept_votes_ge_20": int(len(df)),
        "contest_id_merge_note": "harvest ids '831' and '831.csv' are disjoint "
                                 "caption slices of the same contest and are "
                                 "merged under contest number 831",
    }
    return df, screening


def top_content_words(texts: pd.Series) -> frozenset:
    counts: Counter = Counter()
    for t in texts:
        for tok in TOKEN_RE.findall(str(t).lower()):
            if len(tok) >= 3 and tok not in STOPWORDS:
                counts[tok] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return frozenset(w for w, _ in ranked[:TOP_WORDS])


def contest_reliability(grp: pd.DataFrame, rng: np.random.Generator) -> float | None:
    elig = grp[grp["votes"] >= RELIABILITY_MIN_VOTES]
    if len(elig) < RELIABILITY_MIN_CAPTIONS:
        return None
    if len(elig) > RELIABILITY_CAP_PER_CONTEST:
        elig = elig.sample(n=RELIABILITY_CAP_PER_CONTEST,
                           random_state=int(rng.integers(0, 2**31)))
    counts = elig[["nf", "sf", "f"]].to_numpy(dtype=np.int64)
    votes = elig["votes"].to_numpy(dtype=np.int64)
    half_n = votes // 2
    rs = []
    for _ in range(RELIABILITY_SPLITS):
        a = np.empty_like(counts)
        for i in range(len(counts)):
            a[i] = rng.multivariate_hypergeometric(counts[i], int(half_n[i]))
        b = counts - a
        mean_a = (a[:, 0] + 2 * a[:, 1] + 3 * a[:, 2]) / a.sum(axis=1)
        mean_b = (b[:, 0] + 2 * b[:, 1] + 3 * b[:, 2]) / b.sum(axis=1)
        r = spearmanr(mean_a, mean_b).statistic
        if np.isfinite(r):
            rs.append(float(r))
    if len(rs) < 3:
        return None
    return float(np.median(rs))


def fisher_trend(x: np.ndarray, y: np.ndarray) -> dict:
    mask = np.isfinite(y)
    xs, ys = x[mask], y[mask]
    n = int(len(xs))
    if n < 10:
        return {"n_contests": n, "rho": None, "ci95": None, "p": None,
                "mde_abs_rho_95": None}
    rho = float(spearmanr(xs, ys).statistic)
    se = 1.06 / np.sqrt(n - 3)
    z = float(np.arctanh(np.clip(rho, -0.999999, 0.999999)))
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    p = float(2.0 * norm.sf(abs(z) / se))
    return {
        "n_contests": n,
        "rho": round(rho, 4),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "p": round(p, 6),
        "mde_abs_rho_95": round(float(np.tanh(1.96 * se)), 4),
    }


def bh_adjust(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    qs, running = {}, 1.0
    for rank in range(m, 0, -1):
        name, p = items[rank - 1]
        running = min(running, p * m / rank)
        qs[name] = round(running, 6)
    return qs


def rolling_median(vals: list) -> list:
    s = pd.Series(vals, dtype=float)
    r = s.rolling(ROLLING_WINDOW, min_periods=ROLLING_MIN_PERIODS).median()
    return [round(float(v), 4) if np.isfinite(v) else None for v in r]


def build_preregistration() -> dict:
    return {
        "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "registered_before_computation": True,
        "study_label": "EXPLORATORY, DESCRIPTIVE — no causal claims, no "
                       "confirmatory hypotheses; every trend is a description "
                       "of one publication's contest system over contest number",
        "seed": SEED,
        "unit": "contest (leading integer of the nextml contest id; '831' and "
                "'831.csv' merged), included iff >= "
                f"{MIN_CAPTIONS_PER_CONTEST} captions survive the screens",
        "screens": "divisiveness_study.py screens: votes==nf+sf+f, "
                   "|mean_exact-mean_harvest|<=0.02 (or mean_harvest missing), "
                   "votes>=20; drops receipted",
        "measures": {
            "reliability_raw_split_half_r": (
                "per contest: captions with votes>=40 (contest needs >= "
                f"{RELIABILITY_MIN_CAPTIONS}, subsampled to <= "
                f"{RELIABILITY_CAP_PER_CONTEST}); "
                f"{RELIABILITY_SPLITS} multivariate-hypergeometric vote splits "
                "(votes//2 vs complement); per split, Spearman r between "
                "half-A and half-B caption means; per-contest stat = median "
                "RAW r over splits (>=3 finite required). RAW r only in the "
                "trend; Spearman-Brown appears only in the summary block, "
                "only over contests with r>0, never for r<=0"),
            "log_n_captions": "ln(number of valid captions); rho identical to "
                              "raw n under rank methods, log declared for the "
                              "rolling-median scale",
            "median_votes": "median votes over valid captions",
            "median_caption_length_chars": "median len(text) in characters",
            "median_caption_length_words": "median whitespace-token count "
                                           "(SENSITIVITY companion of the "
                                           "chars measure, NOT in BH family)",
            "vocab_novelty": (
                "1 - Jaccard(top-200 content words of this contest, union of "
                f"top-200 sets of the previous {NOVELTY_WINDOW} included "
                "contests); defined only when exactly "
                f"{NOVELTY_WINDOW} priors exist; content word = regex "
                "[a-z]+(?:'[a-z]+)? on lowercased text, length>=3, not in the "
                "embedded stopword list; ties broken by (-count, token)"),
            "mean_rating": "unweighted mean of mean_exact over valid captions",
            "funny_vote_share": "sum(f) / sum(votes) over valid captions",
        },
        "trend_test": "tied-midrank Spearman rho(contest_number, per-contest "
                      "stat); CI and p from Fisher z with SE = 1.06/sqrt(n-3); "
                      "two-sided",
        "family": {
            "tests": FAMILY,
            "n_tests": len(FAMILY),
            "correction": "Benjamini-Hochberg across exactly these 7 tests; "
                          "non-null declared at q < 0.05",
            "sensitivity_outside_family": SENSITIVITY,
            "sensitivity_reason": "length-in-words is the same construct as "
                                  "length-in-chars (near-collinear); reported "
                                  "with rho/CI but no q to avoid double-"
                                  "counting one construct in the family",
        },
        "mde": {
            "definition": "smallest |rho| whose 95% Fisher-z CI excludes 0: "
                          "tanh(1.96 * 1.06 / sqrt(n-3))",
            "value_at_n_360": round(float(np.tanh(1.96 * 1.06 / np.sqrt(360 - 3))), 4),
            "note": "~0.11 at n=360 contests; trends smaller than this are "
                    "indistinguishable from null here",
        },
        "rolling_series": f"trailing {ROLLING_WINDOW}-contest rolling median, "
                          f"min_periods={ROLLING_MIN_PERIODS}, over contests "
                          "in contest-number order (sequence positions, not "
                          "calendar-spaced)",
        "stopword_list_sha256": hashlib.sha256(
            " ".join(sorted(STOPWORDS)).encode()).hexdigest(),
        "stopword_count": len(STOPWORDS),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=".")
    ap.add_argument("--out", default="jestry_out/caption_temporal_drift.json")
    args = ap.parse_args()
    t0 = time.time()

    parquet = Path(args.data_root) / "data_cache" / "caption_index.parquet"
    if not parquet.exists():
        raise SystemExit(f"missing {parquet} — build it with caption_corpus.py first")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("loading + screening...", flush=True)
    df, screening = load_and_screen(parquet)
    print(f"rows raw={screening['rows_raw']} kept={screening['kept_votes_ge_20']} "
          f"count_mismatch={screening['dropped_count_mismatch']} "
          f"mean_mismatch={screening['dropped_mean_mismatch']}", flush=True)

    # ---- PREREGISTRATION: written to the receipt BEFORE any measure/trend ----
    prereg = build_preregistration()
    prereg_sha = hashlib.sha256(
        json.dumps(prereg, sort_keys=True).encode()).hexdigest()
    stub = {
        "receipt_type": "caption_temporal_drift",
        "receipt_version": 1,
        "status": "preregistered",
        "preregistration": prereg,
        "preregistration_sha256": prereg_sha,
        "screening": screening,
    }
    out_path.write_text(json.dumps(stub, indent=2) + "\n")
    print(f"preregistration written (sha256={prereg_sha[:16]}...) — "
          f"family of {len(FAMILY)} tests, seed={SEED}, exploratory", flush=True)

    rng = np.random.default_rng(SEED)
    sizes = df.groupby("contest_num").size()
    included = sorted(sizes[sizes >= MIN_CAPTIONS_PER_CONTEST].index)
    excluded = int((sizes < MIN_CAPTIONS_PER_CONTEST).sum())
    print(f"contests included={len(included)} excluded(<{MIN_CAPTIONS_PER_CONTEST} "
          f"valid captions)={excluded} span={included[0]}-{included[-1]}", flush=True)

    groups = {c: g for c, g in df.groupby("contest_num") if c in set(included)}

    # ---- per-contest measures ----
    print("per-contest participation / surface / rating measures...", flush=True)
    stats: dict[str, list] = {k: [] for k in FAMILY + SENSITIVITY}
    for c in included:
        g = groups[c]
        texts = g["text"].astype(str)
        stats["log_n_captions"].append(float(np.log(len(g))))
        stats["median_votes"].append(float(g["votes"].median()))
        stats["median_caption_length_chars"].append(float(texts.str.len().median()))
        stats["median_caption_length_words"].append(
            float(texts.str.split().str.len().median()))
        stats["mean_rating"].append(float(g["mean_exact"].mean()))
        stats["funny_vote_share"].append(float(g["f"].sum() / g["votes"].sum()))

    print("vocabulary novelty pass...", flush=True)
    history: deque = deque(maxlen=NOVELTY_WINDOW)
    for idx, c in enumerate(included):
        top = top_content_words(groups[c]["text"])
        if len(history) == NOVELTY_WINDOW:
            prior_union = frozenset().union(*history)
            inter = len(top & prior_union)
            union = len(top | prior_union)
            stats["vocab_novelty"].append(1.0 - inter / union if union else None)
        else:
            stats["vocab_novelty"].append(None)
        history.append(top)
        if (idx + 1) % 100 == 0:
            print(f"  novelty {idx + 1}/{len(included)}", flush=True)

    print("split-half reliability pass (this is the slow one)...", flush=True)
    for idx, c in enumerate(included):
        stats["reliability_raw_split_half_r"].append(
            contest_reliability(groups[c], rng))
        if (idx + 1) % 50 == 0:
            print(f"  reliability {idx + 1}/{len(included)} "
                  f"({time.time() - t0:.0f}s)", flush=True)

    # reliability summary block (referee rule: SB only over r>0, never r<=0)
    rel_raw = [r for r in stats["reliability_raw_split_half_r"] if r is not None]
    rel_pos = [r for r in rel_raw if r > 0]
    med_raw = float(np.median(rel_raw)) if rel_raw else None
    estimable = bool(med_raw is not None and med_raw > 0)
    reliability_summary = {
        "median_raw_split_half": round(med_raw, 4) if med_raw is not None else None,
        "iqr_raw": [round(float(np.percentile(rel_raw, 25)), 4),
                    round(float(np.percentile(rel_raw, 75)), 4)] if rel_raw else None,
        "median_spearman_brown_positive_r_only": (
            round(float(np.median([2 * r / (1 + r) for r in rel_pos])), 4)
            if estimable and rel_pos else None),
        "contests": len(rel_raw),
        "contests_negative_r": len(rel_raw) - len(rel_pos),
        "estimable": estimable,
        "rule": "RAW split-half r is the reported statistic; Spearman-Brown is "
                "applied only where r > 0 and never for r <= 0 (prior wave "
                "published sign-flipped artifacts violating this)",
    }

    # ---- trends + BH across the declared 7-test family ----
    print("trend tests + BH...", flush=True)
    x = np.array(included, dtype=float)
    trends = {}
    for name in FAMILY + SENSITIVITY:
        y = np.array([np.nan if v is None else v for v in stats[name]], dtype=float)
        trends[name] = fisher_trend(x, y)
        trends[name]["in_bh_family"] = name in FAMILY
    qs = bh_adjust({n: trends[n]["p"] for n in FAMILY if trends[n]["p"] is not None})
    for name in FAMILY:
        trends[name]["q_bh"] = qs.get(name)
        trends[name]["nonnull_q_lt_05"] = bool(
            qs.get(name) is not None and qs[name] < 0.05)
    for name in SENSITIVITY:
        trends[name]["q_bh"] = None
        trends[name]["note"] = "sensitivity companion, outside the BH family"

    series = {
        "contest_numbers": [int(c) for c in included],
        "measures": {
            name: {
                "values": [round(v, 4) if v is not None else None
                           for v in stats[name]],
                "rolling_median_20": rolling_median(stats[name]),
            }
            for name in FAMILY + SENSITIVITY
        },
    }

    runtime = round(time.time() - t0, 1)
    receipt = {
        "receipt_type": "caption_temporal_drift",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "source": "nextml caption-contest 3-bin vote histograms via "
                  "data_cache/caption_index.parquet",
        "preregistration": prereg,
        "preregistration_sha256": prereg_sha,
        "screening": screening,
        "contests": {
            "included": len(included),
            "excluded_below_min_captions": excluded,
            "span": [int(included[0]), int(included[-1])],
        },
        "label_reliability_summary": reliability_summary,
        "trends": trends,
        "series": series,
        "truth_boundary": {
            "verified": "descriptive time-ordered drift (contest number as "
                        "ordinal time) of participation, caption surface form, "
                        "vote allocation, and raw split-half label reliability "
                        "in ONE publication's caption-contest system",
            "not_verified": "anything about topicality or 'current events' — "
                            "that needs dated topical labels this corpus "
                            "lacks; drift here is NOT humor aging; no causal "
                            "claim survives — participation and editorial "
                            "policy are confounded with time",
        },
        "caveats": [
            "exploratory study: BH controls FDR only within the declared "
            "7-test family; any post-hoc reading of the series arrays is "
            "uncorrected",
            "contest number is ordinal time; contests are not calendar-evenly "
            "spaced and harvest coverage may vary with era",
            "reliability trend is mechanically coupled to vote counts: more "
            "votes per caption -> higher split-half r, so a reliability trend "
            "is not evidence of labeling-process drift on its own",
            "vocab_novelty depends on declared choices (top-200, 10-contest "
            "window, stopword list); it measures lexical turnover between "
            "adjacent eras, not topicality",
            "mean_rating and funny_vote_share are functions of the same vote "
            "histograms and are correlated by construction; both stay in the "
            "family as declared",
            "log_n_captions counts harvested valid captions, which conflates "
            "true participation with harvest/editorial retention",
        ],
        "runtime_seconds": runtime,
        "data_note": "Caption text is research-only; this receipt contains "
                     "numbers only (no caption text, no word lists).",
    }
    check = hashlib.sha256(
        json.dumps(receipt["preregistration"], sort_keys=True).encode()).hexdigest()
    assert check == prereg_sha, "preregistration block mutated after registration"
    out_path.write_text(json.dumps(receipt, indent=2) + "\n")

    print(f"\nwrote {out_path} ({runtime}s)", flush=True)
    print("trend table (rho [ci95] q | nonnull):", flush=True)
    for name in FAMILY + SENSITIVITY:
        t = trends[name]
        tag = "" if t["in_bh_family"] else " (sensitivity, no q)"
        print(f"  {name:32s} rho={t['rho']} ci={t['ci95']} q={t.get('q_bh')} "
              f"nonnull={t.get('nonnull_q_lt_05', '-')}{tag}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
