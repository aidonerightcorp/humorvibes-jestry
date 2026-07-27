#!/usr/bin/env python3
"""Build the deterministic Humor Genome Open Controls Kaggle release.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable

from humorvibes.open_controls import (
    COUNTERFACTUAL_ARMS,
    DATA_LICENSE,
    DATA_LICENSE_NOTICE,
    DATASET_ID,
    DATASET_TITLE,
    DEFAULT_SEED,
    GENERATOR_ID,
    GENERATOR_VERSION,
    MAX_CONFIGS,
    MAX_FAMILIES,
    MAX_VARIANTS,
    SCHEMA_VERSION,
    AuditAccumulator,
    audit_reference_overlap,
    generation_contract,
    human_contribution_schema,
    human_rating_schema,
    iter_rows,
    model_candidate_schema,
    retrieval_rows,
    row_schema,
    validate_manifest,
    write_jsonl,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "kaggle_open_controls"
DEFAULT_METADATA = ROOT / "open_controls_dataset" / "dataset-metadata.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "source-not-in-git"


def _write_parquet(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - exercised by CLI error path
        raise RuntimeError(
            "Parquet release output requires pyarrow; install requirements-dev.txt or pass --no-parquet"
        ) from exc

    writer: Any = None
    batch: list[dict[str, Any]] = []
    count = 0
    try:
        for row in rows:
            batch.append(row)
            if len(batch) < 2_000:
                continue
            table = pa.Table.from_pylist(batch)
            writer = writer or pq.ParquetWriter(path, table.schema, compression="zstd")
            writer.write_table(table)
            count += len(batch)
            batch.clear()
        if batch:
            table = pa.Table.from_pylist(batch)
            writer = writer or pq.ParquetWriter(path, table.schema, compression="zstd")
            writer.write_table(table)
            count += len(batch)
    finally:
        if writer is not None:
            writer.close()
    return count


def _data_card(summary: dict[str, Any], audit: dict[str, Any], reference: dict[str, Any]) -> str:
    counts = audit["counts"]
    surface = audit["adversarial"]["surface_only_arm_accuracy"]
    return f"""# {DATASET_TITLE}

An openly reusable, deterministic counterfactual corpus for studying one narrow question:
**what changes when an expected continuation is replaced by surprise without repair, surprise
with compact lexical repair, or the same repair explained too explicitly?**

## Executive summary

| Question | Answer |
| --- | --- |
| What is this? | {summary['rows']:,} project-controlled English synthetic records arranged into matched four-arm groups. |
| What is the independent structure? | {counts['premise_families']:,} premise families from {counts['template_families']} isolated lexical-frame templates. |
| Is it human humor evidence? | **No.** No row is human-authored, human-rated, or a ground-truth funniness label. |
| What may it support? | Software fixtures, causal-design prototypes, grouped evaluation, retrieval benchmarks, and preregistered human-rating studies. |
| What may it not support? | Claims that an arm is funny, culturally representative, safe for every audience, or neurologically validated. |

## Counterfactual design

Every configuration contains two surface variants of four matched arms:

1. `expected_literal` — unsurprising continuation with no reframe.
2. `surprising_unresolved` — unexpected continuation with no recoverable connection.
3. `surprising_resolved` — unexpected continuation with a compact lexical reframe.
4. `resolved_overexplained` — the same two senses stated explicitly.

The intended sequence is `expectation -> violation -> optional repair`. It operationalizes a
starting hypothesis; it does not prove a brain mechanism or audience response.

## Release contents

| File | Purpose |
| --- | --- |
| `open_controls.jsonl` | Canonical line-delimited source rows |
| `open_controls.parquet` | Analysis-optimized copy with the identical rows |
| `open-controls-row.schema.json` | Strict row contract |
| `retrieval_documents.jsonl` | One compact-repair document per premise family |
| `retrieval_queries.jsonl` | Paired mechanism queries |
| `retrieval_qrels.jsonl` | Exact relevance mapping for embedding/reranking evaluation |
| `audit.json` | Recomputed balance, leakage, duplication, safety, and artifact checks |
| `reference_overlap.json` | Exact and 12-word overlap screen against the existing local inventory |
| `human-rating.schema.json` | Privacy-minimized contract for future real observations |
| `human-contribution.schema.json` | Original-contribution consent and CC0 attestation contract |
| `model-candidate.schema.json` | Quarantined model-output provenance contract |
| `release_summary.json` | Build parameters and controlling truth boundary |
| `release-metadata.json` | Downloadable Kaggle identity, visibility intent, licence, and discovery metadata |
| `manifest.json` | SHA-256 and byte length for every payload file |

## Scale and independence

The full release is produced by:

```text
{summary['families']} premise families
x {summary['configs']} controlled configurations
x {len(COUNTERFACTUAL_ARMS)} counterfactual arms
x {summary['variants']} surface variants
= {summary['rows']:,} rows
```

