#!/usr/bin/env python3
"""Export the humor genome as a portable dataset: primitives, items, embeddings.

Everything this project measures already exists somewhere: comedy mechanisms and
format specs as Python dataclasses, 23k+ licensed corpus items inside a
hash-keyed index, 768-dimensional embeddings in a 255MB internal JSON, Gemma
frame labels on a subset, and teacher-forced S/R/E signals scattered across
experiment receipts. None of it was loadable by anyone else. This module emits
it as flat, documented files with a manifest of digests.

Outputs (dataset_out/):
  mechanisms.jsonl        14 comedy mechanisms, every field
  formats.jsonl           11 format specs incl. per-format signal weights
  items.jsonl             every indexed item: text, provenance, license,
                          language, and Gemma labels where present
  frames.jsonl            the labeled subset: comic frame + mechanisms +
                          cultural cache + taboo flags
  measured_signals.jsonl  items with real teacher-forced S/R/E from the
                          certified instrument, harvested from receipts
  embeddings_surface.npy  float32 [n_embedded, 768], aligned to the items.jsonl
                          rows whose has_surface_embedding is true, in order
  embeddings_frame.npy    float32 [n_frames, 768], row i = frames.jsonl line i
  DATASET_CARD.md         schema, provenance, licensing, caveats, rebuild
  manifest.json           sha256 + row counts for every file above

The .npy matrices are large and rebuildable, so they are git-ignored by default
and shipped through the Kaggle dataset; everything else is small and committed.

    python3 comedy_primitives_dataset.py            # full export
    python3 comedy_primitives_dataset.py --no-vectors
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from formats import FORMATS
from humor_datacenter.mechanisms import COMEDY_MECHANISMS

HERE = Path(__file__).resolve().parent
OUT = HERE / "dataset_out"
INDEX = HERE / "jestry_out" / "precedent_index_ollama_embeddinggemma.json"


# Redistribution gate. Roughly half the indexed supply comes from bulk community
# scrapes whose own license line says "verify before redistribution"; publishing
# that text in a public repo would be us redistributing it, not the upstream
# dataset. So the export ships TEXT only for lanes we can point at a clear
# permission for, and for everything else ships the row WITHOUT text: the
# provenance, language, labels and embedding stay, so the dataset is still
# scientifically usable and anyone can re-fetch the text under their own terms.
TEXT_OK = (
    "public domain", "cc by-sa", "cc by 2.0", "traditional",
    "icanhazdadjoke", "official_joke_api", "jokeapi", "template metadata",
    "project-internal", "synthetic",
)


def may_redistribute_text(license_str: str) -> bool:
    lic = (license_str or "").strip().lower()
    if not lic or lic == "unknown":
        return False
    if "verify before redistribution" in lic:
        return False
    return any(tok in lic for tok in TEXT_OK)


# Language labels arrive from many lanes in mixed standards: ISO-639-1, ISO-639-3,
# and free text ("Yiddish", "Latin"). Counting the raw strings overstates coverage,
# which is how "45 languages" got into a writeup when the true figure is 43
# (adversarial audit, 2026-07-25). Normalise once, here, so every downstream count
# is of languages rather than of spellings.
LANG_ALIAS = {
    "eng": "en", "ita": "it", "lat": "la", "Latin": "la", "urd": "ur", "isl": "is",
    "hait": "ht", "Yiddish": "yi", "yid": "yi", "deu": "de", "ger": "de", "fra": "fr",
    "fre": "fr", "spa": "es", "rus": "ru", "jpn": "ja", "kor": "ko", "zho": "zh",
    "chi": "zh", "por": "pt", "nld": "nl", "dut": "nl",
}


def normalise_language(code: str) -> str:
    c = (code or "").strip()
    if c in LANG_ALIAS:
        return LANG_ALIAS[c]
    return c.lower() if len(c) <= 3 else c


def _plain(value):
    """Dataclasses/tuples -> JSON-safe structures, order preserved."""
    if dataclasses.is_dataclass(value):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def write_jsonl(path: Path, rows: list[dict]) -> dict:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"rows": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def collect_measured() -> list[dict]:
    """Real instrument measurements, pulled out of the experiment receipts."""
    rows: list[dict] = []
    fb = HERE / "jestry_out" / "format_boundary_items.jsonl"
    if fb.exists():
        for line in fb.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            rows.append({
                "setup": r["setup"], "punchline": r["punchline"],
                "S": r["S"], "R": r["R"], "E": r["E"], "laugh_score": r["laugh_score"],
                "human_grade": r.get("grade"),
                "grade_scale": "Humicroedit meanGrade 0-3" if r.get("grade") is not None else None,
                "split_condition": r["condition"],
                "instrument": "gemma2-full-nll (gemma-2-2b-it Q4_K_M, full vocab)",
                "source_experiment": "format_boundary_experiment",
            })
    nf = HERE / "jestry_out" / "native_format_items.jsonl"
    if nf.exists():
        for line in nf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            rows.append({
                "setup": r["setup"], "punchline": r["punchline"],
                "S": r["S"], "R": r["R"], "E": r["E"], "laugh_score": r["laugh"],
                "human_grade": r.get("log2_score"),
                "grade_scale": "log2(1+reddit upvotes): popularity proxy, not a rating",
                "pair_kind": r["kind"], "frame": r.get("frame", ""),
                "instrument": "gemma2-full-nll (gemma-2-2b-it Q4_K_M, full vocab)",
                "source_experiment": "native_format_probe",
            })
    return rows


CARD = """# Comedy Primitives & Humor Genome Dataset

