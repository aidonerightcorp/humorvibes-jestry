"""Instrument challenger sweep: layouts × hint phrasings × nulls × models.

The charter's challenger doctrine applied to the forced-NLL instrument itself:
run every requested configuration against the frozen reference set (3 canonical
jokes with ground-truth frames + boring + nonsense controls), retain every
outcome, and certify a configuration only if a JOINT (S band, R floor) region
exists that admits all jokes and excludes all controls. Certification feasibility
is searched, not hand-picked; every config row lands in
jestry_out/instrument_sweep.jsonl and a certifiable winner is written to
jestry_out/gemma4_calibration.json (certified: true, config recorded) so Jestry
adopts it through the existing, receipted path.

    python3 instrument_sweep.py                     # stage 1: gemma4 grid
    python3 instrument_sweep.py --models gemma4,gemma4:e2b --top 2

Statistics per (item, config):
- S    = mean forced NLL of the punchline given the setup (bounded low by
         censoring; recorded with censored counts);
- R    = mean(base) - mean(framed replay), net of the same-construction decoy
         null, floored at 0 (no leak guard here: frames are trusted GT);
- R_uc = the same delta over steps uncensored in BOTH passes (alternative
         statistic; recorded for evidence, certification may use either).
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path
from typing import Any

from gemma4_nll import Gemma4ForcedNLLProvider, available

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "jestry_out"

REFERENCE = [
    ("speed_bumps", "joke",
     "I told my therapist about my fear of speed bumps.",
     " She said I'm slowly getting over it.",
     "'Getting over it' is literal — the car physically drives over the speed bumps slowly."),
    ("lion_heart", "joke",
     "My grandfather has the heart of a lion",
     " and a lifetime ban from the zoo.",
     "He literally stole a lion's heart from the zoo, not the metaphor for bravery."),
    ("ai_pm", "joke",
     "The AI project manager finally found the bottleneck:",
     " the calendar wanted attention.",
     "The scheduling tool is a needy coworker whose feelings block the project."),
    ("boring", "control",
     "I told my therapist about my fear of speed bumps.",
     " She said we can talk about it next week.",
     "The therapist is scheduling a routine follow-up appointment."),
    ("nonsense", "control",
     "I told my therapist about my fear of speed bumps.",
     " The quarterly cheese fondue regatta sailed backwards.",
     "The therapist's office is hosting its annual cheese-themed boating event."),
]

DECOY = "It turns out this is really about quarterly regional cheese sales figures."

WRAPS = {
    "paren": lambda h: f"({h})",
    "hint": lambda h: f"Hint: {h}",
    "because": lambda h: f"The joke works because {h}",
}
LAYOUTS = ("prefix", "suffix")
NULLS = {"cheese": DECOY,
         "generic": "This statement should be considered in its ordinary everyday context."}


def framed_ctx(setup: str, hint: str, layout: str, wrap: str) -> str:
    wrapped = WRAPS[wrap](hint)
    if layout == "prefix":
        return wrapped + "\n" + setup + "\n"
    return setup + "\n" + wrapped + "\n"


def pair_stats(base, other) -> dict[str, float]:
    """Aligned per-step deltas between two ForcedProfiles."""
    n = min(len(base.steps), len(other.steps))
    deltas = [base.steps[i].nll - other.steps[i].nll for i in range(n)]
    uc = [d for i, d in enumerate(deltas)
          if not base.steps[i].censored and not other.steps[i].censored]
    return {"mean_delta": sum(deltas) / n if n else 0.0,
            "uc_delta": sum(uc) / len(uc) if uc else 0.0,
            "uc_steps": len(uc), "steps": n}


def feasible_region(jokes: list[dict], controls: list[dict], stat: str
                    ) -> dict[str, float] | None:
    """Search for (s_hi, r_floor) admitting all jokes, excluding all controls.
    s_low is fixed permissively (0.5) because censoring makes S a lower bound."""
    s_low = 0.5
    r_values = sorted({round(x[stat], 3) for x in jokes + controls})
    s_values = sorted({round(x["S"], 2) for x in jokes + controls})
    for r_floor in [v - 0.001 for v in r_values] + [0.05, 0.1, 0.2]:
        for s_hi in [v + 0.01 for v in s_values] + [12.0]:
            ok_j = all(s_low <= j["S"] <= s_hi and j[stat] >= r_floor for j in jokes)
            ok_c = all(not (s_low <= c["S"] <= s_hi and c[stat] >= r_floor)
                       for c in controls)
            if ok_j and ok_c and r_floor > 0:
                margin = min(j[stat] for j in jokes) - max(
                    (c[stat] for c in controls
                     if s_low <= c["S"] <= s_hi), default=0.0)
                return {"s_band": [s_low, round(s_hi, 2)],
                        "r_floor": round(max(r_floor, 0.02), 3),
                        "stat": stat, "margin": round(margin, 3)}
    return None


def run_config(provider: Gemma4ForcedNLLProvider, layout: str, wrap: str,
               null_key: str) -> dict[str, Any]:
    rows = []
    for name, kind, setup, punch, hint in REFERENCE:
        base = provider.nll_tokens(setup + "\n", punch)
        if not base.measured:
            return {"error": f"base pass unmeasured for {name}"}
        base_prof = provider._base_profiles[punch]
        f_prof = provider._replay(framed_ctx(setup, hint, layout, wrap),
                                  provider._path_cache[punch], base_prof)
        n_prof = provider._replay(framed_ctx(setup, NULLS[null_key], layout, wrap),
                                  provider._path_cache[punch], base_prof)
        if f_prof is None or n_prof is None:
            return {"error": f"replay failed for {name}"}
        fs, ns = pair_stats(base_prof, f_prof), pair_stats(base_prof, n_prof)
        rows.append({
            "name": name, "kind": kind,
            "S": round(base.mean, 3), "censored": base_prof.censored,
            "R": round(max(0.0, fs["mean_delta"] - max(0.0, ns["mean_delta"])), 3),
            "R_uc": round(max(0.0, fs["uc_delta"] - max(0.0, ns["uc_delta"])), 3),
            "uc_steps": fs["uc_steps"],
        })
    jokes = [r for r in rows if r["kind"] == "joke"]
    controls = [r for r in rows if r["kind"] == "control"]
    result: dict[str, Any] = {"rows": rows}
    for stat in ("R", "R_uc"):
        region = feasible_region(jokes, controls, stat)
        result[f"region_{stat}"] = region
        result[f"certifiable_{stat}"] = region is not None
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gemma4")
    ap.add_argument("--layouts", default=",".join(LAYOUTS))
    ap.add_argument("--wraps", default=",".join(WRAPS))
    ap.add_argument("--nulls", default="cheese")
    ap.add_argument("--adopt", action="store_true",
                    help="write the best certifiable config as the live calibration")
    args = ap.parse_args()

    assert available(), "ollama not answering"
    OUT.mkdir(exist_ok=True)
    sweep_path = OUT / "instrument_sweep.jsonl"
    best: dict[str, Any] | None = None
    grid = list(itertools.product(
        args.models.split(","), args.layouts.split(","),
        args.wraps.split(","), args.nulls.split(",")))
    print(f"{len(grid)} configs × {len(REFERENCE)} reference items")
    for model, layout, wrap, null_key in grid:
        provider = Gemma4ForcedNLLProvider(model=model, auto_prefix_rewrite=False)
        t0 = time.time()
        res = run_config(provider, layout, wrap, null_key)
        rec = {"receipt_type": "instrument_sweep", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "config": {"model": model, "layout": layout, "wrap": wrap, "null": null_key},
               "wall_s": round(time.time() - t0, 1),
               "api_calls": provider.calls, "errors": provider.errors} | res
        with sweep_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        if "error" in res:
            print(f"{model:12s} {layout:6s} {wrap:8s} {null_key:8s} ERROR {res['error']}")
            continue
        cert = res["certifiable_R"] or res["certifiable_R_uc"]
        jokes_r = [r["R"] for r in res["rows"] if r["kind"] == "joke"]
        ctrl_r = [r["R"] for r in res["rows"] if r["kind"] == "control"]
        print(f"{model:12s} {layout:6s} {wrap:8s} {null_key:8s} "
              f"jokes R={jokes_r} ctrl R={ctrl_r} certifiable={cert}")
        for stat in ("R", "R_uc"):
            region = res.get(f"region_{stat}")
            if region and (best is None or region["margin"] > best["region"]["margin"]):
                best = {"config": rec["config"], "region": region, "rows": res["rows"]}
    if best:
        print("\nBEST certifiable config:", json.dumps(best["config"]),
              "region:", json.dumps(best["region"]))
        if args.adopt:
            receipt = {
                "receipt_type": "gemma4_instrument_calibration", "receipt_version": 2,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "instrument": "gemma4-forced-nll",
                "model": best["config"]["model"],
                "config": best["config"],
                "reference": best["rows"],
                "derived": {"s_band": best["region"]["s_band"],
                            "r_floor": best["region"]["r_floor"],
                            "e_floor": 0.0,
                            "stat": best["region"]["stat"]},
                "certified": True,
                "rule": "joint region searched by instrument_sweep.py; margin "
                        f"{best['region']['margin']}",
            }
            (OUT / "gemma4_calibration.json").write_text(
                json.dumps(receipt, indent=2), encoding="utf-8")
            print("ADOPTED -> jestry_out/gemma4_calibration.json (certified: true)")
    else:
        print("\nNo configuration certified — negative receipts retained in "
              "jestry_out/instrument_sweep.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
