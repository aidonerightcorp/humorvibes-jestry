#!/usr/bin/env python3
"""Harvest one-line frames from every hosted panel judge for each study joke.

THEORY.md §7 follow-up ("hosted frame-writers × local instrument"): frames are
fetched here over the network and BAKED into research_out/frames_latest.json so
the measurement notebook can stay internet-free and score each writer's frame
with local Gemma logits (R net of the decoy null). Provenance travels with the
data.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from llm_panel import available_judges, _dispatch
from research_panel_study import ITEMS

OUT = Path(__file__).resolve().parent / "research_out"

FRAME_PROMPT = (
    "A joke works because a hidden frame reinterprets the punchline — the fact that, once stated, "
    "makes the punchline the OBVIOUS next thing to say.\n"
    "Example — Setup: I told my therapist about my fear of speed bumps. "
    "Punchline: She said I'm slowly getting over it. "
    "Frame: 'Getting over it' is literal — the car physically drives over the bumps slowly.\n\n"
    "Joke: {joke}\n"
    "Frame (ONE short sentence, no preamble, no quotes; if there is genuinely no such fact, write NONE):"
)


def main() -> int:
    judges = available_judges()[:6]
    if not judges:
        print("no judges (set keys)")
        return 1
    OUT.mkdir(exist_ok=True)
    result = {
        "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "judges": [j.describe() for j in judges],
        "items": {},
    }
    for item_id, text, kind, s_measured in ITEMS:
        frames = {}
        for judge in judges:
            raw = _dispatch(judge, FRAME_PROMPT.format(joke=text)) or ""
            frame = raw.strip().splitlines()[0].strip().strip('"') if raw.strip() else ""
            frames[judge.judge_id] = frame
            print(f"{item_id:16s} {judge.judge_id:24s} {frame[:70]}")
        result["items"][item_id] = {"text": text, "kind": kind, "S_measured": s_measured, "frames": frames}
    path = OUT / "frames_latest.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
