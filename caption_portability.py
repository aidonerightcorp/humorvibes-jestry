#!/usr/bin/env python3
"""Is a caption funny, or is it funny AGAINST THIS DRAWING?

The whole project rests on a claim about frames: a punchline lands because it
repairs an expectation the setup built. If that is right, then funniness is not
a property of a string, and a text-only model is not merely weak but bounded.
That has never been testable here, because no corpus rated the same joke in two
different contexts.

The caption corpus does, by accident. 2,492 caption texts were submitted to more
than one contest — the same words, a different drawing, a different crowd. Each
occurrence carries its own crowd mean, so each text has two independent
standings in two different situations.

Three arms, because the raw cross-context correlation alone cannot be read:

1. **CROSS-CONTEXT.** The text's percentile standing in contest A against its
   standing in contest B. Percentiles, not means, because contests differ in
   vote scale and in how harsh their crowd is.
2. **SAME-CONTEXT CONTROL (the ceiling for arm 1).** Both measurements in arm 1
   are noisy, so even a perfectly text-intrinsic funniness would not correlate
   at 1.0. This arm splits each caption's OWN votes into halves and correlates
   the two half-standings on exactly the same items, then lifts the result to
   full length (Spearman-Brown). That is what arm 1 would read if context did
   not matter at all.
3. **PLACEBO.** Arm 1 with the partner shuffled. It has to come out at zero, and
   if it does not, the pipeline is wrong and arms 1 and 2 mean nothing.

The quantity of interest is the RATIO of arm 1 to arm 2: the share of a
caption's standing that travels with its words rather than with the drawing.

    python3 caption_portability.py
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import caption_corpus as cc
from caption_ceiling import MIN_CAPTIONS, MIN_VOTES, clean, spearman_brown, split_half
from humor_features import spearman

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"


def pct_rank(values: np.ndarray) -> np.ndarray:
    """Percentile standing within the array, ties averaged."""
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(len(values), dtype=float)
    # average ties so a block of equal means does not get an arbitrary order
    _, inv, counts = np.unique(values, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    ranks = (sums / counts)[inv]
    return ranks / max(len(values) - 1, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=20260726)
    a = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(a.seed)

    df, dropped = clean(cc.load())
    print(f"usable captions {len(df):,} (dropped {dropped:,})")

    # per-contest standings: full label, and each half of the vote split
    entries: dict[str, list[tuple]] = defaultdict(list)   # norm text -> occurrences
    n_contests = 0
    for contest, g in df.groupby("contest", observed=True):
        if len(g) < MIN_CAPTIONS:
            continue
        n_contests += 1
        C = cc.counts_matrix(g)
        means = (C * cc.SCALE).sum(axis=1) / C.sum(axis=1)
        ma, mb, keep = split_half(C, rng)
        r_full = pct_rank(means)
        r_a, r_b = pct_rank(ma), pct_rank(mb)
        votes = C.sum(axis=1)
        for i, norm in enumerate(g["norm"].to_numpy()):
            if keep[i]:
                entries[norm].append((str(contest), r_full[i], r_a[i], r_b[i],
                                      float(votes[i]), g["text"].to_numpy()[i]))

    # texts appearing in more than one contest, deterministically paired
    pairs = []
    multi3 = 0
    for norm, occ in entries.items():
        by_contest = {}
        for o in occ:
            by_contest.setdefault(o[0], o)      # first occurrence per contest
        if len(by_contest) < 2:
            continue
        if len(by_contest) > 2:
            multi3 += 1
        chosen = [by_contest[c] for c in sorted(by_contest)[:2]]
        pairs.append((norm, chosen[0], chosen[1]))

    print(f"contests {n_contests} | texts in >=2 contests: {len(pairs)} "
          f"({multi3} in 3 or more)")
    if len(pairs) < 100:
        print("too few cross-context pairs to measure")
        return 1

    x_cross = [p[1][1] for p in pairs]
    y_cross = [p[2][1] for p in pairs]
    cross = spearman(x_cross, y_cross)

    # arm 2 on exactly the same items: half-A vs half-B standing, first
    # occurrence, then Spearman-Brown to full length
    ctrl_half = spearman([p[1][2] for p in pairs], [p[1][3] for p in pairs])
    ctrl_full = spearman_brown(ctrl_half)

    # arm 3: placebo
    idx = rng.permutation(len(pairs))
    placebo = spearman(x_cross, [y_cross[i] for i in idx])

    share = cross / ctrl_full if ctrl_full > 0 else float("nan")

    # What arm 1 implies for any text-only model.
    #   standing = T(text) + C(fit with this drawing) + E(vote noise)
    # With C and E independent between contests, the correlation between the two
    # standings of one text IS var(T)/var(standing). A model that sees only the
    # text can at best predict T, and corr(T, standing) = sqrt(var(T)/var(standing)).
    # So the bound on a perfect text-only predictor is sqrt(arm 1).
    text_only_bound = float(np.sqrt(max(cross, 0.0)))
    print(f"\n1. CROSS-CONTEXT  same words, different drawing   spearman {cross:+.4f}  n={len(pairs)}")
    print(f"2. SAME-CONTEXT   same words, same drawing (ceiling) {ctrl_full:+.4f}  "
          f"(half-split {ctrl_half:+.4f})")
    print(f"3. PLACEBO        partner shuffled                  {placebo:+.4f}")
    print(f"\nportable share = arm1 / arm2 = {share:.3f}")
    print(f"implied bound on ANY text-only predictor (within contest): "
          f"spearman <= sqrt({cross:.4f}) = {text_only_bound:.3f}")

    # the items themselves: what travels and what does not
    deltas = [(abs(p[1][1] - p[2][1]), p) for p in pairs]
    deltas.sort(key=lambda kv: -kv[0])
    def show(entry):
        _, p = entry
        return {"text": p[1][5][:150], "contest_a": p[1][0], "standing_a": round(p[1][1], 3),
                "contest_b": p[2][0], "standing_b": round(p[2][1], 3),
                "votes_a": p[1][4], "votes_b": p[2][4]}
    most_context = [show(e) for e in deltas[:6]]
    most_portable = [show(e) for e in deltas[-6:]]
    print("\nmost context-dependent (same words, opposite reception):")
    for r in most_context[:4]:
        print(f"   {r['standing_a']:.2f} -> {r['standing_b']:.2f}  {r['text'][:90]!r}")

    if cross <= 0.02:
        verdict = ("caption standing does not travel at all: the same words land in an "
                   "unrelated place against a different drawing, so funniness here is a "
                   "property of the text-in-context and any text-only predictor is "
                   "bounded well below the label's own reliability")
    elif share < 0.5:
        verdict = (f"a minority of standing travels with the words ({share:.0%} of what "
                   "the label's reliability would allow); most of a caption's reception "
                   "belongs to its fit with the drawing, which bounds text-only models")
    else:
        verdict = (f"most of a caption's standing travels with its words ({share:.0%} of "
                   "the reliability ceiling), so text-only prediction is not the binding "
                   "constraint on this corpus")
    print(f"\nverdict: {verdict}")

    report = {
        "receipt_type": "caption_portability",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": "does a caption's funniness travel with its words to a different drawing?",
        "protocol": {
            "standing": "percentile rank of the crowd mean within its own contest, ties averaged",
            "pairing": "texts normalised for case/whitespace/curly-quotes; first occurrence "
                       "per contest; the two lowest-numbered contests when a text appears in more",
            "control": "split-half of the SAME captions' own votes, Spearman-Brown lifted "
                       "to full length — the value arm 1 would take if context were irrelevant",
            "min_votes_per_caption": MIN_VOTES,
            "min_captions_per_contest": MIN_CAPTIONS,
            "seed": a.seed,
        },
        "n_pairs": len(pairs),
        "n_texts_in_3_or_more_contests": multi3,
        "results": {
            "cross_context_spearman": cross,
            "same_context_ceiling_spearman": ctrl_full,
            "same_context_half_split_spearman": ctrl_half,
            "placebo_spearman": placebo,
            "portable_share": share,
            "text_only_predictor_bound": text_only_bound,
        },
        "text_only_bound_derivation": (
            "standing = T(text) + C(fit with this drawing) + E(vote noise); C and E "
            "independent across contests makes arm 1 equal to var(T)/var(standing), so a "
            "perfect text-only predictor correlates with standing at sqrt(arm 1). Read "
            "as an UPPER bound: texts that recur across contests skew generic, which "
            "inflates arm 1."),
        "verdict": verdict,
        "examples_most_context_dependent": most_context,
        "examples_most_portable": most_portable,
        "caveats": ("a text submitted to two contests is not a random caption — it is more "
                    "likely to be generic, which if anything HELPS it travel, so this is an "
                    "upper bound on portability rather than a lower one"),
        "runtime_s": round(time.time() - t0, 1),
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "caption_portability.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("receipt -> jestry_out/caption_portability.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
