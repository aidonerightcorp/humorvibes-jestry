"""Hard retrieval contracts and provider-neutral evaluation for Open Controls.

The qrels encode generator lineage, not human relevance or funniness judgments.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from .embeddings import EmbeddingRegistry, TOKEN_RE, cosine_similarity
from .errors import IntegrationError
from .open_controls import FRAME_SPECS, SITUATIONS


HARD_BENCHMARK_VERSION = "1.0.0"
CONTEXT_CLUES = {
    "job_fair": "an event where available work and qualifications are discussed",
    "counseling": "a civic office visit about a recurring concern and practical options",
    "planning": "a public agenda review about assigned responsibilities",
    "contest": "a neighborhood competition where entry rules are reviewed",
    "class": "an after-hours learning session with a short presentation",
    "membership": "a local association intake about duties and admission",
    "dinner": "a communal evening meal with a scheduled conversation",
    "help_desk": "a city support counter handling a routine request",
    "hearing": "a municipal testimony session entered into the public record",
    "workshop": "a practical weekend course confirming materials and a booking",
}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "for", "from", "in",
    "into", "is", "it", "of", "on", "or", "that", "the", "their", "then", "this", "to",
    "was", "were", "where", "while", "with",
}


def _error(code: str, message: str, *, detail: dict[str, Any] | None = None) -> IntegrationError:
    return IntegrationError(code, message, 422, detail=detail)


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _tokens(text: str, *, content_only: bool = False) -> list[str]:
    values = [match.group(0).casefold() for match in TOKEN_RE.finditer(text)]
    if content_only:
        return [token for token in values if len(token) > 2 and token not in STOPWORDS]
    return values


def _masked_phrase(text: str, forbidden: list[str]) -> str:
    rendered = text
    for term in forbidden:
        rendered = re.sub(rf"\b{re.escape(term)}\b", "a related technical concept", rendered, flags=re.IGNORECASE)
    return rendered


def _situation_for_document(text: str) -> str:
    matches = [situation.key for situation in SITUATIONS if situation.place.casefold() in text.casefold()]
    if len(matches) != 1:
        raise _error(
            "hard_query_context_unresolved",
            "Each retrieval document must contain exactly one controlled situation place.",
            detail={"matches": matches},
        )
    return matches[0]


def build_hard_retrieval_rows(
    documents: Iterable[dict[str, Any]],
    queries: Iterable[dict[str, Any]],
    qrels: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Derive masked semantic queries and explicit hard negatives from a release contract."""

    docs = [dict(row) for row in documents]
    source_queries = [dict(row) for row in queries]
    source_qrels = [dict(row) for row in qrels]
    if not docs or len(docs) != len(source_queries) or len(docs) != len(source_qrels):
        raise _error(
            "invalid_retrieval_contract",
            "Documents, queries, and qrels must be non-empty and aligned in count.",
        )
    document_by_id = {str(row.get("document_id")): row for row in docs}
    query_by_id = {str(row.get("query_id")): row for row in source_queries}
    if len(document_by_id) != len(docs) or len(query_by_id) != len(source_queries):
        raise _error("duplicate_retrieval_id", "Document and query IDs must be unique.")
    relation_by_query: dict[str, str] = {}
    for row in source_qrels:
        query_id = str(row.get("query_id", ""))
        document_id = str(row.get("document_id", ""))
        if query_id not in query_by_id or document_id not in document_by_id or query_id in relation_by_query:
            raise _error(
                "invalid_retrieval_qrel",
                "Every qrel must map one known query to one known document.",
            )
        relation_by_query[query_id] = document_id
    if set(relation_by_query) != set(query_by_id):
        raise _error("invalid_retrieval_qrel", "Every source query requires exactly one qrel.")

    frames = {f"lexical_{frame.key}": frame for frame in FRAME_SPECS}
    enriched: list[dict[str, Any]] = []
    for row in docs:
        family = str(row.get("template_family_id", ""))
        frame = frames.get(family)
        if frame is None:
            raise _error("unknown_retrieval_family", "Hard queries require a known controlled frame family.")
        if str(row.get("split", "")) not in {"train", "validation", "test"}:
            raise _error("invalid_retrieval_split", "Retrieval rows require train, validation, or test split.")
        enriched.append(
            {
                **row,
                "situation_key": _situation_for_document(str(row.get("text", ""))),
                "frame": frame,
            }
        )

    docs_by_family: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    docs_by_context: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        docs_by_family[(str(row["split"]), str(row["template_family_id"]))].append(row)
        docs_by_context[(str(row["split"]), str(row["situation_key"]))].append(row)
    for values in [*docs_by_family.values(), *docs_by_context.values()]:
        values.sort(key=lambda item: str(item["document_id"]))

    hard_queries: list[dict[str, Any]] = []
    hard_qrels: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []
    lexical_overlaps: list[float] = []
    forbidden_leaks: list[dict[str, str]] = []
    original_query_by_document = {
        document_id: query_by_id[query_id] for query_id, document_id in relation_by_query.items()
    }
    for row in sorted(enriched, key=lambda item: str(item["document_id"])):
        frame = row["frame"]
        context = CONTEXT_CLUES[str(row["situation_key"])]
        forbidden = [frame.entity, frame.pivot_a, frame.pivot_b]
        sense_a = _masked_phrase(frame.sense_a, forbidden)
        sense_b = _masked_phrase(frame.sense_b, forbidden)
        text = (
            f"Retrieve the compact repaired item set around {context}. "
            f"Its hidden lexical frame links {sense_a} with {sense_b} in the {frame.domain} "
            f"domain. Prefer a concise double reading over an explicit explanation."
        )
        source_query = original_query_by_document[str(row["document_id"])]
        query_id = "hard_" + hashlib.sha256(
            f"{HARD_BENCHMARK_VERSION}|{source_query['query_id']}".encode("utf-8")
        ).hexdigest()[:20]
        leaks = [value for value in forbidden if re.search(rf"\b{re.escape(value)}\b", text, re.IGNORECASE)]
        if leaks:
            forbidden_leaks.extend({"query_id": query_id, "term": leak} for leak in leaks)
        query_tokens = set(_tokens(text, content_only=True))
        document_tokens = set(_tokens(str(row["text"]), content_only=True))
        overlap = len(query_tokens & document_tokens) / max(1, len(query_tokens | document_tokens))
        lexical_overlaps.append(overlap)

        same_family = [
            candidate
            for candidate in docs_by_family[(str(row["split"]), str(row["template_family_id"]))]
            if candidate["document_id"] != row["document_id"]
        ]
        same_context = [
            candidate
            for candidate in docs_by_context[(str(row["split"]), str(row["situation_key"]))]
            if candidate["template_family_id"] != row["template_family_id"]
        ]
        if not same_family or not same_context:
            raise _error(
                "hard_negative_unavailable",
                "Each hard query requires same-frame and same-context negatives inside its split.",
            )
        family_negative = same_family[0]
        context_negative = same_context[0]
        hard_queries.append(
            {
                "query_id": query_id,
                "text": text,
                "premise_id": row["premise_id"],
                "template_family_id": row["template_family_id"],
                "situation_key": row["situation_key"],
                "split": row["split"],
                "query_contract": "masked_entity_and_pivots_semantic_frame_v1",
            }
        )
        hard_qrels.append(
            {"query_id": query_id, "document_id": row["document_id"], "relevance": 2}
        )
        hard_negatives.append(
            {
                "query_id": query_id,
                "same_frame_different_context_document_id": family_negative["document_id"],
                "same_context_different_frame_document_id": context_negative["document_id"],
            }
        )

    public_documents = [
        {key: value for key, value in row.items() if key != "frame"} for row in enriched
    ]
    manifest = {
        "receipt_type": "humorvibes_hard_retrieval_manifest",
        "receipt_version": 1,
        "benchmark_version": HARD_BENCHMARK_VERSION,
        "counts": {
            "documents": len(public_documents),
            "queries": len(hard_queries),
            "qrels": len(hard_qrels),
            "hard_negative_rows": len(hard_negatives),
        },
        "splits": dict(sorted(Counter(row["split"] for row in hard_queries).items())),
        "leakage_audit": {
            "entity_or_pivot_leaks": len(forbidden_leaks),
            "maximum_content_token_jaccard_to_relevant_document": max(lexical_overlaps),
            "mean_content_token_jaccard_to_relevant_document": sum(lexical_overlaps) / len(lexical_overlaps),
            "template_family_crosses_splits": any(
                len({row["split"] for row in hard_queries if row["template_family_id"] == family}) > 1
                for family in {row["template_family_id"] for row in hard_queries}
            ),
        },
        "relations": {
            "relevance_origin": "deterministic generator lineage",
            "same_frame_negative": "same lexical frame, different controlled situation",
            "same_context_negative": "same controlled situation, different lexical frame",
        },
        "truth_boundary": {
            "human_relevance_judgments": False,
            "human_funniness_labels": False,
            "semantic_model_quality_established": False,
            "allowed_use": "provider-comparative retrieval evaluation against frozen generator relations",
        },
    }
    manifest["content_digest"] = _canonical_digest(
        {
            "documents": public_documents,
            "queries": hard_queries,
            "qrels": hard_qrels,
            "negatives": hard_negatives,
        }
    )
    if (
        manifest["leakage_audit"]["entity_or_pivot_leaks"]
        or manifest["leakage_audit"]["template_family_crosses_splits"]
    ):
        raise _error(
            "hard_retrieval_leakage",
            "Hard retrieval leakage audit failed.",
            detail={
                "forbidden_leaks": forbidden_leaks[:20],
                "template_family_crosses_splits": manifest["leakage_audit"][
                    "template_family_crosses_splits"
                ],
            },
        )
    return {
        "documents": public_documents,
        "queries": hard_queries,
        "qrels": hard_qrels,
        "hard_negatives": hard_negatives,
        "manifest": manifest,
    }


