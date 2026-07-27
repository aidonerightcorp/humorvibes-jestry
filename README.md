# Humor Genome Wave 2

A public, reproducible Gemma study of humor structure. **HumorVibes** is the implementation name;
**Humor Genome Wave 2** is the canonical research release.

## Start here

| Public artifact | Open it | Status | What it is for |
| --- | --- | --- | --- |
| Executable study | [Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/humor-genome-wave2-gemma) | Public, COMPLETE | Read the write-up and rerun every public measurement |
| Research data | [Kaggle dataset](https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2) | Public, ready | Load the rights-filtered corpus, aligned phrases, frames, census, and manifest |
| Source and receipts | [GitHub repository](https://github.com/aidonerightcorp/humorvibes-jestry) | Public | Inspect implementation, tests, immutable source tags, and machine-readable evidence |

The notebook is the single canonical executable write-up. It clones the immutable
`humor-genome-wave2-v5` source tag, verifies the mounted dataset byte-for-byte and semantically,
loads the attached Gemma 2 checkpoint, and then runs the study. The latest cross-surface receipt is
[`jestry_out/wave2_publication.json`](jestry_out/wave2_publication.json).

## Release at a glance

- **3,164,600 rows** in the full local research inventory, spanning 217 source families and 62
  language labels.
- **121,670 rows** in the public, deterministic, rights-filtered slice; 2,693,272 rows remain in
  the census but are not republished verbatim.
- **7,913 aligned translation pairs** and **2,581 expectation/violation frames**.
- Gemma instrument check: **S = 3.188 over 10 tokens** against the pinned 3.19 reference.
- Full form study: **0/10** joke-form intervals strictly above the proverb control and 10/10
  overlapping it — **SEPARATION IS NOT ESTABLISHED**.
- Contest-held-out caption model: Spearman **0.1555**, or **37.8%** of the measured text-only bound.

`S` is model surprisal, not funniness. The dataset mixes jokes, captions, proverbs, idioms, and
other humor-adjacent text; source-specific human signals are not interchangeable grades.

## How the three public artifacts fit together

| Layer | Contract |
| --- | --- |
| Dataset | Publishes only explicitly redistributable text, plus a full-corpus census and hashes |
| Notebook | Verifies those files, runs Gemma, and displays the controlling statistical receipts |
| Repository | Builds both artifacts and preserves code, tests, provenance, negative results, and publication receipts |

## Canonical repository map

- `wave2_notebook/`: the one notebook to read and publish; older notebook directories are
  supporting experiments, not competing entry points.
- `build_kaggle_export.py`, `wave2_dataset/`, `verify_wave2_release.py`: public dataset build,
  Kaggle metadata, and fail-closed validation.
- `caption_*.py`, `style_taxonomy.py`, `corpus_census.py`: the measured Wave 2 analyses.
- `jestry_out/`: compact, versioned receipts; `wave2_publication.json` is the release index.
- `RESULTS.md`, `STYLES.md`, `DATA_SOURCES.md`: detailed findings, taxonomy, and source provenance.
- `research_out/` and the other notebook folders: historical/supporting experiments retained for
  auditability. They are not required to understand the canonical release.

## Reproduce the public release

```bash
git clone https://github.com/aidonerightcorp/humorvibes-jestry.git
cd humorvibes-jestry
python3 -m pytest -q tests/test_wave2.py
python3 wave2_notebook/build_wave2_notebook.py

kaggle datasets download -d taylorsamarel/humor-genome-wave2 \
  --unzip -p kaggle_wave2_public
python3 verify_wave2_release.py --root kaggle_wave2_public
```

## Project background and additional systems

The repository began as a broader Gemma-powered humor engine for the Build with Gemma: Humor
Genome NYC hackathon. It was formerly called "Punchline Mesh", so a few historical Kaggle slugs
retain that name for stability.

The theory is developed in `THEORY.md`, a derivative of Karl Friston's "Your Brain Is a Detective
Minimizing Surprise" (youtube.com/watch?v=g69Lj3huRvw). The brain is a mesh of dynamic neural
networks (weighted edges, sparse ATP-budgeted firing, tunable paths) supervised by a meta-model
that minimizes surprise. A joke is a controlled prediction error with a cheap, permitted
repair: surprising (S), resolvable through a hidden frame (R), affordable (E), and never
colliding with override-authority meta-meshes (B, the canonical bad-surprise definition below).
Gemma is an instrument here, not an oracle. S/R/E are read off its logits
(`mesh_signals.py`), not self-reported.

The prototype implements one loop:

1. Generate candidates (divergent sampling; per-format contracts in `formats.py`).
2. Retrieve relevant humor data sources and nearby calibrated examples.
3. **Measure** each candidate: S/R/E off Gemma logits, persona-conditioned B (`mesh_signals.py`).
4. Score across the qualitative humor mesh; plan audience/study experiments; rank mechanisms.
5. Compare candidates with pairwise/tournament ranking and the multi-LLM panel (`llm_panel.py`).
6. Explain which of the theory's four failure modes applies (predictable / no re-route /
   too expensive / bad surprise).
