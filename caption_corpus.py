#!/usr/bin/env python3
"""Loader for the New Yorker caption-contest corpus, with a columnar cache.

The 2026-07-26 harvest brought in 2.19M ranked captions over 371 contests, each
carrying the raw vote breakdown (not_funny / somewhat_funny / funny). That
breakdown is the reason this corpus is different from every other one here: it
is the only one where the MEASUREMENT ERROR of the label is visible, so a
predictor's score can be compared against what the label can support rather
than against 1.0.

Structure that matters for any study built on it:

* the drawing holds the situation FIXED while the captions vary, so a
  within-contest comparison is controlled in a way a pile of jokes is not;
* contests differ wildly in how many votes each caption drew, so anything
  pooled across contests mixes caption quality with contest-level vote scale;
* the same caption text recurs, both inside one contest and across contests,
  which is a free experiment as long as re-ingested rows are not mistaken for
  independent re-submissions (`--probe` reports exactly that).

    python3 caption_corpus.py --probe       # structure report, no cache write
    python3 caption_corpus.py --build       # build/refresh the parquet cache
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CORPORA = HERE / "corpora"
CACHE = HERE / "data_cache" / "caption_index.parquet"
CACHE_META = CACHE.with_suffix(".meta.json")
PATTERN = "harvest_nextml_*.jsonl"

# A caption's mean is on the 1..3 scale (not_funny=1, somewhat=2, funny=3).
SCALE = np.array([1.0, 2.0, 3.0])


def _norm_text(t: str) -> str:
    """Key for duplicate detection: case, whitespace and curly quotes folded.

    Deliberately NOT stemmed or punctuation-stripped — two captions differing
    by a comma are the same joke, two differing by a word are not, and an
    aggressive normaliser would quietly merge the second kind.
    """
    t = t.replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t).strip().lower()


def iter_raw():
    for path in sorted(CORPORA.glob(PATTERN)):
        with path.open(encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"malformed caption JSON in {path}:{line_no}: {exc.msg}"
                    ) from exc
                if "_meta" in rec:
                    continue
                m = rec.get("meta") or {}
                if m.get("record_kind") != "ranked_caption":
                    continue
                yield path.name, rec, m


def build(verbose: bool = True) -> pd.DataFrame:
    rows = []
    for fname, rec, m in iter_raw():
        try:
            votes = float(m.get("votes") or 0)
            nf = float(m.get("not_funny") or 0)
            sf = float(m.get("somewhat_funny") or 0)
            f = float(m.get("funny") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid vote counts in {fname}, contest {m.get('contest')!r}"
            ) from exc
        rows.append((str(m.get("contest")), rec.get("text", ""), votes, nf, sf, f,
                     float(rec.get("funniness_label") or 0), rec.get("source", ""), fname))
    df = pd.DataFrame(rows, columns=["contest", "text", "votes", "nf", "sf", "f",
                                     "mean_harvest", "source", "file"])
    df["contest"] = df["contest"].astype("category")
    df["source"] = df["source"].astype("category")
    df["file"] = df["file"].astype("category")
    df["norm"] = [_norm_text(t) for t in df["text"]]
    if verbose:
        print(f"parsed {len(df):,} ranked captions from "
              f"{len(list(CORPORA.glob(PATTERN)))} harvest files")
    return df


def _source_identity() -> tuple[str, list[Path]]:
    """Cheap, local identity for the caption files behind the columnar cache."""
    files = sorted(CORPORA.glob(PATTERN))
    manifest = "|".join(
        f"{path.name}:{path.stat().st_size}:{path.stat().st_mtime_ns}"
        for path in files
    )
    return hashlib.sha256(manifest.encode()).hexdigest(), files


def _write_cache_meta(identity: str, files: list[Path], rows: int) -> None:
    CACHE_META.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_META.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "schema_version": 1,
        "source_identity": identity,
        "rows": rows,
        "files": [{"name": p.name, "bytes": p.stat().st_size,
                   "mtime_ns": p.stat().st_mtime_ns} for p in files],
    }, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CACHE_META)


def load(rebuild: bool = False) -> pd.DataFrame:
    identity, files = _source_identity()
    if CACHE.exists() and not rebuild:
        valid = False
        if CACHE_META.exists():
            try:
                valid = json.loads(CACHE_META.read_text(
                    encoding="utf-8")).get("source_identity") == identity
            except (OSError, json.JSONDecodeError):
                valid = False
        elif files:
            # One-time migration for the already-verified pre-metadata cache:
            # accept it only when it is newer than every source it summarizes,
            # then pin the exact identity for every subsequent read.
            valid = CACHE.stat().st_mtime_ns >= max(p.stat().st_mtime_ns for p in files)
        if valid:
            try:
                df = pd.read_parquet(CACHE)
                if not CACHE_META.exists():
                    _write_cache_meta(identity, files, len(df))
                return df
            except (OSError, ValueError):
                pass
    df = build()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(CACHE)
    _write_cache_meta(identity, files, len(df))
    return df


def counts_matrix(df: pd.DataFrame) -> np.ndarray:
    return np.stack([df["nf"].to_numpy(), df["sf"].to_numpy(), df["f"].to_numpy()], axis=1)


def probe(df: pd.DataFrame) -> dict:
    """Report the structure a study has to respect, rather than assume it."""
    out: dict = {}
    out["n_captions"] = int(len(df))
    out["n_contests"] = int(df["contest"].nunique())

    C = counts_matrix(df)
    tot = C.sum(axis=1)
    out["vote_total_vs_votes_field_mismatch"] = int(np.sum(np.abs(tot - df["votes"].to_numpy()) > 0.5))
    out["votes"] = {
        "min": float(np.min(tot)), "median": float(np.median(tot)),
        "mean": float(np.mean(tot)), "max": float(np.max(tot)),
        "share_ge_20": float(np.mean(tot >= 20)),
        "share_ge_50": float(np.mean(tot >= 50)),
        "share_ge_100": float(np.mean(tot >= 100)),
    }
    # recomputed mean vs the harvested label: a disagreement means one of the
    # two is not what it claims, and every downstream number would inherit it.
    with np.errstate(invalid="ignore", divide="ignore"):
        recomputed = (C * SCALE).sum(axis=1) / np.where(tot > 0, tot, np.nan)
    d = np.abs(recomputed - df["mean_harvest"].to_numpy())
    out["recomputed_mean_max_abs_diff"] = float(np.nanmax(d))
    out["recomputed_mean_disagree_gt_1e6"] = int(np.nansum(d > 1e-6))

    # ---- duplicate structure -------------------------------------------
    # Same normalised text inside one contest. Two readings are possible and
    # they demand opposite treatment, so they are separated here:
    #   * genuinely re-submitted caption   -> independent vote sample, usable
    #   * one row ingested twice           -> the same measurement, not usable
    # An identical (votes, nf, sf, f) tuple is the fingerprint of the latter.
    g = defaultdict(list)
    for contest, norm, nf, sf, f in zip(df["contest"].astype(str), df["norm"],
                                        df["nf"], df["sf"], df["f"]):
        g[(contest, norm)].append((nf, sf, f))
    dup_groups = {k: v for k, v in g.items() if len(v) > 1}
    identical = sum(1 for v in dup_groups.values() if len(set(v)) == 1)
    out["within_contest_dup_groups"] = len(dup_groups)
    out["within_contest_dup_groups_identical_counts"] = identical
    out["within_contest_dup_groups_distinct_counts"] = len(dup_groups) - identical

    # Same text across DIFFERENT contests: the portability experiment.
    per_text = Counter()
    for contest, norm in zip(df["contest"].astype(str), df["norm"]):
        per_text[norm] += 0  # touch
    text_contests = defaultdict(set)
    for contest, norm in zip(df["contest"].astype(str), df["norm"]):
        text_contests[norm].add(contest)
    multi = {t: cs for t, cs in text_contests.items() if len(cs) > 1}
    out["texts_in_multiple_contests"] = len(multi)
    out["max_contests_for_one_text"] = max((len(c) for c in multi.values()), default=0)

    # per-contest source mix: >1 source for a contest is the re-ingest risk
    src_per_contest = df.groupby("contest", observed=True)["source"].nunique()
    out["contests_with_multiple_sources"] = int((src_per_contest > 1).sum())
    per_contest_n = df.groupby("contest", observed=True).size()
    out["captions_per_contest"] = {
        "min": int(per_contest_n.min()), "median": int(per_contest_n.median()),
        "max": int(per_contest_n.max())}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    df = load(rebuild=a.build)
    print(f"loaded {len(df):,} rows, {df['contest'].nunique()} contests "
          f"(cache: {CACHE.relative_to(HERE)})")
    if a.probe:
        rep = probe(df)
        print(json.dumps(rep, indent=1))
        (HERE / "jestry_out" / "caption_corpus_probe.json").write_text(
            json.dumps(rep, indent=2), encoding="utf-8")
        print("receipt -> jestry_out/caption_corpus_probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
