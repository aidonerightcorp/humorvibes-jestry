"""Slim, publishable export of the wave-2 corpus for a Kaggle dataset.

The full corpus is multi-million-row and over a gigabyte, with one source family
large enough to dominate a naive sample.
Shipping that verbatim would be both unwieldy and misleading. This builds a
STRATIFIED slice instead, plus the derived artifacts that carry the actual
findings.

Design decisions that keep the export honest:

* STRATIFIED, NOT TRUNCATED. Rows are capped PER SOURCE FAMILY, so the New
  Yorker caption archive stops dominating and small languages survive. A
  head -n slice would have produced another caption-dominated file.
* DETERMINISTIC. Selection is by sha256 of the text, not by random sampling or
  file order, so the same corpus produces the same export byte-for-byte.
* RIGHTS FAIL CLOSED. Every row keeps its own `source` and `license`, but
  verbatim text ships only when the normalized licence policy explicitly
  permits redistribution. Research-only, noncommercial, conflicting and
  unclassified rows remain in the local census and are excluded from payloads.
* NOTHING IS INVENTED. Only rows already in corpora/ are exported; the census
  and style labels are recomputed here rather than copied, so the numbers in
  the card cannot drift from the data beside them.

    python3 build_kaggle_export.py --per-family 12000
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import corpus_census as cc
import style_taxonomy as st

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "kaggle_wave2"
DATASET_METADATA_TEMPLATE = ROOT / "wave2_dataset" / "dataset-metadata.json"


def _key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(rec: dict[str, Any]) -> str:
    return json.dumps(rec, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _rank(rec: dict[str, Any]) -> int:
    """Text hash first, canonical-row hash only as a deterministic tie break."""
    primary = _key(str(rec.get("text", "")))
    secondary = hashlib.sha256(_canonical(rec).encode("utf-8")).hexdigest()
    return int(primary + secondary, 16)


def _translation_en(rec: dict[str, Any]) -> Any:
    meta = rec.get("meta", {}) or {}
    for key in ("translation_en", "english", "gold", "joke_english",
                "english_translation"):
        if meta.get(key):
            return meta[key]
    # This upstream CSV has no header, so its first English value became the
    # literal column name. The ingestion spec preserves it verbatim; recognise
    # that verified schema here so the Urdu pairs do not disappear on export.
    if rec.get("source") == "hf:Ehtisham1328/urdu-idioms-with-english-translation":
        return meta.get("Hard work is the key to success.")
    return None


def _data_card(summary: dict[str, Any], census: dict[str, Any]) -> str:
    largest = max(summary["families"].values(), default=0)
    largest_share = largest / summary["exported_rows"] if summary["exported_rows"] else 0.0
    excluded_total = sum(summary["excluded_by_licence_class"].values())
    return f"""# Humor Genome Wave 2 — public research dataset

This is the public data layer for the
[Humor Genome Wave 2 executable Gemma study](https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study).
It contains a deterministic, rights-filtered, source-stratified slice of a
{census['items']:,}-item research inventory, plus translation pairs, annotated frames, a full
census, exact build parameters, and a cryptographic manifest.

## Start here

| If you want to… | Use |
| --- | --- |
| Analyze public text with provenance and structural labels | `corpus_sample.jsonl` |
| Study non-English phrases with English counterparts | `aligned_phrases.jsonl` |
| Study expectation and violation without inferring the frame | `expectation_violation_frames.jsonl` |
| Audit what exists in the full local inventory, including unpublished material | `census.json` |
| Reproduce counts and selection policy | `export_summary.json` |
| Verify every mounted byte before analysis | `manifest.json` |

## Release summary

- Full research inventory: **{census['items']:,} rows**.
- Explicitly redistribution-eligible before stratification: **{summary['eligible_rows']:,} rows**.
- Public slice: **{summary['exported_rows']:,} rows** across
  **{summary['languages_in_export']} language labels**.
- Not republished verbatim: **{excluded_total:,} rows**; they remain represented in the census.
- Derived public artifacts: **{summary['aligned_phrase_pairs']:,} aligned phrase pairs** and
  **{summary['expectation_violation_frames']:,} expectation/violation frames**.

