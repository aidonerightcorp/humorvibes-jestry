#!/usr/bin/env python3
"""Full-scale incongruity study: does semantic distance predict funniness?

Every null result in this project so far shares one property: it was measured on
83 items, because that is how many rows the expensive Gemma instrument could
reach in an evening. Nothing survives multiple-comparison control at that size,
so "no effect" and "no power" are indistinguishable. This study removes that
excuse. Humicroedit ships 9,652 human-graded rows; surface features cost
microseconds and word embeddings cost one pass over a 6.5k vocabulary, so the
whole set is affordable.

It also tests the attribute incongruity theory actually predicts for this
dataset, which nothing here had measured. Humicroedit's humor comes from
replacing exactly one word in a real news headline. The theory says the joke
lives in the gap between what stood there and what replaced it: too near and
nothing happens, too far and it is noise rather than wit. That gap is a cosine
distance between two word embeddings, and at n = 9,652 it is measurable.

Custom attributes built here (none existed before):

- ``edit_distance_cos``   semantic distance between the ORIGINAL word and its
                          replacement, the direct incongruity measure
  (An earlier version also included the SQUARE of that distance, meaning to test
  an inverted-U. Spearman is invariant to monotone transforms and the distance is
  strictly positive, so the square was the identical test counted twice; it padded
  the multiple-comparison correction and was removed. Testing a genuine sweet-spot
  shape needs a non-monotone statistic, which is listed as open work rather than
  faked here.)
- ``edit_rarity_delta``   how much rarer the replacement is than the original,
                          in this project's own corpus
- ``edit_position``       where in the headline the substitution lands, since
                          comic timing says late is stronger
- ``edit_len_delta``      length and syllable change introduced by the edit

Protocol, fixed before looking at any result: a seeded 70/30 split. Features are
ranked on TRAIN only; the reported number for every headline claim is its
held-out TEST correlation, with permutation p and Benjamini-Hochberg control
across the whole feature set. A train-selected feature that dies on test is
reported as dying.

    python3 incongruity_study.py            # full run
    python3 incongruity_study.py --limit 800
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import random
import re
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from humor_features import (WORD, benjamini_hochberg, build_frequencies, features,
                            perm_p, spearman, syllables)

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
ZIP_URL = "https://cs.rochester.edu/u/nhossain/humicroedit/semeval-2020-task-7-data.zip"
ZIP_PATH = Path(os.environ.get("HUMICROEDIT_ZIP", HERE / "data_cache" / "humicroedit.zip"))


def ensure_zip() -> Path:
    """Fetch the dataset if absent, so a judge with a clone can run this."""
    if ZIP_PATH.exists():
        return ZIP_PATH
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetching {ZIP_URL} …")
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "HumorVibes research"})
    with urllib.request.urlopen(req, timeout=180) as r:
        ZIP_PATH.write_bytes(r.read())
    return ZIP_PATH
MARKER = re.compile(r"<([^/>]*)/>")
HOST = "http://127.0.0.1:11434"
EMB_MODEL = "embeddinggemma"
CACHE = OUT / "word_embeddings_cache.json"


def embed_words(words: list[str], batch_log: int = 500) -> dict[str, list[float]]:
    """Embed a vocabulary once, cached on disk so reruns are free."""
    cache: dict[str, list[float]] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    todo = [w for w in words if w not in cache]
    print(f"  vocabulary {len(words)}, cached {len(words) - len(todo)}, to embed {len(todo)}")
    t0 = time.time()
    for i, w in enumerate(todo, 1):
        body = json.dumps({"model": EMB_MODEL, "prompt": w}).encode()
        req = urllib.request.Request(f"{HOST}/api/embeddings", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                v = json.loads(r.read()).get("embedding")
            if v:
                cache[w] = v
        except Exception as exc:
            print(f"    embed failed on {w!r}: {type(exc).__name__}")
        if i % batch_log == 0:
            print(f"    {i}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
            CACHE.write_text(json.dumps(cache), encoding="utf-8")
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return cache


def cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def load_rows(limit: int | None) -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(ensure_zip().read_bytes()))
    name = [n for n in z.namelist() if n.endswith("train.csv") and "task-1" in n][0]
    df = pd.read_csv(z.open(name)).dropna(subset=["meanGrade"])
    if limit:
        df = df.head(limit)
    rows = []
    for _, r in df.iterrows():
        m = MARKER.search(str(r["original"]))
        if not m:
            continue
        rows.append({
            "id": int(r["id"]),
            "original_word": str(m.group(1)).lower(),
            "edit_word": str(r["edit"]).lower(),
            "setup": str(r["original"])[:m.start()].strip(),
            "punchline": (str(r["edit"]) + str(r["original"])[m.end():]).strip(),
            "full_edited": MARKER.sub(str(r["edit"]), str(r["original"])),
            "edit_char_pos": m.start() / max(1, len(str(r["original"]))),
            "grade": float(r["meanGrade"]),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    t0 = time.time()

    rows = load_rows(args.limit)
    print(f"graded rows: {len(rows)}")
    freq = build_frequencies()
    total = sum(freq.values())

    vocab = sorted({r["original_word"] for r in rows} | {r["edit_word"] for r in rows})
    print("embedding the edit vocabulary…")
    emb = embed_words(vocab)

    def nlf(w: str) -> float:
        return -math.log((freq.get(w, 0) + 1) / (total + 1))

    built = []
    missing_emb = 0
    for r in rows:
        f = features(r["setup"], r["punchline"], freq, total)
        ov, ev = emb.get(r["original_word"]), emb.get(r["edit_word"])
        if ov and ev:
            d = 1.0 - cos(ov, ev)
        else:
            d = None
            missing_emb += 1
        f["edit_distance_cos"] = round(d, 5) if d is not None else 0.0
        f["edit_rarity_delta"] = round(nlf(r["edit_word"]) - nlf(r["original_word"]), 4)
        f["edit_rarity"] = round(nlf(r["edit_word"]), 4)
        f["edit_position"] = round(r["edit_char_pos"], 4)
        f["edit_len_delta"] = len(r["edit_word"]) - len(r["original_word"])
        f["edit_syl_delta"] = syllables(r["edit_word"]) - syllables(r["original_word"])
        built.append({**f, "grade": r["grade"], "id": r["id"]})
    print(f"featurised {len(built)} rows ({missing_emb} without an embedding pair)")

    feat_names = [k for k in built[0] if k not in ("grade", "id")]
    rng = random.Random(20260725)
    idx = list(range(len(built)))
    rng.shuffle(idx)
    cut = int(len(idx) * 0.7)
    train = [built[i] for i in idx[:cut]]
    test = [built[i] for i in idx[cut:]]
    print(f"split: train {len(train)}, test {len(test)} (seeded, fixed before inspection)")

    gtr = [r["grade"] for r in train]
    gte = [r["grade"] for r in test]
    train_rho = {n: spearman([r[n] for r in train], gtr) for n in feat_names}
    test_rho = {n: spearman([r[n] for r in test], gte) for n in feat_names}
    test_p = {n: perm_p([r[n] for r in test], gte, n_perm=2000) for n in feat_names}
    survive = benjamini_hochberg(test_p)

    ranked = sorted(feat_names, key=lambda n: -abs(train_rho[n]))
    # Confirmatory protocol. Choosing "survivors" by test p-value is selection on
    # the test set, which is the error this split exists to prevent (adversarial
    # audit, 2026-07-25). So the top K by TRAIN rank are pre-registered, and FDR
    # is applied across only those K test p-values. Everything below K is
    # exploratory and labelled as such, never as a finding.
    K = 5
    preregistered = ranked[:K]
    conf_survive = benjamini_hochberg({n: test_p[n] for n in preregistered})
    table = [{"feature": n, "train_rank": i + 1, "train_rho": train_rho[n],
              "test_rho": test_rho[n], "test_perm_p": test_p[n],
              "preregistered": n in preregistered,
              "confirmed": bool(conf_survive.get(n, False)),
              "exploratory_fdr_only": survive[n],
              "sign_held": (train_rho[n] > 0) == (test_rho[n] > 0)}
             for i, n in enumerate(ranked)]
    winners = [t for t in table if t["confirmed"]]

    report = {
        "receipt_type": "incongruity_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": ("at full sample size, does anything predict human funniness, and does "
                     "semantic distance between the replaced word and its replacement "
                     "carry the signal incongruity theory predicts?"),
        "dataset": "Humicroedit task-1 train.csv, all graded rows",
        "n_total": len(built), "n_train": len(train), "n_test": len(test),
        "n_features": len(feat_names),
        "embedding_model": EMB_MODEL,
        "vocabulary_this_run": len(vocab),
        "vocabulary_with_vectors": sum(1 for w in vocab if w in emb),
        "pairs_missing_an_embedding": missing_emb,
        "protocol": ("seeded 70/30 split fixed before inspection. The top 5 features by TRAIN "
                     "rank are pre-registered; Benjamini-Hochberg FDR at 0.05 is then applied to "
                     "those 5 HELD-OUT TEST permutation p-values only. Features outside the top 5 "
                     "are exploratory and are not findings, however good their test p looks."),
        "preregistered_top_k_on_train": preregistered,
        "confirmed_on_held_out_test": [w["feature"] for w in winners],
        "n_survivors": len(winners),
        "table_ranked_by_train": table,
        "custom_attributes": ["edit_distance_cos", "edit_rarity_delta",
                              "edit_rarity", "edit_position", "edit_len_delta", "edit_syl_delta"],
        "runtime_s": round(time.time() - t0, 1),
    }
    (OUT / "incongruity_study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n--- held-out test correlations, top 16 by train rank (n_test={len(test)}) ---")
    for t in table[:16]:
        flag = "CONFIRMED" if t["confirmed"] else ("prereg   " if t["preregistered"] else "exploratory")
        print(f"  train {t['train_rho']:+.4f} | test {t['test_rho']:+.4f} "
              f"p={t['test_perm_p']:.4f} {flag}  {t['feature']}")
    print(f"\npre-registered on train: {preregistered}")
    print(f"CONFIRMED on held-out test (FDR over those {K} only): {len(winners)}")
    for w in winners:
        print(f"  {w['test_rho']:+.4f}  p={w['test_perm_p']:.4f}  {w['feature']}")
    print("receipt -> jestry_out/incongruity_study.json")


if __name__ == "__main__":
    main()