7. Repair the diagnosed failure while preserving the comic turn.
8. **Compile** validated material into deterministic artifacts (`compiled_humor.py`):
   joke programs (seeded slots, zero model calls at runtime) and clip render plans
   (HOOK/BUILD/SNAP timelines for ffmpeg/moviepy) — the Compiled-AI paradigm applied to comedy;
   auditable before performance and stage-safe only after its lint/probe gates pass. The verified
   demonstration intentionally remains `validated: False` because those gates rejected it.

## Canonical bad-surprise definition

Bad surprise is poorly defined, a bad surprise is a surprise that contradicts with internal models within a human brain that are so strong they override logic and are some of the primary drivers of a person's perception, understanding, and good/bad/moral/ethical views of the world. So basically, a surprise is not good if it disagrees with something that is already overriding logic or a surprise is not good it if disagrees with a nearly overwhelming generalization engine in a human mind that has significant overriding power to override logic, promote other false generalizations, and is the primary feature used to reduce surprise in that person's mind.

HumorVibes treats that definition as a first-class evaluation constraint, not as a synonym for offense, randomness, factual error, or incoherence.

## Additional prototype tools

Offline deterministic demo:

```bash
python3 cli_demo.py
```

Inspect the humor datacenter registry and seeded retrieval layer:

```bash
python3 datacenter_cli.py sources
python3 datacenter_cli.py branches
python3 datacenter_cli.py mechanisms
python3 datacenter_cli.py probes
python3 datacenter_cli.py rank-branches "political joke for a mixed audience" --preferences "bridge, not partisan"
python3 datacenter_cli.py rank-mechanisms "AI project managers for a NYC tech meetup" --audience "NYC tech meetup"
python3 datacenter_cli.py rank-probes "political joke for a mixed audience" --preferences "bridge, not partisan"
python3 datacenter_cli.py rank-sources "AI project managers for a NYC tech meetup" --audience "NYC tech meetup"
python3 datacenter_cli.py demo-search "AI project managers for a NYC tech meetup"
python3 datacenter_cli.py context "AI project managers for a NYC tech meetup" --audience "NYC tech meetup" --laughter-seconds 3 --applause 4
python3 datacenter_cli.py demo-lessons
python3 datacenter_cli.py plan-experiments "political joke for a mixed audience" --preferences "bridge, not partisan"
python3 datacenter_cli.py recommend-mechanisms "AI project managers for a NYC tech meetup" --audience "NYC tech meetup"
python3 datacenter_cli.py portability-check "Congress found a bipartisan solution: both sides agreed the printer was the real problem." --audience "mixed political audience" --preferences "bridge"
python3 datacenter_cli.py acquisition-plan "moral frame pairwise ranking for cross ideology political humor" --audience "mixed political audience" --preferences "bridge, dominant models"
python3 datacenter_cli.py market-gaps --audience "tech meetups and corporate teams" --preferences "AI, clean, smart, local"
python3 datacenter_cli.py style-shift-risk --current "clean observational corporate humor" --proposed "political aggressive dark crowdwork" --audience-lock-in 8 --bridge-overlap 2
python3 datacenter_cli.py model-judges
python3 datacenter_cli.py demo-model-convergence
python3 datacenter_cli.py model-jury-prompt --candidate "The AI project manager found the bottleneck: the calendar wanted attention." --audience "NYC tech meetup" --preferences "smart, not mean"
python3 datacenter_cli.py demo-tournament
```

Streamlit UI:

```bash
python3 -m streamlit run app.py
```

Gemma through Ollama:

```bash
export GEMMA_PROVIDER=ollama
export GEMMA_MODEL=gemma3:4b
python3 -m streamlit run app.py
```

