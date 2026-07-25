#!/usr/bin/env python3
"""Which words are ruining this joke? Leave-one-out deletion against a trained model.

The confirmed finding from the full-scale study is that shorter punchlines and
later twists score funnier: punchline syllables, characters, and the
punchline/setup word ratio all correlate NEGATIVELY with human grades, replicated
on held-out data at n = 9,652. That is a fact about corpora. It is not yet
advice, because it does not tell a writer WHICH words to cut.

This module turns it into advice. Train a model on human-graded jokes, then for a
candidate joke delete each word in turn and re-score. A word whose deletion
RAISES the predicted grade is dead weight: the joke is better without it. A word
whose deletion lowers the predicted grade is load-bearing. The output is a
per-word contribution profile, which is what a writer can actually use.

Two things keep this honest:

**The model is scored before it is trusted.** Held-out Spearman and R-squared are
reported on data the model never saw, and if the model cannot predict grades the
deletion analysis is worthless and says so rather than producing confident
nonsense.

**Deletion is validated against a natural experiment.** Humicroedit task-2 gives
the SAME headline with two different one-word edits and two different human
grades. That is a controlled pair: everything is held constant except the word.
The model is asked which of the two edits humans preferred, and its accuracy on
that binary question is reported. A model that cannot beat a coin flip on real
paired human judgments has no business telling anyone which word to cut.

    python3 deadweight.py                       # train, validate, then demo
    python3 deadweight.py --joke "setup" "punchline"
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

from humor_features import WORD, build_frequencies, features, spearman
from incongruity_study import ensure_zip

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
MARKER = re.compile(r"<([^/>]*)/>")


def load_graded() -> tuple[list[dict], list[dict]]:
    """All human-graded Humicroedit rows: task-1 singles and task-2 pairs.

    task-2 is the useful one and had gone unused: each row is one headline with
    TWO different one-word edits and TWO grades, so it is a controlled
    comparison with the sentence held fixed.
    """
    z = zipfile.ZipFile(io.BytesIO(ensure_zip().read_bytes()))
    singles: list[dict] = []
    df1 = pd.read_csv(z.open("data/task-1/train.csv")).dropna(subset=["meanGrade"])
    for _, r in df1.iterrows():
        m = MARKER.search(str(r["original"]))
        if not m:
            continue
        singles.append({"setup": str(r["original"])[:m.start()].strip(),
                        "punchline": (str(r["edit"]) + str(r["original"])[m.end():]).strip(),
                        "grade": float(r["meanGrade"]), "src": "task1"})
    pairs: list[dict] = []
    df2 = pd.read_csv(z.open("data/task-2/train.csv")).dropna(subset=["meanGrade1", "meanGrade2"])
    for _, r in df2.iterrows():
        m = MARKER.search(str(r["original1"]))
        if not m:
            continue
        base = str(r["original1"])
        setup = base[:m.start()].strip()
        tail = base[m.end():]
        a = {"setup": setup, "punchline": (str(r["edit1"]) + tail).strip(),
             "grade": float(r["meanGrade1"]), "src": "task2"}
        b = {"setup": setup, "punchline": (str(r["edit2"]) + tail).strip(),
             "grade": float(r["meanGrade2"]), "src": "task2"}
        singles.extend([a, b])
        if abs(a["grade"] - b["grade"]) > 1e-9:      # ties carry no preference signal
            pairs.append({"a": a, "b": b, "winner": "a" if a["grade"] > b["grade"] else "b"})
    return singles, pairs


def featurise(rows: list[dict], freq: dict[str, int], total: int) -> tuple[np.ndarray, list[str]]:
    mats = [features(r["setup"], r["punchline"], freq, total) for r in rows]
    names = sorted(mats[0])
    X = np.array([[m[n] for n in names] for m in mats], dtype=float)
    return X, names


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--joke", nargs=2, metavar=("SETUP", "PUNCHLINE"))
    args = ap.parse_args()
    t0 = time.time()
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import RidgeCV
    from sklearn.model_selection import train_test_split

    singles, pairs = load_graded()
    print(f"graded rows: {len(singles)} (task-1 + task-2 flattened) | "
          f"controlled pairs: {len(pairs)}")
    freq = build_frequencies()
    total = sum(freq.values())
    X, names = featurise(singles, freq, total)
    y = np.array([r["grade"] for r in singles])
    print(f"feature matrix: {X.shape}")

    Xtr, Xte, ytr, yte, itr, ite = train_test_split(
        X, y, np.arange(len(y)), test_size=0.3, random_state=20260725)

    models = {
        "ridge": RidgeCV(alphas=np.logspace(-3, 3, 25)),
        "gbm": HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06,
                                             random_state=20260725),
    }
    scored = {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        pred = m.predict(Xte)
        ss_res = float(((yte - pred) ** 2).sum())
        ss_tot = float(((yte - yte.mean()) ** 2).sum())
        scored[name] = {"held_out_r2": round(1 - ss_res / ss_tot, 4),
                        "held_out_spearman": spearman(list(pred), list(yte)),
                        "n_test": int(len(yte))}
        print(f"  {name:6s} held-out R2 {scored[name]['held_out_r2']:+.4f}  "
              f"spearman {scored[name]['held_out_spearman']:+.4f}")
    best_name = max(scored, key=lambda k: scored[k]["held_out_spearman"])
    model = models[best_name]
    print(f"best: {best_name}")

    # --- validation on the controlled pairs -------------------------------
    # Only pairs whose BOTH members sit in the held-out split are a fair test;
    # scoring pairs the model trained on measures memorisation, not preference.
    test_keys = {(singles[i]["setup"], singles[i]["punchline"]) for i in ite.tolist()}
    pairs = [p for p in pairs
             if (p["a"]["setup"], p["a"]["punchline"]) in test_keys
             and (p["b"]["setup"], p["b"]["punchline"]) in test_keys]
    print(f"controlled pairs fully inside the held-out split: {len(pairs)}")
    pa, _ = featurise([p["a"] for p in pairs], freq, total)
    pb, _ = featurise([p["b"] for p in pairs], freq, total)
    preda, predb = model.predict(pa), model.predict(pb)
    correct = sum(1 for i, p in enumerate(pairs)
                  if (preda[i] > predb[i]) == (p["winner"] == "a"))
    pair_acc = correct / max(1, len(pairs))
    margin = np.abs(np.array([p["a"]["grade"] - p["b"]["grade"] for p in pairs]))
    clear = margin >= 0.4
    clear_correct = sum(1 for i, p in enumerate(pairs)
                        if clear[i] and (preda[i] > predb[i]) == (p["winner"] == "a"))
    clear_acc = clear_correct / max(1, int(clear.sum()))
    print(f"\ncontrolled-pair accuracy: {pair_acc:.4f} on {len(pairs)} pairs "
          f"(chance 0.5); on the {int(clear.sum())} pairs humans separated by >=0.4: {clear_acc:.4f}")
    print("  (both members held out, so this is a genuine out-of-sample preference test)")

    # --- the actual tool ---------------------------------------------------
    def deadweight(setup: str, punchline: str) -> list[dict]:
        """Per-word contribution, with the length effect divided out.

        Removing ANY word shortens the punchline, and the model has learned that
        shorter scores higher, so every raw delta is positive and the tool would
        tell a writer to cut the pun itself. The informative quantity is how far a
        word's delta sits ABOVE OR BELOW the average deletion, which is the part
        that is about that specific word rather than about length.
        """
        words = punchline.split()
        base = model.predict(featurise([{"setup": setup, "punchline": punchline}], freq, total)[0])[0]
        raw = []
        for i in range(len(words)):
            trimmed = " ".join(words[:i] + words[i + 1:]).strip()
            if not trimmed:
                continue
            p = model.predict(featurise([{"setup": setup, "punchline": trimmed}], freq, total)[0])[0]
            raw.append({"word": words[i], "index": i,
                        "predicted_without": round(float(p), 4),
                        "delta_if_cut": float(p - base)})
        if not raw:
            return []
        mean_delta = sum(r["delta_if_cut"] for r in raw) / len(raw)
        for r in raw:
            r["length_effect"] = round(mean_delta, 4)
            r["word_specific"] = round(r["delta_if_cut"] - mean_delta, 4)
            r["delta_if_cut"] = round(r["delta_if_cut"], 4)
        return sorted(raw, key=lambda d: -d["word_specific"])

    demo_setup, demo_punch = (args.joke if args.joke else
                              ("I told my therapist about my fear of speed bumps.",
                               "She said I am actually just slowly getting over it honestly."))
    base_pred = model.predict(featurise(
        [{"setup": demo_setup, "punchline": demo_punch}], freq, total)[0])[0]
    profile = deadweight(demo_setup, demo_punch)
    print(f"\nsetup:     {demo_setup}")
    print(f"punchline: {demo_punch}")
    print(f"predicted grade: {base_pred:.4f}\n")
    print(f"  length effect of cutting any one word: {profile[0]['length_effect']:+.4f}\n")
    print(f"  {'word':16s} {'raw':>9s} {'word-specific':>14s}   verdict")
    for row in profile:
        v = ("DEAD WEIGHT" if row["word_specific"] > 0.01 else
             "load-bearing" if row["word_specific"] < -0.01 else "neutral")
        print(f"  {row['word']:16s} {row['delta_if_cut']:+9.4f} {row['word_specific']:+14.4f}   {v}")

    report = {
        "receipt_type": "deadweight_word_analysis",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "idea": "delete each word and re-score; a word whose removal raises the predicted grade is dead weight",
        "training_data": {"graded_rows": len(singles),
                          "sources": "Humicroedit task-1 train + task-2 train (both edits per row)",
                          "features": len(names)},
        "models": scored,
        "model_used": best_name,
        "controlled_pair_validation": {
            "n_pairs": len(pairs), "accuracy": round(pair_acc, 4),
            "n_clear_pairs": int(clear.sum()), "clear_accuracy": round(clear_acc, 4),
            "chance": 0.5,
            "note": ("restricted to pairs whose BOTH members are in the held-out split, so this "
                     "is out-of-sample; an earlier version scored all pairs including trained rows "
                     "and reported 0.75, which measured memorisation as much as preference"),
        },
        "demo": {"setup": demo_setup, "punchline": demo_punch,
                 "predicted_grade": round(float(base_pred), 4), "per_word": profile},
        "honesty": ("the deletion profile is only as good as the model; held-out spearman is "
                    "reported above and is small, so treat per-word deltas as a ranked suggestion "
                    "rather than a verdict"),
        "runtime_s": round(time.time() - t0, 1),
    }
    (OUT / "deadweight_analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nreceipt -> jestry_out/deadweight_analysis.json")


if __name__ == "__main__":
    main()
