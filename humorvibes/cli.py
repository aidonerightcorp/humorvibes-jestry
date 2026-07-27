"""Command-line diagnostics and SDK examples for the deployable integration layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .errors import IntegrationError
from .service import HumorVibesService


def _dump(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("capabilities", help="list configured model IDs and truth boundaries")
    doctor = sub.add_parser("doctor", help="validate configuration; --live also probes configured backends")
    doctor.add_argument("--live", action="store_true")

    generate = sub.add_parser("generate", help="run an allowlisted LLM model")
    generate.add_argument("prompt")
    generate.add_argument("--model")
    generate.add_argument("--max-tokens", type=int, default=512)
    generate.add_argument("--temperature", type=float, default=0.8)
    generate.add_argument("--json", action="store_true")
    generate.add_argument("--think", action="store_true")

    humor = sub.add_parser("humor", help="generate candidates under a HumorVibes format contract")
    humor.add_argument("topic")
    humor.add_argument("--format", default="one_liner")
    humor.add_argument("--audience", default="")
    humor.add_argument("--preferences", default="")
    humor.add_argument("--count", type=int, default=4)
    humor.add_argument("--model")

    embed = sub.add_parser("embed", help="embed one or more texts with an allowlisted model")
    embed.add_argument("texts", nargs="+")
    embed.add_argument("--model")
    embed.add_argument("--dimensions", type=int)

    similarity = sub.add_parser("similarity", help="cosine similarity between two texts")
    similarity.add_argument("left")
    similarity.add_argument("right")
    similarity.add_argument("--model")

    adversarial = sub.add_parser(
        "adversarial",
        help="run the deterministic network-free integration attack suite",
    )
    adversarial.add_argument("--out", type=Path, help="also write the JSON receipt to this path")

    openapi = sub.add_parser(
        "openapi",
        help="write the deterministic OpenAPI contract for app/client generation",
    )
    openapi.add_argument("--out", type=Path, default=Path("docs/openapi.json"))

    study_protocol = sub.add_parser(
        "study-protocol",
        help="write the frozen privacy-minimized writer-study protocol",
    )
    study_protocol.add_argument("--out", type=Path, help="write JSON instead of only printing it")
    study_protocol.add_argument(
        "--human-observed",
        action="store_true",
        help="mark the protocol for real human observations; preregistration is still required",
    )

    study_demo = sub.add_parser(
        "study-demo",
        help="run the study analyzer on synthetic contract data (never claim-ready)",
    )
    study_demo.add_argument("--out", type=Path, help="also write the JSON receipt")

    study_analyze = sub.add_parser(
        "study-analyze",
        help="analyze a local privacy-minimized study bundle against a frozen protocol",
    )
    study_analyze.add_argument("--protocol", type=Path, required=True)
    study_analyze.add_argument("--bundle", type=Path, required=True)
    study_analyze.add_argument("--out", type=Path, help="also write the JSON receipt")

    sub.add_parser("serve", help="run the FastAPI server")
    args = parser.parse_args()
    if args.command == "serve":
        from .api import run as run_api

        run_api()
        return 0

    if args.command == "adversarial":
        from .adversarial import run_adversarial_suite

        receipt = run_adversarial_suite()
        _dump(receipt)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return 0 if receipt["ok"] else 1

    if args.command == "openapi":
        from .openapi import export_openapi

        print(export_openapi(args.out))
        return 0

    if args.command in {"study-protocol", "study-demo", "study-analyze"}:
        from .studies import (
            analyze_study,
            default_study_protocol,
            synthetic_demo_receipt,
        )

        try:
            if args.command == "study-protocol":
                payload = default_study_protocol(
                    data_origin="human_observed" if args.human_observed else "synthetic_contract_fixture"
                )
            elif args.command == "study-demo":
                payload = synthetic_demo_receipt()
            else:
                protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
                bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
                payload = analyze_study(protocol, bundle)
        except (OSError, json.JSONDecodeError) as exc:
            _dump({"error": {"code": "invalid_study_file", "message": str(exc)}})
            return 2
        except IntegrationError as exc:
            _dump({"error": exc.public()})
            return 2
        _dump(payload)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return 0

    service = HumorVibesService()
    try:
        if args.command == "capabilities":
            _dump(service.capabilities())
        elif args.command == "doctor":
            _dump(service.ready(live=args.live))
        elif args.command == "generate":
            _dump(service.generate(
                args.prompt,
                model_id=args.model,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                json_mode=args.json,
                think=args.think,
            ))
        elif args.command == "humor":
            _dump(service.generate_humor(
                args.topic,
                format_key=args.format,
                audience=args.audience,
                preferences=args.preferences,
                count=args.count,
                model_id=args.model,
            ))
        elif args.command == "embed":
            _dump(service.embed(args.texts, model_id=args.model, dimensions=args.dimensions))
        elif args.command == "similarity":
            _dump(service.similarity([args.left], [args.right], model_id=args.model))
    except IntegrationError as exc:
        _dump({"error": exc.public()})
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