Exported from the HumorVibes / Jestry project by `comedy_primitives_dataset.py`.
Every file here is derived from artifacts in this repository, and every number
in the manifest is a sha256 of the file it names.

## What this is

A humor dataset built for *measurement*, not just classification. Alongside the
usual text and labels it carries two things most joke corpora lack: a
**dual-channel embedding** (the surface wording and, separately, the comic
frame that explains the joke), and **teacher-forced signal measurements** taken
off a small Gemma model's own logits rather than asked for in a prompt.

## Files

| file | rows | what it holds |
|---|---|---|
| `mechanisms.jsonl` | {n_mech} | Comedy mechanisms as reusable primitives: when each works, concrete rewrite moves, risk notes, and the humor-theory hooks each one comes from. |
| `formats.jsonl` | {n_fmt} | Format specs (one-liner, meme, beat sheet, roast, ...) with length budgets, structural rules, and per-format signal weightings. |
| `items.jsonl` | {n_items} | Every indexed supply item: text, source, license, language, and Gemma labels where present. |
| `frames.jsonl` | {n_frames} | The labeled subset: the comic frame in one sentence, mechanisms used, cultural cache, taboo flags. |
| `measured_signals.jsonl` | {n_meas} | Items with real teacher-forced S/R/E from the certified instrument, plus whatever human signal exists for them. |
| `embeddings_surface.npy` | {n_vec} | float32 [n, 768]. Row i corresponds to the i-th item in `items.jsonl` **whose `has_surface_embedding` is true**, in file order. Filter, then zip. |
| `embeddings_frame.npy` | {n_fvec} | float32 [n, 768], row i corresponds to line i of `frames.jsonl`. |

```python
import json, numpy as np
items = [json.loads(l) for l in open("items.jsonl", encoding="utf-8")]
emb = np.load("embeddings_surface.npy")
rows = [r for r in items if r["has_surface_embedding"]]
assert len(rows) == emb.shape[0]          # the export refuses to ship a misaligned pair
```

## Schema notes

**Signals** (`measured_signals.jsonl`) come from teacher forcing over the full
vocabulary, not sampling and not self-report:

- `S`: mean negative log likelihood of the punchline given the setup, in nats. Surprise.
- `R`: how far that surprisal collapses once a frame is stated, **net of a decoy-hint null control**. Resolution. A confabulated frame nets to zero by construction.
- `E`: `R` per frame token. Affordability: a joke you must explain for a paragraph is not affordable.
- `laugh_score`: the project's 0-100 composite. Treat it as a diagnostic, not ground truth.

