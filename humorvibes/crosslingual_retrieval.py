"""Frozen cross-language retrieval fixture from public-domain aligned proverbs."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .errors import IntegrationError
from .retrieval_benchmark import _canonical_digest


BENCHMARK_VERSION = "crosslingual-proverbs-1.0.0"
SOURCE_NAME = "gutenberg:51090 A Polyglot of Foreign Proverbs"
SOURCE_URL = "https://www.gutenberg.org/ebooks/51090"
LANGUAGES = ("da", "de", "es", "fr", "it", "nl", "pt")


def _error(code: str, message: str, *, detail: dict[str, Any] | None = None) -> IntegrationError:
    return IntegrationError(code, message, 422, detail=detail)


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", value.strip()) if isinstance(value, str) else ""


def read_aligned_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    """Read the immutable aligned-pair export and return its byte digest."""

    payload = Path(path).read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise _error(
                "invalid_crosslingual_jsonl",
                f"Malformed JSON on line {line_number} of {Path(path).name}.",
            ) from exc
        if not isinstance(row, dict):
            raise _error("invalid_crosslingual_jsonl", "Aligned-pair rows must be objects.")
        rows.append(row)
    return rows, hashlib.sha256(payload).hexdigest()


def build_crosslingual_retrieval(
    rows: Iterable[dict[str, Any]],
    *,
    source_snapshot_sha256: str,
    pairs_per_language: int = 70,
) -> dict[str, Any]:
    """Select a deterministic balanced evaluation cohort and freeze its qrels."""

    if not re.fullmatch(r"[0-9a-f]{64}", source_snapshot_sha256):
        raise _error("invalid_crosslingual_snapshot", "The source snapshot needs a SHA-256 digest.")
    if not 20 <= pairs_per_language <= 500:
        raise _error("invalid_crosslingual_sample_size", "Use 20 through 500 pairs per language.")
    candidates: dict[str, list[dict[str, str]]] = {language: [] for language in LANGUAGES}
    seen_source: set[tuple[str, str]] = set()
    seen_translation: set[str] = set()
    rejected = Counter()
    for raw in rows:
        language = _clean(raw.get("language")).lower()
        source_text = _clean(raw.get("text"))
        translation = _clean(raw.get("translation_en"))
        if language not in candidates:
            rejected["unsupported_language"] += 1
            continue
        if raw.get("source") != SOURCE_NAME or raw.get("licence_class") != "redistributable":
            raise _error(
                "invalid_crosslingual_rights",
                "Every selected pair must retain the reviewed Gutenberg source and redistributable class.",
            )
        if not 3 <= len(source_text) <= 300 or not 3 <= len(translation) <= 300:
            rejected["length"] += 1
            continue
        source_key = (language, source_text.casefold())
        translation_key = translation.casefold()
        if source_key in seen_source or translation_key in seen_translation:
            rejected["duplicate"] += 1
            continue
        seen_source.add(source_key)
        seen_translation.add(translation_key)
        pair_digest = hashlib.sha256(
            f"{BENCHMARK_VERSION}|{language}|{source_text}|{translation}".encode("utf-8")
        ).hexdigest()
        candidates[language].append(
            {
                "language": language,
                "source_text": source_text,
                "translation_en": translation,
                "pair_digest": pair_digest,
                "license": _clean(raw.get("license")),
            }
        )

    selected: list[dict[str, str]] = []
    for language in LANGUAGES:
        language_rows = sorted(candidates[language], key=lambda row: row["pair_digest"])
        if len(language_rows) < pairs_per_language:
            raise _error(
                "insufficient_crosslingual_pairs",
                "A required language does not have enough unique aligned pairs.",
                detail={
                    "language": language,
                    "available": len(language_rows),
                    "required": pairs_per_language,
                },
            )
        for position, row in enumerate(language_rows[:pairs_per_language]):
            validation_start = pairs_per_language * 8 // 10
            test_start = pairs_per_language * 9 // 10
            split = "train" if position < validation_start else "validation" if position < test_start else "test"
            selected.append({**row, "split": split})

    documents: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    qrels: list[dict[str, Any]] = []
    for row in sorted(selected, key=lambda value: (value["language"], value["pair_digest"])):
        suffix = row["pair_digest"][:20]
        pair_id = f"xlp_{suffix}"
        document_id = f"xld_{suffix}"
        query_id = f"xlq_{suffix}"
        documents.append(
            {
                "document_id": document_id,
                "pair_id": pair_id,
                "text": row["translation_en"],
                "language": "en",
                "source_language": row["language"],
                "split": row["split"],
                "source": SOURCE_NAME,
                "license": row["license"],
            }
        )
        queries.append(
            {
                "query_id": query_id,
                "pair_id": pair_id,
                "text": row["source_text"],
                "language": row["language"],
                "target_language": "en",
                "split": row["split"],
                "source": SOURCE_NAME,
                "license": row["license"],
            }
        )
        qrels.append({"query_id": query_id, "document_id": document_id, "relevance": 2})

    counts_by_language = Counter(row["language"] for row in queries)
    split_language_counts = {
        split: dict(
            sorted(Counter(row["language"] for row in queries if row["split"] == split).items())
        )
        for split in ("train", "validation", "test")
    }
    manifest = {
        "receipt_type": "humorvibes_crosslingual_retrieval_manifest",
        "receipt_version": 1,
        "benchmark_version": BENCHMARK_VERSION,
        "source_snapshot": {
            "name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "input_sha256": source_snapshot_sha256,
            "copyright_status": "Public domain in the USA per Project Gutenberg ebook 51090",
            "jurisdiction_warning": "Reusers outside the USA must verify local copyright status.",
        },
        "selection": {
            "method": "lowest SHA-256 pair digests after global English-translation deduplication",
            "pairs_per_language": pairs_per_language,
            "language_order": list(LANGUAGES),
            "split_within_language": "first 80 percent train, next 10 percent validation, final 10 percent test after digest sort",
            "rejected_before_selection": dict(sorted(rejected.items())),
        },
        "counts": {
            "documents": len(documents),
            "queries": len(queries),
            "qrels": len(qrels),
            "hard_negative_rows": 0,
            "by_source_language": dict(sorted(counts_by_language.items())),
            "by_split_and_language": split_language_counts,
        },
        "relations": {
            "qrel_origin": "paired foreign proverb and English translation in the historical source",
            "candidate_pool": "all English translations inside the same frozen split",
        },
        "truth_boundary": {
            "human_funniness_labels": False,
            "modern_native_review": False,
            "translation_quality_revalidated": False,
            "qrels_are_historical_editorial_alignments": True,
            "allowed_claim": "cross-language retrieval performance on frozen historical proverb-translation pairs",
        },
    }
    manifest["content_digest"] = _canonical_digest(
        {"documents": documents, "queries": queries, "qrels": qrels, "negatives": []}
    )
    return {
        "documents": documents,
        "queries": queries,
        "qrels": qrels,
        "hard_negatives": [],
        "manifest": manifest,
    }
