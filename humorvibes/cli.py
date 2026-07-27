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

    study_launch = sub.add_parser(
        "study-launch",
        help="build a precision-planned, blinded precollection launch pack",
    )
    study_launch.add_argument("--protocol", type=Path, required=True)
    study_launch.add_argument("--out-dir", type=Path, required=True)
    study_launch.add_argument("--assignment-key-file", type=Path, required=True)
    study_launch.add_argument("--target-effect", type=float)
    study_launch.add_argument("--between-writer-sd", type=float, default=0.45)
    study_launch.add_argument("--within-writer-premise-sd", type=float, default=0.60)
    study_launch.add_argument("--premises-per-writer", type=int, default=2)
    study_launch.add_argument("--alpha", type=float, default=0.05)
    study_launch.add_argument("--power", type=float, default=0.80)
    study_launch.add_argument("--writer-attrition-rate", type=float, default=0.15)
    study_launch.add_argument("--force", action="store_true", help="replace files in an existing pack")

    study_key = sub.add_parser(
        "study-key",
        help="create a mode-0600 private randomization key without printing it",
    )
    study_key.add_argument("--out", type=Path, required=True)

    sub.add_parser("controls-info", help="show the deterministic Open Controls corpus contract")
    controls_sample = sub.add_parser("controls-sample", help="print bounded procedural Open Controls rows")
    controls_sample.add_argument("--count", type=int, default=8)
    controls_sample.add_argument("--seed", type=int, default=20_260_727)
    controls_sample.add_argument("--arm")
    controls_sample.add_argument("--split")
    controls_ratings = sub.add_parser(
        "controls-validate-ratings",
        help="fail-closed validation of privacy-minimized human-rating JSONL",
    )
    controls_ratings.add_argument("path", type=Path)
    controls_contrib = sub.add_parser(
        "controls-validate-contributions",
        help="fail-closed validation of human-original contribution JSONL",
    )
    controls_contrib.add_argument("path", type=Path)
    controls_models = sub.add_parser(
        "controls-validate-model-candidates",
        help="validate provenance-complete model candidates while preserving quarantine",
    )
    controls_models.add_argument("path", type=Path)

    retrieval_build = sub.add_parser(
        "retrieval-hard-build",
        help="derive masked hard queries and hard negatives from an Open Controls release",
    )
    retrieval_build.add_argument("--release-root", type=Path, required=True)
    retrieval_build.add_argument("--out-dir", type=Path, required=True)
    retrieval_build.add_argument("--force", action="store_true")

    retrieval_benchmark = sub.add_parser(
        "retrieval-benchmark",
        help="evaluate TF-IDF or an allowlisted embedding model on frozen hard qrels",
    )
    retrieval_benchmark.add_argument("--root", type=Path, required=True)
    retrieval_benchmark.add_argument("--model", default="lexical:tfidf")
    retrieval_benchmark.add_argument("--out", type=Path)

    multimodal_fixture = sub.add_parser(
        "multimodal-fixture",
        help="build and evaluate the rights-safe procedural multimodal contract fixture",
    )
    multimodal_fixture.add_argument("--out-dir", type=Path, required=True)
    multimodal_fixture.add_argument("--contests", type=int, default=30)
    multimodal_fixture.add_argument("--force", action="store_true")

    multimodal_benchmark = sub.add_parser(
        "multimodal-benchmark",
        help="validate and evaluate text, image, and fusion arms on one frozen fixture",
    )
    multimodal_benchmark.add_argument("--root", type=Path, required=True)
    multimodal_benchmark.add_argument("--out", type=Path)

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
        if getattr(args, "out", None):
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

    if args.command == "study-key":
        from .study_launch import create_assignment_key

        try:
            payload = create_assignment_key(args.out)
        except IntegrationError as exc:
            _dump({"error": exc.public()})
            return 2
        _dump(payload)
        return 0

    if args.command in {"retrieval-hard-build", "retrieval-benchmark"}:
        from .retrieval_benchmark import (
            build_hard_retrieval_rows,
            evaluate_retrieval,
            load_retrieval_dataset,
            read_jsonl,
            write_retrieval_dataset,
        )

        try:
            if args.command == "retrieval-hard-build":
                dataset = build_hard_retrieval_rows(
                    read_jsonl(args.release_root / "retrieval_documents.jsonl"),
                    read_jsonl(args.release_root / "retrieval_queries.jsonl"),
                    read_jsonl(args.release_root / "retrieval_qrels.jsonl"),
                )
                payload = write_retrieval_dataset(
                    args.out_dir, dataset, overwrite=args.force
                )
            else:
                payload = evaluate_retrieval(
                    load_retrieval_dataset(args.root), model_id=args.model
                )
        except (OSError, json.JSONDecodeError) as exc:
            _dump({"error": {"code": "invalid_retrieval_file", "message": str(exc)}})
            return 2
        except IntegrationError as exc:
            _dump({"error": exc.public()})
            return 2
        _dump(payload)
        if getattr(args, "out", None):
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return 0

    if args.command in {"multimodal-fixture", "multimodal-benchmark"}:
        from .multimodal_benchmark import (
            build_synthetic_multimodal_fixture,
            evaluate_multimodal_fixture,
            write_benchmark_receipt,
            write_multimodal_fixture,
        )

        try:
            if args.command == "multimodal-fixture":
                fixture = build_synthetic_multimodal_fixture(contests=args.contests)
                write_multimodal_fixture(args.out_dir, fixture, overwrite=args.force)
                payload = evaluate_multimodal_fixture(args.out_dir)
                write_benchmark_receipt(args.out_dir, payload)
            else:
                payload = evaluate_multimodal_fixture(args.root)
        except (OSError, json.JSONDecodeError) as exc:
            _dump({"error": {"code": "invalid_multimodal_file", "message": str(exc)}})
            return 2
        except IntegrationError as exc:
            _dump({"error": exc.public()})
            return 2
        _dump(payload)
        if getattr(args, "out", None):
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return 0

    if args.command in {
        "controls-info",
        "controls-sample",
        "controls-validate-ratings",
        "controls-validate-contributions",
        "controls-validate-model-candidates",
    }:
        from .open_controls import (
            generation_contract,
            sample_rows,
            validate_human_contributions,
            validate_human_ratings,
            validate_model_candidates,
        )

        try:
            if args.command == "controls-info":
                payload = generation_contract()
            elif args.command == "controls-sample":
                payload = {
                    "rows": sample_rows(args.count, seed=args.seed, arm=args.arm, split=args.split),
                    "truth_boundary": generation_contract()["truth_boundary"],
                }
            elif args.command == "controls-validate-ratings":
                payload = validate_human_ratings(args.path)
            elif args.command == "controls-validate-contributions":
                payload = validate_human_contributions(args.path)
            else:
                payload = validate_model_candidates(args.path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            _dump({"error": {"code": "invalid_open_controls_input", "message": str(exc)}})
            return 2
        _dump(payload)
        return 0 if payload.get("ok", True) else 1

    if args.command in {"study-protocol", "study-demo", "study-analyze", "study-launch"}:
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
            elif args.command == "study-analyze":
                protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
                bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
                payload = analyze_study(protocol, bundle)
            else:
                from .study_launch import build_launch_pack, read_assignment_key, write_launch_pack

                protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
                pack = build_launch_pack(
                    protocol,
                    assignment_key=read_assignment_key(args.assignment_key_file),
                    target_effect=args.target_effect,
                    between_writer_sd=args.between_writer_sd,
                    within_writer_premise_sd=args.within_writer_premise_sd,
                    premises_per_writer=args.premises_per_writer,
                    alpha=args.alpha,
                    power=args.power,
                    writer_attrition_rate=args.writer_attrition_rate,
                )
                payload = write_launch_pack(args.out_dir, pack, overwrite=args.force)
        except (OSError, json.JSONDecodeError) as exc:
            _dump({"error": {"code": "invalid_study_file", "message": str(exc)}})
            return 2
        except IntegrationError as exc:
            _dump({"error": exc.public()})
            return 2
        _dump(payload)
        if getattr(args, "out", None):
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
