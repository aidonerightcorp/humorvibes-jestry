#!/usr/bin/env python3
"""Cheap surface features for jokes, and the baseline question they answer.

Everything this project measures so far comes off a language model's logits and
costs seconds per item. Classical humor research uses surface structure instead:
how long the setup runs, how many syllables the punchline lands in, whether the
last word is rare, whether sounds repeat. Those cost microseconds.

The honest question nobody here had asked: **does the expensive instrument beat
the cheap features?** If word count predicts human funniness as well as
teacher-forced surprisal does, that is worth knowing and worth saying. This
module computes the cheap side deterministically (no model, no network, stdlib
only) so the comparison can be run and receipted.

Feature families, all computed for setup and punchline separately and for the
pair:

- **length**: characters, words, sentences, mean word length, setup/punchline
  word ratio (comic timing is partly a length relationship)
- **syllables**: total and per word, via a vowel-group heuristic with the usual
  silent-e and -le corrections; punchline syllable count is the closest thing to
  a "beat count" available without a pronouncing dictionary
- **phonetics**: alliteration (repeated word-initial consonants), assonance
  (repeated stressed vowel letters), and setup/punchline end-rhyme on the final
  three characters, which is a crude but honest rhyme proxy
- **rarity**: word frequency taken from THIS project's own 23k-item corpus, so
  "rare" means rare in humor text rather than rare in newswire; reported as mean
  and max negative log frequency, plus the rarity of the final word, because a
  punchline usually lands on its least predictable token
- **texture**: type-token ratio, punctuation counts, digits, capitalised words,
  quote marks

    python3 humor_features.py                 # run the full comparison study
    python3 humor_features.py --features-only # just dump features, no stats
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
CORPORA = HERE / "corpora"

VOWELS = "aeiouy"
WORD = re.compile(r"[A-Za-z']+")


def syllables(word: str) -> int:
    """Vowel-group count with silent-e and -le corrections. Deterministic."""
    w = word.lower().strip("'")
    if not w:
        return 0
    groups = 0
    prev_vowel = False
    for ch in w:
        is_v = ch in VOWELS
        if is_v and not prev_vowel:
            groups += 1
        prev_vowel = is_v
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and groups > 1:
        groups -= 1
    if w.endswith("le") and len(w) > 2 and w[-3] not in VOWELS:
        groups += 1
    return max(1, groups)


def build_frequencies(limit_files: int | None = None) -> dict[str, int]:
    """Word frequencies from this project's own corpus, not an external list."""
    freq: Counter[str] = Counter()
    files = sorted(CORPORA.glob("*.jsonl"))
    if limit_files:
        files = files[:limit_files]
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or '"_meta"' in line[:20]:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            body = str(rec.get("text") or rec.get("joke") or "")
            for w in WORD.findall(body.lower()):
                freq[w] += 1
    return dict(freq)


def _phonetic(words: list[str]) -> dict[str, float]:
    if not words:
        return {"alliteration": 0.0, "assonance": 0.0}
    initials = [w[0] for w in words if w]
    allit = 0.0
    if len(initials) > 1:
        counts = Counter(initials)
        allit = (sum(c - 1 for c in counts.values() if c > 1)) / (len(initials) - 1)
    vowel_seq = [c for w in words for c in w if c in VOWELS]
    asson = 0.0
    if len(vowel_seq) > 1:
        counts = Counter(vowel_seq)
        asson = counts.most_common(1)[0][1] / len(vowel_seq)
    return {"alliteration": round(allit, 4), "assonance": round(asson, 4)}


def _rarity(words: list[str], freq: dict[str, int], total: int) -> dict[str, float]:
    if not words or total <= 0:
        return {"rarity_mean": 0.0, "rarity_max": 0.0, "rarity_final": 0.0}
    def nlf(w: str) -> float:
        # add-one smoothing: an unseen word is rarer than any seen word
        return -math.log((freq.get(w, 0) + 1) / (total + 1))
    vals = [nlf(w) for w in words]
    return {"rarity_mean": round(sum(vals) / len(vals), 4),
            "rarity_max": round(max(vals), 4),
            "rarity_final": round(vals[-1], 4)}


