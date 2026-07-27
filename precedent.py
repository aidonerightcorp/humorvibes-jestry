"""Precedent engine: has this joke been done before, and what can build the next one?

The charter's supply-and-provenance plane, pointed at three questions:

1. BEEN-DONE   Is this candidate a re-tell? Checked at two levels:
               - surface: embedding similarity of the raw text;
               - frame: similarity of the extracted comic frame (the same
                 engine in new words is still precedent — comedians call the
                 innocent case parallel thinking and the hidden case theft;
                 the difference is provenance, which is exactly what Jestry
                 receipts exist to record).
2. SUPPLY      What existing phrases, proverbs, stories, and canon items —
               across languages — could power a new bit? (THEORY.md §10-11:
               canonical material rents a population-wide cache.)
3. LABELS      Gemma 4 enriches items on demand: mechanism guesses, a one-line
               frame, language, cultural cache (canonical/topical/insider),
               taboo topics. Enrichment is selective, by demand, with
               provenance — never a precondition for indexing.

Backends (Law: no hidden fallback — every report names its backend):
- OllamaEmbedBackend  embeddinggemma via /api/embed — semantic + multilingual
                      (a Gemma-family embedder, so the lane stays Gemma-native).
- HashEmbedBackend    deterministic token-hash vectors — offline, surface-level
                      token overlap only; reports semantic=False so a miss is
                      never read as proof of novelty.

Verdicts are always scoped: "no precedent found WITHIN THE INDEXED SUPPLY of
N items" — an open-world claim, not an omniscience claim.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from humor_datacenter.embedding import cosine, hash_embedding
from humor_mesh import extract_json_object

ROOT = Path(__file__).resolve().parent
CORPORA_DIR = ROOT / "corpora"
OUT_DIR = ROOT / "jestry_out"

SURFACE_MATCH = 0.90       # >= : effectively the same wording
FRAME_MATCH = 0.86         # >= on frame channel: same engine, new words
NEIGHBORHOOD = 0.75        # >= : adjacent material worth citing (hash backend)
NEIGHBORHOOD_SEMANTIC = 0.66   # semantic embeddings run lower cosines on
                               # lexically-different paraphrases; calibrated on
                               # the monkeys-fall-from-trees probe (0.71)

LABEL_PROMPT = (
    "Label one humor/wisdom item for a joke-precedent database. Item:\n{text}\n\n"
    "Return JSON only:\n"
    '{{"frame": "ONE sentence naming the comic engine or reusable insight",\n'
    '  "mechanisms": ["1-3 of: script_opposition,false_analogy,wordplay_pun,'
    "misdirection_reversal,rule_of_three,callback_tag,specificity_concreteness,"
    "hyperbole_understatement,anthropomorphism,status_inversion,shared_frustration,"
    'self_deprecation,irony_sarcasm,bathos_anti_joke"],\n'
    '  "language": "ISO code of the original text",\n'
    '  "cultural_cache": "canonical|topical|insider",\n'
    '  "taboo_topics": ["only if plainly present, else empty"]}}'
)


def _sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------
class HashEmbedBackend:
    name = "hash-128"
    cache_key = "hash-128-v1"
    semantic = False

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        return [hash_embedding(t) for t in texts]


class OllamaEmbedBackend:
    semantic = True

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        from dataclasses import replace
        from humorvibes.config import Settings
        from humorvibes.embeddings import OllamaEmbeddingBackend

        settings = Settings.from_env()
        self.model = model or os.environ.get("EMBED_MODEL", "embeddinggemma")
        self.host = (host or settings.ollama_host).rstrip("/")
        self.name = f"ollama:{self.model}"
        self.cache_key = f"{self.name}:{_sha(self.host)}"
        self._backend = OllamaEmbeddingBackend(
            replace(settings, ollama_host=self.host), self.model
        )

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        from humorvibes.errors import IntegrationError

        try:
            return self._backend.embed(texts).vectors
        except IntegrationError:
            return None

    def available(self) -> bool:
        return self.embed(["ping"]) is not None


def pick_backend(prefer_semantic: bool = True) -> Any:
    if prefer_semantic:
        b = OllamaEmbedBackend()
        try:
            if b.available():
                return b
        except Exception:
            pass
    return HashEmbedBackend()


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------
@dataclass
class PrecedentHit:
    item_id: str
    text: str
    source: str
    license: str
    language: str
    channel: str          # surface | frame
    score: float
    frame: str = ""


@dataclass
class PrecedentReport:
    query: str
    verdict: str
    backend: str
    semantic: bool
    indexed_items: int
    surface_hits: list[PrecedentHit] = field(default_factory=list)
    frame_hits: list[PrecedentHit] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        def hits(rows: list[PrecedentHit]) -> list[dict[str, Any]]:
            return [{"item_id": h.item_id, "score": round(h.score, 4), "text": h.text[:120],
                     "source": h.source, "license": h.license, "language": h.language,
                     "frame": h.frame[:120]} for h in rows]
        return {"query_digest": _sha(self.query), "verdict": self.verdict,
                "backend": self.backend, "semantic": self.semantic,
                "indexed_items": self.indexed_items, "note": self.note,
                "surface_hits": hits(self.surface_hits), "frame_hits": hits(self.frame_hits)}


class PrecedentIndex:
    """Embeddings + labels over every indexable humor item on disk, cached."""

    def __init__(self, backend: Any = None, out_dir: Path = OUT_DIR,
                 corpora_dir: Path = CORPORA_DIR) -> None:
        self.backend = backend or pick_backend()
        self.out_dir = out_dir
        self.corpora_dir = corpora_dir
        cache_key = str(getattr(self.backend, "cache_key", self.backend.name))
        safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", cache_key)
        self.cache_path = out_dir / f"precedent_index_{safe_key}.json"
        self.items: dict[str, dict[str, Any]] = {}
        self._load_cache()
        self._collect()

    # -- storage -----------------------------------------------------------
    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                self.items = json.loads(self.cache_path.read_text(encoding="utf-8"))["items"]
            except (json.JSONDecodeError, KeyError):
                self.items = {}

    def save(self) -> None:
        self.out_dir.mkdir(exist_ok=True)
        self.cache_path.write_text(json.dumps({"backend": self.backend.name,
                                               "saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                               "items": self.items}, ensure_ascii=False),
                                   encoding="utf-8")

    # -- supply ------------------------------------------------------------
    def _collect(self) -> None:
        live: set[str] = set()
        for path in sorted(self.corpora_dir.glob("*.jsonl")):
            # Stream large harvests. `read_text().splitlines()` temporarily
            # duplicated the 887 MB caption file before the index itself was
            # allocated, turning a routine collect into a multi-gigabyte spike.
            try:
                with path.open(encoding="utf-8") as fh:
                    for i, line in enumerate(fh):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if "_meta" in rec:
                            continue
                        text = str(rec.get("text") or rec.get("joke") or "").strip()
                        if not text:
                            continue
                        iid = f"{path.stem}:{i}"
                        meta = (rec.get("meta", {})
                                if isinstance(rec.get("meta"), dict) else {})
                        digest = _sha(text)
                        live.add(digest)
                        self.items.setdefault(digest, {
                            "item_id": iid, "text": text,
                            "source": rec.get("source", path.stem),
                            "license": rec.get("license", "unknown"),
                            "language": meta.get("language", "en"),
                            "labels": {}, "surface": None, "frame_vec": None,
                        })
            except OSError:
                continue
        accepted = self.out_dir / "accepted_bits.jsonl"
        if accepted.exists():
            for line in accepted.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = rec.get("text", "").strip()
                if text:
                    live.add(_sha(text))
                    self.items.setdefault(_sha(text), {
                        "item_id": rec.get("bit_id", "accepted"), "text": text,
                        "source": "jestry accepted bit", "license": "project-internal",
                        "language": "en", "labels": {}, "surface": None, "frame_vec": None,
                    })
        # evict ghosts: cached entries whose text left the supply must not
        # keep serving "been done" verdicts (adversarial finding: 36 phantom
        # entries from an overwritten harvest file still matched at 1.0)
        ghosts = set(self.items) - live
        if ghosts:
            for key in ghosts:
                del self.items[key]
            self.save()

    # -- embedding ---------------------------------------------------------
    def ensure_embedded(self, batch: int = 32) -> dict[str, int]:
        todo = [(k, v) for k, v in self.items.items() if v.get("surface") is None]
        done = 0
        for i in range(0, len(todo), batch):
            chunk = todo[i:i + batch]
            vecs = self.backend.embed([v["text"] for _, v in chunk])
            if vecs is None:
                break
            for (k, v), vec in zip(chunk, vecs):
                v["surface"] = vec
                done += 1
        ftodo = [(k, v) for k, v in self.items.items()
                 if v.get("frame_vec") is None and v.get("labels", {}).get("frame")]
        fdone = 0
        for i in range(0, len(ftodo), batch):
            chunk = ftodo[i:i + batch]
            vecs = self.backend.embed([v["labels"]["frame"] for _, v in chunk])
            if vecs is None:
                break
            for (k, v), vec in zip(chunk, vecs):
                v["frame_vec"] = vec
                fdone += 1
        if done or fdone:
            self.save()
        return {"surface_embedded": done, "frame_embedded": fdone,
                "total_items": len(self.items)}

    # -- Gemma 4 labeling lane (selective enrichment) ----------------------
    def label_missing(self, provider: Any, limit: int = 10) -> dict[str, Any]:
        """provider needs .judge_json (Gemma 4 through Ollama, or any judge)."""
        labeled = 0
        receipts: list[dict[str, Any]] = []
        for key, item in self.items.items():
            if labeled >= limit:
                break
            if item.get("labels"):
                continue
            parsed = provider.judge_json(LABEL_PROMPT.format(text=item["text"][:600]))
            if not parsed or "frame" not in parsed:
                receipts.append({"item_id": item["item_id"], "status": "label_failed"})
                continue
            item["labels"] = {
                "frame": str(parsed.get("frame", ""))[:240],
                "mechanisms": [str(m) for m in (parsed.get("mechanisms") or [])][:3],
                "language": str(parsed.get("language", item.get("language", "en")))[:8],
                "cultural_cache": str(parsed.get("cultural_cache", ""))[:16],
                "taboo_topics": [str(t) for t in (parsed.get("taboo_topics") or [])][:4],
                "labeler": getattr(provider, "model", getattr(provider, "name", "unknown")),
            }
            item["frame_vec"] = None      # re-embed on next ensure_embedded
            labeled += 1
            receipts.append({"item_id": item["item_id"], "status": "labeled",
                             "frame": item["labels"]["frame"][:80]})
        if labeled:
            self.save()
        return {"labeled": labeled, "attempted": len(receipts), "log": receipts}

    # -- the question ------------------------------------------------------
    def been_done(self, text: str, frame_hint: str = "", k: int = 5) -> PrecedentReport:
        text = text.strip()
        qvecs = self.backend.embed([text] + ([frame_hint] if frame_hint else []))
        if qvecs is None:
            return PrecedentReport(query=text, verdict="index_unavailable",
                                   backend=self.backend.name, semantic=self.backend.semantic,
                                   indexed_items=len(self.items),
                                   note="embedding backend did not answer")
        qs, qf = qvecs[0], (qvecs[1] if frame_hint else None)
        surface: list[PrecedentHit] = []
        frames: list[PrecedentHit] = []
        for item in self.items.values():
            # Gemma's own label wins over the collect-time field when present
            lang = (item.get("labels", {}) or {}).get("language") or item.get("language", "en")
            if item.get("surface"):
                s = cosine(qs, item["surface"])
                surface.append(PrecedentHit(item["item_id"], item["text"], item["source"],
                                            item["license"], lang,
                                            "surface", s,
                                            item.get("labels", {}).get("frame", "")))
            fv = item.get("frame_vec")
            if fv and qf is not None:
                frames.append(PrecedentHit(item["item_id"], item["text"], item["source"],
                                           item["license"], item.get("language", "en"),
                                           "frame", cosine(qf, fv),
                                           item.get("labels", {}).get("frame", "")))
        surface.sort(key=lambda h: -h.score)
        frames.sort(key=lambda h: -h.score)
        embedded = sum(1 for it in self.items.values() if it.get("surface"))
        if embedded == 0:
            return PrecedentReport(query=text, verdict=f"index_unembedded (0/{len(self.items)} vectors)",
                                   backend=self.backend.name, semantic=self.backend.semantic,
                                   indexed_items=len(self.items),
                                   note="run ensure_embedded() first — nothing was actually searched")
        top_s = surface[0].score if surface else 0.0
        top_f = frames[0].score if frames else 0.0
        neighborhood = NEIGHBORHOOD_SEMANTIC if self.backend.semantic else NEIGHBORHOOD
        if top_s >= SURFACE_MATCH:
            verdict = "surface_match: this wording has been done in the indexed supply"
        elif top_f >= FRAME_MATCH:
            verdict = "frame_precedent: same comic engine exists in the indexed supply"
        elif max(top_s, top_f) >= neighborhood:
            verdict = "adjacent_neighborhood: related material exists — worth citing"
        else:
            verdict = f"no_precedent_found within the indexed supply of {len(self.items)} items"
        note = "" if self.backend.semantic else \
            "hash backend: token-overlap only — paraphrase precedent NOT detectable offline"
        if embedded < len(self.items):
            note = (note + f" | partial index: {embedded}/{len(self.items)} embedded").strip(" |")
        return PrecedentReport(query=text, verdict=verdict, backend=self.backend.name,
                               semantic=self.backend.semantic, indexed_items=len(self.items),
                               surface_hits=surface[:k], frame_hits=frames[:k], note=note)

    def cross_lingual(self, text: str, k: int = 5) -> list[PrecedentHit]:
        """Neighbors whose ORIGINAL language differs — the canon bridge."""
        report = self.been_done(text, k=max(k * 4, 16))
        return [h for h in report.surface_hits if h.language not in ("en", "", "und")][:k]


def quick_check(text: str, *, live: bool = True, out_dir: Path = OUT_DIR,
                corpora_dir: Path | None = None) -> dict[str, Any]:
    """One-call been-done check for jestry receipts. Never raises."""
    try:
        backend = pick_backend(prefer_semantic=live)
        kwargs = {"corpora_dir": corpora_dir} if corpora_dir is not None else {}
        idx = PrecedentIndex(backend=backend, out_dir=out_dir, **kwargs)
        idx.ensure_embedded()
        return idx.been_done(text).to_dict()
    except Exception as exc:                      # pragma: no cover - defensive
        return {"verdict": "precedent_check_failed", "error": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    import sys
    idx = PrecedentIndex()
    print(f"backend={idx.backend.name} semantic={idx.backend.semantic}")
    print("embed:", idx.ensure_embedded())
    query = " ".join(sys.argv[1:]) or \
        "I told my therapist about my fear of speed bumps. She said I'm slowly getting over it."
    rep = idx.been_done(query)
    print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False)[:2400])