## Measured-signal CLI (new layer)

```bash
python3 mesh_cli.py formats
python3 mesh_cli.py signals --text "I told my therapist about my fear of speed bumps. She said I'm slowly getting over it." --personas "NYC tech meetup,retired farmers"
python3 mesh_cli.py generate --topic "AI project managers" --format meme_caption --audience "NYC tech meetup"
python3 mesh_cli.py critique --text "HOOK: my landlord says the heat is on ... SNAP: it was a scented candle" --format shorts_script
python3 mesh_cli.py panel --text "..." --personas "improv crowd,corporate offsite"   # frontier-LLM judges, keys-gated
python3 mesh_cli.py compile --topic "meetings" --format one_liner --audience "office workers"
python3 mesh_cli.py run-compiled --artifact compiled_artifacts/<id>.json --seed 7
python3 mesh_cli.py compile-clip --script "HOOK: ... [desk] BUILD: ... [zoom] SNAP: ... [freeze]"
```

Provider selection: `GEMMA_PROVIDER=offline|ollama|transformers` (offline is the default; the
transformers provider auto-selects only inside Kaggle). The Kaggle demo notebook
(`build_notebook.py` → `notebook.ipynb`) runs everything against real Gemma logits. Its latest
pinned output is the verified CPU-fallback run; CUDA is used only when the notebook's probe passes:
https://www.kaggle.com/code/taylorsamarel/humorvibes-measuring-jokes-with-gemma

Reproducibility state (2026-07-12): an authenticated read-only audit re-pulled all six private
Kaggle kernels. All were COMPLETE; normalized source cells matched the local builders and every
mirrored research output matched byte-for-byte. See `research_out/kernel_audit_20260712.md`.
The seventh private kernel, `humorvibes-ablation-court` v4, subsequently completed and passed its
separate source/hash/privacy harvest gate: 200/200 Gemma measurements, fixed S/R/E/B rho=0.033
(95% CI [-0.126, 0.207]), an honest negative result. See
`research_out/kaggle/humorvibes-ablation-court/ABLATION_REPORT.md`. This verification does not make
any notebook public and is not a competition submission.

## Wave 2 corpus and Gemma study (2026-07-26)

Wave 2 turns the source sweep into a reproducible release rather than a directory-sized claim:

- **3,164,600** full-corpus rows across 217 source families and 62 language labels;
- **121,670** redistributable rows in the deterministic, per-family-capped Kaggle slice, selected
  from 471,328 eligible records after a deny-first rights gate;
- **7,913** non-English phrases carrying English counterparts and **2,581** independently
  annotated expectation/violation frames;
- per-record provenance and licence, a full-corpus census, and SHA-256/byte manifests verified by
  the consuming notebook before it measures anything.

The published sample is deliberately stratified and rights-filtered. The caption family is 71.0%
of the full corpus; a random sample would reproduce that imbalance, while the deny-first licence
gate and 12,000-row family cap reduce captions to 2.2% of the public slice and hold every source
family below 9.9%. Selection is SHA-256 ordered and clock-free, so rebuilding the same corpus
yields identical bytes. The other 2,693,272 records remain represented in the local census but
their verbatim text is not published because their licence class is noncommercial, research-only,
or unclassified.

The Gemma-2 form study reports uncertainty, not a winner: all ten joke-form bootstrap intervals
overlap the proverb control, so the checked-in notebook prints **SEPARATION IS NOT ESTABLISHED**.
Its S statistic is model surprisal, not a human funniness grade.

The human-label arm is contest-held-out rather than row-random: 30 structural text features reach
median Spearman **0.1555** on 215,465 captions across 360 unseen drawings, or **37.8% of the
measured text-only bound**. The canonical notebook cross-checks that receipt against the independent
label-ceiling and cross-drawing portability receipts before displaying it.

```bash
python3 harvest_wave2.py list
python3 style_taxonomy.py selftest
python3 build_kaggle_export.py --per-family 12000
python3 verify_wave2_release.py
python3 -m pytest -q tests/test_wave2.py
python3 wave2_notebook/build_wave2_notebook.py
```

Dataset: https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2
Notebook: https://www.kaggle.com/code/taylorsamarel/humor-genome-wave2-gemma

## Files

