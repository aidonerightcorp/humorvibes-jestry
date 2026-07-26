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
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CORPORA = ROOT / "corpora"

# Licence strings are upstream free text, not trusted policy decisions.  Deny
# markers are deliberately evaluated before grants, and grant tokens require
# real token boundaries.  The old substring check classified "permit required"
# as MIT and let "CC BY; do not redistribute" win on the permissive fragment.
_NONCOMMERCIAL = (
    re.compile(r"\bcc\s*[- ]?by\s*[- ]?nc\b", re.I),
    re.compile(r"\bnon[- ]?commercial\b", re.I),
)
_RESEARCH_ONLY = (
    re.compile(r"\bresearch(?:[- ]only|\s+use(?:\s+only)?)\b", re.I),
    re.compile(r"\bdo\s+not\s+redistribute\b", re.I),
    re.compile(r"\b(?:redistribution|publication)\s+(?:is\s+)?(?:not\s+)?permitted\b", re.I),
    re.compile(r"\b(?:permission|permit)\s+(?:is\s+)?required\b", re.I),
    re.compile(r"\bno\s+(?:stated\s+|declared\s+)?licen[cs]e\b", re.I),
    re.compile(r"\blicen[cs]e\s+(?:not\s+declared|unknown|unstated)\b", re.I),
    re.compile(r"\b(?:verify|check)\s+before\s+redistribut", re.I),
    re.compile(r"\bper\s+dataset\s+card\b", re.I),
    re.compile(r"\bunstated\b", re.I),
)
_REDISTRIBUTABLE = (
    re.compile(r"\bpublic\s+domain\b", re.I),
    re.compile(r"\bcc\s*[- ]?0(?:\s*1\.0)?\b|\bcc0\b", re.I),
    re.compile(r"\bcc\s*[- ]?by(?:\s*[- ]?sa)?(?:\s*[- ]?\d(?:\.\d)?)?\b", re.I),
    re.compile(r"\bmit(?:\s+licen[cs]e)?\b", re.I),
    re.compile(r"\bapache(?:\s+licen[cs]e)?(?:\s+version)?\s*2(?:\.0)?\b", re.I),
)


def classify_licence(lic: str) -> str:
    text = " ".join(str(lic or "").split())
    if any(pattern.search(text) for pattern in _NONCOMMERCIAL):
        return "noncommercial"
    if any(pattern.search(text) for pattern in _RESEARCH_ONLY):
        return "research_only"
    if any(pattern.search(text) for pattern in _REDISTRIBUTABLE):
        return "redistributable"
    return "unclassified"


def may_redistribute_text(lic: str) -> bool:
    """Fail-closed release decision for verbatim text.

    This is intentionally narrower than "a licence string exists".  Candidate
    inventory may retain research-only metadata locally; public exports may
    carry text only when the normalized class is explicitly redistributable.
    """
    return classify_licence(lic) == "redistributable"


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


class CensusAccumulator:
    """One-pass census state shared by the CLI and streaming exporters."""

    def __init__(self) -> None:
        self.sources: Counter = Counter()
        self.families: Counter = Counter()
        self.licences: Counter = Counter()
        self.lic_class: Counter = Counter()
        self.langs: Counter = Counter()
        self.kinds: Counter = Counter()
        self.styles: Counter = Counter()
        self.n = 0
        self.graded = 0

    def add(self, rec: dict[str, Any]) -> None:
        if "_meta" in rec or not rec.get("text"):
            return
        self.n += 1
        meta = rec.get("meta", {}) or {}
        src = rec.get("source", "?")
        self.sources[src] += 1
        self.families[source_family(src)] += 1
        licence = rec.get("license", "?")
        self.licences[licence] += 1
        self.lic_class[classify_licence(licence)] += 1
        # top-level `language` is the flattened/export schema; `meta` is the
        # raw corpus one. Both must be read or exports read blank.
        self.langs[meta.get("language") or rec.get("language") or "unknown"] += 1
        if meta.get("record_kind"):
            self.kinds[meta["record_kind"]] += 1
        if meta.get("style"):
            self.styles[str(meta["style"])] += 1
        if rec.get("funniness_label") is not None:
            self.graded += 1

    def report(self, files: int = 0) -> dict[str, Any]:
        top_share = (self.families.most_common(1)[0][1] / self.n) if self.n else 0.0
        return {"files": files, "items": self.n, "graded": self.graded,
                "graded_share": round(self.graded / self.n, 4) if self.n else 0.0,
                "distinct_sources": len(self.sources),
                "distinct_families": len(self.families),
                "distinct_licences": len(self.licences),
                "distinct_languages": len(self.langs),
                "top_source": self.families.most_common(1)[0] if self.families else None,
                "top_source_share": round(top_share, 4),
                "families": dict(self.families.most_common(25)),
                "licence_classes": dict(self.lic_class),
                "sources": dict(self.sources.most_common(40)),
                "languages": dict(self.langs.most_common(60)),
                "record_kinds": dict(self.kinds),
                "declared_styles": dict(self.styles.most_common(30))}


def census(paths: list[Path] | None = None) -> dict[str, Any]:
    """Census over `paths`, defaulting to every JSONL in corpora/.

    Callers must be able to restrict the file set: the published export ships
    derived sidecars (annotated frames, aligned phrase pairs) alongside the
    corpus, and globbing the whole directory folds those into the row count
    with a different schema.
    """
    acc = CensusAccumulator()
    files = 0
    for p in sorted(paths if paths is not None else CORPORA.glob("*.jsonl")):
        files += 1
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                acc.add(r)
    return acc.report(files)


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
