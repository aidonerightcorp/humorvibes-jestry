# The surprise-reduction thesis, in order: claims, instruments, evidence

**Role of this document.** This is the reconciliation map for the whole project: the thesis
stated hierarchically, each tenet tied to the instrument that measures it and the receipt that
records what happened. Every row cites the receipt that controls it; this file supersedes no
receipt. Three documents share the conceptual surface and have distinct jobs:

| Document | Job | Register |
| --- | --- | --- |
| [`../THEORY.md`](../THEORY.md) | The **generative model** — the full mesh-language account of why the thesis could be true, and the canonical verbatim bad-surprise definition | Ambitious, hypothesis-space |
| [`RESEARCH_FOUNDATIONS.md`](RESEARCH_FOUNDATIONS.md) | The **scientific grounding and limits** — lineage, citations, the five quantities that must never collapse, the falsifiable test designs | Conservative, epistemic |
| This file | The **hierarchy and scoreboard** — which tenet predicts what, which receipt tested it, and the status today | Neutral, auditable |

When the three appear to disagree, they do not: THEORY.md speaks in *hypotheses*,
RESEARCH_FOUNDATIONS.md speaks in *evidence rules*, and this file records *outcomes*. A claim is
only as strong as its row in the scoreboard below.

---

## Level 0 — the frame (not a claim)

Predictive processing: brains continually predict their inputs and treat prediction error as a
cost — "the brain is a surprise-reduction engine" (an *anti-surprise engine*, in the project's
informal shorthand; both phrases name the same frame). This project uses that sentence as a
**motivating frame from the predictive-processing tradition (Friston's free-energy principle,
surprisal psycholinguistics), not as a proven conclusion** about every brain or every laugh. Nothing below
requires the strong literal reading; everything below survives if it is merely a good working
model of comprehension.

## Level 1 — the thesis (one sentence, two halves)

> A joke is a **controlled prediction error** — a setup that narrows expectation and a punchline
> that violates it — **with a cheap, audience-permitted repair**: an alternate frame under which
> the punchline suddenly makes sense, reachable quickly, and colliding with nothing the audience
> holds above logic.

Both halves are load-bearing. Surprise alone is noise, horror, or confusion; repair alone is
predictability. Comedy is proposed to live only where all conditions hold at once.

## Level 2 — the six tenets

Each tenet states: the claim, its operationalization, and the falsifiable prediction it makes.

**T1 — Setups narrow expectation.**
A setup drives the predictive system down a dominant continuation path.
*Operationalization:* a frozen language model's next-token distribution given the setup.
*Prediction:* punchline surprisal `S = NLL(P | C)` is measurable, stable across instrument
implementations, and higher for real punchlines than for the setup's most-expected continuation.

**T2 — The punchline is a controlled error, and surprise is necessary but nowhere near
sufficient.**
*Operationalization:* `S` alone.
*Prediction:* an inverted-U — too little `S` is boring, too much resolves as nonsense; therefore
raw `S` should NOT rank funniness monotonically.

**T3 — A working punchline carries its own repair.**
There exists a compact alternate frame `F` under which the punchline is retroactively coherent —
the "getting it" re-route.
*Operationalization:* `R = NLL(P | C) − NLL(P | C+F)`, net of a decoy-frame null.
*Prediction:* jokes show `R > 0` under their true frame; shuffled setup/punchline pairs keep `S`
high but kill `R`.

**T4 — The repair must be affordable.**
A frame that takes a paragraph to state is a joke that dies when explained.
*Operationalization:* `E = R / tokens(F)`.
*Prediction:* real jokes get most of their surprisal collapse from a one-line hint.

**T5 — The repair must be permitted.**
If the frame collides with an interpretive commitment strong enough to override logic, the error
resolves as offense, not play. The controlling definition of bad surprise is the **canonical
verbatim block in [`../THEORY.md`](../THEORY.md) §2** — quoted, never paraphrased. `B` is
audience-relative *by construction*.
*Operationalization:* persona-conditioned judgments plus persona shift in measured signals.
*Prediction:* the same joke shows different `B` under different personas; word- and joke-level
funniness should vary by audience where such commitments differ.

