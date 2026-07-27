# Archived submission paste pack — Humor Genome NYC

> **Archive, not an active checklist.** The deadline passed and no submission is claimed. This
> file preserves the prepared competition copy for provenance. Read [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
> and [`PROJECT_WRITEUP.md`](PROJECT_WRITEUP.md) for the maintained project.

Historical deadline recorded at the time: 2026-07-26 04:00 UTC.

Everything below is copy-paste ready. Order of operations at
https://www.kaggle.com/competitions/humor-genome-nyc → **Writeups tab → New Writeup**.

---

## 1) Writeup body — paste this file's contents verbatim

Paste **`WRITEUP.md`** (1,497 words of prose, under the 1,500 cap; `wc -w` reports
more because it also counts markdown bullet and header markers; every number pinned to
verified kernel artifacts or a receipt in `jestry_out/`; prose de-AI'd with the
humanizer pattern pass on 2026-07-24, zero em dashes, verbatim B definition
byte-identical). Track = **Humor Understanding**.

Optional: if you want the Jestry layer named inside the writeup, replace the
writeup's final sentence ("...`mesh_cli.py {signals|vibe|...}`.") with this one.
Check the word count after doing so; the writeup is already near the cap:

> All code, including Jestry, the charter-governed reuse layer that added a
> certified full-logprob instrument, a 23,779-item been-done index across 43
> languages, and an adversarially-hardened competition pack, is public at
> github.com/aidonerightcorp/humorvibes-jestry.

## 2) Project links — paste each into the Writeup's link fields

```text
https://github.com/aidonerightcorp/humorvibes-jestry
https://www.kaggle.com/code/taylorsamarel/humorvibes-measuring-jokes-with-gemma
https://www.kaggle.com/code/taylorsamarel/humorvibes-jestry-demo-github-wrapper
https://www.kaggle.com/code/taylorsamarel/humorvibes-mesh-zoo-lab
https://www.kaggle.com/code/taylorsamarel/humorvibes-corpus-lab
https://www.kaggle.com/code/taylorsamarel/humorvibes-panel-lab
https://www.kaggle.com/code/taylorsamarel/humorvibes-validate-ratings
https://www.kaggle.com/code/taylorsamarel/humorvibes-ablation-court
No public demo video was published before the deadline.
```

The GitHub repo is ALREADY PUBLIC (repo requirement satisfied — no visibility
flip needed). The wrapper kernel is competition-attached and COMPLETE. Make the
listed research kernels public at submit time (each kernel → Share → Public);
the writeup's numbers are pinned to their existing COMPLETE versions — do NOT
re-run them.

## 3) Live demo line — paste into the writeup/demo section if wanted

```text
Live portal (Cloudflare quick tunnel from a Kaggle kernel; URL rotates per ~8h
session): current session (kernel v8, started 2026-07-24 ~21:55 UTC, alive to
~05:55 UTC, past the deadline)
https://removed-refurbished-seasonal-sorry.trycloudflare.com
Dashboard (receipts-driven charts), Run (route ladder + measured S/R/E/B),
Been done? (46-language precedent index, 12,378 non-English), Charter, Ledger.
This session serves the dataset snapshot taken at its launch: 23,183 registry
cards over a 23,155-item index. Fingerprint before trusting any session:
/api/census must return registry digest cfdb97cfdb654218 (verified matching the
build that kernel mounts). The repo has since grown to a 23,779-item index /
23,824 registry cards, digest a245bf905fdb0d0c, with 270 labeled frames; those
additions ship in the repo and its receipts, and reach the portal on the next
dataset version.
Relaunch anytime: kaggle kernels push -p live_portal/
```

## 4) Images for the writeup (upload from demo_assets/, or hotlink raw GitHub)

```text
demo_assets/jestry_dashboard_20260724.png  : receipts dashboard (funnel, route mix, laugh strip)
demo_assets/jestry_beendone_20260724.png   : cross-lingual been-done: EN paraphrase → KO/JA originals
demo_assets/jestry_charter_20260724.png    : the 18 laws
demo_assets/jestry_registry_20260724.png   : honest registry census
demo_assets/humorvibes_studio_20260712.png : original studio (offline-provider disclosure visible)

raw URLs (render in Kaggle writeups):
https://raw.githubusercontent.com/aidonerightcorp/humorvibes-jestry/main/demo_assets/jestry_dashboard_20260724.png
https://raw.githubusercontent.com/aidonerightcorp/humorvibes-jestry/main/demo_assets/jestry_beendone_20260724.png
https://raw.githubusercontent.com/aidonerightcorp/humorvibes-jestry/main/demo_assets/jestry_charter_20260724.png
https://raw.githubusercontent.com/aidonerightcorp/humorvibes-jestry/main/demo_assets/jestry_registry_20260724.png
```

## 5) Copy-paste result claims (each traces to a receipt in the repo)

```text
- Instrument agreement: speed-bumps joke S=3.19 nats on FOUR independent
  instruments: pinned Kaggle gemma-2-2b run, local llama.cpp full-vocab
  gemma-2-2b (jestry_out/gemma2_full_nll_calibration.json), the in-kernel
  transformers Gemma in the public GitHub wrapper run, and a fourfold-precision
  Q8_0 requant (3.190 → 3.200, max |dS| 0.261 across all five reference cases,
  jokes/controls separate identically): the number is not a quantization
  artifact. jestry_out/gemma2_full_nll_quant_check.json
- Predeclared follow-up, executed and honestly negative: the v4 court blamed
  headline splitting, so we re-split each item at the edited word against the
  old splitter and a placebo cut (n=83, 249 measurements, 0 errors). Anchoring
  the seam DOUBLED how often resolution registered (19.3% → 31.3% of items,
  mean R 0.050 → 0.122; the placebo moved nothing at 20.5%) and still predicted
  funniness no better (all correlations inside noise). The format boundary is
  not a splitting artifact. jestry_out/format_boundary_experiment.json
- Native-format probe, the follow-up's follow-up (30 r/Jokes pairs, title=setup
  body=punchline so NO splitter is involved, 60 measurements, 0 errors): with
  MODEL-WRITTEN frames the instrument does not separate genuine pairs from
  shuffled ones and REVERSES (AUC of R = 0.406; mean R genuine 0.142 vs shuffled
  0.273). Mechanism: asked to explain a punchline that does not belong to its
  setup, the model confabulates an elaborate bridge that collapses surprisal
  harder than a real joke needs, and a fixed generic decoy cannot absorb a
  per-item confabulation. Worked example: "A doctor tells a woman she can no
  longer touch anything alcoholic" + the foreign punchline "If you beat your
  fish, it dies!" + a model frame that literally says the punchline is unrelated
  measured R=1.426, ten times the mean genuine pair. This does NOT contradict the
  certified calibration, which supplies ground-truth frames and still separates
  3 jokes / 0 controls on both quantizations. What it establishes: the
  frame-provenance trust gate (only curated/traditional sources may supply an
  acceptance frame) is empirically necessary, not decorative, and now rests on a
  population instead of one crafted probe. jestry_out/native_format_probe.json
- Honesty bug caught by our own receipts: a corrupt GGUF loaded silently and
  returned NaN for every logit, producing a receipt that still claimed
  measured=true. Non-finite signals now degrade to measured=false in the
  provider. jestry_out/instrument_sweep.jsonl (latest entry)
- Certified instrument: jokes R 0.08/0.12/0.44 vs controls 0.00/0.00 →
  certified=true with an adversarial scope clause (crafted-frame probe R=0.215
  recorded; frame-provenance trust gate enforced in code).
- First accepted outcome: remix route (reuse), laugh 51.8 measured, precedent
  correctly flags surface_match of its own attributed source; frontier
  generation honestly rejected throughout. After an adversarial audit caught a
  vacuous persona gate, the record was corrected by receipt and the outcome
  re-earned at persona_permitted with 4 real judgments.
- Ladder climbed one rung (2026-07-24): the first accept from the
  COMPOSE-RESIDUAL route, where four mechanism cards (anthropomorphism,
  callback_tag, misdirection_reversal, specificity_concreteness) constrain
  generation to the residual twist. Laugh 41.4 measured on the certified
  oracle, acceptance_basis calibrated(2026-07-24T09:59:19), B-gate passed on
  real judgments, one candidate rejected in the same run for "no re-route".
  Unconstrained frontier generation still rejects, so the honest claim is
  narrow: mechanism-card-guided generation can clear the certified bar, free
  generation cannot. The receipt keeps its truth boundary explicit
  (model judgment is not human laughter). jestry_out/receipts.jsonl
- Been-done engine: 23,779 indexed items (jokes, proverbs, anecdotes, quips,
  meme frames), 43 languages (46 raw label values before ISO alias normalisation), 270 Gemma-labeled frames (a citation-template
  parser recovered 640 French and Italian proverbs an earlier lane read as
  zero, and a labeling batch added 40 frames with zero failures);
  EN paraphrase retrieves KO 0.72 / JA 0.70 monkeys-fall originals at full
  23k scale; "Man plans and God laughs." → Yiddish original at 0.849. Frame
  channel (over the labeled sub-index): novel-wording probes with zero
  surface match still rank the cross-lingual family first (Tamil elephant
  0.603 → KO/JA monkeys for "even a grandmaster hangs a queen"): receipted
  in jestry_out/precedent_probes.json, incl. deliberate frame families
  (pit_digger hu/sr/de, wasted_refinement zh/ja/hi, experts_slip ta+ja/ko).
- Redistribution discipline (matters for a public submission): roughly half
  the indexed supply comes from bulk community scrapes whose own license line
  says "verify before redistribution". The published export therefore ships
  those rows WITHOUT text (text: null, text_withheld: true) while keeping
  source, license, language, labels and embedding, so the row stays usable and
  anyone can re-fetch under their own terms. 11,061 rows ship text, 12,718 are
  withheld, and verify gate G13 fails the build if any row ever ships text
  without a redistributable license (0 leaks).
- Exported dataset (comedy_primitives_dataset.py -> dataset_out/): 14 comedy
  mechanisms + 11 format specs as structured primitives, 23,779 licensed items
  in 43 languages, 270 Gemma-labeled frames, 309 rows of real teacher-forced
  S/R/E, and DUAL-CHANNEL 768-dim embeddings (surface wording and comic frame
  embedded separately). Round-trip proven with numpy alone, no project code:
  querying with the Korean "monkeys fall from trees" vector returns the
  Japanese original at 0.892 and the Tamil elephant proverb at 0.627 (same
  comic frame, zero shared surface words). Dataset card documents per-record
  licensing and the caveats (frame channel is sparse; human_grade is two
  different scales and must not be pooled).
- Portal browser-tested for real (headless Chrome over CDP, not curl): all 6
  tabs render, dashboard SVG matches the API card total, census digest agrees,
  been-done returns cross-lingual neighbours, no JS exceptions, no failed
  requests, no phone-viewport overflow. The test found and we fixed: two tabs
  that opened blank, a missing pending state on a ~10s query, and a favicon
  404. jestry_out/browser_test_portal.json
- Honest negatives retained: v4 ablation court rho=0.033 (CI crosses zero) on
  headline edits; gemma4 top-K instrument certification FAILED (receipted);
  gemma4:e2b transport-unusable (EOS-boundary logprob omission, receipted).
- Verification: 13 gates, receipted per run (jestry_out/verify_receipts.jsonl);
  42 offline tests. Gates now include the certified calibration + its
  adversarial scope, the instrument-robustness and executed-follow-up receipts,
  and the exported dataset's row/licence/alignment integrity.
- Competition pack: anti-gaming rebuilt after a constraint-solver exploit hit
  AUC 0.986: punchline-disjoint donor reservoir + templated boring tails +
  self-attack assertions on every build (now 474 items: 203 genuine, 319-item
  test split, 67 distinct boring tails, zero genuine/control overlap).
- Supply growth (all receipted in jestry_out/harvest_receipts.jsonl): 23,064
  records across 129 receipts: content-filtered HF short-jokes bulk (6.4k),
  Russian anekdots (4.3k) and Spanish chistes (2k), full Gutenberg parses
  (Jokes For All Occasions, Toaster's Handbook, Anecdotes & Budget of Fun:
  2.5k anecdotes/stories), per-language wikiquote proverb collections
  (German, Russian, Portuguese, Polish, Swedish, Czech, Romanian,
  Lithuanian, Tunisian Arabic, Hebrew, Bhojpuri, Mazandarani Persian,
  Hungarian, Turkish, Korean, Greek +), 30 wikiquote humorists, keyless joke
  APIs, a stamped-synthetic Gemma-4 lane, and a 152-item curated
  multilingual canon (63 proverbs + classic formats: xiehouyu, Radio
  Yerevan, Beamten, doctor-doctor, oyaji gyagu, Monsieur-et-Madame,
  waiter/viola cycles) with deliberate cross-lingual frame families. Raw
  community-scraped lanes pass a slur/profanity screen before entering the
  public supply.
```

## 6) Final checklist (human, ~20 min total)

1. Video: a finished 1:55.8 narrated 9-beat cut ALREADY EXISTS at
   demo_assets/humorvibes_submission.mp4 (evidence-first 8-beat deck, burned
   captions, music bed; also on raw GitHub). Watch it once; either upload it
   to YouTube as-is (unlisted is fine) and keep the URL, or mute it and
   record your own voice over the captions (SRT beside it is the
   teleprompter), or record fresh per SUBMISSION_STEPS.md. Raw URL:
   https://raw.githubusercontent.com/aidonerightcorp/humorvibes-jestry/main/demo_assets/humorvibes_submission.mp4
2. Make the six research kernels public (Share → Public). Do NOT re-run them.
3. New Writeup → Track "Humor Understanding" → paste WRITEUP.md → add links
   from section 2 (+ video URL) → upload images → **Submit** (not Save Draft).
4. Incognito sanity pass: repo 200s, notebooks render, video plays.
