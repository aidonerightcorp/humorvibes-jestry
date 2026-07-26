"""Structure-aware Wikiquote proverb harvester.

Why this exists: the wq_multilang lane parses top-level ``*`` bullets, which
works on de/en-style pages but yields (near) zero on fr.wikiquote, where the
proverb list wraps every entry in ``{{citation|citation=...}}`` templates.
This standalone lane (additive — touches no existing module):

  1. discovers the actual proverb page titles via the MediaWiki API
     (opensearch), seeded with known-good titles;
  2. fetches page wikitext via ``action=parse&prop=wikitext&format=json``;
  3. extracts and UNIONS citation templates, ``*`` and ``#`` lists, raw
     ``<P>/<BR>`` entries, and sentence-shaped transclusion templates. Mixed
     pages are common, so choosing one representation silently loses rows;
  4. exposes explicit ``{{:A-Z subpage}}`` targets for the wave-2 lane to
     follow (the Indonesian index stores all 1,300+ entries that way);
  5. cleans wikitext (nested templates, [[links]], refs, bold/italic,
     HTML entities), applies a script-aware 3/15-to-300-character range, dedupes
     within-run by normalized text, caps ~600 per language;
  6. writes records in the exact harvest_wq_multilang schema to a NEW
     corpora/harvest_wikiquote_citation_YYYYMMDD[_k].jsonl and APPENDS one
     receipt per language to jestry_out/harvest_receipts.jsonl.

Network etiquette: >=4s between requests, descriptive User-Agent with
contact, a single 60s-backoff retry on HTTP 429; a second 429 stops the
harvest (partial results are still written and receipted honestly).

    python3 harvest_wikiquote_citation.py            # fr + it, cap 600 each
    python3 harvest_wikiquote_citation.py --langs fr --limit 100
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPORA = ROOT / "corpora"
RECEIPTS = ROOT / "jestry_out" / "harvest_receipts.jsonl"

UA = {"User-Agent": "HumorVibesResearch/1.0 (research corpus; contact: amarel.taylor.s@gmail.com)"}
SLEEP_S = 4.0          # farm-wide wikimedia etiquette: never faster than this
RETRY_429_SLEEP_S = 60.0
MAX_PER_LANG = 600
MIN_LEN, MAX_LEN = 15, 300
LICENSE = "CC BY-SA (Wikiquote)"   # exact string used by the wq_multilang lane

_DENSE_SCRIPT = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af]")
_CITATION_NAMES = {"citation", "citazione", "цитат", "цитата", "quote"}
_TEXT_TEMPLATE_NAMES = {
    "ruby", "nihongo", "lang", "nowrap", "small", "smallcaps", "sc",
}
_NON_QUOTE_TEMPLATES = {
    "tema", "theme", "wikipedia", "commons", "indice", "index",
    "protetta", "protected", "sssk", "spiegazione", "explanation",
}

# Per-language lane config. `accept` = casefolded titles we take from
# discovery; `seeds` = known-good fallbacks if discovery misses them.
LANES = {
    "fr": {
        "host": "fr.wikiquote.org",
        "search": "proverbes",
        "accept": {"liste de proverbes", "proverbes français"},
        "seeds": ["Liste de proverbes"],
    },
    "it": {
        "host": "it.wikiquote.org",
        "search": "proverbi italiani",
        "accept": {"proverbi italiani"},
        "seeds": ["Proverbi italiani"],
    },
}


class RateLimited(RuntimeError):
    """Raised when a 429 persists after the single allowed retry."""


# ---------------------------------------------------------------- HTTP layer

_last_request_t = 0.0


def _polite_sleep() -> None:
    global _last_request_t
    wait = SLEEP_S - (time.monotonic() - _last_request_t)
    if wait > 0:
        time.sleep(wait)
    _last_request_t = time.monotonic()


def fetch_json(url: str) -> dict:
    """GET a JSON API URL with etiquette: >=4s spacing, one 429 retry."""
    for attempt in (0, 1):
        _polite_sleep()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt == 0:
                print(f"[rate] 429 from {urllib.parse.urlsplit(url).netloc}; "
                      f"sleeping {RETRY_429_SLEEP_S:.0f}s, retrying once", flush=True)
                time.sleep(RETRY_429_SLEEP_S)
                continue
            if exc.code == 429:
                raise RateLimited(f"429 persisted after retry: {url}") from exc
            raise
    raise RuntimeError("unreachable")


def api_opensearch(host: str, term: str) -> list[str]:
    url = (f"https://{host}/w/api.php?action=opensearch&format=json&limit=15"
           f"&search={urllib.parse.quote(term)}")
    data = fetch_json(url)
    return list(data[1]) if isinstance(data, list) and len(data) > 1 else []


def api_wikitext(host: str, page: str) -> tuple[str, str] | None:
    url = (f"https://{host}/w/api.php?action=parse&prop=wikitext&format=json"
           f"&redirects=1&page={urllib.parse.quote(page)}")
    data = fetch_json(url)
    if "error" in data:
        print(f"[warn] {host}: page {page!r} -> {data['error'].get('code')}", flush=True)
        return None
    parsed = data["parse"]
    return parsed["title"], parsed["wikitext"]["*"]


# ------------------------------------------------------------ wikitext parse

def _iter_top_templates(text: str):
    """Yield (name, content) for every top-level, brace-balanced {{...}}."""
    i, n = 0, len(text)
    while True:
        start = text.find("{{", i)
        if start == -1:
            return
        j, depth = start + 2, 1
        while j < n and depth:
            if text.startswith("{{", j):
                depth += 1
                j += 2
            elif text.startswith("}}", j):
                depth -= 1
                j += 2
            else:
                j += 1
        if depth:                       # unbalanced tail — stop scanning
            return
        content = text[start + 2:j - 2]
        name = content.split("|", 1)[0].strip().casefold()
        yield name, content
        i = j


def _split_top_args(content: str) -> list[str]:
    """Split template content on '|' at depth 0 for {{ }} and [[ ]]."""
    parts, cur, depth_t, depth_l, i = [], [], 0, 0, 0
    while i < len(content):
        two = content[i:i + 2]
        if two == "{{":
            depth_t += 1; cur.append(two); i += 2; continue
        if two == "}}":
            depth_t -= 1; cur.append(two); i += 2; continue
        if two == "[[":
            depth_l += 1; cur.append(two); i += 2; continue
        if two == "]]":
            depth_l -= 1; cur.append(two); i += 2; continue
        ch = content[i]
        if ch == "|" and depth_t == 0 and depth_l == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def _strip_templates(s: str) -> str:
    """Remove any remaining {{...}} blocks (brace-matched, nested-safe)."""
    out, i, n = [], 0, len(s)
    while i < n:
        if s.startswith("{{", i):
            j, depth = i + 2, 1
            while j < n and depth:
                if s.startswith("{{", j):
                    depth += 1; j += 2
                elif s.startswith("}}", j):
                    depth -= 1; j += 2
                else:
                    j += 1
            i = j if depth == 0 else n   # unbalanced: drop the tail
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def _template_value(content: str) -> str:
    """Render text-carrying templates and drop presentational metadata.

    Wikiquote editions use different wrappers for visible text. In particular,
    ``{{Ruby|漢字|かな}}`` contains the proverb in its first argument, while
    ``{{spiegazione|...}}`` is commentary and must not become part of it.
    Unknown templates remain dropped by :func:`_strip_templates`.
    """
    parts = _split_top_args(content)
    name = parts[0].strip().casefold()
    if name in _NON_QUOTE_TEMPLATES or name.startswith(":"):
        return ""
    named: dict[str, str] = {}
    positional: list[str] = []
    for part in parts[1:]:
        key, eq, val = part.partition("=")
        if eq and re.fullmatch(r"\s*[\w àâäéèêëîïôöùûüç'-]{1,30}\s*",
                               key, flags=re.UNICODE):
            named[key.strip().casefold()] = val
        else:
            positional.append(part)
    if name in _CITATION_NAMES:
        return (named.get("citation") or named.get("texte")
                or named.get("citazione") or named.get("цитат")
                or named.get("1") or (positional[0] if positional else ""))
    if name in _TEXT_TEMPLATE_NAMES:
        return named.get("1") or (positional[0] if positional else "")
    return ""


def _expand_text_templates(s: str) -> str:
    """Resolve innermost text wrappers before generic template removal."""
    inner = re.compile(r"\{\{([^{}]*)\}\}")
    for _ in range(24):
        changed = False

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            changed = True
            return _template_value(match.group(1))

        s2 = inner.sub(repl, s)
        s = s2
        if not changed or "{{" not in s:
            break
    return s


def clean_text(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*>.*$", "", s, flags=re.S)   # unclosed ref: drop tail
    s = re.sub(r"<\s*(?:br|p)\b[^>]*>", " ", s, flags=re.I)
    s = re.sub(r"</?[a-zA-Z][^>]*>", " ", s)          # <small>, ...
    s = _expand_text_templates(s)
    s = _strip_templates(s)
    s = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", s)   # [[a|b]] -> b
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)            # [[a]] -> a
    s = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", s)   # [url label] -> label
    s = re.sub(r"\[https?://\S+\]", "", s)
    s = s.replace("'''", "").replace("''", "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(" \t:;–—-")
    if len(s) >= 2 and ((s[0] == "«" and s[-1] == "»")
                        or (s[0] == '"' and s[-1] == '"')):
        s = s[1:-1].strip()
    return s


def looks_like_proverb(s: str) -> bool:
    # A four-character Chinese chengyu is a complete phrase. Applying the
    # Latin-script floor here recreates the exact silent CJK deletion fixed in
    # the wave-2 content screen.
    floor = 3 if _DENSE_SCRIPT.search(s) else MIN_LEN
    if not (floor <= len(s) <= MAX_LEN):
        return False
    low = s.casefold()
    if "http" in low or "www." in low:
        return False
    if s[0] in "#*=|{<[":
        return False
    if low.startswith(("catégorie:", "categoria:", "category:",
                       "file:", "fichier:", "image:")):
        return False
    return any(ch.isalpha() for ch in s)


def norm_key(s: str) -> str:
    return "".join(ch for ch in s.casefold() if ch.isalnum())


def quotes_from_citation_templates(wikitext: str) -> list[str]:
    quotes = []
    for name, content in _iter_top_templates(wikitext):
        if name not in _CITATION_NAMES:
            continue
        parts = _split_top_args(content)
        named: dict[str, str] = {}
        positional: list[str] = []
        for part in parts[1:]:
            key, eq, val = part.partition("=")
            if eq and re.fullmatch(r"\s*[\w àâäéèêëîïôöùûüç'-]{1,30}\s*",
                                   key, flags=re.UNICODE):
                named[key.strip().casefold()] = val
            else:
                positional.append(part)
        raw = named.get("citation") or named.get("texte") \
            or named.get("citazione") or named.get("цитат") \
            or named.get("1") \
            or (positional[0] if positional else "")
        text = clean_text(raw)
        if looks_like_proverb(text):
            quotes.append(text)
    return quotes


def quotes_from_lists(wikitext: str) -> list[str]:
    """Top-level bulleted OR numbered entries.

    Lithuanian Wikiquote alone has 1,500+ ``#`` entries. The old star-only
    parser returned zero without raising, which made a parser limitation look
    like an empty source.
    """
    quotes = []
    for line in wikitext.split("\n"):
        if not re.match(r"^[*#](?![*#])", line):
            continue
        text = clean_text(line[1:].strip())
        if looks_like_proverb(text):
            quotes.append(text)
    return quotes


def quotes_from_html_blocks(wikitext: str) -> list[str]:
    """Entries separated by legacy raw ``<P>``/``<BR>`` markup."""
    if not re.search(r"<(?:p|br)\b", wikitext, flags=re.I):
        return []
    chunks = re.split(r"</?p\b[^>]*>|<br\b[^>]*?/?>", wikitext,
                      flags=re.I)
    return [text for chunk in chunks
            if looks_like_proverb(text := clean_text(chunk))]


def quotes_from_sentence_templates(wikitext: str) -> list[str]:
    """Recover sentence-shaped, argument-free transclusion templates.

    Nynorsk Wikiquote represents ``Ein person er ...`` as ``{{Ein person er
    ...}}``. It is visible page content, not a template invocation with fields.
    Housekeeping templates are explicitly excluded.
    """
    out: list[str] = []
    for name, content in _iter_top_templates(wikitext):
        if ("|" in content or name.startswith(":") or name in _CITATION_NAMES
                or name in _TEXT_TEMPLATE_NAMES or name in _NON_QUOTE_TEMPLATES):
            continue
        text = clean_text(content)
        # Navigation templates such as ``{{Peribahasa Indonesia}}`` are two
        # title words, not sayings. Sentence-shaped Latin templates need at
        # least four words; dense-script phrases can legitimately be shorter.
        if (looks_like_proverb(text)
                and (len(text.split()) >= 4 or _DENSE_SCRIPT.search(text))):
            out.append(text)
    return out


def transcluded_pages(wikitext: str) -> list[str]:
    """Return explicit page transclusions in source order, deduplicated."""
    pages: list[str] = []
    seen: set[str] = set()
    # Preserve source casing: MediaWiki normalises the first character but page
    # title matching beyond it can be case-sensitive.
    for match in re.finditer(r"\{\{\s*:([^{}|]+?)(?:\|[^{}]*)?\}\}", wikitext):
        page = match.group(1).strip()
        key = page.casefold()
        if page and key not in seen:
            seen.add(key)
            pages.append(page)
    return pages


def extract_page(wikitext: str) -> tuple[list[str], str]:
    """Union every representation present; never discard a mixed page arm."""
    arms = [
        ("citation-templates", quotes_from_citation_templates(wikitext)),
        ("lists", quotes_from_lists(wikitext)),
        ("html-blocks", quotes_from_html_blocks(wikitext)),
        ("sentence-templates", quotes_from_sentence_templates(wikitext)),
    ]
    out: list[str] = []
    seen: set[str] = set()
    modes: list[str] = []
    for mode, rows in arms:
        if not rows:
            continue
        modes.append(mode)
        for row in rows:
            key = norm_key(row)
            if key and key not in seen:
                seen.add(key)
                out.append(row)
    return out, "+".join(modes) if modes else "none"


# ------------------------------------------------------------------ file IO

def next_corpus_path(day: str) -> Path:
    base = CORPORA / f"harvest_wikiquote_citation_{day}.jsonl"
    if not base.exists():
        return base
    k = 2
    while True:
        cand = CORPORA / f"harvest_wikiquote_citation_{day}_{k}.jsonl"
        if not cand.exists():
            return cand
        k += 1


def utc_ts() -> str:
    # Same "YYYY-MM-DDTHH:MM:SS" shape as existing receipts, real UTC time.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# --------------------------------------------------------------------- main

def harvest_lang(lang: str, cfg: dict, cap: int):
    """Return (records, stats). Never raises RateLimited past a lane —
    caller decides; partial results are returned via the exception arg."""
    titles = api_opensearch(cfg["host"], cfg["search"])
    discovered = [t for t in titles if t.casefold() in cfg["accept"]]
    pages = list(dict.fromkeys(discovered + cfg["seeds"]))
    print(f"[{lang}] discovery: api={titles!r} -> pages={pages!r}", flush=True)

    records, seen = [], set()
    fetched = dupes = 0
    per_page = []
    for page in pages:
        if len(records) >= cap:
            break
        got = api_wikitext(cfg["host"], page)
        if got is None:
            per_page.append((page, 0, "missing"))
            continue
        title, wikitext = got
        quotes, mode = extract_page(wikitext)
        kept = 0
        for q in quotes:
            fetched += 1
            key = norm_key(q)
            if key in seen:
                dupes += 1
                continue
            if len(records) >= cap:
                break
            seen.add(key)
            records.append({
                "source": f"{lang}.wikiquote:{title}",
                "license": LICENSE,
                "text": q,
                "meta": {"language": lang, "page": title},
            })
            kept += 1
        per_page.append((title, kept, mode))
        print(f"[{lang}] {title!r}: mode={mode} candidates={len(quotes)} "
              f"kept={kept}", flush=True)
    stats = {"fetched": fetched, "new": len(records), "exact_dupes": dupes,
             "pages": per_page,
             "arg": lang + ":" + "+".join(p for p, _, _ in per_page)}
    return records, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--langs", default="fr,it",
                    help="comma list from: " + ",".join(LANES))
    ap.add_argument("--limit", type=int, default=MAX_PER_LANG,
                    help="max records per language")
    args = ap.parse_args()
    langs = [x.strip() for x in args.langs.split(",") if x.strip()]
    for lang in langs:
        if lang not in LANES:
            ap.error(f"unknown lang {lang!r}")

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = next_corpus_path(day)
    all_records: list[dict] = []
    lane_stats: dict[str, dict] = {}
    stopped = None
    for lang in langs:
        try:
            records, stats = harvest_lang(lang, LANES[lang], args.limit)
        except RateLimited as exc:
            stopped = str(exc)
            print(f"[STOP] rate-limited; halting harvest: {exc}", flush=True)
            break
        all_records.extend(records)
        lane_stats[lang] = stats

    if not all_records:
        print("[done] nothing harvested; no corpus file written", flush=True)
        return 1 if stopped else 0

    created = utc_ts()
    header = {"_meta": {"name": out_path.stem, "n": len(all_records),
                        "created": created,
                        "note": "provenance per record; licensing-clean sources only"}}
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(header, ensure_ascii=False) + "\n")
        for rec in all_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[write] {out_path} n={len(all_records)}", flush=True)

    receipt_lines = []
    with RECEIPTS.open("a", encoding="utf-8") as fh:
        for lang, stats in lane_stats.items():
            receipt = {
                "receipt_type": "jestry_harvest",
                "receipt_version": 1,
                "ts": utc_ts(),
                "lane": "wikiquote_citation",
                "arg": stats["arg"],
                "fetched": stats["fetched"],
                "new": stats["new"],
                "exact_dupes": stats["exact_dupes"],
                "near_dupes": 0,
                "dedupe": True,
                "semantic": False,
                "licenses": [LICENSE],
                "path": str(out_path),
            }
            line = json.dumps(receipt, ensure_ascii=False)
            fh.write(line + "\n")
            receipt_lines.append(line)
    print("[receipts] appended:", flush=True)
    for line in receipt_lines:
        print("  " + line, flush=True)

    # Self-check: re-read, assert valid JSONL, show 3 samples per language.
    with out_path.open(encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh]     # raises on invalid JSONL
    assert lines[0]["_meta"]["n"] == len(lines) - 1, "header n mismatch"
    for lang in lane_stats:
        samples = [l for l in lines[1:] if l["meta"]["language"] == lang][:3]
        print(f"[samples:{lang}]", flush=True)
        for s in samples:
            print("  " + json.dumps(s, ensure_ascii=False), flush=True)
    print(f"[selfcheck] OK: {len(lines) - 1} records valid JSONL", flush=True)
    if stopped:
        print(f"[WARNING] harvest stopped early (rate limit): {stopped}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
