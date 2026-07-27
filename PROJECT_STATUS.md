# Project status

Humor Genome Wave 2 is a public, reproducible research project. The Build with Gemma: Humor
Genome NYC deadline has passed, and **no competition submission is claimed**. The work continues
as an open project whose current evidence can be read, rerun, challenged, and extended.

## Public release

| Surface | Canonical location | Current contract |
| --- | --- | --- |
| Executable study | [Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study) | Public; version 14 is COMPLETE and is the canonical executable write-up |
| Research dataset | [Kaggle dataset](https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2) | Public version 7, ready; only explicitly redistributable text is included |
| Source and evidence | [GitHub repository](https://github.com/aidonerightcorp/humorvibes-jestry) | Public; builders, tests, immutable notebook source tags, and receipts |
| Open causal controls | [Kaggle dataset](https://www.kaggle.com/datasets/taylorsamarel/humor-genome-open-controls) and [Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/humor-genome-open-controls-causal-design-lab) | Public dataset version 4 is ready; public notebook version 3 is COMPLETE; 120,000 deterministic CC0 procedural rows plus a frozen hard-retrieval track |

The notebook uses the immutable source tag `humor-genome-wave2-v9`. GitHub `main` may move as
documentation and follow-up research improve; the code executed by the public notebook cannot
move underneath an existing run. The separate control release is pinned by
`humor-genome-open-controls-v2`; its publication receipt records the dataset generator commit,
public versions, downloaded hashes, and terminal notebook status.

## Application and deployment extension

The repository now also contains a separate `humorvibes-research` 0.6.0 application layer:

- an importable Python SDK and a schema-first FastAPI service;
- authenticated native Ollama (local or cloud) and OpenAI-compatible generation;
- validated hash, Ollama, OpenAI-compatible, and optional sentence-transformers embeddings;
- exact model allowlists, bounded requests/responses, secret-safe errors, Prometheus text metrics,
  and a deterministic adversarial audit;
- a typed dependency-free remote client and checked-in OpenAPI contract for application
  integration;
- a strict, privacy-minimized writer-study protocol, synthetic contract fixture, paired analyzer,
  writer-clustered uncertainty, evidence ladder, and local claim-gated receipt;
- a multi-stage non-root Docker image, hardened offline/local-Ollama/cloud-Ollama Compose profiles,
  a two-replica non-root Kubernetes Kustomize base, and a configurable Helm chart.

The local image was built and launched with a read-only root filesystem; its readiness, capability,
embedding, and signal-boundary checks passed. Compose rendering, the Kubernetes security/probe
contracts, a kubectl 1.36.2 Kustomize render, and a Helm 4.2.0 lint/render also passed. The
machine-readable receipt is
[`jestry_out/deployment_validation.json`](jestry_out/deployment_validation.json).

Those statements do **not** claim a public container-registry image, a hosted public API, a live
Kubernetes cluster deployment, or a live LLM/semantic-embedding quality result. The Kubernetes
manifests were statically validated because no cluster client is installed in the verification
environment. This extension does not alter the immutable Kaggle notebook or its measurements.

## What is complete

- The public dataset is deterministic, source-stratified, and deny-first on redistribution
  rights. It contains 121,670 text rows, 7,913 aligned phrase pairs, 2,581
  expectation/violation frames, a full-corpus census, an export summary, and a SHA-256 manifest.
- The canonical notebook verifies all six mounted payloads before analysis, loads its attached
  Gemma 2 checkpoint, runs the pinned instrument check, and displays the controlling statistical
  results and limitations.
- The full local inventory contains 3,164,600 rows across 217 source families and 62 language
  labels. Text that is research-only, noncommercial, or unclassified remains out of the public
  verbatim payload.
- The form study reports uncertainty rather than ranking bare means: 0 of 10 joke-form intervals
  separate from the proverb control, and all 10 overlap it.
- The caption study holds out entire contests. Its median within-contest Spearman correlation is
  0.1555, compared with a measured text-only bound of 0.4110 and label ceiling of 0.8262.
- The release has source-controlled dataset and notebook metadata, deterministic notebook
  generation, automated tests, semantic release checks, and a machine-readable publication
  receipt at [`jestry_out/wave2_publication.json`](jestry_out/wave2_publication.json).
- The notebook opens with the problem, proposed exploration, controlling results, use cases, and
  limitations, includes a sourced predictive-processing-to-product evidence map, and emits a
  machine-readable executive-summary artifact. The supporting notebook
  map is documented in [`docs/NOTEBOOKS.md`](docs/NOTEBOOKS.md).
- Open Controls adds a separate 120,000-row four-arm corpus, strict data/human/model schemas,
  grouped splits, exact and long-phrase overlap checks, easy and entity-masked hard retrieval
  qrels, a bounded SDK/API, a standalone verifier, and a public-notebook builder. A fresh
  anonymous Kaggle download passes all 14 semantic/provenance gates, and notebook v3 completed
  against all 24 manifested files.
  It contains no human-authored or human-rated rows. See
  [`jestry_out/open_controls_publication.json`](jestry_out/open_controls_publication.json).
- The multimodal lane now has an executable 30-contest, 600-caption procedural SVG positive
  control with image-identity gates and exactly comparable text/image/fusion arms. Its high
  fusion score is expected from the synthetic generator and is explicitly not human evidence.
  See [`docs/MULTIMODAL_BENCHMARK.md`](docs/MULTIMODAL_BENCHMARK.md).

## What is deliberately not claimed

- `S` is Gemma surprisal, not funniness.
- Source-specific ratings, votes, scores, and labels are not interchangeable human grades.
- The public slice is stratified and rights-filtered, not a random sample of the full inventory.
- Keyword domains are hypotheses; most form rules are English-biased; source-declared style is a
  separate axis.
- A weak text-only caption result does not bound a multimodal system that can see the drawing.
- Public artifacts do not retroactively create a competition submission.
- “Release complete” does not mean the research question is settled. The negative results are a
  starting point for better experiments.

## How to verify the release

```bash
git clone https://github.com/aidonerightcorp/humorvibes-jestry.git
cd humorvibes-jestry
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
python3 wave2_notebook/build_wave2_notebook.py

kaggle datasets download -d taylorsamarel/humor-genome-wave2 \
  --unzip -p kaggle_wave2_public
python3 verify_wave2_release.py --root kaggle_wave2_public

kaggle datasets download -d taylorsamarel/humor-genome-open-controls \
  --unzip -p kaggle_open_controls_public
python3 verify_open_controls_release.py --root kaggle_open_controls_public
kaggle kernels status taylorsamarel/humor-genome-open-controls-causal-design-lab
```

The local corpus is not required to read or verify the public release. It is required only to
rebuild the public slice from the complete research inventory.

## What people can use this for

The corpus, notebook, SDK/API, and deployment surfaces can support precedent search and candidate
variation for writers, reproducible experiment design for academics, evidence-boundary teaching,
provenance audits, and consent-based application prototypes. They do not replace a comedian's
selection, an audience's response, a native speaker's judgment, or a preregistered human study.

[`docs/PRODUCT_AND_RESEARCH_USE_CASES.md`](docs/PRODUCT_AND_RESEARCH_USE_CASES.md) defines the
persona-specific workflows, minimum study schema, success measures, and claim gates. The
highest-value next experiment is a preregistered within-writer crossover trial with blinded,
opt-in audience evaluation—not a larger model-only ranking. The runnable local contract is in
[`docs/REAL_WORLD_STUDY_WORKBENCH.md`](docs/REAL_WORLD_STUDY_WORKBENCH.md); its synthetic demo is
explicitly not evidence of advantage.

## Where help is useful

Start with [`ROADMAP.md`](ROADMAP.md) for prioritized work, [`CONTRIBUTING.md`](CONTRIBUTING.md)
for the evidence and pull-request contract, and [`docs/EXPANSION_GUIDE.md`](docs/EXPANSION_GUIDE.md)
for exact extension paths. The best near-term contributions are multimodal caption baselines,
human-annotated setup/frame/punchline data, native-form rules for under-covered languages,
licence-verified sources, embedding-model bake-offs on frozen multilingual fixtures, live provider
compatibility checks, and small reproducibility improvements.

## Licensing state

Repository code and documentation are Apache-2.0. The project-controlled Open Controls payload is
CC0-1.0 to the extent contributors hold the relevant rights. The Wave 2 dataset remains a separate
mixed-provenance artifact: each row retains its recorded source licence, and the exporter admits
text only when redistribution is explicit. Neither repository access nor the Open Controls
dedication relicenses imported records, model weights, or third-party assets.
