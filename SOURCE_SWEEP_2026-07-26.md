# Source sweep, 2026-07-26

A six-lane sweep for more humor data: datasets, keyless APIs, multilingual phrases and
translations, memes, academic benchmarks, and joke styles. Everything below was checked with a
real request on 2026-07-26, not recalled. Counts come from `datasets-server` size endpoints,
`categoryinfo` calls, or actual line counts.

Two rules govern what got ingested. Provenance travels per record, so every row carries its own
`source` and `license` rather than inheriting a collection-level claim. And a source that could
not be fetched is written down as dead with its status code, because knowing what is gone is
worth as much as knowing what is live.

## What the corpus gained

Before: 23,885 items, 159 sources, 46 languages.

| Batch | New rows | Signal added |
| --- | --- | --- |
| nextml caption archive (385 contests) | 2,186,939 | mean rating **plus the raw 3-bin vote histogram** per caption |
| taivop/joke-dataset (3 dumps) | 198,573 | reddit score; unfiltered, slur-screened on ingest |
| r/Jokes bulk (staged locally, never ingested) | 98,516 | setup/punchline split + score |
| New Yorker captions (staged locally, never ingested) | 59,537 | mean rating + vote count |
| Wiktionary idioms/proverbs/similes | 12,926 | phrases, 5 languages (first pass) |
| Polyglot of Foreign Proverbs (Gutenberg 51090) | 7,913 | **aligned foreign → English pairs**, 7 languages |
| MemeCap | 6,382 | literal reading vs intended reading vs the metaphor between them |
| Chuck Norris API | 5,988 | 16 source-declared categories |
| HaHackathon (SemEval-2021 T7) | 5,583 | graded funniness + **annotator controversy** + offence |
| New Yorker annotation layers | 2,636 | **705 expectation/violation frames**, 647 explained jokes |
| static dumps, meme templates, style APIs | 2,094 | MIT sets, 271 templates with declared slot counts |

## The find that matters most

`jmhessel/caption_contest_corpus` publishes, for 705 contests, three crowd workers each writing
two separate fields:

- `image_description` — what the scene is
- `image_uncanny_description` — what is wrong with it

That is an expectation and its violation, annotated apart from each other, by humans, in a 0.4 MB
zip. A companion file gives 651 captions with a free-text explanation of why they work. Nothing
else in the sweep separates the three parts of a joke this explicitly, so these are stamped as
frame-carrying supply rather than as ordinary text.

## Keyless APIs

78 endpoints answered 200. The ones that changed the corpus:

| Endpoint | Items | Note |
| --- | --- | --- |
| `api.chucknorris.io` | ~5,200 | 16 categories on every item; `explicit` category skipped at source, not filtered afterwards |
| `v2.jokeapi.dev` | 1,368 EN | 6 categories × 6 languages (cs, de, en, es, fr, pt) |
| `icanhazdadjoke.com` | 744 | `Accept: application/json` required; search index makes topic a usable proxy for subject matter |
| `raw.githubusercontent.com/15Dkatz/official_joke_api` | 451 | the whole DB in one request — polling `random_ten` was never necessary |
| `api.memegen.link/templates` | 211 | declares slot count (`lines`) and links 208 of 211 to Know Your Meme |
| `api.imgflip.com/get_memes` | 100 | fixed top-100, no pagination; `captions` is a lifetime popularity count |
| `en.wiktionary.org` category API | 60k+ | per-language categories for 80+ languages on one wiki |

**Dead, with status:** `numbersapi.com` now 301-redirects to an unrelated commercial site — the
trivia service is gone, and any code still calling it is silently parsing a parked page.
`api.quotable.io`, `evilinsult.com`, `api.pushshift.io`, `boredapi.com`, and about twenty smaller
joke APIs return connection failures or placeholders. Reddit's own `.json` endpoints now 403
keyless clients in every user-agent variation tried.