def features(setup: str, punchline: str, freq: dict[str, int], total: int) -> dict[str, float]:
    s_words = WORD.findall(setup.lower())
    p_words = WORD.findall(punchline.lower())
    s_syl = sum(syllables(w) for w in s_words)
    p_syl = sum(syllables(w) for w in p_words)
    feats: dict[str, float] = {
        "setup_chars": len(setup),
        "punch_chars": len(punchline),
        "setup_words": len(s_words),
        "punch_words": len(p_words),
        "word_ratio": round(len(p_words) / max(1, len(s_words)), 4),
        "setup_syllables": s_syl,
        "punch_syllables": p_syl,
        "syllable_ratio": round(p_syl / max(1, s_syl), 4),
        "punch_syl_per_word": round(p_syl / max(1, len(p_words)), 4),
        "setup_mean_wordlen": round(sum(len(w) for w in s_words) / max(1, len(s_words)), 4),
        "punch_mean_wordlen": round(sum(len(w) for w in p_words) / max(1, len(p_words)), 4),
        "sentences": len(re.findall(r"[.!?]+", setup + " " + punchline)),
        "questions": (setup + punchline).count("?"),
        "exclaims": (setup + punchline).count("!"),
        "quotes": (setup + punchline).count('"') + (setup + punchline).count("'"),
        "digits": sum(ch.isdigit() for ch in setup + punchline),
        "caps_words": sum(1 for w in (setup + " " + punchline).split() if w[:1].isupper()),
    }
    all_words = s_words + p_words
    feats["type_token_ratio"] = round(len(set(all_words)) / max(1, len(all_words)), 4)
    # lexical echo: punchline words that already appeared in the setup. A callback
    # reuses; a non-sequitur does not.
    feats["echo_frac"] = round(
        len(set(p_words) & set(s_words)) / max(1, len(set(p_words))), 4)
    for name, block in (("punch", _phonetic(p_words)), ("pair", _phonetic(all_words))):
        for k, v in block.items():
            feats[f"{name}_{k}"] = v
    for name, words in (("punch", p_words), ("setup", s_words)):
        for k, v in _rarity(words, freq, total).items():
            feats[f"{name}_{k}"] = v
    # crude end-rhyme: do the last words share a trailing trigram?
    tail_s = s_words[-1][-3:] if s_words else ""
    tail_p = p_words[-1][-3:] if p_words else ""
    feats["end_rhyme"] = 1.0 if tail_s and tail_s == tail_p else 0.0
    return feats


