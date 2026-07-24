"""Shared records for humor data, reactions, and audience profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReactionSignal:
    """A normalized human or proxy reaction to one humor item."""

    signal_type: str
    value: float
    scale_min: float = 0.0
    scale_max: float = 10.0
    audience_segment: str = "unknown"
    source: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AudienceProfile:
    """Audience context used for retrieval and adaptation."""

    profile_id: str
    label: str
    description: str = ""
    demographics: dict[str, Any] = field(default_factory=dict)
    preferences: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    dominant_models: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        parts = [self.label, self.description]
        parts.extend(self.preferences)
        parts.extend(self.constraints)
        parts.extend(self.dominant_models)
        return " ".join(x for x in parts if x)


@dataclass
class HumorItem:
    """One text, transcript segment, visual item, or generated candidate."""

    source_id: str
    item_id: str
    text: str
    setup: str = ""
    punchline: str = ""
    context: str = ""
    audience: str = ""
    language: str = "en"
    modality: str = "text"
    labels: list[str] = field(default_factory=list)
    reactions: list[ReactionSignal] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def stable_id(self) -> str:
        return f"{self.source_id}:{self.item_id}"

    def searchable_text(self) -> str:
        parts = [
            self.text,
            self.setup,
            self.punchline,
            self.context,
            self.audience,
            self.language,
            self.modality,
            " ".join(self.labels),
        ]
        for reaction in self.reactions:
            parts.extend([reaction.signal_type, reaction.audience_segment, reaction.notes])
        return " ".join(x for x in parts if x)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reactions"] = [r.to_dict() for r in self.reactions]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HumorItem":
        reactions = [ReactionSignal(**r) for r in data.get("reactions", [])]
        payload = dict(data)
        payload["reactions"] = reactions
        return cls(**payload)
