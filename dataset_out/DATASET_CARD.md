# Comedy Primitives & Humor Genome Dataset

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
| `mechanisms.jsonl` | 14 | Comedy mechanisms as reusable primitives: when each works, concrete rewrite moves, risk notes, and the humor-theory hooks each one comes from. |
| `formats.jsonl` | 11 | Format specs (one-liner, meme, beat sheet, roast, ...) with length budgets, structural rules, and per-format signal weightings. |
| `items.jsonl` | 23779 | Every indexed supply item: text, source, license, language, and Gemma labels where present. |
| `frames.jsonl` | 270 | The labeled subset: the comic frame in one sentence, mechanisms used, cultural cache, taboo flags. |
| `measured_signals.jsonl` | 309 | Items with real teacher-forced S/R/E from the certified instrument, plus whatever human signal exists for them. |
| `embeddings_surface.npy` | 23779 | float32 [n, 768]. Row i corresponds to the i-th item in `items.jsonl` **whose `has_surface_embedding` is true**, in file order. Filter, then zip. |
| `embeddings_frame.npy` | 270 | float32 [n, 768], row i corresponds to line i of `frames.jsonl`. |

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

- Labels on the frame channel cover 270 of 23779 items. The frame
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
