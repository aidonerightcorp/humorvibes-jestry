#!/usr/bin/env python3
"""Multi-mesh panel study: do independent model-audiences behave like the theory says?

Runs J judges × P personas × K items (real jokes + a nonsense control) through
the persona-conditioned panel and tests four pre-registered questions:

  Q1 VALIDITY   Does the panel score the nonsense control below every real joke?
                (Theory: surprise without a re-route is not comedy.)
  Q2 CONVERGENCE Which dimensions do independent meshes agree on? (Prediction:
                structure/resolution converge; bad_surprise_risk diverges most,
                because it is audience-relative by construction.)
  Q3 PORTABILITY Does persona spread flag the insider joke (AI-PM) and the
                political joke as less portable than the clean one-liners?
  Q4 INSTRUMENT Does panel "surprise" track the MEASURED S from gemma-2-2b
                (notebook v4 teacher-forced surprisal) on the overlapping items?

Usage:
  python3 research_panel_study.py               # judges from env keys (Ollama Cloud etc.)
  python3 research_panel_study.py --dry-run     # list judges and exit
Writes research_out/panel_study_<ts>.jsonl (votes) + .md (summary).
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from statistics import mean, pstdev

from llm_panel import available_judges, run_panel

OUT = Path(__file__).resolve().parent / "research_out"

# (item_id, text, kind, measured_S_from_notebook_v4_or_None)
ITEMS = [
    ("speed_bumps", "I told my therapist about my fear of speed bumps. She said I'm slowly getting over it.",
     "clean one-liner", 3.19),
    ("lion_heart", "My grandfather has the heart of a lion and a lifetime ban from the zoo.",
     "dark-benign one-liner", 3.58),
    ("ai_pm", "I asked the AI project manager when the feature would ship. It scheduled a meeting to align on what 'when' means.",
     "insider tech joke", 4.09),
    ("printer_congress", "Congress found a bipartisan solution: both sides agreed the printer was the real problem.",
     "political bridge joke", None),
    ("nonsense_ctrl", "I told my therapist about my fear of speed bumps. The quarterly report shows strong regional cheese sales.",
     "shuffled nonsense CONTROL", 6.80),
]

PERSONAS = [
    "NYC tech meetup crowd",
    "retired farmers with no software exposure",
    "mixed-politics community-center audience",
]


def rank_corr(xs: list[float], ys: list[float]) -> float:
    """Spearman via rank Pearson (tiny n, no scipy)."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, idx in enumerate(order):
            r[idx] = pos
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-judges", type=int, default=6)
    args = ap.parse_args()

    judges = available_judges()[: args.max_judges]
    print(f"{len(judges)} judges:", ", ".join(j.describe() for j in judges) or "NONE (set keys)")
    if args.dry_run or not judges:
        return 0

    OUT.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    votes_path = OUT / f"panel_study_{ts}.jsonl"
    all_votes: dict[str, list] = {}
    with votes_path.open("w", encoding="utf-8") as fh:
        for item_id, text, kind, _s in ITEMS:
            votes = run_panel(text, PERSONAS, format_label="joke", judges=judges)
            all_votes[item_id] = votes
            for v in votes:
                fh.write(json.dumps({"item": item_id, **asdict(v)}) + "\n")
            ok = [v for v in votes if v.ok]
            overall = [v.scores.get("overall") for v in ok if "overall" in v.scores]
            print(f"{item_id:16s} {len(ok)}/{len(votes)} votes  overall={mean(overall):.2f}±{pstdev(overall):.2f}"
                  if overall else f"{item_id:16s} {len(ok)}/{len(votes)} votes  (no overall)")

    # ---- summarize the four questions ----
    lines = [f"# Panel study {ts}", "",
             f"Judges: {', '.join(j.describe() for j in judges)}",
             f"Personas: {', '.join(PERSONAS)}", ""]

    per_item: dict[str, dict] = {}
    for item_id, text, kind, s_measured in ITEMS:
        ok = [v for v in all_votes[item_id] if v.ok]
        overall = [v.scores["overall"] for v in ok if "overall" in v.scores]
        surprise = [v.scores["surprise"] for v in ok if "surprise" in v.scores]
        badr = [v.scores["bad_surprise_risk"] for v in ok if "bad_surprise_risk" in v.scores]
        by_persona = {}
        for p in PERSONAS:
            pv = [v.scores["overall"] for v in ok if v.persona == p and "overall" in v.scores]
            if pv:
                by_persona[p] = round(mean(pv), 2)
        per_item[item_id] = {
            "kind": kind, "overall": round(mean(overall), 2) if overall else None,
            "overall_sd": round(pstdev(overall), 2) if len(overall) > 1 else 0.0,
            "surprise": round(mean(surprise), 2) if surprise else None,
            "bad_risk_sd": round(pstdev(badr), 2) if len(badr) > 1 else 0.0,
            "persona_spread": round(max(by_persona.values()) - min(by_persona.values()), 2) if by_persona else None,
            "by_persona": by_persona, "S_measured": s_measured,
        }

    lines.append("## Per-item results\n")
    lines.append("| item | kind | overall | ±sd | persona spread | bad-risk sd | measured S |")
    lines.append("|---|---|---|---|---|---|---|")
    for iid, r in per_item.items():
        lines.append(f"| {iid} | {r['kind']} | {r['overall']} | {r['overall_sd']} | "
                     f"{r['persona_spread']} | {r['bad_risk_sd']} | {r['S_measured']} |")

    ctrl = per_item["nonsense_ctrl"]["overall"]
    reals = [r["overall"] for iid, r in per_item.items() if iid != "nonsense_ctrl" and r["overall"] is not None]
    q1 = ctrl is not None and reals and ctrl < min(reals)
    lines += ["", f"**Q1 validity (nonsense scores lowest): {'PASS' if q1 else 'FAIL'}** "
              f"(control {ctrl} vs real min {min(reals) if reals else '?'})"]

    dim_sd = {}
    for dim in ("surprise", "resolution", "bad_surprise_risk", "audience_fit", "overall"):
        vals_sd = []
        for iid in per_item:
            ok = [v for v in all_votes[iid] if v.ok and dim in v.scores]
            if len(ok) > 1:
                vals_sd.append(pstdev([v.scores[dim] for v in ok]))
        if vals_sd:
            dim_sd[dim] = round(mean(vals_sd), 2)
    lines += ["", "**Q2 convergence** (mean per-item vote sd; higher = meshes disagree more): "
              + ", ".join(f"{d}={s}" for d, s in sorted(dim_sd.items(), key=lambda kv: kv[1]))]

    spreads = {iid: r["persona_spread"] for iid, r in per_item.items() if r["persona_spread"] is not None}
    lines += ["", "**Q3 portability** (persona spread; higher = insider material): "
              + ", ".join(f"{i}={s}" for i, s in sorted(spreads.items(), key=lambda kv: -kv[1]))]

    paired = [(r["surprise"], r["S_measured"]) for r in per_item.values()
              if r["surprise"] is not None and r["S_measured"] is not None]
    if len(paired) >= 3:
        rc = rank_corr([a for a, _ in paired], [b for _, b in paired])
        lines += ["", f"**Q4 instrument** rank-corr(panel surprise, measured S) over {len(paired)} items: {rc:.2f} "
                  "(note: measured S includes the nonsense item — the panel should rate its *quality* low "
                  "even while its raw surprisal is the highest, so a HIGH correlation here would actually "
                  "mean judges conflate surprise with quality)"]

    md_path = OUT / f"panel_study_{ts}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote", votes_path.name, "and", md_path.name)
    print("\n".join(lines[-12:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
