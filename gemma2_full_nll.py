"""Full-logprob local instrument: gemma-2-2b-it GGUF via llama.cpp, exact NLL.

The top-K-censored gemma4 readout failed certification (receipted). This module
restores the CERTIFIED measurement regime locally: gemma-2-2b-it — the exact
instrument family the pinned Kaggle bands were validated on — evaluated with
``logits_all=True`` so teacher-forced continuation NLL is computed over the
FULL vocabulary in one forward pass. No top-K, no censoring, no stepwise API
calls.

Division of labor (mirrors the Kaggle design, one step cleaner):
- gemma-2-2b-it (llama.cpp, this module)  = the instrument (S/R/E);
- gemma4 via Ollama                       = generator, frame-writer, persona-B
                                            judge (delegated unchanged).

The model runs in a persistent worker under the dedicated venv
(~/.venvs/jestry-nll) because llama-cpp-python lives there; the provider talks
to it over JSON lines on stdin/stdout. Weights: a public (ungated) GGUF —
bartowski/gemma-2-2b-it-GGUF Q4_K_M — so no HF token is involved; provenance
is recorded in every calibration receipt.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mesh_signals import OfflineStub, OllamaProvider, SurprisalProfile

VENV_PY = Path.home() / ".venvs" / "jestry-nll" / "bin" / "python"
GGUF = Path(os.environ.get(
    "GEMMA2_GGUF", str(Path.home() / ".cache" / "gemma-2-2b-it-Q4_K_M.gguf")))

WORKER = r'''
import json, sys
import numpy as np
from llama_cpp import Llama

N_CTX = 2048
llm = Llama(model_path=sys.argv[1], n_ctx=N_CTX, logits_all=True,
            verbose=False, n_threads=max(4, __import__("os").cpu_count() - 2))
print(json.dumps({"ready": True, "n_vocab": llm.n_vocab()}), flush=True)

def full_nll(context, continuation):
    ctx = llm.tokenize(context.encode("utf-8"), add_bos=True, special=False)
    cont = llm.tokenize(continuation.encode("utf-8"), add_bos=False, special=False)
    if not cont:
        return [], []
    if len(ctx) + len(cont) > N_CTX - 4:
        raise ValueError(f"context+continuation = {len(ctx) + len(cont)} tokens "
                         f"exceeds n_ctx {N_CTX}")
    llm.reset()
    llm.eval(ctx + cont)
    # `llm.scores` is preallocated at [n_ctx, n_vocab] = 2048 x 256128. Converting
    # the WHOLE buffer to float64 allocated and copied 4.2 GB per call to read the
    # handful of rows a punchline needs — the dominant cost of every measurement
    # and, on a loaded machine, the difference between seconds and minutes.
    # Row-at-a-time is bit-identical: the same float32 values widened in the same
    # order, so the certified calibration is untouched (verified below).
    scores = llm.scores
    toks, nlls = [], []
    for i, tok in enumerate(cont):
        row = np.asarray(scores[len(ctx) + i - 1], dtype=np.float64)
        m = row.max()
        lse = m + np.log(np.exp(row - m).sum())
        nlls.append(round(float(lse - row[tok]), 4))
        toks.append(llm.detokenize([tok]).decode("utf-8", "replace"))
    return toks, nlls

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
        toks, nlls = full_nll(req["context"], req["continuation"])
        print(json.dumps({"tokens": toks, "nlls": nlls}), flush=True)
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), flush=True)
'''


class Gemma2FullNLLProvider:
    """SignalProvider: exact full-vocab teacher forcing on gemma-2-2b-it."""

    name = "gemma2-full-nll"

    def __init__(self) -> None:
        self.model = "gemma-2-2b-it-Q4_K_M.gguf (llama.cpp)"
        self.think = False
        self._gen = OllamaProvider()          # gemma4 stays generator + judge
        # OllamaProvider defaults to gemma3:4b, which is NOT installed here —
        # leaving it caused every persona judgment to silently return
        # "no judge available" (2026-07-24 adversarial finding: the B-gate
        # passed vacuously). Pin the real judge model explicitly.
        self._gen.model = os.environ.get("GEMMA_MODEL", "gemma4")
        self._proc: subprocess.Popen | None = None
        self.calls = 0
        self.errors = 0
        self.restarts = 0                 # transparent recoveries, still receipted
        self.last_error: str | None = None

    # ---------------------------------------------------------------- worker
    def _ensure_worker(self) -> bool:
        if self._proc is not None and self._proc.poll() is None:
            return True
        if not VENV_PY.exists() or not GGUF.exists():
            self.last_error = f"missing {'venv' if not VENV_PY.exists() else 'gguf'}"
            return False
        try:
            self._proc = subprocess.Popen(
                [str(VENV_PY), "-c", WORKER, str(GGUF)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1)
            ready = json.loads(self._proc.stdout.readline())
            return bool(ready.get("ready"))
        except Exception as exc:
            self.last_error = f"worker boot: {type(exc).__name__}: {exc}"
            self.close()          # terminate, never orphan a loaded model
            return False

    def close(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

    # ---------------------------------------------------- SignalProvider API
    def _ask_worker(self, payload: str) -> dict[str, Any] | None:
        assert self._proc and self._proc.stdin and self._proc.stdout
        try:
            self._proc.stdin.write(payload)
            self._proc.stdin.flush()
            return json.loads(self._proc.stdout.readline())
        except Exception as exc:
            self.last_error = f"worker io: {type(exc).__name__}: {exc}"
            self.close()
            return None

    def nll_tokens(self, context: str, continuation: str) -> SurprisalProfile:
        payload = json.dumps({"context": context, "continuation": continuation}) + "\n"
        resp: dict[str, Any] | None = None
        # a killed/crashed worker can pass the poll() liveness check for one
        # call and fail on write — retry once with a fresh worker before
        # degrading, so a single crash costs nothing
        for attempt in range(2):
            if not self._ensure_worker():
                break
            resp = self._ask_worker(payload)
            if resp is not None:
                if attempt:
                    self.restarts += 1    # recovered on the fresh worker
                break
        if resp is None:
            self.errors += 1
            stub = OfflineStub().nll_tokens(context, continuation)
            stub.measured = False
            return stub
        if "error" in resp:
            self.last_error = resp["error"]
            self.errors += 1
            stub = OfflineStub().nll_tokens(context, continuation)
            stub.measured = False
            return stub
        # Non-finite guard (2026-07-24): a truncated/corrupt GGUF loads and
        # evaluates without raising, but every logit comes back NaN — and NaN
        # NLLs propagated all the way to a receipt that still claimed
        # measured=True. A signal that is not a number was never measured.
        if not all(math.isfinite(v) for v in resp["nlls"]):
            self.last_error = ("non-finite NLL from the worker — corrupt or truncated "
                               f"weights at {GGUF.name}? (verify the GGUF checksum)")
            self.errors += 1
            stub = OfflineStub().nll_tokens(context, continuation)
            stub.measured = False
            return stub
        self.calls += 1
        prof = SurprisalProfile(tokens=resp["tokens"], nlls=resp["nlls"], measured=True)
        prof.censored = 0                     # type: ignore[attr-defined]  full vocab
        prof.nll_is_lower_bound = False       # type: ignore[attr-defined]
        return prof

    def generate(self, prompt: str, *, temperature: float = 0.8, max_tokens: int = 220) -> str:
        return self._gen.generate(prompt, temperature=temperature, max_tokens=max_tokens)

    def judge_json(self, prompt: str) -> dict[str, Any] | None:
        return self._gen.judge_json(prompt)


def available() -> bool:
    p = Gemma2FullNLLProvider()
    ok = p._ensure_worker()
    p.close()
    return ok


if __name__ == "__main__":
    from mesh_signals import compute_signals

    p = Gemma2FullNLLProvider()
    cases = [
        ("I told my therapist about my fear of speed bumps.",
         "She said I'm slowly getting over it.",
         "'Getting over it' is literal — the car physically drives over the speed bumps slowly."),
        ("I told my therapist about my fear of speed bumps.",
         "The quarterly cheese fondue regatta sailed backwards.", ""),
        ("I told my therapist about my fear of speed bumps.",
         "She said we can talk about it next week.", ""),
    ]
    for setup, punch, frame in cases:
        sig = compute_signals(p, setup, punch, frame_hint=frame or None)
        print(f"S={sig.surprise_mean:5.2f}  R_raw={sig.resolution_raw:5.2f}  "
              f"R_null={sig.resolution_null:5.2f}  R_net={sig.resolution:5.2f}  "
              f"E={sig.efficiency:6.3f}  measured={sig.measured}  :: {punch[:44]}")
    print(f"worker calls={p.calls} errors={p.errors} last_error={p.last_error}")
    p.close()
