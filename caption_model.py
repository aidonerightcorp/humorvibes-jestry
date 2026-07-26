#!/usr/bin/env python3
"""The caption model, judged against what is actually achievable.

`three_corpus_study.py` measured features on this corpus by pooling captions
across contests. That protocol has a defect this file exists to correct: the
contests differ in vote scale and in crowd harshness, so a pooled correlation
partly measures WHICH CONTEST a caption came from. It is also trained and tested
on rows from the same contests, so nothing in it says whether the signal
survives an unseen drawing.

This run fixes both, and adds the two numbers that make the result readable:

* **TARGET** — percentile standing within the caption's own contest. The drawing
  and the vote scale are held fixed by construction.
* **CV** — GroupKFold over CONTESTS. A held-out contest is a drawing the model
  has never seen, which is the only honest test of a humor feature.
* **CEILING (caption_ceiling.py)** — the published mean is a finite vote sample,
  so no predictor can exceed spearman ~0.83 against it.
* **TEXT-ONLY BOUND (caption_portability.py)** — a caption's standing barely
  travels to a different drawing, so a model reading only the caption is bounded
  far below the label ceiling, at about sqrt of the cross-context correlation.

A score is meaningless without those two. 0.15 against a ceiling of 1.0 is a
failure; the same 0.15 against a text-only bound of 0.41 is a third of
everything the text can carry.

Finally the transfer matrix is completed. Humicroedit and r/Jokes have been
crossed already; the caption corpus is the third population and the only one
with a controlled context, so it belongs in the same table.

    python3 caption_model.py --per-contest 600
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import caption_corpus as cc
from caption_ceiling import MIN_CAPTIONS, clean
from caption_portability import pct_rank
from humor_features import build_frequencies, features, spearman

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"


def write_report(report: dict) -> None:
    """Atomically checkpoint the core result before optional transfer work."""
    OUT.mkdir(exist_ok=True)
    path = OUT / "caption_model.json"
    pending = OUT / "caption_model.json.tmp"
    pending.write_text(json.dumps(report, indent=2), encoding="utf-8")
    pending.replace(path)


def caption_rows(per_contest: int, seed: int, min_votes: int = 0):
    """Standing computed on the FULL contest, then a deterministic subsample.

    Ranking first and sampling second matters: a percentile computed inside a
    600-row sample is a different quantity from the caption's real standing
    among its 5,000 rivals.
    """
    df, dropped = clean(cc.load())
    rng = np.random.default_rng(seed)
    out = []
    for contest, g in df.groupby("contest", observed=True):
        if len(g) < MIN_CAPTIONS:
            continue
        C = cc.counts_matrix(g)
        votes = C.sum(axis=1)
        means = (C * cc.SCALE).sum(axis=1) / votes
        standing = pct_rank(means)
        idx = np.arange(len(g))
        if min_votes:
            idx = idx[votes[idx] >= min_votes]
        if len(idx) < 50:
            continue
        take = rng.permutation(idx)[:per_contest]
        texts = g["text"].to_numpy()
        for i in take:
            out.append({"contest": str(contest), "setup": "", "punchline": str(texts[i]),
                        "y": float(standing[i]), "votes": float(votes[i])})
    return out, dropped


def matrix(rows, freq, total, names=None):
    mats = [features(r["setup"], r["punchline"], freq, total) for r in rows]
    names = names or sorted(mats[0])
    X = np.array([[m[n] for n in names] for m in mats], dtype=float)
    y = np.array([r["y"] for r in rows])
    return X, y, names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-contest", type=int, default=600)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260726)
    ap.add_argument("--skip-transfer", action="store_true")
    a = ap.parse_args()
    if a.per_contest <= 0:
        ap.error("--per-contest must be positive")
    if a.folds < 2:
        ap.error("--folds must be at least 2")
    t0 = time.time()
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold, train_test_split

    def gbm():
        return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06,
                                             random_state=a.seed)

    rows, dropped = caption_rows(a.per_contest, a.seed)
    contests = sorted({r["contest"] for r in rows})
    if len(contests) < a.folds:
        raise ValueError(
            f"{a.folds} folds requested but only {len(contests)} contests survived cleaning"
        )
    print(f"captions {len(rows):,} over {len(contests)} contests "
          f"(dropped {dropped:,} inconsistent/low-vote rows)")

    freq = build_frequencies()
    total = sum(freq.values())
    X, y, names = matrix(rows, freq, total)
    groups = np.array([r["contest"] for r in rows])
    votes = np.array([r["votes"] for r in rows])
    print(f"features {len(names)} | feature matrix {X.shape}")

    # ---- contest-held-out CV ------------------------------------------
    gkf = GroupKFold(n_splits=a.folds)
    pred = np.zeros(len(y))
    for fold_no, (tr, te) in enumerate(gkf.split(X, y, groups), 1):
        print(f"  contest-held-out fold {fold_no}/{a.folds}: "
              f"train {len(tr):,}, test {len(te):,}", flush=True)
        pred[te] = gbm().fit(X[tr], y[tr]).predict(X[te])

    per_contest_rho = []
    for c in contests:
        m = groups == c
        if m.sum() >= 50:
            per_contest_rho.append(spearman(list(pred[m]), list(y[m])))
    per_contest_rho = np.array(per_contest_rho)
    within = float(np.median(per_contest_rho))
    pooled = spearman(list(pred), list(y))

    # the protocol the previous study used, reproduced here for the contrast:
    # rows shuffled, so train and test share contests
    itr, ite = train_test_split(np.arange(len(y)), test_size=0.3, random_state=a.seed)
    leaky = gbm().fit(X[itr], y[itr])
    leaky_rho = spearman(list(leaky.predict(X[ite])), list(y[ite]))

    # high-vote subset: less label noise, so a higher ceiling to aim at
    hv = votes >= 100
    hv_rho = float(np.median([
        spearman(list(pred[(groups == c) & hv]), list(y[(groups == c) & hv]))
        for c in contests if ((groups == c) & hv).sum() >= 50]))

    ceil = json.loads((OUT / "caption_ceiling.json").read_text())
    port = json.loads((OUT / "caption_portability.json").read_text())
    label_ceiling = ceil["headline"]["median_ceiling"]
    text_bound = port["results"]["text_only_predictor_bound"]

    print(f"\n{'arm':<46}{'spearman':>10}")
    print(f"{'contest-held-out, within-contest (median)':<46}{within:>10.4f}")
    print(f"{'  ... on captions with >=100 votes':<46}{hv_rho:>10.4f}")
    print(f"{'contest-held-out, pooled across contests':<46}{pooled:>10.4f}")
    print(f"{'random-split (shares contests: the old protocol)':<46}{leaky_rho:>10.4f}")
    print(f"\n{'bound':<46}{'value':>10}")
    print(f"{'label ceiling (vote noise)':<46}{label_ceiling:>10.4f}")
    print(f"{'text-only bound (context dependence)':<46}{text_bound:>10.4f}")
    print(f"\nachieved / text-only bound = {within / text_bound:.1%}")
    print(f"achieved / label ceiling   = {within / label_ceiling:.1%}")
    print(f"contests where the model orders better than chance: "
          f"{int((per_contest_rho > 0).sum())}/{len(per_contest_rho)}")

    report = {
        "receipt_type": "caption_model_vs_bounds",
        "receipt_version": 2,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": "how much of the achievable caption signal do structural text "
                    "features actually capture?",
        "protocol": {
            "target": "percentile standing within the caption's own contest, computed on "
                      "the full contest before subsampling",
            "cv": f"GroupKFold over contests, {a.folds} folds — a held-out contest is an "
                  f"unseen drawing",
            "model": "HistGradientBoostingRegressor(max_iter=300, lr=0.06)",
            "features": names,
            "per_contest_sample": a.per_contest,
            "seed": a.seed,
        },
        "n_rows": len(rows), "n_contests": len(contests),
        "results": {
            "within_contest_median_spearman": within,
            "within_contest_iqr": [float(np.percentile(per_contest_rho, 25)),
                                   float(np.percentile(per_contest_rho, 75))],
            "high_vote_subset_spearman": hv_rho,
            "pooled_spearman": pooled,
            "random_split_same_contests_spearman": leaky_rho,
            "contests_above_chance": int((per_contest_rho > 0).sum()),
            "contests_scored": int(len(per_contest_rho)),
        },
        "bounds": {
            "label_ceiling": label_ceiling,
            "text_only_bound": text_bound,
            "achieved_over_text_only_bound": within / text_bound,
            "achieved_over_label_ceiling": within / label_ceiling,
            "sources": ["jestry_out/caption_ceiling.json", "jestry_out/caption_portability.json"],
        },
        "status": "core_complete",
        "core_runtime_s": round(time.time() - t0, 1),
    }
    report["runtime_s"] = report["core_runtime_s"]
    write_report(report)
    print("\ncore receipt checkpoint -> jestry_out/caption_model.json", flush=True)

    # ---- transfer matrix ----------------------------------------------
    if not a.skip_transfer:
        from transfer_study import load_humicroedit, load_reddit, matrix as tmatrix
        hum = load_humicroedit()
        red = load_reddit(40000)
        Xh, yh, _ = tmatrix(hum, freq, total, names)
        Xr, yr, _ = tmatrix(red, freq, total, names)
        cap_model = gbm().fit(X, y)
        hum_model = gbm().fit(Xh, yh)
        red_model = gbm().fit(Xr, yr)
        tm = {
            "caption_to_reddit": spearman(list(cap_model.predict(Xr)), list(yr)),
            "caption_to_humicroedit": spearman(list(cap_model.predict(Xh)), list(yh)),
            "reddit_to_caption_within": float(np.median([
                spearman(list(red_model.predict(X[groups == c])), list(y[groups == c]))
                for c in contests if (groups == c).sum() >= 50])),
            "humicroedit_to_caption_within": float(np.median([
                spearman(list(hum_model.predict(X[groups == c])), list(y[groups == c]))
                for c in contests if (groups == c).sum() >= 50])),
        }
        print(f"\ntransfer matrix (train -> test)")
        for k, v in tm.items():
            print(f"  {k:<34}{v:>+9.4f}")
        report["transfer"] = tm
        report["transfer_note"] = (
            "caption arms are evaluated WITHIN contest (median over contests); the "
            "reddit and humicroedit arms are pooled, since neither corpus has a "
            "controlled context to hold fixed")

    report["status"] = "complete"
    report["completed_ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    report["runtime_s"] = round(time.time() - t0, 1)
    write_report(report)
    print("\nreceipt -> jestry_out/caption_model.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