def _tfidf_vectors(
    document_texts: list[str], query_texts: list[str]
) -> tuple[list[list[float]], list[list[float]], int]:
    tokenized = [_tokens(text) for text in document_texts + query_texts]
    vocabulary = sorted({token for row in tokenized for token in row})
    positions = {token: index for index, token in enumerate(vocabulary)}
    document_frequency = Counter(token for row in tokenized for token in set(row))
    total = len(tokenized)

    def vector(tokens: list[str]) -> list[float]:
        counts = Counter(tokens)
        values = [0.0] * len(vocabulary)
        for token, count in counts.items():
            tf = 1.0 + math.log(count)
            inverse = math.log((1.0 + total) / (1.0 + document_frequency[token])) + 1.0
            values[positions[token]] = tf * inverse
        norm = math.sqrt(sum(value * value for value in values))
        return [value / norm for value in values]

    vectors = [vector(row) for row in tokenized]
    return vectors[: len(document_texts)], vectors[len(document_texts) :], len(vocabulary)


def _embed_all(
    registry: EmbeddingRegistry, texts: list[str], model_id: str
) -> tuple[list[list[float]], dict[str, Any]]:
    vectors: list[list[float]] = []
    metadata: dict[str, Any] | None = None
    batch_durations: list[float] = []
    batch_size = int(registry.settings.max_batch_items)
    for start in range(0, len(texts), batch_size):
        batch_started = time.perf_counter()
        result = registry.embed(texts[start : start + batch_size], model_id=model_id)
        batch_durations.append(time.perf_counter() - batch_started)
        current = result.public(include_vectors=False)
        if metadata is None:
            metadata = current
        elif current["dimensions"] != metadata["dimensions"]:
            raise _error(
                "embedding_dimension_changed",
                "Embedding dimensions changed between benchmark batches.",
            )
        vectors.extend(result.vectors)
    if metadata is None:
        raise _error("empty_retrieval_benchmark", "No texts were available for embedding.")
    metadata = {**metadata, "count": len(vectors)}
    ordered = sorted(batch_durations)
    total_duration = sum(batch_durations)
    metadata["performance"] = {
        "batch_count": len(batch_durations),
        "batch_size_limit": batch_size,
        "embedding_duration_seconds": total_duration,
        "texts_per_second": len(vectors) / total_duration if total_duration else None,
        "batch_latency_seconds": {
            "minimum": ordered[0],
            "median": median(ordered),
            "p95": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
            "maximum": ordered[-1],
        },
    }
    return vectors, metadata


