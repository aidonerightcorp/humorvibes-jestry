#!/usr/bin/env python3
"""HumorVibes CLI — measured signals, multi-format generation, criticism, panel.

Examples:
  python3 mesh_cli.py formats
  python3 mesh_cli.py signals --setup "I told my therapist about my fear of speed bumps." \
      --punchline "She said I'm slowly getting over it." --personas "NYC tech meetup,retired farmers"
  python3 mesh_cli.py critique --text "TOP: me explaining my job / BOTTOM: the job: no" --format meme_caption
  python3 mesh_cli.py generate --topic "AI project managers" --format one_liner --audience "NYC tech meetup"
  python3 mesh_cli.py panel --text "..." --personas "improv crowd,corporate offsite"
Provider selection: GEMMA_PROVIDER=offline|ollama|transformers (default offline).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import compiled_humor
from formats import FORMATS, format_critique_prompt, format_generation_prompt, list_formats
from humor_mesh import extract_candidates
from llm_panel import available_judges, convergence_report, run_panel
from mesh_signals import compute_signals, get_provider, sparkline, split_setup_punchline


def cmd_formats(_: argparse.Namespace) -> int:
    for row in list_formats():
        print(f"{row['key']:16s} {row['label']:34s} [{row['media']}] budget: {row['budget']}")
    return 0


def cmd_signals(args: argparse.Namespace) -> int:
    provider = get_provider(args.provider)
    setup, punchline = (args.setup, args.punchline)
    if args.text and not (setup and punchline):
        setup, punchline = split_setup_punchline(args.text)
    personas = [p.strip() for p in (args.personas or "").split(",") if p.strip()]
    sig = compute_signals(provider, setup, punchline, frame_hint=args.frame or None, personas=personas)
    print(json.dumps(sig.to_dict(), indent=2))
    if sig.profile and sig.profile.nlls:
        print("\nper-token surprisal:", sparkline(sig.profile.nlls))
        print("provider:", provider.name, "| measured:", sig.measured)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    provider = get_provider(args.provider)
    spec = FORMATS[args.format]
    prompt = format_generation_prompt(spec, args.topic, args.audience, args.preferences, count=args.count)
    token_budget = max(420, min(1200, args.count * 140))
    text = provider.generate(prompt, temperature=args.temperature, max_tokens=token_budget)
    if not text:
        print(f"[no generator available under provider '{provider.name}'; prompt below]\n")
        print(prompt)
        _write_generation_receipt(
            args,
            provider,
            prompt,
            "",
            [],
            [],
            token_budget,
            status="provider_or_transport_failure",
        )
        return 1
    print(text)
    candidates = extract_candidates(text, limit=args.count)
    signal_rows: list[dict] = []
    if not args.no_score:
        print("\n--- measured signals per candidate ---")
        for body in candidates:
            setup, punchline = split_setup_punchline(body)
            sig = compute_signals(provider, setup, punchline)
            signal_rows.append({"candidate": body, **sig.to_dict()})
            print(f"S={sig.surprise_mean:5.2f} R={sig.resolution:5.2f} E={sig.efficiency:6.3f} "
                  f"laugh={sig.laugh_score:5.1f} :: {body[:70]}")
    _write_generation_receipt(
        args,
        provider,
        prompt,
        text,
        candidates,
        signal_rows,
        token_budget,
        status="completed" if len(candidates) == args.count else "completed_candidate_count_mismatch",
    )
    return 0


def _write_generation_receipt(
    args: argparse.Namespace,
    provider,
    prompt: str,
    raw_output: str,
    candidates: list[str],
    signal_rows: list[dict],
    token_budget: int,
    *,
    status: str,
) -> None:
    if not getattr(args, "receipt_out", ""):
        return
    path = Path(args.receipt_out).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_type": "humorvibes_gemma_generation",
        "receipt_version": 1,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "provider": provider.name,
        "model": str(getattr(provider, "model", "unknown")),
        "thinking_enabled": bool(getattr(provider, "think", False)),
        "request": {
            "topic": args.topic,
            "format": args.format,
            "audience": args.audience,
            "preferences": args.preferences,
            "requested_candidates": args.count,
            "temperature": args.temperature,
            "token_budget": token_budget,
        },
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_output_sha256": hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
        "parsed_candidate_count": len(candidates),
        "candidates": candidates,
        "signals": signal_rows,
        "truth_boundary": {
            "generation_executed": bool(raw_output),
            "teacher_forced_logprobs_measured": bool(signal_rows) and all(
                bool(row.get("measured")) for row in signal_rows
            ),
            "model_judgment_is_not_human_laughter": True,
            "competition_submission": False,
        },
    }
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nreceipt: {path}")


def cmd_critique(args: argparse.Namespace) -> int:
    provider = get_provider(args.provider)
    spec = FORMATS[args.format]
    setup, punchline = split_setup_punchline(args.text)
    sig = compute_signals(provider, setup, punchline,
                          personas=[p.strip() for p in (args.personas or "").split(",") if p.strip()])
    print("== measured signals ==")
    print(json.dumps(sig.to_dict(), indent=2))
    judged = provider.judge_json(format_critique_prompt(spec, args.text, args.audience))
    print("\n== format editor (Gemma) ==")
    print(json.dumps(judged, indent=2) if judged else f"[no judge under provider '{provider.name}']")
    return 0


def cmd_panel(args: argparse.Namespace) -> int:
    judges = available_judges()
    personas = [p.strip() for p in (args.personas or "general audience").split(",") if p.strip()]
    if not judges:
        print("No panel judges configured (dry run). Set any of: OPENAI_API_KEY [PANEL_OPENAI_MODELS],")
        print("ANTHROPIC_API_KEY [PANEL_ANTHROPIC_MODELS], PANEL_OLLAMA_MODELS. Gemma core stays primary.")
        print("Personas requested:", ", ".join(personas))
        return 0
    print("judges:", ", ".join(j.describe() for j in judges))
    votes = run_panel(args.text, personas, format_label=args.format)
    for v in votes:
        status = v.scores if v.ok else f"ERROR: {v.error}"
        print(f"[{v.judge_id} × {v.persona}] {status} {('— ' + v.reaction) if v.reaction else ''}")
    print("\n== convergence ==")
    print(json.dumps(convergence_report(votes), indent=2))
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    provider = get_provider(args.provider)
    prog = compiled_humor.generate_program(provider, args.topic, args.format, args.audience)
    if prog is None:
        print(f"[stage 1 failed: no template from provider '{provider.name}' — needs ollama/transformers]")
        return 1
    errors = compiled_humor.static_lint(prog)
    if errors:
        print("stage 2 STATIC lint FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    personas = [p.strip() for p in (args.personas or "").split(",") if p.strip()]
    report = compiled_humor.measured_validate(provider, prog, personas=personas)
    path = compiled_humor.freeze(prog, report)
    print(f"artifact: {path}\nvalidated: {prog.validated} (pass_rate={report['pass_rate']}, "
          f"instrumented={report['instrumented']})")
    for r in report["probes"]:
        print(f"  probe S={r['S']:5.2f} R={r['R']:5.2f} E={r['E']:6.3f} "
              f"collision={r['collision']:.1f} in_band={r['in_band']}")
    return 0


def cmd_run_compiled(args: argparse.Namespace) -> int:
    prog = compiled_humor.load_program(args.artifact)
    if not prog.validated and not args.force:
        print("artifact is NOT validated (stage 3 failed or unmeasured); use --force to run anyway")
        return 1
    for i in range(args.count):
        print(compiled_humor.run_program(prog, seed=(args.seed + i) if args.seed is not None else i))
    return 0


def cmd_compile_clip(args: argparse.Namespace) -> int:
    provider = get_provider(args.provider) if not args.no_measure else None
    script = args.script or Path(args.from_file).read_text(encoding="utf-8")
    plan = compiled_humor.compile_clip_plan(script, provider=provider)
    path = compiled_humor.save_clip_plan(plan)
    print(f"plan: {path}\nduration: {plan.duration_s}s, SNAP at {plan.snap_at_s}s, "
          f"validated={plan.validated}, measured={plan.measured}")
    for b in plan.beats:
        print(f"  [{b['t0']:5.2f}-{b['t1']:5.2f}] {b['beat']:5s} {b['caption'][:60]}"
              + (f"  (visual: {b['visual']})" if b["visual"] else ""))
    print("\nffmpeg recipe (zero-model runtime):")
    for cmd in compiled_humor.render_ffmpeg_commands(plan):
        print(" ", cmd)
    return 0


def cmd_temporal(args: argparse.Namespace) -> int:
    import temporal

    provider = get_provider(args.provider)
    prof = temporal.temporal_profile(provider, args.joke, args.fact)
    print(json.dumps(prof.to_dict(), indent=2))
    if args.too_soon:
        setup, punch = split_setup_punchline(args.joke)
        sig = compute_signals(provider, setup, punch)
        print(json.dumps(temporal.too_soon_probe(provider, sig.frame_hint or args.fact, args.joke), indent=2))
    if not prof.measured:
        print("[offline pseudo-measurement — run under transformers for real cache readings]")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    import ingest

    src = args.source
    if src == "wikiquote":
        records = ingest.wikiquote_fetch(args.query or "Mark Twain")
    elif src == "gutenberg":
        records = ingest.gutenberg_fetch(args.query or "toasters_handbook")
    elif src == "rss":
        records = ingest.rss_headlines([args.query] if args.query else None)
    elif src == "transcript":
        records = ingest.parse_transcript(args.query)
    elif src == "imgflip":
        records = ingest.imgflip_templates()
    elif src == "hf":
        records = ingest.hf_dataset_rows(args.query or "short_jokes")
    elif src == "reddit":
        records = ingest.reddit_jokes(args.query or "jokes")
    else:
        print("unknown source"); return 1
    name = args.name or f"{src}_{(args.query or 'default').replace(' ', '_').replace('/', '_')[:40]}"
    path = ingest.save_corpus(records, name)
    print(f"{len(records)} records -> {path}")
    for r in records[:5]:
        print("  -", r["text"][:90])
    return 0


def cmd_genome(args: argparse.Namespace) -> int:
    import humor_genome

    provider = get_provider(args.provider)
    g = humor_genome.analyze(provider, args.joke, audience=args.audience or None,
                             fact=args.fact or None,
                             force=[f.strip() for f in (args.force or "").split(",") if f.strip()])
    print(g.card())
    if args.json:
        print("\n" + json.dumps(g.to_dict(), indent=2, default=str))
    return 0


def cmd_partisan(args: argparse.Namespace) -> int:
    import symmetry_probe

    provider = get_provider(args.provider)
    rep = symmetry_probe.partisan_asymmetry(provider, args.joke)
    print(json.dumps(rep.to_dict(), indent=2))
    if not rep.measured:
        print("[offline: laugh/B from stub, mirror needs a generator — run under transformers/ollama/pollinations]")
    return 0


def cmd_causal(args: argparse.Namespace) -> int:
    import symmetry_probe

    provider = get_provider(args.provider)
    print(json.dumps(symmetry_probe.causal_structure_probe(provider, args.joke).to_dict(), indent=2))
    return 0


def cmd_callback(args: argparse.Namespace) -> int:
    import remix_history

    provider = get_provider(args.provider)
    lines = Path(args.transcript_file).read_text(encoding="utf-8").splitlines() if args.transcript_file \
        else [l.strip() for l in (args.lines or "").split("||") if l.strip()]
    result = remix_history.generate_callbacks(provider, lines, args.context)
    print(json.dumps(result, indent=2))
    return 0


def cmd_history_remix(args: argparse.Namespace) -> int:
    import remix_history

    provider = get_provider(args.provider)
    print(json.dumps(remix_history.generate_historical(provider, args.topic, canon_key=args.canon or None),
                     indent=2))
    return 0


def cmd_deescalate(args: argparse.Namespace) -> int:
    import deescalate as dees

    provider = get_provider(args.provider)
    result = dees.deescalate(
        provider, args.attack, context=args.context,
        audience_personas=[p.strip() for p in (args.personas or "").split(",") if p.strip()] or None,
    )
    print(json.dumps(result, indent=2))
    if provider.name == "offline":
        print("\n[offline provider: no generation — run under ollama/transformers/openai for real replies]")
    return 0


def cmd_vibe(args: argparse.Namespace) -> int:
    import vibe as vibe_mod

    provider = get_provider(args.provider)
    if args.room and args.text:
        if args.shift:
            result = vibe_mod.vibe_shift(provider, args.room, args.text)
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(json.dumps(vibe_mod.vibe_match(provider, args.text, args.room), indent=2))
        return 0
    prof = vibe_mod.vibe_profile(provider, args.text or args.room)
    print(json.dumps(prof.to_dict(), indent=2))
    return 0


def cmd_live(args: argparse.Namespace) -> int:
    import glob as _glob

    from live_set_controller import SetListController, manual_report, measure_laughter_wav

    paths = sorted(_glob.glob(args.artifacts))
    if not paths:
        print(f"no artifacts match {args.artifacts} — compile some first (mesh_cli.py compile)")
        return 1
    ctl = SetListController(paths, seed=args.seed)
    print(f"show {ctl.show_id}: {len(ctl.programs)} artifacts, {len(ctl.posteriors)} frames. "
          "After each joke enter laughter seconds (e.g. 2.5), a .wav path for an audit clip, "
          "'r' for room read, or 'q' to end.")
    while True:
        prog, text, _ = ctl.next_joke()
        print(f"\n>> [{prog.program_id}] {text}")
        raw = input("laughter> ").strip()
        if raw.lower() == "q":
            break
        if raw.lower() == "r":
            print(json.dumps(ctl.room_read(), indent=2))
            raw = input("laughter> ").strip()
            if raw.lower() == "q":
                break
        report = measure_laughter_wav(raw) if raw.lower().endswith(".wav") else manual_report(float(raw or 0))
        ctl.record_result(prog, report)
        print(f"   {report.verdict} (reward {report.reward}) — log: {ctl.log_path.name}")
    print(json.dumps(ctl.room_read(), indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", default=None, help="offline | ollama | transformers")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("formats")

    p = sub.add_parser("signals")
    p.add_argument("--setup", default="")
    p.add_argument("--punchline", default="")
    p.add_argument("--text", default="", help="whole joke; auto-split if setup/punchline not given")
    p.add_argument("--frame", default="", help="optional explicit frame hint")
    p.add_argument("--personas", default="")

    p = sub.add_parser("generate")
    p.add_argument("--topic", required=True)
    p.add_argument("--format", default="one_liner", choices=sorted(FORMATS))
    p.add_argument("--audience", default="")
    p.add_argument("--preferences", default="")
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--no-score", action="store_true")
    p.add_argument("--receipt-out", default="", help="optional JSON execution receipt path")

    p = sub.add_parser("critique")
    p.add_argument("--text", required=True)
    p.add_argument("--format", default="bar_joke", choices=sorted(FORMATS))
    p.add_argument("--audience", default="")
    p.add_argument("--personas", default="")

    p = sub.add_parser("panel")
    p.add_argument("--text", required=True)
    p.add_argument("--format", default="joke")
    p.add_argument("--personas", default="")

    p = sub.add_parser("compile", help="compile a validated deterministic joke program (Gemma at compile time only)")
    p.add_argument("--topic", required=True)
    p.add_argument("--format", default="one_liner", choices=sorted(FORMATS))
    p.add_argument("--audience", default="")
    p.add_argument("--personas", default="")

    p = sub.add_parser("run-compiled", help="execute a frozen artifact: zero model calls, seeded, auditable")
    p.add_argument("--artifact", required=True)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("compile-clip", help="compile HOOK:/BUILD:/SNAP: script into a deterministic render plan")
    p.add_argument("--script", default="")
    p.add_argument("--from-file", default="")
    p.add_argument("--no-measure", action="store_true")

    p = sub.add_parser("live", help="run a live set: Thompson-sampled picks from frozen artifacts, laughter-updated")
    p.add_argument("--artifacts", default="compiled_artifacts/*.json")
    p.add_argument("--seed", type=int, default=0)

    p = sub.add_parser("vibe", help="measure a vibe: register axes + openness; --room for match, --shift for delta")
    p.add_argument("--text", default="", help="the joke/line to profile (or match against --room)")
    p.add_argument("--room", default="", help="recent room context")
    p.add_argument("--shift", action="store_true", help="measure what --text DOES to --room")

    p = sub.add_parser("deescalate", help="humor off-ramps for a hostile comment: funny AND de-escalating, measured")
    p.add_argument("--attack", required=True)
    p.add_argument("--context", default="")
    p.add_argument("--personas", default="")

    p = sub.add_parser("temporal", help="which cache does a joke rent? self-containedness gap + evergreen score")
    p.add_argument("--joke", required=True)
    p.add_argument("--fact", required=True, help="the event/knowledge the joke depends on")
    p.add_argument("--too-soon", action="store_true", help="also run the temporal-distance collision probe")

    p = sub.add_parser("ingest", help="fetch corpora: wikiquote|gutenberg|rss|transcript|imgflip|hf|reddit")
    p.add_argument("--source", required=True, choices=["wikiquote", "gutenberg", "rss", "transcript", "imgflip", "hf", "reddit"])
    p.add_argument("--query", default="", help="page/book/feed-url/file depending on source")
    p.add_argument("--name", default="", help="corpus name (corpora/<name>.jsonl)")

    p = sub.add_parser("genome", help="the full Humor Genome: all measured dimensions in one auto-routed card")
    p.add_argument("--joke", required=True)
    p.add_argument("--audience", default="")
    p.add_argument("--fact", default="", help="the event/knowledge the joke depends on (routes the temporal probe)")
    p.add_argument("--force", default="", help="comma list to force facets: temporal,politics,causal,deescalation")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("partisan", help="reversal test: is a political joke a partisan weapon or a bridge? (asymmetry + mirror)")
    p.add_argument("--joke", required=True)

    p = sub.add_parser("causal", help="correlation/causation joke: spot-the-fallacy vs believe-the-fallacy, measured")
    p.add_argument("--joke", required=True)

    p = sub.add_parser("callback", help="mine + remix someone's earlier statements into measured callbacks")
    p.add_argument("--transcript-file", default="", help="file with one prior statement per line")
    p.add_argument("--lines", default="", help="inline statements separated by ||")
    p.add_argument("--context", required=True, help="the current moment the callback lands in")

    p = sub.add_parser("history-remix", help="remix public-domain canonical knowledge into a modern topic, R_canon-measured")
    p.add_argument("--topic", required=True)
    p.add_argument("--canon", default="", help="canon key (et_tu, trojan_horse, eureka, ...); empty = sample several")

    args = ap.parse_args()
    return {"formats": cmd_formats, "signals": cmd_signals, "generate": cmd_generate,
            "critique": cmd_critique, "panel": cmd_panel, "compile": cmd_compile,
            "run-compiled": cmd_run_compiled, "compile-clip": cmd_compile_clip,
            "live": cmd_live, "vibe": cmd_vibe, "deescalate": cmd_deescalate,
            "callback": cmd_callback, "history-remix": cmd_history_remix,
            "ingest": cmd_ingest, "temporal": cmd_temporal,
            "partisan": cmd_partisan, "causal": cmd_causal,
            "genome": cmd_genome}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
