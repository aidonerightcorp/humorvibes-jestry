# HumorVibes Research Roadmap

This is the working backlog for turning HumorVibes from a joke generator into a humor study and adaptation system.

## Current Thesis

Humor should be modeled as a multi-signal process: structure, surprise, audience response, timing, cultural context,
preference, dominant internal models, and repairability. The canonical bad-surprise definition remains the controlling
definition for risk; external datasets provide proxy signals, not replacements.

## High-Leverage Experiments

1. Cross-ideology portability A/B
   - Generate four matched jokes: partisan-label target, politician target, institution/process target, shared-frustration target.
   - Run label-swap, target-location, moral-frame, shared-frustration, and bad-surprise tests.
   - Success: the shared-process variant wins or ties across subgroups without elevated bad-surprise flags.

2. Audience preference embedding probe
   - Ask 3-5 fast preference questions or pairwise choices before generation.
   - Create a temporary audience vector from preferred mechanisms, lexical texture, targets, and risk tolerance.
   - Success: mechanism recommendations predict later pairwise wins better than global priors.

3. Live response adaptation
   - Log laughter seconds, applause, groans, confusion, silence, and smile level after each joke.
   - Compare static next joke versus response-aware tag, pivot, premise repair, or concrete rewrite.
   - Success: response-aware choices improve reward over three attempts.

4. Bad-surprise boundary pairs
   - Build near-pairs where the same comic turn targets identity/worldview versus situation/process.
   - Ask Gemma to identify which dominant internal model is being contradicted.
   - Success: repairs reduce bad-surprise risk while preserving surprise and resolution.

5. Pairwise tournament ranking
   - Generate 4-6 candidates with distinct mechanisms.
   - Run pairwise judgments and aggregate with `humor_datacenter/ranking.py`.
   - Success: tournament winner also has a strong mesh score, low portability flags, and clear explanation.

6. Repair-preserve-engine comparisons
   - Create safer, sharper, more concrete, bridge, classroom-safe, and more concise variants.
   - Score whether the original comic engine survived.
   - Success: at least one repair improves target fit without making the joke bland.

7. Humor market gap analytics
   - Represent comedian archetypes, audience niches, and joke portfolios as style vectors.
   - Estimate demand, supply density, closest competitors, and style-shift flop risk.
   - Success: identify a niche with high gap score and a low-risk transition path from the current audience promise.

8. Model jury convergence
   - Score the same joke with Gemma/Kimi/GLM-style independent judges.
   - Track per-dimension mean, stdev, convergence, and dissent rationales.
   - Success: use converged dimensions directly and escalate low-convergence dimensions to audience probes.

## Data Acquisition Priority

1. Jester ratings for preference vectors.
2. Humicroedit, FunLines, and HaHackathon for text humor/risk calibration.
3. Humor in Word Embeddings for lexical texture and small audience probes.
4. Open Mic, StandUp4AI, TIC-TALK, and When to Laugh for live response/timing.
5. HumorRank and New Yorker caption preferences for pairwise ranking methods.
6. Morality Frames, political robot jokes, parody/satire papers, and cross-partisan discussion data for political portability.
7. Chumor, Spanish humor corpus, ManzaiSet, UR-FUNNY, HumorDB, SARC, and MUStARD for culture/multimodal expansion.

## Prototype Milestones

1. Use `plan-experiments` in the app sidebar and show the top plan before generation.
2. Add a candidate slate table with pairwise/tournament results.
3. Persist audience sessions to `data/attempt_logs/*.jsonl`.
4. Add import scripts that download only license-safe datasets or ingest user-provided files.
5. Add a short demo preset for cross-ideology bridge jokes.
6. Add a short demo preset for live audience response and tag/pivot behavior.
7. Add source cards showing which external dataset informed each recommendation.
8. Add a market-gap dashboard tab.
9. Add a model-jury convergence dashboard tab with judge outputs and disagreement dimensions.

## Demo Angle

The strongest two-minute demo is:

1. Ask for a political joke for a mixed audience.
2. Show the planner recommending a cross-ideology portability A/B.
3. Generate a candidate that fails the label-swap or moral-frame test.
4. Repair it into a shared-frustration/process-target joke.
5. Run pairwise ranking and show the repaired version winning.
6. Log a live response and show the next-joke adaptation change.

## Expansion Night 2026-07-24 (post-submission levers, all receipted)

Work done after the submission state was frozen (git tag `submission-2026-07-25`), on the `expansion` branch. Each item names its receipt so the next session starts from evidence, not recollection.

1. Format-boundary experiment: edit-anchored canonicalization of Humicroedit headlines versus the generic split and a placebo split, measured on the certified instrument. Design and results: `canonicalize_format.py`, `jestry_out/format_boundary_experiment.json`, audit trail in `jestry_out/format_boundary_items.jsonl`. Follow-up lever: a general headline-to-setup/punchline canonicalizer in front of the instrument, then tweets and captions.
2. Instrument science: quantization robustness probe of the certified calibration (Q8_0 versus the certified Q4_K_M under the same acceptance region): `instrument_quant_check.py`, `jestry_out/gemma2_full_nll_quant_check.json`. Follow-up lever: certify a second model family and tighten the S band with more reference cases.
3. Frame-channel density: labeling lane batch took labeled frames from 230 to 270 with zero failures (`jestry_out/frame_label_batch_20260724.json`). Follow-up lever: schedule recurring batches until frame coverage stops improving been-done verdicts, tracked by hinted-probe rankings.
4. Multilingual supply: citation-template-aware wikiquote lane landed 640 French and Italian proverbs (`harvest_wikiquote_citation.py`, `corpora/harvest_wikiquote_citation_20260724.jsonl`); the Italian page needed bullet parsing, not templates, which is why the earlier lane read zero. Follow-up lever: apply the same page-structure probe to the fa/hi/ar pages that returned thin results.
5. Hostable competition: launch bundle completed under `competition/launch/` (hosting guide, paste-ready description, executed starter notebook, host-side solution file). The one open action is a human clicking through the Kaggle community-competition form.
6. The research synthesis of all instrument findings lives in `RESEARCH_NOTE_INSTRUMENT_BOUNDARIES.md`.