**Moved:** Chronicling America's `chroniclingamerica.loc.gov/search/pages/results/?format=json`
is retired (404); the live path is `www.loc.gov/collections/chronicling-america/?fo=json`, which
reports 1,116,918 hits for `q=joke` — public-domain newspaper humor columns with dates and
geography attached, still unharvested.

## Multilingual and translation-aligned

The corpus was 98.9% English before this lane. What is now ingested or queued:

- **en.wiktionary per-language categories** — Chinese idioms 16,920, Mandarin 14,865, English
  10,599, Polish 4,890, Spanish 3,321, and a long tail down to Amharic and Zulu. One wiki, one
  parser, 80+ languages.
- **Gutenberg 51090, "A Polyglot of Foreign Proverbs" (1869)** — 7,913 proverbs in fr/it/de/es/
  pt/nl/da, each with its English translation on the same line. Public domain.
- **HuggingFace** — `oHenri/chinese_xiehouyu` 14,032 (natively two-part: the riddle sets the
  image, the answer springs it), `psyche/korean_idioms` 16,856, `israel/ProverbEval` 50,552
  across Amharic/Oromo/Tigrinya, `mxronga/yoruba-proverbs-parallel-corpora` 568 parallel,
  `Ehtisham1328/urdu-idioms-with-english-translation` 2,111 parallel,
  `svjack/zh-idiom-in-human-machine-eng` 4,310 with both a human and a machine English gloss,
  `Kalloniatis/Greek-Humor-Dataset` 9,999, `dearprakash/tamil_proverbs` 890.
- **Wikidata** — 2,824 items across 239 languages under proverb/idiom/joke classes, labels **CC0**,
  1,373 items carrying two or more languages. Burmese (419 items) and Egyptian Arabic (196) are
  better served here than by Wikiquote.
- **Wikiquote** — 301 pages of 15+ items across 51 editions, 108,003 list items total, of which 39
  editions are new to this project. Largest: Kannada `ಗಾದೆಗಳು` 4,470, Swedish 3,779, Russian 3,676,
  Finnish 3,158, Dutch 3,127.

### Parser debt, quantified

A `* `-prefixed-line parser silently loses about 10,000 verified Wikiquote items. The specific
failures: numbered `#` lists (lithuanian and arabic pages, ~5,835 items), whole entries wrapped in
`{{Цитат}}` on Bulgarian pages (1,058), index pages whose content lives on A–Z subpages
(Indonesian, 1,376), transcluded page-title proverbs (Norwegian Nynorsk), and raw `<P>`/`<BR>`
HTML on Hindi pages. Each needs its own rule. This is written down rather than fixed because the
fix is cheap and the loss is now measured.

One earlier belief was wrong: Italian `Proverbi italiani` is **not** template-wrapped and yields
2,229 clean lines. The Italian template problem is confined to the dialect and Japanese-proverb
pages, which use `{{Ruby}}` and `{{spiegazione}}`.

## Memes and visual humor

- `schesa/ImgFlip575K_Dataset` — 575,948 memes under 99 templates with per-caption views and
  votes. A fixed frame, a variable slot, and a measure of whether the fill landed. 197 MB of JSON,
  no images. Not yet ingested.
- `Ahren09/MMSoc_Memotion` — 6,992 memes graded on humour, sarcasm, offensive and motivational
  axes simultaneously. Image-heavy at 736 MB; `mteb/MemotionI2TRetrieval` (MIT) is the cheap route
  to the OCR text alone.
- `Anthony3456347095/MET-Meme` — 10,030 with metaphor source domain, target domain, and which
  modality each arrives in.
- `kreimanlab/HumorDB` — 3,545 images rated three ways (binary, 1–10, and pairwise), built from
  minimally-contrastive pairs where a funny image was edited to be unfunny. The GitHub sidecars
  give the ratings without the images in ~1.1 MB.
- xkcd — keyless JSON, 3,275 comics; `alt` text is a second punchline layer and older comics carry
  a full panel `transcript`. `olivierdehaene/xkcd` joins 2,630 of them to their explainxkcd prose.
  **CC BY-NC 2.5**, so noncommercial.

