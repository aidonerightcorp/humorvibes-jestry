# Claude Code handoff: HumorVibes Research

*Role: maintainer/agent operating procedure for the maintainer's machine — the absolute paths
below are that machine's and are intentionally kept. Outside contributors start at
[`CONTRIBUTING.md`](CONTRIBUTING.md); the evidence hierarchy lives in
[`docs/THESIS_AND_EVIDENCE.md`](docs/THESIS_AND_EVIDENCE.md).*

This is the operational handoff for continuing Humor Genome Wave 2 and the `humorvibes-research`
application after the formal v0.8.0 closeout. Read this file, then read
[`PROJECT_CLOSEOUT.md`](PROJECT_CLOSEOUT.md), [`PROJECT_STATUS.md`](PROJECT_STATUS.md), and
[`CONTRIBUTING.md`](CONTRIBUTING.md) before changing code or claims.

The initial delivery is complete. Continue only with bounded maintenance, reproducibility work,
or an existing post-closeout issue whose missing real-world evidence is actually available. Do
not create speculative work merely to keep the project active.

## Repository and authority

- Authoritative local checkout:
  `/home/username/new_algo/comps/humorvibes-jestry-repo`
- Public repository:
  <https://github.com/aidonerightcorp/humorvibes-jestry>
- Default branch: `main`
- Formal application release: `v0.8.0`
- Release commit: `5ca7b020a8a4b9d7ca3d82f85dc87aff704254d0`
- Validated post-publication baseline before this handoff:
  `7929b534b88c927f0e0f8ddfa49b962da1b490d7`
