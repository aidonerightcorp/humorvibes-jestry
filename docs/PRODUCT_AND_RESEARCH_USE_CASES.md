# From humor measurements to useful decisions

## The problem

Writers, audiences, researchers, and product teams all ask some version of “does this humor
work?”, but they do not mean the same thing and no single text-only score can answer them.
Funniness depends on the material, delivery, speaker, audience, relationship, timing, room, visual
context, and culture. Most public humor datasets observe only part of that system, and their
labels are not interchangeable.

Humor Genome Wave 2 therefore solves a narrower, useful problem: it makes humor structure,
provenance, model measurements, and uncertainty inspectable enough to support creative search,
reproducible experiments, and better-designed human studies. It does **not** claim to automate
taste or identify a universally funny joke.

## The proposed solution

The project combines four layers without collapsing their evidence boundaries:

1. A provenance-rich multilingual corpus and a rights-filtered public slice.
2. Structural labels and retrieval features for finding relevant forms and precedents.
3. A separate deterministic four-arm control corpus for experiments and application fixtures.
4. Reproducible Gemma measurements of model surprise and frame resolution.
5. An SDK/API for generation, embeddings, similarity, and research signals, with human validation
   explicitly required before a creative or audience claim is accepted.

The practical loop is **retrieve → generate or edit → diagnose → test with people → retain the
result and context**. The human test is the decision gate; model outputs help create and organize
candidates.

The conceptual chain and its scientific sources are documented in
[`RESEARCH_FOUNDATIONS.md`](RESEARCH_FOUNDATIONS.md). The project begins from predictive processing
and incongruity-resolution, proposes a compact repair model, measures only model-specific quantities
where an instrument exists, and requires human outcomes before a usefulness claim.

## Important variables the current text study does not observe

Useful humor conclusions need more than joke text. A real-world study should deliberately capture
or randomize delivery timing and emphasis, performer voice and familiarity, set order and callbacks,
venue and group size, prior exposure, topical age, language/locale, visual or conversational
context, and the audience's explicit relationship to the material. It should also distinguish
private writing utility, rehearsal preference, self-reported funniness, observable laughter,
sharing/recall, and harm or regret; these are different outcomes. Collect only the minimum context
needed for the declared study and only with an explicit data lifecycle.

## What is usable now

| User | Useful now | Do not claim yet | A real success measure |
| --- | --- | --- | --- |
| Comedian or writer | Search structural precedents, request format-constrained variations, compare wording, and keep an audit trail of candidates | The highest model score is the funniest or will work on stage | Less time to a performer-selected draft; blinded audience lift over the writer's baseline; voice preserved |
| Audience member | Explore joke forms, compare interpretations, and set explicit content/style preferences in an app | The system knows a person's taste, identity, or values from demographic proxies | Opt-in satisfaction, preference controls understood, low regret after recommendations |
| Academic | Reproduce the corpus census and notebook, inspect corrections, reuse grouped-split and receipt patterns, and propose preregistered studies | Surprisal is funniness; source labels are one universal human scale; overlapping form intervals establish a ranking | External replication, calibrated uncertainty, effect sizes on held-out people/contexts, data and analysis auditability |
| Educator or student | Rerun a complete model-instrument study and examine null results, confounds, leakage, and licence filtering | A polished notebook proves a theory | Students can trace every conclusion to code and explain why the strongest claims are bounded |
| Data curator or archivist | Inspect source family, language, licence class, public-selection policy, hashes, and concentration | Public metadata grants permission to redistribute every source row | Provenance completeness, licence review coverage, deterministic rebuilds, concentration reported |
| Product or venue team | Integrate the Python SDK or HTTP API; deploy offline with Docker, Compose, Kustomize, or Helm; configure allowlisted LLM and embedding providers | The API is a production audience oracle, a global safety system, or a hosted service | SLOs, cost and latency budgets, abuse controls, consented outcome metrics, rollback-ready releases |

Open Controls adds matched procedural alternatives to each workflow. Writers can compare forms
without receiving a fake winner; academics can preregister arm contrasts; educators can demonstrate
group leakage; and builders can use stable CC0 fixtures. No one may treat the intended arm as an
observed funniness label. The complete contract is in [`OPEN_CONTROLS.md`](OPEN_CONTROLS.md).

