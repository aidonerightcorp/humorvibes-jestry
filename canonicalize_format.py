#!/usr/bin/env python3
"""Format-boundary experiment: does edit-anchored canonicalization fix headlines?

The v4 ablation court (rho=0.033) and the Humicroedit validation (spearman
0.115, n=180) both measured EDITED HEADLINES through the generic
``split_setup_punchline``, which — headlines rarely containing sentence
separators — falls through to a blind 70% word cut. The format-boundary
hypothesis says the instrument only reads jokes whose prediction-error site
sits at the setup/punchline seam. Humicroedit tells us the true seam: the
edited word. This experiment re-measures the SAME 180-item sample (same zip,
same ``sample(180, random_state=0)``) with the certified local instrument
under three split conditions:

- ``generic``   — split_setup_punchline(edited), replicating the pinned run's
                  splitting (frame source differs; see below);
- ``canonical`` — setup = headline text before the edited word, punchline =
                  edited word through end-of-headline (the seam at the edit);
- ``control``   — a fixed 40% word-boundary cut, so "canonical wins" cannot be
                  explained by "any different split wins".

All three conditions share ONE deterministic, leak-safe frame hint built from
the ORIGINAL word (which never appears in the edited text, so the lexical-leak
guard cannot fire on it). The pinned run let the instrument generate frames;
holding the frame fixed across conditions isolates the split variable, which
is the comparison this experiment is about. The pinned numbers are reported
alongside as context, not as a fourth arm.

Receipts: jestry_out/format_boundary_experiment.json (headline numbers) and
jestry_out/format_boundary_items.jsonl (every measurement, auditable).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from gemma2_full_nll import Gemma2FullNLLProvider
from mesh_signals import compute_signals, split_setup_punchline

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
ZIP_PATH = Path(
    "/tmp/claude-1000/-home-username-new-algo-comps-build-with-gemma-humor-genome-nyc/"
    "1870a159-9394-4d23-9ffb-cb82162bcf3f/scratchpad/humicroedit.zip"
)
ZIP_URL = "https://cs.rochester.edu/u/nhossain/humicroedit/semeval-2020-task-7-data.zip"
MARKER = re.compile(r"<([^/>]*)/>")

# Names the swapped-OUT word only: it is absent from the edited headline, so
# it can never trip the novel-punch-word leak guard the way naming the edit
# word would (a 1-2 word punchline would hit leak=1.0 and zero out R).
HINT_TEMPLATE = "The serious headline expected the word '{orig}' at that spot."


def apply_edit(original: str, edit: str) -> str:
    return MARKER.sub(str(edit), str(original))


def canonical_split(original: str, edit: str) -> tuple[str, str, str] | None:
    """setup = pre-edit context, punchline = edit word .. end. None if degenerate."""
    m = MARKER.search(str(original))
    if not m:
        return None
    setup = original[: m.start()].strip()
    punchline = (str(edit) + original[m.end() :]).strip()
    if not setup.split() or not punchline.split():
        return None
    return setup, punchline, m.group(1)


def control_split(edited: str) -> tuple[str, str]:
    words = edited.split()
    cut = max(1, int(len(words) * 0.4))
    return " ".join(words[:cut]), " ".join(words[cut:])


def corr(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Pearson + tie-naive spearman, byte-matching the pinned notebook's corr()."""

    def rank(v: np.ndarray) -> np.ndarray:
        return np.argsort(np.argsort(v))

    pear = np.corrcoef(a, b)[0, 1]
    spear = np.corrcoef(rank(a), rank(b))[0, 1]
    return round(float(pear), 3), round(float(spear), 3)


def perm_p(a: np.ndarray, b: np.ndarray, n_perm: int = 2000) -> float:
    """Permutation p for |spearman| under label shuffle; seeded, receipt-stable."""

    def spear(x: np.ndarray, y: np.ndarray) -> float:
        rx = np.argsort(np.argsort(x)).astype(float)
        ry = np.argsort(np.argsort(y)).astype(float)
        return float(np.corrcoef(rx, ry)[0, 1])

    obs = abs(spear(a, b))
    rng = np.random.default_rng(0)
    hits = 0
    for _ in range(n_perm):
        if abs(spear(a, rng.permutation(b))) >= obs:
            hits += 1
    return round((hits + 1) / (n_perm + 1), 4)


def load_sample() -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(ZIP_PATH.read_bytes()))
    names = [n for n in z.namelist() if n.endswith("train.csv") and ("task-1" in n or "subtask-1" in n)]
    if not names:
        names = [n for n in z.namelist() if n.endswith("train.csv")]
    df = pd.read_csv(z.open(names[0]))
    df = df.dropna(subset=["meanGrade"]).sample(min(180, len(df)), random_state=0)
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "id": int(r["id"]),
                "original": str(r["original"]),
                "edit": str(r["edit"]),
                "grade": float(r["meanGrade"]),
            }
        )
    return rows