def _bootstrap_metric_intervals(
    rows: list[dict[str, Any]], *, seed_material: str, samples: int = 2000
) -> dict[str, list[float]]:
    """Deterministic percentile intervals over the frozen query rows."""

    if not rows:
        return {}
    values = {
        "MRR": [float(row["reciprocal_rank"]) for row in rows],
        "Recall@1": [float(row["rank"] <= 1) for row in rows],
        "Recall@5": [float(row["rank"] <= 5) for row in rows],
        "Recall@10": [float(row["rank"] <= 10) for row in rows],
        "nDCG@10": [float(row["ndcg_at_10"]) for row in rows],
    }
    seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    output: dict[str, list[float]] = {}
    for name, metric_values in values.items():
        draws = sorted(
            sum(metric_values[rng.randrange(len(metric_values))] for _ in metric_values)
            / len(metric_values)
            for _ in range(samples)
        )
        output[name] = [
            draws[int(samples * 0.025)],
            draws[min(samples - 1, int(samples * 0.975))],
        ]
    return output


def evaluate_retrieval(
    dataset: dict[str, Any],
    *,
    model_id: str = "lexical:tfidf",
    registry: EmbeddingRegistry | None = None,
    record_duration: bool = True,
) -> dict[str, Any]:
    """Evaluate a lexical or configured embedding model against frozen hard qrels."""

    documents = [dict(row) for row in dataset["documents"]]
    queries = [dict(row) for row in dataset["queries"]]
    qrels = [dict(row) for row in dataset["qrels"]]
    negatives = [dict(row) for row in dataset.get("hard_negatives", [])]
    if not documents or not queries or len(queries) != len(qrels):
        raise _error(
            "invalid_retrieval_contract",
            "Benchmark documents, queries, and qrels are required.",
        )
    document_ids = [str(row.get("document_id", "")) for row in documents]
    query_ids = [str(row.get("query_id", "")) for row in queries]
    if len(set(document_ids)) != len(document_ids) or len(set(query_ids)) != len(query_ids):
        raise _error("duplicate_retrieval_id", "Benchmark IDs must be unique.")
    relevant = {str(row.get("query_id")): str(row.get("document_id")) for row in qrels}
    if set(relevant) != set(query_ids) or not set(relevant.values()).issubset(document_ids):
        raise _error("invalid_retrieval_qrel", "Qrels must map every query to one known document.")
    negative_by_query = {str(row["query_id"]): row for row in negatives}
    if negatives and (
        len(negative_by_query) != len(negatives) or set(negative_by_query) != set(query_ids)
    ):
        raise _error("invalid_hard_negatives", "Hard-negative rows must cover every query exactly once.")

    started = time.perf_counter()
    document_vectors: dict[str, list[float]] = {}
    query_vectors: dict[str, list[float]] = {}
    if model_id == "lexical:tfidf":
        dimensions_by_split: dict[str, int] = {}
        for split in sorted({str(row["split"]) for row in queries}):
            split_documents = [row for row in documents if str(row["split"]) == split]
            split_queries = [row for row in queries if str(row["split"]) == split]
            doc_vectors, query_values, dimensions = _tfidf_vectors(
                [str(row["text"]) for row in split_documents],
                [str(row["text"]) for row in split_queries],
            )
            dimensions_by_split[split] = dimensions
            document_vectors.update(
                {str(row["document_id"]): vector for row, vector in zip(split_documents, doc_vectors, strict=True)}
            )
            query_vectors.update(
                {str(row["query_id"]): vector for row, vector in zip(split_queries, query_values, strict=True)}
            )
        model = {
            "model_id": model_id,
            "provider": "stdlib-tfidf",
            "dimensions_by_split": dimensions_by_split,
            "normalized": True,
            "semantic": False,
        }
    else:
        registry_value = registry or EmbeddingRegistry()
        texts = [str(row["text"]) for row in documents] + [str(row["text"]) for row in queries]
        vectors, metadata = _embed_all(registry_value, texts, model_id)
        document_vectors.update(
            {document_id: vector for document_id, vector in zip(document_ids, vectors[: len(documents)], strict=True)}
        )
        query_vectors.update(
            {query_id: vector for query_id, vector in zip(query_ids, vectors[len(documents) :], strict=True)}
        )
        model = {**metadata, "semantic": model_id != "hash:128"}
        if not record_duration:
            # Release baselines are byte-recomputed by the verifier. Runtime timing is useful
            # for live provider receipts but cannot be part of a deterministic release file.
            model.pop("performance", None)

    per_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_query: list[dict[str, Any]] = []
    for query in queries:
        query_id = str(query["query_id"])
        split = str(query["split"])
        candidate_ids = [
            str(row["document_id"]) for row in documents if str(row["split"]) == split
        ]
        scores = [
            (cosine_similarity(query_vectors[query_id], document_vectors[document_id]), document_id)
            for document_id in candidate_ids
        ]
        scores.sort(key=lambda pair: (-pair[0], pair[1]))
        ranked = [document_id for _, document_id in scores]
        target = relevant[query_id]
        rank = ranked.index(target) + 1
        row: dict[str, Any] = {
            "query_id": query_id,
            "split": split,
            "language": str(query.get("language") or "und"),
            "rank": rank,
            "reciprocal_rank": 1.0 / rank,
            "ndcg_at_10": 1.0 / math.log2(rank + 1) if rank <= 10 else 0.0,
        }
        hard = negative_by_query.get(query_id)
        if hard:
            family_id = str(hard["same_frame_different_context_document_id"])
            context_id = str(hard["same_context_different_frame_document_id"])
            if family_id not in ranked or context_id not in ranked:
                raise _error(
                    "invalid_hard_negatives",
                    "Hard negatives must reference documents inside the query split.",
                )
            row.update(
                {
                    "beats_same_frame_negative": rank < ranked.index(family_id) + 1,
                    "beats_same_context_negative": rank < ranked.index(context_id) + 1,
                }
            )
        per_query.append(row)
        per_split[split].append(row)

    benchmark_digest = dataset.get("manifest", {}).get(
        "content_digest", _canonical_digest(dataset)
    )

    def metrics(rows: list[dict[str, Any]], *, slice_id: str) -> dict[str, Any]:
        result = {
            "queries": len(rows),
            "MRR": sum(row["reciprocal_rank"] for row in rows) / len(rows),
            "Recall@1": sum(row["rank"] <= 1 for row in rows) / len(rows),
            "Recall@5": sum(row["rank"] <= 5 for row in rows) / len(rows),
            "Recall@10": sum(row["rank"] <= 10 for row in rows) / len(rows),
            "nDCG@10": sum(row["ndcg_at_10"] for row in rows) / len(rows),
            "median_rank": median(row["rank"] for row in rows),
        }
        if rows and "beats_same_frame_negative" in rows[0]:
            result["beats_same_frame_hard_negative_rate"] = sum(
                row["beats_same_frame_negative"] for row in rows
            ) / len(rows)
            result["beats_same_context_hard_negative_rate"] = sum(
                row["beats_same_context_negative"] for row in rows
            ) / len(rows)
        result["bootstrap_95pct_ci"] = _bootstrap_metric_intervals(
            rows,
            seed_material=f"{benchmark_digest}|{model_id}|{slice_id}",
        )
        return result

    language_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in per_query:
        language_rows[str(row["language"])].append(row)
    failure_slices: dict[str, Any] = {
        "rank_above_10": {
            "queries": sum(row["rank"] > 10 for row in per_query),
            "rate": sum(row["rank"] > 10 for row in per_query) / len(per_query),
        },
        "not_ranked_first": {
            "queries": sum(row["rank"] > 1 for row in per_query),
            "rate": sum(row["rank"] > 1 for row in per_query) / len(per_query),
        },
    }
    if negatives:
        failure_slices.update(
            {
                "lost_to_same_frame_negative": {
                    "queries": sum(not row["beats_same_frame_negative"] for row in per_query),
                    "rate": sum(not row["beats_same_frame_negative"] for row in per_query)
                    / len(per_query),
                },
                "lost_to_same_context_negative": {
                    "queries": sum(not row["beats_same_context_negative"] for row in per_query),
                    "rate": sum(not row["beats_same_context_negative"] for row in per_query)
                    / len(per_query),
                },
            }
        )

    result = {
        "receipt_type": "humorvibes_retrieval_benchmark",
        "receipt_version": 1,
        "benchmark_version": dataset.get("manifest", {}).get("benchmark_version", "unknown"),
        "benchmark_digest": benchmark_digest,
        "frozen_input_digests": {
            "documents": _canonical_digest(documents),
            "queries": _canonical_digest(queries),
            "qrels": _canonical_digest(qrels),
            "hard_negatives": _canonical_digest(negatives),
        },
        "model": model,
        "metrics_by_split": {
            split: metrics(rows, slice_id=f"split:{split}")
            for split, rows in sorted(per_split.items())
        },
        "metrics_by_language": {
            language: metrics(rows, slice_id=f"language:{language}")
            for language, rows in sorted(language_rows.items())
        },
        "failure_slices": failure_slices,
        "overall": metrics(per_query, slice_id="overall"),
        "truth_boundary": {
            "qrels_are_human_judgments": False,
            "retrieval_quality_is_funniness": False,
            "provider_availability_is_model_quality": False,
            "allowed_claim": "measured retrieval performance on frozen generator-lineage relations",
        },
    }
    if record_duration:
        result["duration_seconds"] = time.perf_counter() - started
    digest_payload = {key: value for key, value in result.items() if key != "duration_seconds"}
    if isinstance(digest_payload.get("model"), dict):
        digest_payload["model"] = {
            key: value for key, value in digest_payload["model"].items() if key != "performance"
        }
    result["receipt_digest"] = _canonical_digest(digest_payload)
    result["receipt_digest_excludes_runtime_timing"] = True
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise _error(
                "invalid_retrieval_jsonl",
                f"Invalid JSON at {path.name}:{line_number}.",
            ) from exc
        if not isinstance(value, dict):
            raise _error(
                "invalid_retrieval_jsonl",
                f"Rows at {path.name}:{line_number} must be objects.",
            )
        values.append(value)
    return values


