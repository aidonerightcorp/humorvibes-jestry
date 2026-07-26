"""Wave-2 supply harvester: spec-driven lanes over many more public sources.

Law 1 applied again: this module does NOT rebuild dedupe, receipts, or the
same-day filename bump — it registers new lane callables into
`harvest_supply.LANES` and calls `harvest_supply.harvest`, so every wave-2
record passes the identical provenance/precedent gates as wave 1.

What is new here is the TRANSPORT, which wave 1 did not need:

1. BACKOFF      HuggingFace's datasets-server and the Wikimedia farm both
                answer 429 under load; wave 1 lost whole lanes to that. `_get`
                honours Retry-After, backs off exponentially, and reports the
                final status so a rate-limited lane is receipted as
                rate-limited rather than as empty.
2. SPECS        A source is a dict, not a function. Adding a verified dataset
                is a one-line append to HF_SPECS; the paging, field mapping,
                language stamping, and licence carry-through are shared.
3. SCREENING    Bulk community corpora carry slurs. `screen()` drops records on
                a conservative term list before they ever reach the index.

    python3 harvest_wave2.py list
    python3 harvest_wave2.py hf --arg hahackathon --limit 500
    python3 harvest_wave2.py hf --arg all --limit 200
    python3 harvest_wave2.py wikiquote2 --arg "ja:日本語のことわざ" --limit 400
    python3 harvest_wave2.py gutendex --arg "wit and humor" --limit 300
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

import harvest_supply
import ingest
from ingest import UA

# ---------------------------------------------------------------------------
# transport: the thing wave 1 was missing
# ---------------------------------------------------------------------------
LAST_STATUS: dict[str, Any] = {}

# ---------------------------------------------------------------------------
# Crash/timeout insurance.
#
# `harvest_supply.harvest` calls a lane, gets a finished list, then writes. A
# lane that is killed mid-run therefore returns NOTHING, and hours of fetching
# evaporate. That cost two full runs on 2026-07-26 (a 90-minute study and a
# 60-minute 11-dataset pull), so lanes now append each record to a partial file
# as it is produced. `harvest_wave2.py recover` feeds those partials back
# through the SAME dedupe-and-receipt path, so recovered rows are not privileged
# over freshly fetched ones.
# ---------------------------------------------------------------------------
_PARTIAL_FH: Any = None
_PARTIAL_PATH: Path | None = None


def open_partial(lane: str, arg: str) -> None:
    global _PARTIAL_FH, _PARTIAL_PATH
    d = Path(__file__).resolve().parent / "jestry_out"
    d.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", arg)[:60]
    _PARTIAL_PATH = d / f"partial_{lane}_{safe}_{stamp}.jsonl"
    _PARTIAL_FH = _PARTIAL_PATH.open("a", encoding="utf-8")


def emit(rec: dict[str, Any]) -> dict[str, Any]:
    """Append a record to the partial file, then return it unchanged."""
    if _PARTIAL_FH is not None:
        _PARTIAL_FH.write(json.dumps(rec, ensure_ascii=False) + "\n")
        _PARTIAL_FH.flush()
    return rec


def close_partial(*, completed: bool = False) -> None:
    """Close the crash checkpoint; discard it only after a finished harvest.

    A raised exception leaves the partial in place for ``recover``. Once the
    normal harvest has written its corpus file and receipt, retaining the same
    rows as a recovery candidate only wastes disk and makes a later recovery
    re-read already committed data.
    """
    global _PARTIAL_FH, _PARTIAL_PATH
    if _PARTIAL_FH is not None:
        _PARTIAL_FH.close()
        _PARTIAL_FH = None
    if completed and _PARTIAL_PATH is not None:
        _PARTIAL_PATH.unlink(missing_ok=True)
    _PARTIAL_PATH = None


def _get(url: str, *, timeout: int = 30, tries: int = 4,
         headers: dict[str, str] | None = None) -> bytes | None:
    """GET with Retry-After-aware backoff. Returns None after `tries`.

    A 429 from datasets-server or wikimedia is a THROTTLE, not a dead source;
    wave 1 recorded several live sources as empty because it could not tell the
    difference. The final observed status is left in LAST_STATUS for receipts.
    """
    hdrs = dict(UA) | {"Accept": "application/json"} | (headers or {})
    delay = 2.0
    for attempt in range(tries):
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                LAST_STATUS[url] = r.status
                return r.read()
        except urllib.error.HTTPError as e:
            LAST_STATUS[url] = e.code
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                wait = delay
                ra = e.headers.get("Retry-After") if e.headers else None
                if ra:
                    try:
                        wait = max(wait, float(ra))
                    except ValueError:
                        pass
                time.sleep(min(wait, 60.0))
                delay *= 2
                continue
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            LAST_STATUS[url] = repr(e)
            if attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return None
    return None


def _get_json(url: str, **kw: Any) -> Any:
    raw = _get(url, **kw)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# screening: bulk community corpora carry slurs
# ---------------------------------------------------------------------------
_SLUR_RE = re.compile(
    r"\b(n[i1]gg?[e3]r|f[a4]gg?[o0]t|k[i1]k[e3]|sp[i1]c|ch[i1]nk|tr[a4]nny|"
    r"w[e3]tb[a4]ck|r[e3]t[a4]rd|c[o0]{2}n)\b", re.IGNORECASE)


# Han / kana / hangul. A character in these scripts carries roughly a whole
# morpheme, so a length floor tuned to English alphabetic text is wrong by a
# factor of four or more against them.
_DENSE_SCRIPT = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿가-힯]")

_LANGUAGE_CODES = {
    "arabic": "ar", "chinese": "zh", "czech": "cs", "danish": "da",
    "dutch": "nl", "english": "en", "finnish": "fi", "french": "fr",
    "german": "de", "italian": "it", "japanese": "ja", "korean": "ko",
    "polish": "pl", "portuguese": "pt", "russian": "ru", "spanish": "es",
    "swedish": "sv", "urdu": "ur", "vietnamese": "vi", "yoruba": "yo",
}


def normalize_language(value: Any) -> str:
    """Return an ISO-like code when a source uses an English language name."""
    raw = str(value or "unknown").strip()
    return _LANGUAGE_CODES.get(raw.casefold(), raw.casefold().replace("_", "-"))


def min_chars(text: str) -> int:
    """Minimum plausible length, by script.

    Found 2026-07-26: a flat `len < 8` floor was silently discarding most
    Chinese content. A chengyu is FOUR characters (一箭双雕), and xiehouyu and
    Japanese yojijukugo are similarly dense, so an English-shaped threshold
    deleted 15,000+ of 16,920 Chinese idioms while looking like a safety check.
    """
    return 3 if _DENSE_SCRIPT.search(text) else 8


def screen(text: str) -> bool:
    """True if the record is safe to index. Conservative on slurs: a false drop
    costs one joke, a false keep poisons a public dataset export. NOT
    conservative on length — see min_chars."""
    if not text or len(text.strip()) < min_chars(text):
        return False
    return not _SLUR_RE.search(text)


# ---------------------------------------------------------------------------
# HuggingFace datasets-server lane
# ---------------------------------------------------------------------------
# Each spec: how to turn rows into records. `text` may be a single field name or
# a tuple of (setup_field, punch_field). `labels` names columns worth keeping as
# the validation signal (graded funniness, disagreement, offence).
HF_SPECS: dict[str, dict[str, Any]] = {}
HF_TRANSPORT = "auto"
HF_CACHE = Path(__file__).resolve().parent / "data_cache" / "hf_parquet"
_HF_LOCATION_CACHE: dict[str, tuple[str, str]] = {}


def hf_resolve(repo: str) -> list[tuple[str, str]]:
    """(config, split) pairs actually served for `repo`.

    Guessing 'default' is wrong often enough to matter: HaHackathon serves
    config='train'/split='train' and answers 500 for config='default', which
    reads exactly like a dead dataset. Resolve, never guess.
    """
    data = _get_json("https://datasets-server.huggingface.co/splits?dataset="
                     + urllib.parse.quote(repo, safe=""))
    return [(s["config"], s["split"]) for s in (data or {}).get("splits", [])]


def hf_probe(repo: str, config: str | None = None, split: str | None = None) -> dict[str, Any]:
    """Columns + one example row, so a spec's field names can be checked
    against reality before a bulk pull spends an hour on the wrong key."""
    if config is None or split is None:
        pairs = hf_resolve(repo)
        if not pairs:
            return {"repo": repo, "error": "no splits", "status": LAST_STATUS}
        train = [p for p in pairs if p[1] == "train"] or pairs
        config, split = train[0]
    url = ("https://datasets-server.huggingface.co/first-rows"
           f"?dataset={urllib.parse.quote(repo, safe='')}"
           f"&config={urllib.parse.quote(config, safe='')}"
           f"&split={urllib.parse.quote(split, safe='')}")
    data = _get_json(url)
    if not data:
        return {"repo": repo, "config": config, "split": split,
                "error": "first-rows failed", "status": LAST_STATUS.get(url)}
    cols = [f["name"] for f in data.get("features", [])]
    rows = data.get("rows", [])
    example = rows[0].get("row", {}) if rows else {}
    return {"repo": repo, "config": config, "split": split,
            "columns": cols,
            "example": {k: str(v)[:160] for k, v in example.items()}}


def hf_size(repo: str, config: str, split: str) -> int | None:
    """Authoritative row count. Without it, a transient 429 mid-pull is
    indistinguishable from end-of-data and the lane silently truncates — that
    is exactly how a 8,000-row split first came back as 3,195."""
    data = _get_json("https://datasets-server.huggingface.co/size?dataset="
                     + urllib.parse.quote(repo, safe=""))
    for s in (data or {}).get("size", {}).get("splits", []):
        if s.get("config") == config and s.get("split") == split:
            return s.get("num_rows")
    return None


def _hf_location(key: str) -> tuple[str, str] | None:
    """Resolve and cache the config/split selected for a source spec."""
    if key in _HF_LOCATION_CACHE:
        return _HF_LOCATION_CACHE[key]
    spec = HF_SPECS[key]
    config, split = spec.get("config"), spec.get("split")
    if not config or not split:
        pairs = hf_resolve(spec["repo"])
        if not pairs:
            return None
        train = [pair for pair in pairs if pair[1] == "train"] or pairs
        config, split = train[0]
    location = str(config), str(split)
    _HF_LOCATION_CACHE[key] = location
    return location


def hf_parquet_files(repo: str, config: str, split: str) -> list[dict[str, Any]]:
    """Converted parquet shards published by HuggingFace's dataset server."""
    data = _get_json("https://datasets-server.huggingface.co/parquet?dataset="
                     + urllib.parse.quote(repo, safe=""))
    return [f for f in (data or {}).get("parquet_files", [])
            if f.get("config") == config and f.get("split") == split
            and f.get("url")]


