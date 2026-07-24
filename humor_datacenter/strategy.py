"""Experiment planning and mechanism selection for HumorVibes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt

from .experiment import JokeAttempt, demo_attempts, summarize_attempts
from .mechanisms import rank_mechanisms
from .probes import rank_probe_questions
from .sources import rank_sources_for_request
from .studies import rank_study_branches


@dataclass(frozen=True)
class ExperimentPlan:
    plan_id: str
    title: str
    hypothesis: str
    manipulation: str
    signals_to_collect: tuple[str, ...]
    success_metric: str
    failure_diagnostic: str
    next_action: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MechanismRecommendation:
    mechanism_id: str
    name: str
    score: float
    reason: str
    explore: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def plan_experiments(prompt: str, audience: str = "", preferences: str = "", limit: int = 6) -> list[ExperimentPlan]:
    branches = rank_study_branches(prompt, audience, preferences, limit=limit)
    mechanisms = rank_mechanisms(prompt, audience, preferences, limit=4)
    probes = rank_probe_questions(prompt, audience, preferences, limit=4)
    sources = rank_sources_for_request(prompt, audience, preferences, limit=4)

    mechanism_names = ", ".join(m.name for m in mechanisms[:3])
    probe_names = ", ".join(p.dimension for p in probes[:3])
    source_names = ", ".join(s.name for s in sources[:3])

    plans: list[ExperimentPlan] = []
    for branch in branches:
        if branch.branch_id == "political_ideology_portability":
            plans.append(
                ExperimentPlan(
                    "political_portability_ab",
                    "Cross-Ideology Portability A/B",
                    "A joke travels farther when it targets shared process failure instead of political identity.",
                    "Generate matched variants: partisan-label target, politician target, institution/process target, shared-frustration target.",
                    ("pairwise win rate by subgroup", "groan/confusion", "bad-surprise risk", "label-swap survival"),
                    "The shared-process variant wins or ties across ideological subgroups without elevated risk flags.",
                    "If one subgroup rejects it, inspect the moral frame and whether the target became voter identity.",
                    "Prefer shared frustration/status inversion and collect one dominant-model probe before generating.",
                )
            )
        elif branch.branch_id == "live_response_timing_delivery":
            plans.append(
                ExperimentPlan(
                    "live_delivery_tags",
                    "Live Response Tag/Pivot Study",
                    "Laughter plus low confusion should trigger tags; silence or confusion should trigger premise repair.",
                    "After each candidate, log laughter seconds, applause, groan, confusion, silence, and smile level.",
                    ("response_score", "laughter_seconds", "silence_seconds", "confusion_level", "next_joke_reward"),
                    "Response-aware next jokes outperform static next jokes over three attempts.",
                    "If response-aware variants fail, separate delivery pause issues from unclear semantic setup.",
                    "Use the live response panel and compare tag, pivot, and concrete-rewrite branches.",
                )
            )
        elif branch.branch_id == "audience_preference_embeddings":
            plans.append(
                ExperimentPlan(
                    "audience_embedding_probe",
                    "Audience Preference Embedding Probe",
                    "A few preference judgments can move mechanism ranking toward the audience's taste.",
                    "Ask the audience to pick funniest among short mechanism-varied candidates, then retrieve similar examples.",
                    ("pairwise choices", "mechanism labels", "lexical texture", "audience profile terms"),
                    "The preferred mechanism cluster predicts later pairwise wins better than global mechanism priority.",
                    "If not, the probe questions are too generic or the candidate set did not vary enough.",
                    f"Start with probes: {probe_names}. Use sources: {source_names}.",
                )
            )
        elif branch.branch_id == "bad_surprise_boundary":
            plans.append(
                ExperimentPlan(
                    "bad_surprise_boundary_pairs",
                    "Bad-Surprise Boundary Pair Test",
                    "A joke can be surprising without colliding with dominant internal models.",
                    "Create near-pairs where the comic turn is preserved but the target shifts from identity/worldview to situation/process.",
                    ("bad_surprise_risk", "appropriateness", "confusion", "pairwise preference", "repair rationale"),
                    "The situation/process variant preserves funniness while lowering bad-surprise risk.",
                    "If both variants fail, the premise itself conflicts with a dominant model or lacks resolvable surprise.",
                    "Log dominant-model probes and force Gemma to explain which model is being contradicted.",
                )
            )
        elif branch.branch_id == "ranking_evaluation":
            plans.append(
                ExperimentPlan(
                    "pairwise_tournament",
                    "Pairwise Tournament Ranking",
                    "Pairwise judgments expose humor quality better than isolated scalar ratings.",
                    "Generate 4 candidates with different mechanisms, run pairwise judgments, aggregate with Elo/Bradley-Terry-style scores.",
                    ("pairwise winner", "mechanism labels", "mesh score", "judge rationale"),
                    "The tournament winner also has high mesh score and low portability/risk flags.",
                    "If scalar and pairwise disagree, inspect conciseness, target, and resolution explanations.",
                    "Use rank-candidates before selecting the demo winner.",
                )
            )
        elif branch.branch_id == "model_jury_convergence":
            plans.append(
                ExperimentPlan(
                    "model_jury_convergence",
                    "Model Jury Convergence Study",
                    "A joke is more robust when independent models converge on structure, audience fit, risk, and repairability.",
                    "Score each candidate with Gemma/Kimi/GLM-style judges, compute per-dimension variance, then escalate disagreements.",
                    ("per-dimension mean", "per-dimension stdev", "overall convergence", "dissent rationale"),
                    "Low-risk candidates show high convergence on audience fit, truth alignment, bad-surprise risk, and repairability.",
                    "If models diverge, identify whether disagreement is about culture, market fit, timing, or dominant-model risk.",
                    "Run demo-model-convergence and ask one model to summarize the dissent only after independent scoring.",
                )
            )
        elif branch.branch_id == "humor_market_competition_analytics":
            plans.append(
                ExperimentPlan(
                    "market_gap_style_shift",
                    "Humor Market Gap And Style-Shift Study",
                    "Audience-market gaps appear where demand is high, supply is dense in adjacent styles, and the target niche has a clear promise.",
                    "Represent competitors and audience niches as style vectors; then test style-shift distance and bridge-overlap risk.",
                    ("gap_score", "supply_density", "style_distance", "audience_lock_in", "bridge_overlap", "repeat_intent"),
                    "A niche is attractive when gap score is high and a transition path preserves the old audience promise.",
                    "If a style change flops, inspect whether the comedian broke the expected persona, target, or dominant audience model.",
                    "Run market-gaps and style-shift-risk before recommending a new comedic direction.",
                )
            )
        elif branch.branch_id == "generation_repair_unfun":
            plans.append(
                ExperimentPlan(
                    "repair_preserve_engine",
                    "Repair While Preserving The Comic Engine",
                    "Good repair changes target, wording, or frame without deleting the original expectation violation.",
                    "Ask Gemma for safer, sharper, more concrete, cross-ideology, and classroom-safe rewrites of the same candidate.",
                    ("comic_engine_preserved", "mesh_total", "bad_surprise_risk", "pairwise win rate"),
                    "A repair improves risk or clarity without lowering surprise/resolution below baseline.",
                    "If repair becomes bland, force the mechanism explicitly: " + mechanism_names,
                    "Generate mechanism-labeled repairs and compare against the original candidate.",
                )
            )
        else:
            plans.append(
                ExperimentPlan(
                    f"{branch.branch_id}_probe",
                    branch.name,
                    branch.questions[0],
                    branch.design_use[0],
                    ("mesh dimensions", "pairwise preference", "audience probe answer", "live response"),
                    "The branch-specific intervention improves pairwise ranking or live response.",
                    "If it fails, inspect whether the branch was relevant to this prompt and audience.",
                    f"Use mechanisms: {mechanism_names}. Use probes: {probe_names}.",
                )
            )

    return plans[:limit]


def recommend_mechanisms(
    prompt: str,
    audience: str = "",
    preferences: str = "",
    attempts: list[JokeAttempt] | None = None,
    limit: int = 6,
) -> list[MechanismRecommendation]:
    attempts = attempts or demo_attempts()
    summary = summarize_attempts(attempts)
    ranked = rank_mechanisms(prompt, audience, preferences, limit=12)
    recommendations: list[MechanismRecommendation] = []

    for idx, mechanism in enumerate(ranked):
        stats = summary.get(mechanism.mechanism_id)
        prior = mechanism.priority / 2.0 + max(0, 8 - idx) * 0.35
        if stats:
            n = int(stats["n"])
            reward = float(stats["avg_reward"])
            confidence = min(2.0, sqrt(n) * 0.75)
            score = prior + reward * 0.55 + confidence
            reason = (
                f"local attempts n={n}, avg_reward={stats['avg_reward']}, "
                f"avg_response={stats['avg_response']}"
            )
            explore = n < 2
        else:
            score = prior
            reason = "ranked by prompt fit and source/study priors; no local attempts yet"
            explore = True
        recommendations.append(
            MechanismRecommendation(
                mechanism_id=mechanism.mechanism_id,
                name=mechanism.name,
                score=round(score, 3),
                reason=reason,
                explore=explore,
            )
        )

    recommendations.sort(key=lambda item: (item.score, not item.explore, item.mechanism_id), reverse=True)
    return recommendations[:limit]


def experiment_plan_context_block(prompt: str, audience: str = "", preferences: str = "", limit: int = 4) -> str:
    plans = plan_experiments(prompt, audience, preferences, limit=limit)
    lines = ["Recommended experiment plans:"]
    for plan in plans:
        lines.append(
            f"- {plan.title}: hypothesis={plan.hypothesis} Manipulation={plan.manipulation} "
            f"Metric={plan.success_metric}"
        )
    lines.append("Mechanism recommendations:")
    for rec in recommend_mechanisms(prompt, audience, preferences, limit=4):
        marker = "explore" if rec.explore else "exploit"
        lines.append(f"- {rec.name}: score={rec.score:g}, mode={marker}, reason={rec.reason}")
    return "\n".join(lines)
