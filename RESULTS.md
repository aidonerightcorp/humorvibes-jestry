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

## Open (queued)
- ~~Century test with the fixed jest extractor~~ **DONE 2026-07-11 reconciliation: 12 jests, 3
  alive, top R 0.73** (zoo latest). ~~Headline temporal experiment~~ **RAN, did not discriminate**
  (8/8 canonical, gap 0.0) → fix the `temporal.py` gap conditioning, rerun.
- Leak-guard refinement (punchline-exclusive words only); Humicroedit format-gap follow-up
  (setup/punchline-style corpus with human grades); hosted panels/frame-duels when any key lands;
  Gemini add-on click for platform-credit judging.
