"""Supply harvester: grow the precedent index from public humor, with receipts.

Law 1 applied to ourselves: `ingest.py` already speaks Wikiquote, Gutenberg
jest books, RSS, imgflip, HF datasets, and Reddit — this module orchestrates
those lanes instead of rebuilding them, adds three keyless joke APIs and a
clearly-labeled Gemma 4 synthesis lane, and puts two charter rules in front of
the corpora directory:

1. PROVENANCE  every record carries source + license before it is written;
2. PRECEDENT   every batch is deduped against the index (exact digest always;
               `--semantic` adds embeddinggemma near-dup checks) — the
               harvester itself asks "has this been done?" before ingesting.

Synthetic material is never laundered: the gemma4 lane stamps
`license: synthetic (model-generated...)` so no downstream claim can mistake
model output for human humor. Self-precedent is a feature there — indexing
Gemma's own past output lets the layer catch the generator repeating itself.

    python3 harvest_supply.py icanhazdadjoke --limit 30
    python3 harvest_supply.py official_joke_api --limit 20
    python3 harvest_supply.py jokeapi --limit 20
    python3 harvest_supply.py wikiquote --arg "Oscar Wilde" --limit 30
    python3 harvest_supply.py gutenberg --arg toasters_handbook --limit 40
    python3 harvest_supply.py gemma4 --arg "office life,AI tools" --limit 8
    python3 harvest_supply.py keyless --limit 20      # the three joke APIs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

import ingest
from ingest import UA, save_corpus

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "jestry_out"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _json_get(url: str, timeout: int = 25) -> Any:
    """Resilient JSON GET: Accept header (icanhazdadjoke serves HTML without
    it) and None on any transport/parse failure — a dead lane is a receipt
    fact, not a crash."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, headers=UA | {"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# extra keyless fetchers (the ingest lanes stay authoritative for the rest)
