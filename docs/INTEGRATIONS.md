# Integration and model support

*Role: which providers and model IDs are allowlisted, and what each live check actually reached. Audience: integrators.*

The integration layer has one rule: a configured provider is a capability, not a fallback. Every
request selects an exact allowlisted model ID, and malformed or unavailable upstreams fail with a
sanitized structured error instead of silently switching models or inventing offline output.

## LLM providers

| Provider | Model ID shape | Authentication | JSON mode | Thinking flag | Teacher-forced logprobs |
| --- | --- | --- | --- | --- | --- |
| Offline | `offline` | none | no generation | no | no |
| Ollama native | `ollama:<model>` | optional `OLLAMA_API_KEY` Bearer | yes | yes | generation endpoint only; not claimed as measured S/R/E |
| OpenAI-compatible | `openai:<model>` | configured Bearer key | yes | provider-specific, not exposed | no |
| Transformers research provider | legacy signal path | model platform credentials as needed | provider-specific | provider-specific | yes when the existing instrument says `measured=true` |

Ollama can also expose OpenAI-compatible routes, but HumorVibes uses its native `/api/generate`
and `/api/embed` routes for the Ollama registry so usage fields and batch embedding behavior remain
explicit. OpenAI-compatible endpoints use `/chat/completions` and `/embeddings`. Ollama documents
its compatibility surface at
[OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility).

## Embedding providers

| Provider | Model ID shape | Semantic | Batch | Dimension handling |
| --- | --- | --- | --- | --- |
| Deterministic hash | `hash:128` | no; lexical only | yes | fixed at 128 |
| Ollama native | `ollama:<model>` | model-dependent | yes via `/api/embed` | optional request dimension; observed dimension bound per model instance |
| OpenAI-compatible | `openai:<model>` | model-dependent | yes | optional request dimension; indexed rows reordered and validated |
| sentence-transformers | `sentence-transformers:<model>` | model-dependent | yes | model-defined |

The built-in Ollama catalog includes `embeddinggemma`, `qwen3-embedding`, `all-minilm`,
`nomic-embed-text`, `mxbai-embed-large`, and `bge-m3`; it is an allowlist, not a claim that all six
are installed or equally good. Ollama's embedding guide specifically recommends
`embeddinggemma`, `qwen3-embedding`, and `all-minilm`, says to use the same model for indexing and
querying, and notes that `/api/embed` returns L2-normalized vectors. See
[Ollama embeddings](https://docs.ollama.com/capabilities/embeddings) and the
[`/api/embed` reference](https://docs.ollama.com/api/embed).

Add or narrow models with environment variables:

```bash
export HUMORVIBES_OLLAMA_EMBED_MODELS=embeddinggemma,qwen3-embedding,all-minilm
export HUMORVIBES_EMBEDDING_DEFAULT=ollama:embeddinggemma
humorvibes capabilities
humorvibes embed --model ollama:embeddinggemma "comic timing" "timing a joke"
```

For local sentence-transformers:

```bash
python3 -m pip install -e ".[local-embeddings]"
export HUMORVIBES_SENTENCE_TRANSFORMER_MODELS=sentence-transformers/all-MiniLM-L6-v2
export HUMORVIBES_EMBEDDING_DEFAULT=sentence-transformers:sentence-transformers/all-MiniLM-L6-v2
humorvibes doctor --live
```

Model downloads and licences remain the operator's responsibility. A model appearing in the
capability list means it was configured, not downloaded or live; `humorvibes doctor --live` is the
explicit availability check.

For a receipt across every configured model, use `humorvibes provider-audit`. Offline mode makes
no provider request and proves only the deterministic `hash:128` operation. `--live` separately
records provider reachability and a bounded operation attempt while leaving
`quality_validated=false`. The checked-in 2026-07-27 live receipt is deliberately negative: the
hosted ollama.com endpoint's version route was reachable, generation returned HTTP 410, all six
semantic embedding operations returned HTTP 401, and only `hash:128` executed. That is a
credential/service-state finding, not a semantic-model comparison. This run targeted the hosted
endpoint; the local-server benchmark that completed all arms is docs/PROVIDER_MATRIX.md.

## Existing research-tool integration

The shared transport now backs the API/SDK and the active Ollama paths in `mesh_cli.py`,
`gemma_client.py`, `jestry.py`, `gemma4_nll.py`, `llm_panel.py`, `precedent.py`,
`word_taxonomy.py`, `embedding_bakeoff.py`, `semantic_load.py`, and `incongruity_study.py`.
That removes conflicting key behavior, retired singular embedding endpoints, model-agnostic cache
keys, and unvalidated vector parsing without replacing the canonical research algorithms.

`mesh_signals.py` itself remains byte-identical because its SHA-256 is embedded in a published
Kaggle receipt. `humorvibes/signal_providers.py` extends its provider protocol with authenticated
generation instead of rewriting that historical instrument. The Kaggle Wave 2 notebook remains
pinned to its immutable source tag and attached model. These deployment integrations are an
extension surface, not a retroactive change to published results.

## App patterns

Use the SDK when the application and HumorVibes share a Python process. Use the API when the app
needs language independence, independent scaling, or network isolation. In both cases:

1. Discover exact model IDs with `capabilities()` or `GET /v1/capabilities`.
2. Send a model ID, never a provider URL.
3. Store `model_id`, `provider`, dimensions, and output digest with downstream artifacts.
4. Treat similarity as a retrieval clue, not proof of originality or equivalence.
5. Treat generation/judging as model output, not measured laughter.

The standard-library client in `examples/api_client.py` is dependency-free. The direct SDK example
in `examples/sdk_client.py` runs offline and is suitable for a CI smoke test.
The packaged `HumorVibesClient` and `examples/remote_client.py` provide the same dependency-free
HTTP surface for Python applications, while `docs/openapi.json` is the versioned language-neutral
contract. `GET /v1/research/study-template` exposes the writer-study schema for discovery but has
no upload counterpart; sensitive study operations and privacy-minimized analysis stay local.

Provider reachability and model quality are different gates. Before recommending an embedding
model, benchmark it on frozen relevance judgments for the intended languages and forms. Before
claiming generated material helps writers or audiences, run the consented held-out human tests in
[`REAL_WORLD_STUDY_WORKBENCH.md`](REAL_WORLD_STUDY_WORKBENCH.md).