**T6 — Context dominates text.**
The same words land differently in different rooms; a text-only instrument sees a minority of
what decides the outcome.
*Operationalization:* cross-context standing of identical texts; label-reliability ceilings.
*Prediction:* text-only predictors have a hard ceiling well below the label's own reliability.

## Level 3 — the instruments (and what each is not)

- `S`, `R`, `E` are read off a **pinned, certified instrument**: gemma-2-2b-it, exact full-vocab
  teacher forcing. Every run re-verifies the pinned case (`speed_bumps`, S = 3.190 over 10
  tokens) before measuring; the calibration receipt is
  [`../jestry_out/gemma2_full_nll_calibration.json`](../jestry_out/gemma2_full_nll_calibration.json)
  (`certified: true`), and the regime is quantization-robust (Q4 vs Q8: pinned 3.190 → 3.200,
  max |ΔS| 0.261 — `instrument_quant_check`).
- `B` is a **persona-conditioned model judgment** under the canonical definition. It is a design
  probe, not a human measurement.
- None of the four is funniness. The five quantities — token surprisal, prediction error,
  resolution, amusement, laughter — are kept separate everywhere
  ([`RESEARCH_FOUNDATIONS.md`](RESEARCH_FOUNDATIONS.md)); the claim ladder is
  API call → offline benchmark → preregistered human study → external replication.

## Level 4 — the scoreboard