Rows sharing a premise or template are not independent observations. `split` is assigned by
`template_family_id`: {counts['splits'].get('train', 0):,} train,
{counts['splits'].get('validation', 0):,} validation, and
{counts['splits'].get('test', 0):,} test rows. Random row splitting would leak generator structure.

## Adversarial audit

- Release checks: **{'PASS' if audit['ok'] else 'FAIL'}**.
- Normalized exact duplicate texts: **{audit['violations']['duplicate_normalized_texts']}**.
- Premise/template split leaks: **{len(audit['violations']['premise_split_leaks_capped'])}/
  {len(audit['violations']['template_split_leaks_capped'])}**.
- Surface-only arm prediction: **{surface:.1%}** versus **25.0% chance**. This is a measured
  generator-artifact diagnostic, not evidence of semantic quality.
- Existing-inventory screen: **{reference['exact_matches']} exact** and
  **{reference['long_phrase_matches']} long-phrase** matches across
  **{reference['reference_rows_scanned']:,} readable reference rows**.

The reference screen is useful evidence, not a worldwide originality guarantee. It cannot find
every paraphrase, private work, trademark, privacy issue, or culturally sensitive association.

## Quick start

```python
import pandas as pd

rows = pd.read_parquet("/kaggle/input/humor-genome-open-controls/open_controls.parquet")
assert len(rows) == {summary['rows']}
assert rows.groupby("premise_id")["split"].nunique().max() == 1
print(rows.groupby("counterfactual_arm").size())
```

## Human ratings and contributions

No ratings are bundled. Future studies should join observations by `item_id`, use the supplied
rating schema, collect informed consent, randomize presentation, and measure expectedness,
surprise, resolution, funniness, familiarity, comprehensibility, and offensiveness separately.
Product logs are not automatically research consent.

Human-original contributions belong in a separate lane and require both an authorship
attestation and an explicit CC0 affirmation. Model-generated candidates remain quarantined with
provider, exact model version, prompt hash, parameters, and generation time; local generation
does not itself establish copyright freedom or human authorship.

## Licensing

The Open Controls payload is dedicated under **CC0-1.0** to the extent contributors hold the
relevant rights. Attribution is requested but not required. Imported Humor Genome Wave 2 records
are not part of this payload and retain their own licenses. CC0 does not waive third-party
trademark, patent, privacy, or publicity rights.

