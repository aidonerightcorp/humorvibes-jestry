"""Audience probing, live-response scoring, and adaptation directives."""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import AudienceProfile


@dataclass
class AudienceState:
    label: str
    topic_familiarity: int = 5
    edge_tolerance: int = 4
    abstraction_tolerance: int = 5
    insider_context: int = 5
    political_diversity: int = 5
    political_topic_sensitivity: int = 5
    ideology_bridge_goal: bool = False
    prefers_concise: bool = True
    preferred_styles: list[str] = field(default_factory=list)
    avoid_targets: list[str] = field(default_factory=list)
    dominant_models: list[str] = field(default_factory=list)

    def to_profile(self) -> AudienceProfile:
        constraints = []
        if self.prefers_concise:
            constraints.append("concise wording")
        if self.edge_tolerance <= 3:
            constraints.append("low edge tolerance")
        if self.abstraction_tolerance <= 4:
            constraints.append("prefer concrete language")
        return AudienceProfile(
            profile_id=self.label.lower().replace(" ", "_") or "audience",
            label=self.label,
            description=(
                f"topic_familiarity={self.topic_familiarity}; edge_tolerance={self.edge_tolerance}; "
                f"abstraction_tolerance={self.abstraction_tolerance}; insider_context={self.insider_context}; "
                f"political_diversity={self.political_diversity}; "
                f"political_topic_sensitivity={self.political_topic_sensitivity}; "
                f"ideology_bridge_goal={self.ideology_bridge_goal}"
            ),
            preferences=self.preferred_styles,
            constraints=constraints + self.avoid_targets,
            dominant_models=self.dominant_models,
        )


@dataclass
class LiveResponse:
    laughter_seconds: float = 0.0
    applause_level: int = 0
    groan_level: int = 0
    confusion_level: int = 0
    silence_seconds: float = 0.0
    smile_level: int = 0

    @property
    def response_score(self) -> float:
        positive = self.laughter_seconds * 1.4 + self.applause_level + self.smile_level * 0.7
        negative = self.groan_level * 1.2 + self.confusion_level * 1.4 + self.silence_seconds * 0.8
        return round(max(-10.0, min(10.0, positive - negative)), 2)


@dataclass
class AdaptationPlan:
    semantic_directives: list[str]
    wording_directives: list[str]
    delivery_directives: list[str]
    next_joke_constraints: list[str]

    def to_prompt_block(self) -> str:
        sections = [
            ("Semantic directives", self.semantic_directives),
            ("Wording directives", self.wording_directives),
            ("Delivery directives", self.delivery_directives),
            ("Next joke constraints", self.next_joke_constraints),
        ]
        lines: list[str] = []
        for title, values in sections:
            lines.append(f"{title}:")
            lines.extend(f"- {value}" for value in values)
        return "\n".join(lines)


def default_audience_state(label: str, preferences: str = "") -> AudienceState:
    pref_terms = [x.strip() for x in preferences.replace("/", ",").split(",") if x.strip()]
    combined = " ".join([label, preferences]).lower()
    bridge_goal = any(term in combined for term in ["bridge", "bipartisan", "cross-ideology", "cross ideology"])
    mixed_politics = any(term in combined for term in ["mixed political", "political audience", "liberal", "conservative", "partisan"])
    return AudienceState(
        label=label or "general audience",
        political_diversity=8 if mixed_politics or bridge_goal else 5,
        political_topic_sensitivity=8 if mixed_politics or bridge_goal else 5,
        ideology_bridge_goal=bridge_goal,
        preferred_styles=pref_terms[:6],
        avoid_targets=["avoid identity-based target choices", "avoid broad moral claims about the audience"],
        dominant_models=[
            "professional competence",
            "local cultural context",
            "fairness and status interpretation",
            "political identity and moral framing",
        ],
    )


def adaptation_plan(state: AudienceState, response: LiveResponse) -> AdaptationPlan:
    semantic = []
    wording = []
    delivery = []
    constraints = []

    if state.topic_familiarity <= 4:
        semantic.append("add one compact premise cue before the punchline")
        wording.append("replace insider acronyms with concrete nouns")
    else:
        semantic.append("use audience-specific references without overexplaining them")

    if state.insider_context >= 7:
        semantic.append("lean into shared local or professional context")
    else:
        semantic.append("avoid jokes that require hidden group knowledge")

    if state.edge_tolerance <= 3:
        semantic.append("target the situation, tool, or process rather than a vulnerable person or identity")
        constraints.append("keep the surprise local rather than status-threatening")
    elif state.edge_tolerance >= 7:
        semantic.append("allow a sharper contrast, but keep the target recoverable for the audience")

    if state.abstraction_tolerance <= 4:
        wording.append("make the punchline imageable and concrete")
        wording.append("cut abstract nouns that do not set up the turn")
    else:
        wording.append("allow one abstract concept if the punchline resolves it quickly")

    if state.prefers_concise:
        wording.append("move the twist closer to the end and keep the setup under one sentence")

    if state.political_topic_sensitivity >= 6 or state.political_diversity >= 6 or state.ideology_bridge_goal:
        semantic.append("avoid making one political identity the required butt of the joke")
        semantic.append("prefer shared institutional absurdity, process failure, hypocrisy symmetry, or human foibles")
        wording.append("use descriptive language instead of partisan labels unless the audience explicitly wants partisan satire")
        constraints.append("test whether the premise remains funny if political labels are swapped")
    if state.ideology_bridge_goal:
        semantic.append("preserve disagreement space by targeting the situation rather than the voter")
        constraints.append("prefer jokes that both sides can map onto their own frustrations")
    if state.political_topic_sensitivity >= 8:
        delivery.append("use a soft entry before political material and watch for silence or groans")
        constraints.append("avoid moral condemnation as the punchline engine")

    score = response.response_score
    if score >= 4:
        delivery.append("hold for laughter before adding a tag")
        constraints.append("generate one adjacent tag that preserves the same premise")
    elif response.confusion_level >= 5:
        semantic.append("repair the premise before trying a bigger surprise")
        wording.append("use simpler syntax and a clearer subject-verb-object path")
        delivery.append("slow the setup, then shorten the punchline")
        constraints.append("avoid layered references in the next joke")
    elif response.groan_level >= 5:
        semantic.append("move the target upward, inward, or toward an abstract system")
        wording.append("remove wording that sounds like a personal attack")
        delivery.append("acknowledge the miss briefly, then pivot")
        constraints.append("lower bad-surprise risk on the next candidate")
    elif response.silence_seconds >= 3:
        semantic.append("increase the expectation shift, but preserve the same audience model")
        wording.append("replace the punchline with a stronger verb or more specific object")
        delivery.append("do not wait too long; pivot to a shorter tag")
        constraints.append("generate a shorter alternate punchline")
    else:
        delivery.append("keep normal pace and test one small wording variant")

    return AdaptationPlan(
        semantic_directives=dedupe(semantic),
        wording_directives=dedupe(wording),
        delivery_directives=dedupe(delivery),
        next_joke_constraints=dedupe(constraints),
    )


def audience_context_block(state: AudienceState, response: LiveResponse | None = None) -> str:
    response = response or LiveResponse()
    plan = adaptation_plan(state, response)
    profile = state.to_profile()
    return "\n".join(
        [
            "Audience profile:",
            profile.to_text(),
            f"Live response score: {response.response_score}",
            plan.to_prompt_block(),
        ]
    )


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
