#!/usr/bin/env python3
"""Quantization robustness probe for the certified gemma2-full-nll instrument.

The live calibration (jestry_out/gemma2_full_nll_calibration.json) was earned
on the Q4_K_M GGUF. This probe asks one question: do the SAME reference cases,
measured on a higher-precision quant (Q8_0), still land where the certified
acceptance region says jokes and controls belong? It does not touch the live
calibration; it writes its own receipt.

Protocol replication note: the certified run's controls carry empty frame
hints (nll_calls=11 in the receipt: 3 jokes x 3 evals + 2 controls x 1 eval),
so generation is suppressed here rather than letting today's Ollama state
inject nondeterministic confabulated frames. Jokes use their fixed GT frames.
Both quants are re-measured tonight through this one code path; the Q4 pass
doubles as a drift check against the certified receipt.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from calibrate_gemma4 import CONTROLS, REFERENCE_JOKES

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
QUANTS = {
    "Q4_K_M": str(Path.home() / ".cache" / "gemma-2-2b-it-Q4_K_M.gguf"),
    "Q8_0": str(Path.home() / ".cache" / "gemma-2-2b-it-Q8_0.gguf"),
}


def measure_quant(gguf: str) -> list[dict]:
    os.environ["GEMMA2_GGUF"] = gguf
    # import late so GEMMA2_GGUF is read per process run; the module resolves
    # the path at import time
    import importlib

    import gemma2_full_nll
    importlib.reload(gemma2_full_nll)
    from mesh_signals import compute_signals

    class NoGenProvider(gemma2_full_nll.Gemma2FullNLLProvider):
        def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
            return ""

    p = NoGenProvider()
    rows = []
    for name, setup, punch, frame in REFERENCE_JOKES + CONTROLS:
        sig = compute_signals(p, setup, punch, frame_hint=frame or None)
        rows.append(
            {
                "name": name,
                "kind": "joke" if any(name == j[0] for j in REFERENCE_JOKES) else "control",
                "S": sig.surprise_mean,
                "R": sig.resolution,
                "E": sig.efficiency,
                "measured": sig.measured,
            }
        )
    errors = p.errors
    p.close()
    assert errors == 0, f"instrument errors on {gguf}: {errors}"
    return rows


def main() -> None:
    t0 = time.time()
    cal = json.loads((OUT / "gemma2_full_nll_calibration.json").read_text())
    lo, hi = cal["derived"]["s_band"]
    r_floor = cal["derived"]["r_floor"]
    e_floor = cal["derived"]["e_floor"]

    def in_region(row: dict) -> bool:
        s_ok = lo <= row["S"] <= hi or lo <= row["S"] - row["R"] <= hi
        return s_ok and row["R"] >= r_floor and row["E"] >= e_floor

    results = {}
    for quant, path in QUANTS.items():
        if not Path(path).exists():
            results[quant] = {"error": f"gguf missing: {path}"}
            continue
        rows = measure_quant(path)
        results[quant] = {
            "gguf": Path(path).name,
            "rows": rows,
            "jokes_in_region": [r["name"] for r in rows if r["kind"] == "joke" and in_region(r)],
            "controls_in_region": [r["name"] for r in rows if r["kind"] == "control" and in_region(r)],
        }

    q4, q8 = results.get("Q4_K_M", {}), results.get("Q8_0", {})
    verdict = None
    drift_vs_certified = None
    if "rows" in q4 and "rows" in q8:
        verdict = {
            "q8_separates_under_q4_region": (
                len(q8["jokes_in_region"]) == 3 and not q8["controls_in_region"]
            ),
            "max_abs_S_delta": round(
                max(abs(a["S"] - b["S"]) for a, b in zip(q4["rows"], q8["rows"])), 3
            ),
            "max_abs_R_delta": round(
                max(abs(a["R"] - b["R"]) for a, b in zip(q4["rows"], q8["rows"])), 3
            ),
        }
        cert_rows = {r["name"]: r for r in cal["reference"]}
        drift_vs_certified = {
            r["name"]: round(r["S"] - cert_rows[r["name"]]["S"], 3) for r in q4["rows"]
        }

    receipt = {
        "receipt_type": "instrument_quant_check",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "instrument": "gemma2-full-nll",
        "certified_calibration_ts": cal["ts"],
        "region": {"s_band": [lo, hi], "r_floor": r_floor, "e_floor": e_floor},
        "protocol": "GT frames for jokes, generation suppressed (matches certified nll_calls=11)",
        "results": results,
        "q4_S_drift_vs_certified_receipt": drift_vs_certified,
        "verdict": verdict,
        "runtime_s": round(time.time() - t0, 1),
    }
    out_path = OUT / "gemma2_full_nll_quant_check.json"
    out_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "drift": drift_vs_certified}, indent=2))
    print("receipt ->", out_path)


if __name__ == "__main__":
    main()
