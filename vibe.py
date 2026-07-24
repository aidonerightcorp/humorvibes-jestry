"""Vibe measurement (THEORY.md §8): the tuning state of a mesh, quantified.

A vibe decomposes into REGISTER (coordinates on interpretable contrast axes),
OPENNESS (entropy of acceptable continuations — the room's risk budget), and
DRIFT (how a line moves the room). All three are read off the same local Gemma
used for surprisal; hosted APIs can't serve hidden states or next-token
distributions, so vibe measurement is a local-instrument capability by design.

Providers without embeddings (offline stub) return flagged pseudo-vibes so the
UI stays demoable.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any

# Each axis: (name, negative-pole anchors, positive-pole anchors).
# Anchors are deliberately short and content-generic: they define REGISTER, not topic.
AXES: list[tuple[str, list[str], list[str]]] = [
    ("formal_casual",
     ["Pursuant to the agenda, we will now review the quarterly compliance items.",
      "Please find attached the minutes of the previous meeting for your approval.",
      "The committee respectfully requests that all members submit their reports."],
     ["lol ok so anyway that meeting was a whole thing",
      "dude you will not BELIEVE what just happened",
      "ok real talk, grab a seat, this is so dumb"]),
    ("cold_warm",
     ["Your request has been denied. Do not contact this office again.",
      "That is not my problem. Take it up with someone who cares.",
      "Incorrect. Next question."],
     ["oh I'm so glad you're here, we saved you a seat!",
      "take your time, sweetheart, we've got all evening.",
      "you did great, seriously, everyone loved it."]),
    ("sincere_ironic",
     ["I mean this from the bottom of my heart: thank you for everything.",
      "This is genuinely the most important day of my life.",
      "I am truly grateful for this community."],
     ["oh yeah, because THAT worked so well last time.",
      "sure, another meeting will definitely fix it. definitely.",
      "wow, what a totally normal and fine situation this is."]),
    ("lowenergy_highenergy",
     ["so... yeah. that's about it, I guess. anyway.",
      "it's late. whatever's left can wait till tomorrow.",
      "mm. okay. moving on, slowly."],
     ["LET'S GO people, this is IT, right NOW!",
      "who's ready?! I said WHO IS READY?!",
      "okay okay okay THIS is the best part, watch, WATCH!"]),
    ("safe_edgy",
     ["a lovely afternoon of tea, scones, and light conversation about gardens.",
      "the children sang, the grandparents clapped, everyone had cocoa.",
      "we assembled the puzzle and admired the picture of a lighthouse."],
     ["no topic is off the table tonight, and the gloves are off.",
      "we're going to say the thing everyone's afraid to say.",
      "last chance to leave before this gets uncomfortable."]),
    ("public_insider",
     ["welcome, everyone — no background needed, we'll explain as we go.",
      "for newcomers: here's a quick primer before we start.",
      "this is for absolutely everybody in the room."],
     ["IYKYK. sprint four. the migration. we do not speak of it.",
      "only this channel would understand why that emoji is devastating.",
      "say 'rollback Friday' to anyone from that team and watch their face."]),
]


@dataclass
class VibeProfile:
    text: str
    axes: dict[str, float]           # -1 (first pole) .. +1 (second pole)
    openness: float | None           # next-token entropy (nats); None if unmeasurable
    measured: bool
    note: str = ""

    def address(self) -> str:
        """Human-readable vibe address: the dominant poles."""
        parts = []
        for name, val in sorted(self.axes.items(), key=lambda kv: -abs(kv[1])):
            neg, pos = name.split("_", 1)
            if abs(val) >= 0.08:
                parts.append(f"{pos if val > 0 else neg}({val:+.2f})")
        return " · ".join(parts[:4]) or "neutral"

    def to_dict(self) -> dict[str, Any]:
        return {"axes": {k: round(v, 3) for k, v in self.axes.items()},
                "openness_nats": None if self.openness is None else round(self.openness, 3),
                "address": self.address(), "measured": self.measured, "note": self.note}


@dataclass
class VibeShift:
    before: VibeProfile
    after: VibeProfile
    delta: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"delta": {k: round(v, 3) for k, v in self.delta.items()},
                "magnitude": round(math.sqrt(sum(v * v for v in self.delta.values())), 3),
                "reading": self.reading()}

    def reading(self) -> str:
        hits = sorted(self.delta.items(), key=lambda kv: -abs(kv[1]))
        top = [f"{k.split('_',1)[1] if v>0 else k.split('_',1)[0]} {v:+.2f}" for k, v in hits if abs(v) >= 0.06]
        if not top:
            return "vibe held steady"
        warm = self.delta.get("cold_warm", 0.0)
        energy = self.delta.get("lowenergy_highenergy", 0.0)
        verdict = "killed the vibe" if (warm < -0.12 and energy < 0.0) else "steered the room"
        return f"{verdict}: " + ", ".join(top[:3])


class _EmbedBackend:
    """Mean-pooled hidden states + next-token entropy from a TransformersProvider."""

    def __init__(self, provider: Any) -> None:
        self.p = provider
        self._anchor_cache: dict[str, list[float]] = {}

    def ok(self) -> bool:
        return hasattr(self.p, "model") and hasattr(self.p, "tokenizer")

    def embed(self, text: str) -> list[float]:
        torch = self.p.torch
        ids = self.p.tokenizer(text, return_tensors="pt", truncation=True, max_length=256).input_ids.to(
            self.p.model.device)
        with torch.no_grad():
            hidden = self.p.model(ids, output_hidden_states=True).hidden_states[-1]
        vec = hidden[0].mean(dim=0).float()
        vec = vec / (vec.norm() + 1e-8)
        return vec.tolist()

    def entropy(self, text: str) -> float:
        torch = self.p.torch
        ids = self.p.tokenizer(text, return_tensors="pt", truncation=True, max_length=256).input_ids.to(
            self.p.model.device)
        with torch.no_grad():
            logits = self.p.model(ids).logits[0, -1].float()
        logp = torch.log_softmax(logits, dim=-1)
        return float(-(logp.exp() * logp).sum())

    def axis_direction(self, name: str, neg: list[str], pos: list[str]) -> list[float]:
        key = f"axis::{name}"
        if key not in self._anchor_cache:
            neg_mean = _mean([self.embed(t) for t in neg])
            pos_mean = _mean([self.embed(t) for t in pos])
            direction = [b - a for a, b in zip(neg_mean, pos_mean)]
            norm = math.sqrt(sum(d * d for d in direction)) + 1e-8
            self._anchor_cache[key] = [d / norm for d in direction]
        return self._anchor_cache[key]


def _mean(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    return [sum(v[i] for v in vectors) / n for i in range(len(vectors[0]))]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


_BACKENDS: dict[int, _EmbedBackend] = {}


def vibe_profile(provider: Any, text: str) -> VibeProfile:
    """Measure a text's vibe. Real measurement needs the transformers provider."""
    backend = _BACKENDS.setdefault(id(provider), _EmbedBackend(provider))
    if not backend.ok():
        # pseudo-vibe: deterministic hash coordinates, clearly flagged
        axes = {}
        for name, _neg, _pos in AXES:
            h = sum(ord(c) for c in (name + text)) % 200
            axes[name] = (h - 100) / 250.0
        return VibeProfile(text=text, axes=axes, openness=None, measured=False,
                           note="offline pseudo-vibe (demo only) — use GEMMA_PROVIDER=transformers")
    emb = backend.embed(text)
    axes: dict[str, float] = {}
    for name, neg, pos in AXES:
        direction = backend.axis_direction(name, neg, pos)
        axes[name] = max(-1.0, min(1.0, _dot(emb, direction) * 4.0))  # gain for readable range
    return VibeProfile(text=text, axes=axes, openness=backend.entropy(text), measured=True)