- `THEORY.md`: the canonical theory (Friston-derived mesh framing → computable S/R/E/B signals).
- `mesh_signals.py`: measured surprise/resolution/efficiency/bad-surprise from Gemma logits.
- `formats.py`: short-form media format presets (timing envelopes) for generation + critique.
- `compiled_humor.py`: Compiled-AI pipeline — validation-gated deterministic joke programs and
  clip plans.
- `llm_panel.py`: multi-LLM audience panel (frontier + local judges, keys-gated, convergence report).
- `live_set_controller.py`: laughter-driven live set — WAV audit-clip laughter scoring (3–6 Hz
  burst envelope), per-frame Thompson-sampling over frozen artifacts, auditable JSONL show logs
  (`mesh_cli.py live`).
- `mesh_cli.py`: unified CLI over all of the above.
- `build_notebook.py` / `notebook.ipynb` / `kernel-metadata.json`: Kaggle Gemma demo notebook;
  its verified run used the explicit CPU fallback after the CUDA probe failed.
- `app.py`: Streamlit interface.
- `cli_demo.py`: no-browser demo.
- `gemma_client.py`: provider adapter for deterministic offline, Ollama, and Transformers paths;
  deterministic offline is the local default.
- `humor_mesh.py`: schema, canonical definition, fallback evaluator.
- `humor_datacenter/`: study branches, audience probes, comedy mechanisms, source registry, acquisition planning, market analytics, model-jury convergence, portability checks, pairwise ranking, experiment planning, audience adaptation, experiment logging, schema, embeddings, SQLite store, and demo retrieval.
- `comedy_primitives_dataset.py` → `dataset_out/`: the humor genome as a portable dataset.
  Comedy mechanisms and format specs as structured primitives, every indexed item with its
  source/license/language, the Gemma-labeled frame subset, rows carrying real teacher-forced
  S/R/E, and **dual-channel 768-dim embeddings** (surface wording and comic frame embedded
  separately, which is what makes cross-lingual same-engine retrieval work). Ships a dataset
  card and a manifest of sha256 digests; the `.npy` matrices are git-ignored and rebuilt by
  rerunning the exporter. Verified by gate G13 (row counts, license coverage, matrix alignment).
- `browser_test_portal.py`: real headless-Chrome acceptance test of the portal over the DevTools
  protocol. Every tab clicked and screenshotted, JS exceptions and failed requests captured,
  rendered numbers cross-checked against the API, phone viewport checked for overflow.
  Receipt: `jestry_out/browser_test_portal.json`.
- `canonicalize_format.py`, `native_format_probe.py`, `instrument_quant_check.py`: the
  format-boundary experiment, its native-format follow-up, and the quantization-robustness probe.
  Findings are written up in `RESEARCH_NOTE_INSTRUMENT_BOUNDARIES.md`.
- `DATA_SOURCES.md`: scanned source matrix and acquisition notes.
- `SOURCE_SWEEP_2026-07-26.md`: live source inventory, dead-source ledger, parser repairs, and
  licensing limits for Wave 2.
- `harvest_wave2.py` / `wave2_specs.json`: checkpointed, exact-deduped API/Wikimedia/HuggingFace
  acquisition; bulk HuggingFace reads use resumable Parquet transport with row-API fallback.
- `style_taxonomy.py` / `STYLES.md`: structural form, lexical domain, and source-declared style
  axes, including language-specific forms and the documented length-proxy confound.
- `corpus_census.py` / `build_kaggle_export.py`: one-pass census and bounded-memory deterministic
  release builder; release reads fail closed on malformed JSON.
- `caption_corpus.py` / `caption_ceiling.py` / `caption_portability.py` / `caption_model.py`:
  integrity-clean caption loading, two-estimator label ceiling, cross-drawing text-only bound, and
  contest-held-out structural model. Compact measured receipts live under `jestry_out/`.
- `verify_wave2_release.py` / `verify_jestry.py`: semantic release checks and 16 cross-receipt gates.
- `wave2_notebook/`: deterministic notebook builder, checked-in notebook, and Kaggle metadata.
- `RESEARCH_ROADMAP.md`: concrete study backlog for building the prototype into a stronger hackathon entry.
- `JUDGE_EVIDENCE.md`: claim-by-claim receipt map, negative results, and private/public gates.
- `ablation_lab/`: source-pinned private ablation kernel builder, tests, and receipt-gated
  harvester; versions 1–3 are excluded from evidence and only the harvested v4 result counts.
