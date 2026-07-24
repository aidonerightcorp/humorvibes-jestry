"""Humor market analytics for comedian positioning and style-shift risk."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import sqrt


STYLE_AXES: tuple[str, ...] = (
    "observational",
    "storytelling",
    "wordplay",
    "absurdist",
    "political",
    "personal",
    "affiliative",
    "aggressive",
    "self_deprecating",
    "clean",
    "blue",
    "crowdwork",
    "intellectual",
    "local",
    "dark",
)


@dataclass(frozen=True)
class StyleVector:
    weights: dict[str, float] = field(default_factory=dict)

    def normalized(self) -> dict[str, float]:
        return {axis: max(0.0, min(10.0, float(self.weights.get(axis, 0.0)))) for axis in STYLE_AXES}

    def to_dict(self) -> dict[str, object]:
        return self.normalized()


@dataclass(frozen=True)
class ComedianProfile:
    profile_id: str
    name: str
    style: StyleVector
    audience_segments: tuple[str, ...]
    topics: tuple[str, ...]
    promise: str
    audience_lock_in: float = 5.0
    market_share_proxy: float = 1.0

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["style"] = self.style.to_dict()
        return data


@dataclass(frozen=True)
class MarketSegment:
    segment_id: str
    label: str
    audience: str
    desired_style: StyleVector
    desired_topics: tuple[str, ...]
    demand_proxy: float
    tolerance_for_shift: float
    dominant_models: tuple[str, ...]
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["desired_style"] = self.desired_style.to_dict()
        return data


@dataclass(frozen=True)
class MarketGap:
    segment_id: str
    label: str
    gap_score: float
    demand_proxy: float
    supply_density: float
    closest_competitors: tuple[str, ...]
    opportunity: str
    risk: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StyleShiftAssessment:
    risk_score: float
    risk_level: str
    distance: float
    audience_lock_in: float
    bridge_overlap: float
    likely_failure_modes: tuple[str, ...]
    transition_plan: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEMO_COMPETITORS: tuple[ComedianProfile, ...] = (
    ComedianProfile(
        "clean_observational",
        "Clean Observational Club Comic",
        StyleVector({"observational": 8, "clean": 8, "affiliative": 7, "storytelling": 5, "local": 4}),
        ("corporate", "families", "mainstream clubs"),
        ("work", "relationships", "daily inconvenience"),
        "Reliable low-risk jokes about common life patterns.",
        audience_lock_in=7,
        market_share_proxy=7,
    ),
    ComedianProfile(
        "political_satirist",
        "Political Satirist",
        StyleVector({"political": 9, "intellectual": 7, "aggressive": 6, "wordplay": 4, "dark": 4}),
        ("ideological fans", "late-night viewers", "news-aware audiences"),
        ("elections", "media", "institutions", "public figures"),
        "Sharp topical commentary that rewards shared political context.",
        audience_lock_in=8,
        market_share_proxy=6,
    ),
    ComedianProfile(
        "crowdwork_roaster",
        "Crowdwork Roaster",
        StyleVector({"crowdwork": 9, "aggressive": 7, "blue": 5, "local": 7, "affiliative": 3}),
        ("clubs", "short-form video audiences", "bachelorette/table groups"),
        ("audience interaction", "dating", "jobs", "local details"),
        "Live danger, fast personalization, and status play.",
        audience_lock_in=6,
        market_share_proxy=8,
    ),
    ComedianProfile(
        "absurdist_alt",
        "Absurdist Alt Comic",
        StyleVector({"absurdist": 9, "wordplay": 6, "intellectual": 5, "clean": 5, "storytelling": 3}),
        ("alt rooms", "comedy nerds", "college audiences"),
        ("language", "dream logic", "small rituals"),
        "Form-breaking surprise for audiences that enjoy unresolved weirdness.",
        audience_lock_in=5,
        market_share_proxy=4,
    ),
    ComedianProfile(
        "personal_storyteller",
        "Personal Storyteller",
        StyleVector({"storytelling": 9, "personal": 8, "self_deprecating": 7, "affiliative": 6, "dark": 3}),
        ("theater audiences", "podcast fans", "identity/community audiences"),
        ("family", "aging", "identity", "embarrassment", "resilience"),
        "Trust-heavy personal disclosure that converts pain into shared recognition.",
        audience_lock_in=8,
        market_share_proxy=5,
    ),
    ComedianProfile(
        "tech_workplace",
        "Tech Workplace Comic",
        StyleVector({"observational": 7, "intellectual": 6, "local": 7, "clean": 7, "affiliative": 6}),
        ("tech meetups", "conference audiences", "corporate teams"),
        ("AI", "meetings", "software", "management", "remote work"),
        "Specific workplace recognition without threatening professional identity.",
        audience_lock_in=6,
        market_share_proxy=3,
    ),
)


DEMO_MARKET_SEGMENTS: tuple[MarketSegment, ...] = (
    MarketSegment(
        "ai_workplace_bridge",
        "AI Workplace Bridge Humor",
        "tech meetups and corporate teams",
        StyleVector({"observational": 8, "intellectual": 6, "clean": 8, "affiliative": 7, "local": 7}),
        ("AI", "meetings", "software", "management"),
        demand_proxy=8,
        tolerance_for_shift=5,
        dominant_models=("professional competence", "technical credibility", "work identity"),
        notes="Underserved when jokes become either generic AI fear or too technical for mixed business audiences.",
    ),
    MarketSegment(
        "cross_ideology_process",
        "Cross-Ideology Process Humor",
        "mixed political audiences",
        StyleVector({"political": 5, "observational": 7, "affiliative": 8, "clean": 6, "local": 5}),
        ("bureaucracy", "media incentives", "public services", "meetings"),
        demand_proxy=7,
        tolerance_for_shift=3,
        dominant_models=("political identity", "fairness", "moral framing"),
        notes="Gap exists between partisan satire and bland non-political material.",
    ),
    MarketSegment(
        "clean_dark_repair",
        "Clean Dark-Adjacent Coping Humor",
        "workplace, healthcare, education, recovery groups",
        StyleVector({"dark": 4, "clean": 8, "self_deprecating": 6, "affiliative": 8, "storytelling": 6}),
        ("stress", "burnout", "bureaucracy", "uncertainty"),
        demand_proxy=6,
        tolerance_for_shift=4,
        dominant_models=("emotional safety", "professional care", "dignity"),
        notes="Opportunity is not edgy darkness; it is pressure-release without identity injury.",
    ),
    MarketSegment(
        "local_microculture",
        "Local Microculture Specificity",
        "city-specific rooms and meetups",
        StyleVector({"local": 9, "observational": 7, "affiliative": 6, "storytelling": 5, "clean": 5}),
        ("transit", "weather", "rent", "local habits", "venue-specific rituals"),
        demand_proxy=7,
        tolerance_for_shift=6,
        dominant_models=("local belonging", "insider status", "shared inconvenience"),
        notes="Strong for comics who can probe the room and avoid stale city stereotypes.",
    ),
    MarketSegment(
        "high_concept_clean_alt",
        "High-Concept Clean Alt",
        "college, festival, and online niche audiences",
        StyleVector({"absurdist": 7, "wordplay": 7, "clean": 8, "intellectual": 7, "affiliative": 4}),
        ("language", "science", "AI", "rules", "games"),
        demand_proxy=5,
        tolerance_for_shift=7,
        dominant_models=("playfulness", "novelty tolerance", "clarity"),
        notes="Opportunity when absurdity is framed clearly enough for non-alt rooms.",
    ),
)


def style_distance(left: StyleVector, right: StyleVector) -> float:
    a = left.normalized()
    b = right.normalized()
    return sqrt(sum((a[axis] - b[axis]) ** 2 for axis in STYLE_AXES)) / sqrt(len(STYLE_AXES))


def style_similarity(left: StyleVector, right: StyleVector) -> float:
    return round(max(0.0, 10.0 - style_distance(left, right)), 3)


def parse_style_terms(text: str) -> StyleVector:
    lowered = text.lower()
    weights = {axis: 0.0 for axis in STYLE_AXES}
    keyword_map = {
        "observational": ("observational", "relatable", "everyday"),
        "storytelling": ("story", "storytelling", "narrative"),
        "wordplay": ("wordplay", "pun", "language"),
        "absurdist": ("absurd", "weird", "surreal", "alt"),
        "political": ("politic", "partisan", "ideology", "election"),
        "personal": ("personal", "family", "identity"),
        "affiliative": ("bridge", "warm", "bond", "affiliative", "not mean"),
        "aggressive": ("roast", "aggressive", "insult", "attack"),
        "self_deprecating": ("self-deprecating", "self deprecating", "self"),
        "clean": ("clean", "corporate", "family", "classroom"),
        "blue": ("blue", "dirty", "adult"),
        "crowdwork": ("crowdwork", "crowd work", "audience interaction"),
        "intellectual": ("smart", "intellectual", "technical", "science"),
        "local": ("local", "nyc", "city", "venue"),
        "dark": ("dark", "bleak", "morbid"),
    }
    for axis, terms in keyword_map.items():
        if any(term in lowered for term in terms):
            weights[axis] = 8.0
    if not any(weights.values()):
        weights.update({"observational": 5.0, "affiliative": 5.0, "clean": 5.0})
    return StyleVector(weights)


def market_gaps(
    audience: str = "",
    preferences: str = "",
    segments: tuple[MarketSegment, ...] = DEMO_MARKET_SEGMENTS,
    competitors: tuple[ComedianProfile, ...] = DEMO_COMPETITORS,
    limit: int = 5,
) -> list[MarketGap]:
    query_style = parse_style_terms(" ".join([audience, preferences]))
    scored: list[MarketGap] = []
    for segment in segments:
        competitor_scores = [
            (style_similarity(segment.desired_style, competitor.style), competitor)
            for competitor in competitors
            if topic_overlap(segment.desired_topics, competitor.topics) or audience_overlap(segment.audience, competitor.audience_segments)
        ]
        competitor_scores.sort(key=lambda item: item[0], reverse=True)
        supply_density = sum(score * competitor.market_share_proxy for score, competitor in competitor_scores[:3]) / 30.0
        query_fit = style_similarity(segment.desired_style, query_style) / 10.0
        gap_score = max(0.0, segment.demand_proxy * (1.15 + query_fit) - supply_density)
        closest = tuple(competitor.name for _, competitor in competitor_scores[:3])
        opportunity = (
            f"Build around {', '.join(segment.desired_topics[:3])} using "
            f"{top_style_names(segment.desired_style, 4)}."
        )
        risk = (
            "High audience-model sensitivity; probe dominant models first."
            if segment.tolerance_for_shift <= 4
            else "Moderate risk; test specificity and delivery before scaling."
        )
        scored.append(
            MarketGap(
                segment_id=segment.segment_id,
                label=segment.label,
                gap_score=round(gap_score, 3),
                demand_proxy=segment.demand_proxy,
                supply_density=round(supply_density, 3),
                closest_competitors=closest,
                opportunity=opportunity,
                risk=risk,
            )
        )
    scored.sort(key=lambda item: item.gap_score, reverse=True)
    return scored[:limit]


def assess_style_shift(
    current_style: StyleVector,
    proposed_style: StyleVector,
    audience_lock_in: float = 7.0,
    bridge_overlap: float = 3.0,
    dominant_model_sensitivity: float = 5.0,
) -> StyleShiftAssessment:
    distance = style_distance(current_style, proposed_style)
    risk = distance * 0.9 + audience_lock_in * 0.45 + dominant_model_sensitivity * 0.35 - bridge_overlap * 0.55
    risk_score = round(max(0.0, min(10.0, risk)), 3)
    if risk_score >= 7:
        level = "high"
    elif risk_score >= 4:
        level = "medium"
    else:
        level = "low"

    failures: list[str] = []
    current = current_style.normalized()
    proposed = proposed_style.normalized()
    if proposed["political"] - current["political"] >= 4:
        failures.append("audience reads the shift as moral/ideological repositioning")
    if proposed["aggressive"] - current["aggressive"] >= 4:
        failures.append("audience loses the original trust contract")
    if proposed["blue"] - current["blue"] >= 4 or proposed["dark"] - current["dark"] >= 4:
        failures.append("surprise moves from local joke logic into audience-model threat")
    if proposed["absurdist"] - current["absurdist"] >= 4 and current["observational"] >= 6:
        failures.append("fans who came for recognition do not resolve the new weirdness")
    if not failures:
        failures.append("main risk is weak bridge material, not style change itself")

    transition = [
        "keep 60-70% of the known promise in the first test set",
        "introduce the new style through callbacks, tags, or a short explicit frame",
        "A/B test one style axis at a time and log laughter, groans, silence, and repeat-view intent",
        "use bridge jokes that share the old topic but apply the new mechanism",
    ]
    if risk_score >= 7:
        transition.insert(0, "do not cold-open with the new persona or most polarizing topic")
    return StyleShiftAssessment(
        risk_score=risk_score,
        risk_level=level,
        distance=round(distance, 3),
        audience_lock_in=round(audience_lock_in, 3),
        bridge_overlap=round(bridge_overlap, 3),
        likely_failure_modes=tuple(failures),
        transition_plan=tuple(transition),
    )


def style_shift_from_text(
    current: str,
    proposed: str,
    audience_lock_in: float = 7.0,
    bridge_overlap: float = 3.0,
    dominant_model_sensitivity: float = 5.0,
) -> StyleShiftAssessment:
    return assess_style_shift(
        parse_style_terms(current),
        parse_style_terms(proposed),
        audience_lock_in=audience_lock_in,
        bridge_overlap=bridge_overlap,
        dominant_model_sensitivity=dominant_model_sensitivity,
    )


def market_context_block(audience: str = "", preferences: str = "", limit: int = 3) -> str:
    lines = ["Humor market analytics:"]
    for gap in market_gaps(audience, preferences, limit=limit):
        competitors = ", ".join(gap.closest_competitors) or "none close in demo market"
        lines.append(
            f"- {gap.label}: gap={gap.gap_score:g}, supply={gap.supply_density:g}, "
            f"competitors={competitors}. Opportunity: {gap.opportunity} Risk: {gap.risk}"
        )
    return "\n".join(lines)


def top_style_names(style: StyleVector, limit: int = 5) -> str:
    items = sorted(style.normalized().items(), key=lambda item: item[1], reverse=True)
    return ", ".join(axis for axis, value in items[:limit] if value > 0)


def topic_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    left_terms = {token.lower() for item in left for token in item.replace("/", " ").split()}
    right_terms = {token.lower() for item in right for token in item.replace("/", " ").split()}
    return bool(left_terms & right_terms)


def audience_overlap(segment_audience: str, competitor_audiences: tuple[str, ...]) -> bool:
    segment_terms = {token.lower() for token in segment_audience.replace("/", " ").split()}
    for audience in competitor_audiences:
        if segment_terms & {token.lower() for token in audience.replace("/", " ").split()}:
            return True
    return False
