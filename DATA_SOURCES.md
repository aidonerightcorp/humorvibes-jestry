# Humor Datacenter Sources

HumorVibes now treats humor data as a datacenter, not a single dataset. Each source is mapped to the signal it can
provide: structure, audience reaction, preference, timing, ranking, culture, or risk.

## Integration Rule

Bad-surprise proxies such as offense, confusion, low appropriateness, or low laughter are useful signals, but they are
not the controlling definition. The evaluator still uses the canonical bad-surprise definition in `humor_mesh.py`.

## What the datacenter now exports (2026-07-24)

The ingested supply is no longer only an internal index. `comedy_primitives_dataset.py` writes `dataset_out/`: the
comedy mechanisms and format specs as structured primitives, every indexed item with its own source, license and
language, the Gemma-labeled frame subset, rows carrying real teacher-forced S/R/E, and both embedding channels as
aligned float32 matrices, with a dataset card and a manifest of sha256 digests. Licensing stays per record rather than
per collection, so a redistributor must honour each item's own field; the card spells out which lanes require checking
upstream terms first. Gate G13 in `verify_jestry.py` reloads the export on every verification run and fails if row
counts, license coverage, or matrix alignment drift.

## High-Priority Sources

| Source | Best signal | Integration use |
| --- | --- | --- |
| SemEval-2020 Humicroedit | `0-3` funniness and pairwise headline ranking | Surprise/resolution and ranking calibration |
| FunLines | edited headline jokes and human feedback | Rewrite and generation examples |
| SemEval-2021 HaHackathon | humor plus offense ratings | Humor/offense separation and risk proxies |
| Jester | user-by-joke ratings matrix | Audience/preference embeddings |
| Humor in Word Embeddings | word-level humor ratings and preference vectors | Lexical humor texture and demographic preference directions |
| UR-FUNNY | text/audio/video humor labels | Delivery and multimodal timing |
| Open Mic / StandUp4AI / TIC-TALK | laughter timing and standup segments | Audience reaction, pauses, timing, performance dynamics |
| ManzaiSet | viewer facial/audio responses and viewer clusters | Audience probing and response heterogeneity |
| When to Laugh and How Hard? | laugh-duration intensity labels | Live response intensity calibration |
| Political robot jokes | political topic acceptability and humor style | Cross-ideology topic/style separation |
| Political parody/satire studies | parody, satire, counter-attitudinal exposure | Cross-ideology portability and risk |
| HumorRank | pairwise/tournament ranking method | Bradley-Terry style candidate ranking |
| G-Eval / LLM-as-judge | rubric scoring and judge bias | Multi-model humor scoring and convergence |
| Multi-agent cultural alignment | model diversity and cultural disagreement | Model jury disagreement probes |
| New Yorker cartoon caption preferences | large-scale human caption ratings | Pairwise/ranking benchmark for multimodal humor |
| HumorPlanSearch | strategy planning, KG-style reuse, novelty filtering | Concrete generation strategy search |
| Morality Frames in Political Tweets | moral frame, target entity, ideology | Dominant-model and political wording probes |
| Moral Foundations Questionnaire / MFQ-2 | audience moral-frame survey dimensions | Optional audience probes for high-sensitivity topics |
| Popularity feedback in cultural markets | cumulative advantage and reduced diversity | Market saturation and gap detection |
| Taste persistence / cultural identity | preference lock-in after environment shift | Style-shift flop risk |
| Uniqueness and popularity in music | novelty dimensions and popularity | Familiarity/novelty tradeoff for comedic repositioning |

## Additional Useful Sources From The Scan

- HumorDB: visual humor with pairwise and scalar funniness labels; useful for a future multimodal Gemma demo.
- Harm or Humor: multimodal harmful-humor benchmark; useful for risk probes, but content handling must be deliberate.
- Cards Against LLMs: candidate-slate choices comparing model and human humor preferences; useful for alignment and
  ranking methodology if licensing permits.
