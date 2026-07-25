#!/usr/bin/env python3
"""Does the model transfer, or did it just learn what headlines look like?

The structural model reaches held-out Spearman 0.51 on Humicroedit. That number
is real, and it is also the easiest possible test: train and test rows come from
one corpus, one format (a real news headline with one word swapped), and one
labelling procedure (annotator means, 0 to 3). A model can reach 0.51 there by
learning regularities of *that corpus* and know nothing about humor.

The honest check is a different population. `data_cache/reddit_jokes_bulk.jsonl`
holds 100k r/Jokes posts: native setup/punchline jokes, no substitution, no
annotators, scored by upvotes. Almost everything differs. If the same features
still order those jokes above chance, the signal is about humor. If they do not,
the 0.51 belongs to Humicroedit and the claim has to be narrowed.

Three arms:

1. **Within-corpus baseline.** Humicroedit train to Humicroedit test, the number
   already reported, recomputed here so the comparison is like-for-like.
2. **Transfer.** Train on ALL of Humicroedit, evaluate on Reddit against
   log2(1+score). Upvotes are a popularity proxy, so a small correlation is the
   most that can be expected even in the good case, and the honest reference is
   not 0.51 but zero.
3. **Reddit-native baseline.** Train on Reddit, test on held-out Reddit. This
   separates "the features cannot work on this population" from "the features
   work but do not transfer", which are very different conclusions and are
   routinely confused.

    python3 transfer_study.py --reddit-n 40000
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from humor_features import build_frequencies, features, spearman
from incongruity_study import ensure_zip

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
REDDIT = HERE / "data_cache" / "reddit_jokes_bulk.jsonl"
MARKER = re.compile(r"<([^/>]*)/>")


def load_humicroedit() -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(ensure_zip().read_bytes()))
    rows = []
    df = pd.read_csv(z.open("data/task-1/train.csv")).dropna(subset=["meanGrade"])
    for _, r in df.iterrows():
        m = MARKER.search(str(r["original"]))
        if not m:
            continue
        rows.append({"setup": str(r["original"])[:m.start()].strip(),
                     "punchline": (str(r["edit"]) + str(r["original"])[m.end():]).strip(),
                     "y": float(r["meanGrade"])})
    df2 = pd.read_csv(z.open("data/task-2/train.csv")).dropna(subset=["meanGrade1", "meanGrade2"])
    for _, r in df2.iterrows():
        m = MARKER.search(str(r["original1"]))
        if not m:
            continue
        base = str(r["original1"]); setup = base[:m.start()].strip(); tail = base[m.end():]
        rows.append({"setup": setup, "punchline": (str(r["edit1"]) + tail).strip(),
                     "y": float(r["meanGrade1"])})
        rows.append({"setup": setup, "punchline": (str(r["edit2"]) + tail).strip(),
                     "y": float(r["meanGrade2"])})
    return rows


def load_reddit(limit: int) -> list[dict]:
    rows = []
    with REDDIT.open(encoding="utf-8") as fh:
        for line in fh:
            if len(rows) >= limit:
                break
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append({"setup": r["setup"], "punchline": r["punchline"],
                         "y": math.log2(1 + max(0, int(r["score"])))})
    return rows


def matrix(rows: list[dict], freq, total, names=None):
    mats = [features(r["setup"], r["punchline"], freq, total) for r in rows]
    names = names or sorted(mats[0])
    X = np.array([[m[n] for n in names] for m in mats], dtype=float)
    y = np.array([r["y"] for r in rows])
    return X, y, names


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reddit-n", type=int, default=40000)
    args = ap.parse_args()
    t0 = time.time()
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import train_test_split

    freq = build_frequencies()
    total = sum(freq.values())
    hum = load_humicroedit()
    red = load_reddit(args.reddit_n)
    print(f"humicroedit rows {len(hum)} | reddit rows {len(red)}")

    Xh, yh, names = matrix(hum, freq, total)
    Xr, yr, _ = matrix(red, freq, total, names)
    print(f"shared feature space: {len(names)} features")

    def gbm():
        return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06,
                                             random_state=20260725)

    # 1. within-corpus baseline
    itr, ite = train_test_split(np.arange(len(yh)), test_size=0.3, random_state=20260725)
    m1 = gbm().fit(Xh[itr], yh[itr])
    within = spearman(list(m1.predict(Xh[ite])), list(yh[ite]))

    # 2. transfer: all of humicroedit -> reddit
    m2 = gbm().fit(Xh, yh)
    transfer = spearman(list(m2.predict(Xr)), list(yr))

    # 3. reddit-native baseline
    rtr, rte = train_test_split(np.arange(len(yr)), test_size=0.3, random_state=20260725)
    m3 = gbm().fit(Xr[rtr], yr[rtr])
    native = spearman(list(m3.predict(Xr[rte])), list(yr[rte]))

    # reverse transfer, because a one-way test cannot distinguish "reddit is
    # unlearnable" from "the two corpora disagree"
    reverse = spearman(list(m3.predict(Xh[ite])), list(yh[ite]))

    print(f"\n1. within Humicroedit (train->test)   spearman {within:+.4f}   n_test={len(ite)}")
    print(f"2. TRANSFER Humicroedit -> Reddit    spearman {transfer:+.4f}   n={len(yr)}")
    print(f"3. within Reddit (train->test)       spearman {native:+.4f}   n_test={len(rte)}")
    print(f"4. reverse Reddit -> Humicroedit     spearman {reverse:+.4f}   n_test={len(ite)}")

    if abs(transfer) < 0.02:
        verdict = ("the model does NOT transfer: on a different population its ordering is "
                   "indistinguishable from chance, so the within-corpus 0.51 describes "
                   "Humicroedit, not humor in general")
    elif abs(transfer) < abs(within) / 3:
        verdict = ("partial transfer: the ordering survives on a different population but at a "
                   "small fraction of the within-corpus strength, so the features carry some "
                   "general signal and a great deal of corpus-specific fit")
    else:
        verdict = ("the model transfers: a substantial part of the within-corpus signal survives "
                   "a change of population, format and labelling procedure")
    print(f"\nverdict: {verdict}")

    report = {
        "receipt_type": "cross_corpus_transfer",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": ("does the structural model carry general humor signal, or did it learn "
                     "Humicroedit's shape?"),
        "corpora": {
            "humicroedit": {"n": len(hum), "label": "annotator mean grade 0-3",
                            "format": "news headline with one word substituted"},
            "reddit": {"n": len(red), "label": "log2(1+upvotes), a popularity proxy",
                       "format": "native setup/punchline joke, no substitution"},
        },
        "features": len(names),
        "results": {
            "within_humicroedit_spearman": within,
            "transfer_humicroedit_to_reddit_spearman": transfer,
            "within_reddit_spearman": native,
            "reverse_reddit_to_humicroedit_spearman": reverse,
        },
        "verdict": verdict,
        "caveats": ("upvotes are confounded by timing, subreddit dynamics and visibility, so even "
                    "a perfect humor model would not reach its within-corpus number here; the "
                    "reddit-native arm is included precisely so a low transfer number can be "
                    "attributed to distribution shift rather than to an unlearnable target"),
        "runtime_s": round(time.time() - t0, 1),
    }
    (OUT / "cross_corpus_transfer.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("receipt -> jestry_out/cross_corpus_transfer.json")


if __name__ == "__main__":
    main()