**Cultural cache** (`canonical` / `topical` / `insider`) records which shared
knowledge a joke rents. Canonical items resolve from what a culture durably
knows; topical ones die with the news cycle.

## Provenance and licensing

**Text is withheld where we cannot show a clear right to republish it.** Roughly
half the indexed supply comes from bulk community scrapes whose own license line
reads "verify before redistribution". Publishing that text here would make *us*
the redistributor, so those rows ship with `text: null` and `text_withheld:
true`, keeping their `source`, `license`, `language`, labels and embedding. The
row is still usable for retrieval, clustering and provenance work, and anyone
who accepts the upstream terms can re-fetch the text from the named source. Rows
with `text_withheld: false` carry a license we can point at: public domain,
CC BY-SA with attribution, an explicit public API's terms, or our own output.
The `measured_signals.jsonl` rows keep their setup and punchline text because
they are the experimental record and are unusable without it; their sources are
named per row and the Reddit-derived subset passed a slur, abuse and
identity-topic screen before measurement.

Every item carries its own `source` and `license` string; there is no blanket
license over the whole collection, and you must honour the per-record field.
The mix includes public-domain jest books, traditional proverbs, CC BY-SA
Wikiquote material, public joke APIs, and community-scraped text that passed a
slur and abuse screen. Redistribution terms differ per lane. Items marked
`per dataset card (verify before redistribution)` require you to check the
upstream dataset's terms yourself.

## Honest caveats

- Labels on the frame channel cover {n_frames} of {n_items} items. The frame
  channel is real but sparse; the surface channel is complete.
- `human_grade` is not one scale. Humicroedit rows carry annotator means (0-3);
  Reddit-derived rows carry `log2(1 + upvotes)`, which is a popularity proxy
  confounded by timing and visibility. Do not pool them.
- Measured rows are dominated by experiment sampling, not random selection, so
  they are suitable for method work and unsuitable for population estimates.
- The signals are read off a 2B-parameter model. `RESEARCH_NOTE_INSTRUMENT_BOUNDARIES.md`
  documents where that instrument demonstrably fails, including a headline
  format boundary and a top-K censoring failure. Read it before trusting a
  number.

## Rebuild

```bash
python3 comedy_primitives_dataset.py        # regenerates every file here
```

