# Open project roadmap

This roadmap turns the research backlog into contribution-sized outcomes. Priorities reflect
scientific value and dependency order, not promises about dates. Completed historical experiments
remain in [`RESEARCH_ROADMAP.md`](RESEARCH_ROADMAP.md); current work belongs here.

## P0 — keep the public release reproducible

- [x] Publish one canonical dataset, notebook, and repository.
- [x] Pin the notebook to an immutable source tag and verify mounted payload hashes.
- [x] Publish project status, narrative write-up, contribution rules, and expansion instructions.
- [x] Add Apache-2.0 for repository code and documentation plus a separate CC0-1.0 dedication for
  project-controlled Open Controls data; keep mixed-provenance imports on per-row licences.
- [x] Publish Open Controls as a separately licensed Kaggle dataset and COMPLETE notebook; verify
  a fresh download, remote source, terminal output, anonymous access, and cross-surface receipt.
- [x] Add a read-only cross-surface audit command that checks GitHub visibility, Kaggle dataset
  readiness, notebook completion, source tag, manifest hash, and anonymous HTTP access, then
  writes one receipt. **Good first issue.**
- [x] Add a small dependency smoke test in a clean virtual environment and document the supported
  Python range. **Good first issue.**
- [ ] Archive a citable release snapshot through Zenodo or an equivalent DOI service after the
  first outside contribution.

Acceptance for P0 work: a new machine can clone the repository, install dependencies, run tests,
download the public data, and pass `verify_wave2_release.py` without access to the private corpus.

## P1 — test context instead of asking text to carry it

- [ ] Build a caption-plus-drawing baseline with whole contests held out.
- [ ] Compare text-only, image-only, and multimodal arms on exactly the same contests.
- [ ] Add drawing hashes and leakage checks so duplicated or near-duplicated images cannot cross
  folds.
- [ ] Report performance against the 0.8262 label ceiling; use the 0.4110 bound only for the
  text-only arm.
- [ ] Add calibration and error slices by contest, vote count, and repeated-caption status.

Acceptance: a predeclared receipt records the source snapshot, groups, feature inputs, primary
metric, confidence interval, leakage checks, and every attempted arm, including failures.

## P1 — improve the human target

- [ ] Weight caption training by reliability derived from raw vote counts.
- [ ] Compare weighted and unweighted models with identical contest-held-out folds.
- [ ] Curate human-authored setup, expectation, alternate frame, punchline, and response labels.
- [ ] Measure inter-annotator agreement separately for frame validity, surprise, resolution, and
  funniness instead of requesting one composite score.
- [ ] Add a setup/punchline-native rated corpus to replace the Humicroedit format mismatch.

Acceptance: annotation guidelines, consent/licence terms, sampling plan, raw disagreement, and a
versioned schema ship before a model is ranked against the labels.

## P1 — validate a writer-facing use case

- [x] Ship a strict, privacy-minimized protocol schema, deterministic synthetic contract fixture,
  paired analyzer, writer-clustered bootstrap, and evidence-gated receipt. This validates the
  workflow; it is not a human result.
- [ ] Pre-register a within-writer crossover trial on matched premises with tool-assisted and
  normal-workflow conditions.
- [ ] Keep generated, rejected, selected, edited, rehearsed, and performed versions so selection
  effects are visible.
- [ ] Choose one primary endpoint in advance: blinded audience preference or time to a performed
  draft; treat voice preservation and harmful misreadings as guardrails.
- [ ] Randomize rehearsal order and model writer, premise, audience, and venue as grouped effects.
- [ ] Publish null results, dropouts, opt-outs, costs, and every attempted condition.

Acceptance: the trial satisfies the executable claim gate in
[`docs/REAL_WORLD_STUDY_WORKBENCH.md`](docs/REAL_WORLD_STUDY_WORKBENCH.md) and supports a
bounded statement about the sampled writers and audiences—not “the model is funny.”

## P1 — expand native multilingual structure

