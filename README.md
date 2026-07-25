# HumorVibes

A Gemma-powered humor engine for the Build with Gemma: Humor Genome NYC hackathon.

*(Formerly "Punchline Mesh" — a few internal Kaggle slugs keep the old name for stability:
the `punchline-mesh-src` dataset and already-running kernel sessions.)*

Theory first: see `THEORY.md`, a derivative of Karl Friston's "Your Brain Is a Detective
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

## Run

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
python3 verify_jestry.py                       # ALL GREEN gate (10 gates, live gemma4 incl.)
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
