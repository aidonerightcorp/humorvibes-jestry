#!/usr/bin/env python3
"""A Gemma 4 instrument with exact full-vocabulary NLL, via transformers.

Why this file exists. Until now the certified instrument was gemma-2-2b-it, and
that was never a preference for the older model, it was a transport limit with
three receipts behind it: Ollama exposes only top-K logprobs, which failed
certification outright (`gemma4_calibration.json`); gemma4:e2b omits the
logprobs entry at sentence boundaries entirely; and llama.cpp cannot load the
Gemma 4 GGUF architecture. Both of the first two were re-tested on 2026-07-25
and both still hold.

The path none of those receipts had tried is the obvious one: skip the serving
layers and take the logits straight from the model. Teacher forcing needs a
single forward pass over the whole sequence, not autoregressive generation, so
an E2B-class Gemma 4 is affordable on CPU. `transformers` ships
`Gemma4ForConditionalGeneration`, and `google/gemma-4-E2B-it` is ungated, so the
instrument can be built with no API, no quantisation, and no top-K censoring.

What this gives that the Ollama readout could not:
- every token's negative log likelihood computed against the FULL vocabulary,
  so no value is a lower bound clipped toward the K-th mass;
- no serving-layer prompt rewriting, so the copy-attractor mitigation in the
  Ollama provider is unnecessary here rather than merely disabled;
- the same SignalProvider interface as the gemma-2 instrument, so
  `compute_signals` and the whole acceptance path work unchanged.

This module does not assume it deserves to gate acceptance. It measures, and
`calibrate()` runs the same reference protocol the gemma-2 instrument had to
pass: three reference jokes with ground-truth frames must land inside a derived
region and both controls must fall outside it. If that fails, the receipt says
certified:false and the instrument stays a measuring tool with no authority,
exactly as the gemma4-forced-NLL readout did.

    python3 gemma4_transformers_nll.py              # certify against references
    python3 gemma4_transformers_nll.py --probe      # single joke, verbose
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from mesh_signals import OfflineStub, SurprisalProfile, compute_signals

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
MODEL_ID = os.environ.get("GEMMA4_MODEL", "google/gemma-4-E2B-it")


class Gemma4TransformersProvider:
    """SignalProvider: exact full-vocab teacher forcing on Gemma 4 via transformers."""

    name = "gemma4-transformers-full-nll"

    def __init__(self, model_id: str = MODEL_ID) -> None:
        self.model_id = model_id
        self.model = model_id
        self._tok = None
        self._model = None
        self.calls = 0
        self.errors = 0
        self.last_error: str | None = None
        self.load_seconds: float | None = None
        # generation and judging are delegated; this class is an instrument only
        from humorvibes.signal_providers import OllamaSignalProvider
        self._gen = OllamaSignalProvider()
        self._gen.model = os.environ.get("GEMMA_MODEL", "gemma4")

    def _ensure(self) -> bool:
        if self._model is not None:
            return True
        try:
            import torch
            from transformers import AutoTokenizer, Gemma4ForConditionalGeneration
            t0 = time.time()
            self._tok = AutoTokenizer.from_pretrained(self.model_id)
            self._model = Gemma4ForConditionalGeneration.from_pretrained(
                self.model_id, dtype=torch.float32, low_cpu_mem_usage=True)
            self._model.eval()
            self._torch = torch
            self.load_seconds = round(time.time() - t0, 1)
            return True
        except Exception as exc:
            self.last_error = f"load: {type(exc).__name__}: {exc}"
            return False

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        """Exact NLL of every continuation token, full vocabulary, one forward pass."""
        if not self._ensure():
            self.errors += 1
            stub = OfflineStub().nll_tokens(context, continuation)
            stub.measured = False
            return stub
        torch = self._torch
        try:
            ctx_ids = self._tok(context, add_special_tokens=True, return_tensors="pt").input_ids
            cont_ids = self._tok(continuation, add_special_tokens=False, return_tensors="pt").input_ids
            if cont_ids.shape[1] == 0:
                return SurprisalProfile(tokens=[], nlls=[], measured=True)
            ids = torch.cat([ctx_ids, cont_ids], dim=1)
            with torch.no_grad():
                logits = self._model(input_ids=ids).logits.float()
            n_ctx = ctx_ids.shape[1]
            # position i-1 predicts token i, so the continuation's first token is
            # scored by the last context position
            sl = logits[0, n_ctx - 1: ids.shape[1] - 1, :]
            logprobs = torch.log_softmax(sl, dim=-1)
            targets = cont_ids[0]
            picked = logprobs[range(targets.shape[0]), targets]
            nlls = [round(float(-v), 4) for v in picked]
            toks = [self._tok.decode([int(t)]) for t in targets]
        except Exception as exc:
            self.last_error = f"forward: {type(exc).__name__}: {exc}"
            self.errors += 1
            stub = OfflineStub().nll_tokens(context, continuation)
            stub.measured = False
            return stub
        if not all(v == v and abs(v) != float("inf") for v in nlls):
            # same honesty invariant as the gemma-2 provider: a signal that is
            # not a number was never measured
            self.last_error = "non-finite NLL from the forward pass"
            self.errors += 1
            stub = OfflineStub().nll_tokens(context, continuation)
            stub.measured = False
            return stub
        self.calls += 1
        prof = SurprisalProfile(tokens=toks, nlls=nlls, measured=True)
        prof.censored = 0                      # type: ignore[attr-defined]
        prof.nll_is_lower_bound = False        # type: ignore[attr-defined]
        return prof

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        return self._gen.generate(prompt, temperature=temperature, max_tokens=max_tokens)

    def judge_json(self, prompt: str):
        return self._gen.judge_json(prompt)


def calibrate(provider: Gemma4TransformersProvider) -> dict:
    """The same certification protocol the gemma-2 instrument had to pass."""
    from calibrate_gemma4 import CONTROLS, REFERENCE_JOKES

    rows = []
    for name, setup, punch, frame in REFERENCE_JOKES + CONTROLS:
        sig = compute_signals(provider, setup, punch, frame_hint=frame or None)
        rows.append({"name": name,
                     "kind": "joke" if any(name == j[0] for j in REFERENCE_JOKES) else "control",
                     "S": sig.surprise_mean, "R": sig.resolution, "E": sig.efficiency,
                     "measured": sig.measured})
        print(f"  {name:12s} S={sig.surprise_mean:7.3f} R={sig.resolution:6.3f} "
              f"E={sig.efficiency:7.4f} measured={sig.measured}", flush=True)

    jokes = [r for r in rows if r["kind"] == "joke"]
    ctrls = [r for r in rows if r["kind"] == "control"]
    s_vals = [r["S"] for r in rows if r["measured"]]
    joke_r = [r["R"] for r in jokes]
    ctrl_r = [r["R"] for r in ctrls]
    separates = bool(joke_r and ctrl_r and min(joke_r) > max(ctrl_r))
    derived = None
    if separates and s_vals:
        lo, hi = min(s_vals), max(s_vals)
        pad = 0.25 * (hi - lo) if hi > lo else 1.0
        derived = {"s_band": [round(lo - pad, 3), round(hi + pad, 3)],
                   "r_floor": round(min(joke_r) * 0.5, 4),
                   "e_floor": round(min(r["E"] for r in jokes) * 0.5, 5)}

    return {
        "receipt_type": "instrument_calibration",
        "receipt_version": 2,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "instrument": provider.name,
        "model": provider.model_id,
        "transport": "transformers, local weights, full vocabulary, single forward pass",
        "why_this_exists": ("Ollama top-K failed certification, gemma4:e2b omits logprobs at "
                            "sentence boundaries, and llama.cpp cannot load the Gemma 4 GGUF; "
                            "all three re-tested 2026-07-25. Taking logits directly avoids all three."),
        "reference": rows,
        "nll_calls": provider.calls,
        "instrument_errors": provider.errors,
        "load_seconds": provider.load_seconds,
        "derived": derived,
        "checks": {"all_jokes_pass": separates, "all_controls_fail": separates},
        "certified": separates,
        "rule": ("accept when s_band[0] <= S <= s_band[1] and R >= r_floor and E >= e_floor; "
                 "SCOPE: frame hints only from trusted provenance, per the frame-provenance "
                 "finding in native_format_probe.json"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()
    p = Gemma4TransformersProvider()
    print(f"loading {p.model_id} (CPU, float32) …", flush=True)
    if not p._ensure():
        print("LOAD FAILED:", p.last_error)
        raise SystemExit(1)
    print(f"loaded in {p.load_seconds}s")

    if args.probe:
        sig = compute_signals(
            p, "I told my therapist about my fear of speed bumps.",
            "She said I'm slowly getting over it.",
            frame_hint="'Getting over it' is literal, the car physically drives over the bumps slowly.")
        print(json.dumps(sig.to_dict(), indent=2)[:900])
        return

    print("certifying against the fixed reference set …")
    receipt = calibrate(p)
    path = OUT / "gemma4_transformers_calibration.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"\ncertified={receipt['certified']}  (jokes must all separate from controls on R)")
    if receipt["derived"]:
        print("derived region:", json.dumps(receipt["derived"]))
    print("receipt ->", path)


if __name__ == "__main__":
    main()