Generator/API source: https://github.com/aidonerightcorp/humorvibes-jestry
Canonical CC0 deed: https://creativecommons.org/publicdomain/zero/1.0/
"""


def build(
    *,
    out_dir: Path = DEFAULT_OUT,
    families: int = MAX_FAMILIES,
    configs: int = MAX_CONFIGS,
    variants: int = MAX_VARIANTS,
    seed: int = DEFAULT_SEED,
    generator_commit: str | None = None,
    metadata_template: Path | None = DEFAULT_METADATA,
    reference_paths: Iterable[Path] = (),
    parquet: bool = True,
) -> dict[str, Any]:
    generator_commit = generator_commit or _git_commit()
    out_dir = out_dir.resolve()
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    reference_paths = tuple(sorted(Path(path) for path in reference_paths))

    with tempfile.TemporaryDirectory(prefix=".open-controls-", dir=out_dir.parent) as temp:
        stage = Path(temp)
        corpus_path = stage / "open_controls.jsonl"
        accumulator = AuditAccumulator()
        with corpus_path.open("w", encoding="utf-8", newline="\n") as fh:
            for row in iter_rows(
                families=families,
                configs=configs,
                variants=variants,
                seed=seed,
                generator_commit=generator_commit,
            ):
                accumulator.add(row)
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        audit = accumulator.report()
        if not audit["ok"]:
            raise RuntimeError("Open Controls corpus failed its internal audit: " + json.dumps(audit["checks"], sort_keys=True))

        if parquet:
            parquet_rows = _write_parquet(
                stage / "open_controls.parquet",
                iter_rows(
                    families=families,
                    configs=configs,
                    variants=variants,
                    seed=seed,
                    generator_commit=generator_commit,
                ),
            )
            if parquet_rows != accumulator.rows:
                raise RuntimeError("Parquet and JSONL row counts differ")

        documents, queries, qrels = retrieval_rows(
            iter_rows(
                families=families,
                configs=1,
                variants=variants,
                seed=seed,
                generator_commit=generator_commit,
            )
        )
        write_jsonl(stage / "retrieval_documents.jsonl", documents)
        write_jsonl(stage / "retrieval_queries.jsonl", queries)
        write_jsonl(stage / "retrieval_qrels.jsonl", qrels)

        reference = audit_reference_overlap(accumulator.prototype_rows, reference_paths)
        if reference_paths and not reference["ok"]:
            raise RuntimeError("Open Controls rows overlap the reference inventory; inspect reference_overlap.json")

        summary = {
            "dataset_id": DATASET_ID,
            "title": DATASET_TITLE,
            "schema_version": SCHEMA_VERSION,
            "rows": accumulator.rows,
            "families": families,
            "configs": configs,
            "variants": variants,
            "counterfactual_arms": list(COUNTERFACTUAL_ARMS),
            "random_seed": seed,
            "generator_id": GENERATOR_ID,
            "generator_version": GENERATOR_VERSION,
            "generator_commit": generator_commit,
            "generator_source_sha256": generation_contract()["generator_source_sha256"],
            "license_spdx": DATA_LICENSE,
            "data_origin": "procedural",
            "human_authored_rows": 0,
            "human_rated_rows": 0,
            "retrieval_documents": len(documents),
            "retrieval_queries": len(queries),
            "build_is_clock_free": True,
            "truth_boundary": generation_contract()["truth_boundary"],
        }
        _json(stage / "open-controls-row.schema.json", row_schema())
        _json(stage / "human-rating.schema.json", human_rating_schema())
        _json(stage / "human-contribution.schema.json", human_contribution_schema())
        _json(stage / "model-candidate.schema.json", model_candidate_schema())
        _json(stage / "audit.json", audit)
        _json(stage / "reference_overlap.json", reference)
        _json(stage / "release_summary.json", summary)
        _json(stage / "provenance.json", {
            "dataset_id": DATASET_ID,
            "data_origin": "procedural",
            "source_repository": "https://github.com/aidonerightcorp/humorvibes-jestry",
            "generator_commit": generator_commit,
            "generator_source_sha256": summary["generator_source_sha256"],
            "generator_made_network_calls": False,
            "generator_used_llm_calls": False,
            "human_authorship_claimed": False,
            "human_ratings_included": False,
            "license_spdx": DATA_LICENSE,
            "rights_scope": "project-controlled Open Controls data only",
        })
        (stage / "LICENSE-DATA.txt").write_text(DATA_LICENSE_NOTICE, encoding="utf-8")
        card = _data_card(summary, audit, reference)
        (stage / "DATASET_CARD.md").write_text(card, encoding="utf-8")
        (stage / "README.md").write_text(card, encoding="utf-8")

        if metadata_template is not None:
            metadata = json.loads(metadata_template.read_text(encoding="utf-8"))
        else:
            metadata = {
                "title": DATASET_TITLE,
                "id": f"taylorsamarel/{DATASET_ID}",
                "licenses": [{"name": DATA_LICENSE}],
            }
        # Kaggle consumes and removes its reserved dataset-metadata.json upload control.
        # Preserve an independently verifiable copy inside the downloadable payload.
        _json(stage / "release-metadata.json", metadata)

        manifest_files: dict[str, dict[str, Any]] = {}
        for path in sorted(stage.iterdir()):
            if path.name in {"manifest.json", "dataset-metadata.json"} or not path.is_file():
                continue
            manifest_files[path.name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        _json(stage / "manifest.json", {
            "dataset_id": DATASET_ID,
            "schema_version": SCHEMA_VERSION,
            "files": manifest_files,
        })

        _json(stage / "dataset-metadata.json", metadata)

        out_dir.mkdir(parents=True, exist_ok=True)
        new_names = {path.name for path in stage.iterdir() if path.is_file()}
        unexpected = sorted(path.name for path in out_dir.iterdir() if path.is_file() and path.name not in new_names)
        if unexpected:
            raise RuntimeError(f"refusing to overwrite output directory containing unexpected files: {unexpected}")
        for source in sorted(stage.iterdir()):
            if source.is_file():
                os.replace(source, out_dir / source.name)

    manifest_receipt = validate_manifest(out_dir)
    if not manifest_receipt["ok"]:
        raise RuntimeError("built manifest did not verify: " + json.dumps(manifest_receipt, sort_keys=True))
    return {
        "ok": True,
        "out_dir": str(out_dir),
        "rows": summary["rows"],
        "files": manifest_receipt["files"],
        "audit": audit,
        "reference_overlap": reference,
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--families", type=int, default=MAX_FAMILIES)
    parser.add_argument("--configs", type=int, default=MAX_CONFIGS)
    parser.add_argument("--variants", type=int, default=MAX_VARIANTS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--generator-commit")
    parser.add_argument("--metadata-template", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--reference-dir", type=Path, help="scan every JSONL file in this directory for overlap")
    parser.add_argument("--no-parquet", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    references = sorted(args.reference_dir.glob("*.jsonl")) if args.reference_dir else ()
    receipt = build(
        out_dir=args.out_dir,
        families=args.families,
        configs=args.configs,
        variants=args.variants,
        seed=args.seed,
        generator_commit=args.generator_commit,
        metadata_template=args.metadata_template,
        reference_paths=references,
        parquet=not args.no_parquet,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
