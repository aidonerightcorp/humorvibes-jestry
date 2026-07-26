# HumorVibes - Consolidated measured results (writeup source)

All numbers from verified Kaggle runs (kernels cited). Instrument = gemma-2-2b-it teacher-forced
logprobs unless noted; R is null-controlled after v5.

## 2026-07-12 six-kernel reproducibility audit

An authenticated, read-only Kaggle audit independently re-pulled the source and latest output
of all six pre-existing kernels. All six were COMPLETE and private. After stripping execution
outputs, every code/markdown cell matched the corresponding local notebook exactly; every
research log/JSON mirrored under `research_out/kaggle/` was byte-identical to Kaggle. The audit
also records each attached model source and the API deadline (2026-07-25 04:00 UTC). Receipt:
`research_out/kernel_audit_20260712.json`. This verifies provenance; it does not make the
private notebooks public and does not count as a submission.

## 2026-07-12 v4 S/R/E/B ablation court - COMPLETE, negative result retained

The separate private `humorvibes-ablation-court` completed 200/200 pinned Gemma-2-2B CPU
measurements: 120 deterministic Humicroedit human-rated edits plus 40 complete paired
original/human/shuffled triplets. Source cells matched the local v4 notebook, all output hashes
verified, persona-B and true-logprob coverage were 100%, and no external submission was made.
Full receipt and tables: `research_out/kaggle/humorvibes-ablation-court/ABLATION_REPORT.md`.

- Fixed S/R/E/B score: Pearson r=0.042; Spearman rho=0.033 (p=0.724; 1,000-bootstrap 95% CI
  [-0.126, 0.207]). It did **not** validate as a human-funniness ranker on headline edits.
- Strongest observed single signal: E rho=0.099 (CI [-0.091, 0.291]); R rho=0.088
  (CI [-0.087, 0.271]). Neither interval excludes zero. Only-B was negative, rho=-0.072.
- Drop-one rho: without S 0.014, without R 0.035, without E 0.008, without B 0.053. These are
  small, unstable differences, not component-importance proof.
- Mean full scores: human edit 17.078, original 18.625, shuffled 16.570. Human edits did not beat
  originals (mean difference -1.548; one-sided paired p=0.890) and did not significantly beat
  shuffled edits (+0.507; p=0.171).
- Benign B alone did distinguish human edits from originals (+0.085, p=0.0187) and shuffled edits
  (+0.100, p=0.00216); only the latter survives Bonferroni over ten component/control tests. B
  remains a safety constraint, not a funniness score.
- Runtime: 12,837.39 s (3 h 33 m 57 s), CPU float32, 2.614B parameters, 64.19 s/job. Ten visible
  failures and the four-panel figure are preserved beside the receipt.

The court sharpens the roadmap: current setup/punchline inference is a format mismatch for
single-token headline edits, where shuffled replacements can receive more R/E than genuine edits.
Next validation should use explicit setup/punchline material, test format-aware R/E, and keep B
as a separate constraint rather than forcing all four axes into one fixed scalar.

## 2026-07-11 artifact reconciliation - latest kernel outputs pulled locally

`research_out/kaggle/<slug>/` now holds the latest COMPLETE output + log of every research
kernel (via `kaggle kernels output`). **WRITEUP.md numbers were re-pinned to these artifacts.**

- **Measurement nb (latest, CPU-fallback run)** - log: `research_out/kaggle/humorvibes-measuring-jokes-with-gemma/`.
  Jokes S=3.19/3.58/4.09 (model-guessed frames R=0.00/0.47/0.18 - the 2B is a weak frame-writer,
  consistent with the zoo leaderboard); boring R=0.07; shuffled nonsense raw 2.37 − null 2.67 →
  net 0.00 (the null control kills confabulated resolution in the current run). Compiled pipeline:
  static lint FAIL caught duplicate `{adjective}` slots; 0/3 probes in region → frozen
  `validated: False`; seeded runtime reproduces exactly. Persona B-check: collision 2 (NYC tech
  meetup) vs None (PM offsite). Critic: UDP joke diagnosed "no re-route", repaired.
- **Zoo lab (latest = century-fix rerun)** - `research_out/kaggle/humorvibes-mesh-zoo-lab/research_out/zoo_report.json`.
  Leak-guarded deficits: llama-3.2-3b **0.36** < gemma-2-2b 0.473 = qwen2.5-1.5b 0.473 <
  gemma-3-1b 0.502 (ordering stable, llama still best). Nonsense control 0.0 for ALL four writers;
  gemma-3-1b honest NONE. Cross-instrument invariance PASSED again (identical R ordering
  ai_pm > lion_heart > speed_bumps). **Century test RAN with the fixed jest extractor**: 12 jests
  from the 1916 book, frames by llama-3.2-3b, **3 alive today** (top R 0.73/0.54/0.51) - no longer
  queued.