The `.npy` matrices are large and fully rebuildable from the index, so they are
git-ignored; the JSONL files and this card are committed.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-vectors", action="store_true", help="skip the .npy matrices")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    manifest: dict = {
        "dataset": "comedy-primitives-humor-genome",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "generator": "comedy_primitives_dataset.py",
        "files": {},
    }

    mechanisms = [_plain(m) for m in COMEDY_MECHANISMS]
    formats = [_plain(f) for f in (FORMATS.values() if isinstance(FORMATS, dict) else FORMATS)]
    manifest["files"]["mechanisms.jsonl"] = write_jsonl(OUT / "mechanisms.jsonl", mechanisms)
    manifest["files"]["formats.jsonl"] = write_jsonl(OUT / "formats.jsonl", formats)

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    items_raw = index.get("items", index)
    items: list[dict] = []
    frames: list[dict] = []
    surface_vecs: list[list[float]] = []
    frame_vecs: list[list[float]] = []
    for key in sorted(items_raw):                     # sorted => deterministic export
        it = items_raw[key]
        labels = it.get("labels") or {}
        lic = it.get("license", "unknown")
        shareable = may_redistribute_text(lic)
        row = {
            "item_id": it.get("item_id", key),
            "text": it.get("text", "") if shareable else None,
            "text_withheld": not shareable,
            "source": it.get("source", ""),
            "license": lic,
            "language": normalise_language(labels.get("language") or it.get("language", "en")),
            "has_surface_embedding": bool(it.get("surface")),
            "labeled": bool(labels),
        }
        if labels:
            row.update({
                "frame": labels.get("frame", ""),
                "mechanisms": labels.get("mechanisms", []),
                "cultural_cache": labels.get("cultural_cache", ""),
                "taboo_topics": labels.get("taboo_topics", []),
                "labeler": labels.get("labeler", ""),
            })
            if it.get("frame_vec"):
                frames.append({
                    "item_id": row["item_id"], "text": row["text"],
                    "frame": labels.get("frame", ""),
                    "mechanisms": labels.get("mechanisms", []),
                    "cultural_cache": labels.get("cultural_cache", ""),
                    "taboo_topics": labels.get("taboo_topics", []),
                    "language": row["language"], "license": row["license"],
                    "source": row["source"], "labeler": labels.get("labeler", ""),
                })
                frame_vecs.append(it["frame_vec"])
        items.append(row)
        if it.get("surface"):
            surface_vecs.append(it["surface"])

    manifest["files"]["items.jsonl"] = write_jsonl(OUT / "items.jsonl", items)
    manifest["files"]["frames.jsonl"] = write_jsonl(OUT / "frames.jsonl", frames)
    measured = collect_measured()
    manifest["files"]["measured_signals.jsonl"] = write_jsonl(
        OUT / "measured_signals.jsonl", measured)

    # rows of items.jsonl and embeddings_surface.npy must correspond, so the
    # export refuses to ship a matrix it cannot align rather than shipping a
    # silently offset one
    embedded = [r for r in items if r["has_surface_embedding"]]
    assert len(embedded) == len(surface_vecs), "surface vector/row mismatch"
    assert len(frames) == len(frame_vecs), "frame vector/row mismatch"
    if not args.no_vectors and surface_vecs:
        arr = np.asarray(surface_vecs, dtype=np.float32)
        np.save(OUT / "embeddings_surface.npy", arr)
        manifest["files"]["embeddings_surface.npy"] = {
            "shape": list(arr.shape), "dtype": "float32",
            "aligned_to": "items.jsonl rows where has_surface_embedding is true",
            "sha256": hashlib.sha256((OUT / "embeddings_surface.npy").read_bytes()).hexdigest()}
        if frame_vecs:
            farr = np.asarray(frame_vecs, dtype=np.float32)
            np.save(OUT / "embeddings_frame.npy", farr)
            manifest["files"]["embeddings_frame.npy"] = {
                "shape": list(farr.shape), "dtype": "float32",
                "aligned_to": "frames.jsonl rows",
                "sha256": hashlib.sha256((OUT / "embeddings_frame.npy").read_bytes()).hexdigest()}

    langs: dict[str, int] = {}
    for r in items:
        langs[r["language"]] = langs.get(r["language"], 0) + 1
    licenses: dict[str, int] = {}
    for r in items:
        licenses[r["license"]] = licenses.get(r["license"], 0) + 1
    manifest["summary"] = {
        "items": len(items), "with_surface_embedding": len(embedded),
        "labeled_frames": len(frames), "measured_signal_rows": len(measured),
        "mechanisms": len(mechanisms), "formats": len(formats),
        "languages": len(langs),
        "top_languages": sorted(langs.items(), key=lambda kv: -kv[1])[:10],
        "licenses": sorted(licenses.items(), key=lambda kv: -kv[1])[:12],
        "embedding_backend": index.get("backend", "ollama:embeddinggemma"),
        "embedding_dim": len(surface_vecs[0]) if surface_vecs else None,
    }

    card = CARD.format(
        n_mech=len(mechanisms), n_fmt=len(formats), n_items=len(items),
        n_frames=len(frames), n_meas=len(measured),
        n_vec=len(surface_vecs), n_fvec=len(frame_vecs))
    (OUT / "DATASET_CARD.md").write_text(card, encoding="utf-8")
    manifest["files"]["DATASET_CARD.md"] = {
        "sha256": hashlib.sha256((OUT / "DATASET_CARD.md").read_bytes()).hexdigest()}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest["summary"], indent=2))
    print("\nfiles ->", OUT)
    for name, meta in manifest["files"].items():
        size = (OUT / name).stat().st_size
        print(f"  {name:26s} {size / 1e6:7.2f} MB  {meta.get('rows', meta.get('shape', ''))}")


if __name__ == "__main__":
    main()
