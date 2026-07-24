from __future__ import annotations

import argparse
import json

from humor_datacenter.acquisition import acquisition_targets
from humor_datacenter.audience import LiveResponse, default_audience_state
from humor_datacenter.demo import build_demo_datacenter, datacenter_context
from humor_datacenter.experiment import (
    ExperimentLog,
    JokeAttempt,
    demo_attempts,
    learning_context,
    summarize_attempts,
)
from humor_datacenter.market import (
    DEMO_COMPETITORS,
    DEMO_MARKET_SEGMENTS,
    market_gaps,
    style_shift_from_text,
)
from humor_datacenter.mechanisms import COMEDY_MECHANISMS, rank_mechanisms
from humor_datacenter.model_jury import (
    DEFAULT_JUDGES,
    convergence_report,
    demo_jury_scores,
    model_jury_prompt,
)
from humor_datacenter.portability import PORTABILITY_TESTS, assess_portability
from humor_datacenter.probes import PROBE_QUESTIONS, rank_probe_questions
from humor_datacenter.ranking import demo_candidates, demo_judgments, pairwise_prompt_block, rank_pairwise
from humor_datacenter.strategy import plan_experiments, recommend_mechanisms
from humor_datacenter.studies import STUDY_BRANCHES, rank_study_branches
from humor_datacenter.sources import HUMOR_SOURCES, rank_sources_for_request


