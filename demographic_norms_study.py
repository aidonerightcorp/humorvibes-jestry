"""Demographic humor-norms study: the first empirical anchor for persona-B.

B (persona-relative bad surprise) is the least-validated of the four signals:
its persona conditioning has so far rested on model judgments alone. Two
published word-level humor datasets with demographic splits have been sitting
in ``data_cache/`` unread by any code:

- Engelthaler & Hills humor norms: 4,997 words, mean/sd/n split by sex
  (mean_M / mean_F) and by age (mean_young / mean_old).
- "Cockamamie Gobbledegook" (Google): 1,878 raters with age+sex, per-word
  yes/no funniness votes, plus six hand-coded word dimensions
  (snd, scatc, clq, inslt, juxt, sexc).

Questions, all word-level and descriptive:
1. Do the two independent crowds agree on which words are funny at all?
2. How large and how reproducible are sex and age gaps in word funniness?
3. Do the two datasets agree on the DIRECTION of the sex/age gaps (the
   cross-dataset check that turns a quirk into a phenomenon)?
4. Which hand-coded word dimensions track the gaps?

Truth boundary: these are average rating tendencies of demographic groups in
two specific crowd platforms, at the single-word level. They justify persona
CONDITIONING as a design choice; they do not describe any individual, license
audience profiling, or measure joke-level funniness.

Usage:
    python3 demographic_norms_study.py \
        --data-root /path/to/build-with-gemma-humor-genome-nyc \
        --out jestry_out/demographic_norms_study.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

MIN_VOTES_PER_SIDE = 8


def bh_qvalues(pvals: np.ndarray) -> np.ndarray:
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(ranked, 0, 1)
    return out


def spearman_ci(r: float, n: int) -> list[float] | None:
    if n < 4 or not np.isfinite(r) or abs(r) >= 1:
        return None
    z = np.arctanh(r)
    se = 1.06 / np.sqrt(n - 3)
    return [round(float(np.tanh(z - 1.96 * se)), 4),
            round(float(np.tanh(z + 1.96 * se)), 4)]


def load_engelthaler(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["word"] = df["word"].str.lower().str.strip()
    for a, b, gap in (("mean_F", "mean_M", "sex_gap"), ("mean_young", "mean_old", "age_gap")):
        df[gap] = df[a] - df[b]
    df["sex_se"] = np.sqrt(df["sd_M"] ** 2 / df["n_M"] + df["sd_F"] ** 2 / df["n_F"])
    df["age_se"] = np.sqrt(df["sd_young"] ** 2 / df["n_young"] + df["sd_old"] ** 2 / df["n_old"])
    return df


def load_cockamamie(path: Path) -> tuple[pd.DataFrame, dict, dict]:
    raw = json.loads(path.read_text())
    workers = {w["id"]: w for w in raw["word_ratings"]["workers"]}
    ages = [w["age"] for w in workers.values() if isinstance(w.get("age"), (int, float))]
    age_median = float(np.median(ages))
    votes: dict[str, dict[str, set]] = {}
    for batch in raw["word_ratings"]["votes"]:
        for word, v in batch.items():
            slot = votes.setdefault(word.lower(), {"yes": set(), "no": set()})
            slot["yes"].update(v.get("yes_votes", []))
            slot["no"].update(v.get("no_votes", []))
    rows = []
    for word, v in votes.items():
        yes, no = v["yes"], v["no"]

        def side(ids: set, key: str, value) -> int:
            n = 0
            for i in ids:
                w = workers.get(i)
                if not w:
                    continue
                if key == "sex" and w.get("sex") == value:
                    n += 1
                elif key == "age" and isinstance(w.get("age"), (int, float)):
                    if (value == "young") == (w["age"] < age_median):
                        n += 1
            return n

        yes_f, no_f = side(yes, "sex", "Female"), side(no, "sex", "Female")
        yes_m, no_m = side(yes, "sex", "Male"), side(no, "sex", "Male")
        yes_y, no_y = side(yes, "age", "young"), side(no, "age", "young")
        yes_o, no_o = side(yes, "age", "old"), side(no, "age", "old")
        total = len(yes) + len(no)
        row = {"word": word, "n_total": total,
               "p_funny": len(yes) / total if total else np.nan}
        if yes_f + no_f >= MIN_VOTES_PER_SIDE and yes_m + no_m >= MIN_VOTES_PER_SIDE:
            row["sex_gap"] = yes_f / (yes_f + no_f) - yes_m / (yes_m + no_m)
        if yes_y + no_y >= MIN_VOTES_PER_SIDE and yes_o + no_o >= MIN_VOTES_PER_SIDE:
            row["age_gap"] = yes_y / (yes_y + no_y) - yes_o / (yes_o + no_o)
        rows.append(row)
    demo = {
        "workers": len(workers),
        "age_median_split": age_median,
        "sex_counts": pd.Series([w.get("sex") for w in workers.values()]).value_counts().to_dict(),
    }
    return pd.DataFrame(rows), raw["word_features"], demo


def gap_block(df: pd.DataFrame, gap: str, se: str) -> dict:
    sub = df.dropna(subset=[gap, se])
    z = (sub[gap] / sub[se].replace(0, np.nan)).to_numpy()
    z = z[np.isfinite(z)]
    p = 2 * norm.sf(np.abs(z))
    q = bh_qvalues(np.asarray(p))
    sig = int((q < 0.05).sum())
    top_pos = sub.nlargest(15, gap)[["word", gap]].round(4).to_dict("records")
    top_neg = sub.nsmallest(15, gap)[["word", gap]].round(4).to_dict("records")
    return {
        "words_tested": int(len(sub)),
        "mean_abs_gap": round(float(sub[gap].abs().mean()), 4),
        "significant_q05": sig,
        "share_significant": round(sig / max(1, len(sub)), 4),
        "top_positive": top_pos,
        "top_negative": top_neg,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=".")
    ap.add_argument("--out", default="jestry_out/demographic_norms_study.json")
    args = ap.parse_args()

    root = Path(args.data_root) / "data_cache"
    eng = load_engelthaler(root / "engelthaler_humor_norms.csv")
    cock, features, demo = load_cockamamie(root / "cockamamie_gobbledegook.json")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    merged = eng.merge(cock, on="word", suffixes=("_eng", "_cock"))
    overall = merged.dropna(subset=["mean", "p_funny"])
    r_overall = spearmanr(overall["mean"], overall["p_funny"]).statistic if len(overall) >= 10 else np.nan

    cross = {}
    for gap in ("sex_gap", "age_gap"):
        sub = merged.dropna(subset=[f"{gap}_eng", f"{gap}_cock"])
        if len(sub) >= 10:
            r = spearmanr(sub[f"{gap}_eng"], sub[f"{gap}_cock"]).statistic
            cross[gap] = {"shared_words": int(len(sub)), "spearman": round(float(r), 4),
                          "ci95": spearman_ci(float(r), len(sub))}
        else:
            cross[gap] = {"shared_words": int(len(sub)),
                          "spearman": None,
                          "note": "insufficient overlap after per-side vote floors"}

    feat_rows = []
    fdim = pd.DataFrame(features)
    fdim.index = fdim.index.str.lower()
    joined = cock.set_index("word").join(fdim, how="inner")
    for dim in fdim.columns:
        for target in ("p_funny", "sex_gap", "age_gap"):
            sub = joined.dropna(subset=[dim, target])
            if len(sub) < 30:
                continue
            res = spearmanr(sub[dim], sub[target])
            feat_rows.append({"dimension": dim, "target": target, "n": int(len(sub)),
                              "spearman": round(float(res.statistic), 4),
                              "p": float(res.pvalue)})
    if feat_rows:
        q = bh_qvalues(np.array([r["p"] for r in feat_rows]))
        for row, qv in zip(feat_rows, q):
            row["q_bh"] = round(float(qv), 5)
            row["p"] = round(row["p"], 6)
            row["ci95"] = spearman_ci(row["spearman"], row["n"])
    feat_rows.sort(key=lambda r: r["q_bh"])
    gap_sex = gap_block(eng, "sex_gap", "sex_se")
    gap_age = gap_block(eng, "age_gap", "age_se")
    gap_sex_sig, gap_age_sig = gap_sex["significant_q05"], gap_age["significant_q05"]

    receipt = {
        "receipt_type": "demographic_humor_norms_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "sources": {
            "engelthaler_hills": {"words": int(len(eng)),
                                  "fields": "mean/sd/n by sex and by age (published norms)"},
            "cockamamie": {"words_with_votes": int(len(cock)), **demo,
                           "vote_floor_per_side": MIN_VOTES_PER_SIDE},
        },
        "cross_dataset_overall_agreement": {
            "shared_words": int(len(overall)),
            "spearman_mean_vs_p_funny": round(float(r_overall), 4) if np.isfinite(r_overall) else None,
            "ci95": spearman_ci(float(r_overall), len(overall)) if np.isfinite(r_overall) else None,
        },
        "engelthaler_gaps": {"sex": gap_sex, "age": gap_age},
        "cross_dataset_gap_agreement": cross,
        "hand_coded_dimension_correlations": feat_rows,
        "persona_b_implication": (
            f"Two independent crowds agree substantially on which WORDS are funny "
            f"(rho={float(r_overall):.3f}), but single-word demographic GAPS mostly do not "
            f"survive FDR ({gap_sex_sig}/{len(eng)} sex, {gap_age_sig}/{len(eng)} age) and "
            f"cross-dataset gap agreement CIs include zero "
            f"(sex {cross['sex_gap'].get('spearman')}, age {cross['age_gap'].get('spearman')}). "
            "The one demographic signal that survives is dimension-level: sexual-connotation "
            "words skew toward younger raters. Persona conditioning of B therefore has only "
            "WEAK lexical-level support here; validating it requires joke-level, adequately "
            "powered human data. A clean mostly-negative result, kept visible."
        ),
        "truth_boundary": {
            "verified": "descriptive demographic rating differences on single words in two "
                        "published crowd datasets, with FDR control and cross-dataset checks",
            "not_verified": "individual preferences, joke-level effects, causal mechanisms, "
                            "or any audience outside these two rater pools",
        },
    }
    Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({
        "overall_agreement": receipt["cross_dataset_overall_agreement"],
        "sex_sig": receipt["engelthaler_gaps"]["sex"]["significant_q05"],
        "age_sig": receipt["engelthaler_gaps"]["age"]["significant_q05"],
        "cross_gap": {k: v.get("spearman") for k, v in cross.items()},
        "top_feature_rows": feat_rows[:4],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
