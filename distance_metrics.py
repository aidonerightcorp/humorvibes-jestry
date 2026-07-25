#!/usr/bin/env python3
"""Which notion of "semantic distance" actually predicts funniness?

The incongruity study measures the gap between a headline's original word and
its replacement with one metric, cosine distance, because that is the default
everyone reaches for. Cosine is a choice, not a law: it normalises both vectors
first, so it deliberately discards magnitude. In most embedding spaces magnitude
carries real information, roughly how specific or heavily-attested a token is,
and throwing it away might be discarding exactly the part that makes a
substitution land.

So this compares eight ways of measuring the same gap, on the same word pairs,
against the same held-out split:

- **cosine**        angle only, magnitude discarded (the default)
- **angular**       arccos of cosine, a true metric rather than a similarity
- **euclidean**     straight-line L2, sensitive to both angle and magnitude
- **manhattan**     L1, which weights many small coordinate shifts as heavily as
                    one large one, a different theory of what "different" means
- **chebyshev**     L-infinity, dominated by the single most-changed dimension
- **dot**           unnormalised inner product, angle and magnitude together
- **mag_diff**      |‖orig‖ - ‖edit‖|, magnitude change ALONE, no direction
- **mag_ratio**     ‖edit‖ / ‖orig‖, whether the replacement is a heavier or
                    lighter word in the space

If cosine wins, the default was right and that is worth knowing. If a
magnitude-aware metric wins, the field's habit of normalising first is throwing
away signal on this task, which is a more interesting result.

Protocol is inherited unchanged from the incongruity study: the same seeded
70/30 split, held-out test correlations, permutation p, and Benjamini-Hochberg
control across all eight metrics so that picking the winner is itself corrected.

    python3 distance_metrics.py
"""
from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from humor_features import benjamini_hochberg, perm_p, spearman
from incongruity_study import CACHE, load_rows

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"


def norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def metrics(a: list[float], b: list[float]) -> dict[str, float]:
    na, nb = norm(a), norm(b)
    dot = sum(x * y for x, y in zip(a, b))
    cos = dot / (na * nb) if na and nb else 0.0
    cos_clamped = max(-1.0, min(1.0, cos))
    return {
        "cosine": 1.0 - cos,
        "angular": math.acos(cos_clamped) / math.pi,
        "euclidean": math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))),
        "manhattan": sum(abs(x - y) for x, y in zip(a, b)),
        "chebyshev": max(abs(x - y) for x, y in zip(a, b)) if a else 0.0,
        "dot": dot,
        "mag_diff": abs(na - nb),
        "mag_ratio": (nb / na) if na else 0.0,
    }


def main() -> None:
    t0 = time.time()
    if not CACHE.exists():
        raise SystemExit("no word embedding cache yet; run incongruity_study.py first")
    emb = json.loads(CACHE.read_text(encoding="utf-8"))
    rows = load_rows(None)
    print(f"rows {len(rows)}, cached word vectors {len(emb)}")

    built = []
    skipped = 0
    for r in rows:
        a, b = emb.get(r["original_word"]), emb.get(r["edit_word"])
        if not a or not b:
            skipped += 1
            continue
        built.append({**metrics(a, b), "grade": r["grade"]})
    print(f"pairs with both vectors: {len(built)} (skipped {skipped})")

    names = [k for k in built[0] if k != "grade"]
    rng = random.Random(20260725)          # same seed and split as the incongruity study
    idx = list(range(len(built)))
    rng.shuffle(idx)
    cut = int(len(idx) * 0.7)
    train = [built[i] for i in idx[:cut]]
    test = [built[i] for i in idx[cut:]]
    gtr = [r["grade"] for r in train]
    gte = [r["grade"] for r in test]

    tr = {n: spearman([r[n] for r in train], gtr) for n in names}
    te = {n: spearman([r[n] for r in test], gte) for n in names}
    pv = {n: perm_p([r[n] for r in test], gte, n_perm=2000) for n in names}
    surv = benjamini_hochberg(pv)

    table = sorted(
        ({"metric": n, "train_rho": tr[n], "test_rho": te[n], "test_perm_p": pv[n],
          "survives_fdr": surv[n], "sign_held": (tr[n] > 0) == (te[n] > 0)} for n in names),
        key=lambda d: -abs(d["test_rho"]))

    winners = [t for t in table if t["survives_fdr"]]
    best = table[0] if table else None
    magnitude_aware = {"euclidean", "manhattan", "chebyshev", "dot", "mag_diff", "mag_ratio"}
    # Several of these are monotone transforms of one another on this data, so
    # they are ONE test reported many times and their rank correlations come out
    # identical. Saying "metric X beats cosine" off a 0.003 gap between two
    # statistically indistinguishable, partly-redundant measures would be exactly
    # the noise-ranking this project keeps warning about.
    by_rho: dict[float, list[str]] = {}
    for t in table:
        by_rho.setdefault(round(abs(t["test_rho"]), 4), []).append(t["metric"])
    redundant = {k: v for k, v in by_rho.items() if len(v) > 1}
    cos_rho = abs(next(t["test_rho"] for t in table if t["metric"] == "cosine"))
    gap = abs(best["test_rho"]) - cos_rho if best else 0.0
    if not winners:
        verdict = ("NO metric survives multiple-comparison control, so no distance measure here "
                   "reliably predicts funniness and none can be called the winner. The best and "
                   f"cosine differ by {gap:.4f} in held-out rho, which is noise at this n.")
    elif best["metric"] in magnitude_aware and gap > 0.02:
        verdict = ("a magnitude-aware metric beats plain cosine by a margin that survives "
                   "correction, so normalising first discards signal on this task")
    else:
        verdict = ("cosine is not beaten by any margin that survives correction; the ranking "
                   "among these metrics is not interpretable")

    report = {
        "receipt_type": "distance_metric_comparison",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": ("cosine discards magnitude by construction; does any magnitude-aware "
                     "distance predict funniness better on the same word pairs?"),
        "dataset": "Humicroedit task-1, original word vs replacement word",
        "embedding_model": "embeddinggemma (768d)",
        "n_pairs": len(built), "n_train": len(train), "n_test": len(test),
        "protocol": ("same seeded 70/30 split as incongruity_study.py; held-out test "
                     "correlations with permutation p over 2000 shuffles and "
                     "Benjamini-Hochberg control across all eight metrics"),
        "results_ranked_by_test": table,
        "survivors": [w["metric"] for w in winners],
        "best_metric_by_point_estimate": best["metric"] if best else None,
        "metrics_with_identical_rho": redundant,
        "redundancy_note": ("cosine, angular, euclidean and dot are monotone transforms of one "
                            "another for these vectors, so rank correlation cannot distinguish "
                            "them; they are one test, not four, and the FDR denominator is "
                            "correspondingly inflated"),
        "verdict": verdict,
    }
    (OUT / "distance_metric_comparison.json").write_text(json.dumps(report, indent=2),
                                                         encoding="utf-8")
    print(f"\n--- held-out test, ranked (n_test={len(test)}) ---")
    for t in table:
        flag = "SURVIVES" if t["survives_fdr"] else "        "
        print(f"  train {t['train_rho']:+.4f} | test {t['test_rho']:+.4f} "
              f"p={t['test_perm_p']:.4f} {flag}  {t['metric']}")
    print(f"\nverdict: {verdict}")
    print(f"runtime {time.time() - t0:.0f}s -> jestry_out/distance_metric_comparison.json")


if __name__ == "__main__":
    main()
