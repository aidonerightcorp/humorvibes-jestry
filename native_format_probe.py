#!/usr/bin/env python3
"""Does the instrument read NATIVE setup/punchline jokes better than headlines?

Tonight's format-boundary experiment showed that anchoring the split at a
headline's edited word engages resolution more often but still predicts no
funniness (`jestry_out/format_boundary_experiment.json`). That left one reading
untested: headlines may simply be the wrong shape, and the instrument may work
where the format is native. r/Jokes posts are exactly that shape, with the
title as setup and the body as punchline, so no splitter heuristic is involved
at all.

Two arms, because the available human signal is weak:

- **Arm A (decisive, clean).** Genuine pairs versus shuffled pairs, where a
  punchline is swapped in from a different setup. This is the separation the
  theory actually claims and it needs no rating at all: a genuine pair should
  resolve under its frame, a mismatched one should not survive the decoy null.
  Reported as a rank-sum (Mann-Whitney U / AUC) of R, plus how often R > 0.
- **Arm B (exploratory, noisy).** Correlation of the measured signals with
  log2(1 + upvotes). Upvotes are a popularity proxy confounded by timing,
  subreddit dynamics and visibility, so a null here is weak evidence and is
  reported as such. A positive result would be strong.

Data: SocialGrep/one-million-reddit-jokes via the HF datasets-server (paced;
the server 429s under pressure). Content screening reuses the project's own
lane discipline before anything reaches the instrument or a receipt.

    python3 native_format_probe.py --n 30

Receipt: jestry_out/native_format_probe.json (+ per-item native_format_items.jsonl).
"""
from __future__ import annotations

import argparse
import html
import json
import math
import random
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from gemma2_full_nll import Gemma2FullNLLProvider
from mesh_signals import compute_signals

HERE = Path(__file__).resolve().parent
OUT = HERE / "jestry_out"
DATASET = "SocialGrep/one-million-reddit-jokes"
ROWS_URL = ("https://datasets-server.huggingface.co/rows?dataset="
            + urllib.parse.quote(DATASET, safe="")
            + "&config=default&split=train&offset={off}&length={n}")

# the project's screening discipline: community-scraped supply is filtered
# before it can reach an instrument, a receipt, or a public artifact
BLOCK = re.compile(
    r"\b(n[i1]gg\w*|f[a4]gg\w*|r[e3]t[a4]rd\w*|k[i1]ke|sp[i1]c|ch[i1]nk|tr[a4]nn\w*|c[uo]nt|"
    r"rape|molest\w*|pedo\w*|incest|holocaust|nazi|suicide|kill yourself|kys)\b", re.I)
# Supply is community-scraped and these items get written into a public receipt,
# so the identity-topic screen is deliberately blunt: this probe needs ~30 clean
# pairs out of thousands, and precision costs nothing here.
IDENTITY = re.compile(
    r"\b(arab|jew\w*|muslim|islam\w*|christian|black people|white people|asian|mexican|"
    r"indian|african|gay|lesbian|transgender|women be|blonde|feminis\w*|immigrant\w*|"
    r"race|racist|religion|abortion|slaver\w*)\b", re.I)
ARTIFACT = re.compile(r"&amp;#x200B;|&#x200B;|\[removed\]|\[deleted\]|https?://\S+")


