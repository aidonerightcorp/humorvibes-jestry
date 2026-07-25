#!/usr/bin/env python3
"""Pull a large upvote-scored joke corpus, resumably, into a local cache.

The graded corpora this project can reach top out around 28k rows. To ask
whether an effect is real at a scale where small effects are measurable, we
need a bigger population, and the only humor corpus with a per-item audience
signal at that size is r/Jokes, where each post carries a score.

Upvotes are not a funniness rating. They are a popularity proxy confounded by
posting time, subreddit dynamics, visibility and herd effects, and that caveat
travels with every number derived from this file. What they buy is n: at 100k
rows a correlation of 0.03 is separable from zero, which is not true at 83.

Written to be interrupted. Every page is appended to a JSONL cache and the
fetcher resumes from the last offset, so a network failure costs one page.

    python3 fetch_reddit_bulk.py --target 100000
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "data_cache" / "reddit_jokes_bulk.jsonl"
STATE = HERE / "data_cache" / "reddit_bulk_state.json"
DATASET = "SocialGrep/one-million-reddit-jokes"
URL = ("https://datasets-server.huggingface.co/rows?dataset="
       + urllib.parse.quote(DATASET, safe="")
       + "&config=default&split=train&offset={off}&length={n}")

ARTIFACT = re.compile(r"&amp;#x200B;|&#x200B;|\[removed\]|\[deleted\]|https?://\S+")
BLOCK = re.compile(
    r"\b(n[i1]gg\w*|f[a4]gg\w*|r[e3]t[a4]rd\w*|k[i1]ke|sp[i1]c|ch[i1]nk|tr[a4]nn\w*|c[uo]nt|"
    r"rape|molest\w*|pedo\w*|incest|holocaust|nazi|suicide|kill yourself|kys)\b", re.I)


def clean(t: str) -> str:
    t = html.unescape(html.unescape(str(t or "")))
    return re.sub(r"\s+", " ", ARTIFACT.sub(" ", t)).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=100_000)
    ap.add_argument("--pace", type=float, default=0.35)
    args = ap.parse_args()
    CACHE.parent.mkdir(parents=True, exist_ok=True)

    offset = 0
    kept = 0
    if STATE.exists():
        st = json.loads(STATE.read_text())
        offset, kept = st.get("offset", 0), st.get("kept", 0)
        print(f"resuming at offset {offset} with {kept} rows cached")

    sink = CACHE.open("a", encoding="utf-8")
    t0 = time.time()
    misses = 0
    while kept < args.target:
        try:
            req = urllib.request.Request(URL.format(off=offset, n=100),
                                         headers={"User-Agent": "HumorVibesResearch/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                rows = json.loads(r.read()).get("rows", [])
        except Exception as exc:
            misses += 1
            if misses > 25:
                print(f"stopping: {misses} consecutive failures, last {type(exc).__name__}")
                break
            time.sleep(min(60, 5 * misses))
            continue
        misses = 0
        if not rows:
            print("dataset exhausted")
            break
        for item in rows:
            row = item.get("row", {})
            setup, punch = clean(row.get("title")), clean(row.get("selftext"))
            score = row.get("score")
            if not setup or not punch or not isinstance(score, int):
                continue
            if not (10 <= len(setup) <= 300 and 5 <= len(punch) <= 300):
                continue
            if row.get("subreddit.nsfw") or BLOCK.search(f"{setup} {punch}"):
                continue
            sink.write(json.dumps({"setup": setup, "punchline": punch, "score": score},
                                  ensure_ascii=False) + "\n")
            kept += 1
        offset += 100
        if offset % 5000 == 0:
            sink.flush()
            STATE.write_text(json.dumps({"offset": offset, "kept": kept}))
            rate = kept / max(1e-9, time.time() - t0)
            print(f"  offset {offset}: {kept} kept ({rate:.0f}/s, {time.time()-t0:.0f}s)", flush=True)
        time.sleep(args.pace)
    sink.close()
    STATE.write_text(json.dumps({"offset": offset, "kept": kept}))
    print(f"DONE: {kept} rows cached at {CACHE} (scanned to offset {offset})")


if __name__ == "__main__":
    main()
