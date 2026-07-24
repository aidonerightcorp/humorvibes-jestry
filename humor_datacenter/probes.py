"""Audience probe questions for learning context before and during humor generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProbeQuestion:
    probe_id: str
    question: str
    dimension: str
    why_it_matters: str
    answer_to_signal: str
    keywords: tuple[str, ...]
    priority: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PROBE_QUESTIONS: tuple[ProbeQuestion, ...] = (
    ProbeQuestion(
        "audience_goal",
        "Is the goal to bond the room, sharpen a point, defuse tension, teach, or roast?",
        "intent",
        "The same joke mechanism can be correct or wrong depending on the social job.",
        "Maps to humor style: affiliative, self-enhancing, aggressive, self-deprecating, educational.",
        ("goal", "bond", "teach", "roast", "defuse", "intent"),
        10,
    ),
    ProbeQuestion(
        "acceptable_targets",
        "What targets are acceptable: self, tools, bureaucracy, public figures, institutions, or audience members?",
        "target",
        "Target choice is one of the fastest ways to create bad surprise.",
        "Constrains target and status-inversion mechanisms.",
        ("target", "roast", "audience", "identity", "person", "institution"),
        10,
    ),
    ProbeQuestion(
        "dominant_models",
        "What strong audience beliefs or moral frames should the joke not contradict?",
        "dominant_internal_models",
        "This directly probes the canonical bad-surprise boundary.",
        "Populates dominant_models and avoid_targets.",
        ("belief", "moral", "values", "bad surprise", "sensitive", "worldview"),
        10,
    ),
    ProbeQuestion(
        "inside_context",
        "How much insider language can the audience handle before the joke needs explanation?",
        "insider_context",
        "Insider references can create delight or confusion.",
        "Raises or lowers insider_context and specificity strategy.",
        ("inside", "jargon", "technical", "local", "reference", "context"),
        9,
    ),
    ProbeQuestion(
        "topic_familiarity",
        "How familiar is the audience with the topic: casual, practitioner, expert, or mixed?",
        "topic_familiarity",
        "Familiarity determines setup length and whether a premise cue is needed.",
        "Maps to topic_familiarity and setup compression.",
        ("familiar", "expert", "mixed", "topic", "setup", "premise"),
        9,
    ),
    ProbeQuestion(
        "political_bridge",
        "Should the joke bridge political viewpoints, avoid politics, or intentionally play to one side?",
        "political_portability",
        "Political material often fails by requiring one side to accept the other's moral frame.",
        "Sets ideology_bridge_goal, political_diversity, and political_topic_sensitivity.",
        ("political", "ideology", "liberal", "conservative", "bridge", "partisan"),
        10,
    ),
    ProbeQuestion(
        "edge_tolerance",
        "What is the room's tolerance for edge: classroom-safe, workplace-safe, club-safe, or roast-safe?",
        "edge_tolerance",
        "Edge tolerance changes target choice, wording, and repair thresholds.",
        "Maps to edge_tolerance and risk penalty.",
        ("edge", "safe", "classroom", "workplace", "club", "roast"),
        9,
    ),
    ProbeQuestion(
        "style_preference",
        "Which style fits: dry, absurd, wordplay, observational, self-deprecating, satirical, or story-based?",
        "style",
        "Style preference determines which mechanisms should be explored first.",
        "Maps to mechanism ranking and preferred_styles.",
        ("style", "dry", "absurd", "wordplay", "observational", "satire"),
        8,
    ),
    ProbeQuestion(
        "pace_shape",
        "Should the joke be a one-liner, a short setup-punchline, a story beat, or a tag after a prior laugh?",
        "timing",
        "Pace controls setup length and whether callback/tag mechanisms are appropriate.",
        "Maps to timing, delivery directives, and callback/tag eligibility.",
        ("timing", "one-liner", "story", "tag", "callback", "pace"),
        8,
    ),
    ProbeQuestion(
        "language_culture",
        "Are there language, cultural, regional, or translation constraints?",
        "culture_language",
        "A joke can be structurally good and still fail if the cultural script is unshared.",
        "Maps to culture/language context and local-reference risk.",
        ("language", "culture", "translation", "regional", "local"),
        8,
    ),
    ProbeQuestion(
        "truth_constraint",
        "Does the joke need to preserve factual accuracy, professional credibility, or scientific nuance?",
        "truth_alignment",
        "False premises can produce bad surprise in high-trust or technical rooms.",
        "Raises truth_alignment weight and blocks misinformation-like mechanisms.",
        ("truth", "fact", "science", "professional", "credibility", "accuracy"),
        9,
    ),
    ProbeQuestion(
        "live_miss_diagnosis",
        "If a joke missed, was the response silence, groan, confusion, offense, disagreement, or delayed laughter?",
        "live_response",
        "Different misses require different repairs.",
        "Maps response type to adaptation_plan directives.",
        ("silence", "groan", "confusion", "offense", "miss", "laughter"),
        9,
    ),
)


def rank_probe_questions(prompt: str, audience: str = "", preferences: str = "", limit: int = 6) -> list[ProbeQuestion]:
    text = " ".join([prompt, audience, preferences]).lower()
    scored: list[tuple[int, ProbeQuestion]] = []
    for probe in PROBE_QUESTIONS:
        score = probe.priority
        haystack = " ".join(
            [probe.question, probe.dimension, probe.why_it_matters, probe.answer_to_signal, " ".join(probe.keywords)]
        ).lower()
        for term in text.replace("/", " ").replace("-", " ").split():
            if len(term) >= 4 and term in haystack:
                score += 3
        if any(term in text for term in ["politic", "ideolog", "partisan", "liberal", "conservative", "bridge"]):
            if probe.probe_id in {"political_bridge", "dominant_models", "acceptable_targets"}:
                score += 7
        if any(term in text for term in ["audience", "room", "crowd", "meetup", "classroom", "corporate"]):
            if probe.probe_id in {"audience_goal", "acceptable_targets", "edge_tolerance"}:
                score += 5
        if any(term in text for term in ["technical", "ai", "science", "expert", "professional"]):
            if probe.probe_id in {"topic_familiarity", "inside_context", "truth_constraint"}:
                score += 5
        scored.append((score, probe))
    scored.sort(key=lambda item: (item[0], item[1].priority, item[1].probe_id), reverse=True)
    return [probe for _, probe in scored[:limit]]


def probe_context_block(prompt: str, audience: str = "", preferences: str = "", limit: int = 5) -> str:
    lines = []
    for probe in rank_probe_questions(prompt, audience, preferences, limit=limit):
        lines.append(f"- {probe.question} Signal: {probe.answer_to_signal}")
    return "\n".join(lines)
