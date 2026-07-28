"""Declared-style × surprisal study on the certified gemma-2 full-NLL instrument.

Question: do community-DECLARED humor styles (subreddit self-labels harvested via
arctic-shift: dad_joke, anti_joke, pun, one_liner, science, tech, clean, absurd,
showerthought, general) occupy different surprisal regimes on the pinned
instrument — at zero annotation cost, because the community name is the label?

Design notes:
- Instrument: ``Gemma2FullNLLProvider`` (exact full-vocab teacher forcing on
  gemma-2-2b-it Q4_K_M via llama.cpp). Every run re-verifies the pinned
  calibration case (speed_bumps, S=3.19 over 10 tokens) before measuring and
  aborts if it drifts — an uncalibrated instrument must not produce a receipt.
- S only. No frames are written or measured, so no generator/judge model is
  involved and the frame-provenance gate is not in scope here.
- Items: rows whose harvest already carries a native ``setup``/``punchline``
  split (no canonicalizer — the format-boundary study showed re-splitting is a
  separate intervention). Deterministic screen + sha256-ordered sample.
- Control: the SAME control recipe as the published Wave 2 form study —
  ``wiktionary`` rows with ``record_kind == "proverb"`` (English), split by
  ``mesh_signals.split_setup_punchline``.
- Uncertainty: percentile bootstrap CI per group; a label-permutation test for
  any-group-differences. Mirrors the published "0/10 separate" framing rather
  than ranking bare means.

Truth boundary: S regimes by declared community style are NOT funniness, NOT
style quality, and the subreddit label is confounded with community norms,
moderation, and length culture. Reddit text is research-only: the public
receipt stores aggregates and sha256 item hashes, never verbatim rows. The
row-level checkpoint (with text) stays in the local research tree.

Usage (from the repository root, with the research corpus present locally):
    .venv/bin/python declared_style_study.py \
        --data-root /path/to/build-with-gemma-humor-genome-nyc \
        --out jestry_out/declared_style_study.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ARCTIC_GLOB = "corpora/harvest_arctic_*.jsonl"
CONTROL_GLOB = "corpora/harvest_wiktionary*.jsonl"
CALIBRATION_SETUP = "I told my therapist about my fear of speed bumps."
CALIBRATION_PUNCH = "She said I'm slowly getting over it."
CALIBRATION_S = 3.19
CALIBRATION_TOKENS = 10

URL_RE = re.compile(r"https?://|www\.")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def iter_rows(path: str):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "_meta" in row and "text" not in row:
                continue
            yield row


def screen_pair(setup: str, punch: str) -> bool:
    if not setup or not punch:
        return False
    if not (8 <= len(setup) <= 300 and 2 <= len(punch) <= 200):
        return False
    low_s, low_p = setup.lower(), punch.lower()
    if low_p in low_s or low_s == low_p:
        return False
    if "[removed]" in low_p or "[deleted]" in low_p or "[removed]" in low_s:
        return False
    if URL_RE.search(setup) or URL_RE.search(punch):
        return False
    return True


def collect_style_candidates(data_root: Path, min_candidates: int) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {}
    seen: set[str] = set()
    files = sorted(glob.glob(str(data_root / ARCTIC_GLOB)))
    if not files:
        raise SystemExit(f"no arctic harvest found under {data_root / ARCTIC_GLOB}")
    for path in files:
        for row in iter_rows(path):
            meta = row.get("meta") or {}
            style = meta.get("style")
            setup = (meta.get("setup") or "").strip()
            punch = (meta.get("punchline") or "").strip()
            if not style or meta.get("language") != "en":
                continue
            if not screen_pair(setup, punch):
                continue
            key = sha((setup + "\x1f" + punch).lower())
            if key in seen:
                continue
            seen.add(key)
            buckets.setdefault(style, []).append(
                {"setup": setup, "punchline": punch, "key": key,
                 "subreddit": meta.get("subreddit", "")})
    return {s: v for s, v in buckets.items() if len(v) >= min_candidates}


def collect_control(data_root: Path, per_group: int) -> list[dict]:
    from mesh_signals import split_setup_punchline

    out, seen = [], set()
    for path in sorted(glob.glob(str(data_root / CONTROL_GLOB))):
        for row in iter_rows(path):
            meta = row.get("meta") or {}
            src = str(row.get("source", ""))
            if "wiktionary" not in src or meta.get("record_kind") != "proverb":
                continue
            if meta.get("language") not in ("en", "English"):
                continue
            text = (row.get("text") or "").strip()
            if not text:
                continue
            setup, punch = split_setup_punchline(text)
            if not screen_pair(setup.strip(), punch.strip()):
                continue
            key = sha(text.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append({"setup": setup.strip(), "punchline": punch.strip(), "key": key,
                        "subreddit": "control"})
    out.sort(key=lambda r: r["key"])
    return out[: per_group * 2]


def pick(candidates: list[dict], n: int) -> list[dict]:
    return sorted(candidates, key=lambda r: r["key"])[:n]


def bootstrap_ci(values: list[float], rng: np.random.Generator, iters: int = 10_000):
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return None
    idx = rng.integers(0, arr.size, size=(iters, arr.size))
    means = arr[idx].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4),
            round(float(np.percentile(means, 97.5)), 4)]


def permutation_p(groups: list[list[float]], rng: np.random.Generator,
                  iters: int = 20_000) -> float:
    """Any-difference test: between-group variance of means under label shuffles."""
    sizes = [len(g) for g in groups]
    pooled = np.concatenate([np.asarray(g, dtype=np.float64) for g in groups])

    def stat(vec: np.ndarray) -> float:
        pos, means = 0, []
        for s in sizes:
            means.append(vec[pos: pos + s].mean())
            pos += s
        return float(np.var(means))

    obs = stat(pooled)
    hits = 0
    for _ in range(iters):
        perm = rng.permutation(pooled)
        if stat(perm) >= obs:
            hits += 1
    return (1 + hits) / (1 + iters)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=".", help="tree containing corpora/ (research corpus)")
    ap.add_argument("--out", default="jestry_out/declared_style_study.json")
    ap.add_argument("--rows-out", default=None,
                    help="row-level checkpoint JSONL (contains text; keep in the research tree)")
    ap.add_argument("--per-group", type=int, default=12)
    ap.add_argument("--min-candidates", type=int, default=150)
    ap.add_argument("--seed", type=int, default=20260727)
    ap.add_argument("--calibration-tolerance", type=float, default=0.02)
    ap.add_argument("--max-errors", type=int, default=5)
    ap.add_argument("--calibration-only", action="store_true")
    args = ap.parse_args()

    data_root = Path(args.data_root)
    rows_out = Path(args.rows_out) if args.rows_out else data_root / "jestry_out" / "declared_style_rows_wave1.jsonl"
    rows_out.parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    from gemma2_full_nll import Gemma2FullNLLProvider

    provider = Gemma2FullNLLProvider()

    def measure(setup: str, punch: str):
        prof = provider.nll_tokens(setup + "\n", " " + punch)
        if not prof.measured or not prof.nlls:
            return None
        return {"S": round(prof.mean, 4), "tokens": len(prof.nlls)}

    calib = measure(CALIBRATION_SETUP, CALIBRATION_PUNCH)
    calib_ok = bool(
        calib
        and calib["tokens"] == CALIBRATION_TOKENS
        and abs(calib["S"] - CALIBRATION_S) <= args.calibration_tolerance
    )
    print(f"calibration: {calib} expected S={CALIBRATION_S}±{args.calibration_tolerance} "
          f"tokens={CALIBRATION_TOKENS} -> {'PASS' if calib_ok else 'FAIL'}", flush=True)
    if not calib_ok:
        provider.close()
        receipt = {
            "receipt_type": "declared_style_surprisal_study",
            "receipt_version": 1,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "aborted_uncalibrated",
            "calibration": {"expected_S": CALIBRATION_S, "measured": calib,
                            "tolerance": args.calibration_tolerance, "pass": False},
            "instrument": provider.model,
        }
        Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
        return 1
    if args.calibration_only:
        provider.close()
        return 0

    buckets = collect_style_candidates(data_root, args.min_candidates)
    control = collect_control(data_root, args.per_group)
    if len(control) < args.per_group:
        print(f"WARNING: only {len(control)} control proverbs after screening", flush=True)
    plan = {style: pick(rows, args.per_group) for style, rows in sorted(buckets.items())}
    plan["control_proverb"] = control[: args.per_group]
    total = sum(len(v) for v in plan.values())
    print(f"groups={len(plan) - 1} styles + control; measurements planned={total}", flush=True)

    done: dict[str, dict] = {}
    if rows_out.exists():
        for row in iter_rows(str(rows_out)):
            done[row["key"]] = row
    results: dict[str, list[dict]] = {g: [] for g in plan}
    errors = 0
    with open(rows_out, "a", encoding="utf-8") as ck:
        for group, items in plan.items():
            for it in items:
                if it["key"] in done:
                    prev = done[it["key"]]
                    results[group].append({"key": it["key"], "S": prev["S"],
                                           "tokens": prev["tokens"]})
                    continue
                m = measure(it["setup"], it["punchline"])
                if m is None:
                    errors += 1
                    print(f"ERROR group={group} key={it['key']} "
                          f"({provider.last_error})", flush=True)
                    if errors > args.max_errors:
                        print("too many instrument errors — aborting", flush=True)
                        provider.close()
                        return 1
                    continue
                rec = {"key": it["key"], "group": group, "subreddit": it["subreddit"],
                       "setup": it["setup"], "punchline": it["punchline"], **m}
                ck.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ck.flush()
                results[group].append({"key": it["key"], **m})
                print(f"[{sum(len(v) for v in results.values()):4d}/{total}] "
                      f"{group:16s} S={m['S']:7.3f} tok={m['tokens']:3d}", flush=True)
    provider.close()

    rng = np.random.default_rng(args.seed)
    ctrl_vals = [r["S"] for r in results["control_proverb"]]
    ctrl_ci = bootstrap_ci(ctrl_vals, rng)
    group_stats = {}
    style_groups = {g: v for g, v in results.items() if g != "control_proverb" and v}
    above = below = 0
    for g, rows in sorted(style_groups.items()):
        vals = [r["S"] for r in rows]
        ci = bootstrap_ci(vals, rng)
        strictly_above = bool(ctrl_ci and ci and ci[0] > ctrl_ci[1])
        strictly_below = bool(ctrl_ci and ci and ci[1] < ctrl_ci[0])
        above += strictly_above
        below += strictly_below
        group_stats[g] = {
            "n": len(vals),
            "mean_S": round(float(np.mean(vals)), 4),
            "median_S": round(float(np.median(vals)), 4),
            "ci95": ci,
            "mean_tokens": round(float(np.mean([r["tokens"] for r in rows])), 1),
            "separates_above_control": strictly_above,
            "separates_below_control": strictly_below,
            "item_hashes": sorted(r["key"] for r in rows),
        }
    perm_p = permutation_p([[r["S"] for r in v] for v in style_groups.values()], rng)

    receipt = {
        "receipt_type": "declared_style_surprisal_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "instrument": provider.model,
        "calibration": {"expected_S": CALIBRATION_S, "expected_tokens": CALIBRATION_TOKENS,
                        "measured": calib, "tolerance": args.calibration_tolerance,
                        "pass": True},
        "design": {
            "styles_source": "arctic-shift subreddit self-labels (community-declared)",
            "control": "wiktionary record_kind=proverb (en), split_setup_punchline — "
                       "same recipe as the published Wave 2 form study",
            "per_group": args.per_group,
            "seed": args.seed,
            "selection": "screened candidates ordered by sha256(text), first N per group",
            "signal": "S = mean full-vocab NLL per punchline token, base measurement only "
                      "(no frames, no generator model)",
        },
        "screening": {g: len(v) for g, v in sorted(buckets.items())},
        "groups": group_stats,
        "control_proverb": {
            "n": len(ctrl_vals),
            "mean_S": round(float(np.mean(ctrl_vals)), 4) if ctrl_vals else None,
            "ci95": ctrl_ci,
            "item_hashes": sorted(r["key"] for r in results["control_proverb"]),
        },
        "findings": {
            "groups_strictly_above_control": above,
            "groups_strictly_below_control": below,
            "any_difference_permutation_p": round(perm_p, 5),
            "permutation_iters": 20_000,
        },
        "instrument_errors": errors,
        "truth_boundary": {
            "verified": "surprisal regimes of community-declared style groups on the "
                        "certified instrument, with uncertainty",
            "not_verified": "human funniness, style quality, or a causal style effect — "
                            "the subreddit label is confounded with community norms, "
                            "moderation, and length culture",
        },
        "data_note": "Reddit rows are research-only; this receipt stores aggregates and "
                     "sha256 item hashes only. Row-level text stays in the local research "
                     "tree checkpoint.",
    }
    Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {args.out}: {len(style_groups)} style groups, "
          f"above={above} below={below} perm_p={perm_p:.5f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