def main() -> None:
    t0 = time.time()
    rows = load_sample()
    # 2026-07-24: GPU driver is down (NVML mismatch) and the CPU instrument
    # runs ~35s per measurement, so the full 180x3 design costs ~5h. The
    # pinned sample order is already randomized (random_state=0), so the
    # first N rows are an unbiased subsample; N is receipted.
    n_items = int(os.environ.get("FORMAT_BOUNDARY_N", "84"))
    rows = rows[:n_items]
    provider = Gemma2FullNLLProvider()

    items_path = OUT / "format_boundary_items.jsonl"
    conditions = ("generic", "canonical", "control")
    kept: list[dict] = []
    skipped = 0
    for row in rows:
        can = canonical_split(row["original"], row["edit"])
        if can is None:
            skipped += 1
            continue
        setup_c, punch_c, orig_word = can
        edited = apply_edit(row["original"], row["edit"])
        hint = HINT_TEMPLATE.format(orig=orig_word)
        row["hint"] = hint
        row["splits"] = {
            "generic": split_setup_punchline(edited),
            "canonical": (setup_c, punch_c),
            "control": control_split(edited),
        }
        kept.append(row)

    print(f"items: {len(kept)} kept, {skipped} skipped (degenerate edit position)")
    sink = items_path.open("w", encoding="utf-8")
    series: dict[str, dict[str, list[float]]] = {
        c: {"S": [], "R": [], "E": [], "laugh": [], "grade": []} for c in conditions
    }
    for i, row in enumerate(kept):
        for cond in conditions:
            setup, punch = row["splits"][cond]
            sig = compute_signals(provider, setup, punch, frame_hint=row["hint"])
            if not sig.measured:
                continue
            series[cond]["S"].append(sig.surprise_mean)
            series[cond]["R"].append(sig.resolution)
            series[cond]["E"].append(sig.efficiency)
            series[cond]["laugh"].append(sig.laugh_score)
            series[cond]["grade"].append(row["grade"])
            sink.write(
                json.dumps(
                    {
                        "id": row["id"],
                        "condition": cond,
                        "setup": setup,
                        "punchline": punch,
                        "S": sig.surprise_mean,
                        "R": sig.resolution,
                        "E": sig.efficiency,
                        "laugh_score": sig.laugh_score,
                        "grade": row["grade"],
                    }
                )
                + "\n"
            )
        if (i + 1) % 20 == 0:
            sink.flush()
            print(f"{i + 1}/{len(kept)} ({time.time() - t0:.0f}s, worker errors={provider.errors})", flush=True)
    sink.close()
    provider.close()

    report: dict = {
        "receipt_type": "format_boundary_experiment",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "instrument": provider.name,
        "gguf": "gemma-2-2b-it-Q4_K_M.gguf (bartowski, public)",
        "data": {
            "source": ZIP_URL,
            "zip_sha256": hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest(),
            "sample": (
                "dropna(meanGrade).sample(180, random_state=0) — pinned recipe; "
                f"first {n_items} rows of that sample order (CPU budget, GPU driver down)"
            ),
            "kept": len(kept),
            "skipped_degenerate": skipped,
        },
        "frame_hint_template": HINT_TEMPLATE,
        "design_note": (
            "Frame hint is deterministic and shared across conditions (pinned run used "
            "model-generated frames), so pinned rho=0.115 is context, not a controlled arm; "
            "the controlled comparison is generic vs canonical vs control within this run."
        ),
        "pinned_reference": json.loads(
            (HERE / "research_out/kaggle/humorvibes-validate-ratings/validation_results.json").read_text()
        ),
        "conditions": {},
        "runtime_s": None,
        "worker": {"calls": provider.calls, "errors": provider.errors, "restarts": provider.restarts},
    }
    for cond in conditions:
        g = np.array(series[cond]["grade"])
        block: dict = {"n": int(len(g))}
        for name in ("laugh", "S", "R", "E"):
            arr = np.array(series[cond][name])
            p, s = corr(arr, g)
            block[name] = {
                "pearson": p,
                "spearman": s,
                "perm_p_spearman": perm_p(arr, g),
                "mean": round(float(arr.mean()), 3),
            }
        block["R_positive_frac"] = round(float((np.array(series[cond]["R"]) > 0).mean()), 3)
        report["conditions"][cond] = block
    report["runtime_s"] = round(time.time() - t0, 1)

    (OUT / "format_boundary_experiment.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({c: report["conditions"][c] for c in conditions}, indent=2))
    print("receipt ->", OUT / "format_boundary_experiment.json")


if __name__ == "__main__":
    main()
