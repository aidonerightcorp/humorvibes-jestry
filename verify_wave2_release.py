#!/usr/bin/env python3
"""Verify the complete Wave-2 dataset contract, not only file existence.

    python3 verify_wave2_release.py
    python3 verify_wave2_release.py --root kaggle_wave2

The Kaggle notebook repeats the byte/hash arm before measurement. This local
gate additionally streams every JSONL payload and proves the counts and
stratification claims agree with the census and export summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

import corpus_census as cc

HERE = Path(__file__).resolve().parent
EXPECTED_PAYLOADS = {
    "DATA_CARD.md",
    "aligned_phrases.jsonl",
    "census.json",
    "corpus_sample.jsonl",
    "expectation_violation_frames.jsonl",
    "export_summary.json",
}


class ReleaseValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseValidationError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReleaseValidationError(
                    f"malformed JSON in {path.name}:{line_no}: {exc.msg}"
                ) from exc
            _require(isinstance(row, dict),
                     f"non-object JSON in {path.name}:{line_no}")
            yield line_no, row


def verify(root: Path) -> dict[str, Any]:
    root = root.resolve()
    _require(root.is_dir(), f"release directory does not exist: {root}")
    manifest_path = root / "manifest.json"
    _require(manifest_path.is_file(), "manifest.json is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _require(set(manifest) == EXPECTED_PAYLOADS,
             f"payload set differs: expected {sorted(EXPECTED_PAYLOADS)}, "
             f"got {sorted(manifest)}")

    for name, evidence in manifest.items():
        _require(Path(name).name == name, f"unsafe manifest path: {name!r}")
        path = root / name
        _require(path.is_file(), f"manifest payload is missing: {name}")
        _require(path.stat().st_size == evidence.get("bytes"),
                 f"byte length differs for {name}")
        _require(_sha256(path) == evidence.get("sha256"),
                 f"SHA-256 differs for {name}")

    summary = json.loads((root / "export_summary.json").read_text(encoding="utf-8"))
    census = json.loads((root / "census.json").read_text(encoding="utf-8"))
    _require(summary["full_corpus_rows"] == census["items"],
             "summary full_corpus_rows differs from census items")

    sample_iter = _jsonl(root / "corpus_sample.jsonl")
    try:
        _, first = next(sample_iter)
    except StopIteration as exc:
        raise ReleaseValidationError("corpus_sample.jsonl is empty") from exc
    header = first.get("_meta")
    _require(isinstance(header, dict), "corpus sample has no _meta header")
    _require(header.get("schema_version") == 3, "unexpected sample schema version")
    _require(header.get("rows") == summary["exported_rows"],
             "sample header rows differs from export summary")
    _require(header.get("sampled_from") == census["items"],
             "sample header sampled_from differs from census")
    _require(header.get("eligible_from") == summary["eligible_rows"],
             "sample header eligible_from differs from export summary")
    _require(header.get("release_policy") ==
             "verbatim text only when licence_class=redistributable",
             "sample header does not carry the fail-closed rights policy")
    _require(summary.get("release_policy") == "redistributable_text_only",
             "export summary does not declare the rights policy")
    excluded = summary.get("excluded_by_licence_class")
    _require(isinstance(excluded, dict),
             "export summary omits excluded licence-class counts")
    _require(summary["eligible_rows"] + sum(excluded.values()) == census["items"],
             "eligible plus excluded rows do not reconcile to the census")
    _require("created" not in header, "clock timestamp makes the export nondeterministic")

    families: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    licence_classes: Counter[str] = Counter()
    graded = rows = 0
    required = {"text", "source", "license", "licence_class",
                "language", "form", "domain", "meta"}
    for line_no, row in sample_iter:
        missing = required - set(row)
        _require(not missing,
                 f"corpus_sample.jsonl:{line_no} missing {sorted(missing)}")
        _require(bool(str(row["text"]).strip()),
                 f"corpus_sample.jsonl:{line_no} has blank text")
        rows += 1
        families[cc.source_family(str(row["source"]))] += 1
        languages[str(row["language"])] += 1
        computed_class = cc.classify_licence(str(row["license"]))
        _require(row["licence_class"] == computed_class,
                 f"corpus_sample.jsonl:{line_no} licence class drift")
        _require(cc.may_redistribute_text(str(row["license"])),
                 f"corpus_sample.jsonl:{line_no} ships text without rights clearance")
        licence_classes[computed_class] += 1
        if row.get("funniness_label") is not None:
            graded += 1

    _require(rows == summary["exported_rows"],
             f"sample rows {rows} != summary {summary['exported_rows']}")
    _require(dict(sorted(families.items())) == summary["families"],
             "sample family counts differ from export summary")
    _require(max(families.values(), default=0) <= summary["per_family_cap"],
             "a source family exceeds the published cap")
    _require(len(languages) == summary["languages_in_export"],
             "sample language count differs from export summary")
    _require(dict(sorted(licence_classes.items())) ==
             summary["licence_classes_in_export"],
             "sample licence classes differ from export summary")
    _require(set(licence_classes) <= {"redistributable"},
             "export contains a non-redistributable licence class")
    _require(graded == summary["graded_rows_in_export"],
             "sample graded-row count differs from export summary")

    aligned = 0
    for line_no, row in _jsonl(root / "aligned_phrases.jsonl"):
        aligned += 1
        _require(row.get("language") not in (None, "", "en"),
                 f"aligned_phrases.jsonl:{line_no} is not non-English")
        _require(bool(row.get("translation_en")),
                 f"aligned_phrases.jsonl:{line_no} has no English counterpart")
        _require(bool(row.get("source")) and bool(row.get("license")),
                 f"aligned_phrases.jsonl:{line_no} lacks provenance")
        _require(row.get("licence_class") == "redistributable" and
                 cc.may_redistribute_text(str(row["license"])),
                 f"aligned_phrases.jsonl:{line_no} ships uncleared text")
    _require(aligned == summary["aligned_phrase_pairs"],
             "aligned-pair count differs from export summary")

    frames = 0
    for line_no, row in _jsonl(root / "expectation_violation_frames.jsonl"):
        frames += 1
        _require(bool(row.get("expectation")) and bool(row.get("violation")),
                 f"expectation_violation_frames.jsonl:{line_no} lacks a frame arm")
        _require(bool(row.get("source")) and bool(row.get("license")),
                 f"expectation_violation_frames.jsonl:{line_no} lacks provenance")
        _require(row.get("licence_class") == "redistributable" and
                 cc.may_redistribute_text(str(row["license"])),
                 f"expectation_violation_frames.jsonl:{line_no} ships uncleared text")
    _require(frames == summary["expectation_violation_frames"],
             "frame count differs from export summary")

    card = (root / "DATA_CARD.md").read_text(encoding="utf-8")
    for value in (census["items"], rows, aligned, frames):
        _require(f"{value:,}" in card, f"data card omits published count {value:,}")

    return {
        "status": "PASS",
        "manifest_payloads": len(manifest),
        "full_corpus_rows": census["items"],
        "exported_rows": rows,
        "eligible_rows": summary["eligible_rows"],
        "excluded_rows": sum(excluded.values()),
        "rights_policy": summary["release_policy"],
        "source_families": len(families),
        "language_labels": len(languages),
        "aligned_phrase_pairs": aligned,
        "expectation_violation_frames": frames,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=HERE / "kaggle_wave2")
    args = ap.parse_args()
    try:
        receipt = verify(args.root)
    except (OSError, KeyError, TypeError, json.JSONDecodeError,
            ReleaseValidationError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