## Product workflows worth building and testing

### 1. Writer's-room copilot

**Input:** a premise, intended form, performer voice notes, audience description supplied by the
writer, and optional material the writer owns.

**Workflow:** retrieve nearby forms with `/v1/embed` or `/v1/similarity`; generate bounded
variations with `/v1/humor/generate`; let the writer annotate keep/reject/reason; compare the
selected version with the writer's normal process in a blinded rehearsal.

**Current state:** integration and candidate tooling are available. Quality advantage is not
established. A strict local protocol, synthetic contract fixture, paired analyzer, writer-clustered
bootstrap, and claim gate are now executable; see
[`REAL_WORLD_STUDY_WORKBENCH.md`](REAL_WORLD_STUDY_WORKBENCH.md). The synthetic demo is not evidence
of advantage.

**Test:** randomized within-writer crossover study. Measure minutes to a performer-selected draft,
fraction performed, blind audience response, edit distance from the performer's final wording,
and whether the performer's voice is judged preserved. Analyze by writer, venue, and set rather
than treating every rating as independent.

### 2. Audience-aware rehearsal, not audience profiling

**Input:** audience members' explicit, revocable preferences and optional feedback on material
they actually saw. Do not infer protected traits, ideology, trauma, or moral boundaries from names,
locations, browsing histories, or demographic proxies.

**Workflow:** show alternatives or preference controls; collect consented ratings and “why it did
not work” labels; summarize disagreement for the performer; delete or export a participant's data
on request.

**Current state:** the API can carry operator-supplied audience/preferences text, but the project
does not yet provide consent, identity, retention, or audience-study infrastructure.

**Test:** prospective, opt-in, held-out audience evaluation. Report satisfaction and calibration
by volunteered context, disagreement, opt-out rate, complaint/regret rate, and privacy incidents.
Do not optimize only average laughter at the expense of a harmed minority.

### 3. Academic experiment workbench

**Input:** a preregistered hypothesis, sampling frame, unit of analysis, primary outcome, group
structure, stopping rule, and source snapshot.

**Workflow:** use the public dataset and receipts, define controls, freeze item and model versions,
run grouped or paired analyses, and publish every attempted arm and exclusion.

**Current state:** the reproducible corpus, model instrument, grouped caption baseline, uncertainty
examples, and negative findings are available. The form study is underpowered for separation and
the caption model is text-only.

**Test:** an independent lab reruns the same frozen analysis, then performs an external replication
with new jokes, speakers, audiences, and contexts. Report effect sizes and uncertainty, not just
rankings or thresholded significance.

The Open Controls extension supplies 300 grouped premise families with expected, unresolved,
compact-repair, and over-explained endings plus a strict future-rating schema. It improves stimulus
design but does not populate that schema with fabricated people.

### 4. Humor search and explanation

**Input:** a user-owned joke, topic, form, language, or explanation request.

**Workflow:** embed the query and candidate index with the same model; retrieve precedents with
their licence and provenance; expose why they matched; allow exact-source and language filters.

**Current state:** multiple embedding backends and bounded similarity are available. No semantic
model has yet been benchmarked as the universal default, and similarity is not a novelty detector.

**Test:** frozen multilingual relevance judgments with native speakers, recall@k/nDCG, latency,
cost, licence-filter correctness, duplicate leakage, and failure slices by language and form.

### 5. Multilingual adaptation assistant

**Input:** original material, language pair, locale, intended comic mechanism, and native reviewer.

**Workflow:** retrieve aligned phrases and target-language forms; propose alternatives that preserve
the mechanism rather than literal wording; have native writers label meaning, naturalness,
offense/context, and funniness separately.

**Current state:** the corpus is multilingual and contains aligned pairs, but uneven structural
coverage and machine-derived language metadata limit claims.

**Test:** native-speaker, locale-specific evaluation with literal translation and human adaptation
controls. Measure mechanism preservation, naturalness, funniness, harmful misreadings, and reviewer
agreement per language—never by pooling all languages into one score.

### 6. Reproducibility classroom

**Input:** the canonical public notebook, dataset, immutable source tag, and publication receipt.

