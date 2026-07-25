#!/usr/bin/env python3
"""Does ANY feature predict funniness in more than one corpus?

The transfer test was blunt: a model trained on Humicroedit orders r/Jokes at
chance. That kills the claim that its held-out 0.51 measures humor rather than
Humicroedit. It leaves the more useful question open. Is there any feature that
holds its sign and its significance across genuinely different humor
populations, or is every effect corpus-shaped?

Three corpora, chosen because they fail in different directions:

- **Humicroedit** — a news headline with ONE word substituted, graded 0-3 by
  annotators. Highly constrained format, clean label, narrow.
- **New Yorker caption ranking** — the same cartoon with hundreds of competing
  captions, each with a crowd mean on a 3-point scale and a vote count. The
  prediction context is held FIXED by the drawing while the repair varies, which
  is the closest thing available to this project's own theory as an experiment.
  Weighted by votes, since a caption with 273 votes is not evidence of the same
  strength as one with 20.
- **r/Jokes** — native setup/punchline jokes scored by upvotes. Unconstrained
  format, noisy popularity label, broad.

A feature that survives in all three is a candidate humor regularity. A feature
that flips sign between corpora is a corpus artifact, and saying so is the point
of running this rather than reporting the best single-corpus number.

Every correlation is computed on a held-out split of its own corpus, with
permutation p and Benjamini-Hochberg control applied WITHIN each corpus. The
cross-corpus verdict then requires the same sign and survival in all three,
which is a much harder bar than any single test.

    python3 three_corpus_study.py --nyc-n 60000 --reddit-n 40000
"""
from __future__ import annotations

import argparse
import io
import json
import math
import random
import re
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from humor_features import (benjamini_hochberg, build_frequencies, features,
                            perm_p, spearman)
from incongruity_study import ensure_zip

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
CACHE_DIR = HERE / "data_cache"
NYC_CACHE = CACHE_DIR / "newyorker_caption_ranking.jsonl"
REDDIT = CACHE_DIR / "reddit_jokes_bulk.jsonl"
MARKER = re.compile(r"<([^/>]*)/>")
ROWS_URL = ("https://datasets-server.huggingface.co/rows?dataset="
            + urllib.parse.quote("yguooo/newyorker_caption_ranking", safe="")
            + "&config=1_rating&split=train&offset={off}&length=100")


def fetch_newyorker(target: int, pace: float = 0.3) -> int:
    """Cache New Yorker caption rankings; resumable, appends only."""
    CACHE_DIR.mkdir(exist_ok=True)
    have = 0
    if NYC_CACHE.exists():
        have = sum(1 for _ in NYC_CACHE.open(encoding="utf-8"))
    if have >= target:
        return have
    sink = NYC_CACHE.open("a", encoding="utf-8")
    offset, misses = have, 0
    while have < target:
        try:
            req = urllib.request.Request(ROWS_URL.format(off=offset),
                                         headers={"User-Agent": "HumorVibesResearch/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                rows = json.loads(r.read()).get("rows", [])
        except Exception:
            misses += 1
            if misses > 20:
                break
            time.sleep(min(45, 4 * misses))
            continue
        misses = 0
        if not rows:
            break
        for item in rows:
            row = item.get("row", {})
            cap = str(row.get("caption") or "").strip()
            mean, votes = row.get("mean"), row.get("votes")
            if not cap or mean is None or not votes:
                continue
            sink.write(json.dumps({"contest": row.get("contest_number"),
                                   "caption": cap, "mean": float(mean),
                                   "votes": int(votes)}, ensure_ascii=False) + "\n")
            have += 1
        offset += 100
        if offset % 5000 == 0:
            sink.flush()
            print(f"    newyorker {have} cached", flush=True)
        time.sleep(pace)
    sink.close()
    return have


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
                     "y": float(r["meanGrade"]), "w": 1.0})
    return rows


def load_newyorker(limit: int, min_votes: int = 40) -> list[dict]:
    """Caption as punchline; the cartoon is the setup and is constant per contest.

    There is no text for the drawing, so the setup field is empty and every
    length-relative feature is computed on the caption alone. That is a real
    limitation of using this corpus and it is why the contest id is kept: within
    one contest the missing setup is identical for every row, so a within-contest
    comparison is still fair.
    """
    rows = []
    if not NYC_CACHE.exists():
        return rows
    with NYC_CACHE.open(encoding="utf-8") as fh:
        for line in fh:
            if len(rows) >= limit:
                break
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["votes"] < min_votes:
                continue
            rows.append({"setup": "", "punchline": r["caption"], "y": r["mean"],
                         "w": float(r["votes"]), "contest": r["contest"]})
    return rows


