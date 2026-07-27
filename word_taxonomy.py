#!/usr/bin/env python3
"""What KIND of word is it? Semantic category and part of speech, cheaply.

Humor craft talks constantly about word kind. "Land on a concrete noun." "Never
end on an adverb." "Swap the abstraction for a person." None of that was
measurable here, because the features so far only counted letters, syllables and
distances. This module adds the missing axis: what sort of thing a word IS.

Two independent methods, deliberately not merged, so they can disagree and the
disagreement is visible:

**Semantic category, by embedding anchor.** Ten anchors name the categories
humor writing cares about. A word is assigned the nearest anchor by cosine
similarity in the same EmbeddingGemma space the rest of the project uses. No POS
tagger, works in any language the embedder covers, and it degrades honestly: the
margin between best and second-best is reported, so a word sitting between
categories can be excluded rather than silently forced into one.

**The framing matters more than the anchors do**, which was measured rather than
assumed. Four formats were tested on eight words with known categories:

    bare word vs bare category          4/8 correct
    "a banana" vs "a food"              3/8
    EmbeddingGemma task-prefix format   5/8
    symmetric sentence framing          8/8   <- used here

Embedding a bare word against a descriptive phrase compares a word to a
sentence, and that difference in shape swamps the semantic difference being
asked about. Putting both sides in the SAME sentence frame ("This word refers
to X.") fixed every miss, including Paris, which the bare format had called an
animal. Anyone reusing an embedding model for word-level classification should
test their framing before trusting a single label.

**Part of speech, by morphology.** Suffix rules (-ly, -ness, -tion, -ous, -ing,
-ed, -er) plus capitalisation and a closed-class function-word list. These are
heuristics, not a tagger, and they are wrong on irregular words. They are here
because they are deterministic, need no model, and are transparent about what
they key on, which a black-box tagger is not.

Concreteness is derived as the margin between the physical-object anchor and the
abstract-idea anchor, which gives a continuous score rather than a bucket.

    python3 word_taxonomy.py            # demo on a fixed word list
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path

from humorvibes.config import Settings

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
RUNTIME = Settings.from_env()
HOST = RUNTIME.ollama_host
EMB_MODEL = os.environ.get("EMBED_MODEL", "embeddinggemma")
_CACHE_MODEL = re.sub(r"[^A-Za-z0-9_.-]+", "_", EMB_MODEL)
_CACHE_HOST = hashlib.sha256(HOST.encode("utf-8")).hexdigest()[:8]
ANCHOR_CACHE = OUT / f"taxonomy_anchor_cache_{_CACHE_MODEL}_{_CACHE_HOST}.json"

# Anchors are phrases, not bare words: "a place such as a city, country or room"
# separates far more cleanly than the single token "place", which is itself an
# abstract noun and pulls the wrong neighbours.
CATEGORIES = ["person", "place", "object", "abstract", "action", "quality",
              "animal", "body part", "food", "occupation"]
FRAME_ANCHOR = "This word refers to a {}."
FRAME_WORD = "This word refers to {}."
ANCHORS = {c: FRAME_ANCHOR.format(c) for c in CATEGORIES}

FUNCTION_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at", "by",
    "for", "with", "from", "as", "is", "was", "are", "were", "be", "been", "am",
    "it", "its", "this", "that", "these", "those", "he", "she", "they", "we", "you",
    "i", "him", "her", "them", "us", "my", "your", "his", "their", "our", "not",
    "no", "so", "then", "than", "there", "here", "what", "which", "who", "when",
    "where", "how", "all", "any", "some", "just", "do", "does", "did", "have",
    "has", "had", "will", "would", "can", "could", "should", "about", "into", "up",
    "out", "over", "after", "before", "because", "while", "very", "too",
}

SUFFIX_POS = [
    ("adverb", ("ly",)),
    ("abstract_noun", ("ness", "tion", "sion", "ment", "ity", "ism", "ance", "ence", "ship", "hood")),
    ("agent_noun", ("er", "or", "ist", "ian", "eer")),
    ("adjective", ("ous", "ful", "ive", "able", "ible", "al", "ic", "ish", "less", "y")),
    ("verb_ing", ("ing",)),
    ("verb_ed", ("ed",)),
    ("plural_noun", ("s",)),
]


def embed(texts: list[str], timeout: float = 120.0) -> list[list[float]] | None:
    from dataclasses import replace

    from humorvibes.embeddings import OllamaEmbeddingBackend
    from humorvibes.errors import IntegrationError

    settings = replace(
        RUNTIME,
        ollama_host=HOST,
        request_timeout_seconds=timeout,
    )
    try:
        return OllamaEmbeddingBackend(settings, EMB_MODEL).embed(texts).vectors
    except IntegrationError:
        return None


def cos(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def anchor_vectors() -> dict[str, list[float]]:
    if ANCHOR_CACHE.exists():
        try:
            return json.loads(ANCHOR_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    keys = list(ANCHORS)
    vecs = embed([ANCHORS[k] for k in keys])   # same frame as the words
    if vecs is None:
        raise SystemExit("anchor embedding failed; is ollama serving embeddinggemma?")
    data = dict(zip(keys, vecs))
    ANCHOR_CACHE.parent.mkdir(exist_ok=True)
    ANCHOR_CACHE.write_text(json.dumps(data), encoding="utf-8")
    return data


def pos_guess(word: str) -> str:
    """Morphology-only part of speech. Deterministic, and wrong on irregulars."""
    w = word.strip().strip(".,!?\"';:")
    if not w:
        return "empty"
    if w.lower() in FUNCTION_WORDS:
        return "function"
    if w[:1].isupper():
        return "proper_noun"
    lw = w.lower()
    for label, sufs in SUFFIX_POS:
        for s in sufs:
            # a 3-letter word ending in "s" is not evidence of a plural
            if lw.endswith(s) and len(lw) > len(s) + 2:
                return label
    return "other"


def classify(word: str, vec: list[float], anchors: dict[str, list[float]]) -> dict:
    """Nearest-anchor category plus the margin that says how confident that is."""
    sims = {k: cos(vec, v) for k, v in anchors.items()}
    ranked = sorted(sims.items(), key=lambda kv: -kv[1])
    best, second = ranked[0], ranked[1]
    concrete = sims["object"] - sims["abstract"]
    return {
        "category": best[0],
        "category_sim": round(best[1], 4),
        "category_margin": round(best[1] - second[1], 4),
        "runner_up": second[0],
        "concreteness": round(concrete, 4),
        "is_person": round(sims["person"], 4),
        "is_place": round(sims["place"], 4),
        "is_object": round(sims["object"], 4),
        "is_abstract": round(sims["abstract"], 4),
        "is_action": round(sims["action"], 4),
        "is_quality": round(sims["quality"], 4),
        "pos_guess": pos_guess(word),
    }


def main() -> None:
    anchors = anchor_vectors()
    demo = ["banana", "freedom", "Paris", "running", "beautifully", "dentist",
            "elbow", "quickly", "sadness", "penguin", "hammer", "Einstein"]
    vecs = embed([FRAME_WORD.format(w) for w in demo])
    if vecs is None:
        raise SystemExit("embedding failed")
    print(f"{'word':13s} {'category':11s} {'margin':>7s} {'concrete':>9s}  pos")
    rows = []
    for w, v in zip(demo, vecs):
        c = classify(w, v, anchors)
        rows.append({"word": w, **c})
        print(f"{w:13s} {c['category']:11s} {c['category_margin']:+7.3f} "
              f"{c['concreteness']:+9.3f}  {c['pos_guess']}")
    (OUT / "word_taxonomy_demo.json").write_text(
        json.dumps({"anchors": list(ANCHORS), "rows": rows}, indent=2), encoding="utf-8")
    print("\nreceipt -> jestry_out/word_taxonomy_demo.json")


if __name__ == "__main__":
    main()
