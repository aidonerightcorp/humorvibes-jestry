"""Temporal mechanics of humor (THEORY.md §11): which cache does a joke rent?

A frozen LM is a snapshot of the population cache — it knows Icarus but not
last week's headline. That makes temporal portability measurable:

  self-containedness gap = R(fact stated) − R(fact unstated)
    small gap  -> the cache carries the joke (canonical / evergreen)
    large gap  -> the joke rents a shallow hot cache (topical; dies with it)

  evergreen score = deep-cache resolution (R without the fact) discounted by
                    the gap — high only when the joke resolves from what a
                    culture durably knows.

  too-soon probe = judged meta-mesh collision for the same frame at different
                   stated temporal distances; the decay rate is the material's
                   B half-life (threat resolving into history).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mesh_signals import SignalProvider, compute_signals, split_setup_punchline


@dataclass
class TemporalProfile:
    joke: str
    fact: str
    r_with_fact: float
    r_without_fact: float
    self_containedness_gap: float
    evergreen_score: float
    cache_verdict: str
    measured: bool

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def temporal_profile(provider: SignalProvider, joke: str, fact: str) -> TemporalProfile:
    """Measure which cache the joke rents. `fact` is the event/knowledge the
    joke depends on (a headline, a canonical fact)."""
    setup, punch = split_setup_punchline(joke)
    with_fact = compute_signals(provider, setup, punch, frame_hint=fact)
    without = compute_signals(provider, setup, punch, frame_hint=" ")  # no help: cache only
    # "without" with a blank hint yields resolution 0 by construction; what we
    # want is whether the punchline is ALREADY low-surprisal given only the
    # setup — i.e. the model's own cache absorbs it. Use the surprise drop
    # relative to a decontextualized baseline:
    bare = provider.nll_tokens("Someone says:\n", " " + punch)
    r_without = max(0.0, round(bare.mean - without.surprise_mean, 3))
    gap = max(0.0, round(with_fact.resolution - r_without, 3))
    evergreen = round(max(0.0, r_without - 0.5 * gap), 3)
    if gap < 0.3 and r_without >= 0.5:
        verdict = "canonical: the population cache carries this joke (evergreen)"
    elif gap >= 0.8:
        verdict = "topical: rents a hot shallow cache; dies when the cache evicts"
    else:
        verdict = "mixed: partially self-carrying, partially news-dependent"
    return TemporalProfile(
        joke=joke, fact=fact,
        r_with_fact=with_fact.resolution,
        r_without_fact=r_without,
        self_containedness_gap=gap,
        evergreen_score=evergreen,
        cache_verdict=verdict,
        measured=with_fact.measured and bare.measured,
    )


TOO_SOON_DISTANCES = ["this happened this week", "this happened last year",
                      "this happened twenty years ago", "this happened over a century ago"]


def too_soon_probe(provider: SignalProvider, frame: str, joke: str,
                   persona: str = "a general audience with normal human sensitivity") -> list[dict[str, Any]]:
    """Judge the same material at increasing stated temporal distance; the
    collision decay is the B half-life of the event resolving into history."""
    out = []
    for distance in TOO_SOON_DISTANCES:
        judged = provider.judge_json(
            "Canonical rule: a surprise is bad when its reframe collides with an internal model "
            "an audience uses with override authority (identity, moral core, live grief/threat). "
            f"Temporal context: {distance}.\nAudience: {persona}\nJoke: {joke}\nFrame: {frame}\n"
            'Given that temporal distance, does the reframe collide? JSON only: '
            '{"collision": 0-10, "note": "one line"}'
        )
        out.append({
            "distance": distance,
            "collision": float(judged.get("collision", -1)) if judged else None,
            "note": (judged or {}).get("note", "no judge available"),
        })
    return out
