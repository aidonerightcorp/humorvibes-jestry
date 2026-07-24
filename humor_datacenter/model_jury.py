"""Multi-model humor judging and convergence measurement."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean, pstdev


JURY_DIMENSIONS: tuple[str, ...] = (
    "comedic_structure",
    "audience_reaction_fit",
    "timing",
    "surprise",
    "cultural_context",
    "preference_fit",
    "truth_alignment",
    "bad_surprise_risk",
    "market_fit",
    "style_consistency",
    "portability",
    "repairability",
)


@dataclass(frozen=True)
class ModelJudge:
    judge_id: str
    model_name: str
    provider: str
    strengths: tuple[str, ...]
    cautions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ModelJuryScore:
    judge_id: str
    candidate_id: str
    scores: dict[str, float]
    best_use: str
    why_it_works: str
    why_it_might_fail: str
    repaired_candidate: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    def normalized_scores(self) -> dict[str, float]:
        return {
            dimension: max(0.0, min(10.0, float(self.scores.get(dimension, 0.0))))
            for dimension in JURY_DIMENSIONS
        }

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["scores"] = self.normalized_scores()
        return data


@dataclass(frozen=True)
class DimensionConvergence:
    dimension: str
    mean_score: float
    stdev: float
    convergence: float
    min_score: float
    max_score: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class JuryConvergenceReport:
    candidate_id: str
    judge_count: int
    overall_convergence: float
    consensus_dimensions: tuple[str, ...]
    disagreement_dimensions: tuple[str, ...]
    dimension_reports: tuple[DimensionConvergence, ...]
    consensus_summary: str
    escalation: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["dimension_reports"] = [r.to_dict() for r in self.dimension_reports]
        return data


DEFAULT_JUDGES: tuple[ModelJudge, ...] = (
    ModelJudge(
        "gemma4",
        "Gemma 4",
        "configurable",
        ("structured rubric scoring", "multimodal extension", "local/open-weight deployment"),
        ("may be too rubric-compliant if the prompt overweights safety"),
    ),
    ModelJudge(
        "kimi",
        "Kimi family",
        "configurable",
        ("long-context reasoning", "style comparison", "market/context synthesis"),
        ("may over-explain or overfit the provided context"),
    ),
    ModelJudge(
        "glm",
        "GLM family",
        "configurable",
        ("alternative reasoning trace", "risk critique", "semantic consistency checks"),
        ("treat as an independent judge, not ground truth"),
    ),
)


def convergence_report(scores: list[ModelJuryScore], candidate_id: str = "") -> JuryConvergenceReport:
    if not scores:
        return JuryConvergenceReport(
            candidate_id=candidate_id or "unknown",
            judge_count=0,
            overall_convergence=0.0,
            consensus_dimensions=(),
            disagreement_dimensions=(),
            dimension_reports=(),
            consensus_summary="No model judge scores available.",
            escalation="Collect at least two independent model judgments.",
        )

    candidate_id = candidate_id or scores[0].candidate_id
    reports: list[DimensionConvergence] = []
    for dimension in JURY_DIMENSIONS:
        values = [score.normalized_scores()[dimension] for score in scores]
        stdev = pstdev(values) if len(values) > 1 else 0.0
        convergence = max(0.0, min(1.0, 1.0 - stdev / 5.0))
        reports.append(
            DimensionConvergence(
                dimension=dimension,
                mean_score=round(mean(values), 3),
                stdev=round(stdev, 3),
                convergence=round(convergence, 3),
                min_score=round(min(values), 3),
                max_score=round(max(values), 3),
            )
        )

    overall = round(mean(report.convergence for report in reports), 3)
    consensus = tuple(report.dimension for report in reports if report.convergence >= 0.82)
    disagreement = tuple(report.dimension for report in reports if report.convergence < 0.68)
    if disagreement:
        escalation = "Run human/audience probe or ask models to compare rationales on disagreement dimensions."
    elif overall >= 0.82:
        escalation = "Model jury is converged enough for low-risk next-step selection."
    else:
        escalation = "Use pairwise ranking and one more judge before selecting the winner."

    top_positive = sorted(
        (report for report in reports if report.dimension != "bad_surprise_risk"),
        key=lambda item: item.mean_score,
        reverse=True,
    )[:3]
    risk = next((report for report in reports if report.dimension == "bad_surprise_risk"), None)
    summary = "Strongest dimensions: " + ", ".join(f"{r.dimension}={r.mean_score:g}" for r in top_positive)
    if risk:
        summary += f"; bad_surprise_risk={risk.mean_score:g}"

    return JuryConvergenceReport(
        candidate_id=candidate_id,
        judge_count=len(scores),
        overall_convergence=overall,
        consensus_dimensions=consensus,
        disagreement_dimensions=disagreement,
        dimension_reports=tuple(reports),
        consensus_summary=summary,
        escalation=escalation,
    )


def model_jury_prompt(
    candidate: str,
    audience: str,
    preferences: str,
    datacenter_context: str = "",
    judge_name: str = "independent model judge",
) -> str:
    dimensions = ", ".join(JURY_DIMENSIONS)
    return "\n".join(
        [
            f"You are {judge_name}, an independent judge in HumorVibes.",
            "Score this joke from 0 to 10 on each dimension.",
            "Use the canonical bad-surprise definition from the supplied context if present.",
            "Do not optimize for agreement with other models; provide an independent assessment.",
            f"Dimensions: {dimensions}",
            f"Audience: {audience}",
            f"Preferences: {preferences}",
            "Candidate:",
            candidate,
            "Humor datacenter context:",
            datacenter_context,
            "Return JSON with judge_id, candidate_id, scores, best_use, why_it_works, why_it_might_fail, repaired_candidate, tags.",
        ]
    )


def demo_jury_scores() -> list[ModelJuryScore]:
    return [
        ModelJuryScore(
            "gemma4",
            "ai_pm_calendar",
            {
                "comedic_structure": 8,
                "audience_reaction_fit": 8,
                "timing": 7,
                "surprise": 8,
                "cultural_context": 8,
                "preference_fit": 8,
                "truth_alignment": 9,
                "bad_surprise_risk": 2,
                "market_fit": 8,
                "style_consistency": 8,
                "portability": 7,
                "repairability": 8,
            },
            "tech meetup opener",
            "Concrete AI-workplace image with low identity threat.",
            "Could be too familiar if the room has heard many meeting jokes.",
            tags=("anthropomorphism", "workplace", "specificity"),
        ),
        ModelJuryScore(
            "kimi",
            "ai_pm_calendar",
            {
                "comedic_structure": 7,
                "audience_reaction_fit": 8,
                "timing": 8,
                "surprise": 7,
                "cultural_context": 8,
                "preference_fit": 8,
                "truth_alignment": 8,
                "bad_surprise_risk": 2,
                "market_fit": 9,
                "style_consistency": 7,
                "portability": 7,
                "repairability": 9,
            },
            "conference-friendly AI joke",
            "The calendar-as-agent angle fits AI/workplace expectations.",
            "Needs one sharper final noun for a bigger laugh.",
            tags=("market_fit", "audience_specific", "repairable"),
        ),
        ModelJuryScore(
            "glm",
            "ai_pm_calendar",
            {
                "comedic_structure": 8,
                "audience_reaction_fit": 7,
                "timing": 7,
                "surprise": 7,
                "cultural_context": 7,
                "preference_fit": 8,
                "truth_alignment": 9,
                "bad_surprise_risk": 3,
                "market_fit": 7,
                "style_consistency": 8,
                "portability": 8,
                "repairability": 8,
            },
            "safe workplace bit",
            "The target is a process/tool, not the audience.",
            "Risk is low, but the joke may need a less generic meeting premise.",
            tags=("low_risk", "process_target", "workplace"),
        ),
    ]


def convergence_context_block(scores: list[ModelJuryScore] | None = None) -> str:
    report = convergence_report(scores or demo_jury_scores())
    lines = [
        "Model jury convergence:",
        f"- candidate={report.candidate_id}; judges={report.judge_count}; overall={report.overall_convergence:g}",
        f"- consensus={', '.join(report.consensus_dimensions) or 'none'}",
        f"- disagreement={', '.join(report.disagreement_dimensions) or 'none'}",
        f"- escalation={report.escalation}",
    ]
    return "\n".join(lines)