- **Corpus lab (latest)** - `research_out/kaggle/humorvibes-corpus-lab/research_out/corpus_report.json`.
  n=30; 8 jokes over the naive band (S 5.54–8.92); max R 2.317; remix 3/6 transfers survived
  (CAPITALS/Paris meme 2.32→1.37, shorts 2.32→1.38; be-lion meme 2.01→2.07). Temporal RSS probe:
  8/8 verdicts "canonical" with gap 0.0 even for topical items → **the self-containedness gap
  metric did not discriminate in this run** (conditioning fix queued); honest null.
- **Panel lab (latest)** - `research_out/kaggle/humorvibes-panel-lab/research_out/frame_duel.json`.
  Ground-truth frames R = 0.347 / 0.388 / 1.29 with R_null = 0.0; local 2B honest NONE on
  nonsense. (These are the writeup's "0.35–1.29 net of controls".)
- **Validate-ratings (NEW in ledger - was previously unrecorded)** -
  `research_out/kaggle/humorvibes-validate-ratings/validation_results.json`. First external
  validation vs human funniness grades (Humicroedit SemEval-2020-7, 180 items, grades 0.0–2.6):
  laugh_score pearson +0.108 / spearman +0.115 (best predictor), R spearman +0.101, S ≈ 0.
  **Weak positive - reported honestly.** Working hypothesis: format mismatch (headline edits vs
  setup/punchline). Roadmap item, not hidden.
- **Version-history-only numbers** (no local artifact; live in Kaggle notebook version history,
  visible once kernels are public): nonsense R 1.60→0.34 (measurement v4→v5), speed-bumps R=1.11
  (v4), qwen leaky-frame 2.23 + llama unguarded deficit 0.026 + beat-GT-2/3 (zoo v1), zoo v2
  deficits 0.308/0.366/0.426, corpus v1 census S 7.6–8.7 / R 3.42 / ghoul remix 1.84→2.57.
  WRITEUP.md now cites these only as attributed history, never as current-run numbers.
- **Kernel status (2026-07-11)**: humorvibes-measuring-jokes-with-gemma, -mesh-zoo-lab,
  -corpus-lab, -panel-lab, -validate-ratings, -studio-g2 all COMPLETE and private. Old slugs
  (humor-genome-measuring-jokes-with-gemma, punchline-mesh-panel-lab, punchline-mesh-studio-g2)
  404 after the rename - local kernel-metadata.json ids updated to the live slugs so future
  pushes update the real kernels instead of minting dead ones.

## Gemma 4 local generation hardening (2026-07-11)

- A real local Ollama `gemma4` run requested four one-liners and returned all
  four after the adapter made thinking opt-in (`GEMMA_THINK=0` by default) and
  scaled the visible-token budget with the requested candidate count.
- The structured execution receipt is
  `research_out/gemma4_generation_receipt_20260711.json` (SHA256
  `7e37c84a7695717a26f5379787e3a3f27c8b9b1515bcca9b2c1ed8225354b0b4`).
  It records model, request, prompt/output hashes, four parsed candidates, and
  the distinction between real generation and unmeasured teacher-forced
  logprobs.
- This fixes the earlier truncated two-candidate smoke result. It is an
  operational generation result, **not** evidence that the jokes are funny and
  not a competition submission. Ollama still does not expose the continuation
  logprobs needed for measured S/R/E; those remain honestly unmeasured here.

## The theory's falsifiable tests
- **Jokes vs controls** (measurement nb v4–v6): real jokes separate from the boring control on R
  (0 for boring) and from shuffled nonsense once controls are right.
- **Null control earned twice** (v4→v5): raw frame-collapse over-credited nonsense (R=1.60) because
  the frame-guesser confabulates; decoy-hint null cut it to 0.34. Then the zoo lab (v1) showed a
  confabulated frame can *beat* the generic decoy via lexical overlap with the punchline (qwen:
  net 2.23 on nonsense) → **leaky-frame guard** added (overlap-discounted R). Instruments need
  adversarial controls, twice over.
- **Ground-truth frames measure large**: R = 0.35 (speed bumps), 0.39 (lion heart), **1.29**
  (ai_pm) net of null (panel-lab, twice reproduced).

## Historical cross-model results (mesh zoo v1, before the current leak guard)

The numbers in this section are retained as attributed version-history evidence because they
motivated the leak guard. They are not the current guarded leaderboard; see the reconciled latest
zoo result near the top of this file and "Zoo v2" below.

- **Frame-writing leaderboard (explanation deficit vs ground truth; lower better)**:
  llama-3.2-3b **0.026** ≪ gemma-2-2b 0.654 ≈ qwen2.5-1.5b 0.655 ≈ gemma-3-1b 0.675.
  Llama-3.2-3B beat the hand-written ground truth on 2/3 jokes (ai_pm 1.62 vs 1.29) - the frame
  bottleneck is solved with zero API keys.
- **Cross-instrument ordering check: PASSED** - Gemma-2 and Llama-3.2 produce the identical R
  ordering (ai_pm > lion_heart > speed_bumps). This shows the ordering is not unique to one
  model's logits on these three fixed jokes; it is not a population-level invariance result.
- Honest-NONE on nonsense is prompt-sensitive: panel-lab prompt got honest NONE from the 2B; the
  zoo v1 prompt did not → v2 adds an explicit NONE example + the leak guard.

## Corpus census (corpus lab, 30 internet jokes, free APIs)
- **Puns break the naive S band**: top dad jokes measure S = 7.6–8.7 nats with R up to 3.42 -
  a strong frame absorbs excess error → scorer recalibrated to judge the inverted-U on
  **residual surprise (S − R)**.
- Remix (format transfer): metric correctly detected 1 surviving transfer (ghoul → shorts beat,
  R 1.84→2.57) and correctly failed the 2B's other attempts; format-transfer needs the bigger
  writers (now: llama-3.2-3b keylessly).

## Live infrastructure (all reproducible)
- Studio (Streamlit + tunnel from a Kaggle kernel): 3 sessions served; v3 =
  full stack (Vibe + Live Set tabs). URL announced on ntfy topic per session.
- Laughter bandit: synthetic-WAV smoke - burst detector fired (8 bursts, "chuckle"), posterior
  dropped a bombing frame 0.5→0.38 and switched frames on the next pick; JSONL show log.
- Compiled comedy: 4-stage pipeline; lint correctly REJECTED a malformed 2B template (literal
  {slot}); few-shot fix → lint PASS; probes gate honestly (1/3 in region → not validated);
  seeded runtime reproduces exactly.

## Ops findings (documented in kaggle-ops lessons)
- Kaggle P100 (sm_60) is incompatible with the current torch image → every kernel ships a
  CUDA-probe → CPU fallback; T4 works.
- Orphaned kernel slugs: a push that dies mid-create 404s that slug forever; mint new slugs.
- Batch kernels expose no logs mid-run → live URL dead-drop via ntfy.

## Zoo v2 (leak-guarded rerun)
- **Confabulation hole CLOSED**: qwen's nonsense frame drops 2.23 → 0.0 under the overlap guard;
  gemma-3-1b now honestly writes NONE; all four writers score 0.0 on the nonsense control.
- **Ordering stable**: llama-3.2-3b still the best writer (deficit 0.308 vs gemma-2 0.366,
  qwen 0.426, gemma-3-1b 0.502). Note: the guard also taxes legitimate frames that quote the
  joke's own words - v1's llama deficit was 0.026 unguarded. Calibration refinement queued:
  count only punchline-exclusive words as leak (setup words are fair reuse).
- **Cross-instrument invariance: PASSED again** (identical R ordering, both instruments).
- **Century test v2 = parser artifact, not a temporal finding**: the block-splitter sampled the
  book's PREFACE (biographical essays about Twain), not the jest entries - 0/10 "alive" said
  nothing about old jokes. The subsequent fixed extractor skipped front matter and required
  jest-like structure; its current result is 3/12 above R=0.5, top R=0.73.

## 2026-07-24 format-boundary experiment - the predeclared follow-up, executed

Question: the v4 court's rho=0.033 was attributed to headlines defeating setup/punchline
inference. If that is the cause, anchoring the split at the edited word should recover the
correlation. Design: same pinned sample recipe (Humicroedit train.csv, `sample(180,
random_state=0)`, first 84 rows by CPU budget, 83 measured after one degenerate edit position),
three split conditions per item on the certified local instrument, one shared deterministic
leak-safe frame hint across conditions so the split is the only variable. 249 measurements,
zero instrument errors. Receipt: `jestry_out/format_boundary_experiment.json`, per-item audit
trail in `jestry_out/format_boundary_items.jsonl`.

| condition | laugh vs grade | S vs grade | R vs grade | mean R | items with R>0 |
|---|---|---|---|---|---|
| generic (pinned splitter) | -0.025 | 0.112 | -0.047 | 0.050 | 19.3% |
| canonical (edit-anchored) | -0.092 | 0.163 | 0.030 | 0.122 | 31.3% |
| control (fixed 40% cut) | -0.103 | 0.183 | -0.052 | 0.039 | 20.5% |

**Correction, 2026-07-25.** The correlations in this table were recomputed after our own adversarial audit found that the ranking function broke ties by array position, which silently correlates a low-cardinality column with row order. Several values moved and three changed sign (generic R read +0.056 against a true -0.047). The statistic now uses tied-value midranks, verified against scipy. The engagement fractions, the measured S/R/E values, and the conclusion are unaffected: no split condition predicts human funniness, and every correlation remains inside noise. The receipt carries a `correction_2026_07_25` block listing every changed value.

- **Mechanistic positive**: edit-anchoring roughly doubles how often resolution registers at all
  (19.3% to 31.3% of items) and lifts mean R from 0.050 to 0.122. The placebo cut is also a
  different split and does not move it (20.5%), so the lift is specific to the seam.
- **Predictive negative**: no condition predicts human funniness. Every laugh correlation sits
  inside noise, canonical slightly negative. Spearman correlations, permutation p over 2000
  seeded shuffles.
- **Conclusion**: the format boundary is NOT a splitting artifact. Fixing the seam engages the
  mechanism without buying predictive validity, which is a sharper falsification than the
  hypothesis it tested. Open readings: Humicroedit humor may be incongruity without repair, or a
  2B instrument may not resolve it at n=83.
- E is an exact rescaling of R here (the shared hint is always ten words), so their correlations
  are identical by construction, not by coincidence.
- Caveat: this run fixes the frame hint across conditions to isolate the split, while the pinned
  validation run generated a frame per item; the pinned rho=0.115 is context, not a fourth arm.

## 2026-07-24 native-format probe - model-written frames INVERT the ordering

The follow-up the format-boundary result demanded: if headlines are the wrong shape, does the
instrument work where the shape is native? r/Jokes gives title=setup, body=punchline with no
splitter involved. 30 pairs, 60 measurements, 0 instrument errors, content-screened.
Receipt: `jestry_out/native_format_probe.json`, per-item `jestry_out/native_format_items.jsonl`.

- **Arm A (clean, no ratings needed): genuine vs shuffled-punchline separation FAILS and reverses.**
  AUC of R = 0.406. Mean R genuine 0.142 vs shuffled 0.273. R clears zero on 56.7% of genuine
  pairs vs 66.7% of shuffled. Composite laugh score sits at chance (AUC 0.497).
- **Arm B (exploratory, noisy): null**, as expected from a popularity proxy. Spearman vs
  log2(1+upvotes): laugh -0.017, R -0.044, S -0.191.
- **Mechanism, and why this does NOT contradict the certified calibration.** The calibration
  supplies GROUND-TRUTH frames to the reference jokes and no frame to the controls, which is why
  controls measured exactly 0. This probe let the model write a frame for every item, including
  the mismatched ones. Asked to explain a punchline that does not belong to its setup, the model
  confabulates a bridge, and a bridge reconciling two unrelated ideas is more elaborate than the
  obvious frame a real joke needs, so it collapses surprisal harder. The fixed generic decoy null
  cannot absorb a per-item confabulation, and the leak guard only removes frames that quote the
  punchline, not frames that merely reason hard.
- **Worked example** (top shuffled pair): setup "A doctor tells a woman she can no longer touch
  anything alcoholic" + foreign punchline "If you beat your fish, it dies!" + model frame "The
  doctor is implying the woman's hands are too shaky or weak to handle alcohol, and the punchline
  is a literal, unrelated..." measured **R = 1.426**, ten times the mean genuine pair. The frame
  states outright that the punchline is unrelated and still collapses the surprisal.
- **What it establishes**: the frame-provenance trust gate (only curated/traditional sources may
  supply a frame that reaches the acceptance oracle) is empirically necessary, not decorative.
  It previously rested on one crafted-frame probe; it now has a 30-pair population behind it.
  Model-written frames do not merely admit a bad joke occasionally, they invert the ordering.
- Limits: 30 pairs, one subreddit, conservative content screen, so direction is clearer than
  effect size. The certified regime measures with given frames and is unaffected (see the
  quantization section below: Q4 and Q8 both separate 3 jokes / 0 controls).

## 2026-07-24 quantization robustness of the certified instrument

Same five reference cases, same acceptance region, two quantizations of the same public
gemma-2-2b-it GGUF. Receipt: `jestry_out/gemma2_full_nll_quant_check.json`.

- Q4_K_M reproduces the certified calibration receipt with **zero drift** on all five cases.
- Q8_0 (fourfold precision) separates identically: all three jokes in region, both controls out.
- Max |delta S| across quantizations 0.261, max |delta R| 0.006. The pinned speed-bumps number
  moves 3.190 to 3.200, so **S=3.19 is not a quantization artifact**; four instruments now agree
  (pinned Kaggle transformers, in-kernel transformers, llama.cpp Q4, llama.cpp Q8).

## 2026-07-24 silent-NaN honesty bug (found, fixed, receipted)

A resumed download produced a corrupt GGUF (2,834,392,928 bytes vs published 2,784,495,456;
sha256 c6c8c1e8 vs published 2d448a9a). llama.cpp loaded it without error and returned NaN for
every logit, and the NaN reached a receipt that still said `measured: true`. Fixed in
`gemma2_full_nll.py`: non-finite NLLs count as instrument errors and degrade to
`measured: false`. Discipline: verify a GGUF checksum against the published object before
trusting any receipt from it; never resume a partial GGUF with `curl -C -`. Receipt:
`jestry_out/instrument_sweep.jsonl` (latest entry). The certified Q4 calibration is unaffected.

## 2026-07-25 the predictive model, and why its headline number is corpus-bound

**The model.** Humicroedit task-2 had gone unused: each row is one headline with TWO different
one-word edits and TWO grades, so flattening it with task-1 gives **28,414 human-graded rows**
and a set of controlled pairs where the sentence is held constant. A gradient-boosted model over
30 structural features (lengths, syllables, rarity against this project's own corpus, punctuation,
position, lexical echo) reaches:

- **held-out Spearman +0.5075, R^2 +0.243** on 8,525 unseen rows
- **70.7%** accuracy choosing the human-preferred edit on controlled pairs whose BOTH members are
  held out (77.0% on the 1,579 pairs humans separated by >= 0.4), against 50% chance

For scale, the pinned single-signal Humicroedit validation reached spearman 0.115. An earlier
version of the pair test scored all pairs including trained rows and read 0.75; that measured
memorisation and was replaced with the out-of-sample figure above.

**And it does not transfer.** A within-corpus number is the easiest possible test, so the same
model was moved to a different population: 100,000 r/Jokes posts (native setup/punchline jokes,
no substitution, scored by upvotes rather than annotators). Receipt:
`jestry_out/cross_corpus_transfer.json`.

| arm | spearman |
|---|---|
| within Humicroedit (train to test) | +0.5075 |
| **transfer Humicroedit to Reddit** | **-0.0091** |
| within Reddit (train to test) | +0.1631 |
| reverse Reddit to Humicroedit | +0.0907 |

The third arm is what makes the second interpretable: r/Jokes IS learnable at 0.163, so the
transfer failure is distribution shift rather than an impossible target. The asymmetry between
arms 2 and 4 carries its own information: a model trained on the noisier, more varied corpus
learns a little that applies to headlines, while the headline-trained model learns nothing that
applies to native jokes. The Humicroedit-learnable signal is narrow and corpus-shaped.

**How the number must be quoted.** 0.5075 is held-out performance on news headlines with one word
substituted, graded by annotators. It is not a general humor predictor, and it is not quoted here
without that scope.

## 2026-07-25 dead-weight words, and the limit of structural features

From the question "can we detect extra words that ruin a joke": delete each word, re-score, and
the change is that word's contribution (`deadweight.py`). Removing ANY word shortens the punchline
and the model has learned shorter scores higher, so every raw delta is positive; each is therefore
centred on the mean deletion to isolate the word-specific part.

On the demo joke it ranks *slowly* and *getting* as dead weight. **Those two words are the pun.**
Every feature the model sees is structural, so it cannot know that a plain word is holding a
reframe. It correctly top-ranks *honestly* and *just*, so it is a filler detector and is described
as one. Receipt: `jestry_out/deadweight_analysis.json`.

`semantic_load.py` adds the missing axis without a trained model:
`load(word) = cos(setup, punchline) - cos(setup, punchline without word)`. Two things were measured
rather than assumed. Function words had to be excluded, because with them included *and*, *a* and
*the* ranked as the most load-bearing words in the lion/zoo joke: deleting a function word from a
short string perturbs the embedding through grammaticality, not meaning. And the metric measures
TOPICAL tie rather than comic load. It rescues the case the structural model gets wrong (*slowly*
and *zoo* come top), but *ban* ranks last in the lion joke although the line collapses without it,
because *ban* shares no topic with "heart of a lion". Scope shipped in the receipt: use the top
content word as a candidate payoff, not the ranking as a cut list.

## 2026-07-26 wave-2 corpus census, and the one family that matters

The census (`jestry_out/corpus_census.json`, taken 12:08 UTC) reads **2,261,096 items over 486
sources, 172 families, 46 languages and 26 licence strings**, 97.0% carrying a numeric grade. It is
a snapshot: the final nextml harvest file landed a minute later and is not in it, so the corpus is
larger than the census says. Anything quoted from that file should carry the timestamp.

The shape matters more than the size. One family is **84.2%** of the census — the NextML mirror of
the New Yorker caption contest. Measured directly from the harvest files rather than from the
snapshot: **2,186,939 ranked captions over 371 contests**, median 5,631 captions per contest.
Everything below is about that family, because it is the only corpus here that ships **the raw vote
breakdown per item** (not_funny / somewhat_funny / funny) instead of a mean alone. A visible label
error is what turns a prediction score from a number into a judgement.

Licence classes are tracked rather than assumed: 2,168,401 research-only, 59,537 noncommercial,
32,248 redistributable, 910 unclassified. The export's redistribution gate (G13) keys on that
field, so the noncommercial caption bulk cannot leak into a shipped artifact by accident.

## 2026-07-26 two form labels were wrong, found before the study that would have used them

`form_signal_study.py` asks whether joke FORM changes what the certified instrument finds
surprising. Before spending instrument time, the labels it depends on were sampled and read. Two of
the ten target forms were badly wrong:

- **limerick** fired on the opening words alone. `^there (once )?(was|were) an?\b` matched 652
  items, of which a read of a deterministic sample put roughly a quarter in the form. "There was a
  fly in my soup" and "There was a snake in his boot." were being counted as limericks.
- **yo_mama** fired on any mention of a mother. Of 7,177 raw hits, **5,773 were not the genre** —
  overwhelmingly Chuck Norris facts that happen to contain "your mother".

Both are now structural rather than lexical, pinned by the real corpus items that were mislabelled
(selftest 22/22, up from 12 cases that never covered these forms):

- A limerick IS its **AABBA rhyme**, so `_is_limerick()` verifies the scheme instead of the opener:
  five line-units, rhyme keys from each unit's final vowel-cluster, both couplets required, line
  breaks preferred over punctuation as the unit boundary. Count **652 → 8**, all 8 genuine on
  inspection. Recall is now the weak side rather than precision, which is the right trade for a
  study that reports a per-form mean.
- **yo_mama** requires the dialectal spelling ("yo mama") or the escalation frame ("your mother is
  so ..."), with an adverb lookahead so "...as your Mother so nicely asked" no longer qualifies.
  Count **7,177 → 1,486**, 9 of 10 genuine in the sample.

Two details that each cost a real detection, worth keeping: an orthographic rhyme key must
normalise the English /ʌ/ that is spelled with an o, or `front` fails to rhyme with `hunt`; and a
token regex of `[A-Za-z']+` will return a lone apostrophe as a line's rhyme word (`out 'duck!',`),
silently rejecting the item. The pre-fix run of the study was already in flight and was discarded
rather than reported.

## 2026-07-26 the label's own reliability, and the ceiling it puts under every score

Every prediction number in this project has been quoted against an implicit ceiling of 1.0. That
ceiling is wrong. A caption's published funniness is a mean over a finite number of crowd votes, so
it carries sampling error, and no predictor can correlate with a noisy measurement better than a
second independent measurement of the same thing does. Receipt: `jestry_out/caption_ceiling.json`,
gate G14.

Two estimators on deliberately unrelated assumptions:

- **split-half** — deal each caption's own votes into two disjoint halves (multivariate
  hypergeometric), average each, correlate across the captions of one contest, Spearman-Brown back
  to full length. Nothing assumed about the vote distribution.
- **analytic** — the multinomial sampling variance of each caption's mean over the observed
  within-contest variance of means. Different assumptions entirely.

Over **2,052,842 usable captions in 360 contests**, all within contest, because the drawing and the
vote scale change between contests:

| quantity | median | p10 | p90 |
|---|---|---|---|
| reliability, split-half on ranks | 0.683 | 0.561 | 0.782 |
| reliability, split-half on values | 0.794 | 0.712 | 0.850 |
| reliability, analytic | 0.797 | 0.715 | 0.852 |
| **ceiling on Spearman** | **0.826** | 0.749 | 0.884 |

The two estimators first appeared to disagree by 0.109. They do not: the split-half was computed on
ranks and the analytic one is a variance ratio. Comparing like with like, **0.794 vs 0.797 — a gap
of 0.003** between a non-parametric resampling of the actual votes and a closed-form variance
argument. That agreement is the receipt; 0.826 is merely what it implies.

Reliability rises with votes exactly as sampling error must, which is the third check that the
estimator measures what it claims:

| votes per caption | contests | reliability | ceiling |
|---|---|---|---|
| 20–50 | 47 | 0.617 | 0.786 |
| 50–100 | 205 | 0.675 | 0.822 |
| 100–200 | 95 | 0.721 | 0.849 |
| 200+ | 13 | 0.823 | 0.907 |

**Integrity finding, dropped rather than averaged over.** 27,829 captions (1.3%) publish a mean
their own vote counts cannot produce, and 7,061 have a `votes` field disagreeing with the sum of
their counts — count vector and mean column written from different snapshots of a live contest. The
clearest case reads `not_funny=5, votes=5` with a mean of 1.2, which needs six votes. This study
resamples the counts, so such a row is unusable in either direction; 134,097 rows are excluded in
total, including the sub-20-vote tail.

## 2026-07-26 funniness is mostly not in the words — the bound on any text-only model

The theory says a punchline lands by repairing an expectation the setup built, which implies
funniness is not a property of a string. That has never been testable here: no corpus rated the same
joke in two contexts. This one does, by accident. **2,173 caption texts were submitted to more than
one contest** — same words, different drawing, different crowd. Receipt:
`jestry_out/caption_portability.json`, gate G15.

| arm | spearman |
|---|---|
| 1. cross-context — same words, different drawing | **+0.1689** |
| 2. same-context ceiling — split-half of the same captions' own votes | +0.6913 |
| 3. placebo — arm 1 with the partner shuffled | +0.0111 |

Arm 2 is what arm 1 would read if context were irrelevant, computed on exactly the same items, so
the ratio is the honest quantity: **24% of a caption's standing travels with its words**. Arm 3
reads zero, so the pairing and the ranking are not leaking.

**What it bounds.** Write standing = T(text) + C(fit with this drawing) + E(vote noise). With C and
E independent between contests, arm 1 *is* var(T)/var(standing), and a model seeing only the text
can at best predict T, so it correlates with standing at sqrt(arm 1). **Any text-only predictor is
bounded at spearman ≈ 0.411 within contest**, against a label that would support 0.826. That is an
upper bound: a caption submitted to two contests skews generic, which helps it travel.

The items say it better than the statistic. "He still doesn't get it." stood in the 98th percentile
against one drawing and the 1st against another. "Haven't seen him." went 5th → 100th. Same words,
opposite reception.

## 2026-07-26 structural text model: 37.8% of the text-only bound

`caption_model.py` fixes the pooled-contest defect in the earlier caption arm. Its target is each
caption's percentile within its own full contest; sampling happens only after that percentile is
computed. Five-fold `GroupKFold` holds out whole contests, so every test drawing is unseen. The
completed receipt covers **215,465 captions in 360 contests** and 30 deterministic structural text
features. Receipt: `jestry_out/caption_model.json`, gate G16.

| evaluation | Spearman |
|---|---:|
| contest-held-out, median within contest (IQR 0.1173–0.1898) | **0.1555** |
| contest-held-out, captions with at least 100 votes | 0.1038 |
| contest-held-out, pooled | 0.1538 |
| random split sharing contests, pooled | 0.1541 |

The model recovers **37.8% of the 0.411 text-only bound** and **18.8% of the 0.826 label ceiling**;
358/360 contest-level correlations are positive. The pooled held-out and shared-contest scores are
effectively the same, so contest identity did not inflate this model's pooled result. The lower
high-vote result is reported rather than rationalized; less label noise did not improve this arm.

Transfer remains weak and asymmetric:

| train → test | Spearman |
|---|---:|
| caption → Reddit jokes | +0.0959 |
| caption → Humicroedit | +0.0490 |
| Reddit jokes → caption, median within contest | -0.0029 |
| Humicroedit → caption, median within contest | +0.0471 |

This is a human-label prediction result, but it is text-only and sees no cartoon. It does not show
that the features cause humor, and it leaves most of even the portable text signal uncaptured. The
run took 85.9 minutes on a saturated shared host. Because the original process wrote only after
transfer, version 2 now atomically checkpoints `core_complete` before optional transfer work and
records core and end-to-end runtimes separately.

## 2026-07-26 Wave 2 release: completed, stratified, and fail-closed

The final strict scan contains **3,164,600 rows in 117 files, 767 source labels, 217 source
families and 62 language labels**. It carries 2,587,825 source-specific human signals (81.8%). The
published Kaggle slice is SHA-256 ordered, deny-first on redistribution rights, and capped at
12,000 rows per family: **121,670 redistributable rows, 7,913 aligned non-English/English pairs,
and 2,581 expectation/violation frames**. It is drawn from 471,328 licence-eligible rows. The
caption family falls from 71.0% of the full corpus to 2.2% of the public slice; no public source
family exceeds 9.9%. The remaining 2,693,272 rows stay in the local census but their verbatim text
is excluded: 2,580,994 research-only, 59,537 noncommercial, and 52,741 unclassified.

The release builder now scans the corpus once with bounded per-family heaps. It fails on malformed
JSON instead of silently dropping a row, has no clock field, stages every artifact before replacing
the prior release, and hashes every mounted payload. `verify_wave2_release.py` then streams the
release again and checks hashes, JSONL counts, family caps, languages, licence classes, grades,
aligned-pair invariants, frame provenance, and agreement among the sample header, summary, census
and data card. Final receipt: **PASS**, six payloads.

The deterministic-build test produces identical hashes on consecutive schema-3 builds. The domain
audit also found a semantic bug before publication: the keyword patterns had a leading word
boundary but no trailing one, so `car` matched “carpet” and `cat` matched “category.” After adding
the second boundary, exactly the files that should change did change—`corpus_sample.jsonl` and its
manifest—while the census, selection summary, aligned pairs, frame rows and data card stayed
byte-identical. The semantic release gate passed again on the corrected artifact.

The full style relabel now has a machine-readable cross-tab in its header. **80,246 rows (2.5%)**
receive a specific form. The sourcing intervention is visible rather than asserted: Russian is
2.9% specific (4,489 rows), Bulgarian 6.2% (3,454), and Polish 2.9% (433), after the final joke
harvest; proverb-heavy Portuguese, Greek, Amharic, Japanese, Italian, Arabic and Turkish remain at
effectively zero. Generic forms and the length-only `shaggy_dog` proxy are excluded from every
domain×form claim.

## Open (queued)
- ~~Century test with the fixed jest extractor~~ **DONE 2026-07-11 reconciliation: 12 jests, 3
  alive, top R 0.73** (zoo latest). ~~Headline temporal experiment~~ **RAN, did not discriminate**
  (8/8 canonical, gap 0.0) → fix the `temporal.py` gap conditioning, rerun.
- ~~Humicroedit format-gap follow-up~~ **DONE 2026-07-24: edit-anchored canonicalization engages
  the mechanism (R>0 on 19.3% → 31.3% of items) but does not predict funniness; the boundary is
  not a splitting artifact** (see the format-boundary section above). Next in that line: a
  setup/punchline-native rated corpus, since Humicroedit may simply not carry repair-driven humor.
- Leak-guard refinement (punchline-exclusive words only); hosted panels/frame-duels when any key
  lands; Gemini add-on click for platform-credit judging.
- **Re-run the per-feature caption arm of `three_corpus_study.py` within contest.** Its New Yorker
  column pools captions across contests, which is the same confound the model-level correction
  above quantifies; the per-feature signs and FDR survivals inherit it and have not been rechecked.
- **The 705 human expectation/violation frames** in the caption annotation layers are the first
  frames in this project that are neither model-written nor crafted here. The frame-provenance trust
  gate exists precisely because model-written frames invert the ordering — a human-annotated frame
  set is the missing arm of that experiment.
- **Weight training by label reliability.** Every caption's vote count gives its mean a known
  standard error, so rows are not equally informative; the ceiling work above computes the per-row
  variance already and nothing yet uses it.
- **The bound is on TEXT-only models, not on models.** 0.411 falls out of the caption's context
  dependence, so the way past it is to give the model the drawing, not better text features.
