"""Licensing-clean data ingestion for HumorVibes.

Every source here is chosen for clean terms: Wikiquote (CC BY-SA, attributed),
Project Gutenberg (public domain), RSS headlines (facts/titles for commentary),
user-supplied transcripts (their own material), Imgflip's public template API.
No performer clips, no paywalled scraping, no ToS-gray endpoints.

All fetchers return normalized records:
  {"source": ..., "license": ..., "text": ..., "meta": {...}}
and `save_corpus` writes JSONL under corpora/ with provenance headers, ready
for the corpus lab (measure), history-remix (canon), and callback mining
(transcripts).
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CORPORA = Path(__file__).resolve().parent / "corpora"
UA = {"User-Agent": "HumorVibes research toolkit (Humor Genome NYC hackathon; contact via Kaggle taylorsamarel)"}


def _get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get_json(url: str, timeout: int = 25) -> Any:
    return json.loads(_get(url, timeout).decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# Wikiquote: canonical quotes at scale (CC BY-SA, attribution kept)
# ---------------------------------------------------------------------------
def wikiquote_fetch(page: str, max_quotes: int = 40) -> list[dict[str, Any]]:
    """Fetch quotes from a Wikiquote page (person or theme) via the MediaWiki API."""
    api = ("https://en.wikiquote.org/w/api.php?action=parse&prop=wikitext&format=json&redirects=1&page="
           + urllib.parse.quote(page))
    data = _get_json(api)
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    title = data.get("parse", {}).get("title", page)
    quotes: list[dict[str, Any]] = []
    # Wikiquote convention: quotes are top-level '*' bullets; sub-bullets are sourcing.
    for line in wikitext.splitlines():
        if not line.startswith("* ") or line.startswith("**"):
            continue
        text = re.sub(r"\{\{[^}]*\}\}", "", line[2:])          # templates
        text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)  # [[link|text]]
        text = re.sub(r"'{2,}", "", text).strip()               # bold/italic markup
        text = re.sub(r"<[^>]+>", "", text)
        if 20 <= len(text) <= 400 and not text.lower().startswith(("see ", "main article")):
            quotes.append({
                "source": f"wikiquote:{title}",
                "license": "CC BY-SA 4.0 (en.wikiquote.org)",
                "text": text,
                "meta": {"attributed_to": title},
            })
        if len(quotes) >= max_quotes:
            break
    return quotes


# ---------------------------------------------------------------------------
# Project Gutenberg: public-domain joke books (the century test)
# ---------------------------------------------------------------------------
# Curated PD humor collections (verified-era jest books; IDs on gutenberg.org):
GUTENBERG_JOKE_BOOKS = {
    "toasters_handbook": 18464,   # Toaster's Handbook: Jokes, Stories, Quotations (1916)
    "jokes_for_all": 39944,       # More Toasts (1922)
}


def gutenberg_fetch(book: str = "toasters_handbook", max_items: int = 60) -> list[dict[str, Any]]:
    """Pull a public-domain jest book and split it into candidate joke items.
    Enables the CENTURY TEST: do 1910s frames still collapse a modern mesh?"""
    book_id = GUTENBERG_JOKE_BOOKS.get(book, None) or int(book)
    try:
        text = _get(f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt").decode("utf-8", "replace")
    except Exception:
        text = _get(f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt").decode("utf-8", "replace")
    # strip PG header/footer
    body = re.split(r"\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG[^\n]*\n", text)[-1]
    body = re.split(r"\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG", body)[0]
    items, out = re.split(r"\n\s*\n", body), []
    for block in items:
        block = " ".join(block.split())
        # jest-book heuristics: short narrative blocks with dialogue or a question
        if 60 <= len(block) <= 420 and (('"' in block) or ("?" in block)) and not block.isupper():
            out.append({
                "source": f"gutenberg:{book_id}",
                "license": "Public domain (Project Gutenberg)",
                "text": block,
                "meta": {"era": "1910s-1920s", "book": book},
            })
        if len(out) >= max_items:
            break
    return out


# ---------------------------------------------------------------------------
# RSS headlines: today's topical material (facts/titles for commentary)
# ---------------------------------------------------------------------------
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
]


def rss_headlines(feeds: list[str] | None = None, max_per_feed: int = 12) -> list[dict[str, Any]]:
    out = []
    for feed in feeds or DEFAULT_FEEDS:
        try:
            xml = _get(feed).decode("utf-8", "replace")
        except Exception:
            continue
        titles = re.findall(r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", xml, flags=re.DOTALL)
        for t in titles[:max_per_feed]:
            t = " ".join(t.split())
            if len(t) >= 15:
                out.append({"source": f"rss:{urllib.parse.urlparse(feed).netloc}",
                            "license": "headline (title) used for commentary/research",
                            "text": t, "meta": {"feed": feed, "fetched": time.strftime("%Y-%m-%d")}})
    return out


# ---------------------------------------------------------------------------
# Transcripts (user-owned material) -> callback-mining lines
# ---------------------------------------------------------------------------
def parse_transcript(path: str | Path) -> list[dict[str, Any]]:
    """Parse .vtt/.srt/.txt into clean spoken lines for remix_history mining."""
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    lines: list[str] = []
    if path_suffix(path) in (".vtt", ".srt"):
        for line in raw.splitlines():
            line = line.strip()
            if (not line or line.isdigit() or "-->" in line or line.upper().startswith("WEBVTT")
                    or re.match(r"^\d{2}:\d{2}", line)):
                continue
            line = re.sub(r"<[^>]+>", "", line)
            if line and (not lines or line != lines[-1]):
                lines.append(line)
    else:
        lines = [l.strip() for l in raw.splitlines() if len(l.split()) >= 3]
    # merge fragments into sentence-ish units
    merged, buf = [], ""
    for line in lines:
        buf = (buf + " " + line).strip()
        if buf.endswith((".", "!", "?")) or len(buf) > 160:
            merged.append(buf)
            buf = ""
    if buf:
        merged.append(buf)
    return [{"source": f"transcript:{Path(path).name}", "license": "user-supplied material",
             "text": m, "meta": {}} for m in merged]


def path_suffix(p: str | Path) -> str:
    return Path(p).suffix.lower()


# ---------------------------------------------------------------------------
# Imgflip meme templates (public API): real current formats for meme_caption
# ---------------------------------------------------------------------------
def imgflip_templates(max_items: int = 40) -> list[dict[str, Any]]:
    data = _get_json("https://api.imgflip.com/get_memes")
    out = []
    for m in data.get("data", {}).get("memes", [])[:max_items]:
        out.append({"source": "imgflip:get_memes", "license": "template metadata via public API",
                    "text": m.get("name", ""), "meta": {"id": m.get("id"), "box_count": m.get("box_count"),
                                                        "url": m.get("url")}})
    return out


# ---------------------------------------------------------------------------
# HuggingFace datasets-server: keyless JSON rows of PUBLIC datasets (the
# research goldmine — several carry human FUNNINESS LABELS for validation)
# ---------------------------------------------------------------------------
HF_JOKE_DATASETS = {
    # name -> (repo, config, split, text_field, label_field or None)
    "short_jokes": ("Fraser/short-jokes", "default", "train", "Joke", None),
    "rjokes": ("SocialGrep/one-million-reddit-jokes", "default", "train", "selftext", "score"),  # upvotes = funniness proxy
    "hahackathon": ("SemEvalWorkshop/humicroedit", "subtask-1", "train", "edit", "meanGrade"),   # SemEval humor grades
}


def hf_dataset_rows(name: str = "short_jokes", n: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Fetch rows from a public HF dataset via the keyless datasets-server REST API.
    Several carry human funniness labels (upvote score / SemEval grade) — use those
    to VALIDATE measured laugh_score against real ratings, not just to source jokes."""
    repo, config, split, tf, lf = HF_JOKE_DATASETS.get(name, (name, "default", "train", "text", None))
    url = (f"https://datasets-server.huggingface.co/rows?dataset={urllib.parse.quote(repo)}"
           f"&config={config}&split={split}&offset={offset}&length={min(n, 100)}")
    try:
        data = _get_json(url)
    except Exception as e:
        print(f"HF datasets-server fetch failed for {repo} ({config}/{split}): {e}. "
              "Verify the exact repo/config at huggingface.co/datasets, or download the dataset "
              "directly inside a Kaggle internet-ON kernel (ungated datasets need no key).")
        return []
    out = []
    for row in data.get("rows", []):
        r = row.get("row", {})
        text = str(r.get(tf, "")).strip()
        if not text:
            continue
        rec = {"source": f"hf:{repo}", "license": "per dataset card (verify before redistribution)",
               "text": text, "meta": {"config": config, "split": split}}
        if lf and lf in r:
            rec["funniness_label"] = r[lf]   # the validation signal
        out.append(rec)
    return out


