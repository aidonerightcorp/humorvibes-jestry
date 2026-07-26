"""Census of everything in corpora/: sources, licences, languages, grades.

Written because the corpus crossed the point where nobody can eyeball it. Three
things this reports that a naive `wc -l` cannot, and that matter for publishing:

* LICENCE COVERAGE, per record. The collection has no single licence — it spans
  CC BY 4.0, CC BY-SA, CC BY-NC (noncommercial), MIT, public domain, and several
  sources with NO stated licence at all. The redistributable share is reported
  separately from the research-only share, because those are different rights.
* GRADED SHARE. How many items carry a human funniness signal rather than being
  bare text. This is the number that decides what experiments are possible.
* CONCENTRATION. When one source contributes the majority of rows, corpus-wide
  averages describe that source, not humor. The top-source share is printed so
  that stays visible.

    python3 corpus_census.py
    python3 corpus_census.py --json jestry_out/corpus_census.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CORPORA = ROOT / "corpora"

# Licence strings are free text per record; these substrings classify them.
REDISTRIBUTABLE = ("cc by 4.0", "cc by 3.0", "cc by 2.0", "cc by-sa", "mit",
                   "public domain", "apache", "cc0")
NONCOMMERCIAL = ("cc by-nc", "-nc ", "noncommercial", "non-commercial")
RESEARCH_ONLY = ("research use", "do not redistribute", "no stated licence",
                 "no license", "per dataset card", "unstated")


def classify_licence(lic: str) -> str:
    low = lic.lower()
    if any(k in low for k in NONCOMMERCIAL):
        return "noncommercial"
    if any(k in low for k in REDISTRIBUTABLE):
        return "redistributable"
    if any(k in low for k in RESEARCH_ONLY):
        return "research_only"
    return "unclassified"


def source_family(src: str) -> str:
    """Collapse per-item source strings into the collection they came from.

    Without this the census lies by dilution: the caption archive writes one
    source string PER CONTEST, so 385 sibling sources each look like ~0.5% of
    the corpus while together they are the overwhelming majority. Concentration
    has to be measured on the family, not the label.
    """
    if src.startswith("nextml/caption-contest-data"):
        return "nextml/caption-contest-data (all contests)"
    if src.startswith("New Yorker caption contest"):
        return "New Yorker caption contest (annotation layers)"
    if src.startswith("taivop/joke-dataset"):
        return "taivop/joke-dataset (all dumps)"
    for prefix in (".wikiquote:", ".wiktionary:"):
        if prefix in src:
            lang, _, rest = src.partition(prefix)
            return f"{prefix.strip('.:')} ({lang})"
    if src.startswith("hf:"):
        return src
    if src.startswith("gutenberg:"):
        return "gutenberg (public-domain jest books)"
    return src


def census(paths: list[Path] | None = None) -> dict[str, Any]:
    """Census over `paths`, defaulting to every JSONL in corpora/.

    Callers must be able to restrict the file set: the published export ships
    derived sidecars (annotated frames, aligned phrase pairs) alongside the
    corpus, and globbing the whole directory folds those into the row count
    with a different schema.
    """
    sources: Counter = Counter()
    families: Counter = Counter()
    licences: Counter = Counter()
    lic_class: Counter = Counter()
    langs: Counter = Counter()
    kinds: Counter = Counter()
    styles: Counter = Counter()
    n = graded = 0
    files = 0
    for p in sorted(paths if paths is not None else CORPORA.glob("*.jsonl")):
        files += 1
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "_meta" in r or not r.get("text"):
                    continue
                n += 1
                meta = r.get("meta", {}) or {}
                src = r.get("source", "?")
                sources[src] += 1
                families[source_family(src)] += 1
                lic = r.get("license", "?")
                licences[lic] += 1
                lic_class[classify_licence(lic)] += 1
                # top-level `language` is the flattened/export schema; `meta` is
                # the raw corpus one. Both must be read or exports read blank.
                langs[meta.get("language") or r.get("language") or "unknown"] += 1
                if meta.get("record_kind"):
                    kinds[meta["record_kind"]] += 1
                if meta.get("style"):
                    styles[str(meta["style"])] += 1
                if r.get("funniness_label") is not None:
                    graded += 1
    top_share = (families.most_common(1)[0][1] / n) if n else 0.0
    return {"files": files, "items": n, "graded": graded,
            "graded_share": round(graded / n, 4) if n else 0.0,
            "distinct_sources": len(sources), "distinct_families": len(families),
            "distinct_licences": len(licences),
            "distinct_languages": len(langs),
            "top_source": families.most_common(1)[0] if families else None,
            "top_source_share": round(top_share, 4),
            "families": dict(families.most_common(25)),
            "licence_classes": dict(lic_class),
            "sources": dict(sources.most_common(40)),
            "languages": dict(langs.most_common(60)),
            "record_kinds": dict(kinds), "declared_styles": dict(styles.most_common(30))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    c = census()
    print(f"files {c['files']}   items {c['items']:,}   sources {c['distinct_sources']}   "
          f"languages {c['distinct_languages']}   licences {c['distinct_licences']}")
    print(f"graded (human funniness signal): {c['graded']:,} = {c['graded_share']:.1%}")
    ts, tn = c["top_source"]
    print(f"largest source FAMILY: {ts} = {tn:,} rows = {c['top_source_share']:.1%} of the corpus")
    if c["top_source_share"] > 0.4:
        print("  ^ over 40%: corpus-wide averages describe THIS SOURCE, not humor in general.")
        print("    Stratify by source family before quoting any corpus-wide statistic.")
    print("\nsource families:")
    for k, v in list(c["families"].items())[:12]:
        print(f"  {k[:62]:<62} {v:>9,}  {v / c['items']:>6.1%}")
    print("\nlicence classes:")
    for k, v in sorted(c["licence_classes"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:<18} {v:>9,}  {v / c['items']:>6.1%}")
    print("\ntop sources:")
    for k, v in list(c["sources"].items())[:18]:
        print(f"  {k[:62]:<62} {v:>9,}")
    print("\nlanguages (top 20):")
    for k, v in list(c["languages"].items())[:20]:
        print(f"  {k:<10} {v:>9,}")
    if c["record_kinds"]:
        print("\nrecord kinds:")
        for k, v in sorted(c["record_kinds"].items(), key=lambda kv: -kv[1]):
            print(f"  {k:<24} {v:>9,}")
    if c["declared_styles"]:
        print("\ndeclared styles (from the source, not inferred):")
        for k, v in list(c["declared_styles"].items())[:18]:
            print(f"  {k:<24} {v:>9,}")
    if a.json:
        out = ROOT / a.json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
