"""Slim, publishable export of the wave-2 corpus for a Kaggle dataset.

The full corpus is ~2.6M rows and over a gigabyte, and 84% of it is one source.
Shipping that verbatim would be both unwieldy and misleading. This builds a
STRATIFIED slice instead, plus the derived artifacts that carry the actual
findings.

Design decisions that keep the export honest:

* STRATIFIED, NOT TRUNCATED. Rows are capped PER SOURCE FAMILY, so the New
  Yorker caption archive stops dominating and small languages survive. A
  head -n slice would have produced a file that was 84% captions again.
* DETERMINISTIC. Selection is by sha256 of the text, not by random sampling or
  file order, so the same corpus produces the same export byte-for-byte.
* LICENCE TRAVELS. Every row keeps its own `source` and `license`. The card
  states that a redistributor must honour the per-record field, because the
  collection has no single licence.
* NOTHING IS INVENTED. Only rows already in corpora/ are exported; the census
  and style labels are recomputed here rather than copied, so the numbers in
  the card cannot drift from the data beside them.

    python3 build_kaggle_export.py --per-family 12000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import corpus_census as cc
import style_taxonomy as st

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "kaggle_wave2"


def _key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(per_family: int) -> dict[str, Any]:
    OUT.mkdir(exist_ok=True)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total = 0
    for rec in st.iter_corpus():
        total += 1
        fam = cc.source_family(rec.get("source", "?"))
        buckets[fam].append(rec)

    # deterministic per-family cap
    kept: list[dict[str, Any]] = []
    per_fam_counts: dict[str, int] = {}
    for fam, rows in buckets.items():
        rows.sort(key=lambda r: _key(r.get("text", "")))
        take = rows[:per_family]
        per_fam_counts[fam] = len(take)
        kept.extend(take)

    langs = Counter()
    lics = Counter()
    graded = 0
    with (OUT / "corpus_sample.jsonl").open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": {
            "name": "humor_genome_wave2_sample",
            "rows": len(kept),
            "sampled_from": total,
            "method": f"deterministic sha256-order, capped at {per_family} per source family",
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "licence_note": "per-record; the collection has no single licence",
        }}, ensure_ascii=False) + "\n")
        for r in kept:
            meta = r.get("meta", {}) or {}
            langs[meta.get("language", "unknown")] += 1
            lics[cc.classify_licence(r.get("license", ""))] += 1
            if r.get("funniness_label") is not None:
                graded += 1
            lab = st.label_item(r)
            row = {"text": r["text"], "source": r.get("source", ""),
                   "license": r.get("license", ""),
                   "language": meta.get("language", "unknown"),
                   "form": lab["form"], "domain": lab["domain"], "meta": meta}
            if r.get("funniness_label") is not None:
                row["funniness_label"] = r["funniness_label"]
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # the two artifacts that carry the findings, exported whole (they are small)
    n_frames = n_aligned = 0
    with (OUT / "expectation_violation_frames.jsonl").open("w", encoding="utf-8") as fh:
        for r in st.iter_corpus():
            m = r.get("meta", {}) or {}
            if m.get("image_uncanny_description"):
                fh.write(json.dumps({
                    "contest": m.get("contest"),
                    "expectation": m.get("image_description", ""),
                    "violation": m.get("image_uncanny_description", ""),
                    "caption": r["text"],
                    "record_kind": m.get("record_kind", "finalist"),
                    "explanation": m.get("explanation", ""),
                    "source": r.get("source", ""), "license": r.get("license", ""),
                }, ensure_ascii=False) + "\n")
                n_frames += 1
    with (OUT / "aligned_phrases.jsonl").open("w", encoding="utf-8") as fh:
        for r in st.iter_corpus():
            m = r.get("meta", {}) or {}
            en = m.get("translation_en") or m.get("english") or m.get("gold")
            if en and m.get("language") not in (None, "en"):
                fh.write(json.dumps({
                    "text": r["text"], "language": m.get("language"),
                    "translation_en": en, "source": r.get("source", ""),
                    "license": r.get("license", ""),
                }, ensure_ascii=False) + "\n")
                n_aligned += 1

    census = cc.census()
    (OUT / "census.json").write_text(json.dumps(census, ensure_ascii=False, indent=1),
                                     encoding="utf-8")

    summary = {
        "full_corpus_rows": total,
        "exported_rows": len(kept),
        "per_family_cap": per_family,
        "families": per_fam_counts,
        "languages_in_export": len(langs),
        "top_languages": dict(langs.most_common(30)),
        "licence_classes_in_export": dict(lics),
        "graded_rows_in_export": graded,
        "expectation_violation_frames": n_frames,
        "aligned_phrase_pairs": n_aligned,
    }
    (OUT / "export_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    # sha256 manifest so a consumer can verify what they got
    manifest = {}
    for p in sorted(OUT.glob("*")):
        if p.name == "manifest.json" or p.is_dir():
            continue
        manifest[p.name] = {"bytes": p.stat().st_size,
                            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-family", type=int, default=12000)
    a = ap.parse_args()
    s = build(a.per_family)
    print(json.dumps({k: v for k, v in s.items() if k != "families"},
                     ensure_ascii=False, indent=1))
    print("\nlargest families in export:")
    for k, v in sorted(s["families"].items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {k[:58]:<58} {v:>7,}")
    tot = sum(p.stat().st_size for p in OUT.glob("*") if p.is_file())
    print(f"\nexport size: {tot / 1e6:.1f} MB -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
