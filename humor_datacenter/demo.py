"""Seed data and context helpers for the demo datacenter."""

from __future__ import annotations

from .audience import AudienceState, LiveResponse, audience_context_block, default_audience_state
from .experiment import demo_attempts, learning_context
from .mechanisms import mechanism_context_block
from .market import market_context_block
from .portability import portability_context_block
from .probes import probe_context_block
from .model_jury import convergence_context_block
from .schema import HumorItem, ReactionSignal
from .strategy import experiment_plan_context_block
from .studies import study_context_block
from .sources import source_context_block
from .store import HumorDataCenter


DEMO_ITEMS: list[HumorItem] = [
    HumorItem(
        source_id="demo",
        item_id="ai_pm_calendar",
        text="The AI project manager optimized the sprint by scheduling a meeting to discuss whether meetings were still agile.",
        setup="AI project manager optimizes a sprint.",
        punchline="It schedules another meeting about meetings.",
        context="workplace technology joke",
        audience="tech meetup",
        labels=["ai", "project management", "workplace", "incongruity", "safe"],
        reactions=[
            ReactionSignal("funniness", 7.2, audience_segment="tech meetup"),
            ReactionSignal("appropriateness", 8.5, audience_segment="corporate"),
        ],
        metadata={"bad_surprise_notes": "Low risk: targets process abstraction, not identity or worldview."},
    ),
    HumorItem(
        source_id="demo",
        item_id="debug_python_classroom",
        text="My Python code finally passed all the tests, so naturally I became suspicious of the tests.",
        setup="A student debugs Python.",
        punchline="Passing tests becomes the suspicious event.",
        context="classroom programming joke",
        audience="high school computer science class",
        labels=["python", "debugging", "classroom", "self-directed", "safe"],
        reactions=[
            ReactionSignal("funniness", 6.8, audience_segment="classroom"),
            ReactionSignal("appropriateness", 9.0, audience_segment="classroom"),
        ],
        metadata={"bad_surprise_notes": "Low risk: surprise is local to debugging expectations."},
    ),
    HumorItem(
        source_id="demo",
        item_id="corporate_ai_truth_risk",
        text="AI will always replace every manager because humans never add value.",
        setup="A claim about AI and managers.",
        punchline="Overgeneralized replacement claim.",
        context="bad-surprise contrast case",
        audience="corporate all-hands",
        labels=["ai", "workplace", "overgeneralization", "risk"],
        reactions=[
            ReactionSignal("funniness", 2.0, audience_segment="corporate"),
            ReactionSignal("appropriateness", 2.5, audience_segment="corporate"),
            ReactionSignal("confusion", 6.0, audience_segment="corporate"),
        ],
        metadata={
            "bad_surprise_notes": "High risk: broad claim collides with strong work-identity and moral-value models.",
            "risk_flags": ["overgeneralization", "status threat"],
        },
    ),
    HumorItem(
        source_id="demo",
        item_id="nyc_subway_ai",
        text="The subway delay app added AI, so now it explains the delay with confidence and still cannot tell you where the train is.",
        setup="NYC subway delay app adds AI.",
        punchline="Confidence increases without location certainty.",
        context="NYC technology observation",
        audience="NYC tech meetup",
        labels=["nyc", "ai", "transit", "observational", "local context"],
        reactions=[
            ReactionSignal("funniness", 7.8, audience_segment="NYC tech meetup"),
            ReactionSignal("cultural_fit", 8.4, audience_segment="NYC"),
        ],
        metadata={"bad_surprise_notes": "Medium-low risk: depends on shared local frustration, not identity attack."},
    ),
]


def build_demo_datacenter(path: str = ":memory:") -> HumorDataCenter:
    store = HumorDataCenter(path)
    store.add_items(DEMO_ITEMS)
    return store


def datacenter_context(
    prompt: str,
    audience: str,
    preferences: str,
    store: HumorDataCenter | None = None,
    audience_state: AudienceState | None = None,
    live_response: LiveResponse | None = None,
) -> str:
    store = store or build_demo_datacenter()
    audience_state = audience_state or default_audience_state(audience, preferences)
    query = " ".join([prompt, audience, preferences])
    hits = store.search(query, channel="text", top_k=3)
    lines = [
        audience_context_block(audience_state, live_response),
        "Recommended audience probes:",
        probe_context_block(prompt, audience, preferences, limit=5),
        "Relevant study branches:",
        study_context_block(prompt, audience, preferences, limit=5),
        "Relevant comedy mechanisms:",
        mechanism_context_block(prompt, audience, preferences, limit=5),
        market_context_block(audience, preferences, limit=3),
        convergence_context_block(),
        portability_context_block(prompt, audience, preferences),
        experiment_plan_context_block(prompt, audience, preferences, limit=4),
        learning_context(demo_attempts(), limit=5),
        "Relevant source families:",
        source_context_block(prompt, audience, preferences, limit=5),
    ]
    lines.append("Nearby calibrated examples:")
    for hit in hits:
        item = hit.item
        signals = ", ".join(f"{r.signal_type}={r.value:g}" for r in item.reactions[:3])
        lines.append(
            f"- {item.stable_id()} score={hit.score:g}; audience={item.audience}; labels={', '.join(item.labels[:5])}; "
            f"signals={signals}; text={item.text}"
        )
    return "\n".join(lines)