- Chumor / CFunSet: Chinese humor and explanations; useful for cross-cultural humor tests.
- SARC: Reddit sarcasm with user, topic, and conversation context; useful for context modeling, not direct humor scoring.
- MUStARD / MUStARD++: multimodal sarcasm, emotion, valence, and dialogue context; useful for delivery and mismatch.
- Crowd-annotated Spanish humor corpus: humor value/funniness scores from many annotators; useful for subjectivity.
- POPQUORN: demographic-sensitive annotation data for offensiveness, politeness, and rewriting; not humor-specific, but
  useful for audience and annotator modeling.
- Political robot joke work: useful for separating humor style from political-topic acceptability.
- New Yorker cartoon-caption preference data: useful for ranking methods, human-vs-model comparison, and multimodal
  caption humor.
- HumorPlanSearch: useful as a design pattern for strategy search, retrieval of prior high-performing strategies,
  novelty filtering, multi-persona feedback, pairwise win rates, and iterative revision.
- Morality Frames in Political Tweets: useful for mapping target entity, ideology, polarity, and moral frame before a
  political joke accidentally activates a dominant moral model.
- Moral Foundations Questionnaire / MFQ-2: useful only as voluntary audience-probe structure, not as a complete model of
  political identity.
- Political parody detection: useful for recognizing satire, sarcasm, and parody mechanics in political text.
- Cross-partisan YouTube discussion data: useful for modeling when cross-ideology replies become higher-risk.
- Political metaphor/framing work: useful for choosing wording that does not accidentally import a partisan frame.
- Reverse-Engineering Satire: useful for finding which semantic edits make satire funny or serious.

## Local Implementation

The current repo implementation is intentionally dependency-light:

- `humor_datacenter/studies.py`: study-branch taxonomy spanning theory, audience, timing, culture, safety, politics,
  multimodal delivery, generation, and ranking.
- `humor_datacenter/probes.py`: audience probe question bank.
- `humor_datacenter/mechanisms.py`: concrete comedy mechanisms and rewrite operations.
- `humor_datacenter/acquisition.py`: source acquisition plans, expected schemas, local raw-data paths, and license gates.
- `humor_datacenter/market.py`: comedian style vectors, market-gap scoring, and style-shift flop-risk estimates.
- `humor_datacenter/model_jury.py`: multi-model judging schema, per-dimension convergence, and escalation logic.
- `humor_datacenter/experiment.py`: JSONL audience attempt logging and mechanism-level lesson summaries.
- `humor_datacenter/ranking.py`: pairwise candidate judgments and Elo/Bradley-Terry-style tournament aggregation.
- `humor_datacenter/strategy.py`: concrete experiment plans and mechanism recommendations from priors plus logs.
- `humor_datacenter/portability.py`: label-swap, target, moral-frame, shared-frustration, and bad-surprise portability
  checks.
- `humor_datacenter/sources.py`: curated registry and source ranking.
- `humor_datacenter/audience.py`: audience probes, live-response scoring, and adaptation directives.
- `humor_datacenter/schema.py`: records for humor items, reactions, and audience profiles.
- `humor_datacenter/embedding.py`: deterministic hashed vector channels.
- `humor_datacenter/store.py`: SQLite store with brute-force vector search.
- `humor_datacenter/demo.py`: seeded examples for offline demos.
- `datacenter_cli.py`: source listing, ranking, and demo search commands.

Vector channels:

- `text`: semantic retrieval over the whole item.
- `structure`: setup, punchline, and humor labels.
- `audience`: audience fit, context, and preference terms.
- `reaction`: ratings, laughter, appropriateness, and other response signals.
- `risk`: bad-surprise notes and proxy risk signals.

## Audience Probe Loop

The live loop is:

```text
probe audience -> infer audience state -> generate/score joke -> collect response -> adapt next wording
```

Probe signals:

