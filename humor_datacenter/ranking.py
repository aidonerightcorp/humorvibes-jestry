"""Pairwise ranking utilities for humor candidates.

Humor ratings are noisy and audience-specific. This module keeps a small
Bradley-Terry/Elo-style layer so HumorVibes can compare candidate jokes
without pretending a single scalar mesh score is the whole answer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pow


@dataclass(frozen=True)
class HumorCandidate:
    candidate_id: str
    text: str
    mechanisms: tuple[str, ...] = ()
    audience: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PairwiseJudgment:
    left_id: str
    right_id: str
    winner_id: str
    audience: str = ""
    judge: str = "gemma"
    rationale: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TournamentResult:
    candidate_id: str
    rating: float
    wins: int
    losses: int
    comparisons: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def rank_pairwise(
    judgments: list[PairwiseJudgment],
    candidate_ids: list[str] | None = None,
    prior_rating: float = 1000.0,
    k_factor: float = 32.0,
) -> list[TournamentResult]:
    """Return Elo-style rankings from pairwise humor judgments."""

    ids = list(candidate_ids or [])
    for judgment in judgments:
        for candidate_id in (judgment.left_id, judgment.right_id, judgment.winner_id):
            if candidate_id and candidate_id not in ids:
                ids.append(candidate_id)

    ratings = {candidate_id: prior_rating for candidate_id in ids}
    wins = {candidate_id: 0 for candidate_id in ids}
    losses = {candidate_id: 0 for candidate_id in ids}

    for judgment in judgments:
        if judgment.left_id not in ratings or judgment.right_id not in ratings:
            continue
        if judgment.winner_id not in {judgment.left_id, judgment.right_id}:
            continue

        left_rating = ratings[judgment.left_id]
        right_rating = ratings[judgment.right_id]
        expected_left = 1.0 / (1.0 + pow(10.0, (right_rating - left_rating) / 400.0))
        left_score = 1.0 if judgment.winner_id == judgment.left_id else 0.0
        right_score = 1.0 - left_score

        ratings[judgment.left_id] = left_rating + k_factor * (left_score - expected_left)
        ratings[judgment.right_id] = right_rating + k_factor * (right_score - (1.0 - expected_left))

        wins[judgment.winner_id] += 1
        loser_id = judgment.right_id if judgment.winner_id == judgment.left_id else judgment.left_id
        losses[loser_id] += 1

    results = [
        TournamentResult(
            candidate_id=candidate_id,
            rating=round(ratings[candidate_id], 3),
            wins=wins[candidate_id],
            losses=losses[candidate_id],
            comparisons=wins[candidate_id] + losses[candidate_id],
        )
        for candidate_id in ids
    ]
    return sorted(results, key=lambda item: (item.rating, item.wins, -item.losses, item.candidate_id), reverse=True)


def pairwise_prompt_block(candidates: list[HumorCandidate], audience_context: str = "") -> str:
    lines = [
        "Compare candidates pairwise for this audience.",
        "Judge the funnier candidate, but penalize bad-surprise risk, unresolved surprise, and audience mismatch.",
    ]
    if audience_context:
        lines.extend(["Audience context:", audience_context])
    lines.append("Return JSON judgments with left_id, right_id, winner_id, and rationale.")
    lines.append("Candidates:")
    for candidate in candidates:
        mechanisms = ", ".join(candidate.mechanisms) or "unknown"
        lines.append(f"- {candidate.candidate_id}: mechanisms={mechanisms}; text={candidate.text}")
    return "\n".join(lines)


def demo_candidates() -> list[HumorCandidate]:
    return [
        HumorCandidate(
            "ai_pm_meeting",
            "The AI project manager optimized the sprint by scheduling a meeting about whether meetings were agile.",
            ("anthropomorphism", "shared_frustration", "misdirection_reversal"),
            "NYC tech meetup",
        ),
        HumorCandidate(
            "ai_pm_replace",
            "AI will replace managers because humans never add value.",
            ("hyperbole_understatement", "status_inversion"),
            "corporate all-hands",
        ),
        HumorCandidate(
            "ai_pm_calendar",
            "The AI project manager found the bottleneck: the calendar had achieved sentience and wanted attention.",
            ("anthropomorphism", "specificity_concreteness"),
            "NYC tech meetup",
        ),
    ]


def demo_judgments() -> list[PairwiseJudgment]:
    return [
        PairwiseJudgment(
            "ai_pm_meeting",
            "ai_pm_replace",
            "ai_pm_meeting",
            "NYC tech meetup",
            rationale="Shared workplace friction beats a broad status-threat claim.",
        ),
        PairwiseJudgment(
            "ai_pm_calendar",
            "ai_pm_replace",
            "ai_pm_calendar",
            "NYC tech meetup",
            rationale="Concrete anthropomorphism avoids the overgeneralized replacement premise.",
        ),
        PairwiseJudgment(
            "ai_pm_calendar",
            "ai_pm_meeting",
            "ai_pm_calendar",
            "NYC tech meetup",
            rationale="The calendar image is more specific while preserving the same AI-workplace surprise.",
        ),
    ]
