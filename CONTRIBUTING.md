# Contributing to Humor Genome Wave 2

Contributions are welcome across research design, data provenance, multilingual taxonomy,
statistics, model instrumentation, documentation, and reproducibility. A contribution does not
need to make a metric go up. A clean negative result, a removed confound, or a smaller reliable
reproduction is valuable here.

Read [`PROJECT_STATUS.md`](PROJECT_STATUS.md) before starting. Choose a bounded item from
[`ROADMAP.md`](ROADMAP.md), or open a research proposal using the repository issue template.
Read [`docs/PRODUCT_AND_RESEARCH_USE_CASES.md`](docs/PRODUCT_AND_RESEARCH_USE_CASES.md) when a
change affects a writer, audience, academic, or product claim; it defines the human-evidence gate
and the minimum study fields.

## Licensing boundary

Repository code and documentation are Apache-2.0. Unless explicitly marked otherwise, an
intentional code or documentation contribution is submitted under that licence. Dataset records
remain separate: imported Wave 2 rows retain their per-record licences, while only the
project-controlled Open Controls payload is dedicated under CC0-1.0. Never use CC0 to launder an
import, transcription, model output, or contribution whose rights are unclear.

## Local setup

Python 3.10 through 3.14 are supported and clean-install tested. The package declares
`>=3.10`; each newly released Python version must pass the same isolated-wheel matrix before it
is added to the supported range.

```bash
git clone https://github.com/aidonerightcorp/humorvibes-jestry.git
cd humorvibes-jestry
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
humorvibes adversarial
```

When dependency metadata changes, refresh both locks and review the diff before building:

```bash
uv lock
uv export --frozen --extra api --extra telemetry --no-dev --no-emit-project --no-hashes \
  --output-file requirements-api.lock
```

For API or deployment changes, also run:

```bash
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml -f compose.ollama.yaml config --quiet
python3 verify_deployment.py --docker \
  --kustomize-image registry.k8s.io/kubectl:v1.36.2 \
  --helm-image alpine/helm:4.2.0@sha256:af08f75a3130d666a50b9fc150f40987ef20b885cf67659aabf4b83a5f2c5501
```

Do not commit provider keys, literal Kubernetes Secrets, model caches, or corpus rows as
integration fixtures. Use malformed stub responses for adversarial tests and keep live-provider
diagnostics opt-in.

The public release verifier does not require the private local corpus:

```bash
kaggle datasets download -d taylorsamarel/humor-genome-wave2 \
  --unzip -p kaggle_wave2_public
python3 verify_wave2_release.py --root kaggle_wave2_public
```

Audit both public GitHub/Kaggle releases without mutating either service:

```bash
python3 tools/public_release_audit.py --out jestry_out/public_surface_audit.json
python3 tools/clean_install_smoke.py --python 3.12
```

The live audit checks anonymous visibility, Kaggle readiness, terminal notebook state, public tag
resolution, and freshly downloaded manifest hashes. Use `--offline` only for a no-network local
receipt/schema check; an offline pass is not publication evidence.

Rebuilding the 3.16-million-row inventory or running Gemma locally is optional and substantially
heavier. The public Kaggle notebook is the reference environment for the canonical model run.

## Evidence rules

Every pull request must preserve these boundaries:

- Model surprisal is not funniness.
- A source-specific score is not a universal human grade.
- A candidate source specification is not harvested data.
- A local result is not a public result.
- A successful file upload is not a verified executable release.
- Research-only, noncommercial, conflicting, and unclassified text must not enter the public
  verbatim payload.
- Point estimates must not replace uncertainty when the controlling result includes an interval.
- Negative results and known confounds stay visible.

If a claim changes, update the code that computes it, the test or receipt that checks it, and the
nearest reader-facing document. Do not edit a result into prose without an executable path back
to the underlying rows.

## Contribution lanes

### Documentation or reproducibility

These are good first contributions. Fix a broken link, reduce setup friction, add a focused test,
make an error message actionable, or reproduce one receipt on another platform. Run the full test
suite and include the command output in the pull request.

### Taxonomy or language coverage

Add structural form rules only with positive and negative fixtures from the target language.
Report precision-oriented coverage by language before and after the change. Keep lexical domain
labels separate from structural form and source-declared style. See
[`docs/EXPANSION_GUIDE.md`](docs/EXPANSION_GUIDE.md). Native-language changes also follow
[`docs/NATIVE_LANGUAGE_CONTRIBUTIONS.md`](docs/NATIVE_LANGUAGE_CONTRIBUTIONS.md) and must pass
`humorvibes native-fixture-validate`; one pull request may cover only one language and form.