def clean(text: str) -> str:
    text = html.unescape(html.unescape(str(text or "")))
    text = ARTIFACT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch(target: int, pace: float = 2.5) -> list[dict]:
    """Paced pull; keeps only clean, native setup/punchline pairs."""
    kept: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while len(kept) < target * 6 and offset < 4000:
        url = ROWS_URL.format(off=offset, n=100)
        req = urllib.request.Request(url, headers={"User-Agent": "HumorVibesResearch/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                rows = json.loads(r.read()).get("rows", [])
        except Exception as exc:                       # 429 or transient: back off once
            print(f"  fetch {offset}: {type(exc).__name__}, backing off 30s")
            time.sleep(30)
            offset += 100
            continue
        if not rows:
            break
        for item in rows:
            row = item.get("row", {})
            setup, punch = clean(row.get("title")), clean(row.get("selftext"))
            score = row.get("score")
            if not setup or not punch or not isinstance(score, int):
                continue
            if not (15 <= len(setup) <= 180 and 10 <= len(punch) <= 180):
                continue
            blob = f"{setup} {punch}"
            if BLOCK.search(blob) or IDENTITY.search(blob):
                continue
            if row.get("subreddit.nsfw"):
                continue
            key = punch.lower()[:60]
            if key in seen:
                continue
            seen.add(key)
            kept.append({"setup": setup, "punchline": punch, "score": int(score),
                         "permalink": row.get("permalink", "")})
        offset += 100
        time.sleep(pace)
    return kept


def stratified(pool: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Spread the sample across upvote magnitude so arm B has variance."""
    bins: dict[int, list[dict]] = {}
    for row in pool:
        bins.setdefault(int(math.log2(1 + max(0, row["score"]))), []).append(row)
    picked: list[dict] = []
    keys = sorted(bins)
    while len(picked) < n and keys:
        for k in list(keys):
            if not bins[k]:
                keys.remove(k)
                continue
            picked.append(bins[k].pop(rng.randrange(len(bins[k]))))
            if len(picked) >= n:
                break
    return picked


def auc(pos: list[float], neg: list[float]) -> float:
    """Rank-sum AUC: P(a random genuine R exceeds a random shuffled R)."""
    if not pos or not neg:
        return float("nan")
    vals = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks: dict[int, float] = {}
    i = 0
    order = 1
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1][0] == vals[i][0]:
            j += 1
        avg = (order + (order + (j - i))) / 2.0
        for k in range(i, j + 1):
            ranks[k] = avg
        order += (j - i) + 1
        i = j + 1
    rsum = sum(ranks[k] for k, (_, lab) in enumerate(vals) if lab == 1)
    n1, n0 = len(pos), len(neg)
    return round((rsum - n1 * (n1 + 1) / 2) / (n1 * n0), 4)


def spearman(a: list[float], b: list[float]) -> float:
    """Tied values share their average rank; see humor_features.rank_midpoint.

    The tie-naive version this replaced correlated a low-cardinality column with
    row order (adversarial audit, 2026-07-25).
    """
    from humor_features import rank_midpoint
    ra, rb = rank_midpoint(a), rank_midpoint(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return round(num / den, 3) if den else 0.0


def _headline_comparison() -> dict:
    """Read the headline experiment's numbers from ITS receipt, never copy them.

    These were literals with a "source" field asserting a provenance they did not
    have: correct on the day, silently false the moment that experiment is re-run
    (adversarial audit, 2026-07-25).
    """
    path = OUT / "format_boundary_experiment.json"
    if not path.exists():
        return {"unavailable": "format_boundary_experiment.json not present"}
    rec = json.loads(path.read_text(encoding="utf-8"))
    canon = rec["conditions"]["canonical"]
    return {
        "headline_canonical_R_positive_frac": canon["R_positive_frac"],
        "headline_laugh_spearman": canon["laugh"]["spearman"],
        "source": "jestry_out/format_boundary_experiment.json",
        "read_at_runtime": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args()
    t0 = time.time()
    rng = random.Random(7)

    print(f"fetching {DATASET} (paced)…")
    pool = fetch(args.n)
    print(f"  clean native pairs available: {len(pool)}")
    items = stratified(pool, args.n, rng)
    print(f"  sampled: {len(items)} across log2 upvote bins")

    # shuffled control: a punchline from a DIFFERENT setup (derangement)
    idx = list(range(len(items)))
    shifted = idx[1:] + idx[:1]
    provider = Gemma2FullNLLProvider()
    sink = (OUT / "native_format_items.jsonl").open("w", encoding="utf-8")
    genuine: list[dict] = []
    shuffled: list[dict] = []

    for i, row in enumerate(items):
        for kind, punch in (("genuine", row["punchline"]),
                            ("shuffled", items[shifted[i]]["punchline"])):
            sig = compute_signals(provider, row["setup"], punch)   # frame generated, as pinned
            if not sig.measured:
                continue
            rec = {"kind": kind, "setup": row["setup"], "punchline": punch,
                   "score": row["score"], "log2_score": round(math.log2(1 + max(0, row["score"])), 3),
                   "S": sig.surprise_mean, "R": sig.resolution, "E": sig.efficiency,
                   "laugh": sig.laugh_score, "frame": sig.frame_hint[:160]}
            (genuine if kind == "genuine" else shuffled).append(rec)
            sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if (i + 1) % 5 == 0:
            sink.flush()
            print(f"  {i + 1}/{len(items)} pairs ({time.time() - t0:.0f}s, "
                  f"errors={provider.errors})", flush=True)
    sink.close()
    provider.close()

    gR = [r["R"] for r in genuine]
    sR = [r["R"] for r in shuffled]
    report = {
        "receipt_type": "native_format_probe",
        "receipt_version": 1,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "instrument": provider.name,
        "dataset": DATASET,
        "protocol": ("r/Jokes title=setup, body=punchline (no splitter heuristic); frames "
                     "generated by the model as in the pinned validation run; shuffled arm "
                     "swaps in a punchline from a different setup (cyclic derangement)"),
        "screening": "slur/abuse regex + nsfw flag + artifact strip before measurement",
        "n_pairs": len(items),
        "arm_A_genuine_vs_shuffled": {
            "n_genuine": len(genuine), "n_shuffled": len(shuffled),
            "auc_R": auc(gR, sR),
            "mean_R_genuine": round(sum(gR) / len(gR), 4) if gR else None,
            "mean_R_shuffled": round(sum(sR) / len(sR), 4) if sR else None,
            "frac_R_positive_genuine": round(sum(1 for v in gR if v > 0) / len(gR), 3) if gR else None,
            "frac_R_positive_shuffled": round(sum(1 for v in sR if v > 0) / len(sR), 3) if sR else None,
            "auc_laugh": auc([r["laugh"] for r in genuine], [r["laugh"] for r in shuffled]),
        },
        "arm_B_upvote_correlation": {
            "note": ("upvotes are a popularity proxy confounded by timing, subreddit dynamics "
                     "and visibility; a null here is weak evidence, a positive would be strong"),
            "spearman_laugh_vs_log2score": spearman([r["laugh"] for r in genuine],
                                                    [r["log2_score"] for r in genuine]),
            "spearman_R_vs_log2score": spearman(gR, [r["log2_score"] for r in genuine]),
            "spearman_S_vs_log2score": spearman([r["S"] for r in genuine],
                                                [r["log2_score"] for r in genuine]),
        },
        "comparison": _headline_comparison(),
        "worker": {"calls": provider.calls, "errors": provider.errors,
                   "restarts": provider.restarts},
        "runtime_s": round(time.time() - t0, 1),
    }
    (OUT / "native_format_probe.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("arm_A_genuine_vs_shuffled", "arm_B_upvote_correlation")}, indent=2))
    print("receipt ->", OUT / "native_format_probe.json")


if __name__ == "__main__":
    main()
