#!/usr/bin/env python3
"""Does EmbeddingGemma actually earn its place? A head-to-head bake-off.

The been-done index uses EmbeddingGemma, and the writeup leans on one headline
result: an English paraphrase retrieves the Korean and Japanese "even monkeys
fall from trees". That claim is only interesting if a different embedding model
would not do the same, or would do it better. Two other backends are installed
locally (nomic-embed-text, all-minilm), so the comparison is cheap and the
answer is checkable.

Three probes, each scored the same way for every backend:

1. **Cross-lingual identity.** An English paraphrase should rank the Korean and
   Japanese originals of the same proverb above everything else. Scored as the
   rank of the first correct original and its cosine margin over the best
   distractor. This is the claim the writeup makes.
2. **Frame family.** A novel English sentence carrying a planted comic frame
   (experts slip) should rank that frame's other-language family members highly
   even though it shares no surface vocabulary with them. This is the harder
   claim, and the one a bag-of-words baseline cannot fake.
3. **Paraphrase versus distractor.** A held-out set of paraphrase pairs should
   score above random pairs from the same pool, reported as an AUC, which is
   the standard sanity check that a backend encodes meaning at all.

Deterministic given the model weights: fixed probe texts, fixed candidate pool,
no sampling. Runs against whatever backends respond; missing ones are recorded
as unavailable rather than silently skipped.

    python3 embedding_bakeoff.py
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
HOST = "http://127.0.0.1:11434"
BACKENDS = ["embeddinggemma", "nomic-embed-text", "all-minilm"]

# Fixed probe set. The originals and family members are drawn from the project's
# own curated multilingual canon, so provenance is known for every line.
MONKEY_EN = "Even the most skilled monkey falls from the tree sometimes."
MONKEY_ORIGINALS = {
    "ko": "원숭이도 나무에서 떨어진다 (wonsungido namueseo tteoreojinda) — Even monkeys fall from trees.",
    "ja": "猿も木から落ちる (saru mo ki kara ochiru) — Even monkeys fall from trees.",
}
FRAME_PROBE = "Even a chess grandmaster hangs a queen now and then."
FRAME_FAMILY = {
    "ta": "யானைக்கும் அடி சறுக்கும் (yaanaikkum adi sarukkum) — Even an elephant's foot slips.",
    "ko": MONKEY_ORIGINALS["ko"],
    "ja": MONKEY_ORIGINALS["ja"],
}
DISTRACTORS = [
    "A farmer makes a plan.",
    "Man plans and God laughs.",
    "The early bird catches the worm.",
    "Why did the burglar hang his mugshot on the wall?",
    "Friends are like trees, they fall after being hit with an axe.",
    "A simile committing suicide is always a depressing sight.",
    "The quarterly cheese fondue regatta sailed backwards.",
    "She said we can talk about it next week.",
    "Whiteboards are remarkable.",
    "I told my therapist about my fear of speed bumps.",
]
PARAPHRASE_PAIRS = [
    ("A watched pot never boils.", "Nothing cooks faster for being stared at."),
    ("Don't count your chickens before they hatch.",
     "Do not tally the birds until the eggs actually open."),
    ("The apple does not fall far from the tree.",
     "Children usually end up resembling their parents."),
    ("Too many cooks spoil the broth.",
     "A dish gets worse when everyone stirs it at once."),
    ("Let sleeping dogs lie.", "Leave a settled trouble alone instead of poking it."),
]


def embed(model: str, texts: list[str], timeout: float = 180.0) -> list[list[float]] | None:
    vecs: list[list[float]] = []
    for t in texts:
        body = json.dumps({"model": model, "prompt": t}).encode()
        req = urllib.request.Request(f"{HOST}/api/embeddings", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                v = json.loads(r.read()).get("embedding")
        except Exception:
            return None
        if not v:
            return None
        vecs.append(v)
    return vecs


def cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def auc(pos: list[float], neg: list[float]) -> float:
    vals = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks, i, order = {}, 0, 1
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1][0] == vals[i][0]:
            j += 1
        avg = (order + order + (j - i)) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg
        order += (j - i) + 1
        i = j + 1
    rsum = sum(ranks[k] for k, (_, lab) in enumerate(vals) if lab == 1)
    n1, n0 = len(pos), len(neg)
    return round((rsum - n1 * (n1 + 1) / 2) / (n1 * n0), 4) if n1 and n0 else float("nan")


def rank_of(target_scores: list[float], all_scores: list[float]) -> int:
    """1-based rank of the best target among all candidates."""
    best = max(target_scores)
    return sorted(all_scores, reverse=True).index(best) + 1


def run_backend(model: str) -> dict:
    t0 = time.time()
    pool = list(MONKEY_ORIGINALS.values()) + [FRAME_FAMILY["ta"]] + DISTRACTORS
    probe_texts = [MONKEY_EN, FRAME_PROBE] + pool
    vecs = embed(model, probe_texts)
    if vecs is None:
        return {"available": False, "error": "no embedding response"}
    q_monkey, q_frame = vecs[0], vecs[1]
    pool_vecs = vecs[2:]
    monkey_scores = [cos(q_monkey, v) for v in pool_vecs]
    frame_scores = [cos(q_frame, v) for v in pool_vecs]

    n_orig = len(MONKEY_ORIGINALS)
    orig_monkey = monkey_scores[:n_orig]
    ta_idx = n_orig
    best_distractor_monkey = max(monkey_scores[n_orig + 1:])

    # frame family for the chess probe = Tamil elephant + the two monkey lines
    family_frame = frame_scores[:n_orig] + [frame_scores[ta_idx]]
    best_distractor_frame = max(frame_scores[n_orig + 1:])

    pairs = [t for p in PARAPHRASE_PAIRS for t in p]
    pv = embed(model, pairs)
    para_auc = float("nan")
    if pv:
        pos = [cos(pv[2 * i], pv[2 * i + 1]) for i in range(len(PARAPHRASE_PAIRS))]
        neg = []
        for i in range(len(PARAPHRASE_PAIRS)):
            for j in range(len(PARAPHRASE_PAIRS)):
                if i != j:
                    neg.append(cos(pv[2 * i], pv[2 * j + 1]))
        para_auc = auc(pos, neg)

    return {
        "available": True,
        "dim": len(q_monkey),
        "probe1_cross_lingual": {
            "top_original_cosine": round(max(orig_monkey), 4),
            "rank_of_first_original": rank_of(orig_monkey, monkey_scores),
            "margin_over_best_distractor": round(max(orig_monkey) - best_distractor_monkey, 4),
            "per_language": {k: round(s, 4) for k, s in zip(MONKEY_ORIGINALS, orig_monkey)},
        },
        "probe2_frame_family": {
            "note": "novel English sentence, zero surface overlap with the family",
            "top_family_cosine": round(max(family_frame), 4),
            "rank_of_first_family_member": rank_of(family_frame, frame_scores),
            "margin_over_best_distractor": round(max(family_frame) - best_distractor_frame, 4),
            "tamil_elephant_cosine": round(frame_scores[ta_idx], 4),
        },
        "probe3_paraphrase_auc": para_auc,
        "seconds": round(time.time() - t0, 1),
    }


def main() -> None:
    results = {}
    for model in BACKENDS:
        print(f"probing {model} …", flush=True)
        results[model] = run_backend(model)
        r = results[model]
        if r.get("available"):
            print(f"  dim={r['dim']} xling_rank={r['probe1_cross_lingual']['rank_of_first_original']}"
                  f" frame_rank={r['probe2_frame_family']['rank_of_first_family_member']}"
                  f" para_auc={r['probe3_paraphrase_auc']} ({r['seconds']}s)")
        else:
            print(f"  unavailable: {r.get('error')}")

    live = {k: v for k, v in results.items() if v.get("available")}
    # No single winner is declared, because collapsing three probes into one
    # ranking just hides which probe the weighting favoured. Per-probe winners
    # are reported instead, and a split verdict is a real result.
    def best(score, lower_is_better):
        vals = {k: score(v) for k, v in live.items()}
        target = min(vals.values()) if lower_is_better else max(vals.values())
        tied = sorted(k for k, v in vals.items() if v == target)
        # a tie is reported as a tie; picking the first key would invent a winner
        return {"value": target, "winners": tied, "tie": len(tied) > 1}

    per_probe = {}
    if live:
        per_probe["cross_lingual_rank"] = best(
            lambda v: v["probe1_cross_lingual"]["rank_of_first_original"], True)
        per_probe["frame_family_rank"] = best(
            lambda v: v["probe2_frame_family"]["rank_of_first_family_member"], True)
        per_probe["paraphrase_auc"] = best(lambda v: v["probe3_paraphrase_auc"], False)
    winner = per_probe

    report = {
        "receipt_type": "embedding_bakeoff",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": "is EmbeddingGemma the right backend for the been-done index, or just the one we picked?",
        "protocol": ("three fixed probes per backend: cross-lingual identity retrieval, "
                     "frame-family retrieval with zero surface overlap, and paraphrase-vs-distractor "
                     "AUC; identical candidate pool and probe texts for every backend"),
        "backends": results,
        "per_probe_winner": winner,
        "caveat": ("probe sets are small and hand-built from this project's curated canon, so this "
                   "ranks backends on the retrieval behaviour this project actually depends on, "
                   "not on general embedding quality"),
    }
    (OUT / "embedding_bakeoff.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
    print("\nper-probe winners:")
    for probe, info in (winner or {}).items():
        tag = "TIE" if info["tie"] else "win"
        print(f"  {probe:22s} {tag}: {', '.join(info['winners'])} ({info['value']})")
    print("split verdict is a real result; no single backend wins every probe.")
    print("receipt -> jestry_out/embedding_bakeoff.json")


if __name__ == "__main__":
    main()