Status legend: **instrument-level** = a property of the measurement machinery, receipted;
**within-corpus** = held-out result inside one population; **null** = tested and not found;
**untested** = designed, not run. Human-level support exists for NO row — that gate is the
writer crossover pilot (issue #3).

| Tenet | Prediction tested | Receipt | Outcome |
| --- | --- | --- | --- |
| T1 | S measurable, stable, reproducible | `wave2_publication.json`, `gemma2_full_nll_calibration.json`, `gemma2_full_nll_quant_check.json` | **Confirmed (instrument-level).** The pinned case reads 3.188–3.200 across four instrument implementations and two quantizations — one band around the pinned 3.19, not one identical number |
| T1 | Instrument respects its format boundary | `canonicalize_format` follow-up | **Confirmed (instrument-level).** Explicit setup/punchline only; edit-anchored re-splitting doubles engagement (19.3%→31.3% of items) but does NOT improve funniness prediction — the boundary is real, not a splitting artifact |
| T2 | Raw S should not rank funniness | form study (Wave 2 notebook, v14 run; carried into v15); ablation court | **Null, as the tenet itself predicts.** 0/10 joke-form CIs sit above the proverb control (all overlap); combined S/R/E/B vs human preference ρ = 0.033, CI [−0.126, 0.207] |
| T2 | Declared style occupies distinct S regimes | `declared_style_study.json` | **Underpowered — separation not established (n=12/group).** Seven community-declared styles (subreddit self-labels, zero annotation cost) vs the same proverb-control recipe on the certified instrument: 0/7 CIs separate in either direction, but the criterion could not have fired at this n (it requires a group CI-low above 5.999; the largest observed is 4.740). A separate any-difference test among the seven styles (control excluded) gives p = 0.45. Token length is an uncontrolled covariate (r ≈ −0.63 across groups). Zero instrument errors; calibration re-verified in-run (S = 3.1899/10) |
| T3 | Jokes resolve under their true frame; controls don't | `gemma2_full_nll_calibration.json` | **Proposed; instrument-level consistency check only** (matching `R`'s status in RESEARCH_FOUNDATIONS.md). The local calibration receipt is `certified: true` — jokes pass the R rule while boring/shuffled controls fail it, and frame provenance is hard-gated after an adversarial crafted-frame probe — but there is no public pinned R measurement, no construct validation, and no human comprehension data |
| T3 (captions) | Trusted HUMAN frames should out-collapse decoys | `human_frames_resolution_study.json` | **Tested negative (well-powered).** With crowd-annotated scene/uncanny frames, the true frame LOSES to seeded decoys (paired R_net −0.107 [−0.184, −0.041], p = 0.004, n = 34, MDE 0.073) and R does not separate top from bottom captions — the format boundary holds even against human frames in the caption domain |
| T4 | A one-line hint carries most of the surprisal collapse (hint-dose curve) | `human_frames_resolution_study.json` | **First measurements, direction inverted from naive reading.** Full frame R ≈ −0.04; half +0.143; 3-word prefix +0.149 — short generic primers collapse most, consistent with priming rather than repair on this format (exploratory arm) |
| T5 (persona shift) | The same joke shows different measured S under different persona preambles | — | **Untested.** Only the judged-collision half of T5 has instrument-level probes |
| T3/T4 | Frames written by an untrusted model can fake R | `gemma4_calibration.json` (certified: false) | **Boundary held.** The gemma-4 forced-NLL readout failed certification and is barred from gating acceptance — an instrument refusing its own upgrade is the thesis's discipline working |
| T5 | Funniness varies by audience at the lexical level | `demographic_norms_study.json` | **Not detectable at these per-word n.** Two crowds agree on which words are funny (ρ = 0.414) but per-word demographic gaps have near-zero reliability (sex 0.058, age ≈ 0), so only 2/4,997 sex and 0/4,997 age gaps survive Welch-t + FDR (Benjamini–Hochberg), and the cross-dataset gap arm has no attainable signal at these reliabilities (attenuation-ceiling-bound; the negative age point is reported, not absorbed). One dimension-level survivor in the declared 12-test family (sexual-connotation words skew younger, ρ = 0.136, q = 0.008). This is an instrument limit, not evidence that differences are absent; joke-level human data still required |
| T6 | Text-only prediction has a hard ceiling | `caption_ceiling.json`, `caption_portability.json`, `caption_model.json` | **Confirmed (within-corpus).** Label ceiling 0.8262; only ~24% of the label-permitted signal (17% of observed standing) travels with the words → text-only bound 0.4110; current text model 0.1555 median within contest (358/360 contests above chance). The gap worth chasing is the drawing |
| T6 | Divisiveness (the shape of disagreement) behaves as a target | `divisiveness_study.json` | **Measured; no free lunch.** Pole-conflict is a real label overall (split-half Spearman–Brown ~0.51 vs ~0.67 for the mean, ≥40-vote sample) but contest-held-out text features predict it no better than the mean: ~17% of its own ceiling vs ~19%. Per-vote-bin cells are outcome-conditioned strata (votes track the mean at ρ ≈ 0.99 within contest) and low-vote bins are not estimable — the overall row is the quotable one. 12,605 integrity-inconsistent rows dropped, never averaged over |
| (discipline) | The sole survivor must hold within contest (pooling confound) | `caption_within_contest_study.json` | **Confirmed clean.** `punch_rarity_max` at 100% of pooled magnitude within contest (median ρ −0.0876 vs −0.0874; 98.1% sign-consistent over 360 contests; q = 0.0016); two weak pooled features flip sign — the confound was real, the invariant survives it |
| T6 (time) | The crowd label stays meaningful as participation changes | `caption_temporal_drift.json` | **Stable.** Votes/caption double (trend ρ +0.358) and vocabulary turns over (+0.15), yet mean rating, funny share, and split-half reliability are flat across ~380 contests — participation drifts, the label does not (exploratory, pre-registered) |
| (discipline) | Structural features that fit one corpus should not be called "humor" | `cross_corpus_transfer.json`, `three_corpus_study.json` | **Null with one survivor.** Within-Humicroedit 0.508 collapses to −0.009 on Reddit; exactly one of 30 features (`punch_rarity_max`, ρ ≈ −0.05…−0.09) survives sign+FDR in all three corpora — and its sign is *negative*: rarer punchline words correlate with slightly *less* funny, consistent with affordability (T4) and against naive "more surprise = funnier" |
| (craft) | Concrete word choice matters | `word_type_study.json`, `word_type_rjokes_replication.json` | **Corpus-local — does NOT transfer.** Within Humicroedit: body-part +0.205, lift 0.114 → 0.230. On r/Jokes (n = 98k): body-part flips to **−0.118** (p = 0.0001, well-powered), category deltas anti-correlate across corpora (ρ ≈ −0.68), and the lift shrinks ~24× (+0.005). The second cross-population collapse, mirroring the structural model's |
| T1–T5 jointly | Assisted writing beats unassisted for real writers | issue #3 protocol (`REAL_WORLD_STUDY_WORKBENCH.md`) | **Untested.** The pilot is fully built and fail-closed; it awaits consented humans. This is the claim gate for every product sentence |

