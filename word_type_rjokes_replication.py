#!/usr/bin/env python3
"""Does the word-type result survive the population that killed the last one?

word_type_study.py found, on Humicroedit, that the KIND of word swapped into a
headline predicts the human grade: body-part words landed +0.2046 over the
pooled mean, food +0.1251, animal +0.0464, and the word-type block lifted
held-out Spearman 0.1137 -> 0.2296. That receipt is honest about its limit: one
corpus, one edit format, uncorrected p values. And this project has already
watched a strong within-corpus structural model collapse on r/Jokes
(cross_corpus_transfer: 0.508 -> -0.009), so "it worked on Humicroedit" is a
hypothesis about r/Jokes, not a result.

This study is the transfer test. Same classifier (word_taxonomy sentence-framed
embedding anchors, same anchor cache, same word-type cache extended in place),
different population: ~98.5k r/Jokes setup/punchline rows, outcome
log1p(upvote score) — a POPULARITY PROXY, not a funniness grade, and the
receipt says so everywhere it matters.

What cannot be identical, and is receipted as reconstruction rather than
replication-of-instrument:

- Humicroedit rows have exactly ONE swapped word; r/Jokes rows do not. The
  unit here is the punchline's content words, reduced to a per-row DOMINANT
  semantic category (modal category, ties by summed anchor similarity, then
  alphabetical). The original's edit/original pair features (concreteness
  shift, category_changed) have no analogue and are dropped.
- The original used a single 70/30 split; this study uses seeded 5-fold CV
  with a bootstrap CI over the per-fold lift, which is the stronger design.
- The original left category p values uncorrected; here the category family is
  declared up front and Benjamini-Hochberg is applied within it.

Pre-registration (hypotheses, family, seed, MDE at realized n) is written to a
checkpoint BEFORE any outcome-group statistic is computed, and reproduced
verbatim in the receipt.

    python3 word_type_rjokes_replication.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True          # leave no .pyc in either tree

REPO = Path(__file__).resolve().parent
RESEARCH = Path(os.environ.get(
    "JESTRY_RESEARCH_ROOT",
    "/home/username/new_algo/comps/build-with-gemma-humor-genome-nyc"))
DATA = RESEARCH / "corpora" / "harvest_local_20260726_2.jsonl"
R_OUT = RESEARCH / "jestry_out"
REPO_OUT = REPO / "jestry_out"
RECEIPT = REPO_OUT / "word_type_rjokes_replication.json"
TYPE_CACHE = R_OUT / "word_type_cache.json"          # extended in place (checkpoint)
PREREG_CKPT = R_OUT / "word_type_rjokes_replication_prereg_checkpoint.json"
STAGE_CKPT = R_OUT / "word_type_rjokes_replication_stage_checkpoint.json"
ORIGINAL_RECEIPT = R_OUT / "word_type_study.json"

SEED = 20260728
N_PERM = 10_000
MIN_GROUP = 300           # family membership threshold (original used 30)
EMBED_BATCH = 128
COVERAGE_FLOOR = 0.50     # token-occurrence coverage below this -> honest stop
WORDRE = re.compile(r"[A-Za-z']+")

T0 = time.time()


def say(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# The research tree owns the caches (anchor cache, word-type cache, corpora
# frequency cache), so both modules are loaded FROM the research tree. The
# repo's humor_features.py is byte-identical (asserted below), so "the repo's
# 30 structural features" is literally what runs.
wt = load_module("wt_research", RESEARCH / "word_taxonomy.py")
hf = load_module("hf_research", RESEARCH / "humor_features.py")

_sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
HF_REPO_SHA, HF_RES_SHA = _sha(REPO / "humor_features.py"), _sha(RESEARCH / "humor_features.py")
assert HF_REPO_SHA == HF_RES_SHA, "repo and research humor_features.py diverged; reuse claim void"

POS_LABELS = ["adverb", "adjective", "abstract_noun", "agent_noun", "verb_ing",
              "verb_ed", "plural_noun", "proper_noun", "function", "other"]
CATS = list(wt.CATEGORIES)


# ------------------------------------------------------------------ tokenizing
def content_words(text: str) -> list[str]:
    """Punchline content words. Deterministic, receipted rule.

    Same [A-Za-z']+ regex as humor_features; lowercased; trailing 's stripped
    ("dog's" -> "dog", "it's" -> "it" which the function list then removes);
    tokens still holding an apostrophe (don't, would've) are dropped as
    function-word contractions; then function words and tokens under 3 letters
    are dropped.
    """
    out = []
    for t in WORDRE.findall(text.lower()):
        t = t.strip("'")
        if t.endswith("'s"):
            t = t[:-2]
        if "'" in t or len(t) < 3 or t in wt.FUNCTION_WORDS:
            continue
        out.append(t)
    return out


def load_rows() -> tuple[list[dict], dict]:
    rows, n_raw, dup, seen = [], 0, 0, set()
    with DATA.open(encoding="utf-8") as fh:
        first = json.loads(fh.readline())
        assert "_meta" in first, "expected _meta header line"
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            m = r.get("meta") or {}
            s, p, sc = m.get("setup"), m.get("punchline"), m.get("score")
            n_raw += 1
            if s is None or p is None or sc is None or sc < 0:
                continue
            key = (str(s), str(p))
            if key in seen:
                dup += 1        # kept: reposts are real observations of the population
            seen.add(key)
            rows.append({"setup": str(s), "punchline": str(p),
                         "y": math.log1p(float(sc)),
                         "cw": content_words(str(p))})
    screening = {"file": DATA.name, "file_sha256_16": _sha(DATA)[:16],
                 "meta_n": first["_meta"].get("n"), "rows_raw": n_raw,
                 "rows_kept": len(rows),
                 "exact_duplicate_rows_kept": dup,
                 "source": "reddit:r/Jokes (bulk), en, score >= 0"}
    return rows, screening


# ------------------------------------------------------------------ embeddings
def embed_batch(texts: list[str], timeout: float = 300.0):
    """Ollama /api/embed with a list input: one request per batch instead of one
    per word (measured 285 -> 18 ms/word). Cosine is scale-invariant, so the
    endpoint's normalization difference cannot move a classification; parity is
    still verified against word_taxonomy.embed on a seeded sample before use."""
    body = json.dumps({"model": wt.EMB_MODEL, "input": texts}).encode()
    req = urllib.request.Request(f"{wt.HOST}/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            vecs = json.loads(r.read()).get("embeddings")
    except Exception:
        return None
    return vecs if vecs and len(vecs) == len(texts) else None


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(f"{wt.HOST}/api/tags", timeout=5) as r:
            return bool(json.loads(r.read()).get("models"))
    except Exception:
        return False


def _write_cache(cache: dict) -> None:
    tmp = TYPE_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache), encoding="utf-8")
    tmp.replace(TYPE_CACHE)


def classify_vocab(missing: list[str], cache: dict, anchors: dict) -> dict:
    """Extend the word-type cache in place, checkpointing as it goes."""
    parity = {"checked": 0, "mismatch": 0}
    use_batch = True
    rng = np.random.default_rng(SEED)
    sample = [missing[i] for i in rng.choice(len(missing), min(12, len(missing)), replace=False)]
    seq = wt.embed([wt.FRAME_WORD.format(w) for w in sample])
    bat = embed_batch([wt.FRAME_WORD.format(w) for w in sample])
    if seq and bat:
        for w, a, b in zip(sample, seq, bat):
            parity["checked"] += 1
            if wt.classify(w, a, anchors)["category"] != wt.classify(w, b, anchors)["category"]:
                parity["mismatch"] += 1
        use_batch = parity["mismatch"] == 0
    say(f"endpoint parity: {parity['checked'] - parity['mismatch']}/{parity['checked']} "
        f"category-identical -> {'batched /api/embed' if use_batch else 'sequential fallback'}")

    t0, done = time.time(), 0
    for i in range(0, len(missing), EMBED_BATCH):
        chunk = missing[i:i + EMBED_BATCH]
        frames = [wt.FRAME_WORD.format(w) for w in chunk]
        vecs = embed_batch(frames) if use_batch else wt.embed(frames)
        if vecs is None:
            say("    embed failed; retrying once in 5s")
            time.sleep(5)
            vecs = embed_batch(frames) if use_batch else None
            if vecs is None:
                vecs = wt.embed(frames)             # last resort: original path
            if vecs is None:
                say("    embedding backend stopped responding; keeping what we have")
                break
        for w, v in zip(chunk, vecs):
            cache[w] = wt.classify(w, v, anchors)
        done += len(chunk)
        if (i // EMBED_BATCH) % 8 == 0 or done == len(missing):
            _write_cache(cache)
            rate = done / max(1e-9, time.time() - t0)
            say(f"    classified {done}/{len(missing)} "
                f"({rate:.0f} w/s, eta {(len(missing) - done) / max(rate, 1e-9):.0f}s)")
    _write_cache(cache)
    parity["path"] = "batched /api/embed" if use_batch else "sequential per-word fallback"
    return parity


# ------------------------------------------------------------------ statistics
def bh(pvals: dict[str, float]) -> dict[str, bool]:
    return hf.benjamini_hochberg(pvals) if pvals else {}


def mde_delta(sd: float, k: int, n: int) -> float:
    """Two-sided alpha .05, power .80 minimum detectable |group mean - pooled
    mean| for a group of k inside n, sampling without replacement."""
    return round(2.802 * sd * math.sqrt(max(0.0, 1.0 / k - 1.0 / n)), 4)


def main() -> None:
    say(f"study seed {SEED}; repo={REPO.name} research={RESEARCH.name}")
    REPO_OUT.mkdir(exist_ok=True)

    # ---------------- stage 1: rows -------------------------------------
    rows, screening = load_rows()
    say(f"rows kept {screening['rows_kept']}/{screening['rows_raw']} "
        f"(dups kept {screening['exact_duplicate_rows_kept']})")

    vocab = Counter(w for r in rows for w in r["cw"])
    cache: dict[str, dict] = {}
    if TYPE_CACHE.exists():
        cache = json.loads(TYPE_CACHE.read_text(encoding="utf-8"))
    need = ("category", "category_sim", "category_margin", "concreteness", "pos_guess")
    known = {w for w in vocab if w in cache and all(k in cache[w] for k in need)}
    tok_total = sum(vocab.values())

    def coverage() -> dict:
        tok = sum(c for w, c in vocab.items() if w in known)
        row = sum(1 for r in rows if any(w in known for w in r["cw"]))
        return {"vocab": round(len(known) / max(1, len(vocab)), 4),
                "token_occurrences": round(tok / max(1, tok_total), 4),
                "rows_with_ge1_classified_word": round(row / len(rows), 4)}
    cov_before = coverage()
    say(f"content vocab {len(vocab)}; cache-covered {len(known)} "
        f"(token coverage {cov_before['token_occurrences']:.1%})")

    # ---------------- stage 2: classify missing vocabulary ---------------
    missing = sorted(w for w in vocab if w not in known)
    embed_info = {"ollama_up": ollama_up(), "newly_classified": 0, "parity": None}
    if missing and embed_info["ollama_up"]:
        anchors = wt.anchor_vectors()
        say(f"classifying {len(missing)} novel words via {wt.EMB_MODEL} "
            f"(sentence frame: {wt.FRAME_WORD!r})")
        embed_info["parity"] = classify_vocab(missing, cache, anchors)
        known = {w for w in vocab if w in cache and all(k in cache[w] for k in need)}
        embed_info["newly_classified"] = sum(1 for w in missing if w in known)
    elif missing:
        say("OLLAMA IS DOWN: not starting services, not hashing; "
            "restricting to cache-covered vocabulary")
    cov_after = coverage()
    say(f"coverage after: vocab {cov_after['vocab']:.1%}, "
        f"tokens {cov_after['token_occurrences']:.1%}, rows {cov_after['rows_with_ge1_classified_word']:.1%}")

    if cov_after["token_occurrences"] < COVERAGE_FLOOR:
        # Honest stop: a category table computed over a minority of tokens is
        # not the study that was asked for.
        RECEIPT.write_text(json.dumps({
            "receipt_type": "word_type_rjokes_replication", "receipt_version": 1,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "status": "insufficient coverage, not run to conclusion",
            "screening": screening, "coverage_before": cov_before,
            "coverage_after": cov_after, "embedding": embed_info,
            "note": ("embedding backend unavailable and the existing word-type cache covers "
                     f"under {COVERAGE_FLOOR:.0%} of punchline content-word occurrences; "
                     "running anyway would silently redefine the population as "
                     "'jokes made of Humicroedit vocabulary'")}, indent=2),
            encoding="utf-8")
        say(f"INSUFFICIENT COVERAGE -> {RECEIPT}")
        return

    # ---------------- stage 3: per-row assembly --------------------------
    say("assembling per-row dominant category / POS / concreteness")
    built, skipped = [], 0
    for r in rows:
        cls = [cache[w] for w in r["cw"] if w in known]
        if not cls:
            skipped += 1
            continue
        by_cat: dict[str, list[dict]] = {}
        for c in cls:
            by_cat.setdefault(c["category"], []).append(c)
        # modal category; ties by summed anchor similarity, then alphabetical
        dom = sorted(by_cat.items(),
                     key=lambda kv: (-len(kv[1]), -sum(c["category_sim"] for c in kv[1]), kv[0]))[0][0]
        pos_counts = Counter(c["pos_guess"] for c in cls)
        dom_pos = sorted(pos_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        r2 = {"setup": r["setup"], "punchline": r["punchline"], "y": r["y"],
              "_cat": dom, "_pos": dom_pos,
              "punch_mean_concreteness": sum(c["concreteness"] for c in cls) / len(cls),
              "punch_final_concreteness": cls[-1]["concreteness"],
              "punch_mean_category_margin": sum(c["category_margin"] for c in cls) / len(cls),
              "dominant_share": len(by_cat[dom]) / len(cls)}
        built.append(r2)
    say(f"built {len(built)} rows ({skipped} skipped: no classified content word)")

    # ---------------- stage 4: features ----------------------------------
    say("frequency table (project corpora; cached by manifest)")
    freq = hf.build_frequencies()
    total = sum(freq.values())
    say(f"  {len(freq):,} types / {total:,} tokens")
    say("structural features x rows (repo's 30, byte-identical module)")
    struct_names = None
    for r in built:
        f = hf.features(r["setup"], r["punchline"], freq, total)
        if struct_names is None:
            struct_names = list(f)
        r["_struct"] = [f[k] for k in struct_names]
    assert len(struct_names) == 30, f"expected 30 structural features, got {len(struct_names)}"
    type_names = ([f"dom_is_{c.replace(' ', '_')}" for c in CATS]
                  + [f"dom_pos_{p}" for p in POS_LABELS]
                  + ["punch_mean_concreteness", "punch_final_concreteness",
                     "punch_mean_category_margin", "dominant_share"])
    for r in built:
        r["_type"] = ([1.0 if r["_cat"] == c else 0.0 for c in CATS]
                      + [1.0 if r["_pos"] == p else 0.0 for p in POS_LABELS]
                      + [r["punch_mean_concreteness"], r["punch_final_concreteness"],
                         r["punch_mean_category_margin"], r["dominant_share"]])

    y = np.array([r["y"] for r in built])
    cat_codes = np.array([CATS.index(r["_cat"]) for r in built])
    pos_codes = np.array([POS_LABELS.index(r["_pos"]) for r in built])
    cat_counts = np.bincount(cat_codes, minlength=len(CATS))
    pos_counts_v = np.bincount(pos_codes, minlength=len(POS_LABELS))

    # ---------------- stage 5: PRE-REGISTRATION (before any group stat) --
    sd_y = float(y.std(ddof=1))
    n = len(built)
    fam_a = [c for c, k in zip(CATS, cat_counts) if k >= MIN_GROUP]
    fam_b = [p for p, k in zip(POS_LABELS, pos_counts_v) if k >= MIN_GROUP]
    prereg = {
        "written_before_any_outcome_group_statistic": True,
        "quantities_seen_so_far": ("outcome marginal sd and n, and label-marginal category/POS "
                                   "counts; no category-outcome or feature-outcome statistic yet"),
        "seed": SEED,
        "outcome": "log1p(reddit upvote score) — POPULARITY PROXY, not a funniness grade",
        "unit_reconstruction": ("original = single swapped word per Humicroedit row; here = modal "
                                "semantic category over punchline content words (ties: summed "
                                "anchor similarity, then alphabetical)"),
        "H1": ("'body part' dominant-category mean outcome minus pooled mean > 0 (sign "
               "replication of Humicroedit +0.2046); tested by label permutation, "
               f"{N_PERM} shuffles, statistic |group mean - pooled mean|, two-sided p, "
               "BH within family A; replication claim requires delta>0 AND BH-significant"),
        "H2": ("word-type block (24 features) lifts held-out tied-midrank Spearman over the 30 "
               "structural features; 5-fold CV, HistGradientBoostingRegressor(max_iter=300, "
               "learning_rate=0.06) both arms; replication claim requires mean per-fold lift > 0 "
               "AND 95% bootstrap CI over folds (10000 resamples) excluding 0"),
        "H3": ("secondary: Spearman(punchline mean concreteness, outcome) > 0; permutation p, "
               f"{N_PERM} shuffles, two-sided report, claim requires rho>0 and p<0.05"),
        "family_A_semantic_categories_n_ge_300": {c: int(k) for c, k in zip(CATS, cat_counts) if k >= MIN_GROUP},
        "family_B_pos_descriptive_n_ge_300": {p: int(k) for p, k in zip(POS_LABELS, pos_counts_v) if k >= MIN_GROUP},
        "alpha": 0.05,
        "mde_at_realized_n": {
            "definition": "two-sided alpha .05, power .80: 2.802*sd(y)*sqrt(1/k - 1/N)",
            "sd_y": round(sd_y, 4), "N": n,
            "per_category_delta": {c: mde_delta(sd_y, int(k), n)
                                    for c, k in zip(CATS, cat_counts) if k >= MIN_GROUP},
            "H3_spearman_mde": round(2.802 / math.sqrt(n), 4),
            "H2_note": ("an honest fold-lift MDE needs the fold variance, which does not exist "
                        "before the CV runs; the pre-registered decision rule above is therefore "
                        "the commitment, not a power number")},
        "structural_features": struct_names,
        "type_features": type_names,
        "excluded_by_construction": ("dom_pos_proper_noun and dom_pos_function cannot fire: "
                                     "tokens are lowercased and function words are removed "
                                     "before classification; columns kept as constant zeros "
                                     "for block parity"),
    }
    PREREG_CKPT.write_text(json.dumps(prereg, indent=2), encoding="utf-8")
    say(f"PRE-REGISTERED -> {PREREG_CKPT.name}")
    say(f"  family A ({len(fam_a)}): {fam_a}")
    say(f"  family B ({len(fam_b)}): {fam_b}")
    say(f"  MDE examples: " + ", ".join(f"{c}={prereg['mde_at_realized_n']['per_category_delta'][c]}"
                                        for c in fam_a[:4]))

    # ---------------- stage 6: permutation tests -------------------------
    pooled = float(y.mean())
    obs_cat = np.array([y[cat_codes == i].mean() if cat_counts[i] else pooled
                        for i in range(len(CATS))])
    obs_pos = np.array([y[pos_codes == i].mean() if pos_counts_v[i] else pooled
                        for i in range(len(POS_LABELS))])
    conc = np.array([r["punch_mean_concreteness"] for r in built])
    from scipy.stats import rankdata
    r_conc, r_y = rankdata(conc), rankdata(y)          # tied midranks
    r_conc = (r_conc - r_conc.mean()) / r_conc.std()
    r_yz = (r_y - r_y.mean()) / r_y.std()
    obs_rho = float(np.dot(r_conc, r_yz) / n)

    say(f"pooled mean log1p(score) = {pooled:.4f}; running {N_PERM} label permutations")
    rng = np.random.default_rng(SEED)
    hits_cat = np.zeros(len(CATS)); hits_pos = np.zeros(len(POS_LABELS)); hits_rho = 0
    d_cat, d_pos = np.abs(obs_cat - pooled), np.abs(obs_pos - pooled)
    for b in range(N_PERM):
        perm = rng.permutation(n)
        yp = y[perm]
        mc = np.bincount(cat_codes, weights=yp, minlength=len(CATS)) / np.maximum(cat_counts, 1)
        mp = np.bincount(pos_codes, weights=yp, minlength=len(POS_LABELS)) / np.maximum(pos_counts_v, 1)
        hits_cat += (np.abs(mc - pooled) >= d_cat)
        hits_pos += (np.abs(mp - pooled) >= d_pos)
        if abs(float(np.dot(r_conc, r_yz[perm]) / n)) >= abs(obs_rho):
            hits_rho += 1
        if (b + 1) % 2000 == 0:
            say(f"    permutation {b + 1}/{N_PERM}")
    p_cat = {c: round((hits_cat[i] + 1) / (N_PERM + 1), 5) for i, c in enumerate(CATS)}
    p_pos = {p: round((hits_pos[i] + 1) / (N_PERM + 1), 5) for i, p in enumerate(POS_LABELS)}
    p_rho = round((hits_rho + 1) / (N_PERM + 1), 5)

    original = json.loads(ORIGINAL_RECEIPT.read_text(encoding="utf-8"))
    orig_cat = {d["label"]: d for d in original["by_semantic_category"]}
    bh_a = bh({c: p_cat[c] for c in fam_a})
    bh_b = bh({p: p_pos[p] for p in fam_b})

    def cat_row(c: str) -> dict:
        i = CATS.index(c)
        o = orig_cat.get(c, {})
        delta = round(float(obs_cat[i] - pooled), 4)
        return {"label": c, "n": int(cat_counts[i]),
                "mean_log1p_score": round(float(obs_cat[i]), 4),
                "delta_vs_pooled": delta, "perm_p": p_cat[c],
                "bh_significant_at_05": bool(bh_a.get(c, False)),
                "mde_delta": prereg["mde_at_realized_n"]["per_category_delta"][c],
                "humicroedit_delta": o.get("delta_vs_pooled"),
                "humicroedit_n": o.get("n"),
                "sign_match_vs_humicroedit": (None if c not in orig_cat else
                                              bool(delta * o["delta_vs_pooled"] > 0))}
    cat_stats = sorted((cat_row(c) for c in fam_a), key=lambda d: -d["mean_log1p_score"])
    pos_stats = sorted(({"label": p, "n": int(pos_counts_v[POS_LABELS.index(p)]),
                         "mean_log1p_score": round(float(obs_pos[POS_LABELS.index(p)]), 4),
                         "delta_vs_pooled": round(float(obs_pos[POS_LABELS.index(p)] - pooled), 4),
                         "perm_p": p_pos[p], "bh_significant_at_05": bool(bh_b.get(p, False))}
                        for p in fam_b), key=lambda d: -d["mean_log1p_score"])

    say("--- dominant semantic category vs pooled mean (family A, BH within family) ---")
    for s in cat_stats:
        star = " *BH" if s["bh_significant_at_05"] else ""
        sm = {True: "sign=SAME", False: "sign=FLIP", None: ""}[s["sign_match_vs_humicroedit"]]
        say(f"  {s['label']:11s} n={s['n']:6d} delta {s['delta_vs_pooled']:+.4f} "
            f"(mde {s['mde_delta']}) p={s['perm_p']:.5f}{star}  "
            f"humicroedit {s['humicroedit_delta']:+.4f} {sm}")
    say(f"concreteness spearman rho={obs_rho:+.4f} p={p_rho:.5f}")

    # delta-vector agreement across the categories both studies report
    common = [c for c in fam_a if c in orig_cat]
    ours = [float(obs_cat[CATS.index(c)] - pooled) for c in common]
    theirs = [orig_cat[c]["delta_vs_pooled"] for c in common]
    delta_agreement = {
        "n_common_categories": len(common),
        "n_sign_match": sum(1 for a, b_ in zip(ours, theirs) if a * b_ > 0),
        "delta_spearman_descriptive": hf.spearman(ours, theirs),
        "note": "descriptive over ~10 category points; not a test"}

    stage = {"config": {"seed": SEED, "n_perm": N_PERM, "min_group": MIN_GROUP},
             "pooled_mean": round(pooled, 4), "cat_stats": cat_stats,
             "pos_stats": pos_stats, "concreteness": {"rho": round(obs_rho, 4), "p": p_rho},
             "delta_agreement": delta_agreement}
    STAGE_CKPT.write_text(json.dumps(stage, indent=2), encoding="utf-8")
    say(f"stage checkpoint -> {STAGE_CKPT.name}")

    # ---------------- stage 7: predictive-lift replication ---------------
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import KFold
    Xs = np.array([r["_struct"] for r in built], dtype=float)
    Xt = np.array([r["_type"] for r in built], dtype=float)
    Xa = np.hstack([Xs, Xt])
    say(f"5-fold CV: structural {Xs.shape[1]} vs structural+type {Xa.shape[1]} features, "
        f"HistGradientBoostingRegressor(max_iter=300, lr=0.06, seed {SEED})")
    folds, oof_s, oof_a = [], np.zeros(n), np.zeros(n)
    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    for fi, (itr, ite) in enumerate(kf.split(Xs), 1):
        t0 = time.time()
        rho = {}
        for arm, X, oof in (("structural_only", Xs, oof_s), ("structural_plus_type", Xa, oof_a)):
            m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06,
                                              random_state=SEED)
            m.fit(X[itr], y[itr])
            pred = m.predict(X[ite])
            oof[ite] = pred
            rho[arm] = hf.spearman(list(pred), list(y[ite]))   # tied midranks
        folds.append({"fold": fi, **rho,
                      "lift": round(rho["structural_plus_type"] - rho["structural_only"], 4)})
        say(f"  fold {fi}: struct {rho['structural_only']:+.4f}  "
            f"+type {rho['structural_plus_type']:+.4f}  lift {folds[-1]['lift']:+.4f} "
            f"({time.time() - t0:.0f}s)")
    lifts = np.array([f["lift"] for f in folds])
    rng = np.random.default_rng(SEED)
    boots = rng.choice(lifts, size=(10_000, len(lifts)), replace=True).mean(axis=1)
    ci = [round(float(np.percentile(boots, q)), 4) for q in (2.5, 97.5)]
    pooled_oof = {"structural_only": hf.spearman(list(oof_s), list(y)),
                  "structural_plus_type": hf.spearman(list(oof_a), list(y))}
    lift_mean = round(float(lifts.mean()), 4)
    say(f"mean fold lift {lift_mean:+.4f}, bootstrap CI95 {ci}; pooled OOF "
        f"struct {pooled_oof['structural_only']:+.4f} -> +type {pooled_oof['structural_plus_type']:+.4f}")

    # ---------------- stage 8: receipt -----------------------------------
    bp = next((s for s in cat_stats if s["label"] == "body part"), None)
    h1 = (bp is not None and bp["delta_vs_pooled"] > 0 and bp["bh_significant_at_05"])
    h2 = bool(lift_mean > 0 and ci[0] > 0)
    h3 = bool(obs_rho > 0 and p_rho < 0.05)
    report = {
        "receipt_type": "word_type_rjokes_replication",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "status": "complete",
        "seed": SEED,
        "question": ("do the Humicroedit word-type findings (body-part/concrete words land "
                     "higher; word-type features add held-out predictive power) replicate on "
                     "r/Jokes, the population where the structural model collapsed "
                     "(cross_corpus_transfer 0.508 -> -0.009)?"),
        "dataset": {"file": str(DATA.relative_to(RESEARCH)), **screening,
                    "outcome": ("log1p(upvote score): a POPULARITY PROXY confounded by timing "
                                "and visibility, NOT a funniness grade (cross_corpus_transfer "
                                "caveat inherited); transfer_study used the monotone-equivalent "
                                "log2(1+score)")},
        "classifier_provenance": {
            "instrument": ("word_taxonomy sentence-framed embedding anchors "
                           f"({wt.EMB_MODEL}, frame {wt.FRAME_WORD!r}), anchor cache and "
                           "word-type cache shared with the original study and extended in place"),
            "hand_check_reliability": "original receipt: right about 10 of 12 on a hand-checked demo",
            "content_vocab": len(vocab), "cached_before": len(vocab) - len(missing),
            "newly_classified": embed_info["newly_classified"],
            "endpoint_parity": embed_info["parity"],
            "coverage_before": cov_before, "coverage_after": cov_after},
        "pre_registration": prereg,
        "pooled_mean_log1p_score": round(pooled, 4),
        "n_rows_built": n, "skipped_no_classified_word": skipped,
        "by_semantic_category": cat_stats,
        "delta_vector_agreement_vs_humicroedit": delta_agreement,
        "by_part_of_speech_descriptive": pos_stats,
        "concreteness": {"spearman_vs_outcome": round(obs_rho, 4), "perm_p": p_rho,
                         "mde": prereg["mde_at_realized_n"]["H3_spearman_mde"]},
        "predictive_lift": {
            "design": "5-fold seeded CV (original: single 70/30 split, seed 20260725)",
            "model": "HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06) — matches original",
            "per_fold": folds,
            "lift_mean": lift_mean, "lift_bootstrap_ci95_over_folds": ci,
            "bootstrap_note": "10000 resamples of 5 fold lifts; 5 points make a coarse CI, receipted as such",
            "pooled_oof_spearman": pooled_oof,
            "n_struct_features": int(Xs.shape[1]), "n_type_features": int(Xt.shape[1]),
            "humicroedit_reference": original["predictive_lift"]},
        "verdicts": {
            "H1_body_part_positive_delta": {"replicates": bool(h1), "observed": bp},
            "H2_type_block_lifts_heldout_spearman": {"replicates": h2,
                                                     "lift_mean": lift_mean, "ci95": ci},
            "H3_concreteness_positive": {"holds": h3, "rho": round(obs_rho, 4), "p": p_rho}},
        "truth_boundary": {
            "verified": ("associations between embedding-assigned punchline word types and "
                         "log-upvotes within one subreddit's bulk harvest, plus the held-out "
                         "predictive increment of those types over 30 surface features"),
            "not_claimed": ("that upvotes measure funniness (popularity proxy; timing and "
                            "visibility confounds); that the result generalizes beyond r/Jokes; "
                            "that categories are exact (classifier ~10/12 on hand-check, and "
                            "the modal-category reduction is a reconstruction, not the "
                            "original single-edit-word instrument); that rarity features are "
                            "corpus-independent (frequency table includes this file, "
                            "outcome-blind)")},
        "caveats": ("one community, one platform, popularity outcome; dominant-category labels "
                    "dilute on long punchlines (median 3 content words, p95 = 16); category "
                    "means inherit classifier error; per-fold lift CI rests on 5 folds; no "
                    "per-word rankings are reported anywhere in this receipt by design"),
        "data_note": "no joke text appears in this receipt; dataset identified by sha256 prefix",
        "runtime_s": round(time.time() - T0, 1),
    }
    RECEIPT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    say(f"receipt -> {RECEIPT}")
    say(f"HEADLINE: H1 body-part {'REPLICATES' if h1 else 'does NOT replicate'} "
        f"(delta {bp['delta_vs_pooled'] if bp else 'n/a'}); "
        f"H2 lift {'REPLICATES' if h2 else 'does NOT replicate'} ({lift_mean:+.4f} CI {ci}); "
        f"H3 concreteness {'holds' if h3 else 'does not hold'} ({obs_rho:+.4f})")


if __name__ == "__main__":
    main()