def main() -> int:
    parser = argparse.ArgumentParser(description="HumorVibes humor datacenter utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sources", help="Print the curated source registry as JSON")
    sub.add_parser("branches", help="Print the study branch registry as JSON")
    sub.add_parser("mechanisms", help="Print the comedy mechanism registry as JSON")
    sub.add_parser("probes", help="Print the audience probe registry as JSON")
    sub.add_parser("portability-tests", help="Print cross-ideology portability tests as JSON")
    sub.add_parser("market-archetypes", help="Print demo comedian and market segment archetypes")
    sub.add_parser("model-judges", help="Print configured model jury archetypes")
    sub.add_parser("demo-model-convergence", help="Run demo multi-model convergence report")
    sub.add_parser("demo-lessons", help="Print demo live-experiment lesson priors")
    sub.add_parser("demo-tournament", help="Run the built-in pairwise candidate tournament")

    rank = sub.add_parser("rank-sources", help="Rank data sources for a prompt")
    rank.add_argument("prompt")
    rank.add_argument("--audience", default="")
    rank.add_argument("--preferences", default="")

    acquisition = sub.add_parser("acquisition-plan", help="Plan source acquisition for a prompt")
    acquisition.add_argument("prompt")
    acquisition.add_argument("--audience", default="")
    acquisition.add_argument("--preferences", default="")

    search = sub.add_parser("demo-search", help="Search the seeded local demo datacenter")
    search.add_argument("query")
    search.add_argument("--channel", default="text", choices=["text", "structure", "audience", "reaction", "risk"])

    context = sub.add_parser("context", help="Print prompt context for Gemma")
    context.add_argument("prompt")
    context.add_argument("--audience", default="")
    context.add_argument("--preferences", default="")
    context.add_argument("--laughter-seconds", type=float, default=0.0)
    context.add_argument("--applause", type=int, default=0)
    context.add_argument("--groan", type=int, default=0)
    context.add_argument("--confusion", type=int, default=0)
    context.add_argument("--silence-seconds", type=float, default=0.0)
    context.add_argument("--smile", type=int, default=0)

    branch_rank = sub.add_parser("rank-branches", help="Rank study branches for a prompt")
    branch_rank.add_argument("prompt")
    branch_rank.add_argument("--audience", default="")
    branch_rank.add_argument("--preferences", default="")

    mechanism_rank = sub.add_parser("rank-mechanisms", help="Rank comedy mechanisms for a prompt")
    mechanism_rank.add_argument("prompt")
    mechanism_rank.add_argument("--audience", default="")
    mechanism_rank.add_argument("--preferences", default="")

    probe_rank = sub.add_parser("rank-probes", help="Rank audience probe questions for a prompt")
    probe_rank.add_argument("prompt")
    probe_rank.add_argument("--audience", default="")
    probe_rank.add_argument("--preferences", default="")

    plan = sub.add_parser("plan-experiments", help="Build concrete experiment plans for a prompt")
    plan.add_argument("prompt")
    plan.add_argument("--audience", default="")
    plan.add_argument("--preferences", default="")

    recommend = sub.add_parser("recommend-mechanisms", help="Recommend mechanisms from priors plus attempt logs")
    recommend.add_argument("prompt")
    recommend.add_argument("--audience", default="")
    recommend.add_argument("--preferences", default="")
    recommend.add_argument("--path", default="")

    portability = sub.add_parser("portability-check", help="Heuristically assess cross-ideology portability")
    portability.add_argument("candidate")
    portability.add_argument("--audience", default="")
    portability.add_argument("--preferences", default="")

    pairwise = sub.add_parser("pairwise-prompt", help="Print a Gemma prompt for pairwise candidate judgment")
    pairwise.add_argument("--audience-context", default="")

    gaps = sub.add_parser("market-gaps", help="Find underserved humor market segments")
    gaps.add_argument("--audience", default="")
    gaps.add_argument("--preferences", default="")

    shift = sub.add_parser("style-shift-risk", help="Assess whether a comedian style change may flop")
    shift.add_argument("--current", required=True)
    shift.add_argument("--proposed", required=True)
    shift.add_argument("--audience-lock-in", type=float, default=7.0)
    shift.add_argument("--bridge-overlap", type=float, default=3.0)
    shift.add_argument("--dominant-model-sensitivity", type=float, default=5.0)

    jury_prompt = sub.add_parser("model-jury-prompt", help="Print a model-specific judging prompt")
    jury_prompt.add_argument("--candidate", required=True)
    jury_prompt.add_argument("--audience", default="")
    jury_prompt.add_argument("--preferences", default="")
    jury_prompt.add_argument("--judge-name", default="independent model judge")

    log = sub.add_parser("log-attempt", help="Append one audience response to a JSONL experiment log")
    log.add_argument("--path", required=True)
    log.add_argument("--session-id", default="default")
    log.add_argument("--prompt", required=True)
    log.add_argument("--audience", default="")
    log.add_argument("--candidate", required=True)
    log.add_argument("--mechanisms", default="")
    log.add_argument("--mesh-total", type=float, default=0.0)
    log.add_argument("--laughter-seconds", type=float, default=0.0)
    log.add_argument("--applause", type=int, default=0)
    log.add_argument("--groan", type=int, default=0)
    log.add_argument("--confusion", type=int, default=0)
    log.add_argument("--silence-seconds", type=float, default=0.0)
    log.add_argument("--smile", type=int, default=0)
    log.add_argument("--notes", default="")

    summarize = sub.add_parser("summarize-log", help="Summarize a JSONL experiment log by mechanism")
    summarize.add_argument("--path", required=True)

    args = parser.parse_args()

    if args.cmd == "sources":
        print(json.dumps([s.to_dict() for s in HUMOR_SOURCES], indent=2))
        return 0

    if args.cmd == "branches":
        print(json.dumps([b.to_dict() for b in STUDY_BRANCHES], indent=2))
        return 0

    if args.cmd == "mechanisms":
        print(json.dumps([m.to_dict() for m in COMEDY_MECHANISMS], indent=2))
        return 0

    if args.cmd == "probes":
        print(json.dumps([p.to_dict() for p in PROBE_QUESTIONS], indent=2))
        return 0

    if args.cmd == "portability-tests":
        print(json.dumps([p.to_dict() for p in PORTABILITY_TESTS], indent=2))
        return 0

    if args.cmd == "market-archetypes":
        print(
            json.dumps(
                {
                    "competitors": [c.to_dict() for c in DEMO_COMPETITORS],
                    "segments": [s.to_dict() for s in DEMO_MARKET_SEGMENTS],
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "model-judges":
        print(json.dumps([j.to_dict() for j in DEFAULT_JUDGES], indent=2))
        return 0

    if args.cmd == "demo-model-convergence":
        print("Scores:")
        print(json.dumps([s.to_dict() for s in demo_jury_scores()], indent=2))
        print("Convergence:")
        print(json.dumps(convergence_report(demo_jury_scores()).to_dict(), indent=2))
        return 0

    if args.cmd == "demo-lessons":
        attempts = demo_attempts()
        print(learning_context(attempts))
        print(json.dumps(summarize_attempts(attempts), indent=2))
        return 0

    if args.cmd == "demo-tournament":
        candidates = demo_candidates()
        print("Candidates:")
        print(json.dumps([c.to_dict() for c in candidates], indent=2))
        print("Judgments:")
        print(json.dumps([j.to_dict() for j in demo_judgments()], indent=2))
        print("Ranking:")
        print(json.dumps([r.to_dict() for r in rank_pairwise(demo_judgments())], indent=2))
        return 0

    if args.cmd == "rank-sources":
        for source in rank_sources_for_request(args.prompt, args.audience, args.preferences):
            print(f"{source.source_id}\tpriority={source.priority}\t{source.name}\t{source.url}")
        return 0

    if args.cmd == "acquisition-plan":
        print(json.dumps([t.to_dict() for t in acquisition_targets(args.prompt, args.audience, args.preferences)], indent=2))
        return 0

    if args.cmd == "rank-branches":
        for branch in rank_study_branches(args.prompt, args.audience, args.preferences):
            print(f"{branch.branch_id}\tpriority={branch.priority}\t{branch.name}")
        return 0

    if args.cmd == "rank-mechanisms":
        for mechanism in rank_mechanisms(args.prompt, args.audience, args.preferences):
            print(f"{mechanism.mechanism_id}\tpriority={mechanism.priority}\t{mechanism.name}")
        return 0

    if args.cmd == "rank-probes":
        for probe in rank_probe_questions(args.prompt, args.audience, args.preferences):
            print(f"{probe.probe_id}\tpriority={probe.priority}\t{probe.question}")
        return 0

    if args.cmd == "plan-experiments":
        print(json.dumps([p.to_dict() for p in plan_experiments(args.prompt, args.audience, args.preferences)], indent=2))
        return 0

    if args.cmd == "recommend-mechanisms":
        attempts = ExperimentLog(args.path).read() if args.path else demo_attempts()
        print(json.dumps([r.to_dict() for r in recommend_mechanisms(args.prompt, args.audience, args.preferences, attempts)], indent=2))
        return 0

    if args.cmd == "portability-check":
        print(json.dumps(assess_portability(args.candidate, args.audience, args.preferences).to_dict(), indent=2))
        return 0

    if args.cmd == "pairwise-prompt":
        print(pairwise_prompt_block(demo_candidates(), args.audience_context))
        return 0

    if args.cmd == "market-gaps":
        print(json.dumps([g.to_dict() for g in market_gaps(args.audience, args.preferences)], indent=2))
        return 0

    if args.cmd == "style-shift-risk":
        print(
            json.dumps(
                style_shift_from_text(
                    args.current,
                    args.proposed,
                    audience_lock_in=args.audience_lock_in,
                    bridge_overlap=args.bridge_overlap,
                    dominant_model_sensitivity=args.dominant_model_sensitivity,
                ).to_dict(),
                indent=2,
            )
        )
        return 0

    if args.cmd == "model-jury-prompt":
        print(model_jury_prompt(args.candidate, args.audience, args.preferences, judge_name=args.judge_name))
        return 0

    if args.cmd == "demo-search":
        store = build_demo_datacenter()
        for hit in store.search(args.query, channel=args.channel):
            print(f"{hit.score:0.4f}\t{hit.item.stable_id()}\t{hit.item.text}")
        return 0

    if args.cmd == "context":
        state = default_audience_state(args.audience, args.preferences)
        response = LiveResponse(
            laughter_seconds=args.laughter_seconds,
            applause_level=args.applause,
            groan_level=args.groan,
            confusion_level=args.confusion,
            silence_seconds=args.silence_seconds,
            smile_level=args.smile,
        )
        print(datacenter_context(args.prompt, args.audience, args.preferences, audience_state=state, live_response=response))
        return 0

    if args.cmd == "log-attempt":
        response = LiveResponse(
            laughter_seconds=args.laughter_seconds,
            applause_level=args.applause,
            groan_level=args.groan,
            confusion_level=args.confusion,
            silence_seconds=args.silence_seconds,
            smile_level=args.smile,
        )
        attempt = JokeAttempt(
            session_id=args.session_id,
            prompt=args.prompt,
            audience=args.audience,
            candidate=args.candidate,
            mechanism_ids=[x.strip() for x in args.mechanisms.split(",") if x.strip()],
            mesh_total=args.mesh_total,
            live_response=response,
            notes=args.notes,
        )
        ExperimentLog(args.path).append(attempt)
        print(json.dumps(attempt.to_dict(), indent=2))
        return 0

    if args.cmd == "summarize-log":
        attempts = ExperimentLog(args.path).read()
        print(learning_context(attempts))
        print(json.dumps(summarize_attempts(attempts), indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