# ---------------------------------------------------------------- statistics
def spearman(a: list[float], b: list[float]) -> float:
    if len(a) < 3:
        return 0.0
    def rank(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        for pos, idx in enumerate(order):
            out[idx] = float(pos)
        return out
    ra, rb = rank(a), rank(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return round(num / den, 4) if den else 0.0


def perm_p(a: list[float], b: list[float], n_perm: int = 4000, seed: int = 7) -> float:
    """Permutation p for |spearman| under label shuffle. Seeded, reproducible."""
    import random
    rng = random.Random(seed)
    obs = abs(spearman(a, b))
    shuffled = list(b)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(shuffled)
        if abs(spearman(a, shuffled)) >= obs:
            hits += 1
    return round((hits + 1) / (n_perm + 1), 4)


def benjamini_hochberg(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    """Which findings survive FDR control across the whole feature sweep.

    Testing ~30 features against one outcome and reporting the winner is how a
    noise ranking gets published, so every headline correlation below is marked
    with whether it survives this.
    """
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    survive: dict[str, bool] = {k: False for k in pvals}
    largest = -1
    for i, (_, p) in enumerate(items, start=1):
        if p <= alpha * i / m:
            largest = i
    for i, (k, _) in enumerate(items, start=1):
        survive[k] = i <= largest
    return survive


def auc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return float("nan")
    vals = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks: dict[int, float] = {}
    i, order = 0, 1
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
    return round((rsum - n1 * (n1 + 1) / 2) / (n1 * n0), 4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-only", action="store_true")
    args = ap.parse_args()

    freq = build_frequencies()
    total = sum(freq.values())
    print(f"corpus frequency table: {len(freq):,} word types, {total:,} tokens")

    measured = [json.loads(l) for l in
                (OUT / "native_format_items.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    fb_path = OUT / "format_boundary_items.jsonl"
    fb = [json.loads(l) for l in fb_path.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if fb_path.exists() else []

    rows = []
    for r in measured:
        f = features(r["setup"], r["punchline"], freq, total)
        rows.append({**f, "kind": r["kind"], "S": r["S"], "R": r["R"], "E": r["E"],
                     "laugh": r["laugh"], "log2_score": r.get("log2_score"),
                     "src": "native_format"})
    for r in fb:
        if r["condition"] != "canonical":
            continue
        f = features(r["setup"], r["punchline"], freq, total)
        rows.append({**f, "kind": "graded", "S": r["S"], "R": r["R"], "E": r["E"],
                     "laugh": r["laugh_score"], "grade": r["grade"], "src": "humicroedit"})

    with (OUT / "humor_features_rows.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"featurised {len(rows)} rows -> jestry_out/humor_features_rows.jsonl")
    if args.features_only:
        return

    feat_names = [k for k in rows[0] if k not in
                  ("kind", "S", "R", "E", "laugh", "log2_score", "grade", "src")]

    # --- Arm 1: predicting HUMAN grades (Humicroedit, canonical split) --------
    graded = [r for r in rows if r["src"] == "humicroedit"]
    grade_corr, grade_p = {}, {}
    if graded:
        g = [r["grade"] for r in graded]
        for name in feat_names:
            vals = [r[name] for r in graded]
            grade_corr[name] = spearman(vals, g)
            grade_p[name] = perm_p(vals, g)
        for sig in ("S", "R", "E", "laugh"):
            vals = [r[sig] for r in graded]
            grade_corr[f"[gemma] {sig}"] = spearman(vals, g)
            grade_p[f"[gemma] {sig}"] = perm_p(vals, g)
    grade_survive = benjamini_hochberg(grade_p) if grade_p else {}

    # --- Arm 2: separating genuine from shuffled (native format) -------------
    gen = [r for r in rows if r.get("kind") == "genuine"]
    shuf = [r for r in rows if r.get("kind") == "shuffled"]
    sep_auc = {}
    if gen and shuf:
        for name in feat_names:
            sep_auc[name] = auc([r[name] for r in gen], [r[name] for r in shuf])
        for sig in ("S", "R", "E", "laugh"):
            sep_auc[f"[gemma] {sig}"] = auc([r[sig] for r in gen], [r[sig] for r in shuf])

    def top(d: dict[str, float], key=lambda v: abs(v), n: int = 12):
        return sorted(d.items(), key=lambda kv: -key(kv[1]))[:n]

    report = {
        "receipt_type": "surface_feature_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": ("do cheap deterministic surface features predict humour as well as "
                     "teacher-forced Gemma signals that cost seconds per item?"),
        "frequency_table": {"types": len(freq), "tokens": total,
                            "source": "this project's own corpora/*.jsonl"},
        "n_rows": len(rows),
        "n_features": len(feat_names),
        "arm1_human_grade_spearman": {
            "n": len(graded),
            "dataset": "Humicroedit canonical split, annotator mean grade 0-3",
            "multiple_comparison": (f"{len(grade_p)} tests against one outcome; permutation p over "
                                    "4000 seeded shuffles, Benjamini-Hochberg FDR at 0.05"),
            "survivors_after_fdr": sorted(k for k, ok in grade_survive.items() if ok),
            "top_features": [{"feature": k, "spearman": v, "perm_p": grade_p.get(k),
                              "survives_fdr": grade_survive.get(k, False)}
                             for k, v in top(grade_corr)],
            "all": grade_corr,
            "all_perm_p": grade_p,
        },
        "arm2_genuine_vs_shuffled_auc": {
            "n_genuine": len(gen), "n_shuffled": len(shuf),
            "dataset": "r/Jokes native pairs vs punchline swapped from another setup",
            "construction_confound": (
                "the shuffled control is built by swapping a punchline in from a different "
                "setup, which necessarily destroys shared vocabulary. echo_frac measures "
                "exactly that shared vocabulary, so a high echo_frac AUC is partly the "
                "control's construction reflected back and must NOT be read as a general "
                "humour detector. It is reported because the confound is the finding: any "
                "swap-based benchmark can be beaten this way, including ours."),
            "top_features": top(sep_auc, key=lambda v: abs(v - 0.5)),
            "all": sep_auc,
        },
    }
    (OUT / "surface_feature_study.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n--- Arm 1: predicting human grades (n={len(graded)}) ---")
    for t in report["arm1_human_grade_spearman"]["top_features"]:
        flag = "SURVIVES FDR" if t["survives_fdr"] else "noise-ranked"
        print(f"  rho={t['spearman']:+.4f}  p={t['perm_p']:.4f}  {flag:12s}  {t['feature']}")
    surv = report["arm1_human_grade_spearman"]["survivors_after_fdr"]
    print(f"  => surviving FDR at 0.05: {surv or 'NONE, cheap or expensive'}")
    print(f"\n--- Arm 2: genuine vs shuffled AUC (n={len(gen)}v{len(shuf)}) ---")
    for k, v in report["arm2_genuine_vs_shuffled_auc"]["top_features"]:
        print(f"  {v:.4f}  {k}")
    print("\nreceipt -> jestry_out/surface_feature_study.json")


if __name__ == "__main__":
    main()