# ---------------------------------------------------------------------------
def icanhazdadjoke(limit: int = 30, term: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while len(out) < limit and page <= 6:
        data = _json_get(
            f"https://icanhazdadjoke.com/search?limit=30&page={page}"
            + (f"&term={term}" if term else ""))
        for row in (data or {}).get("results", []):
            joke = str(row.get("joke", "")).strip()
            if joke:
                out.append({"source": "icanhazdadjoke.com API",
                            "license": "icanhazdadjoke API terms (attribution requested)",
                            "text": joke,
                            "meta": {"api_id": row.get("id", ""), "language": "en"}})
        if not (data or {}).get("results"):
            break
        page += 1
    return out[:limit]


def official_joke_api(limit: int = 20, _arg: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    while len(out) < limit:
        rows = _json_get("https://official-joke-api.appspot.com/jokes/ten")
        if not rows:
            break
        for row in rows:
            setup = str(row.get("setup", "")).strip()
            punch = str(row.get("punchline", "")).strip()
            if setup and punch:
                out.append({"source": "official-joke-api.appspot.com",
                            "license": "public API (github: 15Dkatz/official_joke_api)",
                            "text": f"{setup} {punch}",
                            "meta": {"setup": setup, "punchline": punch,
                                     "type": row.get("type", ""), "language": "en"}})
    return out[:limit]


def jokeapi(limit: int = 20, _arg: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    while len(out) < limit:
        batch = min(10, limit - len(out))
        data = _json_get(f"https://v2.jokeapi.dev/joke/Any?safe-mode&amount={batch}")
        rows = (data or {}).get("jokes") or ([data] if data and data.get("joke") or
                                             data and data.get("setup") else [])
        if not rows:
            break
        for row in rows:
            if row.get("type") == "twopart":
                text = f"{row.get('setup', '').strip()} {row.get('delivery', '').strip()}"
                meta = {"setup": row.get("setup", ""), "punchline": row.get("delivery", "")}
            else:
                text = str(row.get("joke", "")).strip()
                meta = {}
            if text.strip():
                out.append({"source": "v2.jokeapi.dev (safe-mode)",
                            "license": "JokeAPI (jokes submitted by users; safe-mode filtered)",
                            "text": text.strip(),
                            "meta": meta | {"category": row.get("category", ""),
                                            "language": "en"}})
    return out[:limit]


SYNTH_PROMPT = (
    "Write {n} distinct one-liner jokes, one per line, across these topics: {topics}. "
    "Each must have a real setup expectation and a turn. No numbering, no commentary."
)


def gemma4_synthesize(limit: int = 8, topics: str = "office life, AI tools, city living"
                      ) -> list[dict[str, Any]]:
    from jestry import ollama_generate_with_usage
    res = ollama_generate_with_usage(SYNTH_PROMPT.format(n=limit, topics=topics),
                                     temperature=0.95, max_tokens=90 * limit)
    if not res.get("ok"):
        return []
    from humor_mesh import extract_candidates
    rows = []
    for cand in extract_candidates(res["response"], limit=limit):
        rows.append({"source": f"model-generated ({res['model']} via ollama)",
                     "license": "synthetic (model-generated; NOT human humor; "
                                "indexed for self-precedent only)",
                     "text": cand,
                     "meta": {"model": res["model"], "prompt_sha256": res["prompt_sha256"],
                              "language": "en", "synthetic": True}})
    return rows


LANES: dict[str, Callable[[int, str], list[dict[str, Any]]]] = {
    "icanhazdadjoke": lambda n, a: icanhazdadjoke(n, a),
    "official_joke_api": official_joke_api,
    "jokeapi": jokeapi,
    "gemma4": lambda n, a: gemma4_synthesize(n, a or "office life, AI tools, city living"),
    "wikiquote": lambda n, a: ingest.wikiquote_fetch(a or "Oscar Wilde", max_quotes=n),
    "gutenberg": lambda n, a: ingest.gutenberg_fetch(a or "toasters_handbook", max_items=n),
    "rss": lambda n, a: ingest.rss_headlines(max_per_feed=max(3, n // 4)),
    "imgflip": lambda n, a: ingest.imgflip_templates(max_items=n),
    "hf": lambda n, a: ingest.hf_dataset_rows(a or "short_jokes", n=n),
    "reddit": lambda n, a: ingest.reddit_jokes(a or "jokes", n=n),
}
KEYLESS_TRIO = ("icanhazdadjoke", "official_joke_api", "jokeapi")


# ---------------------------------------------------------------------------
# dedupe + receipts
# ---------------------------------------------------------------------------
def harvest(lane: str, limit: int = 20, arg: str = "", *, dedupe: bool = True,
            semantic: bool = False, out_dir: Path = OUT_DIR) -> dict[str, Any]:
    if lane not in LANES:
        raise SystemExit(f"unknown lane '{lane}'; lanes: {', '.join(LANES)} + keyless")
    fetched = LANES[lane](limit, arg)
    known: set[str] = set()
    near_dupes = 0
    idx = None
    if dedupe:
        from precedent import HashEmbedBackend, PrecedentIndex, pick_backend
        idx = PrecedentIndex(backend=pick_backend(semantic) if semantic else HashEmbedBackend(),
                             out_dir=out_dir)
        known = set(idx.items.keys())
        if semantic:
            idx.ensure_embedded()
    fresh: list[dict[str, Any]] = []
    seen_batch: set[str] = set()
    for rec in fetched:
        text = rec.get("text", "").strip()
        if not text:
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        if digest in known or digest in seen_batch:
            continue
        if idx is not None and semantic:
            rep = idx.been_done(text, k=1)
            if rep.surface_hits and rep.surface_hits[0].score >= 0.97:
                near_dupes += 1
                continue
        seen_batch.add(digest)
        fresh.append(rec)
    stamp = time.strftime("%Y%m%d")
    path = None
    if fresh:
        # never overwrite a same-day file: save_corpus opens "w", and an
        # overwrite is what left ghost entries in the precedent cache
        name = f"harvest_{lane}_{stamp}"
        n = 2
        while (ingest.CORPORA / f"{name}.jsonl").exists():
            name = f"harvest_{lane}_{stamp}_{n}"
            n += 1
        path = save_corpus(fresh, name)
    receipt = {
        "receipt_type": "jestry_harvest", "receipt_version": 1,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "lane": lane, "arg": arg,
        "fetched": len(fetched), "new": len(fresh),
        "exact_dupes": len(fetched) - len(fresh) - near_dupes, "near_dupes": near_dupes,
        "dedupe": dedupe, "semantic": semantic,
        "licenses": sorted({r.get("license", "unknown") for r in fresh}),
        "path": str(path) if path else None,
    }
    out_dir.mkdir(exist_ok=True)
    with (out_dir / "harvest_receipts.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser(description="grow the humor supply, with receipts")
    ap.add_argument("lane", help=f"one of: {', '.join(LANES)}, or 'keyless' for the joke-API trio")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--arg", default="", help="lane argument (author, book, subreddit, topics)")
    ap.add_argument("--no-dedupe", action="store_true")
    ap.add_argument("--semantic", action="store_true",
                    help="near-dup check via embeddinggemma (needs Ollama)")
    args = ap.parse_args()
    lanes = KEYLESS_TRIO if args.lane == "keyless" else (args.lane,)
    for lane in lanes:
        rec = harvest(lane, args.limit, args.arg,
                      dedupe=not args.no_dedupe, semantic=args.semantic)
        print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
