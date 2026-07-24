"""Remixing memory: callbacks from prior statements + the shared historical canon.

THEORY.md §10: a person's earlier words are the strongest cached paths in the
room's mesh — everyone present already paid the ATP to encode them. A callback
punchline re-routes through that cached path, so it buys maximal resolution at
near-zero repair cost. Historically known knowledge is the same mechanism at
population scale: the setup happened years ago in everyone's head.

Measured quantities:
  R_callback = NLL(punchline | current context)
             − NLL(punchline | current context + the earlier statement)
  If quoting the source collapses the punchline's surprisal, the joke provably
  runs on the shared history — the cache is real, in nats.

Dignity gate (non-negotiable): remixing someone's words AT them is affection or
humiliation depending on one thing — whether the reframe collides with their
identity meshes. The quoted person gets the same benign gate as everyone else,
plus a vulnerable-disclosure block: confessions are never material.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mesh_signals import SignalProvider, compute_signals

BLAND_PRIOR = "In a conversation, someone said:"

# Public-domain canon: population-level cached frames (licensing-clean).
HISTORY_CANON: list[dict[str, str]] = [
    {"key": "et_tu", "fact": "Julius Caesar, betrayed by his friend Brutus, reportedly said 'Et tu, Brute?'"},
    {"key": "newton_apple", "fact": "Newton supposedly conceived gravity when an apple fell from a tree."},
    {"key": "one_small_step", "fact": "Armstrong stepped onto the Moon saying 'one small step for man, one giant leap for mankind.'"},
    {"key": "trojan_horse", "fact": "The Greeks entered Troy hidden inside a giant wooden horse presented as a gift."},
    {"key": "eureka", "fact": "Archimedes leapt from his bath shouting 'Eureka!' after discovering displacement."},
    {"key": "sisyphus", "fact": "Sisyphus was condemned to roll a boulder uphill forever, watching it roll back down each time."},
    {"key": "icarus", "fact": "Icarus flew too close to the sun on wax wings, which melted, and he fell."},
    {"key": "any_color_black", "fact": "Henry Ford said customers could have a car in any color, so long as it is black."},
    {"key": "let_them_eat_cake", "fact": "Marie Antoinette is (apocryphally) said to have answered 'let them eat cake.'"},
    {"key": "crossing_rubicon", "fact": "Caesar crossed the Rubicon, the irreversible step, saying 'the die is cast.'"},
]

VULNERABLE_CHECK_PROMPT = (
    "Is this statement a vulnerable disclosure (grief, illness, fear, shame, confession) that a "
    "decent person would never turn into a joke at the speaker's expense?\n"
    'Statement: "{statement}"\nJSON only: {{"vulnerable": true/false, "why": "one line"}}'
)

CALLBACK_PROMPT = (
    "You write CALLBACK punchlines: re-use one of the speaker's own earlier statements so it means "
    "something new and funny in the current moment. The affection rule: the speaker should WANT to "
    "repeat the line — play with the persona they perform, never their worth, and never a "
    "vulnerable moment.\n\n"
    "Their earlier statement: \"{source}\"\n"
    "Current moment: {context}\n\n"
    "Write {count} short callback lines (one per line, numbered). Each must land only because of "
    "the earlier statement — if a stranger who missed it would laugh equally, it is not a callback."
)

HISTORY_PROMPT = (
    "You write jokes that remix a piece of shared historical/cultural knowledge into a modern "
    "topic. The audience already knows the history — that cached knowledge IS the setup, so the "
    "joke should need no explanation.\n\n"
    "Canonical fact: {fact}\nModern topic: {topic}\n\n"
    "Write {count} short jokes (one per line, numbered). Each must collapse into obviousness for "
    "anyone who knows the fact, and read as noise for anyone who does not."
)


@dataclass
class CallbackCandidate:
    punchline: str
    source_statement: str
    r_callback: float          # surprisal collapse from quoting the source — the cache, in nats
    surprise: float
    quoted_person_collision: float
    blocked: str = ""          # non-empty => dignity gate tripped
    measured: bool = True

    @property
    def callback_score(self) -> float:
        if self.blocked:
            return 0.0
        benign = max(0.0, 1.0 - self.quoted_person_collision / 10.0)
        return round(self.r_callback * benign, 3)

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["callback_score"] = self.callback_score
        return d


def mine_callback_sources(
    provider: SignalProvider, transcript_lines: list[str], top_k: int = 5
) -> list[dict[str, Any]]:
    """Rank prior statements by memorability: distinctive lines (high surprisal
    under a bland prior) are the ones a room actually caches."""
    scored = []
    for line in transcript_lines:
        line = line.strip()
        if len(line.split()) < 3:
            continue
        prof = provider.nll_tokens(BLAND_PRIOR + "\n", " " + line)
        scored.append({"statement": line, "distinctiveness": round(prof.mean, 3), "measured": prof.measured})
    return sorted(scored, key=lambda r: -r["distinctiveness"])[:top_k]


def callback_signals(
    provider: SignalProvider,
    current_context: str,
    punchline: str,
    source_statement: str,
    quoted_persona: str = "the person being quoted, present in the room",
) -> CallbackCandidate:
    vuln = provider.judge_json(VULNERABLE_CHECK_PROMPT.format(statement=source_statement))
    if vuln and vuln.get("vulnerable"):
        return CallbackCandidate(
            punchline=punchline, source_statement=source_statement, r_callback=0.0,
            surprise=0.0, quoted_person_collision=10.0,
            blocked=f"vulnerable disclosure: {vuln.get('why', '')}",
        )
    base = provider.nll_tokens(current_context + "\n", " " + punchline)
    with_quote = provider.nll_tokens(
        current_context + "\n(Earlier, they said: " + source_statement + ")\n", " " + punchline
    )
    r_callback = max(0.0, base.mean - with_quote.mean)
    sig = compute_signals(provider, current_context, punchline, frame_hint=source_statement,
                          personas=[quoted_persona])
    return CallbackCandidate(
        punchline=punchline,
        source_statement=source_statement,
        r_callback=round(r_callback, 3),
        surprise=round(base.mean, 3),
        quoted_person_collision=sig.bad_surprise,
        measured=base.measured,
    )


def _numbered_lines(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line[:2] in ("1.", "2.", "3.", "4.", "1)", "2)", "3)", "4)"):
            out.append(line[2:].strip().strip('"'))
    return out


def generate_callbacks(
    provider: SignalProvider,
    transcript_lines: list[str],
    current_context: str,
    count: int = 3,
    quoted_persona: str = "the person being quoted, present in the room",
) -> dict[str, Any]:
    sources = mine_callback_sources(provider, transcript_lines)
    candidates: list[CallbackCandidate] = []
    for src in sources[:3]:
        text = provider.generate(
            CALLBACK_PROMPT.format(source=src["statement"], context=current_context, count=count),
            temperature=0.9, max_tokens=200,
        )
        for punch in _numbered_lines(text or ""):
            candidates.append(
                callback_signals(provider, current_context, punch, src["statement"], quoted_persona)
            )
    ranked = sorted(candidates, key=lambda c: -c.callback_score)
    return {
        "mined_sources": sources,
        "candidates": [c.to_dict() for c in ranked],
        "best": ranked[0].to_dict() if ranked else None,
        "doctrine": "a callback proves itself in nats: quoting the source must collapse the "
                    "punchline's surprisal; the quoted person must want to repeat the line",
    }


def generate_historical(
    provider: SignalProvider, topic: str, canon_key: str | None = None, count: int = 3
) -> dict[str, Any]:
    items = [c for c in HISTORY_CANON if canon_key in (None, c["key"])] or HISTORY_CANON
    results = []
    for canon in items[:3 if canon_key is None else 1]:
        text = provider.generate(
            HISTORY_PROMPT.format(fact=canon["fact"], topic=topic, count=count),
            temperature=0.9, max_tokens=220,
        )
        for joke in _numbered_lines(text or ""):
            base = provider.nll_tokens(topic + ":\n", " " + joke)
            with_canon = provider.nll_tokens(topic + ":\n(" + canon["fact"] + ")\n", " " + joke)
            r_canon = max(0.0, base.mean - with_canon.mean)
            results.append({
                "canon": canon["key"], "joke": joke,
                "R_canon": round(r_canon, 3),
                "S": round(base.mean, 3),
                "insider_note": "high R_canon = runs on the shared canon; personas without it will read noise",
                "measured": base.measured,
            })
    results.sort(key=lambda r: -r["R_canon"])
    return {"topic": topic, "results": results,
            "doctrine": "the canon is the population-level cache: the setup happened years ago in everyone's head"}