# ---------------------------------------------------------------------------
# Reddit r/jokes public JSON — live, topical, upvote-scored (research use;
# NOT for redistribution — respect Reddit's API terms)
# ---------------------------------------------------------------------------
def reddit_jokes(subreddit: str = "jokes", sort: str = "top", n: int = 25, t: str = "week") -> list[dict[str, Any]]:
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={min(n, 100)}&t={t}"
    try:
        data = _get_json(url)
    except Exception:
        return []
    out = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        title = (d.get("title") or "").strip()
        body = (d.get("selftext") or "").strip()
        text = (title + (" " + body if body else "")).strip()
        if len(text) >= 10:
            out.append({"source": f"reddit:r/{subreddit}", "license": "Reddit content — research use only, do not redistribute",
                        "text": text, "funniness_label": d.get("score"),  # upvotes
                        "meta": {"id": d.get("id"), "ups": d.get("score")}})
    return out


# ---------------------------------------------------------------------------
def save_corpus(records: list[dict[str, Any]], name: str) -> Path:
    CORPORA.mkdir(exist_ok=True)
    out = CORPORA / f"{name}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": {"name": name, "n": len(records),
                                       "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                       "note": "provenance per record; licensing-clean sources only"}}) + "\n")
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out


def load_corpus(name_or_path: str) -> list[dict[str, Any]]:
    p = Path(name_or_path)
    if not p.exists():
        p = CORPORA / f"{name_or_path}.jsonl"
    records = []
    for line in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if "_meta" not in rec:
            records.append(rec)
    return records
