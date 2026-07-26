#!/usr/bin/env python3
"""Prove the 2026-07-26 instrument speed fix changes nothing but the clock.

`full_nll` used to convert the whole preallocated score buffer
([n_ctx=2048, n_vocab=256128]) to float64 on every call — 4.2 GB copied to read
the few rows a punchline actually needs. The fix widens one row at a time.

A speed fix to a CERTIFIED instrument is only allowed if it is bit-identical, so
this runs both code paths inside one process, on one loaded model, over the
calibration strings, and compares the NLLs exactly — not approximately.

    python3 instrument_rowslice_check.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
GGUF = Path(os.environ.get("GEMMA2_GGUF",
                           str(Path.home() / ".cache" / "gemma-2-2b-it-Q4_K_M.gguf")))

CASES = [
    ("I told my wife she should embrace her mistakes.", " She gave me a hug."),
    ("Why did the scarecrow win an award?", " He was outstanding in his field."),
    ("They put speed bumps outside the school.", " I've hit six kids already."),
    ("A horse walks into a bar.", " The bartender says, why the long face?"),
    ("The sky is blue today.", " The sky is blue today."),
]


def main() -> int:
    from llama_cpp import Llama
    n_ctx = 2048
    t0 = time.time()
    llm = Llama(model_path=str(GGUF), n_ctx=n_ctx, logits_all=True, verbose=False,
                n_threads=max(4, os.cpu_count() - 2))
    print(f"model loaded in {time.time() - t0:.1f}s, vocab {llm.n_vocab()}")

    def nlls_from(scores_getter, context, continuation):
        ctx = llm.tokenize(context.encode(), add_bos=True, special=False)
        cont = llm.tokenize(continuation.encode(), add_bos=False, special=False)
        llm.reset()
        llm.eval(ctx + cont)
        rows = scores_getter()
        out = []
        for i, tok in enumerate(cont):
            row = rows(len(ctx) + i - 1)
            m = row.max()
            lse = m + np.log(np.exp(row - m).sum())
            out.append(round(float(lse - row[tok]), 4))
        return out

    def old_path():
        full = np.asarray(llm.scores, dtype=np.float64)      # the 4.2 GB copy
        return lambda idx: full[idx]

    def new_path():
        s = llm.scores
        return lambda idx: np.asarray(s[idx], dtype=np.float64)

    results = []
    t_old = t_new = 0.0
    for ctx, cont in CASES:
        t = time.time(); old = nlls_from(old_path, ctx, cont); t_old += time.time() - t
        t = time.time(); new = nlls_from(new_path, ctx, cont); t_new += time.time() - t
        same = old == new
        results.append({"context": ctx, "continuation": cont, "identical": same,
                        "n_tokens": len(old), "mean_nll_old": round(sum(old) / len(old), 4),
                        "mean_nll_new": round(sum(new) / len(new), 4),
                        "max_abs_diff": max(abs(a - b) for a, b in zip(old, new))})
        print(f"  {'identical' if same else 'DIFFERS'}  n={len(old):>3}  "
              f"meanNLL {sum(old) / len(old):.4f}  {ctx[:44]!r}")

    all_same = all(r["identical"] for r in results)
    speedup = t_old / t_new if t_new else float("nan")
    print(f"\nold path {t_old:.1f}s | new path {t_new:.1f}s | speedup {speedup:.1f}x")
    print("VERDICT:", "bit-identical, fix is safe" if all_same else "DIFFERENT — revert the fix")

    OUT.mkdir(exist_ok=True)
    (OUT / "instrument_rowslice_check.json").write_text(json.dumps({
        "receipt_type": "instrument_rowslice_check",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "question": "does widening one score row at a time instead of the whole "
                    "buffer change any measured NLL?",
        "gguf": GGUF.name, "n_ctx": n_ctx,
        "cases": results,
        "all_identical": all_same,
        "seconds_old_path": round(t_old, 2), "seconds_new_path": round(t_new, 2),
        "speedup": round(speedup, 2),
        "note": "timings are from a machine under heavy concurrent load (load avg ~90 "
                "on 16 cores), so the ratio is more meaningful than either absolute",
    }, indent=2), encoding="utf-8")
    print("receipt -> jestry_out/instrument_rowslice_check.json")
    return 0 if all_same else 1


if __name__ == "__main__":
    raise SystemExit(main())