def _download_parquet(info: dict[str, Any]) -> Path | None:
    """Download one shard atomically, resuming a partial file when possible."""
    url = str(info["url"])
    expected = int(info.get("size") or 0)
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(info.get("filename") or "data.parquet"))
    HF_CACHE.mkdir(parents=True, exist_ok=True)
    dest = HF_CACHE / f"{digest}_{name}"
    if dest.exists() and (not expected or dest.stat().st_size == expected):
        return dest
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(4):
        start = part.stat().st_size if part.exists() else 0
        headers = dict(UA)
        if start:
            headers["Range"] = f"bytes={start}-"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                # A server may ignore Range and return 200. Truncate in that
                # case; appending a complete response would corrupt the shard.
                append = start > 0 and getattr(resp, "status", 200) == 206
                with part.open("ab" if append else "wb") as fh:
                    while chunk := resp.read(1024 * 1024):
                        fh.write(chunk)
            if expected and part.stat().st_size != expected:
                if part.stat().st_size > expected:
                    part.unlink()
                raise OSError(
                    f"shard length {part.stat().st_size if part.exists() else 0} != {expected}")
            os.replace(part, dest)
            return dest
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            LAST_STATUS[url] = repr(exc)
            if attempt == 3:
                return None
            time.sleep(2 ** attempt)
    return None


def _record_from_hf_row(spec: dict[str, Any], repo: str, config: str,
                        split: str, row: dict[str, Any],
                        source_offset: int) -> dict[str, Any] | None:
    tf = spec["text"]
    labels = spec.get("labels", [])
    if isinstance(tf, (list, tuple)):
        parts = [str(row.get(field, "")).strip() for field in tf]
        body = " ".join(part for part in parts if part)
        extra = {field: row.get(field) for field in tf if row.get(field)}
    else:
        body = str(row.get(tf, "")).strip()
        extra = {}
    body = " ".join(body.split())
    if not screen(body):
        return None
    language = spec.get("lang", "en")
    language_field = spec.get("language_field")
    if language_field and row.get(language_field):
        language = row[language_field]
    language = normalize_language(language)
    meta = {"config": config, "split": split,
            "language": language,
            # This makes a partial file a true resume point, not merely a copy
            # of accepted rows whose upstream cursor has been lost.
            "_hf_row_offset": source_offset} | extra
    for label in labels:
        if label in row and row[label] is not None:
            if label == language_field:
                meta["language_source_value"] = row[label]
            else:
                meta[label] = row[label]
    translation_field = spec.get("translation")
    if translation_field and row.get(translation_field):
        meta["translation_en"] = row[translation_field]
    rec: dict[str, Any] = {
        "source": f"hf:{repo}",
        "license": spec.get("license", "per dataset card (verify before redistribution)"),
        "text": body,
        "meta": meta,
    }
    grade = spec.get("grade")
    if grade and grade in row and row[grade] is not None:
        rec["funniness_label"] = row[grade]
    return rec


def hf_spec_fetch_parquet(key: str, limit: int, start_offset: int = 0
                          ) -> list[dict[str, Any]] | None:
    """Fast, restartable bulk path. ``None`` means fall back to rows API."""
    if limit <= 0:
        return []
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return None
    spec = HF_SPECS[key]
    repo = spec["repo"]
    location = _hf_location(key)
    if location is None:
        return None
    config, split = location
    shards = hf_parquet_files(repo, config, split)
    if not shards:
        return None
    out: list[dict[str, Any]] = []
    global_offset = 0
    for info in shards:
        path = _download_parquet(info)
        if path is None:
            return None
        parquet = pq.ParquetFile(path)
        shard_rows = parquet.metadata.num_rows
        if global_offset + shard_rows <= start_offset:
            global_offset += shard_rows
            continue
        for batch in parquet.iter_batches(batch_size=4096):
            for row in batch.to_pylist():
                source_offset = global_offset
                global_offset += 1
                if source_offset < start_offset:
                    continue
                rec = _record_from_hf_row(
                    spec, repo, config, split, row, source_offset)
                if rec is not None:
                    out.append(emit(rec))
                    if len(out) >= limit:
                        return out
        # ``global_offset`` was advanced per row unless the whole shard was
        # skipped above; assert catches pyarrow metadata/iteration drift.
        assert global_offset >= shard_rows
    return out


def _hf_rows(repo: str, config: str, split: str, offset: int,
             length: int) -> tuple[list[dict[str, Any]], bool]:
    """Returns (rows, ok). ok=False means the REQUEST failed; an empty list
    with ok=True means the split is genuinely exhausted. Collapsing those two
    into `[]` is what truncated earlier pulls."""
    url = ("https://datasets-server.huggingface.co/rows"
           f"?dataset={urllib.parse.quote(repo, safe='')}"
           f"&config={urllib.parse.quote(config, safe='')}"
           f"&split={urllib.parse.quote(split, safe='')}"
           f"&offset={offset}&length={min(length, 100)}")
    data = _get_json(url)
    if data is None:
        return [], False
    return [r.get("row", {}) for r in data.get("rows", [])], True


def hf_spec_fetch(key: str, limit: int, start_offset: int = 0) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    spec = HF_SPECS[key]
    repo = spec["repo"]
    location = _hf_location(key)
    if location is None:
        print(f"  ! {repo}: no splits served (status "
              f"{LAST_STATUS and list(LAST_STATUS.values())[-1]})")
        return []
    config, split = location
    if HF_TRANSPORT in ("auto", "parquet"):
        fast = hf_spec_fetch_parquet(key, limit, start_offset)
        if fast is not None:
            return fast
        if HF_TRANSPORT == "parquet":
            print(f"  ! {repo}: parquet unavailable; falling back to rows API")
    out: list[dict[str, Any]] = []
    offset = max(int(spec.get("offset", 0)), start_offset)
    total = hf_size(repo, config, split)
    hard_stop = min(limit, (total - offset)) if total else limit
    failures = 0
    while len(out) < limit and offset < (total or 10 ** 9):
        rows, ok = _hf_rows(repo, config, split, offset, min(100, limit - len(out)))
        if not ok:
            failures += 1
            if failures > 6:
                print(f"  ! {repo}: giving up at offset {offset} after 6 failed pages "
                      f"({len(out)}/{hard_stop} rows) — RATE-LIMITED, not exhausted")
                break
            time.sleep(5.0 * failures)
            continue
        failures = 0
        if not rows:
            break
        page_start = offset
        for i, row in enumerate(rows):
            rec = _record_from_hf_row(
                spec, repo, config, split, row, page_start + i)
            if rec is not None:
                out.append(emit(rec))
        offset += len(rows)
        time.sleep(float(spec.get("pace", 1.0)))
    return out[:limit]


def _waterfill(available: list[int], budget: int) -> list[int]:
    """Fair caps that redistribute unused capacity from small sources."""
    caps = [0] * len(available)
    active = set(range(len(available)))
    remaining = min(budget, sum(max(0, n) for n in available))
    while active and remaining > 0:
        share = (remaining + len(active) - 1) // len(active)
        small = [i for i in active if available[i] <= share]
        if small:
            for i in small:
                caps[i] = available[i]
                remaining -= caps[i]
                active.remove(i)
            continue
        ordered = sorted(active)
        base, extra = divmod(remaining, len(ordered))
        for pos, i in enumerate(ordered):
            caps[i] = base + (1 if pos < extra else 0)
        remaining = 0
    return caps


def hf_lane(limit: int = 200, arg: str = "") -> list[dict[str, Any]]:
    tokens = list(HF_SPECS) if arg in ("", "all") else [k.strip() for k in arg.split(",")]
    parsed: list[tuple[str, int]] = []
    for token in tokens:
        key, marker, raw_offset = token.partition("@")
        try:
            offset = int(raw_offset) if marker else 0
        except ValueError:
            print(f"  ! invalid resume offset in '{token}' (expected key@ROW)")
            continue
        parsed.append((key, max(0, offset)))
    out: list[dict[str, Any]] = []
    available: list[int] = []
    for key, offset in parsed:
        if key not in HF_SPECS:
            available.append(0)
            continue
        location = _hf_location(key)
        total = hf_size(HF_SPECS[key]["repo"], *location) if location else None
        available.append(max(0, (total if total is not None else limit) - offset))
    caps = _waterfill(available, limit)
    carry = 0
    for pos, (k, offset) in enumerate(parsed):
        if k not in HF_SPECS:
            print(f"  ! unknown hf spec '{k}'")
            continue
        cap = min(available[pos], caps[pos] + carry)
        if cap <= 0:
            print(f"  hf:{k:<28}       0 rows  (source exhausted at {offset:,})")
            continue
        got = hf_spec_fetch(k, cap, offset)
        carry = max(0, cap - len(got))
        print(f"  hf:{k:<28} {len(got):>7} rows  "
              f"(raw offset {offset:,}; cap {cap:,}; {HF_TRANSPORT})")
        out.extend(got)
    return out[:limit]


