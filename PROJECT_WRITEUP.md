# Humor Genome Wave 2: measuring humor structure without pretending to measure funniness

## Summary

Humor Genome Wave 2 is an open, reproducible study of a narrow question: can a predictive language
model expose useful structure in the way a joke sets and breaks an expectation? Gemma 2 is used as
an instrument, not an oracle. The project reads continuation surprisal from model logits, keeps
that measurement separate from human response, and tests it alongside a large provenance-aware
corpus and a held-out human-label study.

The controlling results are mostly negative. In the form experiment, every joke-form confidence
interval overlaps the proverb control. In the caption experiment, deterministic text features
recover a median within-contest Spearman correlation of 0.1555, or 37.8% of a separately measured
text-only bound. Those results are more useful than a leaderboard-style ranking: they identify
where the current measurements do not separate, how much of humor response is contextual, and
which next experiments can actually change the answer.

The complete study runs in the public
[Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study).
Its rights-filtered data are in the public
[Kaggle dataset](https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2), and all source,
tests, provenance logic, and receipts are in the public
[GitHub repository](https://github.com/aidonerightcorp/humorvibes-jestry).

## The research question

The project began with a predictive-processing account of humor: a setup makes one continuation
cheap to predict, while a punchline forces a surprising but economical reinterpretation. The
implementation separates four proposed dimensions:

- surprise (`S`): continuation negative log likelihood under the setup;
- resolution (`R`): how much an explicit alternate frame reduces that surprise, net of a null;
- efficiency (`E`): resolution per frame token;
- bad surprise (`B`): an audience-relative constraint, not a funniness score.

Only the first dimension controls the Wave 2 form experiment. That boundary matters. Higher `S`
means “less predictable to this checkpoint under this split,” not “funnier.” Resolution and safety
proxies introduce their own model and annotation assumptions, so the release does not collapse
them into one universal humor number.

“The brain is a surprise-reduction engine” is the motivating shorthand, not a biological result
of this project. Predictive coding, the free-energy principle, information-theoretic surprisal,
token negative log-likelihood, human comprehension, amusement, and laughter occupy different
levels of explanation. [`docs/RESEARCH_FOUNDATIONS.md`](docs/RESEARCH_FOUNDATIONS.md) defines those
terms, traces the primary literature, and maps each link in the theory to current evidence and
missing tests.

## Building a corpus that can support honest questions

The full local inventory contains 3,164,600 rows in 217 source families with 62 language labels.
It combines jokes, captions, proverbs, idioms, riddles, wordplay, aligned phrases, and controls.
About 81.8% of rows carry a source-specific human signal, but these signals range from votes and
ratings to labels and platform scores. They remain typed by source rather than being normalized
into a fictional global grade.

A naive random release would be misleading: one New Yorker caption archive is 71.0% of the full
inventory. The public builder therefore uses a deterministic SHA-256 ordering, caps each source
family at 12,000 rows, and fails closed on redistribution rights. Only rows explicitly classified
as redistributable can appear verbatim. Research-only, noncommercial, conflicting, and
unclassified material stays represented in the census but out of the text payload.

The resulting public slice contains 121,670 rows across 166 source families and 59 language
labels. It also publishes 7,913 non-English/English aligned phrase pairs and 2,581 independently
annotated expectation/violation frames. Six payload hashes, row counts, family caps, licence
classes, pair invariants, frame provenance, and cross-file summaries are verified before the
notebook measures anything.

This is a reproducible research release, not a universal benchmark. The sample is intentionally
stratified, and its coverage reflects the licences and public sources that could be verified.

## A separate controlled corpus for the causal question

The observational corpus cannot answer the cleanest mechanism question because it rarely contains
matched alternative endings for the same premise. Humor Genome Open Controls therefore adds a
separate, project-controlled dataset rather than inventing rows inside Wave 2. Its 120,000 English
records cross 300 premise families, 50 configurations, four counterfactual arms, and two surface
variants. The arms hold a premise fixed while presenting an expected literal continuation,
unresolved surprise, compact lexical repair, or the same repair explained explicitly.

The release is deterministic and CC0 to the extent contributors hold the relevant rights. It has
strict schemas, premise/template-isolated splits, retrieval qrels, a surface-artifact adversary,
exact and 12-word overlap screening against 3.16 million readable corpus records, and independent
manifest verification. It contains zero human-authored and zero human-rated rows. Its labels say
how the generator was constructed, not what an audience experienced.

This makes Open Controls useful for application fixtures, grouped evaluation, embedding bakeoffs,
and preparing a preregistered study. The next evidentiary step is to randomize and blind the arms,
then collect expectedness, surprise, resolution, funniness, familiarity, comprehensibility, and
offensiveness separately from consenting people. See
[`docs/OPEN_CONTROLS.md`](docs/OPEN_CONTROLS.md) for the full contract and release procedure.

## Gemma as a measured instrument

The canonical notebook attaches `google/gemma-2/transformers/gemma-2-2b-it/2` and computes
teacher-forced token losses. Before the study, a pinned reference joke is measured at `S = 3.188`
over 10 continuation tokens, agreeing with the stored 3.19 reference. This check catches changes
in tokenization, split, checkpoint, loss mask, or averaging convention before they can silently
move the downstream statistic.

The form study then samples eight items from each of ten structural joke forms plus a proverb
control. Selection is deterministic. Bootstrap intervals are reported for each arm. The largest
mean is `what_do_you_call` at 6.680 and the proverb mean is 3.652, but the uncertainty controls
the conclusion: every form interval overlaps the control interval, and no form interval lies
strictly above the control's upper bound. The notebook therefore prints:

> SEPARATION IS NOT ESTABLISHED

The ordering is a candidate hypothesis for a larger, pre-registered run. It is not evidence that
one form is funnier or even reliably more surprising than another in the target population.

## Human labels, context, and the text-only bound

The strongest human-signal source is a caption-contest archive with raw vote counts. It makes two
checks possible that a single mean rating cannot.

First, split-half and analytic estimators measure the reliability of the label itself. Across
2,052,842 usable captions in 360 contests, the estimated Spearman ceiling is 0.8262. A perfect
model cannot correlate at 1.0 with a noisy finite-vote observation.

Second, 2,173 identical caption texts appeared under more than one drawing. Their cross-context
rank correlation is 0.1689, while a same-context split-half arm reaches 0.6913 and a shuffled
placebo reaches 0.0111. Under the stated variance model, this implies an approximate text-only
Spearman bound of `sqrt(0.1689) = 0.4110`. The bound applies to systems that see only caption text;
it is not a ceiling on a multimodal model that sees the cartoon.

Against that target, a deterministic 30-feature structural text model is evaluated with whole
contests held out. On 215,465 captions across 360 unseen-contest groups, its median
within-contest Spearman correlation is 0.1555. That is 37.8% of the measured text-only bound and
18.8% of the label ceiling. The model is weak, but the protocol is informative: contest identity
does not leak into test folds, and the score is stated against both observable noise and missing
context.

## Corrections that changed the story

Several attractive conclusions failed during audit:

1. A fabricated reference text initially made a correct instrument look broken. Replacing it with
   the actual pinned text restored the 3.19 calibration.
2. Bare form means appeared to put all ten joke arms above the proverb control. Bootstrap
   intervals showed that 0 of 10 separated. The uncertainty-based verdict replaced the ranking.
3. A `shaggy_dog` label appeared to dominate military, religious, and medical humor. That label
   was assigned by length alone and mostly detected long Reddit posts. It was removed from
   domain-by-form claims.
4. An eight-character content floor deleted most four-character Chinese idioms. A script-aware
   floor preserved real chengyu while retaining a minimum-content check.
5. Lexical form rules misclassified “your mother” mentions and limerick-like openings. Structural
   tests replaced the broad triggers before the form run.

These are not footnotes. They show why provenance, controls, uncertainty, and adversarial samples
belong in the executable artifact rather than in an after-the-fact disclaimer.

## What the release contributes

The project contributes an inspectable research workflow more than a single winning metric:

- a large, typed corpus inventory without treating all labels as the same target;
- a deterministic and rights-aware public export instead of an opaque sample;
- a model measurement with a pinned calibration case;
- a confidence-interval result that keeps the non-separation visible;
- a contest-held-out human-label baseline stated against reliability and context bounds;
- executable checks linking the GitHub source, Kaggle data, and Kaggle notebook;
- a ledger of negative results and corrected confounds.
- a separate 120,000-row CC0 counterfactual-control corpus whose synthetic origin cannot be
  mistaken for human evidence.

## Limitations and next experiments

Form coverage remains strongly English-biased. Domain labels are keyword guesses. The form study
has only eight items per arm. The caption result concerns one platform and misses the drawings.
The text-only bound rests on repeated generic captions and a stated additive variance argument.
The safety and resolution dimensions still need stronger human annotation and audience-specific
validation.

For the writer-facing product, the most valuable next experiment is a preregistered within-writer
crossover with paired premises and held-out, consenting audiences. The repository now supplies the
strict protocol, privacy-minimized schemas, synthetic fixture, writer-clustered analysis, and claim
gate in [`docs/REAL_WORLD_STUDY_WORKBENCH.md`](docs/REAL_WORLD_STUDY_WORKBENCH.md). It supplies no
human observations, and its deliberately positive synthetic fixture remains non-claim-ready.

For the caption research, the most valuable next experiment is multimodal: give a model the caption and drawing, hold out
whole contests, and test whether it moves beyond the text-only result without leaking contest
identity. Other high-priority work includes reliability-weighted training, human-authored frame
annotations, native-form taxonomies for under-covered languages, larger pre-registered form
samples, and a second calibrated model family.

The prioritized work is in [`ROADMAP.md`](ROADMAP.md). Reproducible extension instructions are in
[`docs/EXPANSION_GUIDE.md`](docs/EXPANSION_GUIDE.md), and the contribution contract is in
[`CONTRIBUTING.md`](CONTRIBUTING.md).
