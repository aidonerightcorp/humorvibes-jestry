#!/usr/bin/env python3
"""Does the pooled caption arm of three_corpus_study.py survive WITHIN contest?

RESULTS.md flags this twice: the three-corpus study's New Yorker column pools
captions across contests, which is a known confound — a feature can correlate
with the crowd mean merely because contests differ in both the feature and the
mean. The sole cross-corpus survivor, ``punch_rarity_max`` (pooled caption
rho = -0.0874), inherits that pooling, as do every other per-feature sign and
FDR survival in that column. This study re-runs the caption arm with the
contest held fixed.

Protocol (preregistered in the receipt BEFORE any correlation is computed):

- Same 30-feature extractor as the pooled run, REUSED BY IMPORT from
  ``humor_features.py`` (byte-identical in the repo and the research tree; the
  module's data paths are redirected to --data-root, which is exactly how the
  original resolved them by living there). No feature is reimplemented.
- Same integrity screens as ``divisiveness_study.py`` on the certified
  ``caption_index.parquet``: votes == nf+sf+f, recomputed mean within 0.02 of
  the harvest mean, votes >= 20. Drop counts receipted.
- Contests with >= 200 valid captions; up to 1,500 captions sampled per
  contest with a seeded RNG.
- Per feature: tied-midrank Spearman (scipy.stats.spearmanr semantics,
  validated cell-for-cell against scipy) between the feature and mean_exact
  WITHIN each contest; summarized as the median within-contest rho and the
  share of contests matching the pooled run's sign.
- Significance: permutation test shuffling mean_exact WITHIN contest
  (contest structure preserved), statistic = median within-contest rho,
  two-sided p = (1 + #{|perm| >= |obs|}) / (1 + n_perm), then
  Benjamini-Hochberg across the declared family of exactly 30 features.

Nine of the 30 features are constant by construction in this arm (the cartoon
has no text, so setup is empty): they are declared degenerate up front and
enter the family at p = 1, exactly as they did in the pooled run. Caption text
never enters the receipt or the checkpoint.

Usage:
    python3 caption_within_contest_study.py \
        --data-root /path/to/build-with-gemma-humor-genome-nyc \
        --out jestry_out/caption_within_contest_study.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy import stats as sps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import humor_features  # noqa: E402  (path set above)
from humor_features import (benjamini_hochberg, build_frequencies,  # noqa: E402
                            features)

# Constant by construction when setup == "" (the cartoon has no text): every
# setup-side statistic is 0 for every row, echo_frac needs setup vocabulary,
# and end_rhyme needs a setup tail. These are exactly the nine features the
# pooled receipt reports at rho == 0.0. Declared BEFORE results; they enter
# the BH family at p = 1 (the pooled run's own convention for them).
DECLARED_DEGENERATE = [
    "echo_frac", "end_rhyme", "setup_chars", "setup_mean_wordlen",
    "setup_rarity_final", "setup_rarity_max", "setup_rarity_mean",
    "setup_syllables", "setup_words",
]
# Exact identities when setup == "": word_ratio == punch_words and
# syllable_ratio == punch_syllables (max(1, 0) == 1 in the denominators), and
# the pair_* phonetic features equal their punch_* twins because
# all_words == punch words. The pooled receipt shows each pair at identical
# rho, confirming the algebra. Declared up front so duplicate rows in the
# table are not read as independent confirmations.
DECLARED_COLLINEAR = {"word_ratio": "punch_words",
                      "syllable_ratio": "punch_syllables",
                      "pair_alliteration": "punch_alliteration",
                      "pair_assonance": "punch_assonance"}


def screen(parquet: Path) -> tuple[pd.DataFrame, dict]:
    """The divisiveness_study.py integrity screens, drop counts receipted."""
    df = pd.read_parquet(parquet, columns=["contest", "text", "votes", "nf",
                                           "sf", "f", "mean_harvest"])
    n_raw = len(df)
    for col in ("votes", "nf", "sf", "f"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["votes", "nf", "sf", "f", "text"])
    df = df[(df["votes"] > 0) & (df["nf"] >= 0) & (df["sf"] >= 0) & (df["f"] >= 0)]
    n_basic = len(df)
    consistent = df["votes"] == df["nf"] + df["sf"] + df["f"]
    n_count_mismatch = int((~consistent).sum())
    df = df[consistent]
    df["mean_exact"] = (1 * df["nf"] + 2 * df["sf"] + 3 * df["f"]) / df["votes"]
    mean_ok = (df["mean_harvest"].isna()) | ((df["mean_exact"] - df["mean_harvest"]).abs() <= 0.02)
    n_mean_mismatch = int((~mean_ok).sum())
    df = df[mean_ok]
    df = df[df["votes"] >= 20]
    screens = {
        "rows_raw": n_raw,
        "dropped_nonfinite_or_nonpositive": n_raw - n_basic,
        "dropped_count_mismatch": n_count_mismatch,
        "dropped_mean_mismatch": n_mean_mismatch,
        "kept_votes_ge_20": int(len(df)),
    }
    return df, screens


def featurize(work: pd.DataFrame, names: list[str], freq: dict, total: int) -> np.ndarray:
    F = np.empty((len(work), len(names)), dtype=np.float64)
    t0 = time.time()
    texts = work["text"].astype(str).to_numpy()
    for i, txt in enumerate(texts):
        f = features("", txt, freq, total)
        for j, n in enumerate(names):
            F[i, j] = f[n]
        if (i + 1) % 50_000 == 0:
            rate = (i + 1) / (time.time() - t0)
            print(f"    featurized {i + 1}/{len(texts)} rows ({rate:.0f}/s)", flush=True)
    return F


def atomic_write(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def bh_q(pvals: dict[str, float]) -> dict[str, float]:
    """Standard BH step-up adjusted q values (monotone from the right)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    raw = [p * m / (i + 1) for i, (_, p) in enumerate(items)]
    for i in range(m - 2, -1, -1):
        raw[i] = min(raw[i], raw[i + 1])
    return {k: min(1.0, q) for (k, _), q in zip(items, raw)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=".")
    ap.add_argument("--out", default="jestry_out/caption_within_contest_study.json")
    ap.add_argument("--seed", type=int, default=20260728)
    ap.add_argument("--per-contest-cap", type=int, default=1_500)
    ap.add_argument("--min-contest-rows", type=int, default=200)
    ap.add_argument("--n-perm", type=int, default=1_000)
    ap.add_argument("--validate-cells", type=int, default=200)
    args = ap.parse_args()
    t0 = time.time()

    root = Path(args.data_root).resolve()
    parquet = root / "data_cache" / "caption_index.parquet"
    if not parquet.exists():
        raise SystemExit(f"missing {parquet}")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ckpt_path = root / "jestry_out" / "caption_within_contest_rows.parquet"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)

    # --- feature extractor, reused by import with paths redirected ----------
    # humor_features resolves CORPORA/CACHE_DIR relative to its own file; the
    # original pooled run resolved them by running from the research tree. The
    # repo and research copies are byte-identical, so redirecting the two path
    # constants reproduces the original resolution without touching any code.
    humor_features.CORPORA = root / "corpora"
    humor_features.CACHE_DIR = root / "data_cache"
    corpora_files = sorted(humor_features.CORPORA.glob("*.jsonl"))
    cache_key = humor_features._freq_cache_key(corpora_files)
    cache_file = humor_features.CACHE_DIR / f"word_frequencies_{cache_key}.json.gz"
    cache_hit = cache_file.exists()
    print(f"frequency cache key {cache_key} (hit={cache_hit})", flush=True)
    freq = build_frequencies()
    total = sum(freq.values())
    print(f"frequency table: {len(freq):,} types, {total:,} tokens", flush=True)

    # --- screens (divisiveness_study.py, verbatim) --------------------------
    df, screens = screen(parquet)
    df["contest"] = df["contest"].astype(str)
    print(f"screens: {screens}", flush=True)
    div_path = HERE / "jestry_out" / "divisiveness_study.json"
    if div_path.exists():
        div = json.loads(div_path.read_text(encoding="utf-8"))["screening"]
        screens["matches_divisiveness_study_receipt"] = (
            div["rows_raw"] == screens["rows_raw"]
            and div["dropped_count_mismatch"] == screens["dropped_count_mismatch"]
            and div["dropped_mean_mismatch"] == screens["dropped_mean_mismatch"]
            and div["kept_votes_ge_20"] == screens["kept_votes_ge_20"])
        print(f"screen counts match divisiveness receipt: "
              f"{screens['matches_divisiveness_study_receipt']}", flush=True)

    # --- per-contest sampling (seeded, contests in lexicographic order) -----
    rng_sample = np.random.default_rng(args.seed)
    parts = []
    for _, grp in df.groupby("contest", sort=True):
        if len(grp) < args.min_contest_rows:
            continue
        take = min(len(grp), args.per_contest_cap)
        parts.append(grp.sample(n=take, random_state=int(rng_sample.integers(0, 2**31))))
    work = pd.concat(parts, ignore_index=True)
    contests = work["contest"].to_numpy()
    seg_starts = np.flatnonzero(np.r_[True, contests[1:] != contests[:-1]])
    seg_ends = np.r_[seg_starts[1:], len(work)]
    contest_ids = [contests[s] for s in seg_starts]
    n_c = (seg_ends - seg_starts).astype(int)
    C = len(contest_ids)
    sampling = {
        "contests_eligible_ge_min": C,
        "min_contest_rows": args.min_contest_rows,
        "per_contest_cap": args.per_contest_cap,
        "rows_sampled": int(len(work)),
        "per_contest_n": {"min": int(n_c.min()), "median": float(np.median(n_c)),
                          "max": int(n_c.max())},
        "contests_at_cap": int((n_c == args.per_contest_cap).sum()),
        "sampling_note": ("per-contest pandas .sample with random_state drawn "
                          "sequentially from numpy default_rng(seed) over contests "
                          "in lexicographic order"),
    }
    print(f"sampled {len(work)} rows across {C} contests "
          f"(per-contest n: {n_c.min()}..{n_c.max()})", flush=True)

    # --- pooled comparison column (quoted, not recomputed) ------------------
    pooled_receipt = json.loads((HERE / "jestry_out" / "three_corpus_study.json")
                                .read_text(encoding="utf-8"))
    pooled_ny = pooled_receipt["per_corpus"]["newyorker"]
    pooled_rho = pooled_ny["spearman"]
    pooled_fdr = pooled_ny["survives_fdr"]
    names = sorted(pooled_rho)  # the declared 30-feature family, pooled order
    assert len(names) == 30, f"family must be exactly 30, got {len(names)}"

    # --- PREREGISTRATION: written to the receipt BEFORE any correlation -----
    se_typ = float(np.median(1.0 / np.sqrt(n_c - 1)))
    sd_median_null = float(1.2533 * se_typ / np.sqrt(C))
    z_bh1 = float(sps.norm.ppf(1 - (0.05 / 30) / 2))
    mde_bh_rank1 = round(z_bh1 * sd_median_null, 4)
    mde_nominal = round(1.959964 * sd_median_null, 4)
    p_floor = round(1.0 / (args.n_perm + 1), 6)
    prereg = {
        "written_before_results_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": (
            "H1: punch_rarity_max, the sole cross-corpus survivor of "
            "three_corpus_study.py (pooled caption rho -0.0874), retains a "
            "negative association with the crowd mean WITHIN contest (median "
            "within-contest rho < 0 and BH-FDR survival). The confound model "
            "predicts attenuation toward 0 once cross-contest pooling is removed. "
            "The other 29 features are re-tested under the same protocol."),
        "primary_metric": (
            "median within-contest tied-midrank Spearman rho vs mean_exact, plus "
            "BH-FDR survival of a within-contest permutation p (statistic = the "
            "median itself); secondary: share of contests matching the pooled sign"),
        "family_size": 30,
        "alpha": 0.05,
        "n_permutations": args.n_perm,
        "permutation_scheme": ("shuffle mean_exact WITHIN each contest, contest "
                               "structure preserved; two-sided "
                               "p = (1 + #{|perm median| >= |obs median|}) / (1 + n_perm)"),
        "seeds": {"sampling": args.seed,
                  "permutations": f"numpy default_rng([{args.seed}, 1])",
                  "validation_cells": f"numpy default_rng([{args.seed}, 2])"},
        "declared_degenerate_features": DECLARED_DEGENERATE,
        "degenerate_convention": (
            "9 of the 30 features are constant by construction in this arm "
            "(setup is empty: the cartoon has no text), so a within-contest rank "
            "correlation cannot fire for them at ANY n. They stay in the declared "
            "family at p = 1 — the pooled run's own value for them — rather than "
            "being reported as null results."),
        "declared_collinear_identities": DECLARED_COLLINEAR,
        "minimum_detectable_effect": {
            "back_of_envelope": (
                f"single within-contest null Spearman SE ~ 1/sqrt(n-1); median "
                f"sampled per-contest n gives typical SE {se_typ:.4f}; the median "
                f"across C={C} contests has null SD ~ 1.2533*SE/sqrt(C) = "
                f"{sd_median_null:.4f}; two-sided detection at the BH rank-1 "
                f"threshold p<=0.05/30 (z={z_bh1:.2f}) needs |median rho| >~ "
                f"{mde_bh_rank1}; at nominal alpha=0.05, >~ {mde_nominal}."),
            "typical_within_contest_se": round(se_typ, 4),
            "null_sd_of_median": round(sd_median_null, 5),
            "mde_abs_median_rho_at_bh_rank1": mde_bh_rank1,
            "mde_abs_median_rho_nominal_05": mde_nominal,
            "resolution_statement": (
                f"permutation p floor = 1/(n_perm+1) = {p_floor}, which is below "
                f"the BH rank-1 cutoff 0.05/30 = {round(0.05 / 30, 6)}, so a single "
                f"survivor CAN fire at this permutation count. Any observed "
                f"|median rho| below ~{mde_bh_rank1} is below design resolution: "
                f"a non-survival there is 'underpowered', not evidence of absence."),
        },
    }
    receipt_stub = {
        "receipt_type": "caption_within_contest_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "preregistered",
        "preregistration": prereg,
        "screens": screens,
        "sampling": sampling,
    }
    atomic_write(out_path, receipt_stub)
    print(f"preregistration written -> {out_path} (before any correlation)", flush=True)
    print(f"  MDE @ BH rank-1: |median rho| >~ {mde_bh_rank1}", flush=True)

    # --- featurize (or resume from the research-tree checkpoint) ------------
    ck_meta = {"seed": args.seed, "per_contest_cap": args.per_contest_cap,
               "min_contest_rows": args.min_contest_rows,
               "screens": {k: v for k, v in screens.items() if isinstance(v, int)},
               "freq_cache_key": cache_key, "feature_names": names,
               "n_rows": int(len(work))}
    F = None
    if ckpt_path.exists():
        try:
            tbl = pq.read_table(ckpt_path)
            meta = json.loads(tbl.schema.metadata[b"study_meta"].decode())
            if meta == ck_meta:
                ck = tbl.to_pandas()
                if (ck["contest"].to_numpy() == contests).all() and \
                   np.array_equal(ck["mean_exact"].to_numpy(),
                                  work["mean_exact"].to_numpy()):
                    F = ck[names].to_numpy(dtype=np.float64)
                    print(f"resumed features from checkpoint {ckpt_path}", flush=True)
        except Exception as e:  # noqa: BLE001 - a bad checkpoint just refeaturizes
            print(f"checkpoint unusable ({e}); refeaturizing", flush=True)
    if F is None:
        print(f"featurizing {len(work)} rows x {len(names)} features…", flush=True)
        F = featurize(work, names, freq, total)
        ckdf = pd.DataFrame({"contest": contests,
                             "votes": work["votes"].to_numpy(),
                             "mean_exact": work["mean_exact"].to_numpy()})
        for j, n in enumerate(names):
            ckdf[n] = F[:, j]
        tbl = pa.Table.from_pandas(ckdf, preserve_index=False)
        tbl = tbl.replace_schema_metadata({b"study_meta": json.dumps(ck_meta).encode()})
        pq.write_table(tbl, ckpt_path)
        print(f"row checkpoint (features only, no caption text) -> {ckpt_path}", flush=True)
    y = work["mean_exact"].to_numpy(dtype=np.float64)

    # --- per-contest tied midranks, normalized ------------------------------
    # Spearman == Pearson on tied midranks; ranking commutes with permutation
    # of y, so per-contest normalized rank vectors are permutation-reusable.
    # Validated against scipy.stats.spearmanr cell-for-cell below.
    Zf_segs, zy_segs = [], []
    finite = np.zeros((C, len(names)), dtype=bool)
    y_const = 0
    for ci, (s, e) in enumerate(zip(seg_starts, seg_ends)):
        R = sps.rankdata(F[s:e], method="average", axis=0)
        R -= R.mean(axis=0)
        norms = np.sqrt((R ** 2).sum(axis=0))
        const = norms == 0
        norms[const] = 1.0
        R /= norms
        R[:, const] = 0.0
        ry = sps.rankdata(y[s:e], method="average")
        ry -= ry.mean()
        ny = np.sqrt((ry ** 2).sum())
        if ny == 0:
            y_const += 1
            finite[ci, :] = False
            Zf_segs.append(R)
            zy_segs.append(np.zeros_like(ry))
            continue
        ry /= ny
        finite[ci, :] = ~const
        Zf_segs.append(np.ascontiguousarray(R))
        zy_segs.append(ry)
    rho_obs = np.full((C, len(names)), np.nan)
    for ci in range(C):
        r = zy_segs[ci] @ Zf_segs[ci]
        rho_obs[ci, finite[ci]] = r[finite[ci]]

    # --- validation: the fast path IS scipy.stats.spearmanr -----------------
    rng_val = np.random.default_rng([args.seed, 2])
    fin_cells = np.argwhere(finite)
    pick = fin_cells[rng_val.choice(len(fin_cells),
                                    size=min(args.validate_cells, len(fin_cells)),
                                    replace=False)]
    max_diff = 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for ci, j in pick:
            s, e = seg_starts[ci], seg_ends[ci]
            ref = sps.spearmanr(F[s:e, j], y[s:e]).statistic
            max_diff = max(max_diff, abs(ref - rho_obs[ci, j]))
        degen_cells = np.argwhere(~finite)
        degen_agree = True
        for ci, j in degen_cells[rng_val.choice(len(degen_cells),
                                                size=min(10, len(degen_cells)),
                                                replace=False)]:
            s, e = seg_starts[ci], seg_ends[ci]
            if not np.isnan(sps.spearmanr(F[s:e, j], y[s:e]).statistic):
                degen_agree = False
    print(f"scipy validation: max |diff| over {len(pick)} cells = {max_diff:.2e}; "
          f"degenerate cells NaN in scipy too: {degen_agree}", flush=True)

    # --- observed summaries -------------------------------------------------
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        med_obs = np.nanmedian(rho_obs, axis=0)
    n_used = finite.sum(axis=0)
    med_obs[n_used == 0] = np.nan

    # --- permutation test: shuffle y within contest, 1000x ------------------
    rng_perm = np.random.default_rng([args.seed, 1])
    hits = np.zeros(len(names), dtype=np.int64)
    testable = np.isfinite(med_obs)
    rho_p = np.full((C, len(names)), np.nan)
    tp = time.time()
    for p in range(args.n_perm):
        for ci in range(C):
            if not finite[ci].any():
                continue
            idx = rng_perm.permutation(len(zy_segs[ci]))
            r = zy_segs[ci][idx] @ Zf_segs[ci]
            rho_p[ci, finite[ci]] = r[finite[ci]]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            med_p = np.nanmedian(rho_p, axis=0)
        hits[testable] += (np.abs(med_p[testable]) >= np.abs(med_obs[testable]))
        if (p + 1) % 100 == 0:
            print(f"    permutation {p + 1}/{args.n_perm} "
                  f"({(p + 1) / (time.time() - tp):.1f}/s)", flush=True)
    perm_p = {}
    for j, n in enumerate(names):
        perm_p[n] = round(float((1 + hits[j]) / (1 + args.n_perm)), 6) if testable[j] else 1.0

    # --- BH across the declared family of exactly 30 ------------------------
    survives = benjamini_hochberg(perm_p, alpha=0.05)
    qvals = bh_q(perm_p)
    assert all(survives[k] == (qvals[k] <= 0.05) for k in perm_p), "BH q/bool disagree"

    # --- per-feature table (alphabetical: no ranking by noisy magnitude) ----
    table = []
    for j, n in enumerate(names):
        prho = pooled_rho[n]
        row = {
            "feature": n,
            "pooled_rho_from_three_corpus_receipt": prho,
            "pooled_survives_fdr": bool(pooled_fdr[n]),
            "median_within_contest_rho": (round(float(med_obs[j]), 4)
                                          if testable[j] else None),
            "n_contests_used": int(n_used[j]),
            "sign_consistent_share": None,
            "perm_p": perm_p[n],
            "q_bh": round(qvals[n], 6),
            "survives": bool(survives[n]),
        }
        if testable[j] and prho != 0.0:
            sgn = 1.0 if prho > 0 else -1.0
            vals = rho_obs[finite[:, j], j]
            row["sign_consistent_share"] = round(float(np.mean(np.sign(vals) == sgn)), 4)
        if n in DECLARED_DEGENERATE:
            row["status"] = "degenerate_constant_in_caption_arm (declared pre-hoc; p=1 by convention)"
        if n in DECLARED_COLLINEAR:
            row["status"] = f"identical to {DECLARED_COLLINEAR[n]} when setup is empty (declared pre-hoc)"
        table.append(row)

    observed_degenerate = sorted(n for j, n in enumerate(names) if n_used[j] == 0)
    degenerate_matches = observed_degenerate == sorted(DECLARED_DEGENERATE)

    # --- verdict on the preregistered feature -------------------------------
    j_prm = names.index("punch_rarity_max")
    prm = table[j_prm]
    med = prm["median_within_contest_rho"]
    mde = mde_bh_rank1
    if prm["survives"] and med is not None and np.sign(med) == np.sign(prm["pooled_rho_from_three_corpus_receipt"]):
        ratio = med / prm["pooled_rho_from_three_corpus_receipt"]
        tail = (f"the effect holds within contest at {ratio:.0%} of the pooled magnitude — "
                f"it is not a cross-contest pooling artifact"
                if ratio >= 0.5 else
                f"the effect survives within contest but attenuates to {ratio:.0%} of the "
                f"pooled magnitude — part of the pooled value was pooling")
    elif med is not None and abs(med) < mde:
        tail = (f"the within-contest effect is below the design resolution (~{mde}) and does "
                f"not survive; the pooled value is consistent with a cross-contest pooling "
                f"artifact (with the caveat that |rho| < {mde} cannot be ruled in or out here)")
    elif prm["survives"]:
        tail = "the effect survives within contest but with the OPPOSITE sign — the pooled sign is a pooling artifact"
    else:
        tail = (f"the effect does not survive BH within contest despite being above the "
                f"~{mde} resolution — the pooled survival does not replicate within contest")
    verdict = (
        f"punch_rarity_max: pooled caption rho {prm['pooled_rho_from_three_corpus_receipt']:+.4f} "
        f"(pooled FDR survivor); within contest, median within-contest rho "
        f"{med:+.4f} across {prm['n_contests_used']} contests, "
        f"{prm['sign_consistent_share']:.1%} of contests matching the pooled sign, "
        f"permutation p {prm['perm_p']:.4g}, q_BH {prm['q_bh']:.4g} — "
        f"{'survives' if prm['survives'] else 'does not survive'} FDR in the 30-feature family; {tail}.")

    within_survivors = sorted(r["feature"] for r in table if r["survives"])
    pooled_survivors = sorted(k for k, v in pooled_fdr.items() if v)

    receipt = {
        "receipt_type": "caption_within_contest_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "question": ("do the pooled New Yorker per-feature results of "
                     "three_corpus_study.py survive when the contest is held fixed?"),
        "preregistration": prereg,
        "provenance": {
            "feature_extractor": ("humor_features.features imported from the repo, "
                                  "byte-identical to the research-tree copy; data paths "
                                  "redirected to --data-root (how the original resolved them)"),
            "humor_features_sha256_16": "ad27055afeedaa55",
            "data_root": str(root),
            "caption_index_rows": screens["rows_raw"],
            "frequency_table": {"types": len(freq), "tokens": total,
                                "cache_key": cache_key, "cache_hit": cache_hit},
            "pooled_comparison_source": "jestry_out/three_corpus_study.json (quoted, not recomputed)",
            "spearman_engine": {
                "method": ("per-contest tied-midrank rank-Pearson (scipy.stats.rankdata "
                           "method='average'), validated cell-for-cell against "
                           "scipy.stats.spearmanr"),
                "validated_cells": int(len(pick)),
                "max_abs_diff_vs_scipy": float(f"{max_diff:.3e}"),
                "degenerate_cells_nan_in_scipy_too": bool(degen_agree),
            },
        },
        "screens": screens,
        "sampling": sampling,
        "contests_with_constant_mean_excluded": y_const,
        "per_feature": table,
        "degenerate_features": {
            "declared_pre_hoc": sorted(DECLARED_DEGENERATE),
            "observed": observed_degenerate,
            "observed_matches_declared": degenerate_matches,
        },
        "within_contest_fdr_survivors": within_survivors,
        "pooled_fdr_survivors_for_reference": pooled_survivors,
        "punch_rarity_max_verdict": verdict,
        "truth_boundary": {
            "verified": ("within-contest rank association between 30 deterministic surface "
                         "features and the crowd mean rating of ONE publication's caption "
                         "contest (screened votes>=20 rows); this is within-one-publication "
                         "caption behavior"),
            "not_verified": ("humor in general, other audiences, other formats, causal "
                             "claims, or any setup-side feature — the cartoon has no text, "
                             "so setup-side features are structurally untestable here"),
        },
        "caveats": [
            "per-contest sampling cap of 1,500 rows (seeded, receipted); results are "
            "conditional on that cap",
            "the family is the 30 features exactly as declared; 9 structurally constant "
            "features enter BH at p=1 (the pooled run's own convention), which only makes "
            "the correction more conservative for the 21 testable features",
            "word_ratio, syllable_ratio, pair_alliteration and pair_assonance are exact "
            "duplicates of punch_words, punch_syllables, punch_alliteration and "
            "punch_assonance in this arm (empty setup) — 21 testable features carry at "
            "most 17 distinct signals",
            "the word-frequency table is the research tree's CURRENT corpus "
            f"(cache {cache_key}), which postdates the 2026-07-25 pooled run — the corpus "
            "grew on 2026-07-26, including the caption harvest itself — so rarity features "
            "here use a larger frequency table than the pooled numbers did; the pooled "
            "column is quoted from the committed receipt, not recomputed",
            "the pooled arm sampled the first 60k cached rows at votes>=40 and held out "
            "30%; this arm uses the certified caption_index at votes>=20 with integrity "
            "screens across all contests — a documented population difference on top of "
            "the pooling difference under test",
            f"permutation resolution: p floor {p_floor} with {args.n_perm} permutations",
            "no caption text appears in this receipt or in the row checkpoint",
        ],
        "runtime_s": round(time.time() - t0, 1),
    }
    atomic_write(out_path, receipt)

    print(f"\n--- per-feature within-contest results (alphabetical; family=30) ---", flush=True)
    for r in table:
        m = "     " if r["median_within_contest_rho"] is None else f"{r['median_within_contest_rho']:+.4f}"
        s = "  n/a " if r["sign_consistent_share"] is None else f"{r['sign_consistent_share']:.3f}"
        flag = "FDR" if r["survives"] else ("degen" if r["feature"] in DECLARED_DEGENERATE else "   ")
        print(f"  {r['feature']:22s} pooled {r['pooled_rho_from_three_corpus_receipt']:+.4f}  "
              f"within {m}  signshare {s}  p={r['perm_p']:.4g}  q={r['q_bh']:.4g}  {flag}")
    print(f"\nwithin-contest FDR survivors ({len(within_survivors)}): {within_survivors}")
    print(f"\n{verdict}")
    print(f"\nreceipt -> {out_path} ({time.time() - t0:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