- Validated baseline at the 2026-07-28 post-closeout refresh: `bb24900` (PR #36 merge);
  after the adversarial referee round: `18aaf4d` (PR #38 merge). Re-verify with the
  standard commands rather than trusting any hash
- Immutable Wave 2 notebook source tags: `humor-genome-wave2-v10` (current; notebook v16) and `humor-genome-wave2-v9` (v14 run); neither moves
- Immutable Open Controls source tag: `humor-genome-open-controls-v2`

The large artifact tree at
`/home/username/new_algo/comps/build-with-gemma-humor-genome-nyc` is not the publication Git
checkout. It contains heavy local research artifacts and may be useful for explicitly requested
rebuilds, but all commits, pull requests, tags, and releases must originate from the authoritative
checkout above. The private/heavy corpus is not required to test the application or verify the
public releases.

Before starting work, inspect rather than assume current state:

```bash
cd /home/username/new_algo/comps/humorvibes-jestry-repo
git status --short --branch
git remote -v
git fetch --prune origin
git log -5 --oneline --decorate
gh pr list --repo aidonerightcorp/humorvibes-jestry --state open
gh issue list --repo aidonerightcorp/humorvibes-jestry \
  --state open --milestone "Post-closeout research and ecosystem"
```

Do not pull, reset, delete branches, or discard files until the worktree and any user-owned changes
have been inspected. Do not move either immutable notebook tag or the v0.8.0 release tag.

## Problem being solved

Humor research and humor-writing tools often collapse several different things into one score:
linguistic surprise, source popularity, a model preference, an audience response, and actual
writer benefit. That makes attractive demonstrations easy to produce and reliable conclusions
hard to defend. Multilingual and multimodal humor add cultural, contextual, licensing, consent,
and leakage problems that a larger text model does not solve by itself.

This project explores a narrower and testable starting point: predictive systems continually
reduce surprise, while humor can involve a setup that supports one prediction followed by a
punchline that forces a rapid, coherent reinterpretation. “The brain is a surprise-reduction
engine” is a motivating predictive-processing frame, not a completed biological theory. Model
surprisal is therefore an instrument for one computational property, not a measurement of
funniness.

The proposed solution is an evidence-bearing research and integration stack:

1. preserve a provenance-rich, rights-filtered multilingual corpus;
2. run reproducible Gemma and statistical experiments with uncertainty and negative results;
3. provide deterministic CC0 controls and frozen retrieval tasks;
4. keep human, synthetic, model, local, and public evidence visibly separate;
5. provide consent-, rights-, and privacy-aware protocols for the human studies that could test
   actual writer or audience value;
6. expose bounded SDK, CLI, API, embedding, provider, Docker, and Kubernetes contracts that an
   application can integrate without upgrading proxy measurements into product claims.

The conceptual grounding and citations are in
[`docs/RESEARCH_FOUNDATIONS.md`](docs/RESEARCH_FOUNDATIONS.md). Persona-specific uses and claim
gates are in
[`docs/PRODUCT_AND_RESEARCH_USE_CASES.md`](docs/PRODUCT_AND_RESEARCH_USE_CASES.md).

## Controlling findings

These findings must remain visible in code, notebooks, documentation, and downstream summaries:

- The form study did **not** establish separation. Zero of ten joke-form bootstrap confidence
  intervals sit strictly above the proverb control interval, and all ten overlap it.
- Gemma surprisal `S` is not funniness. A larger `S` means the measured continuation was less
  predictable to the pinned model under the pinned token mask.
- The caption study is weak on text alone: median within-contest Spearman correlation is `0.1555`.
  The measured text-only bound is `0.4110`, while the label ceiling is `0.8262`. A text-only result
  does not bound a system that can see the drawing.
- The strongest structural model does not transfer (within-Humicroedit `0.5075` → `-0.0091` on
  Reddit); the sole three-corpus survivor is `punch_rarity_max` with a negative sign. Wave-1
  post-closeout receipts (2026-07-27) replicate the null pattern: declared-style 0/7 separate
  but underpowered at n=12 (among-styles permutation p = 0.45), divisiveness reliable overall
  but not easier to predict, word-level demographic gaps not detectable at these per-word n
  (2/4,997 under Welch-t+FDR). Per-tenet status: `docs/THESIS_AND_EVIDENCE.md`.
- The surprise-reduction account remains a falsifiable design framework, not proof that a model
  understands humor or that the brain is fully explained by prediction error.
- Synthetic controls, generated fixtures, API checks, and provider retrieval benchmarks validate
  software and proxy-task behavior. They do not establish human funniness, writer benefit,
  cultural validity, or audience suitability.
- A domain/form cross-tab must exclude `shaggy_dog` when interpreting structure because that label
  is assigned by length and can proxy source verbosity.
- Script-aware length screening is required. A Latin-script character floor previously removed
  legitimate short Chinese content such as four-character chengyu.
- The highest-value scientific continuation is the preregistered writer crossover pilot with
  consented writers and blinded, opt-in audience evaluation. The repository contains the launch
  and analysis contracts, but no human outcome is claimed.

## Stable public surfaces

| Surface | Verified public identity | State |
| --- | --- | --- |
| Wave 2 dataset | <https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2> | Dataset v7, ready |
| Wave 2 executable study | <https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study> | Notebook v16, `COMPLETE` |
| Open Controls dataset | <https://www.kaggle.com/datasets/taylorsamarel/humor-genome-open-controls> | Dataset v4, ready |
| Open Controls study | <https://www.kaggle.com/code/taylorsamarel/humor-genome-open-controls-causal-design-lab> | Notebook v4, `COMPLETE` |
| Application release | <https://github.com/aidonerightcorp/humorvibes-jestry/releases/tag/v0.8.0> | Public wheel, sdist, release notes, and manifest |
| Container | <https://github.com/users/aidonerightcorp/packages/container/package/humorvibes-jestry> | Public `linux/amd64` and `linux/arm64` image |
| Continuation milestone | <https://github.com/aidonerightcorp/humorvibes-jestry/milestone/2> | Open external-evidence work, not release debt |

The independently verified container identity is:

```text
ghcr.io/aidonerightcorp/humorvibes-jestry@sha256:95568eb899c1a3aa51d8dc1a0884212390f9cc4e85c3aa643477a6355673f4e7
```

The v0.8.0 release passed 221 tests at the tag. The post-publication closeout baseline passed 222
tests, all 27 network-free adversarial contracts, clean wheel installs on Python 3.10 through
3.14, a complete v0.7.0 DOI source-identity rebuild, Kustomize and Helm renders, and the hardened
container smoke test. The controlling post-publication CI run is
<https://github.com/aidonerightcorp/humorvibes-jestry/actions/runs/30316511374>.

Machine-readable controlling evidence:

- [`jestry_out/v0_8_0_publication.json`](jestry_out/v0_8_0_publication.json), SHA-256
  `2d2dc37a74a046c7dbedc39fc30619cd44322aba5171084fb014a5891c802480`
- [`jestry_out/v0_8_0_deployment_validation.json`](jestry_out/v0_8_0_deployment_validation.json),
  SHA-256 `c5485f7072af9f9f57db4b4b0274d1905a6f86c62e87202e4cc7e38df389410f`
- [`jestry_out/v0_8_0_public_surface_audit.json`](jestry_out/v0_8_0_public_surface_audit.json),
  SHA-256 `961b35877ead6bba28335be609e16e4c5833bea69f985b8afb069c441f43ddc3`
- [`jestry_out/wave2_publication.json`](jestry_out/wave2_publication.json) for the Wave 2 release
- [`jestry_out/open_controls_publication.json`](jestry_out/open_controls_publication.json) for the
  Open Controls release

Treat a receipt as evidence only for its declared scope and truth boundary. Recompute its SHA-256
after an intentional receipt update; never silently edit a receipt while leaving a stale hash in
reader-facing documentation.

## What is implemented

### Reproducible research and data

- `build_kaggle_export.py`, `verify_wave2_release.py`, `wave2_dataset/`, and `wave2_notebook/`
  build and verify the rights-filtered Wave 2 public release and canonical notebook.
- `style_taxonomy.py`, `corpus_census.py`, and the study scripts preserve form, domain,
  source/style, language, and sampling distinctions.
- `build_open_controls.py`, `verify_open_controls_release.py`, `open_controls_dataset/`, and
  `open_controls_notebook/` provide 120,000 project-controlled CC0 procedural rows, schemas,
  grouped splits, and frozen easy/hard retrieval tracks.
- `source_spec_preflight.py` validates one proposed source against committed licensed fixtures
  before any network fetch or corpus write.

### SDK, providers, and API

- `humorvibes/config.py`, `llm.py`, `embeddings.py`, `signal_providers.py`, and `http.py` implement
  bounded offline, Ollama local/cloud, OpenAI-compatible, hash, and optional local embedding
  contracts with model allowlists and secret-safe errors.
- `humorvibes/service.py`, `api.py`, `client.py`, `cli.py`, and `docs/openapi.json` expose the typed
  SDK, dependency-free client, CLI, FastAPI endpoints, and deterministic OpenAPI contract.
- `humorvibes/observability.py` provides low-cardinality metrics and body-free tracing. Do not add
  bodies, keys, raw user IDs, or provider URLs to telemetry.
- `humorvibes/adversarial.py` is the deterministic, network-free attack suite. A passing suite is a
  software contract, not a model-quality result.

### Human-evidence and benchmark gates

- `humorvibes/studies.py`, `study_launch.py`, and
  [`docs/REAL_WORLD_STUDY_WORKBENCH.md`](docs/REAL_WORLD_STUDY_WORKBENCH.md) implement the
  privacy-minimized writer crossover protocol, blinded schedules, hierarchical sensitivity,
  analysis, and fail-closed claim gates.
- `humorvibes/multimodal_benchmark.py`, `human_multimodal.py`, and
  [`docs/MULTIMODAL_BENCHMARK.md`](docs/MULTIMODAL_BENCHMARK.md) separate procedural positive
  controls from rights-cleared, consented human cohorts.
- `humorvibes/native_fixtures.py` and
  [`docs/NATIVE_LANGUAGE_CONTRIBUTIONS.md`](docs/NATIVE_LANGUAGE_CONTRIBUTIONS.md) require one
  language/form per pull request, rights evidence, positive and hard-negative fixtures, and a
  privacy-minimized native/fluent human attestation.
- `humorvibes/provider_matrix.py`, `retrieval_benchmark.py`, `crosslingual_retrieval.py`,
  `provider_matrix_live_v1.json`, and [`docs/PROVIDER_MATRIX.md`](docs/PROVIDER_MATRIX.md) preserve
  exact model/server identities, failures, throughput, frozen benchmark digests, intervals, and
  language slices. No universal semantic default was established.
- `humorvibes/doi_archive.py`, `tools/build_doi_archive.py`, and `tools/verify_doi_archive.py`
  verify the complete immutable v0.7.0 source inventory. They do not mint or imply a DOI.

### Packaging and deployment

- `pyproject.toml` and `uv.lock` define `humorvibes-research` 0.8.0 and the supported Python
  3.10–3.14 matrix.
- `Dockerfile`, `compose.yaml`, `compose.ollama.yaml`, and `compose.ollama-cloud.yaml` provide
  offline, local Ollama, and Ollama cloud deployment paths without embedding keys.
- `deploy/kubernetes/`, `deploy/helm/humorvibes/`, `deploy/gateway/`, and
  `deploy/overlays/ghcr/` provide restricted non-root, read-only, default-deny deployment
  contracts and a digest-pinned public-image overlay.
- `.github/workflows/app-contracts.yml` is the required CI gate.
- `.github/workflows/publish-container.yml` builds release artifacts and the attested
  multi-architecture image only from version-matching release tags.

## Reproduce the maintained state

Use the same locked setup as CI:

```bash
cd /home/username/new_algo/comps/humorvibes-jestry-repo
uv sync --frozen --extra api --extra dev
uv run --frozen pytest -q
uv run --frozen humorvibes adversarial
git diff --check
uv build --wheel
```

Run the live, read-only cross-surface audit when Kaggle credentials are configured. It also checks
anonymous HTTP visibility and downloads the public manifests for byte comparison:

```bash
uv run --frozen python tools/public_release_audit.py \
  --out /tmp/humorvibes-public-surface-audit.json
```

Inspect capabilities without any network model call:

```bash
uv run --frozen humorvibes capabilities
uv run --frozen humorvibes doctor
uv run --frozen humorvibes openapi --out /tmp/humorvibes-openapi.json
```

Run the exact released image locally with the same hardened controls used in verification:

```bash
docker run --rm --read-only --tmpfs /tmp:rw,size=64m \
  --cap-drop ALL --security-opt no-new-privileges:true \
  -p 127.0.0.1:8080:8080 \
  ghcr.io/aidonerightcorp/humorvibes-jestry@sha256:95568eb899c1a3aa51d8dc1a0884212390f9cc4e85c3aa643477a6355673f4e7
```

Then, from another shell:

```bash
curl --fail --silent --show-error http://127.0.0.1:8080/health/ready
curl --fail --silent --show-error http://127.0.0.1:8080/v1/capabilities
```

For an API or deployment change, also run the exact deployment verifier documented in
[`CONTRIBUTING.md`](CONTRIBUTING.md):

```bash
uv run --frozen python verify_deployment.py --docker \
  --kustomize-image registry.k8s.io/kubectl:v1.36.2 \
  --helm-image alpine/helm:4.2.0@sha256:af08f75a3130d666a50b9fc150f40987ef20b885cf67659aabf4b83a5f2c5501
```

Do not run the multi-million-row corpus rebuild, a Kaggle publication, a live provider matrix, or a
human-study collection merely as a smoke test. Those operations require explicit scope, rights or
consent review, credentials, resource planning, and a versioned receipt destination.

## Evidence and safety rules

These are binding for future work:

1. Preserve candidate versus validated truth, synthetic versus human evidence, local versus
   public state, configured versus reachable providers, and draft versus published artifacts.
2. Never describe model surprisal, source votes, retrieval accuracy, or generated ratings as
   human funniness.
3. Do not simulate participants, native reviewers, consent, legal review, rights ownership,
   repository-owner actions, a production deployment, or a DOI.
4. Keep failed arms, null results, confidence intervals, confounds, attrition, and exclusions in
   the controlling output.
5. Do not commit credentials, `.env` contents, literal Kubernetes Secrets, model caches, raw
   identity fields, or private/research-only corpus rows.
6. Repository code and documentation are Apache-2.0. Open Controls project-owned data is CC0-1.0.
   Imported dataset records retain their own per-record licences. Unclear rights fail closed for
   public verbatim export.
7. Do not edit generated notebooks directly. Change the builder, rebuild, run its focused tests,
   and verify the generated notebook diff.
8. If a claim changes, update the computation, regression test, machine-readable receipt, and
   nearest reader-facing document together.
9. Do not rewrite `main`, release tags, notebook source tags, or public release history. Use a
   scoped branch and pull request. A new immutable release receives a new tag.
10. Never treat a successful upload or running job as publication proof. Wait for terminal state,
    download the result independently, and compare its content and hashes.

## Post-closeout maintenance log

The narrative record of this era is [`docs/POST_CLOSEOUT_RECORD.md`](docs/POST_CLOSEOUT_RECORD.md);
the verbatim referee reports behind PR #38 are
[`docs/REFEREE_REPORT_2026-07-28.md`](docs/REFEREE_REPORT_2026-07-28.md).

The closeout did not freeze the repository; it froze the claims. Four bounded waves have
landed since v0.8.0, none changing the application package:

| PR | What it did |
| --- | --- |
| #34 | Wave 1: three receipted studies (declared-style 0/7 null, divisiveness no-free-lunch, demographic mostly-null), ported word-type/three-corpus receipts, three flagship figures, `docs/THESIS_AND_EVIDENCE.md`, two-audit doc reconciliation, public ceiling explainer |
| #35 | Notebook refresh: thesis-in-one-screen at the top of all three public notebooks, receipted follow-ups section, immutable tag `humor-genome-wave2-v10` |
| #36 | Publication record: wave2 v15 / Open Controls v4 / ceiling v2 (at the time; superseded to v4 by #37) verified terminal + read back; doc version bumps |
| #38 | Adversarial referee round (methods + consistency): Spearman–Brown withheld for non-positive r, Welch t on per-word gaps (9→2/4,997), underpowered labels with receipted power analyses, ranked noise-lists removed, exact test pins; wave2 notebook v16 pushed and read back |
| #37 | `ceiling_demo/` ported into the repo with a deterministic static build and tests; ceiling v4 pushed from the repo and byte-verified; this log |

## Known caveats that are not hidden

- The v0.8.0 precompletion release manifest listed `dist/.gitignore` in its `python_assets` map,
  although GitHub correctly uploaded only the wheel, sdist, release manifest, and release notes.
  The four public asset hashes were independently verified, and the workflow now requires exactly
  one wheel and one sdist. Do not mutate the historical release to hide this record.
- The public v0.8.0 image passed anonymous pull, provenance/SBOM, labels, and hardened standalone
  API runtime checks. No v0.8.0 Kubernetes cluster apply is claimed.
- The last live Kubernetes apply proof is the historical v0.7.1 disposable local `kind` run in
  [`jestry_out/v0_7_1_kind_smoke.json`](jestry_out/v0_7_1_kind_smoke.json). It is not hosted or
  production evidence.
- No hosted public API, hosted production cluster, completed writer/audience trial,
  native-language human review, rights-cleared human multimodal cohort, or public DOI is claimed.
- The competition deadline passed and no Build with Gemma competition submission is claimed.

## Legitimate continuation lanes

All remaining work is tracked under the
[`Post-closeout research and ecosystem`](https://github.com/aidonerightcorp/humorvibes-jestry/milestone/2)
milestone.

| Lane | Issue | Start only when | Completion evidence |
| --- | --- | --- | --- |
| Writer crossover pilot | [#3](https://github.com/aidonerightcorp/humorvibes-jestry/issues/3) | Ethics/IRB determination, consented writers, audience recruitment, and preregistration are real | Privacy-minimized observed bundle, blinded analysis, uncertainty, attrition, adverse events, and claim-gated receipt |
| Human multimodal benchmark | [#4](https://github.com/aidonerightcorp/humorvibes-jestry/issues/4) | Rights-cleared drawings/captions and consent/rating records exist | Passing human-cohort preflight, leakage audit, identical held-out arms, human results, and limitations |
| Native-language fixtures | [#5](https://github.com/aidonerightcorp/humorvibes-jestry/issues/5), [#20-#26](https://github.com/aidonerightcorp/humorvibes-jestry/issues?q=is%3Aissue%20state%3Aopen%20label%3Amultilingual) | A native/fluent reviewer can attest to one language and one form | Rights evidence, immutable fixture hashes, at least 20 positives and 20 hard negatives, error report, and one-language PR |
| DOI publication | [#9](https://github.com/aidonerightcorp/humorvibes-jestry/issues/9) | A repository owner is ready to publish through Zenodo | Real public record, DOI resolution, deposited-file hashes, and anonymous verification receipt |
| Streaming generation | [#7](https://github.com/aidonerightcorp/humorvibes-jestry/issues/7) | A concrete integrator needs it | Bounded protocol, disconnect/cancellation, backpressure, secret-safe errors, fake and live-gated tests |
| Vector storage | [#8](https://github.com/aidonerightcorp/humorvibes-jestry/issues/8) | A concrete storage target and user decision are named | Model/dimension identity, no-network fake, backend conformance, migration behavior, and receipts |
| Real deployment overlay | [#10](https://github.com/aidonerightcorp/humorvibes-jestry/issues/10) | Registry, cluster, ingress, secret manager, egress, DNS, and TLS target are named | Digest-pinned apply, rollout and live API checks, failure/cleanup evidence, and explicit hosted/local scope |

If the required external evidence is not available, do not close the issue with generated or model
substitutes. A useful maintenance audit, clarified protocol, or clean negative result is preferable
to fabricated completion.

## Pull-request operating procedure

For a bounded change:

1. Re-read the relevant issue, `CONTRIBUTING.md`, and the nearest domain document.
2. State the user, decision, baseline, changed artifact, primary metric, evidence level, and
   limitations before implementation.
3. Create `agent/<short-scope>` from current `main` after confirming a clean worktree.
4. Edit only in-scope source files. Preserve unrelated user changes and generated evidence.
5. Run the focused tests, then the full locked suite and `git diff --check`.
6. Add or update compact fixtures and receipts when behavior or a claim changes.
7. Inspect the complete diff and secret-scan any live-provider output.
8. Commit intentionally, push the branch, and open a pull request with commands and results.
9. Require every CI job to pass before merge. Do not bypass checks because local tests passed.
10. After any public publication, independently read back anonymous pages, terminal notebook/job
    state, release assets, image digests, and manifest hashes before claiming completion.

The minimum general verification is:

```bash
uv sync --frozen --extra api --extra dev
uv run --frozen pytest -q
uv run --frozen humorvibes adversarial
git diff --check
```

Use focused commands from `CONTRIBUTING.md` for notebook, taxonomy, Open Controls, source,
provider, human-study, or deployment changes.

## Definition of done for Claude Code

A future task is done only when:

- the requested behavior exists without placeholders or silently skipped branches;
- affected tests and end-to-end paths pass;
- evidence scope is stated honestly;
- rights, consent, privacy, and secret boundaries pass;
- generated artifacts are rebuilt from source rather than hand-edited;
- public or remote state is independently read back when publication is in scope;
- documentation names the problem, solution, result, use, limitation, and exact next action;
- changes are in a scoped public pull request with green CI;
- no required human, owner-account, legal, or named-environment action is represented as completed
  by software alone.

If there is no evidence-bearing continuation available, the correct handoff result is: the project
remains formally closed, maintained, reproducible, and ready for a real contributor—not
perpetually expanded by synthetic demonstrations.