- `research_out/kaggle/humorvibes-ablation-court/`: 200-row S/R/E/B ablation, paired controls,
  failure table/figure, model/data/runtime receipts, and compact judge-facing report.
- `demo_assets/humorvibes_studio_20260712.png`: current branded studio screenshot. It visibly
  discloses the offline deterministic provider and is not presented as Gemma measurement evidence.
- `prompts/`: structured Gemma prompts.
- `examples/`: demo inputs.

## Jestry — the verified laugh-reuse layer (2026-07-23, additive)

A constitution-governed reuse/construction layer over everything above, built with
Gemma 4 (Ollama `gemma4`) + embeddinggemma. Charter (18 laws, machine-encoded and
test-pinned): `JESTRY-CHARTER-AND-CONSTITUTION-2026-07-23.md`. Writeup:
`JESTRY_WRITEUP.md`. Nothing in the pinned evidence above is modified — the
harvested-ablation source-hash tests stay green.

```bash
python3 jestry_cli.py charter                  # the 18 laws, funnel, acceptance levels
python3 jestry_cli.py cards                    # honest registry census (kind-separated)
python3 jestry_cli.py run "Make a joke about AI project managers" \
    --audience "NYC tech meetup" --personas "NYC tech meetup" --format one_liner
python3 -c "from precedent import PrecedentIndex; i=PrecedentIndex(); i.ensure_embedded(); \
print(i.been_done('Man plans and God laughs.').verdict)"   # been-done? (embeddinggemma)
python3 harvest_supply.py keyless --limit 20   # grow supply w/ provenance + dedupe receipts
python3 calibrate_gemma4.py                    # instrument certification (currently: honest FAIL)
python3 jestry_portal.py                       # stdlib live portal on :8081
python3 verify_jestry.py                       # 16 receipt gates; unavailable live checks skip honestly
```

- `jestry.py` — routes ladder (replay → remix → compose-residual → frontier → abstain),
  hard `HumorPolicy` gates, nine-stage contribution-funnel receipts
  (`jestry_out/receipts.jsonl`), groaner ledger, governed laughter bandit.
- `gemma4_nll.py` — forced-NLL S/R/E via Ollama top-K logprobs; copy-attractor
  finding + `certified: false` calibration receipt (`jestry_out/gemma4_calibration.json`):
  uncertified instruments can measure and diagnose but never mint acceptance
  (`RouteProfile.require_certified`); the certified path is `gemma2_full_nll.py`.
- `precedent.py` — "has this joke been done?" at surface + frame level, multilingual
  canon (`corpora/proverbs_multilingual.jsonl`), Gemma 4 labeling lane.
- `harvest_supply.py` — licensing-clean supply growth (ingest lanes + 3 keyless joke
  APIs + stamped synthetic lane + Claude-authored canon lane), receipted; API lanes
  are precedent-deduped on fetch (the authored canon lane predates its own entries).
- `live_portal/` — Kaggle kernel that tunnels the portal via trycloudflare
  (same recipe as the studio kernel; new slug `humorvibes-jestry-portal`).
- `competition/` — hostable "Humor Vibes Open" community-competition pack: design doc,
  dependency-free AUC metric, deterministic data builder (built on the ablation
  court's format-boundary lesson: explicit setup/punchline items only).

## Demo script

Prompt: "Make a joke about AI project managers for a NYC tech meetup. Keep it smart, not mean."

Show:

- With a Gemma provider selected, Gemma generates three candidates; the deterministic offline
  demo exercises the same workflow but is never presented as Gemma evidence.
- The mesh scores structure, audience fit, timing, surprise, cultural context, preference fit, truth alignment, and bad-surprise risk.
- The datacenter panel shows relevant source families and nearby calibrated examples.
- The audience probe/live response panel changes semantic, wording, and delivery directives for the next candidate.
- Political diversity and cross-ideology bridge controls test whether a joke can travel across political identities.
- Experiment planning suggests which study to run next, which probes to ask, and which mechanisms to explore or exploit.
- Market analytics estimates underserved humor niches and style-shift risk for established audiences.
- Model-jury convergence shows where independent model judges agree or disagree before trusting a score.
- Pairwise tournament ranking compares multiple candidates when scalar mesh scores disagree.
- The app selects the strongest candidate.
- The repair step preserves the comic turn while reducing bad-surprise risk for the audience.
