"""Small SQLite-backed store for humor items and vector channels."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .embedding import cosine, hash_embedding, item_embeddings
from .schema import HumorItem


@dataclass
class SearchHit:
    item: HumorItem
    score: float
    channel: str


class HumorDataCenter:
    """A lightweight local store that can be replaced by a vector DB later."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.create()

    def create(self) -> None:
        self.conn.execute(
            """
            create table if not exists humor_items (
                stable_id text primary key,
                source_id text not null,
                item_id text not null,
                language text not null,
                modality text not null,
                payload text not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists humor_embeddings (
                stable_id text not null,
                channel text not null,
                vector text not null,
                primary key (stable_id, channel)
            )
            """
        )
        self.conn.commit()

    def upsert_item(self, item: HumorItem) -> None:
        payload = json.dumps(item.to_dict(), sort_keys=True)
        self.conn.execute(
            """
            insert into humor_items (stable_id, source_id, item_id, language, modality, payload)
            values (?, ?, ?, ?, ?, ?)
            on conflict(stable_id) do update set
                source_id=excluded.source_id,
                item_id=excluded.item_id,
                language=excluded.language,
                modality=excluded.modality,
                payload=excluded.payload
            """,
            (item.stable_id(), item.source_id, item.item_id, item.language, item.modality, payload),
        )
        for channel, vector in item_embeddings(item).items():
            self.conn.execute(
                """
                insert into humor_embeddings (stable_id, channel, vector)
                values (?, ?, ?)
                on conflict(stable_id, channel) do update set vector=excluded.vector
                """,
                (item.stable_id(), channel, json.dumps(vector)),
            )
        self.conn.commit()

    def add_items(self, items: list[HumorItem]) -> None:
        for item in items:
            self.upsert_item(item)

    def item_count(self) -> int:
        row = self.conn.execute("select count(*) as n from humor_items").fetchone()
        return int(row["n"])

    def get_item(self, stable_id: str) -> HumorItem | None:
        row = self.conn.execute("select payload from humor_items where stable_id = ?", (stable_id,)).fetchone()
        if not row:
            return None
        return HumorItem.from_dict(json.loads(row["payload"]))

    def search(self, query: str, channel: str = "text", top_k: int = 5) -> list[SearchHit]:
        qvec = hash_embedding(query)
        rows = self.conn.execute(
            "select stable_id, vector from humor_embeddings where channel = ?",
            (channel,),
        ).fetchall()
        hits: list[SearchHit] = []
        for row in rows:
            item = self.get_item(str(row["stable_id"]))
            if not item:
                continue
            score = cosine(qvec, json.loads(row["vector"]))
            hits.append(SearchHit(item=item, score=round(score, 4), channel=channel))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def close(self) -> None:
        self.conn.close()