This is not a random sample and not a universal funniness benchmark. Its purpose is public,
auditable research without allowing one caption archive or unclear redistribution rights to
dominate the release.

## Quick start on Kaggle

```python
import json
from pathlib import Path

root = next(Path("/kaggle/input").rglob("corpus_sample.jsonl")).parent
with (root / "corpus_sample.jsonl").open(encoding="utf-8") as fh:
    header = json.loads(next(fh))["_meta"]
    first = json.loads(next(fh))

print(header)
print(first["text"], first["source"], first["license"])
```

## Files

| file | what it is |
| --- | --- |
| `corpus_sample.jsonl` | {summary['exported_rows']:,} rows with text, per-row provenance/licence, language, form, domain, metadata, and a human signal where one exists |
| `expectation_violation_frames.jsonl` | {summary['expectation_violation_frames']:,} human-annotated expectation/violation frames |
| `aligned_phrases.jsonl` | {summary['aligned_phrase_pairs']:,} non-English phrases paired with English text |
| `census.json` | full-corpus counts by source family, language, and licence class |
| `export_summary.json` | exact selection counts and parameters |
| `manifest.json` | SHA-256 and byte length of every published payload file |

## Main row schema

| field | meaning |
| --- | --- |
| `text` | verbatim public text |
| `source`, `license`, `licence_class` | per-row provenance and release decision |
| `language` | source-provided or normalized language label |
| `form` | deterministic structural-template label |
| `domain` | lexical topic guess, not ground truth |
| `meta` | source-specific metadata, including declared style where available |
| `funniness_label` | optional source-specific human signal; scales differ across families |

## Selection

Rows are ordered by SHA-256 of their text and capped at
{summary['per_family_cap']:,} per source family. The largest family is therefore
{largest_share:.1%} of the export rather than allowing the caption archive to dominate.
The export contains {summary['languages_in_export']} language labels. There is no random state,
clock timestamp, or input-order tie: the same corpus and cap produce identical bytes.

## Licensing

**The collection has no single licence.** The complete local inventory includes material that
is useful for research but is not cleared for republication. This release fails closed: only
rows whose normalized per-record licence is explicitly redistributable carry text. The exported
licence classes are:
{json.dumps(summary['licence_classes_in_export'], ensure_ascii=False, sort_keys=True)}.
Rows excluded before sampling are:
{json.dumps(summary['excluded_by_licence_class'], ensure_ascii=False, sort_keys=True)}.
That classification is a release policy, not legal advice; downstream users must still honour
the exact per-row licence and attribution terms.

## Labels and limitations

- `form` is a deterministic structural-template label. Generic buckets describe shape, not
  mechanism.
- `domain` is a keyword guess, not ground truth.
- Source-declared style metadata is stronger than either inferred axis.
- `funniness_label` is source-specific (mean rating, vote ratio, or upvotes); do not pool it
  across families without calibration.
- Screening is a script-aware length floor plus a conservative slur regex. It does not detect
  every stereotype or harmful premise.
- The multilingual supply contains many proverbs/idioms as well as jokes. Phrase rows are not
  silently presented as human-graded comedy.

## Related public artifacts

- Executable write-up: https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study
- Source, methods, tests, and receipts: https://github.com/aidonerightcorp/humorvibes-jestry
- Machine-readable publication receipt:
  https://github.com/aidonerightcorp/humorvibes-jestry/blob/main/jestry_out/wave2_publication.json
