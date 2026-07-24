# The Humor Vibes Open — a hostable Kaggle community competition, built with Gemma

**Status:** complete design + working metric + deterministic data builder, ready to
host as a Kaggle Community Competition. Governed by the Jestry charter
(`../JESTRY-CHARTER-AND-CONSTITUTION-2026-07-23.md`): every design rule below traces
to a measured lesson in this repository, including the negative ones.

## Why this competition shape

The HumorVibes v4 ablation court (200/200 measurements, source-pinned, private)
falsified the fixed S/R/E/B scalar as a ranker **on headline edits**: ρ=0.033 with a
CI crossing zero. The autopsy located the boundary, not just the failure — headline
substitutions defeat setup/punchline inference. So this competition is built on the
other side of that boundary:

1. **Explicit setup/punchline items only.** Every item has a real setup field and a
   real punchline field. No headline edits.
2. **Constructed ground truth before human ground truth.** Track A's labels are
   structural facts, not funniness opinions: an item is either a genuine
   human-attested joke (harvested with provenance) or a constructed control
   (shuffled punchline from a different setup, or a deliberately boring
   continuation). The claim "your scorer separates jokes from non-jokes" is
   testable with zero annotation budget — it is exactly the separation the theory
   demands (surprise without a re-route is nonsense; no surprise is boring).
3. **Human ratings are the extension, not the foundation.** A private human-rated
   round can be added later; the metric interface already carries a per-item
   `Usage` split.

## Tracks

### Track A — Humor understanding (leaderboard, primary)

Given `test.csv` (id, setup, punchline), submit a `humor_score` per item.
**Metric: AUC** of `humor_score` separating genuine jokes from constructed controls
(`competition/metric_humor_vibes.py`, dependency-free, rank-based with tie
handling). Secondary diagnostic reported by the metric: matched-pair accuracy on
(genuine, shuffled-of-the-same-setup) pairs — a harder, per-setup discrimination.

Baseline for the leaderboard page: the HumorVibes measured `laugh_score` off Gemma
logits (teacher-forced S/R/E + null control + leak guard), which reached Spearman
ρ=0.115 against human grades on Humicroedit — weak, honestly reported, and exactly
the bar entrants should beat.

### Track B — Constrained generation (judged, protocol supplied)

Generate jokes for supplied (topic, audience) briefs. Scored by the frozen
instrument protocol: measured S/R/E in the laugh region on a **certified**
instrument (Kaggle-hosted Gemma with full logprobs — top-K-censored local readouts
are not certifiable; see `jestry_out/gemma4_calibration.json` for the receipt that
rule is built on), persona-conditioned B-gate under the brief's audience, null
control and leak guard always on. Model self-ratings are inadmissible.

### Track C — Been-done detection (precedent)

Given text pairs, classify: `surface_retell` / `same_frame_new_words` /
`different_bit`. Training pairs are constructible from the multilingual canon (the
same frame appears across languages by design — e.g. the Korean/Japanese/German
"chase two rabbits" family) and from Gemma-4-labeled frame clusters. This track
turns the joke-theft-vs-parallel-thinking dispute into a measurable task.

## Anti-gaming rules (each one is a lesson this repo already paid for)

- **Null controls in the test set.** A fraction of hidden test items are shuffled
  controls whose scores must rank low; a scorer that credits confabulated
  resolution (raw R without a decoy null) loses AUC exactly there.
- **Leak guard doctrine.** Track B frames that lexically contain the punchline are
  discounted by the protocol (the zoo-lab confabulation hole, closed twice).
- **Provenance requirement.** Track B submissions must carry per-item generation
  receipts (model, prompt digest). Hidden-fallback generation (a human writing
  "model" jokes) is a rules violation.
- **Public/private split.** `solution.csv` carries `Usage ∈ {Public, Private}`;
  public-leaderboard tuning is public-leaderboard-guided development, not a
  population estimate — the split is the guard.
- **Format boundary stated up front.** The metric measures joke-vs-control
  separation on explicit setup/punchline items. It does not certify a general
  funniness oracle; the ablation court is the citation for why that claim is not
  for sale here.

## Data pipeline (deterministic, licensed)

`make_competition_data.py` builds everything from on-disk, provenance-carrying
supply:

- **Genuine items**: harvested public-API jokes that ship native setup/punchline
  fields (`harvest_official_joke_api_*.jsonl`, `harvest_jokeapi_*.jsonl` twopart
  items), plus the three canonical reference jokes. Every record keeps source +
  license columns.
- **Shuffled controls**: derangement of punchlines across setups (seeded).
- **Boring controls**: fixed low-surprise continuations attached to genuine setups.
- Outputs: `data/train.csv` (labels visible), `data/test.csv`,
  `data/solution.csv` (labels + Usage split, host-only), and
  `data/sample_submission.csv`. Same seed → byte-identical rebuild. Scale up by
  re-running `harvest_supply.py` with bigger limits first; the builder picks up
  every dated harvest file automatically.

## Hosting checklist (Kaggle Community Competition)

1. Run `python3 ../harvest_supply.py keyless --limit 200` (or more) for a full-size
   pool, then `python3 make_competition_data.py`.
2. Create the community competition; upload `test.csv`, `train.csv`,
   `sample_submission.csv` as Data; keep `solution.csv` host-side.
3. Paste `metric_humor_vibes.py` as the evaluation metric (it implements the
   Kaggle metric interface: `score(solution, submission, row_id_column_name)`).
4. Set the public/private split from the `Usage` column.
5. Publish the overview from this document's Tracks + Rules sections, with the
   Gemma-integration requirement stated (Track B protocol requires a Kaggle-hosted
   Gemma; Track A baseline is the Gemma-measured laugh_score).
6. Attach the starter notebook: mount a Gemma checkpoint, vendor
   `mesh_signals.py`, score `test.csv` with `compute_signals`, submit — the
   baseline is reproducible end-to-end by any entrant.