- [ ] Add precision-oriented form rules and fixtures for Portuguese, Greek, Amharic, Japanese,
  Italian, Arabic, and Turkish, where current specific-form coverage is effectively zero.
- [ ] Recruit native reviewers for each affected language; machine translation alone is not an
  acceptance test.
- [ ] Benchmark form coverage, false-positive samples, and aligned-pair consistency before and
  after each language addition.
- [ ] Add language-aware normalization tests for punctuation, script length, and token boundaries.

Acceptance: each language contribution includes verified positive and negative fixtures, a native
review note, coverage deltas, and no regression in `style_taxonomy.py selftest`.

## P2 — strengthen the form and instrument experiments

- [ ] Pre-register a larger balanced form study with a power calculation and source-held-out
  sensitivity analysis.
- [ ] Separate within-source from between-source effects so style does not proxy dataset origin.
- [ ] Certify a second model family using the same pinned texts, token masks, and acceptance bands.
- [ ] Test checkpoint size and quantization without changing the item sample.
- [ ] Replace model-written frames with human-authored frames in the resolution experiment.
- [ ] Refine the lexical-overlap leak guard and rerun the existing negative controls.

Acceptance: every comparison changes one factor at a time, retains failed arms, and reports paired
uncertainty rather than a table of unqualified means.

## P2 — make data contribution easier

- [ ] Add a command that validates one proposed source spec against a small live sample and emits
  a reviewable provenance/licence receipt. **Good first issue.**
- [ ] Add tiny committed fixture corpora for each supported ingestion shape. **Good first issue.**
- [ ] Generate a machine-readable schema reference from the exporter and test it against all
  public JSONL rows.
- [ ] Add a dry-run release report showing exactly which rows and licences would enter or leave a
  new public version.
- [ ] Add citation export for every public source family.

Acceptance: a contributor can test a parser and release policy on fixtures without downloading the
multi-million-row inventory.

## P2 — productionize the integration surface

The initial SDK/API, authenticated Ollama/OpenAI-compatible transports, multi-model embedding
registry, offline adversarial audit, Docker/Compose profiles, Kubernetes base, and local real-world
study workbench and bounded Open Controls endpoints are implemented in 0.6.0. Useful follow-ups are:

- [ ] Publish a signed multi-architecture image to GHCR and add a digest-pinned deployment overlay.
- [ ] Add gateway examples for TLS, identity, global rate limiting, and request tracing.
- [ ] Add optional streaming generation with disconnect/cancellation and backpressure tests.
- [ ] Add an external metrics backend and OpenTelemetry spans without logging prompts or keys.
- [ ] Add live compatibility jobs for a version matrix of Ollama and two OpenAI-compatible servers.
- [ ] Benchmark configured embedding models on frozen multilingual retrieval fixtures before
  recommending a default semantic model.
- [ ] Add a vector-database adapter protocol with conformance tests for SQLite, pgvector, and
  Qdrant; preserve model/dimension identity in every collection.
- [ ] Add a deployment-specific Kubernetes overlay only after its ingress controller, secret
  manager, registry, and egress policy are named.

Acceptance: each adapter has a no-network fake, an opt-in live test, explicit capability metadata,
bounded inputs/outputs, secret-redaction tests, and a receipt that distinguishes configured,
reachable, and quality-validated states.

## P3 — exploratory systems

- [ ] Compare retrieval over surface wording versus explicit comic frames.
- [ ] Evaluate audience-conditioned safety constraints with real subgroup annotations.
- [ ] Test deterministic compiled-humor artifacts only after human validation gates are defined.
- [ ] Turn the existing prototype UI into a receipt reader for the canonical study rather than a
  second source of result claims.

These are exploratory until P1 data and validation work land. UI polish does not upgrade an
unvalidated humor metric into evidence.

## How to claim an item

Open a GitHub issue using the research proposal template. Name one roadmap item, define the
smallest reviewable increment, list data/licence dependencies, and identify the receipt that will
show completion. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`docs/EXPANSION_GUIDE.md`](docs/EXPANSION_GUIDE.md).
