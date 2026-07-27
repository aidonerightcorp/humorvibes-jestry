# Semantic provider and retrieval-quality matrix

## Executive summary

An embedding endpoint can be configured yet unreachable, reachable yet schema-incompatible, or
compatible yet poor on the project task. HumorVibes now measures those states separately and
publishes failed arms alongside successful ones. The first live matrix executed five exact
model/interface combinations on two byte-identical retrieval tracks. All five completed, across
two independently implemented servers: Ollama 0.24.0 and Hugging Face Text Embeddings Inference
(TEI) 1.9.0.

EmbeddingGemma had the highest MRR and nDCG@10 on both proxy tasks in this one hardware/run
cohort. That is evidence for these frozen retrieval relations, not a general model recommendation
and not evidence about funniness. The checked-in receipt deliberately makes no default selection.

## What was measured

| Track | Rows | Relation | Languages | Evidence boundary |
| --- | ---: | --- | --- | --- |
| masked hard frames | 300 queries + 300 documents | deterministic generator lineage, with same-frame and same-context negatives | English (`und` in the original rows) | no human relevance or funniness labels |
| cross-language proverbs | 490 queries + 490 documents | historical foreign-proverb/English-translation pairs | da, de, es, fr, it, nl, pt → en | historical editorial alignment; no modern native review |

The second track is a deterministic, balanced subset of Henry G. Bohn's *A Polyglot of Foreign
Proverbs*, [Project Gutenberg ebook 51090](https://www.gutenberg.org/ebooks/51090). Gutenberg
marks the book public domain in the USA. The manifest retains that jurisdiction limit, the input
snapshot SHA-256, selection method, per-language split counts, and exact output digest.

Every result reports MRR, Recall@1/5/10, nDCG@10, deterministic query-bootstrap 95% intervals,
split/language slices, failure counts, batch latency, throughput, and query/document/qrel hashes.

## Live results on 2026-07-27

The host had 16 x86-64 CPUs and an NVIDIA RTX 3060 12 GB. Ollama reported its models fully on the
GPU. TEI used its pinned CPU image and float32 ONNX Runtime. Throughput is therefore
implementation- and hardware-specific.

| exact combination | dims | cross-language MRR (95% CI) | hard-frame MRR (95% CI) | cross / hard texts/s | licence recorded by the run |
| --- | ---: | ---: | ---: | ---: | --- |
| Ollama native · `embeddinggemma:latest` | 768 | **0.8977** [0.8728, 0.9206] | **0.8131** [0.7777, 0.8486] | 97.8 / 80.1 | Gemma Terms, 2025-03-24 |
| Ollama native · `qwen3-embedding:0.6b` | 1,024 | 0.8710 [0.8441, 0.8945] | 0.4797 [0.4349, 0.5215] | 86.2 / 63.6 | **NOASSERTION in local metadata** |
| Ollama native · `paraphrase-multilingual:latest` | 768 | 0.8696 [0.8434, 0.8949] | 0.5751 [0.5320, 0.6192] | **162.8 / 130.8** | Apache-2.0 in local metadata |
| Ollama OpenAI-compatible · `embeddinggemma:latest` | 768 | **0.8977** [0.8733, 0.9219] | **0.8131** [0.7756, 0.8483] | 103.3 / 87.6 | Gemma Terms, 2025-03-24 |
| TEI OpenAI-compatible · `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 0.8074 [0.7776, 0.8375] | 0.5301 [0.4872, 0.5753] | 53.5 / 29.3 | Apache-2.0 |

The native and OpenAI-compatible routes to the exact same EmbeddingGemma digest produced
identical point metrics on both tracks. Their independently resampled interval endpoints and
single-run throughput varied slightly; neither difference is a quality result.

The hardest language slice for EmbeddingGemma was Danish (MRR 0.6288), while the other six ranged
from 0.8984 to 0.9594. That gap could reflect digitization, historical translation style, model
coverage, or source composition. It should trigger native review and error analysis, not a claim
about Danish language quality.

## Reproduce or extend it

The machine-readable inputs and result are:

- [`provider_matrix_live_v1.json`](../provider_matrix_live_v1.json): exact model/server digests,
  request schemas, dimensions, timeouts, hardware declarations, and frozen benchmark digests;
- [`provider_matrix_live_v1.json`](../jestry_out/provider_matrix_live_v1.json): aggregate live
  receipt with no vectors, text bodies, or credentials;
- [`crosslingual_retrieval_v1`](../jestry_out/crosslingual_retrieval_v1): balanced public-domain
  query/document/qrel bytes and manifest;
- [`provider_matrix.py`](../humorvibes/provider_matrix.py): fail-closed runner;
- [`provider-matrix-live.yml`](../.github/workflows/provider-matrix-live.yml): opt-in self-hosted
  workflow. It will not run on ordinary hosted CI or silently download models.

With matching services already running:

```bash
humorvibes provider-matrix \
  --spec provider_matrix_live_v1.json \
  --out /tmp/provider-matrix-live.json
```

For another provider, copy the spec to a new version, give the run an immutable model revision and
server artifact, record its licence and real dimensions, and keep both benchmark digests fixed.
Never overwrite this receipt when the server, model, quantization, preprocessing, task bytes, or
hardware class changes.

## What this still does not answer

- The qrels do not say which text is funny, helpful to a writer, or preferred by an audience.
- The cross-language source is historical and European-language-heavy; native-reviewed fixtures
  remain a separate contribution gate.
- One accelerator run is not a stable latency benchmark. Repeat runs with warm/cold and
  concurrency cohorts before capacity planning.
- A model with missing or ambiguous licence metadata must not become the product default even if
  its endpoint works.
- Retrieval quality does not validate clustering, generation, safety, cultural fit, or downstream
  application utility.
