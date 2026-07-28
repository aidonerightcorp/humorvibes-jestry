# Comedy data: scraping engines, gathering, and datasets

*Status: source-landscape notes from the July 2026 build. Inventory numbers are superseded by
SOURCE_SWEEP_2026-07-26.md; the validation promised in §5 below has since RUN — see the executed
result note in that section.*

What HumorVibes already gathers, the full landscape of comedy datasets, and — the real prize —
the **labeled** ones that let us *validate* the measured genome against human laughter.

## 1. What we already have (built + working)

**Ingestion engine** (`ingest.py`, `mesh_cli.py ingest --source ...`), provenance-first, each record
carries source + license:
- **wikiquote** — CC BY-SA canonical quotes (verified: 40 Twain quotes). Grows the historical-remix canon.
- **gutenberg** — public-domain jest books (1916/1922) for the century test.
- **rss** — live topical headlines (BBC tech/science) for the headline→joke pipeline.
- **transcript** — .vtt/.srt/.txt parser (your OWN sets) → callback mining.
- **imgflip** — meme template metadata via public API (verified: 40 templates).
- **hf** — keyless HF datasets-server REST rows (repo/config must be verified live).
- **reddit** — r/jokes public JSON (research use only; Reddit rate-limits/blocks bots).

Plus the **datacenter registry** (`humor_datacenter/sources.py`, `DATA_SOURCES.md`): a scanned matrix
of ~25 research corpora with modality/access notes, and the Corpus Lab notebook that live-fetches
icanhazdadjoke + JokeAPI and measures the whole corpus onto the laugh region.

## 2. Live joke APIs (keyless, safe, already partly wired)

- **icanhazdadjoke.com** (JSON), **JokeAPI v2** (jokeapi.dev), **Official Joke API**,
  **Chuck Norris / dad-joke / pun APIs**. Good for volume + freshness; NO funniness labels.

## 3. Research datasets — THE VALIDATION GOLDMINE (funniness labels)

The point of a *measurement* project is to check the measurements against real human ratings. These
carry funniness labels, so we can correlate our `laugh_score` (and each of S/R/E/B) against them —
the ultimate falsification test for the whole theory:

| Dataset | Signal / label | Why it matters here |
|---|---|---|
| **rJokes** (Reddit jokes + upvotes) | upvote score = funniness proxy, ~500k | large, labeled; regress laugh_score on log-upvotes |
| **HaHackathon / SemEval-2021 Task 7** | mean humor grade (0–5) + controversy | gold human ratings; the canonical humor-rating benchmark |
| **Humicroedit / FunLines** | funniness of a one-word headline edit (0–3) | isolates the SURPRISE/edit mechanism — direct S/R test |
| **Jester** | 1.7M continuous joke ratings, 150 jokes | dense per-joke rating distribution |
| **New Yorker Caption Contest** | pairwise caption preferences (nyc-caption) | pairwise = our tournament format; captions + image |
| **ColBERT / "200k short jokes" (humor detection)** | binary funny/not | large binary classifier data |
| **Short-Jokes (231k)** | unlabeled volume | generation seed / retrieval bank |
| **Pun of the Day, SemEval-2017 Task 7 (puns)** | pun location + type | validates the residual-surprise pun finding |

**Multimodal (for the video/live tracks):**
- **UR-FUNNY** — multimodal humor (TED-style; text+audio+video, laughter-labeled).
- **MUStARD / MUStARD++** — sarcasm detection with video + laugh-track labels.
- **StandUp4AI, TIC-TALK, ManzaiSet** — stand-up / comedic performance corpora (timing, audience).
- **HumorDB** — image humor.

**Cross-lingual/cultural (for the portability/vibe axes):** Chumor (Chinese), Spanish humor corpus,
POPQUORN (demographic-conditioned ratings — directly feeds persona-relative B), SARC (sarcasm).

## 4. Scraping / gathering — with honest licensing lines

- **OK to gather + measure** (don't redistribute raw): Reddit r/jokes (API terms), Twitter/X threads,
  YouTube auto-captions of *your own* or CC-licensed sets.
- **OK to redistribute**: Wikiquote (CC BY-SA, attribute), Project Gutenberg (public domain), the
  research datasets under their cards (most are research-use; cite).
- **Do NOT scrape**: performers' special transcripts, paywalled material, anything for a derivative
  performance. Comedians' bits are IP; the project's clip work uses licensed corpora or original
  material rendered via ClipPlan.

## 5. The high-value next build (validation)

`validate_against_ratings.py` (executed): load a labeled set (HaHackathon or rJokes), measure each
item's genome on the Kaggle instrument, and report **correlation(laugh_score, human_rating)** plus
per-signal correlations (does R track funniness? does the residual-surprise recalibration improve
the fit?). That turns "we measured it" into "our measurement predicts human laughter at r = X" — the
single strongest sentence the writeup could contain.

This validation has since run, twice, and the honest result is the project's controlling negative:
the combined S/R/E/B ablation court against human preference measured Spearman ρ = 0.033 (95% CI
[−0.126, 0.207]; RESULTS.md, jestry_out receipts), and a laugh-score correlation pass read Pearson
+0.108 / Spearman +0.115. The measurement predicts human ratings at close to chance on that arena —
which is why every downstream document treats S/R/E/B as instruments, not as funniness.