- intent: bond, sharpen, defuse, teach, roast
- acceptable targets
- dominant internal models that should not be contradicted
- topic familiarity
- edge tolerance
- abstraction tolerance
- insider-context level
- political diversity
- political topic sensitivity
- cross-ideology bridge goal
- concise versus roomy wording preference
- avoid-target constraints
- dominant internal models likely to shape interpretation

Response signals:

- laughter duration
- applause level
- groan level
- confusion level
- silence duration
- visible smile level

Adaptation outputs:

- semantic directives: what kind of target, premise, and expectation shift to use next
- wording directives: concrete versus abstract language, setup length, syntax simplicity
- delivery directives: pause, tag, pivot, slow setup, or shorten punchline
- next-joke constraints: lower risk, stronger twist, clearer premise, or adjacent tag

## Cross-Ideology Humor Probe

A political joke should be evaluated for portability, not only average funniness.

Recommended checks:

- **Label-swap test:** does the joke still work if partisan labels are swapped, or is the entire mechanism in-group
  hostility?
- **Target test:** is the target a voter identity, a politician, a process failure, a shared institution, or a human
  foible?
- **Moral-frame test:** does the punchline require one side to accept the other side's moral hierarchy?
- **Shared-frustration test:** can both sides map the joke onto something they already find absurd?
- **Bad-surprise test:** does the surprise collide with a dominant political identity or moral model strongly enough to
  override the joke's local logic?

For bridge goals, prefer jokes about shared procedural absurdity, bureaucracy, status games, technology failure, media
incentives, or symmetrical hypocrisy. Avoid requiring the audience to laugh at its own core identity unless the user
explicitly asks for partisan satire.

## Study Branches

The datacenter now separates sources from study branches. Sources are datasets, papers, or benchmarks. Branches are
research questions the app should reason over.

- Comedic structure and incongruity resolution.
- Bad surprise and boundary modeling.
- Audience preference and humor embeddings.
- Live response, timing, and delivery.
- Humor styles and social function.
- Political and ideological portability.
- Culture, language, and local context.
- Multimodal, visual, and performance humor.
- Sarcasm, irony, and parody.
- Cognitive and neural humor processing.
- Generation, repair, and unfun editing.
- Ranking, evaluation, and leaderboards.
- Coping, health, workplace, and education.

These branches are injected into Gemma context through `datacenter_context(...)`, so the model receives both nearby
examples and the relevant study lenses for the current prompt.

## Comedy Mechanisms

The app now separates high-level study branches from concrete rewrite mechanisms:

- Script opposition.
- False analogy.
- Wordplay / pun.
- Misdirection / reversal.
- Rule of three / AAB.
- Callback / tag.
- Specificity / concreteness.
- Hyperbole / understatement.
- Anthropomorphism.
- Status inversion.
- Shared frustration.
- Self-deprecation.
- Irony / sarcasm.
- Bathos / anti-joke.

Each mechanism has:

- when to use it
- concrete rewrite moves
- risk notes
- study hooks
- ranking keywords

The point is to make Gemma's repairs operational. Instead of "make this funnier," the system can say "use shared
frustration, replace abstract nouns with concrete objects, avoid sarcasm for this mixed audience, then test a callback
only if the prior laugh landed."

## Experiment Loop

Audience response should accumulate into lessons:

```text
joke candidate -> mechanism labels -> mesh score -> live response -> reward -> mechanism summary
```

Use the CLI:

```bash
python3 datacenter_cli.py log-attempt \
  --path /tmp/punchline_mesh_attempts.jsonl \
  --prompt "AI project managers" \
  --audience "NYC tech meetup" \
  --candidate "The AI project manager optimized the sprint by scheduling a meeting about meetings." \
  --mechanisms "anthropomorphism,shared_frustration,misdirection_reversal" \
  --mesh-total 6.4 \
  --laughter-seconds 3 \
  --applause 3 \
  --smile 5

python3 datacenter_cli.py summarize-log --path /tmp/punchline_mesh_attempts.jsonl
```

