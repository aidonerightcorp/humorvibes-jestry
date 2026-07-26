"""Does joke FORM change what Gemma finds surprising?

The corpus now carries a structural form label (style_taxonomy.py), so for the
first time the question is askable: a knock-knock, a what-do-you-call pun, and a
walks-into-a-bar setup are different machines for producing an expectation — do
they land in different surprisal regimes on the certified instrument?

Protocol, deliberately narrow so the number means one thing:

* INSTRUMENT   gemma-2-2b-it Q4_K_M through llama.cpp, the same certified
  instrument that pins S=3.19 on `speed_bumps`. No other instrument gates this.
* MEASURE      S only (surprise of the punchline given the setup). R needs a
  frame, and generating one per item would add a model call whose temperature
  makes the comparison noisier, not sharper. S is one deterministic forward
  pass, so a difference between forms is a difference in the data.
* SAMPLING     deterministic: items are sorted by a sha256 of their text and the
  first k per form are taken. Re-running gives the identical sample, and the
  order does not track source, length, or ingest date.
* CONTROL      a `wiktionary_proverb` arm. Proverbs are short assertions with no
  punchline, so if the form effect is real, proverbs should sit apart from the
  joke forms rather than in the middle of them.

What this CANNOT say: nothing here is about funniness. S is how surprised a 2B
model is by the last clause. A form with higher S is not a better joke, and
these items carry no human grade, so no claim about quality is available.

    python3 form_signal_study.py --per-form 12
    python3 form_signal_study.py --per-form 3 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import style_taxonomy as st

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "jestry_out"

# Forms worth contrasting: each is a distinct expectation-building machine.
# Generic buckets are excluded — "one_liner" is a shape, not a mechanism.
TARGET_FORMS = [
    "knock_knock", "what_do_you_call", "whats_the_difference", "walks_into_bar",
    "light_bulb", "q_and_a", "yo_mama", "doctor_doctor", "limerick",
    "setup_punchline",
]
CONTROL_SOURCES = ("wiktionary",)


def _key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect(per_form: int) -> dict[str, list[dict[str, Any]]]:
    """Deterministic stratified sample by form, plus a proverb control arm."""
    buckets: dict[str, list[dict[str, Any]]] = {f: [] for f in TARGET_FORMS}
    buckets["control_proverb"] = []
    for rec in st.iter_corpus():
        text = " ".join(rec.get("text", "").split())
        if not (20 <= len(text) <= 300):
            continue
        meta = rec.get("meta", {}) or {}
        if meta.get("language", "en") != "en":
            continue
        src = rec.get("source", "")
        if any(c in src for c in CONTROL_SOURCES) and meta.get("record_kind") == "proverb":
            buckets["control_proverb"].append({"text": text, "source": src})
            continue
        form = st.classify_form(text, meta)["form"]
        if form in buckets:
            buckets[form].append({"text": text, "source": src})
    # deterministic: hash-order, not corpus order
    for form, items in buckets.items():
        items.sort(key=lambda r: _key(r["text"]))
        buckets[form] = items[:per_form]
    return buckets


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _boot_ci(xs: list[float], n: int = 2000, seed: int = 7) -> tuple[float, float]:
    """Percentile bootstrap. Sample sizes here are small enough that a normal
    approximation would overstate precision."""
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        means.append(_mean([xs[rng.randrange(len(xs))] for _ in range(len(xs))]))
    means.sort()
    return (means[int(0.025 * n)], means[int(0.975 * n)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-form", type=int, default=12)
    ap.add_argument("--dry-run", action="store_true",
                    help="show the sample and stop, without touching the instrument")
    a = ap.parse_args()

    buckets = collect(a.per_form)
    print("sample:")
    for form, items in buckets.items():
        print(f"  {form:<22} {len(items):>3}")
    if a.dry_run:
        for form, items in buckets.items():
            if items:
                print(f"\n{form}: {items[0]['text'][:100]!r}")
        return 0

    import gemma2_full_nll as g
    from mesh_signals import split_setup_punchline
    if not g.available():
        print("certified instrument unavailable (venv or GGUF missing) — refusing "
              "to substitute a different model, since the whole point is that this "
              "one is the calibrated one")
        return 1
    provider = g.Gemma2FullNLLProvider()

    results: dict[str, list[float]] = {}
    rows: list[dict[str, Any]] = []
    errors = 0
    t0 = time.time()
    total = sum(len(v) for v in buckets.values())
    done = 0
    # Append each measurement as it lands. A previous run measured for 90
    # minutes, hit its timeout, and left NOTHING behind, because the receipt was
    # only written after the final item. At ~25-45s per measurement on CPU, a
    # run that cannot be interrupted safely is a run that cannot be trusted to
    # finish.
    OUT.mkdir(exist_ok=True)
    partial = OUT / "form_signal_partial.jsonl"
    partial.write_text("", encoding="utf-8")
    for form, items in buckets.items():
        vals: list[float] = []
        for it in items:
            setup, punch = split_setup_punchline(it["text"])
            if not setup.strip() or not punch.strip():
                continue
            try:
                r = provider.nll_tokens(setup + "\n", " " + punch)
            except Exception as e:
                errors += 1
                print(f"  ! {form}: {e}")
                continue
            if not math.isfinite(r.mean):
                errors += 1
                continue
            vals.append(r.mean)
            row = {"form": form, "S": round(r.mean, 4),
                   "n_tokens": len(r.tokens), "setup": setup[:120],
                   "punchline": punch[:120], "source": it["source"]}
            rows.append(row)
            with partial.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            done += 1
            if done % 10 == 0:
                el = time.time() - t0
                print(f"  [{done}/{total}] {el / 60:.1f} min elapsed, "
                      f"~{(el / done) * (total - done) / 60:.1f} min left", flush=True)
        results[form] = vals

    print(f"\n{'form':<22} {'n':>3}  {'mean S':>7}  {'95% CI':>18}")
    ordered = sorted(results.items(), key=lambda kv: -_mean(kv[1]) if kv[1] else 0)
    for form, vals in ordered:
        if not vals:
            print(f"{form:<22} {0:>3}  {'--':>7}")
            continue
        lo, hi = _boot_ci(vals)
        print(f"{form:<22} {len(vals):>3}  {_mean(vals):>7.3f}  [{lo:>6.3f}, {hi:>6.3f}]")

    ctrl = results.get("control_proverb", [])
    joke_forms = {f: v for f, v in results.items() if f != "control_proverb" and v}
    verdict = "insufficient data"
    if ctrl and joke_forms:
        c_lo, c_hi = _boot_ci(ctrl)
        separated = [f for f, v in joke_forms.items()
                     if len(v) >= 3 and _boot_ci(v)[0] > c_hi]
        overlapping = [f for f in joke_forms if f not in separated]
        verdict = (f"{len(separated)}/{len(joke_forms)} joke forms have a mean-S "
                   f"CI strictly above the proverb control's upper bound "
                   f"({c_hi:.3f}); {len(overlapping)} overlap it")
        print(f"\nverdict: {verdict}")
        print(f"  separated:   {sorted(separated)}")
        print(f"  overlapping: {sorted(overlapping)}")

    OUT.mkdir(exist_ok=True)
    receipt = {
        "receipt_type": "form_signal_study", "receipt_version": 1,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "instrument": "gemma2-full-nll (gemma-2-2b-it Q4_K_M, llama.cpp)",
        "measure": "S only (mean punchline NLL given setup); R not measured",
        "per_form_requested": a.per_form,
        "sampling": "deterministic: sha256(text) order, English only, 20-300 chars",
        "errors": errors,
        "elapsed_min": round((time.time() - t0) / 60, 2),
        "per_form": {f: {"n": len(v), "mean_S": round(_mean(v), 4) if v else None,
                         "ci95": [round(x, 4) for x in _boot_ci(v)] if len(v) > 1 else None}
                     for f, v in results.items()},
        "verdict": verdict,
        "caveat": "S is model surprisal, not funniness; these items carry no human grade",
    }
    with (OUT / "form_signal_receipts.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    (OUT / "form_signal_rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nreceipt -> {OUT / 'form_signal_receipts.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