### Source acquisition

Verify the upstream source, schema, licence, and a real response before registering it. Preserve
per-row provenance and upstream labels. Ambiguous redistribution rights are acceptable for local
research inventory only; the exporter will and must fail closed.

Start with `python3 source_spec_preflight.py`. It runs from committed fixtures without a network
connection or corpus write. Use `--live` only after the fixture passes, and include the body-free
receipt in the pull request. The exact workflow and failure gates are in
[`docs/EXPANSION_GUIDE.md`](docs/EXPANSION_GUIDE.md).

Never commit multi-hundred-megabyte generated corpus payloads. Commit the source specification,
parser, fixtures, tests, compact receipts, and documentation. Publish an updated public payload
only through the release process.

### New experiment

State the hypothesis, unit of analysis, split strategy, controls, primary metric, uncertainty
method, stopping rule, and expected receipt before running the expensive arm. Keep exploratory
and confirmatory results visibly distinct. Prefer group-held-out splits whenever rows share a
contest, source, author, prompt, or other context.

For a real-world pilot, also define the user, decision being improved, existing baseline, consent
and retention policy, adverse outcomes, opt-out path, and exact claim gate. Product usage logs are
not automatically research consent, and demographic proxies must not substitute for audience
members' explicit preferences.

### Embedding or provider benchmark

Start from [`provider_matrix_live_v1.json`](provider_matrix_live_v1.json) and
[`docs/PROVIDER_MATRIX.md`](docs/PROVIDER_MATRIX.md). A comparable live run must pin the model
revision or digest, server implementation and version, exact server artifact, request schema,
embedding dimension, benchmark digests, and hardware. Record model-licence metadata even when it
is `NOASSERTION`; availability through a provider is not evidence of redistribution rights.

Never place a provider key in the specification or receipt. Use environment-variable references,
run the built-in secret scan, and preserve failed arms in the result. Do not overwrite an existing
receipt when model bytes, server bytes, hardware, benchmark inputs, or the matrix schema change;
create a newly versioned specification and receipt instead.

```bash
humorvibes provider-matrix \
  --spec provider_matrix_live_v1.json \
  --out /tmp/provider_matrix_live_v1.json
```

Provider reachability is only a compatibility check. A quality claim requires the frozen tracks,
their input digests, interval estimates, and the limitations recorded with the receipt.

## Required checks

For every change:

```bash
python3 -m pytest -q
git diff --check
```

For Wave 2 notebook changes:

```bash
python3 wave2_notebook/build_wave2_notebook.py
python3 -m pytest -q tests/test_wave2.py
git diff --exit-code -- wave2_notebook/humor_genome_wave2.ipynb
```

For taxonomy changes:

```bash
python3 style_taxonomy.py selftest
python3 -m pytest -q tests/test_wave2.py
```

For a rebuilt public payload:

```bash
python3 build_kaggle_export.py --per-family 12000 \
  --corpora-dir corpora --out-dir kaggle_wave2 \
  --metadata-template wave2_dataset/dataset-metadata.json
python3 verify_wave2_release.py --root kaggle_wave2
```

For Open Controls generator, schema, API, or notebook changes:

```bash
python3 build_open_controls.py --reference-dir corpora
python3 verify_open_controls_release.py --root kaggle_open_controls
python3 open_controls_notebook/build_open_controls_notebook.py
python3 -m pytest -q tests/test_open_controls.py
git diff --exit-code -- open_controls_notebook/humor_genome_open_controls.ipynb
```

Human-original data contributions use the contract in `docs/OPEN_CONTROLS.md`. Do not commit
identity fields or fabricate ratings, consent, authorship attestations, or populated human lanes.

Publishing to Kaggle requires the maintainer's credentials and is not expected from an outside
contributor.

## Pull-request checklist

- Explain the research or maintenance problem in plain language.
- List every generated or public artifact affected.
- Include the exact verification commands and results.
- Add regression fixtures for parser, taxonomy, selection, or claim changes.
- State licence and provenance for every new source.
- State limitations and negative findings.
- Keep unrelated generated files and local caches out of the commit.
- Do not move an immutable source tag. A new executable release receives a new tag.

The pull-request template mirrors this checklist so reviewers can trace a change from claim to
code to receipt.