This is the hook for later contextual-bandit behavior: explore mechanisms early, then exploit the mechanisms that
score well for the current audience while continuing to test alternatives.

## Pairwise Ranking Loop

Scalar mesh scores are useful, but humor often needs direct comparison:

```text
candidate slate -> pairwise judgments -> tournament aggregation -> winner plus disagreement notes
```

Use the CLI:

```bash
python3 datacenter_cli.py demo-tournament
python3 datacenter_cli.py pairwise-prompt --audience-context "NYC tech meetup, smart not mean, low tolerance for broad status threats"
```

The current implementation uses an Elo-style update that is compatible with the HumorRank/Bradley-Terry direction. It is
deliberately simple enough to run offline during the demo.

## Study Planner

Use the planner when a request mentions audience probing, politics, ranking, live response, or bad surprise:

```bash
python3 datacenter_cli.py plan-experiments \
  "political joke for a mixed liberal conservative audience" \
  --preferences "bridge, not partisan"

python3 datacenter_cli.py recommend-mechanisms \
  "AI project managers for a NYC tech meetup" \
  --audience "NYC tech meetup"

python3 datacenter_cli.py portability-check \
  "Congress found a bipartisan solution: both sides agreed the printer was the real problem." \
  --audience "mixed political audience" \
  --preferences "bridge"
```

The planner turns broad research branches into testable work: cross-ideology A/B variants, live tag/pivot studies,
audience preference probes, bad-surprise near-pairs, pairwise tournaments, model-jury convergence, market-gap searches,
style-shift risk checks, and repair-preserve-engine comparisons.

## Market Analytics

Comedians compete for audience/style spaces, not only topics. The market layer currently uses archetypes until real
licensed transcripts, ticket data, ratings, social clips, and audience survey data are available.

```bash
python3 datacenter_cli.py market-archetypes
python3 datacenter_cli.py market-gaps \
  --audience "tech meetups and corporate teams" \
  --preferences "AI, clean, smart, local"

python3 datacenter_cli.py style-shift-risk \
  --current "clean observational corporate humor" \
  --proposed "political aggressive dark crowdwork" \
  --audience-lock-in 8 \
  --bridge-overlap 2
```

The main style-shift hypothesis is that a change flops when style distance is high, the audience is locked into the old
promise, bridge material is weak, and the new style activates dominant audience models before the comic engine resolves.

## Model Jury Convergence

Use multiple judges when a joke is ambiguous. Average score alone is not enough; convergence by dimension is the useful
signal.

```bash
python3 datacenter_cli.py model-judges
python3 datacenter_cli.py demo-model-convergence
python3 datacenter_cli.py model-jury-prompt \
  --candidate "The AI project manager found the bottleneck: the calendar wanted attention." \
  --audience "NYC tech meetup" \
  --preferences "smart, not mean" \
  --judge-name "Gemma 4"
```

High convergence means the joke is likely robust under the rubric. Low convergence means the app should ask for a human
probe, run pairwise audience tests, or compare model rationales only after independent scoring.

## Acquisition Planner

The acquisition planner converts a prompt into source-specific ingestion steps without bundling third-party data:

```bash
python3 datacenter_cli.py acquisition-plan \
  "moral frame pairwise ranking for cross ideology political humor" \
  --audience "mixed political audience" \
  --preferences "bridge, dominant models"

python3 datacenter_cli.py acquisition-plan \
  "audience laughter timing for standup comedy response" \
  --audience "live showcase" \
  --preferences "timing, delivery"
```

Each target includes an official URL, `data/raw/<source_id>/` landing path, expected schema fields, required action, and
license gate. The point is to keep the hackathon repo runnable while making future data ingestion explicit and safe.

## Acquisition Notes

Do not scrape or bundle copyrighted standup/sitcom transcripts for the hackathon repo. Prefer released benchmark data,
derived metadata, source links, or a documented acquisition script that asks the user to provide licensed files. The
demo store contains only small local examples so the app stays runnable without external data.
