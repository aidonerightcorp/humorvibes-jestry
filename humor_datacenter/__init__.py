"""Local humor datacenter utilities for HumorVibes."""

from .acquisition import AcquisitionTarget, acquisition_targets
from .audience import AudienceState, LiveResponse, adaptation_plan, audience_context_block
from .experiment import ExperimentLog, JokeAttempt, learning_context, summarize_attempts
from .market import ComedianProfile, MarketGap, MarketSegment, StyleShiftAssessment, StyleVector, market_gaps, style_shift_from_text
from .mechanisms import COMEDY_MECHANISMS, ComedyMechanism, rank_mechanisms
from .model_jury import (
    DEFAULT_JUDGES,
    DimensionConvergence,
    JuryConvergenceReport,
    ModelJudge,
    ModelJuryScore,
    convergence_report,
    model_jury_prompt,
)
from .portability import PORTABILITY_TESTS, PortabilityAssessment, assess_portability
from .probes import PROBE_QUESTIONS, ProbeQuestion, rank_probe_questions
from .ranking import HumorCandidate, PairwiseJudgment, TournamentResult, rank_pairwise
from .schema import AudienceProfile, HumorItem, ReactionSignal
from .strategy import ExperimentPlan, MechanismRecommendation, plan_experiments, recommend_mechanisms
from .studies import STUDY_BRANCHES, StudyBranch, rank_study_branches
from .sources import HUMOR_SOURCES, HumorSource, rank_sources_for_request
from .store import HumorDataCenter, SearchHit

__all__ = [
    "AudienceProfile",
    "AudienceState",
    "AcquisitionTarget",
    "COMEDY_MECHANISMS",
    "ComedianProfile",
    "ComedyMechanism",
    "DEFAULT_JUDGES",
    "DimensionConvergence",
    "ExperimentLog",
    "ExperimentPlan",
    "HUMOR_SOURCES",
    "HumorCandidate",
    "HumorDataCenter",
    "HumorItem",
    "HumorSource",
    "JokeAttempt",
    "JuryConvergenceReport",
    "LiveResponse",
    "MarketGap",
    "MarketSegment",
    "ModelJudge",
    "ModelJuryScore",
    "MechanismRecommendation",
    "PORTABILITY_TESTS",
    "PairwiseJudgment",
    "PortabilityAssessment",
    "PROBE_QUESTIONS",
    "ProbeQuestion",
    "ReactionSignal",
    "SearchHit",
    "STUDY_BRANCHES",
    "StyleShiftAssessment",
    "StyleVector",
    "StudyBranch",
    "TournamentResult",
    "adaptation_plan",
    "acquisition_targets",
    "assess_portability",
    "audience_context_block",
    "convergence_report",
    "learning_context",
    "market_gaps",
    "model_jury_prompt",
    "plan_experiments",
    "rank_mechanisms",
    "rank_pairwise",
    "rank_probe_questions",
    "rank_study_branches",
    "recommend_mechanisms",
    "style_shift_from_text",
    "summarize_attempts",
    "rank_sources_for_request",
]