**Not ingested, deliberately.** The Hateful Memes family is governed by a Facebook licence
agreement that forbids redistribution; ungated HuggingFace mirrors exist but re-hosting does not
grant the licence. `nils-herrmann/hateful_memes_fine_grained` (MIT, labels only, no images and no
meme text) is the one clean artifact in that family. MAMI, Memotion 3, and MultiOFF are behind
request forms.

## Sarcasm, irony, and disagreement

- **EPIC** (`CreativeLang/EPIC_Irony`) — 14,172 rows, one per annotator per text: 74 annotators,
  3,000 texts, with annotator demographics and the parent comment. **2,010 of 3,000 texts are
  contested**, so a majority vote would throw away most of the signal. Licence not declared.
- **Ciron** — 8,766 Weibo posts with a graded 1–5 irony rating and an explicit "insufficient
  evidence" class.
- **iSarcasmEval third-party annotations** — 3,000 items carrying the author's intended label
  *and* how many of five annotators perceived it. Intended versus perceived, side by side.
- **Ling & Klinger** — 81,408 tweets, 4-class (figurative/irony/sarcasm/regular), **CC0**.
- **Misra Sarcasm Headlines** — 28,619, **CC BY 4.0**.

**SARC is gone.** All three Princeton paths 404, and Wayback archived the directory listings but
never the `.bz2` payloads. The Kaggle mirror `danofer/sarcasm` is the only verified route to the
labeled 1,010,826-row balanced split. The HuggingFace mirror `CreativeLang/SARC_Sarcasm` is the
raw comment dump and **has no label column** — easy to mistake for the task data.

## Joke styles

The corpus had no style axis, so `style_taxonomy.py` was written to add two independent labels:
FORM (structural template) and DOMAIN (subject matter). Self-test 14/14.

Over 187,423 items at the time of labelling, the specific forms found were q_and_a 31,087,
what_do_you_call 5,900, walks_into_bar 1,684, whats_the_difference 1,437, yo_mama 742,
knock_knock 561, light_bulb 512, limerick 162, how_many_x 155, doctor_doctor 76, wellerism 42,
xiehouyu 7, tom_swifty 1.

Two limits are worth stating plainly. Only **6.0%** of items receive a *specific* form; the rest
fall into catch-all buckets (one_liner, setup_punchline, q_and_a, dialogue) that describe shape
rather than mechanism. And **non-English specific-form coverage is approximately zero** — the
templates are English in practice, so a Swedish proverb reads as "labelled" while telling us
nothing. Coverage is therefore reported twice, and the specific-form column is the honest one.

Domains are thin exactly where a comedy writer would want them: military 0.5%, legal 0.5%,
science 0.6%, tech 0.7%, against animal 6.4% and family 5.7%.

## Licensing reality

Of 2.26M items at census time: 95.9% research-only, 2.6% noncommercial, 1.4% redistributable.
The corpus is a research instrument, not a redistributable dataset, and the per-record `license`
field is what a redistributor must honour. The clean lanes are Wikidata labels (CC0), Ling &
Klinger (CC0), Misra headlines (CC BY 4.0), the caption-contest annotation layers (CC BY 4.0),
Gutenberg (public domain), Wiktionary and Wikiquote (CC BY-SA 4.0), Chuck Norris (CC BY 3.0), and
anything from `iabufarha` (MIT).

One concentration fact governs every corpus-wide statistic: the caption archive is **84%** of all
rows. Any average taken over the whole corpus describes New Yorker captions. Stratify by source
family first.

## Content screening

A conservative slur regex runs before any record reaches the index, and drop counts are printed
per batch. It is not sufficient. The deterministic sample drawn for the form study surfaced
ethnic-stereotype jokes that contain no slurs at all — an accent-based Chinese/German pun, a
Gestapo light-bulb joke. A stereotype-level screen is a separate problem from a slur-level one,
and only the latter exists today.
