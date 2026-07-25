#!/usr/bin/env python3
"""Does the KIND of word you swap in predict how funny it lands?

Comedy craft has strong opinions about word type. Land on a concrete noun. Name
an animal, not a concept. Never end on an adverb. Those are testable claims, and
Humicroedit is the right instrument for testing them: every row is a real news
headline with exactly ONE word replaced, and a human grade for the result. The
sentence is held nearly constant; the word type is the variable.

Nothing in this project had measured that, because the features were all
lengths, distances and counts. This study adds the axis:

- **semantic category** of the replacement word, by embedding anchor
  (person, place, object, abstract, action, quality, animal, body part, food,
  occupation) using the sentence-framed classifier validated in word_taxonomy.py
- **concreteness**, a continuous score, the object-anchor similarity minus the
  abstract-anchor similarity
- **part of speech** by morphology (adverb, adjective, agent noun, verb forms,
  proper noun, function word)
- and the same for the ORIGINAL word, plus whether the edit CHANGED category,
  because a swap that moves a concept to an animal is a different comic move
  from one that swaps two animals

Two analyses, because they answer different questions:

1. **Per-category mean grade**, with counts and a permutation test against the
   pooled mean, so "animals are funnier" is either supported at some n or not.
2. **Do these features add predictive power** on top of the structural ones, or
   are they already implied by length and rarity? Measured as held-out Spearman
   with and without the type block, on the same seeded split.

    python3 word_type_study.py
"""
from __future__ import annotations

import io
import json
import math
import random
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from humor_features import build_frequencies, features, spearman
from incongruity_study import CACHE, ensure_zip
from word_taxonomy import FRAME_WORD, anchor_vectors, classify, embed, pos_guess

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
MARKER = re.compile(r"<([^/>]*)/>")
TYPE_CACHE = OUT / "word_type_cache.json"


def load_rows() -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(ensure_zip().read_bytes()))
    df = pd.read_csv(z.open("data/task-1/train.csv")).dropna(subset=["meanGrade"])
    rows = []
    for _, r in df.iterrows():
        m = MARKER.search(str(r["original"]))
        if not m:
            continue
        rows.append({"original_word": str(m.group(1)).lower(),
                     "edit_word": str(r["edit"]).lower(),
                     "setup": str(r["original"])[:m.start()].strip(),
                     "punchline": (str(r["edit"]) + str(r["original"])[m.end():]).strip(),
                     "grade": float(r["meanGrade"])})
    return rows