# ---------------------------------------------------------------------------
# Wikiquote lane 2: reuses the {{citation}}-aware parser from wave 1
# ---------------------------------------------------------------------------
def wikiquote2_lane(limit: int = 400, arg: str = "") -> list[dict[str, Any]]:
    """arg = ``lang:Page Title`` or a comma-separated list.

    Explicit ``{{:subpage}}`` transclusions are followed breadth-first, with a
    hard page cap. Indonesian Wikiquote stores its A-Z proverb collection in
    24 such pages; treating the index page as the corpus returned zero rows.
    Only explicit transclusions are followed, so ordinary article links cannot
    turn a bounded harvest into a site crawl.
    """
    import harvest_wikiquote_citation as hwc

    targets = [t.strip() for t in arg.split(",") if t.strip()]
    out: list[dict[str, Any]] = []
    per = max(1, limit // max(1, len(targets)))
    for t in targets:
        lang, _, page = t.partition(":")
        lang, page = lang.strip(), page.strip()
        queue = [page]
        seen_pages: set[str] = set()
        kept = 0
        while queue and kept < per and len(seen_pages) < 64:
            requested = queue.pop(0)
            page_key = requested.casefold()
            if page_key in seen_pages:
                continue
            seen_pages.add(page_key)
            got = hwc.api_wikitext(f"{lang}.wikiquote.org", requested)
            if not got:
                print(f"  wq:{lang}:{requested} -> no wikitext")
                continue
            title, wikitext = got
            quotes, how = hwc.extract_page(wikitext)
            page_kept = 0
            for q in quotes:
                if kept >= per:
                    break
                if not screen(q):
                    continue
                out.append(emit({
                    "source": f"{lang}.wikiquote:{title}",
                    "license": "CC BY-SA (Wikiquote)",
                    "text": q,
                    "meta": {"language": lang, "page": title,
                             "extractor": how},
                }))
                kept += 1
                page_kept += 1
            children = hwc.transcluded_pages(wikitext)
            queue.extend(p for p in children if p.casefold() not in seen_pages)
            print(f"  wq:{lang}:{title:<40} {page_kept:>5} quotes ({how}); "
                  f"{len(children)} explicit subpages")
            hwc._polite_sleep()
        if queue:
            print(f"  ! wq:{lang}:{page}: stopped at the 64-page safety cap")
    return out[:limit]


# ---------------------------------------------------------------------------
# Gutendex lane: resolve public-domain jest books by SEARCH, not by remembered
# id (wave 1 lost time to hand-remembered ids that were wrong).
# ---------------------------------------------------------------------------
def gutendex_lane(limit: int = 300, arg: str = "wit and humor") -> list[dict[str, Any]]:
    terms = [t.strip() for t in arg.split(",") if t.strip()] or ["wit and humor"]
    out: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for term in terms:
        data = _get_json("https://gutendex.com/books?search="
                         + urllib.parse.quote(term) + "&languages=en")
        for book in (data or {}).get("results", [])[:6]:
            bid = book.get("id")
            if not bid or bid in seen_ids:
                continue
            seen_ids.add(bid)
            title = book.get("title", "")
            try:
                got = ingest.gutenberg_fetch(str(bid), max_items=max(20, limit // 4))
            except Exception as e:
                print(f"  gutenberg:{bid} {title[:40]} -> {e}")
                continue
            kept = [g | {"meta": dict(g.get("meta", {}),
                                      title=title, language="en", gutendex_term=term)}
                    for g in got if screen(g.get("text", ""))]
            print(f"  gutenberg:{bid:<6} {title[:44]:<44} {len(kept):>5} items")
            out.extend(kept)
            if len(out) >= limit:
                return out[:limit]
            time.sleep(1.0)
    return out[:limit]


# ---------------------------------------------------------------------------
# Generic keyless-API lane
# ---------------------------------------------------------------------------
# Each spec: url template with {i}, a extractor path, source + license labels.
API_SPECS: dict[str, dict[str, Any]] = {}


def _dig(obj: Any, path: str) -> Any:
    for part in path.split("."):
        if part == "":
            continue
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list) and part.isdigit():
            obj = obj[int(part)] if int(part) < len(obj) else None
        else:
            return None
    return obj


def api_lane(limit: int = 200, arg: str = "") -> list[dict[str, Any]]:
    keys = list(API_SPECS) if arg in ("", "all") else [k.strip() for k in arg.split(",")]
    out: list[dict[str, Any]] = []
    per = max(1, limit // max(1, len(keys)))
    for k in keys:
        if k not in API_SPECS:
            print(f"  ! unknown api spec '{k}'")
            continue
        spec = API_SPECS[k]
        got: list[dict[str, Any]] = []
        page = int(spec.get("start", 1))
        stalls = 0
        while len(got) < per and stalls < 3:
            url = spec["url"].format(i=page, n=min(spec.get("batch", 20), per - len(got)))
            data = _get_json(url, headers=spec.get("headers"))
            rows = _dig(data, spec.get("rows", "")) if spec.get("rows") else data
            if rows is None:
                stalls += 1
                page += 1
                continue
            if isinstance(rows, dict):
                rows = [rows]
            if not rows:
                stalls += 1
                page += 1
                continue
            before = len(got)
            for row in rows:
                if isinstance(spec["text"], (list, tuple)):
                    parts = [str(_dig(row, f) or "").strip() for f in spec["text"]]
                    text = " ".join(p for p in parts if p)
                    extra = {f.split(".")[-1]: _dig(row, f) for f in spec["text"]}
                else:
                    text = str(_dig(row, spec["text"]) or "").strip()
                    extra = {}
                text = " ".join(text.split())
                if not screen(text):
                    continue
                got.append({"source": spec["source"], "license": spec["license"],
                            "text": text,
                            "meta": {"language": spec.get("lang", "en")} | extra})
            if len(got) == before:
                stalls += 1
            page += 1
            time.sleep(float(spec.get("pace", 0.5)))
        print(f"  api:{k:<28} {len(got):>6} items")
        out.extend(got)
    return out


# ---------------------------------------------------------------------------
# New Yorker caption-contest ANNOTATION layers.
#
# The raw rankings were already staged locally, but the layer that matters most
# was never fetched. For 705 contests, three crowd workers each wrote:
#   image_description         what the scene IS      -> the expectation
#   image_uncanny_description what is WRONG with it  -> the violation
# and 651 captions carry a free-text explanation of why they work -> the repair.
#
# That is this project's whole model of a joke, annotated by humans, in 0.4 MB.
# Nothing else found in the sweep separates expectation from violation this
# explicitly, so these records are stamped as frame-carrying supply.
# ---------------------------------------------------------------------------
NYC_ZIPS = {
    "annotations": "all_newyorker_contest_annotations.json.zip",
    "explanations": "joke_explanations_flat.json.zip",
}
NYC_LICENSE = "CC BY 4.0 (jmhessel/caption_contest_corpus)"


def nyc_lane(limit: int = 5000, arg: str = "") -> list[dict[str, Any]]:
    """arg: 'finalists', 'frames', 'explanations', or '' for all three."""
    import zipfile
    from pathlib import Path

    cache = Path(__file__).resolve().parent / "data_cache"
    which = [w_.strip() for w_ in arg.split(",") if w_.strip()] or \
        ["finalists", "frames", "explanations"]
    out: list[dict[str, Any]] = []

    ann_path = cache / NYC_ZIPS["annotations"]
    if ann_path.exists() and ({"finalists", "frames"} & set(which)):
        zf = zipfile.ZipFile(ann_path)
        contests = json.loads(zf.read(zf.namelist()[0]).decode("utf-8"))
        for cnum, c in contests.items():
            hits = (c.get("mturk_annotations") or {}).get("description_hit") or []
            # keep every annotator's read: disagreement about WHAT IS WRONG is
            # itself signal, so they are not collapsed to one description here
            scene = [h.get("image_description") for h in hits if h.get("image_description")]
            uncanny = [h.get("image_uncanny_description") for h in hits
                       if h.get("image_uncanny_description")]
            frame_meta = {
                "contest": c.get("contest_number", cnum),
                "contest_type": c.get("contest_type", ""),
                "image_description": scene[0] if scene else "",
                "image_uncanny_description": uncanny[0] if uncanny else "",
                "n_annotators": len(hits),
                "scene_variants": scene[1:],
                "uncanny_variants": uncanny[1:],
                "language": "en",
            }
            if "finalists" in which:
                for rank, cap in enumerate(c.get("official_newyorker_finalists") or [], 1):
                    cap = " ".join(str(cap).split()).strip('"“”')
                    if not screen(cap):
                        continue
                    out.append({
                        "source": "New Yorker caption contest (official finalists)",
                        "license": NYC_LICENSE,
                        "text": cap,
                        "meta": frame_meta | {"editor_rank": rank,
                                              "oracle": "official_newyorker_finalists"},
                    })
            if "frames" in which and uncanny:
                # the frame itself, as supply: a stated expectation plus the
                # stated way it is broken, with no punchline attached
                txt = f"{frame_meta['image_description']} {frame_meta['image_uncanny_description']}"
                txt = " ".join(txt.split())
                if screen(txt):
                    out.append({
                        "source": "New Yorker caption contest (scene/uncanny annotation)",
                        "license": NYC_LICENSE,
                        "text": txt,
                        "meta": frame_meta | {"record_kind": "frame",
                                              "humor_hook": frame_meta["image_uncanny_description"]},
                    })
            if len(out) >= limit:
                return out[:limit]

    exp_path = cache / NYC_ZIPS["explanations"]
    if exp_path.exists() and "explanations" in which:
        zf = zipfile.ZipFile(exp_path)
        rows = json.loads(zf.read(zf.namelist()[0]).decode("utf-8"))
        for row in rows:
            cap = " ".join(str(row.get("caption", "")).split())
            if not screen(cap):
                continue
            out.append({
                "source": "New Yorker caption contest (explained captions)",
                "license": NYC_LICENSE,
                "text": cap,
                "meta": {"language": "en",
                         "contest": row.get("contest_number"),
                         "explanation": row.get("explanation", ""),
                         "n_explanation_tokens": row.get("n_expl_toks"),
                         "record_kind": "explained_joke"},
            })
            if len(out) >= limit:
                break
    return out[:limit]


# ---------------------------------------------------------------------------
# The full nextml caption-contest archive: 385 contests, not the 13 that were
# staged locally. Each summary CSV gives, per caption, the mean rating AND the
# raw three-bin histogram (not_funny / somewhat_funny / funny) AND a precision
# (confidence-interval width).
#
# The histogram is the point. A mean of 1.5 can come from unanimous mild
# amusement or from half the room loving it and half hating it, and those are
# different jokes. Only the bins can tell them apart.
#
# Two sampler variants exist per contest (LilUCB adaptive, RoundRobin uniform).
# Both are kept and stamped; where a caption appears in both, dedupe keeps the
# first and the sampler field records which regime that number came from.
# ---------------------------------------------------------------------------
NEXTML_RAW = ("https://raw.githubusercontent.com/nextml/caption-contest-data/"
              "gh-pages/summaries/")


def nextml_lane(limit: int = 2_000_000, arg: str = "") -> list[dict[str, Any]]:
    """arg: optional comma list of contest numbers; default = every contest."""
    import csv
    import io

    listing = _get("https://api.github.com/repos/nextml/caption-contest-data/"
                   "git/trees/gh-pages?recursive=1")
    names: list[str] = []
    if listing:
        try:
            tree = json.loads(listing.decode("utf-8")).get("tree", [])
            names = [t["path"].split("/")[-1] for t in tree
                     if t.get("type") == "blob"
                     and t.get("path", "").startswith("summaries/")
                     and t.get("path", "").endswith(".csv")]
        except (json.JSONDecodeError, KeyError):
            names = []
    if not names:
        print("  ! could not list the archive (GitHub API rate limit?) — "
              "pass --arg with explicit contest numbers to proceed")
        return []
    def _parse(fname: str) -> tuple[str, str]:
        """'510_LilUCB.csv' -> ('510','LilUCB'); later contests are just
        '831.csv' with no sampler suffix, which a naive partition('_') would
        record as contest='831.csv'."""
        stem = fname[:-4] if fname.endswith(".csv") else fname
        contest, _, sampler = stem.partition("_")
        return contest, (sampler or "unspecified")

    if arg:
        want = {a.strip().replace(".csv", "") for a in arg.split(",") if a.strip()}
        names = [n for n in names if _parse(n)[0] in want]

    out: list[dict[str, Any]] = []
    for i, name in enumerate(sorted(names), 1):
        contest, sampler = _parse(name)
        raw = _get(NEXTML_RAW + urllib.parse.quote(name), timeout=60)
        if raw is None:
            print(f"  ! {name}: fetch failed")
            continue
        try:
            rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8", "replace"))))
        except csv.Error:
            continue
        kept = 0
        for r in rows:
            cap = " ".join(str(r.get("caption", "")).split())
            if not screen(cap):
                continue

            def _num(key: str) -> Any:
                v = r.get(key)
                try:
                    return float(v) if v not in (None, "") else None
                except (TypeError, ValueError):
                    return None

            out.append(emit({
                "source": f"nextml/caption-contest-data contest {contest}",
                "license": "no LICENSE file in repo — research use, do not redistribute",
                "text": cap,
                "funniness_label": _num("mean"),
                "meta": {"language": "en", "record_kind": "ranked_caption",
                         "contest": contest, "sampler": sampler,
                         "rank": r.get("rank"), "mean": _num("mean"),
                         "precision": _num("precision"), "votes": _num("votes"),
                         "not_funny": _num("not_funny"),
                         "somewhat_funny": _num("somewhat_funny"),
                         "funny": _num("funny")},
            }))
            kept += 1
            if len(out) >= limit:
                print(f"  hit limit at {name}")
                return out
        if i % 25 == 0 or kept == 0:
            print(f"  [{i}/{len(names)}] {name:<28} {kept:>5} captions "
                  f"(running total {len(out)})", flush=True)
        time.sleep(0.15)
    return out


# ---------------------------------------------------------------------------
# "A Polyglot of Foreign Proverbs" (Gutenberg 51090, 1869): ~8,000 proverbs in
# seven languages, EACH WITH ITS ENGLISH TRANSLATION on the same line.
#
# Aligned pairs are the scarce thing. Everything else multilingual in this
# corpus is a monolingual list; this one states what the phrase MEANS in
# English, which is what makes cross-lingual frame transfer testable rather
# than merely assertable. Public domain, one 1.1 MB file.
#
# Markup: `Foreign text. _English translation._` — except the German section,
# which drops the underscores and needs its own rule.
# ---------------------------------------------------------------------------
POLYGLOT_SECTIONS = [
    ("FRENCH PROVERBS.", "fr"), ("ITALIAN PROVERBS.", "it"),
    ("GERMAN PROVERBS.", "de"), ("SPANISH PROVERBS.", "es"),
    ("PORTUGUESE PROVERBS.", "pt"), ("DUTCH PROVERBS.", "nl"),
    ("DANISH PROVERBS.", "da"),
]
# The back matter is headed by a bare "INDEX." — NOT "ENGLISH INDEX", which
# appears only in the table of contents. Terminating on the wrong string let the
# final language section run to end-of-file and swallow English index lines.
_POLYGLOT_END = re.compile(r"\n\s+INDEX\.\s*\n")
_ITALIC = re.compile(r"_([^_]+)_")


def polyglot_lane(limit: int = 12000, arg: str = "") -> list[dict[str, Any]]:
    from pathlib import Path
    p = Path(__file__).resolve().parent / "data_cache" / "pg51090_polyglot.txt"
    if not p.exists():
        print("  ! data_cache/pg51090_polyglot.txt missing")
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    # Strip the Gutenberg licence footer FIRST. Without this the last language
    # section runs to end-of-file and the boilerplate parses as Danish proverbs
    # ("Professor Michael S." / "Hart was the originator of...").
    text = re.split(r"\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG", text)[0]
    text = re.split(r"\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG[^\n]*\n", text)[-1]
    # locate section spans by their LAST occurrence (the first is the contents page)
    end_m = _POLYGLOT_END.search(text)
    if end_m:
        text = text[:end_m.start()]
    marks: list[tuple[int, str | None]] = []
    for head, lang in POLYGLOT_SECTIONS:
        idx = text.rfind(head)
        if idx >= 0:
            marks.append((idx, lang))
    marks.sort()
    out: list[dict[str, Any]] = []
    for i, (start, lang) in enumerate(marks):
        if lang is None:
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = text[start:end]
        # entries are blank-line separated; rejoin wrapped lines
        for block in re.split(r"\n\s*\n", body):
            block = " ".join(block.split())
            if len(block) < 20 or block.isupper():
                continue
            m = _ITALIC.search(block)
            if m:
                english = m.group(1).strip()
                foreign = block[:m.start()].strip().rstrip("_").strip()
            elif lang == "de":
                # ONLY the German section drops the italic markers. Applying
                # this fallback everywhere split English index lines on
                # abbreviations ("Mr.", "Eccles.") and filed them as Danish.
                parts = re.split(r"(?<=[a-zß])\. (?=[A-Z])", block, maxsplit=1)
                if len(parts) != 2 or len(parts[1]) < 8:
                    continue
                foreign, english = parts[0].strip() + ".", parts[1].strip()
            else:
                continue
            if not foreign or not english or len(foreign) < 8:
                continue
            if not screen(foreign) or not screen(english):
                continue
            out.append({
                "source": "gutenberg:51090 A Polyglot of Foreign Proverbs",
                "license": "Public domain (Project Gutenberg)",
                "text": foreign,
                "meta": {"language": lang, "record_kind": "proverb",
                         "translation_en": english, "aligned": True,
                         "era": "1869", "book": "A Polyglot of Foreign Proverbs"},
            })
            if len(out) >= limit:
                return out
    from collections import Counter
    counts = Counter(r["meta"]["language"] for r in out)
    print(f"  polyglot aligned pairs: {dict(counts)}")
    return out


# ---------------------------------------------------------------------------
# Style-per-subreddit, via arctic-shift.
#
# Reddit's own keyless `.json` endpoints now 403 in every user-agent variation,
# and pushshift is moderator-only. arctic-shift is the surviving keyless route,
# and it is the right one for STYLE work: a subreddit is a community-declared
# style label attached to text that also carries a score. r/dadjokes is a
# 558,779-post corpus of things people agreed were dad jokes.
#
# `over_18` is honoured per row rather than per subreddit, because a SFW
# subreddit still contains individual NSFW posts.
# ---------------------------------------------------------------------------
STYLE_SUBREDDITS = {
    "dadjokes": "dad_joke", "MilitaryHumor": "military", "ProgrammerHumor": "tech",
    "cleanjokes": "clean", "AntiJokes": "anti_joke", "punny": "pun",
    "oneliners": "one_liner", "3amjokes": "absurd", "DadJokes": "dad_joke",
    "Jokes": "general", "Showerthoughts": "showerthought",
    "dishwasherjokes": "anti_joke", "MedicalHumor": "medical",
    "lawyerjokes": "legal", "chemistryjokes": "science", "mathjokes": "science",
    "AviationHumor": "aviation", "teachersjokes": "school",
}
ARCTIC = "https://arctic-shift.photon-reddit.com/api/posts/search"


def arctic_lane(limit: int = 40000, arg: str = "") -> list[dict[str, Any]]:
    """arg: comma-separated subreddits, or '' for the style list above."""
    subs = ([s.strip() for s in arg.split(",") if s.strip()]
            or list(STYLE_SUBREDDITS))
    per = max(50, limit // max(1, len(subs)))
    out: list[dict[str, Any]] = []
    for sub in subs:
        style = STYLE_SUBREDDITS.get(sub, sub.lower())
        got, before_id, stalls, nsfw_skipped = 0, None, 0, 0
        while got < per and stalls < 3:
            url = f"{ARCTIC}?subreddit={urllib.parse.quote(sub)}&limit=100&sort=desc"
            if before_id:
                url += f"&before={before_id}"
            data = _get_json(url, timeout=45)
            rows = (data or {}).get("data")
            if not rows:
                stalls += 1
                time.sleep(2.0)
                continue
            stalls = 0
            for r in rows:
                if r.get("over_18"):
                    nsfw_skipped += 1
                    continue
                title = str(r.get("title") or "").strip()
                body = str(r.get("selftext") or "").strip()
                if body in ("[removed]", "[deleted]"):
                    body = ""
                text = " ".join(f"{title} {body}".split())
                if not screen(text) or len(text) > 1200:
                    continue
                rec = {"source": f"reddit:r/{sub} (arctic-shift)",
                       "license": "Reddit content — research use only, do not redistribute",
                       "text": text,
                       "meta": {"language": "en", "style": style,
                                "subreddit": sub, "score": r.get("score"),
                                "num_comments": r.get("num_comments"),
                                "created_utc": r.get("created_utc")}}
                if title and body:
                    rec["meta"] |= {"setup": title, "punchline": body}
                if r.get("score") is not None:
                    rec["funniness_label"] = r["score"]
                out.append(emit(rec))
                got += 1
                if len(out) >= limit:
                    print(f"  r/{sub:<20} {got:>6} (limit hit)")
                    return out
            before_id = rows[-1].get("created_utc")
            if before_id is None:
                break
            time.sleep(0.8)
        print(f"  r/{sub:<20} {got:>6} kept  ({nsfw_skipped} nsfw skipped)", flush=True)
    return out


# ---------------------------------------------------------------------------
# Public-domain humor by CATEGORY.
#
# The corpus was style-blind and, worse, style-IMBALANCED: military 0.5%,
# legal 0.5%, science 0.6% against animal 6.4%. Reddit and joke APIs simply do
# not carry occupational or national humor in quantity. Project Gutenberg does,
# in curated single-subject volumes, and the category comes free with the book.
#
# Every id below was resolved and fetched. Two traps, both hit in practice:
#   * the README trap — gutendex sometimes lists a `*-readme.txt` as a book's
#     plain-text edition; fetching it returns a 404 page of exactly 6,395 bytes
#     that otherwise parses into "jokes";
#   * minstrel/blackface joke books exist in this collection and are excluded by
#     id, not by keyword, because their slurs are in dialect spelling that the
#     screen regex does not catch.
# ---------------------------------------------------------------------------
GUTENBERG_CATEGORIES: dict[str, list[int]] = {
    "military": [23733, 32335],
    "medical": [69467],
    "legal": [48339, 27785],
    "jewish": [45037, 33707, 77680, 54248],
    "russian": [71756],
    "german": [69421, 74708, 52083],
    "irish": [19220, 68835],
    "scottish": [26150],
    "french": [14156, 46285],
    "spanish": [69530],
    "dutch": [64761],
    "italian": [71712],
    "finnish": [51795, 48397],
    "nasreddin": [54690, 54691],
    "clerihew": [46691],
    "spoonerism": [62289],
    "parody": [70548, 70544, 62396, 46700, 64229],
    "riddles": [36571, 52598, 14358, 56772],
    "limerick_nonsense": [6652],
    "epigram": [41713],
    "epitaph": [42634],
    "jest_book": [15338, 12444, 20352, 43326, 29419, 21084, 43996, 29821, 54409],
    "wit_anthology": [18464, 24434, 21196, 10947, 50874, 78694, 30131, 36556],
    "burlesque": [22145],
    "wellerism_source": [580],
    "toasts_anecdotes": [2517],
}
# Excluded deliberately: 69826, 58982 (minstrel joke books — blackface
# caricature and dialect slurs throughout; the slur regex does not catch
# dialect spellings, so exclusion is by id).
GUTENBERG_EXCLUDE = {69826, 58982}
_PG_404_BYTES = 6395


def gutenberg_categories_lane(limit: int = 60000, arg: str = "") -> list[dict[str, Any]]:
    """arg: comma-separated category names, or '' for all."""
    cats = ([c.strip() for c in arg.split(",") if c.strip()]
            or list(GUTENBERG_CATEGORIES))
    out: list[dict[str, Any]] = []
    for cat in cats:
        ids = GUTENBERG_CATEGORIES.get(cat)
        if not ids:
            print(f"  ! unknown category '{cat}'")
            continue
        for bid in ids:
            if bid in GUTENBERG_EXCLUDE:
                continue
            raw = _get(f"https://www.gutenberg.org/ebooks/{bid}.txt.utf-8", timeout=120)
            if raw is None or len(raw) <= _PG_404_BYTES + 50:
                print(f"  ! {cat}/{bid}: no plain-text edition "
                      f"({len(raw) if raw else 'fetch failed'} B) — README trap")
                continue
            text = raw.decode("utf-8", "replace")
            body = re.split(r"\*\*\* ?START OF (?:THE|THIS) PROJECT GUTENBERG[^\n]*\n",
                            text)[-1]
            body = re.split(r"\*\*\* ?END OF (?:THE|THIS) PROJECT GUTENBERG", body)[0]
            kept = 0
            for block in re.split(r"\n\s*\n", body):
                block = " ".join(block.split())
                if not (60 <= len(block) <= 600):
                    continue
                if block.isupper() or not ('"' in block or "?" in block or "!" in block):
                    continue
                if not screen(block):
                    continue
                out.append({
                    "source": f"gutenberg:{bid}",
                    "license": "Public domain (Project Gutenberg)",
                    "text": block,
                    "meta": {"language": "en", "style_category": cat,
                             "record_kind": "public_domain_humor",
                             "gutenberg_id": bid, "era": "pre-1930"},
                })
                kept += 1
                if len(out) >= limit:
                    print(f"  {cat}/{bid:<6} {kept:>5} items (limit hit)")
                    return out
            print(f"  {cat + '/' + str(bid):<26} {kept:>5} items", flush=True)
            time.sleep(0.5)
    return out


# ---------------------------------------------------------------------------
# unfun.me (West & Horvitz, AAAI 2019): satirical Onion headlines that humans
# minimally edited until they read as REAL news, with a rating of how well the
# un-funning worked.
#
# This project models a joke as controlled prediction error plus a cheap repair.
# unfun.me is that relation run backwards and recorded: the edit that REMOVES
# the humor localises exactly where the humor lived. 254 of the pairs differ by
# a single chunk, and those carry hand-annotated Raskin/Attardo script-opposition
# labels — the mechanism, named, by a human.
# ---------------------------------------------------------------------------
UNFUN_FILES = {
    "pairs": ("https://raw.githubusercontent.com/epfl-dlab/unfun/master/data/"
              "pairs_with_ratings.tsv"),
    "editdist1": ("https://raw.githubusercontent.com/epfl-dlab/unfun/master/data/"
                  "pairs_editdist_1.tsv"),
    "script_opposition": ("https://raw.githubusercontent.com/epfl-dlab/unfun/master/"
                          "data/pairs_editdist_1_SCRIPT-OPPOSITION.tsv"),
}


def unfun_lane(limit: int = 12000, arg: str = "") -> list[dict[str, Any]]:
    import csv
    import io
    out: list[dict[str, Any]] = []
    for key, url in UNFUN_FILES.items():
        raw = _get(url, timeout=90)
        if raw is None:
            print(f"  ! unfun/{key}: fetch failed ({LAST_STATUS.get(url)})")
            continue
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8", "replace")),
                                   delimiter="\t"))
        kept = 0
        for r in rows:
            # column names differ between the three files; take what is present
            satirical = (r.get("original_title") or r.get("old_title") or "").strip()
            serious = (r.get("title") or r.get("new_title") or "").strip()
            if not satirical:
                continue
            satirical = " ".join(satirical.split())
            if not screen(satirical):
                continue
            meta: dict[str, Any] = {
                "language": "en", "record_kind": "unfunned_pair",
                "unfun_file": key,
                "serious_rewrite": " ".join(serious.split()),
                "removed_chunk": r.get("old_chunk", ""),
                "replacement_chunk": r.get("new_chunk", ""),
                "chunk_label": r.get("modified_chunk_label", ""),
            }
            # the script-opposition file adds one column per SSTH dimension
            opps = [k for k, v in r.items()
                    if k and str(v).strip() in ("1", "1.0", "TRUE", "True")
                    and k not in ("uid", "id", "original_id", "rating")]
            if key == "script_opposition" and opps:
                meta["script_opposition"] = opps
            rec = {"source": "unfun.me (epfl-dlab/unfun)",
                   "license": "no LICENSE file in repo — research use",
                   "text": satirical, "meta": meta}
            grade = r.get("rating") or r.get("mean_rating")
            try:
                if grade not in (None, ""):
                    rec["funniness_label"] = float(grade)
                    meta["unfunning_rating"] = float(grade)
            except (TypeError, ValueError):
                pass
            out.append(rec)
            kept += 1
            if len(out) >= limit:
                return out
        print(f"  unfun/{key:<18} {kept:>6} pairs")
    return out


# ---------------------------------------------------------------------------
# Word-level funniness norms. Not jokes — FEATURES. They go to data_cache/ for
# the word-taxonomy and dead-weight-word work, not into the joke corpus.
# ---------------------------------------------------------------------------
WORD_NORMS = {
    "engelthaler_humor_norms.csv":
        "https://raw.githubusercontent.com/tomasengelthaler/HumorNorms/master/humor_dataset.csv",
    "cockamamie_gobbledegook.json":
        "https://raw.githubusercontent.com/limorigu/Cockamamie-Gobbledegook/master/"
        "data/cockamamie_gobbledegook_us_data.json",
    "cmudict.dict":
        "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict",
}


def fetch_word_norms() -> dict[str, Any]:
    from pathlib import Path
    cache = Path(__file__).resolve().parent / "data_cache"
    cache.mkdir(exist_ok=True)
    got = {}
    for name, url in WORD_NORMS.items():
        p = cache / name
        if p.exists() and p.stat().st_size > 1000:
            got[name] = p.stat().st_size
            print(f"  {name:<34} cached {p.stat().st_size:,} B")
            continue
        raw = _get(url, timeout=180)
        if raw is None:
            print(f"  ! {name}: fetch failed ({LAST_STATUS.get(url)})")
            continue
        p.write_bytes(raw)
        got[name] = len(raw)
        print(f"  {name:<34} {len(raw):,} B")
    return got


# ---------------------------------------------------------------------------
# Static GitHub joke dumps. One request each, no polling, no rate limit.
#
# taivop/joke-dataset is the largest keyless haul available and it carries
# reddit `score`, but it is UNFILTERED reddit: the first record in the file is
# racial humour. Every row goes through screen() and the drop count is printed,
# because a silent filter is indistinguishable from a filter that isn't running.
# ---------------------------------------------------------------------------
def taivop_lane(limit: int = 250000, arg: str = "") -> list[dict[str, Any]]:
    files = {
        "wocka": ("https://raw.githubusercontent.com/taivop/joke-dataset/master/wocka.json",
                  "wocka.com"),
        "stupidstuff": ("https://raw.githubusercontent.com/taivop/joke-dataset/master/stupidstuff.json",
                        "stupidstuff.org"),
        "reddit_jokes": ("https://raw.githubusercontent.com/taivop/joke-dataset/master/reddit_jokes.json",
                         "reddit r/jokes (taivop dump)"),
    }
    which = [w_.strip() for w_ in arg.split(",") if w_.strip()] or list(files)
    out: list[dict[str, Any]] = []
    for key in which:
        if key not in files:
            continue
        url, origin = files[key]
        raw = _get(url, timeout=180)
        if raw is None:
            print(f"  ! taivop/{key}: fetch failed")
            continue
        try:
            rows = json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError:
            print(f"  ! taivop/{key}: bad JSON")
            continue
        kept = dropped = 0
        for r in rows:
            title = str(r.get("title", "")).strip()
            body = str(r.get("body", "")).strip()
            text = " ".join(f"{title} {body}".split()) if title else " ".join(body.split())
            if not text:
                continue
            if not screen(text):
                dropped += 1
                continue
            meta = {"language": "en", "dump": key,
                    "category": r.get("category", ""),
                    "joke_id": r.get("id", "")}
            if title and body:
                meta |= {"setup": title, "punchline": body}
            rec = {"source": f"taivop/joke-dataset ({origin})",
                   "license": "no stated licence; aggregated public jokes — research use",
                   "text": text, "meta": meta}
            for grade in ("score", "rating"):
                if r.get(grade) is not None:
                    rec["funniness_label"] = r[grade]
                    meta[grade] = r[grade]
                    break
            out.append(rec)
            kept += 1
            if len(out) >= limit:
                print(f"  taivop/{key:<14} {kept:>7} kept, {dropped:>5} screened out (limit hit)")
                return out
        print(f"  taivop/{key:<14} {kept:>7} kept, {dropped:>5} screened out")
    return out


def static_dumps_lane(limit: int = 5000, arg: str = "") -> list[dict[str, Any]]:
    """Whole small corpora that back a polling API — fetch the file, not the API."""
    out: list[dict[str, Any]] = []
    raw = _get("https://raw.githubusercontent.com/15Dkatz/official_joke_api/"
               "master/jokes/index.json", timeout=60)
    if raw:
        try:
            for r in json.loads(raw.decode("utf-8", "replace")):
                setup = str(r.get("setup", "")).strip()
                punch = str(r.get("punchline", "")).strip()
                text = " ".join(f"{setup} {punch}".split())
                if screen(text):
                    out.append({
                        "source": "15Dkatz/official_joke_api (full dump)",
                        "license": "MIT (repo)",
                        "text": text,
                        "meta": {"language": "en", "style": r.get("type", ""),
                                 "setup": setup, "punchline": punch},
                    })
        except json.JSONDecodeError:
            pass
    raw = _get("https://raw.githubusercontent.com/amoudgl/short-jokes-dataset/"
               "master/data/reddit-cleanjokes.csv", timeout=60)
    if raw:
        import csv
        import io
        try:
            for r in csv.DictReader(io.StringIO(raw.decode("utf-8", "replace"))):
                text = " ".join(str(r.get("Joke", "")).split())
                if screen(text):
                    out.append({
                        "source": "amoudgl/short-jokes-dataset (reddit-cleanjokes)",
                        "license": "no stated licence; pre-cleaned reddit set",
                        "text": text,
                        "meta": {"language": "en", "screened_upstream": True},
                    })
        except csv.Error:
            pass
    print(f"  static_dumps    {len(out):>7} items")
    return out[:limit]


def chucknorris_lane(limit: int = 6000, arg: str = "") -> list[dict[str, Any]]:
    """Category-labelled by construction: every joke carries its own category
    list. The `explicit` category is skipped rather than screened after the
    fact, since the API tells us up front what it is."""
    cats = _get_json("https://api.chucknorris.io/jokes/categories") or []
    skip = {"explicit"}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    # the search endpoint is the only bulk lever; sweep common substrings
    probes = [c for c in cats if c not in skip] + \
             list("abcdefghijklmnopqrstuvwxyz") + ["the", "a", "chuck", "norris"]
    for probe in probes:
        if len(out) >= limit:
            break
        data = _get_json("https://api.chucknorris.io/jokes/search?query="
                         + urllib.parse.quote(probe))
        for r in (data or {}).get("result", []):
            jid = r.get("id")
            if not jid or jid in seen:
                continue
            cats_here = r.get("categories") or []
            if set(cats_here) & skip:
                continue
            text = " ".join(str(r.get("value", "")).split())
            if not screen(text):
                continue
            seen.add(jid)
            out.append({
                "source": "api.chucknorris.io",
                "license": "CC BY 3.0",
                "text": text,
                "meta": {"language": "en", "style": "chuck_norris_fact",
                         "categories": cats_here,
                         "category": cats_here[0] if cats_here else "uncategorized",
                         "api_id": jid},
            })
        time.sleep(0.4)
    print(f"  chucknorris     {len(out):>7} unique jokes")
    return out[:limit]


# Wiktionary category members: idioms, proverbs, similes. Titles ARE the phrases.
#
# The important structural fact: en.wiktionary hosts per-LANGUAGE categories, so
# 80+ languages are reachable from a single wiki with one parser and one rate
# limit, instead of one edition at a time. `phrase_lang` is the language of the
# PHRASE; the host wiki is incidental.
_EN_WIKT = [
    ("Chinese", "zh", 16920), ("Mandarin", "zh", 14865), ("English", "en", 10599),
    ("Polish", "pl", 4890), ("Spanish", "es", 3321), ("Finnish", "fi", 1235),
    ("German", "de", 1022), ("Portuguese", "pt", 991), ("Japanese", "ja", 926),
    ("Italian", "it", 831), ("Swedish", "sv", 809), ("Dutch", "nl", 737),
    ("Thai", "th", 500), ("Hungarian", "hu", 470), ("Vietnamese", "vi", 411),
    ("Turkish", "tr", 383), ("French", "fr", 333), ("Russian", "ru", 315),
    ("Romanian", "ro", 276), ("Welsh", "cy", 245), ("Hindi", "hi", 204),
    ("Danish", "da", 157), ("Galician", "gl", 149), ("Czech", "cs", 142),
    ("Macedonian", "mk", 141), ("Yoruba", "yo", 126), ("Icelandic", "is", 122),
    ("Azerbaijani", "az", 116), ("Telugu", "te", 113), ("Arabic", "ar", 107),
    ("Catalan", "ca", 96), ("Serbo-Croatian", "sh", 93), ("Ukrainian", "uk", 88),
    ("Korean", "ko", 81), ("Yiddish", "yi", 74), ("Tamil", "ta", 70),
    ("Malay", "ms", 61), ("Indonesian", "id", 58), ("Georgian", "ka", 54),
    ("Persian", "fa", 50), ("Latin", "la", 51), ("Greek", "el", 76),
    ("Hebrew", "he", 36), ("Irish", "ga", 33), ("Swahili", "sw", 29),
    ("Albanian", "sq", 25), ("Basque", "eu", 11), ("Marathi", "mr", 12),
]

WIKTIONARY_CATS: list[tuple[str, str, str, str]] = []
for _name, _code, _n in _EN_WIKT:
    WIKTIONARY_CATS.append(("en", f"Category:{_name} idioms", "idiom", _code))
    WIKTIONARY_CATS.append(("en", f"Category:{_name} proverbs", "proverb", _code))
WIKTIONARY_CATS += [
    ("en", "Category:English similes", "simile", "en"),
    # native editions hold phrases the English wiki does not
    ("ru", "Категория:Фразеологизмы/ru", "idiom", "ru"),
    ("de", "Kategorie:Redewendung (Deutsch)", "idiom", "de"),
    ("tr", "Kategori:Türkçe atasözleri", "proverb", "tr"),
    ("ko", "분류:한국어 속담", "proverb", "ko"),
    ("ja", "カテゴリ:日本語 ことわざ", "proverb", "ja"),
    ("es", "Categoría:ES:Refranes", "proverb", "es"),
    ("hu", "Kategória:magyar közmondások", "proverb", "hu"),
    ("de", "Kategorie:Sprichwort (Deutsch)", "proverb", "de"),
    ("he", "קטגוריה:פתגמים", "proverb", "he"),
    ("fr", "Catégorie:Proverbes en français", "proverb", "fr"),
    ("sv", "Kategori:Svenska/Ordspråk", "proverb", "sv"),
    ("cs", "Kategorie:Česká přísloví", "proverb", "cs"),
    ("nl", "Categorie:Spreekwoord in het Nederlands", "proverb", "nl"),
    ("pt", "Categoria:Provérbio (Português)", "proverb", "pt"),
    ("fi", "Luokka:Suomen kielen sananlaskut", "proverb", "fi"),
    ("id", "Kategori:id:Peribahasa", "proverb", "id"),
]


def wiktionary_lane(limit: int = 20000, arg: str = "") -> list[dict[str, Any]]:
    """Wikimedia 429s easily and farm-wide. Serialised at ~1 req/s with a
    contact-bearing User-Agent, which is what the API docs ask for."""
    targets = WIKTIONARY_CATS
    if arg:
        want = {a.strip() for a in arg.split(",") if a.strip()}
        targets = [t for t in targets
                   if t[0] in want or t[2] in want or t[3] in want]
    ua = {"User-Agent": "HumorGenomeResearch/1.0 (amarel.taylor.s@gmail.com)"}
    out: list[dict[str, Any]] = []
    missing: list[str] = []
    for host, cat, kind, phrase_lang in targets:
        lang = host
        got, cont, fails = 0, None, 0
        while len(out) < limit:
            url = (f"https://{lang}.wiktionary.org/w/api.php?action=query"
                   f"&list=categorymembers&cmtitle={urllib.parse.quote(cat)}"
                   f"&cmlimit=500&format=json&cmnamespace=0")
            if cont:
                url += "&cmcontinue=" + urllib.parse.quote(cont)
            data = _get_json(url, headers=ua)
            if not data:
                # One transient failure must not abandon a 16,920-member
                # category at page 4. Back off and retry the SAME cursor;
                # only give up after several consecutive failures, and say so.
                fails += 1
                if fails > 5:
                    print(f"  ! {cat}: gave up after 5 failed pages at {got} of "
                          f"{'?' if cont else 'end'} — INCOMPLETE", flush=True)
                    break
                time.sleep(5.0 * fails)
                continue
            fails = 0
            for m in data.get("query", {}).get("categorymembers", []):
                title = " ".join(str(m.get("title", "")).split())
                if title.startswith(("Appendix:", "Apéndice:", "Anhang:")):
                    continue
                if not screen(title):
                    continue
                out.append({
                    "source": f"{host}.wiktionary:{cat}",
                    "license": "CC BY-SA 4.0 (Wiktionary)",
                    "text": title,
                    # `language` is the language of the PHRASE, not of the wiki
                    # that hosts it — en.wiktionary serves 80+ languages.
                    "meta": {"language": phrase_lang, "host_wiki": host,
                             "record_kind": kind, "category": cat,
                             "pageid": m.get("pageid")},
                })
                got += 1
            cont = (data.get("continue") or {}).get("cmcontinue")
            time.sleep(1.1)
            if not cont:
                break
        if got:
            print(f"  wikt:{phrase_lang}:{kind:<9} {got:>6}  {cat}", flush=True)
        else:
            missing.append(cat)
    if missing:
        # an empty category is usually a wrong name, not an empty topic; say so
        print(f"  ({len(missing)} categories returned nothing — likely renamed: "
              f"{', '.join(m[:40] for m in missing[:6])}"
              f"{' ...' if len(missing) > 6 else ''})")
    return out[:limit]


def showerthoughts_lane(limit: int = 600, arg: str = "") -> list[dict[str, Any]]:
    """r/Showerthoughts with real upvote counts, reachable while reddit's own
    JSON endpoints 403 keyless clients."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    misses = 0
    while len(out) < limit and misses < 25:
        data = _get_json("https://api.popcat.xyz/showerthoughts")
        text = " ".join(str((data or {}).get("result", "")).split())
        if not text or text in seen or not screen(text):
            misses += 1
            time.sleep(0.5)
            continue
        seen.add(text)
        misses = 0
        rec = {"source": "api.popcat.xyz/showerthoughts (r/Showerthoughts)",
               "license": "reddit content — research use only, do not redistribute",
               "text": text,
               "meta": {"language": "en", "style": "showerthought",
                        "author": (data or {}).get("author", ""),
                        "upvotes": (data or {}).get("upvotes")}}
        if (data or {}).get("upvotes") is not None:
            rec["funniness_label"] = data["upvotes"]
        out.append(rec)
        time.sleep(0.35)
    print(f"  showerthoughts  {len(out):>7} unique")
    return out


# ---------------------------------------------------------------------------
# Meme lanes.
#
# A meme template is a REUSABLE FRAME with a declared number of slots, which is
# the same object this project calls a format. memegen publishes the slot count
# (`lines`) and links 208/211 templates to their Know Your Meme origin; imgflip
# publishes lifetime caption counts, i.e. how heavily each frame has been mined.
#
# MemeCap goes further and states, per meme, the literal reading AND the
# intended reading AND the metaphor connecting them — a labelled repair step.
# ---------------------------------------------------------------------------
def meme_templates_lane(limit: int = 400, arg: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows = _get_json("https://api.memegen.link/templates") or []
    for t in rows:
        name = str(t.get("name", "")).strip()
        if not name:
            continue
        example = " / ".join(str(x) for x in (t.get("example", {}).get("text") or []))
        text = f"{name}: {example}" if example else name
        out.append({
            "source": "api.memegen.link/templates",
            "license": "memegen engine MIT; template names/examples community-sourced",
            "text": " ".join(text.split()),
            "meta": {"language": "en", "record_kind": "meme_template",
                     "template_id": t.get("id"), "slots": t.get("lines"),
                     "overlays": t.get("overlays"),
                     "keywords": t.get("keywords") or [],
                     "kym_source": t.get("source") or ""},
        })
    data = _get_json("https://api.imgflip.com/get_memes") or {}
    for t in (data.get("data", {}) or {}).get("memes", []):
        name = str(t.get("name", "")).strip()
        if not name:
            continue
        out.append({
            "source": "api.imgflip.com/get_memes",
            "license": "keyless public API; no stated licence (metadata only)",
            "text": name,
            "meta": {"language": "en", "record_kind": "meme_template",
                     "template_id": t.get("id"), "slots": t.get("box_count"),
                     "lifetime_captions": t.get("captions")},
        })
    return out[:limit]


def memecap_lane(limit: int = 7000, arg: str = "") -> list[dict[str, Any]]:
    """MemeCap: literal caption vs intended caption vs the metaphor between
    them. The metaphor field is the closest thing in any public corpus to an
    explicit statement of WHICH substitution makes the joke resolve."""
    from pathlib import Path
    cache = Path(__file__).resolve().parent / "data_cache"
    out: list[dict[str, Any]] = []
    for fname in ("memecap_trainval.json", "memecap_test.json"):
        p = cache / fname
        if not p.exists():
            continue
        try:
            rows = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for row in rows:
            meme_caps = row.get("meme_captions") or []
            img_caps = row.get("img_captions") or []
            title = str(row.get("title", "")).strip()
            text = " ".join((meme_caps[0] if meme_caps else title).split())
            if not screen(text):
                continue
            metaphors = row.get("metaphors") or []
            out.append({
                "source": "MemeCap (eujhwang/meme-cap)",
                "license": "no stated licence; images referenced not bundled — research use",
                "text": text,
                "meta": {"language": "en", "record_kind": "meme_caption",
                         "category": row.get("category", ""),
                         "title": title,
                         "literal_image_caption": img_caps[0] if img_caps else "",
                         "intended_meme_caption": meme_caps[0] if meme_caps else "",
                         "metaphors": metaphors,
                         "post_id": row.get("post_id", "")},
            })
            if len(out) >= limit:
                return out
    return out[:limit]


# ---------------------------------------------------------------------------
# Style lane: jokes that arrive WITH a category label.
#
# The corpus was style-blind — 185k items and no way to ask whether a military
# joke resolves differently from a dad joke. These three APIs all expose a
# category/type/search axis, so the label comes free with the text instead of
# having to be inferred afterwards.
# ---------------------------------------------------------------------------
# icanhazdadjoke has no categories, but its search index makes TOPIC a usable
# proxy: every hit for term=army is a dad-joke-form joke about the army.
DADJOKE_TERMS = [
    "army", "navy", "soldier", "pilot", "police", "doctor", "nurse", "lawyer",
    "teacher", "engineer", "computer", "programmer", "science", "math", "music",
    "farmer", "chef", "food", "coffee", "beer", "cat", "dog", "horse", "fish",
    "bird", "bear", "cow", "chicken", "tree", "flower", "ocean", "mountain",
    "car", "train", "plane", "boat", "money", "bank", "work", "office", "school",
    "book", "movie", "ghost", "vampire", "pirate", "king", "wizard", "robot",
    "space", "moon", "sun", "snow", "rain", "time", "clock", "door", "window",
    "shoe", "hat", "bread", "cheese", "egg", "potato", "sport", "football",
    "golf", "run", "sleep", "dream", "phone", "email", "internet", "battery",
]


def _dadjoke_search(term: str, cap: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page, pages = 1, 1
    while len(out) < cap and page <= pages and page <= 8:
        data = _get_json(
            f"https://icanhazdadjoke.com/search?limit=30&page={page}"
            f"&term={urllib.parse.quote(term)}")
        if not data:
            break
        pages = int(data.get("total_pages") or 1)
        for row in data.get("results", []):
            joke = str(row.get("joke", "")).strip()
            if screen(joke):
                out.append({
                    "source": "icanhazdadjoke.com API",
                    "license": "icanhazdadjoke API terms (attribution requested)",
                    "text": " ".join(joke.split()),
                    "meta": {"language": "en", "api_id": row.get("id", ""),
                             "style": "dad_joke", "topic": term},
                })
        page += 1
        time.sleep(0.6)
    return out[:cap]


def _jokeapi_category(cat: str, lang: str, cap: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stalls = 0
    while len(out) < cap and stalls < 3:
        n = min(10, cap - len(out))
        data = _get_json(f"https://v2.jokeapi.dev/joke/{urllib.parse.quote(cat)}"
                         f"?safe-mode&lang={lang}&amount={n}")
        rows = (data or {}).get("jokes") or ([data] if data and not data.get("error") else [])
        if not rows:
            stalls += 1
            time.sleep(2.0)
            continue
        before = len(out)
        for row in rows:
            if row.get("type") == "twopart":
                setup = str(row.get("setup", "")).strip()
                punch = str(row.get("delivery", "")).strip()
                text, extra = f"{setup} {punch}", {"setup": setup, "punchline": punch}
            else:
                text, extra = str(row.get("joke", "")).strip(), {}
            text = " ".join(text.split())
            if not screen(text):
                continue
            out.append({
                "source": "v2.jokeapi.dev (safe-mode)",
                "license": "JokeAPI (user-submitted; safe-mode filtered)",
                "text": text,
                "meta": {"language": lang, "style": row.get("category", cat).lower(),
                         "category": row.get("category", cat),
                         "flags": [k for k, v in (row.get("flags") or {}).items() if v]}
                        | extra,
            })
        if len(out) == before:
            stalls += 1
        time.sleep(0.7)
    return out[:cap]


def _official_type(kind: str, cap: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stalls = 0
    while len(out) < cap and stalls < 4:
        rows = _get_json(f"https://official-joke-api.appspot.com/jokes/"
                         f"{urllib.parse.quote(kind)}/ten")
        if not rows or not isinstance(rows, list):
            stalls += 1
            time.sleep(1.5)
            continue
        before = len(out)
        for row in rows:
            setup = str(row.get("setup", "")).strip()
            punch = str(row.get("punchline", "")).strip()
            text = " ".join(f"{setup} {punch}".split())
            if not screen(text):
                continue
            out.append({
                "source": "official-joke-api.appspot.com",
                "license": "public API (github: 15Dkatz/official_joke_api)",
                "text": text,
                "meta": {"language": "en", "style": row.get("type", kind),
                         "setup": setup, "punchline": punch},
            })
        if len(out) == before:
            stalls += 1
        time.sleep(0.5)
    return out[:cap]


def styles_lane(limit: int = 2000, arg: str = "") -> list[dict[str, Any]]:
    """arg: 'dad', 'jokeapi', 'official', or '' for all three."""
    which = [w_.strip() for w_ in arg.split(",") if w_.strip()] or ["dad", "jokeapi", "official"]
    out: list[dict[str, Any]] = []
    if "dad" in which:
        per = max(4, (limit // 2) // len(DADJOKE_TERMS))
        for term in DADJOKE_TERMS:
            got = _dadjoke_search(term, per)
            if got:
                print(f"  dad:{term:<14} {len(got):>4}")
            out.extend(got)
    if "jokeapi" in which:
        cats = _get_json("https://v2.jokeapi.dev/categories") or {}
        categories = [c for c in (cats.get("categories") or []) if c != "Any"]
        langs = (_get_json("https://v2.jokeapi.dev/languages") or {}).get("jokeLanguages") or ["en"]
        for cat in categories:
            for lang in langs:
                got = _jokeapi_category(cat, lang, max(10, limit // 40))
                if got:
                    print(f"  jokeapi:{cat}/{lang:<8} {len(got):>4}")
                out.extend(got)
    if "official" in which:
        kinds = _get_json("https://official-joke-api.appspot.com/types") or []
        for kind in (kinds if isinstance(kinds, list) else []):
            got = _official_type(str(kind), max(20, limit // 20))
            if got:
                print(f"  official:{str(kind):<14} {len(got):>4}")
            out.extend(got)
    return out


# ---------------------------------------------------------------------------
# Local staged lane: material already downloaded into data_cache/ that never
# reached corpora/. Both files below carry a HUMAN GRADE, which is scarcer and
# more useful than raw joke text.
# ---------------------------------------------------------------------------
LOCAL_SPECS: dict[str, dict[str, Any]] = {
    "newyorker": {
        "path": "data_cache/newyorker_caption_ranking.jsonl",
        "text": "caption",
        "source": "nextml/caption-contest-data (New Yorker Caption Contest)",
        "license": "CC BY-NC 4.0 — research use, non-commercial",
        "lang": "en",
        "grade": "mean",
        "keep": ["contest", "mean", "votes"],
        "why": "one fixed cartoon setup, many ranked candidate repairs — the "
               "project's theory as a natural experiment",
    },
    "reddit_bulk": {
        "path": "data_cache/reddit_jokes_bulk.jsonl",
        "text": ("setup", "punchline"),
        "source": "reddit:r/Jokes (bulk)",
        "license": "Reddit content — research use only, do not redistribute",
        "lang": "en",
        "grade": "score",
        "keep": ["score"],
        "why": "explicit setup/punchline split with upvote score",
    },
}


def local_lane(limit: int = 5000, arg: str = "") -> list[dict[str, Any]]:
    from pathlib import Path
    keys = list(LOCAL_SPECS) if arg in ("", "all") else [k.strip() for k in arg.split(",")]
    out: list[dict[str, Any]] = []
    per = max(1, limit // max(1, len(keys)))
    for k in keys:
        spec = LOCAL_SPECS.get(k)
        if not spec:
            print(f"  ! unknown local spec '{k}'")
            continue
        p = Path(__file__).resolve().parent / spec["path"]
        if not p.exists():
            print(f"  ! {spec['path']} missing")
            continue
        got = 0
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                if got >= per:
                    break
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "_meta" in row:
                    continue
                tf = spec["text"]
                if isinstance(tf, (list, tuple)):
                    parts = [str(row.get(f, "")).strip() for f in tf]
                    text = " ".join(p_ for p_ in parts if p_)
                    extra = {f: row.get(f) for f in tf if row.get(f)}
                else:
                    text = str(row.get(tf, "")).strip()
                    extra = {}
                text = " ".join(text.split())
                if not screen(text):
                    continue
                meta = {"language": spec.get("lang", "en")} | extra
                for f in spec.get("keep", []):
                    if row.get(f) is not None:
                        meta[f] = row[f]
                rec = {"source": spec["source"], "license": spec["license"],
                       "text": text, "meta": meta}
                if spec.get("grade") and row.get(spec["grade"]) is not None:
                    rec["funniness_label"] = row[spec["grade"]]
                out.append(rec)
                got += 1
        print(f"  local:{k:<26} {got:>6} items")
    return out


# ---------------------------------------------------------------------------
LANES: dict[str, Callable[[int, str], list[dict[str, Any]]]] = {
    "hf": hf_lane,
    "wikiquote2": wikiquote2_lane,
    "gutendex": gutendex_lane,
    "api": api_lane,
    "local": local_lane,
    "styles": styles_lane,
    "nyc": nyc_lane,
    "meme_templates": meme_templates_lane,
    "memecap": memecap_lane,
    "nextml": nextml_lane,
    "taivop": taivop_lane,
    "static_dumps": static_dumps_lane,
    "chucknorris": chucknorris_lane,
    "wiktionary": wiktionary_lane,
    "showerthoughts": showerthoughts_lane,
    "polyglot": polyglot_lane,
    "unfun": unfun_lane,
    "gutenberg_categories": gutenberg_categories_lane,
    "arctic": arctic_lane,
}
harvest_supply.LANES.update(LANES)


def _load_specs() -> None:
    """Specs live in a JSON sidecar so a verified source is DATA, not a code
    edit — the sourcing sweep writes the file, this module consumes it."""
    from pathlib import Path
    p = Path(__file__).resolve().parent / "wave2_specs.json"
    if not p.exists():
        return
    blob = json.loads(p.read_text(encoding="utf-8"))
    HF_SPECS.update(blob.get("hf", {}))
    API_SPECS.update(blob.get("api", {}))


_load_specs()


def main() -> int:
    global HF_TRANSPORT
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lane", help="one of: " + ", ".join(LANES)
                    + ", or 'list' / 'recover'")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--arg", default="")
    ap.add_argument("--no-dedupe", action="store_true")
    ap.add_argument("--semantic", action="store_true")
    ap.add_argument("--hf-transport", choices=("auto", "rows", "parquet"),
                    default=os.environ.get("HUMOR_HF_TRANSPORT", "auto"),
                    help="HF bulk transport; auto prefers resumable parquet and falls back to rows")
    a = ap.parse_args()
    HF_TRANSPORT = a.hf_transport

    if a.lane == "recover":
        # Re-ingest whatever a killed run managed to write. Recovered records go
        # through the SAME lane machinery (dedupe, licences, receipt) as fresh
        # ones — recovery must not become a way to smuggle rows past the gates.
        from pathlib import Path
        d = Path(__file__).resolve().parent / "jestry_out"
        parts = sorted(d.glob(f"partial_{a.arg or '*'}*.jsonl"))
        if not parts:
            print("no partial files to recover")
            return 0
        recovered: list[dict[str, Any]] = []
        for p in parts:
            n0 = len(recovered)
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue          # a kill mid-write leaves one torn line
                if rec.get("text"):
                    recovered.append(rec)
            print(f"  {p.name:<56} {len(recovered) - n0:>7} rows")
        harvest_supply.LANES["_recovered"] = lambda _l, _a: recovered
        r = harvest_supply.harvest("_recovered", limit=len(recovered), arg="recover",
                                   dedupe=not a.no_dedupe, semantic=a.semantic)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    if a.lane == "list":
        print(f"HF specs ({len(HF_SPECS)}):")
        for k, v in sorted(HF_SPECS.items()):
            print(f"  {k:<32} {v['repo']:<48} lang={v.get('lang', 'en')}")
        print(f"\nAPI specs ({len(API_SPECS)}):")
        for k, v in sorted(API_SPECS.items()):
            print(f"  {k:<32} {v['source']}")
        return 0

    open_partial(a.lane, a.arg)
    completed = False
    try:
        r = harvest_supply.harvest(a.lane, limit=a.limit, arg=a.arg,
                                   dedupe=not a.no_dedupe, semantic=a.semantic)
        completed = True
    finally:
        close_partial(completed=completed)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
