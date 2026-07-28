"""Human-frames resolution study: the missing arm of the frame-provenance experiment.

Every prior R (resolution) measurement used frames that were model-written or
project-crafted — and the frame-provenance trust gate exists precisely because
model-written frames can invert the ordering. This study uses the first frames
in the project that are neither: the human-annotated New Yorker layers, where
three crowd workers wrote, for each cartoon and before seeing captions, what
the scene IS (`image_description`) and what is UNCANNY about it
(`image_uncanny_description`). RESULTS.md names this "the missing arm of that
experiment".

Design (pre-registered; the receipt's plan block is frozen before measurement):

- setup    = the human scene description;  punchline = a real contest caption;
  frame    = the human uncanny description (T3's trusted alternate frame).
- Per selected contest: the top-decile and bottom-decile caption by crowd mean
  (votes >= 40, integrity-screened). Measurements on the certified gemma-2
  full-NLL instrument, protocol-identical to ``mesh_signals.compute_signals``:
  base NLL(setup -> caption), framed NLL(setup + "(hint)" -> caption) for the
  TRUE frame and for a DECOY frame (another contest's uncanny description,
  seeded derangement). R = base_mean - framed_mean; R_net = R_true - R_decoy.
- T4 hint-dose arm (first dedicated T4 measurement in the project): on the top
  caption only, the true frame at three doses — full, first half, first three
  words — testing whether a compact hint already carries most of the collapse.

Hypotheses: H1 mean paired R_net > 0 on top captions; H2 R_net(top) >
R_net(bottom) within contest; H3 (exploratory direction) dose response of R
and per-token efficiency E. Leak guard: items where a frame shares > 40% of
the caption's novel content words are excluded, not discounted.

Truth boundary: this measures the certified instrument's surprisal collapse
under trusted human frames. It is not human comprehension, not funniness, and
the top/bottom contrast conditions on the crowd mean by design. Caption and
scene text are research-only: the public receipt stores aggregates and sha256
hashes; row-level text stays in the research-tree checkpoint.

Usage (from the repository root):
    .venv/bin/python human_frames_resolution_study.py \
        --data-root /path/to/build-with-gemma-humor-genome-nyc \
        --out jestry_out/human_frames_resolution_study.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

CALIBRATION_SETUP = "I told my therapist about my fear of speed bumps."
CALIBRATION_PUNCH = "She said I'm slowly getting over it."
CALIBRATION_S = 3.19
CALIBRATION_TOKENS = 10
LEAK_LIMIT = 0.4


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def content_words(text: str) -> set[str]:
    return {w.lower().strip(".,!?\"'()") for w in text.split() if len(w) > 3}


def leak_share(frame: str, setup: str, punch: str) -> float:
    novel = content_words(punch) - content_words(setup)
    if not novel:
        return 1.0
    return len(novel & content_words(frame)) / len(novel)


def norm_text(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").replace("‘", "'")
                    .replace("“", '"').replace("”", '"').split())


def load_frames(data_root: Path) -> tuple[dict[int, dict], dict[int, list[str]]]:
    """Frames keyed by the jmhessel corpus's OWN 1..705 index, plus each
    index's finalist captions (the '?' rows) for bridging to real contest
    numbers — the two ID spaces are different and share no direct key."""
    frames: dict[int, dict] = {}
    finalists: dict[int, list[str]] = {}
    path = data_root / "corpora" / "harvest_nyc_20260726.jsonl"
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            meta = row.get("meta") or {}
            contest = meta.get("contest")
            if not isinstance(contest, int):
                continue
            kind = meta.get("record_kind")
            if kind == "frame":
                scene = (meta.get("image_description") or "").strip()
                uncanny = (meta.get("image_uncanny_description") or "").strip()
                if len(scene) >= 20 and len(uncanny) >= 10:
                    frames[contest] = {"scene": scene, "uncanny": uncanny}
            elif kind is None and "editor_rank" in meta or "oracle" in meta:
                text = (row.get("text") or "").strip()
                if text:
                    finalists.setdefault(contest, []).append(text)
    return frames, finalists


def build_contest_mapping(data_root: Path, finalists: dict[int, list[str]]) -> dict[int, int]:
    """Map jmhessel index -> real New Yorker contest number by locating each
    index's finalist captions verbatim (normalized) in the caption parquet.
    Only captions whose normalized text maps to a UNIQUE real contest vote;
    an index is mapped when its votes are unanimous."""
    import pandas as pd

    df = pd.read_parquet(data_root / "data_cache" / "caption_index.parquet",
                         columns=["contest", "norm"])
    df["real"] = (df["contest"].astype(str).str.replace(".csv", "", regex=False)
                  .astype(int))
    counts = df.groupby("norm")["real"].nunique()
    unique_norms = set(counts[counts == 1].index)
    lookup = (df[df["norm"].isin(unique_norms)]
              .drop_duplicates("norm").set_index("norm")["real"].to_dict())
    mapping: dict[int, int] = {}
    for idx, caps in finalists.items():
        votes = {lookup[norm_text(c)] for c in caps if norm_text(c) in lookup}
        if len(votes) == 1:
            mapping[idx] = votes.pop()
    return mapping


def load_captions(data_root: Path, contests: set[int]) -> dict[int, dict]:
    import pandas as pd

    df = pd.read_parquet(data_root / "data_cache" / "caption_index.parquet",
                         columns=["contest", "text", "votes", "nf", "sf", "f",
                                  "mean_harvest"])
    df["contest"] = (df["contest"].astype(str).str.replace(".csv", "", regex=False)
                     .astype(int))
    for col in ("votes", "nf", "sf", "f"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["votes", "nf", "sf", "f", "text"])
    df = df[df["votes"] == df["nf"] + df["sf"] + df["f"]]
    df["mean_exact"] = (1 * df["nf"] + 2 * df["sf"] + 3 * df["f"]) / df["votes"]
    ok = df["mean_harvest"].isna() | ((df["mean_exact"] - df["mean_harvest"]).abs() <= 0.02)
    df = df[ok & (df["votes"] >= 40)]
    df = df[df["contest"].isin(contests)]
    out: dict[int, dict] = {}
    for contest, grp in df.groupby("contest"):
        if len(grp) < 50:
            continue
        grp = grp.sort_values("mean_exact")
        lo = grp.iloc[int(len(grp) * 0.05)]
        hi = grp.iloc[int(len(grp) * 0.95)]
        top_txt, bot_txt = str(hi["text"]).strip(), str(lo["text"]).strip()
        if not (3 <= len(top_txt) <= 200 and 3 <= len(bot_txt) <= 200):
            continue
        out[int(contest)] = {
            "top": {"text": top_txt, "mean": float(hi["mean_exact"])},
            "bottom": {"text": bot_txt, "mean": float(lo["mean_exact"])},
            "n_captions": int(len(grp)),
        }
    return out


def dose_variants(frame: str) -> dict[str, str]:
    words = frame.split()
    return {
        "full": frame,
        "half": " ".join(words[: max(3, len(words) // 2)]),
        "w3": " ".join(words[:3]),
    }


def boot_ci(vals: list[float], rng: np.random.Generator, iters: int = 10_000):
    arr = np.asarray(vals, dtype=np.float64)
    if arr.size == 0:
        return None
    idx = rng.integers(0, arr.size, size=(iters, arr.size))
    means = arr[idx].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4),
            round(float(np.percentile(means, 97.5)), 4)]


def signflip_p(vals: list[float], rng: np.random.Generator, iters: int = 20_000) -> float:
    arr = np.asarray(vals, dtype=np.float64)
    obs = abs(arr.mean())
    signs = rng.choice([-1.0, 1.0], size=(iters, arr.size))
    perm = np.abs((signs * arr).mean(axis=1))
    return float((1 + (perm >= obs).sum()) / (1 + iters))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", default=".")
    ap.add_argument("--out", default="jestry_out/human_frames_resolution_study.json")
    ap.add_argument("--rows-out", default=None)
    ap.add_argument("--n-contests", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20260728)
    ap.add_argument("--calibration-tolerance", type=float, default=0.02)
    ap.add_argument("--max-errors", type=int, default=6)
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()

    data_root = Path(args.data_root)
    rows_out = Path(args.rows_out) if args.rows_out else (
        data_root / "jestry_out" / "human_frames_resolution_rows.jsonl")
    rows_out.parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    frames, finalists = load_frames(data_root)
    mapping = build_contest_mapping(data_root, finalists)
    frames = {mapping[i]: v for i, v in frames.items() if i in mapping}
    captions = load_captions(data_root, set(frames))
    usable = sorted(set(frames) & set(captions))
    ordered = sorted(usable, key=lambda c: sha(str(c)))
    plan_contests: list[int] = []
    decoy_of: dict[int, int] = {}
    excluded_leak = 0
    for c in ordered:
        if len(plan_contests) >= args.n_contests:
            break
        scene = frames[c]["scene"]
        true_frame = frames[c]["uncanny"]
        top = captions[c]["top"]["text"]
        bot = captions[c]["bottom"]["text"]
        if (leak_share(true_frame, scene, top) > LEAK_LIMIT
                or leak_share(true_frame, scene, bot) > LEAK_LIMIT):
            excluded_leak += 1
            continue
        plan_contests.append(c)
    for i, c in enumerate(plan_contests):
        d = plan_contests[(i + len(plan_contests) // 2) % len(plan_contests)]
        if d == c:
            d = plan_contests[(i + 1) % len(plan_contests)]
        decoy_of[c] = d

    prereg = {
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypotheses": {
            "H1": "mean paired R_net = mean(R_true - R_decoy) > 0 on top-decile captions "
                  "(bootstrap CI + sign-flip permutation p)",
            "H2": "within-contest R_net(top) > R_net(bottom) (paired bootstrap CI)",
            "H3_exploratory": "dose response of R and per-token E across full/half/3-word "
                               "hints (direction reported, no threshold claim)",
        },
        "design": {
            "instrument": "gemma2-full-nll (certified); protocol identical to "
                          "mesh_signals.compute_signals base/framed measurements",
            "setup": "human image_description", "frame": "human image_uncanny_description",
            "decoy": "another selected contest's uncanny description (seeded derangement)",
            "caption_arms": "top and bottom decile by crowd mean (votes >= 40, "
                             "integrity-screened) — a deliberate outcome-conditioned contrast",
            "leak_rule": f"exclude items with frame-caption novel-word overlap > {LEAK_LIMIT}",
            "n_contests_planned": args.n_contests,
            "seed": args.seed,
        },
        "power": {
            "formula": "MDE(95%) ~= 1.96 * SD(paired R_net) / sqrt(n); observed SD is "
                       "filled post-hoc and the criterion CAN fire iff CI excludes 0",
            "n": args.n_contests,
        },
        "family": "H1 and H2 are the confirmatory family (2 tests, reported without "
                   "correction as two pre-registered primary/secondary); H3 is exploratory",
    }
    plan_summary = {
        "frames_annotated": len(finalists) and len(mapping) or 0,
        "index_to_contest_mapped": len(mapping),
        "frames_with_real_contest": len(frames),
        "contests_with_usable_captions": len(usable),
        "excluded_for_leak_at_planning": excluded_leak,
        "planned": len(plan_contests),
        "mapping_note": "jmhessel 1..705 index bridged to real contest numbers via "
                         "unique-normalized finalist captions; unanimous votes only",
    }
    print("PLAN:", json.dumps(plan_summary), flush=True)
    if args.plan_only:
        print(json.dumps(prereg, indent=1)[:600], flush=True)
        return 0

    from gemma2_full_nll import Gemma2FullNLLProvider

    provider = Gemma2FullNLLProvider()

    def measure(setup: str, cont: str, hint: str | None):
        ctx = setup + "\n" if hint is None else setup + "\n(" + hint + ")\n"
        prof = provider.nll_tokens(ctx, " " + cont)
        if not prof.measured or not prof.nlls:
            return None
        return {"mean": round(prof.mean, 4), "tokens": len(prof.nlls)}

    calib = measure(CALIBRATION_SETUP, CALIBRATION_PUNCH, None)
    calib_ok = bool(calib and calib["tokens"] == CALIBRATION_TOKENS
                    and abs(calib["mean"] - CALIBRATION_S) <= args.calibration_tolerance)
    print(f"calibration: {calib} -> {'PASS' if calib_ok else 'FAIL'}", flush=True)
    if not calib_ok:
        provider.close()
        Path(args.out).write_text(json.dumps({
            "receipt_type": "human_frames_resolution_study", "receipt_version": 1,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "aborted_uncalibrated", "calibration": calib,
            "preregistration": prereg}, indent=2) + "\n")
        return 1

    done: dict[str, dict] = {}
    if rows_out.exists():
        with open(rows_out, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                done[r["key"]] = r
    errors = 0
    results: dict[int, dict] = {}
    with open(rows_out, "a", encoding="utf-8") as ck:
        for idx, c in enumerate(plan_contests):
            scene = frames[c]["scene"]
            true_f = frames[c]["uncanny"]
            decoy_f = frames[decoy_of[c]]["uncanny"]
            doses = dose_variants(true_f)
            jobs = {}
            for arm in ("top", "bottom"):
                cap = captions[c][arm]["text"]
                jobs[f"{arm}:base"] = (scene, cap, None)
                jobs[f"{arm}:true"] = (scene, cap, true_f)
                jobs[f"{arm}:decoy"] = (scene, cap, decoy_f)
            jobs["top:half"] = (scene, captions[c]["top"]["text"], doses["half"])
            jobs["top:w3"] = (scene, captions[c]["top"]["text"], doses["w3"])
            row: dict[str, dict] = {}
            failed = False
            for name, (s, p, h) in jobs.items():
                key = sha(f"{c}|{name}|{s}|{p}|{h or ''}")
                if key in done:
                    row[name] = {"mean": done[key]["mean"], "tokens": done[key]["tokens"]}
                    continue
                m = measure(s, p, h)
                if m is None:
                    errors += 1
                    print(f"ERROR contest={c} {name} ({provider.last_error})", flush=True)
                    if errors > args.max_errors:
                        provider.close()
                        print("too many instrument errors — aborting", flush=True)
                        return 1
                    failed = True
                    break
                ck.write(json.dumps({"key": key, "contest": c, "arm": name,
                                     **m}) + "\n")
                ck.flush()
                row[name] = m
            if failed:
                continue
            results[c] = row
            print(f"[{idx + 1:3d}/{len(plan_contests)}] contest={c} "
                  f"Rnet_top={row['top:base']['mean'] - row['top:true']['mean'] - (row['top:base']['mean'] - row['top:decoy']['mean']):+.3f}",
                  flush=True)
    provider.close()

    rng = np.random.default_rng(args.seed)

    def r_of(row: dict, arm: str, which: str) -> float:
        return row[f"{arm}:base"]["mean"] - row[f"{arm}:{which}"]["mean"]

    rnet_top = [r_of(v, "top", "true") - r_of(v, "top", "decoy") for v in results.values()]
    rnet_bot = [r_of(v, "bottom", "true") - r_of(v, "bottom", "decoy") for v in results.values()]
    h2_diff = [t - b for t, b in zip(rnet_top, rnet_bot)]
    dose_r = {d: [] for d in ("full", "half", "w3")}
    dose_e = {d: [] for d in ("full", "half", "w3")}
    for c, v in results.items():
        words = {"full": len(frames[c]["uncanny"].split()),
                 "half": max(3, len(frames[c]["uncanny"].split()) // 2), "w3": 3}
        for dose, arm in (("full", "true"), ("half", "half"), ("w3", "w3")):
            r = r_of(v, "top", arm)
            dose_r[dose].append(r)
            dose_e[dose].append(r / words[dose])

    sd = float(np.std(rnet_top, ddof=1)) if len(rnet_top) > 2 else None
    prereg["power"]["observed_sd_paired_rnet"] = round(sd, 4) if sd else None
    prereg["power"]["observed_mde_95"] = (
        round(1.96 * sd / np.sqrt(len(rnet_top)), 4) if sd else None)

    receipt = {
        "receipt_type": "human_frames_resolution_study",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "instrument": "gemma-2-2b-it-Q4_K_M.gguf (llama.cpp), certified",
        "calibration": {"expected_S": CALIBRATION_S, "measured": calib, "pass": True},
        "preregistration": prereg,
        "plan_summary": plan_summary,
        "n_analyzed": len(results),
        "instrument_errors": errors,
        "results": {
            "H1_rnet_top": {"mean": round(float(np.mean(rnet_top)), 4),
                             "ci95": boot_ci(rnet_top, rng),
                             "signflip_p": round(signflip_p(rnet_top, rng), 5),
                             "n": len(rnet_top)},
            "H2_top_minus_bottom": {"mean": round(float(np.mean(h2_diff)), 4),
                                     "ci95": boot_ci(h2_diff, rng), "n": len(h2_diff)},
            "rnet_bottom_reference": {"mean": round(float(np.mean(rnet_bot)), 4),
                                       "ci95": boot_ci(rnet_bot, rng)},
            "H3_dose_exploratory": {
                dose: {"R_mean": round(float(np.mean(dose_r[dose])), 4),
                        "R_ci95": boot_ci(dose_r[dose], rng),
                        "E_per_token_mean": round(float(np.mean(dose_e[dose])), 4)}
                for dose in ("full", "half", "w3")},
        },
        "item_hashes": sorted(sha(f"{c}") for c in results),
        "truth_boundary": {
            "verified": "surprisal collapse of the certified instrument under trusted "
                        "HUMAN-authored frames, net of seeded decoys, with a pre-registered "
                        "paired design",
            "not_verified": "human comprehension, funniness, or generalization beyond this "
                            "publication's cartoons; the top/bottom contrast conditions on "
                            "the crowd mean by design; scene descriptions are annotators' "
                            "text, not the drawing itself",
        },
        "data_note": "caption and scene text are research-only; aggregates and hashes only "
                     "in this receipt — row-level values stay in the research-tree checkpoint",
    }
    Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
    print("wrote", args.out, "| H1 mean", receipt["results"]["H1_rnet_top"]["mean"],
          "CI", receipt["results"]["H1_rnet_top"]["ci95"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