def type_table(words: list[str]) -> dict[str, dict]:
    """Classify a vocabulary once. Reuses the sentence-framed word cache."""
    cache: dict[str, dict] = {}
    if TYPE_CACHE.exists():
        try:
            cache = json.loads(TYPE_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    todo = [w for w in words if w not in cache]
    print(f"  vocabulary {len(words)}, cached {len(words) - len(todo)}, to classify {len(todo)}")
    if todo:
        anchors = anchor_vectors()
        t0 = time.time()
        for i in range(0, len(todo), 64):
            chunk = todo[i:i + 64]
            vecs = embed([FRAME_WORD.format(w) for w in chunk])
            if vecs is None:
                print("    embedding backend stopped responding; keeping what we have")
                break
            for w, v in zip(chunk, vecs):
                cache[w] = classify(w, v, anchors)
            if (i // 64) % 10 == 0:
                TYPE_CACHE.write_text(json.dumps(cache), encoding="utf-8")
                print(f"    {min(i + 64, len(todo))}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
        TYPE_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    return cache


def perm_mean_test(group: list[float], pool: list[float], n_perm: int = 4000,
                   seed: int = 7) -> float:
    """Is this category's mean grade unusual, given its size? Seeded."""
    if not group or len(pool) <= len(group):
        return 1.0
    rng = random.Random(seed)
    obs = abs(sum(group) / len(group) - sum(pool) / len(pool))
    k, hits = len(group), 0
    for _ in range(n_perm):
        s = rng.sample(pool, k)
        if abs(sum(s) / k - sum(pool) / len(pool)) >= obs:
            hits += 1
    return round((hits + 1) / (n_perm + 1), 4)


def main() -> None:
    t0 = time.time()
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import train_test_split

    rows = load_rows()
    print(f"graded rows: {len(rows)}")
    vocab = sorted({r["edit_word"] for r in rows} | {r["original_word"] for r in rows})
    print("classifying the edit vocabulary…")
    types = type_table(vocab)
    freq = build_frequencies()
    total = sum(freq.values())

    CATS = ["person", "place", "object", "abstract", "action", "quality",
            "animal", "body part", "food", "occupation"]
    POS = ["adverb", "adjective", "abstract_noun", "agent_noun", "verb_ing",
           "verb_ed", "plural_noun", "proper_noun", "function", "other"]

    built, skipped = [], 0
    for r in rows:
        te, to = types.get(r["edit_word"]), types.get(r["original_word"])
        if not te or not to:
            skipped += 1
            continue
        f = features(r["setup"], r["punchline"], freq, total)
        f["edit_concreteness"] = te["concreteness"]
        f["orig_concreteness"] = to["concreteness"]
        f["concreteness_shift"] = round(te["concreteness"] - to["concreteness"], 4)
        f["category_changed"] = 1.0 if te["category"] != to["category"] else 0.0
        f["edit_category_margin"] = te["category_margin"]
        for c in CATS:
            f[f"edit_is_{c.replace(' ', '_')}"] = 1.0 if te["category"] == c else 0.0
        for p in POS:
            f[f"edit_pos_{p}"] = 1.0 if te["pos_guess"] == p else 0.0
        built.append({**f, "grade": r["grade"],
                      "_cat": te["category"], "_pos": te["pos_guess"]})
    print(f"featurised {len(built)} rows ({skipped} skipped for a missing classification)")

    grades = [b["grade"] for b in built]
    pooled_mean = sum(grades) / len(grades)

    # --- 1. per-category and per-POS means -------------------------------
    def group_stats(key: str, labels: list[str]) -> list[dict]:
        out = []
        for lab in labels:
            g = [b["grade"] for b in built if b[key] == lab]
            if len(g) < 30:                     # too few to say anything
                continue
            out.append({"label": lab, "n": len(g),
                        "mean_grade": round(sum(g) / len(g), 4),
                        "delta_vs_pooled": round(sum(g) / len(g) - pooled_mean, 4),
                        "perm_p": perm_mean_test(g, grades)})
        return sorted(out, key=lambda d: -d["mean_grade"])

    cat_stats = group_stats("_cat", CATS)
    pos_stats = group_stats("_pos", POS)

    print(f"\npooled mean grade: {pooled_mean:.4f}")
    print("\n--- funniness by semantic category of the swapped-in word ---")
    print(f"  {'category':13s} {'n':>6s} {'mean':>8s} {'vs pooled':>11s} {'perm p':>8s}")
    for s in cat_stats:
        star = " *" if s["perm_p"] < 0.05 else ""
        print(f"  {s['label']:13s} {s['n']:6d} {s['mean_grade']:8.4f} "
              f"{s['delta_vs_pooled']:+11.4f} {s['perm_p']:8.4f}{star}")
    print("\n--- funniness by part of speech of the swapped-in word ---")
    print(f"  {'pos':13s} {'n':>6s} {'mean':>8s} {'vs pooled':>11s} {'perm p':>8s}")
    for s in pos_stats:
        star = " *" if s["perm_p"] < 0.05 else ""
        print(f"  {s['label']:13s} {s['n']:6d} {s['mean_grade']:8.4f} "
              f"{s['delta_vs_pooled']:+11.4f} {s['perm_p']:8.4f}{star}")

    # --- 2. do the type features ADD anything? ---------------------------
    type_names = [k for k in built[0]
                  if k.startswith(("edit_is_", "edit_pos_")) or k in
                  ("edit_concreteness", "orig_concreteness", "concreteness_shift",
                   "category_changed", "edit_category_margin")]
    struct_names = [k for k in built[0]
                    if k not in type_names and not k.startswith("_") and k != "grade"]
    y = np.array([b["grade"] for b in built])
    Xs = np.array([[b[n] for n in struct_names] for b in built], dtype=float)
    Xa = np.array([[b[n] for n in struct_names + type_names] for b in built], dtype=float)
    idx = np.arange(len(y))
    itr, ite = train_test_split(idx, test_size=0.3, random_state=20260725)

    def fit_score(X: np.ndarray) -> dict:
        m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06,
                                          random_state=20260725)
        m.fit(X[itr], y[itr])
        pred = m.predict(X[ite])
        ss_res = float(((y[ite] - pred) ** 2).sum())
        ss_tot = float(((y[ite] - y[ite].mean()) ** 2).sum())
        return {"held_out_spearman": spearman(list(pred), list(y[ite])),
                "held_out_r2": round(1 - ss_res / ss_tot, 4)}

    s_only, s_both = fit_score(Xs), fit_score(Xa)
    lift = round(s_both["held_out_spearman"] - s_only["held_out_spearman"], 4)
    print(f"\nstructural features only : spearman {s_only['held_out_spearman']:+.4f} "
          f"R2 {s_only['held_out_r2']:+.4f}  ({len(struct_names)} features)")
    print(f"structural + word type   : spearman {s_both['held_out_spearman']:+.4f} "
          f"R2 {s_both['held_out_r2']:+.4f}  ({len(struct_names) + len(type_names)} features)")
    print(f"lift from word-type features: {lift:+.4f} held-out spearman")

    report = {
        "receipt_type": "word_type_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": "does the KIND of word swapped in predict how funny the result is?",
        "dataset": "Humicroedit task-1 train, one-word substitutions into real headlines",
        "n_rows": len(built), "skipped_unclassified": skipped,
        "pooled_mean_grade": round(pooled_mean, 4),
        "classifier": ("word_taxonomy sentence-framed embedding anchors (validated 8/8 on known "
                       "cases against 4/8 for bare-word framing) + morphology part of speech"),
        "by_semantic_category": cat_stats,
        "by_part_of_speech": pos_stats,
        "predictive_lift": {"structural_only": s_only, "structural_plus_type": s_both,
                            "spearman_lift": lift,
                            "n_struct_features": len(struct_names),
                            "n_type_features": len(type_names)},
        "caveats": ("category labels come from an embedding classifier that is right about 10 of 12 "
                    "on a hand-checked demo, so category means inherit its errors; groups smaller "
                    "than 30 rows are dropped rather than reported; perm p is against the pooled "
                    "mean and is NOT corrected across the categories shown, so treat a single "
                    "starred row as a lead rather than a result"),
        "runtime_s": round(time.time() - t0, 1),
    }
    (OUT / "word_type_study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nreceipt -> jestry_out/word_type_study.json")


if __name__ == "__main__":
    main()
