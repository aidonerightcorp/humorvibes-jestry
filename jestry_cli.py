"""Jestry CLI — the verified laugh-reuse loop from a terminal.

    python3 jestry_cli.py charter
    python3 jestry_cli.py cards
    python3 jestry_cli.py search "AI project managers" --audience "NYC tech meetup"
    python3 jestry_cli.py route "AI project managers" --format one_liner
    python3 jestry_cli.py run "AI project managers" --audience "NYC tech meetup" \
        --personas "NYC tech meetup,retired farmers" --format one_liner
    python3 jestry_cli.py laugh --frame "calendar as needy coworker" --seconds 2.5
    python3 jestry_cli.py promote
    python3 jestry_cli.py groaners
    python3 jestry_cli.py stats
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jestry import (  # noqa: E402
    ACCEPTANCE_LEVELS, CHARTER_VERSION, FUNNEL_STAGES, LAWS, MOTTO,
    BitRegistry, HumorPolicy, Jestry, RouteProfile, WorkSpec,
)


def _spec_from_args(args: argparse.Namespace) -> WorkSpec:
    return WorkSpec.from_request(
        args.request, audience=args.audience, format_key=args.format,
        preferences=args.preferences, personas=args.personas,
        consent=args.consent, candidates=args.candidates)


def cmd_charter(_args: argparse.Namespace) -> int:
    print(f"Jestry charter v{CHARTER_VERSION}")
    print(f"Motto: {MOTTO}\n")
    for i, (name, body) in enumerate(LAWS, 1):
        print(f"Law {i:2d} — {name}\n        {body}")
    print("\nFunnel:", " -> ".join(FUNNEL_STAGES))
    print("Acceptance:", " < ".join(ACCEPTANCE_LEVELS))
    return 0


def cmd_cards(args: argparse.Namespace) -> int:
    reg = BitRegistry()
    census = reg.census()
    print(f"registry digest {reg.digest()}")
    for kind, n in sorted(census.items()):
        print(f"  {kind:22s} {n}")
    if args.kind:
        for card in reg.cards.values():
            if card.kind == args.kind:
                print(f"  [{card.acceptance_level:18s}] {card.bit_id:34s} {card.one_line[:64]}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    reg = BitRegistry()
    spec = _spec_from_args(args)
    for card in reg.search(spec, limit=args.limit):
        print(f"[{card.kind:12s}|{card.acceptance_level:18s}] {card.bit_id:36s} {card.one_line[:60]}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    j = Jestry()
    spec = _spec_from_args(args)
    route = j.compile_route(spec)
    print(json.dumps(route.to_dict(), indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    j = Jestry()
    spec = _spec_from_args(args)
    receipt = j.run(spec, live=not args.offline)
    out = receipt["outcome"]
    print(f"route   {receipt['route']['kind']}  ({receipt['route']['compat']})")
    if receipt["escalations"]:
        for esc in receipt["escalations"]:
            print(f"escalate {esc['from']} -> {esc['to']}: {esc['reason']}")
    for cand in receipt["candidates"]:
        mark = "ACCEPT" if cand["accepted"] else "reject"
        laugh = cand.get("laugh_score")
        laugh_s = f"{laugh:5.1f}" if isinstance(laugh, (int, float)) else "  n/a"
        print(f"  [{mark}] laugh={laugh_s} measured={cand.get('measured')} :: {cand['text'][:74]}")
        if not cand["accepted"]:
            print(f"          {cand.get('failure_mode', '')[:96]}")
    if out["accepted"]:
        print(f"\nOUTCOME accepted at level '{out['acceptance_level']}' -> {out['bit_id']}")
        print(f"  {out['text']}")
    else:
        print(f"\nOUTCOME not accepted: {out.get('reason', '')}")
        if out.get("unknowns"):
            print("  open questions:", "; ".join(out["unknowns"]))
    print(f"\nreceipt appended to {j.receipts.path}")
    return 0 if out["accepted"] or out.get("abstained") else 1


def cmd_laugh(args: argparse.Namespace) -> int:
    j = Jestry()
    entry = j.laughloop.record_laughter(args.frame, args.seconds)
    print(json.dumps(entry, indent=2))
    print("shadow updated; serving unchanged until `promote` (governed self-tuning)")
    return 0


def cmd_promote(_args: argparse.Namespace) -> int:
    j = Jestry()
    print(json.dumps(j.laughloop.promote(), indent=2))
    for frame, mean in j.laughloop.serving_order():
        print(f"  serving {mean:.3f}  {frame[:70]}")
    return 0


def cmd_groaners(args: argparse.Namespace) -> int:
    j = Jestry()
    for rec in j.groaners.tail(args.n):
        print(f"[{rec['failure_mode'][:44]:44s}] {rec['joke'][:64]}")
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    j = Jestry()
    print(json.dumps(j.north_star_vector(), indent=2))
    return 0


def cmd_beendone(args: argparse.Namespace) -> int:
    from precedent import quick_check
    rep = quick_check(args.text, live=not args.offline)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Jestry — verified laugh-reuse layer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("charter").set_defaults(fn=cmd_charter)

    p = sub.add_parser("cards")
    p.add_argument("--kind", default="")
    p.set_defaults(fn=cmd_cards)

    def req_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("request")
        p.add_argument("--audience", default="")
        p.add_argument("--format", default="one_liner")
        p.add_argument("--preferences", default="")
        p.add_argument("--personas", default="")
        p.add_argument("--consent", action="store_true")
        p.add_argument("--candidates", type=int, default=3)

    p = sub.add_parser("search")
    req_args(p)
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("route")
    req_args(p)
    p.set_defaults(fn=cmd_route)

    p = sub.add_parser("run")
    req_args(p)
    p.add_argument("--offline", action="store_true",
                   help="no model calls: replay-only rungs, honest non-acceptance elsewhere")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("laugh")
    p.add_argument("--frame", required=True)
    p.add_argument("--seconds", type=float, required=True)
    p.set_defaults(fn=cmd_laugh)

    sub.add_parser("promote").set_defaults(fn=cmd_promote)

    p = sub.add_parser("groaners")
    p.add_argument("-n", type=int, default=10)
    p.set_defaults(fn=cmd_groaners)

    sub.add_parser("stats").set_defaults(fn=cmd_stats)

    p = sub.add_parser("beendone")
    p.add_argument("text")
    p.add_argument("--offline", action="store_true")
    p.set_defaults(fn=cmd_beendone)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
