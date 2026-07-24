"""Dependency-light humor embeddings.

This prototype uses deterministic hashed vectors so the datacenter works offline.
The API is intentionally narrow: a production version can swap these functions
for Gemma embeddings, sentence-transformers, or a hosted embedding endpoint.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable

from .schema import HumorItem


TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def hash_embedding(text: str | Iterable[str], dims: int = 128) -> list[float]:
    if not isinstance(text, str):
        text = " ".join(str(x) for x in text)
    vec = [0.0] * dims
    for token in tokenize(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + min(len(token), 12) / 12.0
        vec[bucket] += sign * weight
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def channel_texts(item: HumorItem) -> dict[str, str]:
    reaction_text = " ".join(
        f"{r.signal_type} {r.value} {r.audience_segment} {r.notes}" for r in item.reactions
    )
    risk_terms = " ".join(
        str(x)
        for x in [
            item.metadata.get("bad_surprise_notes", ""),
            item.metadata.get("risk_flags", ""),
            item.metadata.get("appropriateness", ""),
            item.metadata.get("offense", ""),
            item.metadata.get("confusion", ""),
        ]
    )
    return {
        "text": item.searchable_text(),
        "structure": " ".join([item.setup, item.punchline, " ".join(item.labels)]),
        "audience": " ".join([item.audience, item.context, " ".join(item.labels)]),
        "reaction": reaction_text,
        "risk": risk_terms,
    }


def item_embeddings(item: HumorItem, dims: int = 128) -> dict[str, list[float]]:
    return {channel: hash_embedding(text, dims=dims) for channel, text in channel_texts(item).items()}