## Level 5 — what the thesis buys, even at today's evidence level

- **Diagnosis, not a score.** The four conditions give a repair taxonomy: predictable (raise S),
  no frame (rebuild the turn), too expensive (compress the frame), collision (replace the frame,
  not the wording). A single "funniness number" is exactly what the scoreboard forbids.
- **Been-done as frame retrieval.** If jokes are frames, precedent search should match on the
  *mechanism*, not the words — the dual-channel (surface + frame) precedent index described in
  [`../README.md`](../README.md) retrieves a Korean proverb for an English paraphrase (0.72) and
  a Yiddish proverb for "Man plans and God laughs" (0.85 surface match).
- **The drawing gap.** T6's receipts say the way past 0.411 on captions is multimodal input, not
  better text features — which is why the multimodal lane (issue #4) is gated on rights-cleared
  images rather than more text modeling.
- **Formats as budgets.** One-liners, memes, and bits are different envelopes for where surprisal
  may accumulate — a scheduling consequence of T4, testable per format.
- **Anti-surprise, read correctly.** The engine's job is to *reduce* surprise; comedy rents the
  machinery by supplying an error the engine can afford to fix. That is why the sole cross-corpus
  invariant is a *negative* rarity coefficient, why explained jokes die (E), and why offense is a
  repair the audience refuses (B) — the thesis predicts its own failure modes, and the receipts
  above show it failing exactly there and nowhere worse.

## Reading order for the public surface

1. [`../README.md`](../README.md) — what this is, in one screen.
2. This file — the thesis, the instruments, and the scoreboard.
3. [`../THEORY.md`](../THEORY.md) — the full generative model (mesh language, vibe, compiled comedy).
4. [`RESEARCH_FOUNDATIONS.md`](RESEARCH_FOUNDATIONS.md) — lineage, citations, evidence rules, test designs.
5. [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) → [`../RESULTS.md`](../RESULTS.md) → `jestry_out/` receipts — current state and every number's source.
6. [`PRODUCT_AND_RESEARCH_USE_CASES.md`](PRODUCT_AND_RESEARCH_USE_CASES.md) → [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — what you may build and claim, and how to contribute.

## Canonical numbers (anti-drift appendix)

Every public document should agree with this list or cite a newer receipt that supersedes it:
pinned S **3.190/10 tokens**; form separation **0/10, not established**; ablation court
**ρ = 0.033 [−0.126, 0.207]**; caption model **0.1555** vs text bound **0.4110** vs label ceiling
**0.8262**, portable share **~24%**, placebo **0.0111**; transfer **0.5075 / −0.0091 / 0.1631 /
0.0907**; sole three-corpus survivor **punch_rarity_max (−0.054/−0.087/−0.066)**; word-type lift
**0.1137 → 0.2296**, body-part **+0.2046 (p = 0.0002)**; demographic norms **ρ = 0.414** agreement,
**2/4,997** and **0/4,997** gaps under Welch-t+FDR (per-word reliability ≈ 0.06/0 — not
detectable, not absent); declared-style **0/7 with an unfirable criterion at n=12
(underpowered), among-styles permutation p = 0.45**; divisiveness reliability **~0.51** vs mean
**~0.67** overall (per-bin cells are outcome strata), both text-predicted at **~17–19% of
ceiling**; within-contest invariant **−0.0876** (confirmed, not a pooling artifact); temporal
trends: participation **+0.358**, label flat; human-frames R_net **−0.107 [−0.184, −0.041]**
(true frame loses to decoys); r/Jokes body-part **−0.118** (sign flip vs +0.205), lift
**+0.005** (~24× smaller). Sources: the receipt named beside each row above.
