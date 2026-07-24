from __future__ import annotations

import html
import inspect
import json

import streamlit as st

import compiled_humor
from formats import FORMATS, format_generation_prompt
from gemma_client import GemmaClient, read_prompt
from mesh_signals import compute_signals, get_provider, sparkline, split_setup_punchline
from humor_datacenter.audience import AudienceState, LiveResponse, adaptation_plan
from humor_datacenter.demo import build_demo_datacenter, datacenter_context
from humor_datacenter.market import market_gaps, style_shift_from_text
from humor_datacenter.model_jury import DEFAULT_JUDGES, convergence_report, demo_jury_scores, model_jury_prompt
from humor_datacenter.portability import assess_portability
from humor_datacenter.probes import rank_probe_questions
from humor_datacenter.ranking import PairwiseJudgment, rank_pairwise
from humor_datacenter.sources import rank_sources_for_request
from humor_datacenter.strategy import plan_experiments, recommend_mechanisms
from humor_mesh import (
    CANONICAL_BAD_SURPRISE_DEFINITION,
    best_candidate,
    extract_candidates,
    extract_json_object,
    fallback_evaluate,
    fallback_generate,
    normalize_mesh_record,
    to_json,
)


PRESETS = {
    "NYC tech meetup": {
        "prompt": "Make a joke about AI project managers for a NYC tech meetup.",
        "audience": "NYC tech meetup",
        "preferences": "smart, not mean, concise, local",
        "bridge": False,
    },
    "Mixed political room": {
        "prompt": "Make a joke about politics for a mixed liberal and conservative audience.",
        "audience": "mixed political audience",
        "preferences": "bridge, not partisan, target shared process failure",
        "bridge": True,
    },
    "Comedian style shift": {
        "prompt": "Should a clean observational corporate comic move into political aggressive crowdwork?",
        "audience": "existing corporate audience",
        "preferences": "market gap, style shift, model convergence",
        "bridge": False,
    },
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1440px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3, p, li, label, span {
            overflow-wrap: anywhere;
        }
        div[data-testid="stMetric"] {
            min-height: 86px;
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            padding: 0.75rem 0.85rem;
            background: var(--secondary-background-color);
        }
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricValue"] {
            white-space: normal;
            overflow-wrap: anywhere;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.35rem;
            line-height: 1.25;
        }
        section[data-testid="stSidebar"] textarea,
        section[data-testid="stSidebar"] input {
            line-height: 1.35;
        }
        div[data-testid="stTabs"] div[role="tablist"] {
            flex-wrap: wrap;
            row-gap: 0.25rem;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            min-height: 2.35rem;
            white-space: nowrap;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            overflow: hidden;
        }
        pre {
            white-space: pre-wrap !important;
            overflow-wrap: anywhere !important;
        }
        .pm-status-grid,
        .pm-card-grid {
            display: grid;
            gap: 0.75rem;
            margin: 0.75rem 0 1.1rem;
        }
        .pm-status-grid {
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        }
        .pm-card-grid {
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        }
        .pm-card-grid.pm-wide {
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        }
        .pm-card {
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 8px;
            background: var(--secondary-background-color);
            padding: 0.85rem 0.95rem;
            min-width: 0;
        }
        .pm-card.pm-winner {
            border-left: 4px solid #14b8a6;
            background: rgba(20, 184, 166, 0.08);
        }
        .pm-card.pm-risk {
            border-left: 4px solid #f59e0b;
            background: rgba(245, 158, 11, 0.08);
        }
        .pm-label {
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }
        .pm-value {
            color: var(--text-color);
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        .pm-title {
            color: var(--text-color);
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.3;
            margin-bottom: 0.35rem;
        }
        .pm-body {
            color: var(--text-color);
            font-size: 0.92rem;
            line-height: 1.45;
            overflow-wrap: anywhere;
        }
        .pm-meta {
            color: #94a3b8;
            font-size: 0.82rem;
            line-height: 1.35;
            margin-top: 0.45rem;
            overflow-wrap: anywhere;
        }
        .pm-badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin-top: 0.55rem;
        }
        .pm-badge {
            border: 1px solid rgba(148, 163, 184, 0.45);
            border-radius: 999px;
            color: var(--text-color);
            background: rgba(148, 163, 184, 0.12);
            font-size: 0.72rem;
            font-weight: 650;
            padding: 0.16rem 0.48rem;
            max-width: 100%;
            overflow-wrap: anywhere;
        }
        .pm-kv {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(92px, 1fr));
            gap: 0.35rem;
            margin-top: 0.65rem;
        }
        .pm-kv div {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 6px;
            padding: 0.35rem 0.45rem;
            background: rgba(148, 163, 184, 0.08);
            min-width: 0;
        }
        .pm-kv span {
            display: block;
            color: #94a3b8;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .pm-kv strong {
            display: block;
            color: var(--text-color);
            font-size: 0.9rem;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.75rem;
            }
            div[data-testid="column"] {
                min-width: min(100%, 320px) !important;
                flex: 1 1 100% !important;
            }
            .pm-status-grid,
            .pm-card-grid,
            .pm-card-grid.pm-wide {
                grid-template-columns: minmax(0, 1fr);
            }
            .pm-card {
                padding: 0.75rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def badge_row(items: list[object] | tuple[object, ...], limit: int = 6) -> str:
    shown = [item for item in items if item][:limit]
    if not shown:
        return ""
    return '<div class="pm-badge-row">' + "".join(f'<span class="pm-badge">{esc(item)}</span>' for item in shown) + "</div>"


def status_grid(items: list[tuple[str, object]]) -> None:
    cards = []
    for label, value in items:
        cards.append(
            f'<div class="pm-card"><div class="pm-label">{esc(label)}</div>'
            f'<div class="pm-value">{esc(fmt(value))}</div></div>'
        )
    st.markdown(f'<div class="pm-status-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def wide_dataframe(data, **kwargs) -> None:
    params = inspect.signature(st.dataframe).parameters
    if "width" in params:
        st.dataframe(data, width="stretch", **kwargs)
        return
    st.dataframe(data, use_container_width=True, **kwargs)


def render_probe_cards(probes) -> None:
    cards = []
    for probe in probes:
        cards.append(
            f'<div class="pm-card"><div class="pm-title">{esc(probe.dimension)}</div>'
            f'<div class="pm-body">{esc(probe.question)}</div>'
            f'<div class="pm-meta">{esc(probe.answer_to_signal)}</div></div>'
        )
    st.markdown(f'<div class="pm-card-grid pm-wide">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_experiment_cards(plans) -> None:
    cards = []
    for item in plans:
        cards.append(
            f'<div class="pm-card"><div class="pm-title">{esc(item.title)}</div>'
            f'<div class="pm-body">{esc(item.hypothesis)}</div>'
            f'<div class="pm-meta"><strong>Next:</strong> {esc(item.next_action)}</div></div>'
        )
    st.markdown(f'<div class="pm-card-grid pm-wide">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_market_gap_cards(gaps) -> None:
    cards = []
    for gap in gaps:
        cards.append(
            f'<div class="pm-card"><div class="pm-title">{esc(gap.label)}</div>'
            f'<div class="pm-body">{esc(gap.opportunity)}</div>'
            f'<div class="pm-kv"><div><span>Gap</span><strong>{esc(fmt(gap.gap_score))}</strong></div>'
            f'<div><span>Demand</span><strong>{esc(fmt(gap.demand_proxy))}</strong></div>'
            f'<div><span>Supply</span><strong>{esc(fmt(gap.supply_density))}</strong></div></div>'
            f'<div class="pm-meta">{esc(gap.risk)}</div>{badge_row(gap.closest_competitors)}</div>'
        )
    st.markdown(f'<div class="pm-card-grid pm-wide">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_source_cards(sources) -> None:
    cards = []
    for source in sources:
        cards.append(
            f'<div class="pm-card"><div class="pm-title">{esc(source.name)}</div>'
            f'<div class="pm-body">{esc(source.caveats or source.access_status)}</div>'
            f'<div class="pm-kv"><div><span>Priority</span><strong>{esc(source.priority)}</strong></div>'
            f'<div><span>Access</span><strong>{esc(source.access_status)}</strong></div></div>'
            f'{badge_row(source.signal_types)}<div class="pm-meta">{esc(source.url)}</div></div>'
        )
    st.markdown(f'<div class="pm-card-grid pm-wide">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_candidate_cards(scores, audience: str, preferences: str) -> None:
    cards = []
    ordered = sorted(enumerate(scores, start=1), key=lambda item: item[1].total, reverse=True)
    for rank, (original_idx, score) in enumerate(ordered, start=1):
        portability = assess_portability(score.candidate, audience, preferences)
        winner_class = " pm-winner" if rank == 1 else ""
        risk_class = " pm-risk" if score.bad_surprise_risk >= 6 else ""
        flags = score.risk_flags or portability.flags
        cards.append(
            f'<div class="pm-card{winner_class}{risk_class}"><div class="pm-label">c{original_idx} rank {rank}</div>'
            f'<div class="pm-title">{esc(score.candidate)}</div><div class="pm-kv">'
            f'<div><span>Mesh</span><strong>{esc(fmt(score.total))}</strong></div>'
            f'<div><span>Surprise</span><strong>{esc(fmt(score.surprise))}</strong></div>'
            f'<div><span>Risk</span><strong>{esc(fmt(score.bad_surprise_risk))}</strong></div>'
            f'<div><span>Portability</span><strong>{esc(fmt(portability.score))}</strong></div></div>'
            f'{badge_row(flags)}<div class="pm-meta"><strong>Repair:</strong> {esc(score.repaired_candidate or score.candidate)}</div></div>'
        )
    st.markdown(f'<div class="pm-card-grid pm-wide">{"".join(cards)}</div>', unsafe_allow_html=True)


def load_demo_datacenter():
    return build_demo_datacenter()


def gemma_generate_jokes(
    client: GemmaClient,
    prompt: str,
    audience: str,
    preferences: str,
    context: str,
) -> list[str]:
    template = read_prompt("generate_jokes.md")
    text = client.generate(
        template.format(
            prompt=prompt,
            audience=audience,
            preferences=preferences,
            datacenter_context=context,
        ),
        temperature=0.85,
    )
    if not text:
        return fallback_generate(prompt, audience, 3)
    return extract_candidates(text, limit=5) or fallback_generate(prompt, audience, 3)


def gemma_evaluate(
    client: GemmaClient,
    candidate: str,
    prompt: str,
    audience: str,
    preferences: str,
    context: str,
):
    template = read_prompt("evaluate_humor_mesh.md")
    response = client.generate(
        template.format(
            canonical_bad_surprise_definition=CANONICAL_BAD_SURPRISE_DEFINITION,
            prompt=prompt,
            audience=audience,
            preferences=preferences,
            candidate=candidate,
            datacenter_context=context,
        ),
        temperature=0.2,
    )
    parsed = extract_json_object(response or "")
    if parsed:
        return normalize_mesh_record(parsed, candidate)
    return fallback_evaluate(candidate, prompt, audience, preferences)


def mesh_pairwise_judgments(scores) -> list[PairwiseJudgment]:
    judgments: list[PairwiseJudgment] = []
    for i, left_score in enumerate(scores):
        for j, right_score in enumerate(scores[i + 1 :], start=i + 1):
            left_id = f"c{i + 1}"
            right_id = f"c{j + 1}"
            winner_id = left_id if left_score.total >= right_score.total else right_id
            judgments.append(
                PairwiseJudgment(
                    left_id=left_id,
                    right_id=right_id,
                    winner_id=winner_id,
                    judge="mesh_score",
                    rationale="Higher mesh total from structure, surprise, audience fit, truth, and bad-surprise risk.",
                )
            )
    return judgments


def apply_preset(name: str) -> None:
    preset = PRESETS[name]
    st.session_state["prompt"] = preset["prompt"]
    st.session_state["audience"] = preset["audience"]
    st.session_state["preferences"] = preset["preferences"]
    st.session_state["ideology_bridge_goal"] = preset["bridge"]


def init_state() -> None:
    if "prompt" not in st.session_state:
        apply_preset("NYC tech meetup")
    st.session_state.setdefault("scores", [])
    st.session_state.setdefault("jokes", [])
    st.session_state.setdefault("last_context", "")
    st.session_state.setdefault("score_key", None)
    st.session_state.setdefault("score_source", "Seeded offline")


def seed_fallback_results(prompt: str, audience: str, preferences: str) -> None:
    jokes = fallback_generate(prompt, audience, 3)
    st.session_state["jokes"] = jokes
    st.session_state["scores"] = [fallback_evaluate(joke, prompt, audience, preferences) for joke in jokes]
    st.session_state["score_key"] = (prompt, audience, preferences)
    st.session_state["score_source"] = "Seeded offline"


def build_audience_state(
    audience: str,
    preferences: str,
    topic_familiarity: int,
    edge_tolerance: int,
    abstraction_tolerance: int,
    insider_context: int,
    political_diversity: int,
    political_topic_sensitivity: int,
    ideology_bridge_goal: bool,
    prefers_concise: bool,
) -> AudienceState:
    style_terms = [x.strip() for x in preferences.replace("/", ",").split(",") if x.strip()]
    return AudienceState(
        label=audience or "general audience",
        topic_familiarity=topic_familiarity,
        edge_tolerance=edge_tolerance,
        abstraction_tolerance=abstraction_tolerance,
        insider_context=insider_context,
        political_diversity=political_diversity,
        political_topic_sensitivity=political_topic_sensitivity,
        ideology_bridge_goal=ideology_bridge_goal,
        prefers_concise=prefers_concise,
        preferred_styles=style_terms[:6],
        avoid_targets=["avoid identity-based target choices", "avoid broad moral claims about the audience"],
        dominant_models=[
            "professional competence",
            "local cultural context",
            "fairness and status interpretation",
            "political identity and moral framing",
        ],
    )


def score_rows(scores, audience: str, preferences: str) -> list[dict[str, object]]:
    rows = []
    for idx, score in enumerate(scores, start=1):
        portability = assess_portability(score.candidate, audience, preferences)
        rows.append(
            {
                "id": f"c{idx}",
                "mesh": score.total,
                "structure": score.comedic_structure,
                "surprise": score.surprise,
                "truth": score.truth_alignment,
                "bad_surprise_risk": score.bad_surprise_risk,
                "portability": portability.score,
            }
        )
    return rows


def main() -> None:
    st.set_page_config(page_title="HumorVibes", layout="wide")
    inject_styles()
    init_state()

    st.title("HumorVibes")
    st.caption("Generate, score, adapt, and compare joke candidates against audience context.")

    with st.sidebar:
        st.subheader("Scenario")
        preset = st.selectbox("Preset", list(PRESETS), index=0)
        if st.button("Load preset"):
            apply_preset(preset)
            st.session_state["scores"] = []
            st.session_state["jokes"] = []

        prompt = st.text_area("Humor request", key="prompt", height=120)
        audience = st.text_input("Audience", key="audience")
        preferences = st.text_input("Preferences / constraints", key="preferences")

        st.subheader("Audience state")
        topic_familiarity = st.slider("Topic familiarity", 0, 10, 7)
        edge_tolerance = st.slider("Edge tolerance", 0, 10, 4)
        abstraction_tolerance = st.slider("Abstraction tolerance", 0, 10, 6)
        insider_context = st.slider("Insider context", 0, 10, 7)
        political_diversity = st.slider("Political diversity", 0, 10, 5)
        political_topic_sensitivity = st.slider("Political sensitivity", 0, 10, 5)
        ideology_bridge_goal = st.checkbox("Cross-ideology bridge", key="ideology_bridge_goal")
        prefers_concise = st.checkbox("Concise", value=True)

        st.subheader("Live response")
        laughter_seconds = st.slider("Laughter seconds", 0.0, 10.0, 0.0, 0.5)
        applause_level = st.slider("Applause", 0, 10, 0)
        groan_level = st.slider("Groan", 0, 10, 0)
        confusion_level = st.slider("Confusion", 0, 10, 0)
        silence_seconds = st.slider("Silence seconds", 0.0, 10.0, 0.0, 0.5)
        smile_level = st.slider("Smiles", 0, 10, 0)

    store = load_demo_datacenter()
    audience_state = build_audience_state(
        audience,
        preferences,
        topic_familiarity,
        edge_tolerance,
        abstraction_tolerance,
        insider_context,
        political_diversity,
        political_topic_sensitivity,
        ideology_bridge_goal,
        prefers_concise,
    )
    live_response = LiveResponse(
        laughter_seconds=laughter_seconds,
        applause_level=applause_level,
        groan_level=groan_level,
        confusion_level=confusion_level,
        silence_seconds=silence_seconds,
        smile_level=smile_level,
    )
    context = datacenter_context(
        prompt,
        audience,
        preferences,
        store,
        audience_state=audience_state,
        live_response=live_response,
    )
    st.session_state["last_context"] = context
    score_key = (prompt, audience, preferences)
    if st.session_state.get("score_key") != score_key or not st.session_state.get("scores"):
        seed_fallback_results(prompt, audience, preferences)

    client = GemmaClient()
    provider_label = "Gemma via Ollama" if client.available() else "Offline fallback"
    top_gap = market_gaps(audience, preferences, limit=1)[0]
    jury_report = convergence_report(demo_jury_scores())

    status_grid(
        [
            ("Provider", provider_label),
            ("Score source", st.session_state.get("score_source", "Seeded offline")),
            ("Live response", live_response.response_score),
            ("Top market gap", top_gap.gap_score),
            ("Jury convergence", jury_report.overall_convergence),
        ]
    )

    tabs = st.tabs(["Jokes", "Audience", "Market", "Model Jury", "Sources", "Measured Signals", "Compiled", "Live Set", "Vibe", "Genome"])

    with tabs[9]:
        st.subheader("The Humor Genome — every measured dimension, auto-routed")
        st.caption(
            "One joke → its full genome: signals (S/R/E/B), vibe (register + openness), and the "
            "specialized probes that apply — temporal cache, partisan asymmetry, causal-inference "
            "structure, or a de-escalation off-ramp for hostile input. Each facet flags measured vs. "
            "offline; nothing over-claims."
        )
        import humor_genome
        gj = st.text_area("Joke (or a hostile comment to de-escalate)", key="genome_joke",
                          value="Congress found a bipartisan solution: both sides agreed the printer was the real problem.")
        ga = st.text_input("Audience (optional)", key="genome_aud")
        gforce = st.multiselect("Force facets (else auto-routed)", ["temporal", "politics", "causal", "deescalation"], key="genome_force")
        if st.button("Sequence the genome", type="primary"):
            provider = get_provider()
            with st.spinner(f"Analyzing via provider '{provider.name}'"):
                g = humor_genome.analyze(provider, gj, audience=ga or None, force=gforce or None)
            status_grid([("Laugh", g.laugh_score), ("Surprise", round(g.surprise, 2)),
                         ("Resolution", round(g.resolution, 2)), ("Bad-surprise", round(g.bad_surprise, 1)),
                         ("Routed", ", ".join(g.routed) or "core only")])
            st.code(g.card(), language="text")
            if g.facets:
                with st.expander("Facet detail"):
                    st.json({k: v for k, v in g.facets.items()})
            if not g.measured:
                st.info("Offline stub — run under GEMMA_PROVIDER=transformers (Kaggle studio) for measured signals.")

    with tabs[0]:
        run = st.button("Generate and score", type="primary")
        if run:
            with st.spinner("Generating and scoring candidates"):
                jokes = gemma_generate_jokes(client, prompt, audience, preferences, context)
                scores = [gemma_evaluate(client, joke, prompt, audience, preferences, context) for joke in jokes]
            st.session_state["jokes"] = jokes
            st.session_state["scores"] = scores
            st.session_state["score_key"] = score_key
            st.session_state["score_source"] = provider_label

        scores = st.session_state.get("scores", [])
        if not scores:
            seed_fallback_results(prompt, audience, preferences)
            scores = st.session_state.get("scores", [])
        else:
            winner = best_candidate(scores)
            left, right = st.columns([0.58, 0.42])
            with left:
                st.subheader("Score summary")
                wide_dataframe(score_rows(scores, audience, preferences), hide_index=True)
                if len(scores) >= 2:
                    tournament = rank_pairwise(mesh_pairwise_judgments(scores))
                    st.subheader("Mesh-derived tournament")
                    wide_dataframe([result.to_dict() for result in tournament], hide_index=True)
            with right:
                if winner:
                    st.subheader("Best candidate")
                    status_grid([("Mesh", winner.total), ("Surprise", winner.surprise), ("Risk", winner.bad_surprise_risk)])
                    st.markdown(f'<div class="pm-card pm-winner"><div class="pm-body">{esc(winner.candidate)}</div></div>', unsafe_allow_html=True)
                    if winner.risk_flags:
                        st.warning("; ".join(winner.risk_flags))
                    st.subheader("Repair")
                    st.markdown(
                        f'<div class="pm-card"><div class="pm-body">{esc(winner.repaired_candidate or winner.candidate)}</div></div>',
                        unsafe_allow_html=True,
                    )

            st.subheader("Candidate details")
            render_candidate_cards(scores, audience, preferences)

            for idx, score in enumerate(sorted(scores, key=lambda s: s.total, reverse=True), start=1):
                with st.expander(f"c{idx} details: {score.total}"):
                    portability = assess_portability(score.candidate, audience, preferences)
                    st.write(score.candidate)
                    st.write("Portability: " + "; ".join(portability.flags))
                    st.code(to_json(score), language="json")

    with tabs[1]:
        plan = adaptation_plan(audience_state, live_response)
        left, right = st.columns(2)
        with left:
            st.subheader("Recommended probes")
            render_probe_cards(rank_probe_questions(prompt, audience, preferences, limit=6))
            st.subheader("Experiment plans")
            render_experiment_cards(plan_experiments(prompt, audience, preferences, limit=5))
        with right:
            st.subheader("Adaptation directives")
            st.code(plan.to_prompt_block(), language="text")
            st.subheader("Mechanism recommendations")
            wide_dataframe([rec.to_dict() for rec in recommend_mechanisms(prompt, audience, preferences, limit=6)], hide_index=True)

    with tabs[2]:
        st.subheader("Market gaps")
        gaps = market_gaps(audience, preferences)
        wide_dataframe(
            [
                {
                    "segment": gap.label,
                    "gap": gap.gap_score,
                    "demand": gap.demand_proxy,
                    "supply": gap.supply_density,
                }
                for gap in gaps
            ],
            hide_index=True,
        )
        render_market_gap_cards(gaps)

        st.subheader("Style-shift risk")
        current_style = st.text_input("Current style", "clean observational corporate humor")
        proposed_style = st.text_input("Proposed style", "political aggressive dark crowdwork")
        sliders = st.columns(3)
        audience_lock_in = sliders[0].slider("Audience lock-in", 0.0, 10.0, 8.0, 0.5)
        bridge_overlap = sliders[1].slider("Bridge overlap", 0.0, 10.0, 2.0, 0.5)
        dominant_model_sensitivity = sliders[2].slider("Dominant-model sensitivity", 0.0, 10.0, 5.0, 0.5)
        shift = style_shift_from_text(
            current_style,
            proposed_style,
            audience_lock_in=audience_lock_in,
            bridge_overlap=bridge_overlap,
            dominant_model_sensitivity=dominant_model_sensitivity,
        )
        status_grid([("Risk", shift.risk_score), ("Level", shift.risk_level), ("Style distance", shift.distance)])
        st.markdown(
            '<div class="pm-card-grid pm-wide">'
            f'<div class="pm-card pm-risk"><div class="pm-title">Failure modes</div><div class="pm-body">{esc("; ".join(shift.likely_failure_modes))}</div></div>'
            f'<div class="pm-card"><div class="pm-title">Transition plan</div><div class="pm-body">{esc("; ".join(shift.transition_plan))}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    with tabs[3]:
        st.subheader("Model judges")
        wide_dataframe([judge.to_dict() for judge in DEFAULT_JUDGES], hide_index=True)
        report = convergence_report(demo_jury_scores())
        status_grid(
            [
                ("Judges", report.judge_count),
                ("Overall convergence", report.overall_convergence),
                ("Disagreements", len(report.disagreement_dimensions)),
            ]
        )
        st.markdown(
            '<div class="pm-card-grid pm-wide">'
            f'<div class="pm-card"><div class="pm-title">Consensus</div><div class="pm-body">{esc(report.consensus_summary)}</div></div>'
            f'<div class="pm-card"><div class="pm-title">Escalation</div><div class="pm-body">{esc(report.escalation)}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
        wide_dataframe([row.to_dict() for row in report.dimension_reports], hide_index=True)
        candidate_for_prompt = best_candidate(st.session_state.get("scores", []))
        prompt_candidate = candidate_for_prompt.candidate if candidate_for_prompt else "The AI project manager found the bottleneck: the calendar wanted attention."
        with st.expander("Judge prompt"):
            st.code(model_jury_prompt(prompt_candidate, audience, preferences, context, "Gemma 4"), language="text")

    with tabs[4]:
        st.subheader("Ranked source families")
        sources = rank_sources_for_request(prompt, audience, preferences, limit=10)
        wide_dataframe(
            [
                {
                    "source": source.name,
                    "priority": source.priority,
                    "modalities": ", ".join(source.modalities),
                }
                for source in sources
            ],
            hide_index=True,
        )
        render_source_cards(sources)
        with st.expander("Canonical bad-surprise definition"):
            st.write(CANONICAL_BAD_SURPRISE_DEFINITION)
        with st.expander("Full datacenter context"):
            st.write(f"Seeded local examples: {store.item_count()}")
            st.code(context, language="text")

    with tabs[5]:
        st.subheader("Measured signals (THEORY.md)")
        st.caption(
            "A joke is a controlled prediction error with a cheap, permitted repair. "
            "S = punchline surprisal | setup; R = surprisal collapse given the frame; "
            "E = R per frame token (the ATP constraint). Read off Gemma logits, never self-reported. "
            "Provider: GEMMA_PROVIDER=transformers for real measurement (offline stub otherwise, flagged)."
        )
        default_joke = "I told my therapist about my fear of speed bumps. She said I'm slowly getting over it."
        sig_text = st.text_area("Material to measure", value=default_joke, height=90, key="sig_text")
        sig_frame = st.text_input("Optional frame hint (leave blank to let Gemma guess)", key="sig_frame")
        sig_personas = st.text_input("Personas (comma-separated) for bad-surprise checks", key="sig_personas",
                                     value="NYC tech meetup, retired farmers")
        if st.button("Measure S / R / E / B"):
            provider = get_provider()
            s_setup, s_punch = split_setup_punchline(sig_text)
            with st.spinner(f"Measuring via provider '{provider.name}'"):
                sig = compute_signals(
                    provider, s_setup, s_punch, frame_hint=sig_frame or None,
                    personas=[p.strip() for p in sig_personas.split(",") if p.strip()],
                )
            status_grid([
                ("S surprise", sig.surprise_mean),
                ("R resolution", sig.resolution),
                ("E efficiency", sig.efficiency),
                ("B collision", sig.bad_surprise),
                ("Laugh score", sig.laugh_score),
            ])
            st.markdown(f"**Diagnosis:** {sig.failure_mode}")
            if sig.profile and sig.profile.nlls:
                st.code("per-token surprisal  " + sparkline(sig.profile.nlls), language="text")
            if not sig.measured:
                st.info("Offline stub values (demo only) — set GEMMA_PROVIDER=transformers or run the "
                        "Kaggle notebook for real logit measurements.")
            if sig.personas:
                wide_dataframe(
                    [{"persona": p.persona, "collision": p.collision, "colliding model": p.colliding_model,
                      "S shift": p.surprise_shift, "note": p.note} for p in sig.personas],
                    hide_index=True,
                )

    with tabs[6]:
        st.subheader("Compiled comedy — Gemma at compile time, zero model calls at runtime")
        st.caption(
            "Four stages: generate template -> static lint (banned-target rule, format budget) -> "
            "measured probe validation -> frozen artifact. Runtime is a seeded RNG + string ops: "
            "auditable before it is ever performed. Live shows run artifacts, not models."
        )
        c_topic = st.text_input("Topic family", value="office meetings", key="c_topic")
        c_format = st.selectbox("Format", sorted(FORMATS), index=sorted(FORMATS).index("one_liner"), key="c_format")
        if st.button("Compile joke program"):
            provider = get_provider()
            with st.spinner("Stage 1: Gemma drafts the template"):
                prog = compiled_humor.generate_program(provider, c_topic, c_format, audience)
            if prog is None:
                st.error(f"Stage 1 needs a generator (provider '{provider.name}' has none). "
                         "Set GEMMA_PROVIDER=ollama with a local Gemma, or use the Kaggle notebook.")
            else:
                lint = compiled_humor.static_lint(prog)
                if lint:
                    st.error("Stage 2 static lint failed: " + "; ".join(lint))
                else:
                    with st.spinner("Stage 3: measured probe validation"):
                        report = compiled_humor.measured_validate(provider, prog)
                    path = compiled_humor.freeze(prog, report)
                    st.success(f"Stage 4: frozen {path.name} | validated={prog.validated} "
                               f"(pass rate {report['pass_rate']}, instrumented={report['instrumented']})")
                    wide_dataframe(report["probes"], hide_index=True)
                    st.markdown("**Deterministic runtime** (same seed = same joke):")
                    for seed in (7, 7, 8):
                        st.code(f"seed={seed}: " + compiled_humor.run_program(prog, seed=seed), language="text")
        arts = sorted(compiled_humor.ARTIFACT_DIR.glob("*.json")) if compiled_humor.ARTIFACT_DIR.exists() else []
        if arts:
            with st.expander(f"Frozen artifacts ({len(arts)})"):
                for a in arts[-10:]:
                    st.write(a.name)

    with tabs[7]:
        st.subheader("Live set — laughter-driven joke selection over frozen artifacts")
        st.caption(
            "The room is a mesh we estimate online: every joke is an experiment, laughter is the "
            "reward. Thompson sampling exploits hot frames (callbacks = cheap re-routes through a "
            "frame the room has cached) and explores when the room goes cold. Picks come ONLY from "
            "validated compiled artifacts — adaptation changes the order, never the material."
        )
        from live_set_controller import SetListController, manual_report, measure_laughter_wav

        art_paths = sorted(compiled_humor.ARTIFACT_DIR.glob("*.json")) if compiled_humor.ARTIFACT_DIR.exists() else []
        if not art_paths:
            st.info("No frozen artifacts yet — compile a few joke programs in the Compiled tab first.")
        else:
            if "live_ctl" not in st.session_state:
                st.session_state["live_ctl"] = SetListController(art_paths)
                st.session_state["live_current"] = None
            ctl = st.session_state["live_ctl"]
            col_a, col_b = st.columns([0.55, 0.45])
            with col_a:
                if st.button("Next joke", type="primary"):
                    prog, text, samples = ctl.next_joke()
                    st.session_state["live_current"] = (prog, text)
                cur = st.session_state.get("live_current")
                if cur:
                    st.markdown(
                        f'<div class="pm-card pm-winner"><div class="pm-body">{esc(cur[1])}</div></div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"artifact {cur[0].program_id} · frame: {cur[0].frame}")
                    laugh_s = st.slider("Laughter seconds (manual)", 0.0, 8.0, 0.0, 0.25, key="live_laugh")
                    clip = st.file_uploader("…or upload an audience audit clip (.wav)", type=["wav"], key="live_clip")
                    if st.button("Record result"):
                        if clip is not None:
                            tmp = compiled_humor.ARTIFACT_DIR.parent / "show_logs" / f"clip_{cur[0].program_id}.wav"
                            tmp.parent.mkdir(exist_ok=True)
                            tmp.write_bytes(clip.getvalue())
                            report = measure_laughter_wav(tmp)
                        else:
                            report = manual_report(laugh_s)
                        ctl.record_result(cur[0], report)
                        st.session_state["live_current"] = None
                        st.success(f"{report.verdict} — reward {report.reward} (log: {ctl.log_path.name})")
            with col_b:
                read = ctl.room_read()
                st.markdown(f"**Room read** · {read['performed']} performed")
                wide_dataframe(
                    [{"frame": f[:60], "posterior": v["mean"], "plays": v["plays"]}
                     for f, v in read["frames"].items()],
                    hide_index=True,
                )
                st.markdown(f"**Advice:** {read['advice']}")

    with tabs[8]:
        st.subheader("Vibe — the room's tuning state, quantified (THEORY.md §8)")
        st.caption(
            "A vibe = the shape of the mesh's expectation before content arrives: REGISTER "
            "(coordinates on contrast axes), OPENNESS (continuation entropy = the room's risk "
            "budget), DRIFT (what a line does to the room). Off-vibe ≠ bad surprise: off-vibe is "
            "fixable by rewording (same frame, new address); bad surprise needs a new frame."
        )
        import vibe as vibe_mod

        v_room = st.text_area("Room context (recent lines, the feed, the chat…)", key="v_room",
                              value="Pursuant to the agenda, the committee will now review quarterly compliance items.")
        v_line = st.text_input("Line / joke to check against the room", key="v_line",
                               value="dude this quarterly report is a whole vibe lmaooo")
        c1, c2, c3 = st.columns(3)
        provider = get_provider()
        if c1.button("Profile room"):
            st.json(vibe_mod.vibe_profile(provider, v_room).to_dict())
        if c2.button("Match line ↔ room"):
            st.json(vibe_mod.vibe_match(provider, v_line, v_room))
        if c3.button("Shift (what the line DOES)"):
            st.json(vibe_mod.vibe_shift(provider, v_room, v_line).to_dict())
        if provider.name == "offline":
            st.info("Offline pseudo-vibes (demo only) — run under GEMMA_PROVIDER=transformers "
                    "(the Kaggle studio does this automatically) for measured register/openness.")


if __name__ == "__main__":
    main()