**Workflow:** students predict a result, run the notebook, inspect a correction or confound, and
write a claim that matches the evidence status.

**Current state:** available now.

**Test:** a clean account can reproduce the controlling outputs; students can distinguish model
surprisal from human funniness, mean ordering from interval separation, and a length proxy from a
genre label.

## Evidence needed for stronger conclusions

### P0: make the next study decision-valid

- Pre-register the target population, item pool, primary endpoint, smallest worthwhile effect,
  power or precision target, exclusion rules, and stopping rule.
- Collect human outcomes that match the use case: blinded preference and rewrite utility for
  writers; laughter/ratings plus context for audiences; separate frame, surprise, resolution, and
  funniness labels for research.
- Use balanced, larger form samples and report source-held-out sensitivity. The current eight
  items per arm can generate hypotheses but cannot establish the observed ordering.
- Randomize candidate order and condition, preserve rejected outputs, blind raters where possible,
  and account for repeated ratings by joke, writer, audience member, and venue.
- Define a claim gate before running: a product claim is allowed only when its human outcome and
  held-out population pass the preregistered criterion.

### P1: test causes and missing context

- Create within-joke causal edits that alter one proposed mechanism while holding topic, author,
  and wording as stable as possible.
- Add delivery and context: audio timing, speaker identity supplied with consent, room/venue,
  preceding material, and images for caption humor. Compare text-only, context-only, and combined
  arms on identical held-out groups.
- Validate form and adaptation labels with native speakers and report each locale separately.
- Calibrate across at least one second model family and tokenizer using frozen texts and masks;
  model agreement is a robustness check, not human validation.
- Replicate on future material and external communities to expose temporal, source, and platform
  drift.

### P2: qualify a product

- Establish latency, throughput, cost, availability, cancellation, and model-version rollback
  budgets for the chosen provider and embedding model.
- Benchmark retrieval quality before choosing a semantic embedding default; bind every index to
  provider, model, revision, dimensions, normalization, and source snapshot.
- Add explicit consent, retention/deletion, access controls, audit logs that exclude prompts and
  secrets, and a human appeal/override path for audience-facing personalization.
- Threat-model prompt injection, cross-tenant data exposure, denial-of-wallet, abusive generation,
  upstream compromise, and inference of sensitive traits.
- Run an opt-in pilot, publish intended and adverse outcomes, and require a rollback criterion.

## Minimum study schema

Every useful real-world observation should preserve:

- `material_id`, source/author permission, version, language, form, and any paired control;
- `writer_id`, `audience_id`, and `venue_id` as pseudonymous group identifiers, not inferred traits;
- delivery/context version, condition assignment, timestamp window, and model/configuration digest;
- separate outcomes for selection, rating, laughter or behavior, frame resolution, harm/regret,
  and free-text rationale where consented;
- missingness, opt-out, exclusions, evaluator disagreement, and whether the row was exploratory or
  confirmatory.

Raw identity is not required for the analysis and should not enter the research export. Collection
must have a declared consent, retention, deletion, and access policy before any audience pilot.

## Claim gate

| Evidence status | Allowed language |
| --- | --- |
| API or model call succeeded | “The system generated, embedded, or measured this item.” |
| Offline benchmark succeeded | “It performed this way on this frozen benchmark.” |
| Preregistered held-out human study succeeded | “It improved the named outcome for the sampled population and context by the reported amount.” |
| Independent external replication succeeded | “The result replicated across the named populations, sources, models, or contexts.” |

Never shorten those statements to “this is funnier” unless the named human outcome, population,
context, uncertainty, and comparison are present. A null result, a failure slice, or evidence that
an effect does not travel is useful product information.

## A practical next experiment

The highest-value next step is a small, preregistered writer-assistance crossover trial—not a
larger model-only ranking. Recruit multiple writers, have each develop matched premises with and
without the tool, keep both accepted and rejected candidates, and evaluate final versions in
randomized blind rehearsal with new opt-in audience members. The primary endpoint should be chosen
in advance (for example, blind preference or time to a performed draft), with writer, premise, and
audience treated as groups. This directly tests whether the system helps a real person do useful
work while preserving the project's core evidence boundary.