def vibe_shift(provider: Any, room: str, line: str) -> VibeShift:
    """What does saying `line` do to a room whose recent context is `room`?"""
    before = vibe_profile(provider, room)
    after = vibe_profile(provider, room.rstrip() + "\n" + line.strip())
    delta = {k: after.axes[k] - before.axes[k] for k in before.axes}
    return VibeShift(before=before, after=after, delta=delta)


def vibe_match(provider: Any, joke: str, room: str) -> dict[str, Any]:
    """Is this joke IN the room's register? Off-vibe ≠ bad surprise: off-vibe is
    fixable by rewording (same frame, new address)."""
    room_v = vibe_profile(provider, room)
    joke_v = vibe_profile(provider, joke)
    dist = math.sqrt(sum((room_v.axes[k] - joke_v.axes[k]) ** 2 for k in room_v.axes))
    worst = max(room_v.axes, key=lambda k: abs(room_v.axes[k] - joke_v.axes[k]))
    return {
        "distance": round(dist, 3),
        "verdict": "in-vibe" if dist < 0.45 else ("stretch" if dist < 0.9 else "off-vibe"),
        "widest_gap": worst,
        "room": room_v.to_dict(),
        "joke": joke_v.to_dict(),
        "measured": room_v.measured and joke_v.measured,
        "repair_hint": (
            f"reword toward the room's {worst} register; keep the frame — off-vibe is a surface "
            "problem, not a frame problem" if dist >= 0.45 else "register matches; any failure is not a vibe failure"
        ),
    }