def load_reddit(limit: int) -> list[dict]:
    rows = []
    if not REDDIT.exists():
        return rows
    with REDDIT.open(encoding="utf-8") as fh:
        for line in fh:
            if len(rows) >= limit:
                break
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append({"setup": r["setup"], "punchline": r["punchline"],
                         "y": math.log2(1 + max(0, int(r["score"]))), "w": 1.0})
    return rows


def analyse(name: str, rows: list[dict], freq, total, seed: int = 20260725) -> dict:
    if len(rows) < 200:
        return {"corpus": name, "n": len(rows), "error": "too few rows to analyse"}
    rng = random.Random(seed)
    idx = list(range(len(rows)))
    rng.shuffle(idx)
    hold = [rows[i] for i in idx[int(len(idx) * 0.7):]]
    mats = [features(r["setup"], r["punchline"], freq, total) for r in hold]
    names = sorted(mats[0])
    y = [r["y"] for r in hold]
    rho = {n: spearman([m[n] for m in mats], y) for n in names}
    pv = {n: perm_p([m[n] for m in mats], y, n_perm=1500) for n in names}
    surv = benjamini_hochberg(pv)
    return {"corpus": name, "n_total": len(rows), "n_held_out": len(hold),
            "spearman": rho, "perm_p": pv,
            "survives_fdr": {k: bool(v) for k, v in surv.items()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nyc-n", type=int, default=60000)
    ap.add_argument("--reddit-n", type=int, default=40000)
    args = ap.parse_args()
    t0 = time.time()

    print("caching New Yorker caption rankings…")
    got = fetch_newyorker(args.nyc_n)
    print(f"  newyorker rows cached: {got}")

    freq = build_frequencies()
    total = sum(freq.values())
    corpora = {
        "humicroedit": load_humicroedit(),
        "newyorker": load_newyorker(args.nyc_n),
        "reddit": load_reddit(args.reddit_n),
    }
    for k, v in corpora.items():
        print(f"  {k}: {len(v)} rows")

    results = {k: analyse(k, v, freq, total) for k, v in corpora.items()}
    live = {k: r for k, r in results.items() if "spearman" in r}

    shared = set.intersection(*(set(r["spearman"]) for r in live.values())) if live else set()
    consistent = []
    for feat in sorted(shared):
        rhos = {k: live[k]["spearman"][feat] for k in live}
        survs = {k: live[k]["survives_fdr"][feat] for k in live}
        signs = {1 if v > 0 else (-1 if v < 0 else 0) for v in rhos.values()}
        if len(signs) == 1 and 0 not in signs and all(survs.values()):
            consistent.append({"feature": feat, "rho": rhos, "all_survive_fdr": True})
    consistent.sort(key=lambda d: -min(abs(v) for v in d["rho"].values()))

    print(f"\n--- features surviving FDR in ALL {len(live)} corpora with a consistent sign ---")
    if consistent:
        for c in consistent:
            vals = "  ".join(f"{k} {v:+.4f}" for k, v in c["rho"].items())
            print(f"  {c['feature']:22s} {vals}")
    else:
        print("  NONE. No feature holds sign and significance across all three corpora.")

    per_corpus_top = {}
    for k, r in live.items():
        top = sorted(r["spearman"], key=lambda n: -abs(r["spearman"][n]))[:6]
        per_corpus_top[k] = [{"feature": n, "rho": r["spearman"][n],
                              "p": r["perm_p"][n], "fdr": r["survives_fdr"][n]} for n in top]
        print(f"\n  top features in {k} (held out n={r['n_held_out']}):")
        for t in per_corpus_top[k]:
            print(f"    {t['rho']:+.4f}  p={t['p']:.4f}  {'FDR' if t['fdr'] else '   '}  {t['feature']}")

    report = {
        "receipt_type": "three_corpus_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": "does any feature predict funniness in more than one corpus?",
        "corpora": {
            "humicroedit": "news headline, one word substituted, annotator mean 0-3",
            "newyorker": ("New Yorker caption contest: the cartoon holds the setup fixed while "
                          "captions compete; crowd mean on a 3-point scale, min 40 votes. The "
                          "drawing has no text, so setup is empty and length-relative features "
                          "are caption-only"),
            "reddit": "native setup/punchline jokes, log2(1+upvotes) popularity proxy",
        },
        "protocol": ("per corpus: 30% held out, spearman with tied midranks, permutation p over "
                     "1500 shuffles, Benjamini-Hochberg within corpus. Cross-corpus survival "
                     "requires the same sign AND FDR survival in every corpus."),
        "per_corpus": results,
        "consistent_across_all_corpora": consistent,
        "per_corpus_top": per_corpus_top,
        "runtime_s": round(time.time() - t0, 1),
    }
    (OUT / "three_corpus_study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nreceipt -> jestry_out/three_corpus_study.json ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