"""


def build(per_family: int, *, paths: Iterable[Path] | None = None,
          out_dir: Path | None = None,
          metadata_template: Path | None = None) -> dict[str, Any]:
    if per_family <= 0:
        raise ValueError("per_family must be positive")
    out_dir = out_dir or OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    source_paths = sorted(st.CORPORA.glob("*.jsonl") if paths is None else paths)
    # Each heap holds only the best N rows for one family. The old exporter
    # retained every decoded dict in the multi-million-row corpus before
    # sorting, which made a supposedly slim export require several gigabytes
    # of RAM.
    buckets: dict[str, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
    serial = 0
    census_acc = cc.CensusAccumulator()
    excluded: Counter = Counter()
    eligible_rows = 0

    with tempfile.TemporaryDirectory(prefix=".kaggle-wave2-", dir=out_dir.parent) as td:
        stage = Path(td)
        frames_path = stage / "expectation_violation_frames.jsonl"
        aligned_path = stage / "aligned_phrases.jsonl"
        n_frames = n_aligned = 0
        with frames_path.open("w", encoding="utf-8") as frames_fh, \
                aligned_path.open("w", encoding="utf-8") as aligned_fh:
            # A release must fail closed: best-effort analysis readers may skip
            # damaged lines, but published counts must never silently omit one.
            for rec in st.iter_corpus(source_paths, strict=True):
                census_acc.add(rec)
                licence = str(rec.get("license", ""))
                licence_class = cc.classify_licence(licence)
                if not cc.may_redistribute_text(licence):
                    excluded[licence_class] += 1
                    continue
                eligible_rows += 1
                fam = cc.source_family(rec.get("source", "?"))
                rank = _rank(rec)
                item = (-rank, serial, rec)
                serial += 1
                heap = buckets[fam]
                if len(heap) < per_family:
                    heapq.heappush(heap, item)
                elif rank < -heap[0][0]:
                    heapq.heapreplace(heap, item)

                meta = rec.get("meta", {}) or {}
                if meta.get("image_uncanny_description"):
                    frames_fh.write(json.dumps({
                        "contest": meta.get("contest"),
                        "expectation": meta.get("image_description", ""),
                        "violation": meta.get("image_uncanny_description", ""),
                        "caption": rec["text"],
                        "record_kind": meta.get("record_kind", "finalist"),
                        "explanation": meta.get("explanation", ""),
                        "source": rec.get("source", ""),
                        "license": rec.get("license", ""),
                        "licence_class": licence_class,
                    }, ensure_ascii=False, sort_keys=True) + "\n")
                    n_frames += 1
                english = _translation_en(rec)
                language = meta.get("language") or rec.get("language")
                if english and language not in (None, "en"):
                    aligned_fh.write(json.dumps({
                        "text": rec["text"], "language": language,
                        "translation_en": english,
                        "source": rec.get("source", ""),
                        "license": rec.get("license", ""),
                        "licence_class": licence_class,
                    }, ensure_ascii=False, sort_keys=True) + "\n")
                    n_aligned += 1

        census = census_acc.report(len(source_paths))
        total = census["items"]
        selected: dict[str, list[dict[str, Any]]] = {}
        per_fam_counts: dict[str, int] = {}
        for fam in sorted(buckets):
            rows = [item[2] for item in buckets[fam]]
            rows.sort(key=lambda rec: (_rank(rec), _canonical(rec)))
            selected[fam] = rows
            per_fam_counts[fam] = len(rows)

        exported_rows = sum(per_fam_counts.values())
        langs: Counter = Counter()
        lics: Counter = Counter()
        graded = 0
        sample_path = stage / "corpus_sample.jsonl"
        with sample_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"_meta": {
                "name": "humor_genome_wave2_sample",
                "schema_version": 3,
                "rows": exported_rows,
                "sampled_from": total,
                "eligible_from": eligible_rows,
                "method": (f"deterministic sha256-order, capped at {per_family} "
                           "per source family after a deny-first rights gate"),
                "release_policy": "verbatim text only when licence_class=redistributable",
                "licence_note": "per-record; exact licence and attribution still travel",
            }}, ensure_ascii=False, sort_keys=True) + "\n")
            for fam in sorted(selected):
                for rec in selected[fam]:
                    meta = rec.get("meta", {}) or {}
                    language = meta.get("language") or rec.get("language") or "unknown"
                    langs[language] += 1
                    lics[cc.classify_licence(rec.get("license", ""))] += 1
                    if rec.get("funniness_label") is not None:
                        graded += 1
                    lab = st.label_item(rec)
                    row = {"text": rec["text"], "source": rec.get("source", ""),
                           "license": rec.get("license", ""),
                           "licence_class": cc.classify_licence(rec.get("license", "")),
                           "language": language, "form": lab["form"],
                           "domain": lab["domain"], "meta": meta}
                    if rec.get("funniness_label") is not None:
                        row["funniness_label"] = rec["funniness_label"]
                    fh.write(json.dumps(row, ensure_ascii=False,
                                        sort_keys=True) + "\n")

        (stage / "census.json").write_text(
            json.dumps(census, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        summary = {
            "full_corpus_rows": total,
            "eligible_rows": eligible_rows,
            "exported_rows": exported_rows,
            "release_policy": "redistributable_text_only",
            "excluded_by_licence_class": dict(sorted(excluded.items())),
            "per_family_cap": per_family,
            "families": per_fam_counts,
            "languages_in_export": len(langs),
            "top_languages": dict(langs.most_common(30)),
            "licence_classes_in_export": dict(sorted(lics.items())),
            "graded_rows_in_export": graded,
            "expectation_violation_frames": n_frames,
            "aligned_phrase_pairs": n_aligned,
        }
        (stage / "export_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        (stage / "DATA_CARD.md").write_text(_data_card(summary, census), encoding="utf-8")
        metadata = out_dir / "dataset-metadata.json"
        metadata_source = metadata_template or metadata
        if metadata_source.exists():
            (stage / metadata.name).write_bytes(metadata_source.read_bytes())

        manifest: dict[str, dict[str, Any]] = {}
        for path in sorted(stage.iterdir()):
            # Kaggle consumes dataset-metadata.json as an upload descriptor and
            # does not mount it as a dataset file, so putting it in the payload
            # manifest creates a guaranteed false failure for consumers.
            if path.name in ("manifest.json", "dataset-metadata.json") or path.is_dir():
                continue
            manifest[path.name] = {
                "bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

        # Publish payloads first and the manifest last. A hard kill during this
        # short commit window can leave a mixed directory, but never one that
        # passes verification: the old manifest will reject changed payloads.
        # Ordinary exceptions restore the previous files from hard-link/copy
        # backups. This is fail-closed transactional publication, not a false
        # claim that a multi-file directory swap is universally atomic.
        backup = stage / ".previous"
        backup.mkdir()
        publish = sorted((p for p in stage.iterdir()
                          if p.name not in ("manifest.json", ".previous")),
                         key=lambda p: p.name)
        manifest_path = stage / "manifest.json"
        touched = publish + [manifest_path]
        for path in touched:
            dest = out_dir / path.name
            if dest.exists():
                backup_path = backup / path.name
                try:
                    os.link(dest, backup_path)
                except OSError:
                    backup_path.write_bytes(dest.read_bytes())
        installed: list[Path] = []
        try:
            for path in publish:
                dest = out_dir / path.name
                os.replace(path, dest)
                installed.append(dest)
            os.replace(manifest_path, out_dir / "manifest.json")
            installed.append(out_dir / "manifest.json")
        except BaseException:
            for dest in reversed(installed):
                old = backup / dest.name
                if old.exists():
                    os.replace(old, dest)
                else:
                    dest.unlink(missing_ok=True)
            raise
        return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-family", type=int, default=12000)
    ap.add_argument("--corpora-dir", type=Path, default=st.CORPORA,
                    help="directory containing source JSONL files")
    ap.add_argument("--out-dir", type=Path, default=OUT,
                    help="directory to receive the Kaggle payload")
    ap.add_argument("--metadata-template", type=Path,
                    default=DATASET_METADATA_TEMPLATE,
                    help="source-controlled Kaggle dataset metadata JSON")
    a = ap.parse_args()
    source_paths = sorted(a.corpora_dir.glob("*.jsonl"))
    s = build(a.per_family, paths=source_paths, out_dir=a.out_dir,
              metadata_template=a.metadata_template)
    print(json.dumps({k: v for k, v in s.items() if k != "families"},
                     ensure_ascii=False, indent=1))
    print("\nlargest families in export:")
    for k, v in sorted(s["families"].items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {k[:58]:<58} {v:>7,}")
    tot = sum(p.stat().st_size for p in a.out_dir.glob("*") if p.is_file())
    print(f"\nexport size: {tot / 1e6:.1f} MB -> {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
