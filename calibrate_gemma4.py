"""Calibrate the gemma4-forced-NLL laugh region against reference material.

The S band (1.2–5.5 nats) and R floor (0.5) hard-coded in mesh_signals were
calibrated on gemma-2-2b full teacher forcing. The gemma4 top-K-censored
instrument reads systematically differently (censoring undercounts both S and
R), so acceptance thresholds must be re-derived FROM REFERENCE MEASUREMENTS —
canonical jokes with ground-truth frames must land inside the region, boring
and shuffled controls must land outside. That is instrument calibration with a
receipt, not tuning-until-my-joke-passes; mesh_signals itself stays untouched
(evolution is additive).

    python3 calibrate_gemma4.py          # writes jestry_out/gemma4_calibration.json

Jestry loads the receipt when (and only when) the same instrument name is
active, and records the acceptance basis on every receipt.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from gemma4_nll import Gemma4ForcedNLLProvider, available
from mesh_signals import compute_signals

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "jestry_out" / "gemma4_calibration.json"

# The project's three fixed canonical jokes with their ground-truth frames
# (panel-lab material), plus matched controls.
REFERENCE_JOKES = [
    ("speed_bumps",
     "I told my therapist about my fear of speed bumps.",
     "She said I'm slowly getting over it.",
     "'Getting over it' is literal — the car physically drives over the speed bumps slowly."),
    ("lion_heart",
     "My grandfather has the heart of a lion",
     "and a lifetime ban from the zoo.",
     "He literally stole a lion's heart from the zoo, not the metaphor for bravery."),
    ("ai_pm",
     "The AI project manager finally found the bottleneck:",
     "the calendar wanted attention.",
     "The scheduling tool is a needy coworker whose feelings block the project."),
]
CONTROLS = [
    ("boring",
     "I told my therapist about my fear of speed bumps.",
     "She said we can talk about it next week.",
     ""),
    ("nonsense",
     "I told my therapist about my fear of speed bumps.",
     "The quarterly cheese fondue regatta sailed backwards.",
     ""),
]


def calibrate(provider=None, out_path: Path | None = None) -> dict:
    global OUT
    if provider is None:
        assert available(), "ollama/gemma4 not answering — calibration needs the live instrument"
        provider = Gemma4ForcedNLLProvider()
    if out_path is not None:
        OUT = out_path
    p = provider
    rows = []
    for name, setup, punch, frame in REFERENCE_JOKES + CONTROLS:
        sig = compute_signals(p, setup, punch, frame_hint=frame or None)
        rows.append({"name": name, "kind": "joke" if frame else "control",
                     "S": sig.surprise_mean, "R": sig.resolution, "E": sig.efficiency,
                     "censored": getattr(sig.profile, "censored", 0),
                     "tokens": len(sig.profile.nlls) if sig.profile else 0,
                     "measured": sig.measured})
        print(f"{name:12s} S={sig.surprise_mean:5.2f} R={sig.resolution:5.2f} "
              f"E={sig.efficiency:6.3f} censored={getattr(sig.profile, 'censored', '?')}")
    jokes = [r for r in rows if r["kind"] == "joke"]
    controls = [r for r in rows if r["kind"] == "control"]
    assert all(r["measured"] for r in rows), "calibration requires measured signals"

    joke_r = [r["R"] for r in jokes]
    ctrl_r = [r["R"] for r in controls]
    joke_s = [r["S"] for r in jokes]
    receipt = {
        "receipt_type": "instrument_calibration",
        "receipt_version": 2,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "instrument": p.name,
        "model": str(p.model),
        "reference": rows,
        "nll_calls": getattr(p, "calls", None),
        "instrument_errors": getattr(p, "errors", None),
    }
    separated = min(joke_r) > max(ctrl_r)
    if separated:
        r_floor = round((min(joke_r) + max(ctrl_r)) / 2, 3)
        nonsense_s = next(r["S"] for r in controls if r["name"] == "nonsense")
        s_low = round(min(joke_s) * 0.6, 2)
        s_high = round(min(max(joke_s) * 1.3, nonsense_s * 0.98), 2)
        e_floor = round(min(r["E"] for r in jokes) * 0.5, 4)
        derived = {"s_band": [s_low, s_high], "r_floor": r_floor, "e_floor": e_floor}

        def in_region(r: dict) -> bool:
            # the SAME residual-surprise rule jestry applies at acceptance:
            # a strong frame absorbs excess error (corpus-lab doctrine)
            s_eff = r["S"]
            if s_eff > s_high:
                s_eff = max(s_low, s_eff - r["R"])
            return s_low <= s_eff <= s_high and r["R"] >= r_floor and r["E"] >= e_floor

        checks = {
            "all_jokes_pass": all(in_region(r) for r in jokes),
            "all_controls_fail": all(not in_region(r) for r in controls),
        }
        certified = checks["all_jokes_pass"] and checks["all_controls_fail"]
        # adversarial scope probe (2026-07-24 finding): a hand-crafted frame
        # can lift a boring line's R into the region. Measure it, record it,
        # and scope the certification: acceptance frames must come from
        # trusted provenance (enforced by jestry.trusted_frame_source).
        adv_sig = compute_signals(
            p, "I told my therapist about my fear of speed bumps.",
            "She said we can talk about it next week.",
            frame_hint="The therapist is postponing the discussion to a later appointment.")
        adv = {"probe": "boring + crafted frame",
               "S": adv_sig.surprise_mean, "R": adv_sig.resolution,
               "E": adv_sig.efficiency,
               "in_region_if_frame_trusted": in_region(
                   {"S": adv_sig.surprise_mean, "R": adv_sig.resolution,
                    "E": adv_sig.efficiency}),
               "mitigation": "frame provenance hard gate — untrusted frame_hints "
                             "never reach the oracle (jestry.trusted_frame_source)"}
        receipt |= {"derived": derived if certified else None, "checks": checks,
                    "certified": certified,
                    "adversarial_scope": adv,
                    "rule": ("accept when s_band[0] <= S <= s_band[1] (or S - R inside "
                             "band) and R >= r_floor and E >= e_floor; SCOPE: frame "
                             "hints only from trusted provenance (see adversarial_scope)")}
    else:
        # Honest negative: under top-20 censoring this instrument does not
        # separate the reference jokes from controls on R. The receipt is the
        # evidence; instrument-scored acceptance stays gated on a certified
        # instrument (e.g. full-logprob teacher forcing in the Kaggle kernel).
        receipt |= {"derived": None, "certified": False,
                    "failure": {"joke_R": joke_r, "control_R": ctrl_r,
                                "reason": "reference jokes do not separate from "
                                          "controls on R under top-K censoring"}}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"\ncertified={receipt['certified']}  receipt -> {OUT}")
    if receipt.get("derived"):
        print(json.dumps(receipt["derived"], indent=2))
    return receipt


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", choices=["forced", "full", "kaggle"], default="forced",
                    help="forced = gemma4 top-K stepwise; full = gemma-2-2b llama.cpp "
                         "full-vocab; kaggle = transformers checkpoint (in-kernel)")
    args = ap.parse_args()
    if args.instrument == "full":
        from gemma2_full_nll import Gemma2FullNLLProvider
        prov = Gemma2FullNLLProvider()
        try:
            calibrate(provider=prov,
                      out_path=ROOT / "jestry_out" / "gemma2_full_nll_calibration.json")
        finally:
            prov.close()
    elif args.instrument == "kaggle":
        from mesh_signals import TransformersProvider
        calibrate(provider=TransformersProvider(),
                  out_path=ROOT / "jestry_out" / "transformers_calibration.json")
    else:
        calibrate()
