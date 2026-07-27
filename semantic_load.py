#!/usr/bin/env python3
"""Which words carry the joke's meaning? The signal the structural model lacks.

`deadweight.py` ranks words by how much a trained model's predicted grade moves
when each is deleted. It correctly finds filler, and it published its own
failure: on "She said I am actually just slowly getting over it honestly" it
ranks *slowly* and *getting* as dead weight, when those two words ARE the pun.
The cause is not the model, it is the feature set. Lengths, syllables, rarity
and position cannot represent the fact that a plain word is holding a reframe.

This module supplies the missing axis directly, without a trained model:

    semantic_load(word) = cos(setup, punchline) - cos(setup, punchline_minus_word)

A word whose removal breaks the punchline's semantic tie back to the setup has
HIGH load: it is the bridge. A word whose removal leaves that tie untouched has
near-zero load: it is decoration. "Speed bumps" and "slowly getting over"
connect through exactly this relationship, and no length feature can see it.

The two signals answer different questions and are reported side by side rather
than blended into one score, because they disagree usefully:

    structural delta   does cutting this word make the line tighter?
    semantic load      does cutting this word break what the line MEANS?

A word that is structurally cuttable AND semantically inert is safe to cut. A
word that is structurally cuttable but semantically load-bearing is exactly the
trap the previous version fell into, and the combined verdict names it as such.

    python3 semantic_load.py                          # demo, including the failing case
    python3 semantic_load.py --joke "setup" "punchline"
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from humorvibes.config import Settings
from humorvibes.embeddings import OllamaEmbeddingBackend, cosine_similarity
from humorvibes.errors import IntegrationError

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
RUNTIME = Settings.from_env()
EMB_MODEL = os.environ.get("HUMORVIBES_SEMANTIC_LOAD_EMBED_MODEL", "embeddinggemma")


def embed(texts: list[str], timeout: float = 120.0) -> list[list[float]] | None:
    runtime = Settings.from_env({**os.environ, "HUMORVIBES_REQUEST_TIMEOUT": str(timeout)})
    try:
        return OllamaEmbeddingBackend(runtime, EMB_MODEL).embed(texts).vectors
    except IntegrationError:
        return None


def cos(a, b) -> float:
    return cosine_similarity(a, b)


def semantic_profile(setup: str, punchline: str, skip_function: bool = True) -> dict | None:
    """Per-word semantic load: how much removing it breaks the setup link.

    Function words are skipped by default, measured rather than assumed: with
    them included, "and", "a" and "the" ranked as the most load-bearing words in
    the lion/zoo joke, because deleting a function word from a short string
    perturbs the embedding through grammaticality rather than meaning. Excluding
    them moved the real payoff word ("zoo") to the top of that ranking.
    """
    from word_taxonomy import FUNCTION_WORDS
    all_words = punchline.split()
    if not all_words:
        return None
    keep = [i for i, w in enumerate(all_words)
            if not (skip_function and w.lower().strip(".,!?'\";:") in FUNCTION_WORDS)]
    if not keep:
        keep = list(range(len(all_words)))
    words = [all_words[i] for i in keep]
    variants = [punchline] + [" ".join(all_words[:i] + all_words[i + 1:]).strip()
                              for i in keep]
    vecs = embed([setup] + variants)
    if vecs is None:
        return None
    setup_vec, full_vec, minus_vecs = vecs[0], vecs[1], vecs[2:]
    base_link = cos(setup_vec, full_vec)
    rows = []
    for w, v in zip(words, minus_vecs):
        link = cos(setup_vec, v)
        rows.append({"word": w, "link_without": round(link, 5),
                     "semantic_load": round(base_link - link, 5)})
    loads = [r["semantic_load"] for r in rows]
    mean_load = sum(loads) / len(loads)
    for r in rows:
        # centre for the same reason deadweight.py centres its deltas: removing
        # ANY word shortens the string and nudges the embedding, so the shared
        # part is not about this particular word
        r["load_relative"] = round(r["semantic_load"] - mean_load, 5)
    return {"setup_punchline_link": round(base_link, 5),
            "mean_load": round(mean_load, 5),
            "content_words_scored": len(rows),
            "function_words_skipped": len(all_words) - len(rows),
            "words": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--joke", nargs=2, metavar=("SETUP", "PUNCHLINE"))
    args = ap.parse_args()
    t0 = time.time()

    cases = [args.joke] if args.joke else [
        # the case deadweight.py gets wrong, kept as the first test
        ("I told my therapist about my fear of speed bumps.",
         "She said I am actually just slowly getting over it honestly."),
        # a clean one-liner, to check the signal is not just flagging long words
        ("My grandfather has the heart of a lion",
         "and a lifetime ban from the zoo."),
    ]

    receipts = []
    for setup, punch in cases:
        prof = semantic_profile(setup, punch)
        if prof is None:
            print("embedding backend unavailable; nothing measured")
            return
        print(f"\nsetup:     {setup}")
        print(f"punchline: {punch}")
        print(f"setup-punchline link: {prof['setup_punchline_link']:.4f}\n")
        ranked = sorted(prof["words"], key=lambda r: -r["load_relative"])
        print(f"  {'word':16s} {'semantic load':>14s}   carries meaning?")
        for r in ranked:
            v = ("LOAD-BEARING" if r["load_relative"] > 0.004 else
                 "inert (safe to cut)" if r["load_relative"] < -0.004 else "neutral")
            print(f"  {r['word']:16s} {r['load_relative']:+14.5f}   {v}")
        receipts.append({"setup": setup, "punchline": punch, **prof})

    report = {
        "receipt_type": "semantic_load_analysis",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "method": ("semantic_load(word) = cos(setup, punchline) - cos(setup, punchline without "
                   "word), using EmbeddingGemma; centred on the mean deletion so the shared "
                   "shortening effect is divided out"),
        "why": ("deadweight.py's structural model ranked 'slowly' and 'getting' as cuttable when "
                "they carry the pun, because no structural feature can represent meaning. This "
                "measures the setup-punchline tie directly and needs no trained model."),
        "what_it_measures_and_what_it_does_not": {
            "measures": ("TOPICAL tie to the setup. In both test cases the top-ranked content word "
                         "is a genuine payoff word: 'slowly' bridges to speed bumps, 'zoo' "
                         "recontextualises the lion. That is a real signal the structural model "
                         "does not have, and it rescues the case deadweight.py gets wrong."),
            "does_not_measure": ("comic dependency in general. 'ban' ranks LAST in the lion joke "
                                 "although the line collapses without it, because 'ban' shares no "
                                 "topic with 'heart of a lion'; removing it leaves a string that is "
                                 "still about zoos and animals. Topical overlap and comic load are "
                                 "correlated, not identical."),
            "honest_scope": ("use the top-ranked content word as a candidate payoff, not the full "
                             "ranking as a cut list. Two jokes is also a demo, not an evaluation; "
                             "a real one needs human-annotated payoff words, which this project "
                             "does not yet have."),
        },
        "cases": receipts,
        "runtime_s": round(time.time() - t0, 1),
    }
    (OUT / "semantic_load_analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nreceipt -> jestry_out/semantic_load_analysis.json")


if __name__ == "__main__":
    main()