def load_retrieval_dataset(root: Path) -> dict[str, Any]:
    return {
        "documents": read_jsonl(root / "hard_retrieval_documents.jsonl"),
        "queries": read_jsonl(root / "hard_retrieval_queries.jsonl"),
        "qrels": read_jsonl(root / "hard_retrieval_qrels.jsonl"),
        "hard_negatives": read_jsonl(root / "hard_retrieval_negatives.jsonl"),
        "manifest": json.loads(
            (root / "hard_retrieval_manifest.json").read_text(encoding="utf-8")
        ),
    }


def write_retrieval_dataset(
    root: Path, dataset: dict[str, Any], *, overwrite: bool = False
) -> dict[str, Any]:
    targets = {
        "hard_retrieval_documents.jsonl": dataset["documents"],
        "hard_retrieval_queries.jsonl": dataset["queries"],
        "hard_retrieval_qrels.jsonl": dataset["qrels"],
        "hard_retrieval_negatives.jsonl": dataset["hard_negatives"],
    }
    paths = [root / name for name in (*targets, "hard_retrieval_manifest.json")]
    if not overwrite and any(path.exists() for path in paths):
        raise _error(
            "retrieval_dataset_exists",
            "Refusing to replace an existing hard retrieval dataset.",
        )
    root.mkdir(parents=True, exist_ok=True)
    for name, rows in targets.items():
        (root / name).write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
                for row in rows
            ),
            encoding="utf-8",
        )
    (root / "hard_retrieval_manifest.json").write_text(
        json.dumps(dataset["manifest"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dataset["manifest"]
