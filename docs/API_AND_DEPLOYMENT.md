# API and deployment guide

HumorVibes now has one application-facing service layer that can be imported as a Python SDK,
served through FastAPI, built as a non-root container, run with Docker Compose, or scheduled on
Kubernetes. It is separate from the immutable Kaggle measurement path: deploying this service
does not change the published study or turn model output into human funniness evidence.

## Choose a runtime

| Runtime | Default behavior | Network/model required | Best for |
| --- | --- | --- | --- |
| Python SDK | `offline` LLM, `hash:128` embedding | No | embedding an app directly |
| Local API | same | No | development and contract testing |
| Docker/Compose | same, bound to `127.0.0.1:8080` | No | reproducible app integration |
| Compose + local Ollama | Gemma generation + EmbeddingGemma | Pulls local models | workstation or single server |
| Compose + Ollama cloud | authenticated Ollama native API | `OLLAMA_API_KEY` | hosted inference without local weights |
| Kubernetes | two offline/hash API replicas, ClusterIP only | No | a secure base to customize |
| Helm | configurable version of the Kubernetes base | No by default | repeatable environment-specific installation |
| Envoy Gateway example | TLS 1.3, edge API-key identity, local/global rate limits, trace context | TLS/API-key Secrets; Redis | named production edge contract |

The offline hash backend is deterministic token hashing for integration tests and lexical
retrieval. It is explicitly marked `semantic: false`; it is not a substitute for a semantic
embedding model.

## Python SDK

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[api]"
python3 examples/sdk_client.py
```

The smallest application integration is:

```python
from humorvibes import HumorVibesService

service = HumorVibesService()
vectors = service.embed(["setup", "punchline"], model_id="hash:128")
matrix = service.similarity(["Even experts slip."], ["A master can blunder."])
```

Importing `humorvibes` never downloads a model or makes a network request. Live providers are
called only when the application invokes a live-model method or enables a live readiness probe.

For a Python application calling an independently deployed service, use the packaged remote
client. It uses the same bounded, redirect-free transport as the provider adapters and does not
print its API key:

```python
from humorvibes import HumorVibesClient

client = HumorVibesClient.from_env()
capabilities = client.capabilities()
matches = client.similarity(["expert mistake"], ["grandmaster blunder"])
study_contract = client.study_template()  # discovery only; human rows stay local
controls = client.open_controls_sample(count=4, arm="surprising_resolved", split="test")
```

Set `HUMORVIBES_URL` and, when enabled on the server, `HUMORVIBES_API_KEY`. The complete executable
example is [`examples/remote_client.py`](../examples/remote_client.py).

## Local API

```bash
python3 -m pip install -e ".[api]"
humorvibes doctor
humorvibes-api
```

Then, from a second shell:

```bash
curl --fail http://127.0.0.1:8080/health/live
curl --fail http://127.0.0.1:8080/v1/capabilities
curl --fail -X POST http://127.0.0.1:8080/v1/embed \
  -H 'Content-Type: application/json' \
  -d '{"texts":["comic timing","timing a joke"]}'
python3 examples/api_client.py
```

Interactive OpenAPI documentation is at `http://127.0.0.1:8080/docs` while the server is
running. Request and response schemas reject unknown fields; callers cannot override provider
hosts, keys, or model allowlists per request.

Non-Python clients can generate code from the checked-in
[`docs/openapi.json`](openapi.json) contract. Rebuild it deterministically with:

```bash
humorvibes openapi --out docs/openapi.json
```

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health/live` | process liveness; deliberately does not call a model |
| GET | `/health/ready` | configuration readiness; live probes only when explicitly enabled |
| GET | `/version` | package version |
| GET | `/metrics` | Prometheus text counters; protected when API auth is enabled |
| GET | `/v1/capabilities` | exact allowlisted models, formats, limits, and truth boundaries |
| POST | `/v1/generate` | generic allowlisted LLM generation |
| POST | `/v1/humor/generate` | format-constrained candidate generation |
| POST | `/v1/judge` | strict JSON-object model response parsing |
| POST | `/v1/embed` | validated batch embeddings |
| POST | `/v1/similarity` | bounded cosine-similarity matrix |
| POST | `/v1/signals` | existing S/R/E/B signal surface with measured state attached |
| GET | `/v1/research/study-template` | privacy-minimized writer-study contract and truth boundary; no data upload |
| GET | `/v1/open-controls/metadata` | deterministic corpus scale, licence, mechanism, and truth contract |
| POST | `/v1/open-controls/sample` | bounded procedural fixtures; no model, dataset download, or human data |

Run the study protocol and analyzer locally. The service deliberately does not accept human-study
rows over HTTP:

```bash
humorvibes study-protocol --human-observed --out protocol.json
humorvibes study-demo --out synthetic_receipt.json
humorvibes study-analyze --protocol protocol.json --bundle privacy_minimized_bundle.json
```

See [`REAL_WORLD_STUDY_WORKBENCH.md`](REAL_WORLD_STUDY_WORKBENCH.md) before collecting data.

Audit configured provider claims independently from the API readiness path:

```bash
humorvibes provider-audit --out provider-offline.json
HUMORVIBES_REQUEST_TIMEOUT=20 humorvibes provider-audit --live --out provider-live.json
```

The receipt records four separate states for every exact allowlisted model: configured, provider
reachable, operation executed, and quality validated. A reachable version endpoint is not an
executed generation, and an executed embedding is not retrieval-quality evidence. Output text is
replaced by a digest and configured keys are scanned out of the serialized receipt.

When `HUMORVIBES_API_KEY` is set, all `/v1/*` routes and `/metrics` require
`Authorization: Bearer <key>`. Health and version routes stay unauthenticated for orchestrator
probes. TLS belongs at the reverse proxy, ingress, or service mesh boundary.

### Metrics and traces

Prometheus counters remain available at `/metrics`. Set `HUMORVIBES_STATSD_HOST` to mirror only
low-cardinality request counts, status classes, errors, and duration to an external StatsD sink.
No route, request ID, prompt, response, authorization value, provider URL, or user identifier is
sent to StatsD; UDP failures are best-effort and appear in the local Prometheus output.

The production image includes the optional OpenTelemetry SDK and OTLP/HTTP exporter. Set a
per-signal traces endpoint to enable spans:

```bash
export HUMORVIBES_OTEL_TRACES_ENDPOINT=http://otel-collector.observability.svc:4318/v1/traces
export HUMORVIBES_OTEL_SERVICE_NAME=humorvibes-api
export HUMORVIBES_OTEL_SAMPLE_RATIO=0.1
```

Spans contain only method, fixed route, response status, duration, service name, and a boolean
that asserts bodies are not recorded. W3C `traceparent` context is extracted so a gateway span and
application span can join one trace; sampled responses include `X-Trace-ID`. Exporter credentials,
when required, stay in the standard `OTEL_EXPORTER_OTLP_TRACES_HEADERS` environment variable and
are never added to settings summaries or receipts. Plain HTTP exporters remain limited to local
or private-network destinations unless the operator explicitly enables insecure remote URLs.

## Docker

The public 0.7.1 image is available by its independently verified multi-architecture digest:

```bash
docker pull ghcr.io/aidonerightcorp/humorvibes-jestry@sha256:b08c221c8f47056875508088d994eff673fc1357bf9b3d4d9f5ed27efe0a02a0
gh attestation verify \
  oci://ghcr.io/aidonerightcorp/humorvibes-jestry@sha256:b08c221c8f47056875508088d994eff673fc1357bf9b3d4d9f5ed27efe0a02a0 \
  --repo aidonerightcorp/humorvibes-jestry
```

Its publication receipt records the anonymous pull, `linux/amd64` and `linux/arm64` manifests,
SLSA provenance identity, SBOM setting, OCI labels, non-root/read-only runtime, and API probe.
Use [`deploy/overlays/ghcr`](../deploy/overlays/ghcr) to render the base with
that exact digest. The overlay and Helm chart were also installed against that digest in a
disposable `kind` cluster; the complete result and cleanup receipt is
[`jestry_out/v0_7_1_kind_smoke.json`](../jestry_out/v0_7_1_kind_smoke.json).

Build and run the image directly:

```bash
docker build -t humorvibes-research:0.7.1 .
docker run --rm --read-only --tmpfs /tmp:rw,size=64m \
  -p 127.0.0.1:8080:8080 humorvibes-research:0.7.1
```

Or run the hardened Compose profile:

```bash
docker compose up --build --wait
curl --fail http://127.0.0.1:8080/health/ready
docker compose down
```

Run the combined SDK, adversarial, Compose, Kubernetes-static, and live-container verifier with:

```bash
python3 verify_deployment.py --docker \
  --kustomize-image registry.k8s.io/kubectl:v1.36.2 \
  --helm-image alpine/helm:4.2.0@sha256:af08f75a3130d666a50b9fc150f40987ef20b885cf67659aabf4b83a5f2c5501 \
  --out jestry_out/deployment_validation.json
```

Without `--docker`, the command still checks the SDK, adversarial contracts, Compose rendering,
and Kubernetes manifest structure. The optional pinned kubectl image renders the Kustomize base
without requiring a host installation or claiming that a cluster apply occurred.
The optional pinned Helm image lints and renders the chart under the same truth boundary.

With `--docker`, the verifier first rebuilds the named image from the current checkout and then
launches it. Add `--no-build` only when deliberately validating an already-built or pulled image.

The image uses a wheel-building stage, carries only runtime dependencies, runs as UID/GID 10001,
and has an in-image health check. Compose additionally drops Linux capabilities, blocks privilege
escalation, mounts a read-only root filesystem, and binds only to loopback by default. These
choices follow the general single-process container pattern in the
[FastAPI container deployment guide](https://fastapi.tiangolo.com/deployment/docker/).

Tagged releases trigger [the pinned container publication workflow](../.github/workflows/publish-container.yml).
It builds `linux/amd64` and `linux/arm64`, publishes to GHCR, attaches BuildKit provenance and an
SBOM, creates a GitHub/Sigstore provenance attestation, and prints the immutable manifest digest.
The 0.7.1 publication passed those gates and is pinned above; future versions must repeat them
before their digest enters an overlay.

### Local Ollama Compose profile

This profile starts Ollama, waits for it, pulls both models, then starts the API:

```bash
docker compose -f compose.yaml -f compose.ollama.yaml up --build --wait
curl --fail http://127.0.0.1:8080/health/ready
curl --fail -X POST http://127.0.0.1:8080/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Return one concise sentence about comic timing.","max_tokens":80}'
docker compose -f compose.yaml -f compose.ollama.yaml down
```

Override `OLLAMA_MODEL` or `OLLAMA_EMBED_MODEL` before starting when those models are already
approved for your environment. The profile pins the verified Ollama `0.32.4` release rather than
floating on `latest`; production deployments should additionally pin the image digest. Model IDs
remain an exact server-side allowlist.

### Ollama cloud profile and API key

Ollama's hosted native API uses Bearer authentication with `OLLAMA_API_KEY`; local Ollama does not
require authentication. The official contracts are documented in
[Ollama authentication](https://docs.ollama.com/api/authentication) and the
[API introduction](https://docs.ollama.com/api/introduction).

```bash
export OLLAMA_API_KEY
export HUMORVIBES_API_KEY
docker compose -f compose.yaml -f compose.ollama-cloud.yaml up --build --wait
curl --fail http://127.0.0.1:8080/v1/capabilities \
  -H "Authorization: Bearer ${HUMORVIBES_API_KEY}"
```

The outbound `OLLAMA_API_KEY` and inbound `HUMORVIBES_API_KEY` are separate. Neither is serialized
by the capability endpoint, error responses, caches, or receipts. The cloud overlay refuses to
start when `OLLAMA_API_KEY` is absent.

## Kubernetes

The base manifests run the exact same image as two non-root, read-only replicas behind a
cluster-internal `ClusterIP` Service. They include startup, liveness, and readiness probes,
resource requests/limits, rolling-update constraints, no service-account token, a runtime
seccomp profile, disabled Service-link environment injection, same-namespace ingress, and
default-deny egress. Disabling Service links prevents a Service named `humorvibes` from injecting
`HUMORVIBES_PORT=tcp://...` over the application's numeric listen-port setting. The distinction
among probe types follows the
[Kubernetes probe contract](https://kubernetes.io/docs/concepts/workloads/pods/probes/).

For a local `kind` cluster:

```bash
docker build -t humorvibes-research:0.7.1 .
kind load docker-image humorvibes-research:0.7.1
kubectl apply -k deploy/kubernetes
kubectl rollout status deployment/humorvibes
kubectl port-forward service/humorvibes 8080:80
```

Then run `python3 examples/api_client.py` in another shell. For `minikube`, use
`minikube image load humorvibes-research:0.7.1` in place of the `kind` command.

To reproduce the verified public-image path instead of building locally, apply the digest overlay:

```bash
kubectl apply -k deploy/overlays/ghcr
kubectl rollout status deployment/humorvibes
kubectl port-forward service/humorvibes 8080:80
curl --fail http://127.0.0.1:8080/health/ready
```

The checked-in receipt proves this path on an ephemeral local cluster only. A hosted deployment
still needs an environment-specific gateway, DNS, TLS certificate, secret manager, observability
destination, egress policy, autoscaling load test, and rollback exercise.

Before exposing the Service outside the cluster, require inbound authentication:

```bash
export HUMORVIBES_API_KEY
kubectl create secret generic humorvibes-secrets \
  --from-literal=HUMORVIBES_API_KEY="${HUMORVIBES_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/humorvibes
```

For Ollama cloud, add `OLLAMA_API_KEY` to that Secret, then configure the allowlist and defaults:

```bash
export OLLAMA_API_KEY
kubectl create secret generic humorvibes-secrets \
  --from-literal=HUMORVIBES_API_KEY="${HUMORVIBES_API_KEY}" \
  --from-literal=OLLAMA_API_KEY="${OLLAMA_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl set env deployment/humorvibes \
  OLLAMA_HOST=https://ollama.com \
  HUMORVIBES_OLLAMA_MODELS=gemma3:4b \
  HUMORVIBES_OLLAMA_EMBED_MODELS=embeddinggemma \
  HUMORVIBES_LLM_DEFAULT=ollama:gemma3:4b \
  HUMORVIBES_EMBEDDING_DEFAULT=ollama:embeddinggemma
```

For a remote cluster, push `humorvibes-research:0.7.1` to your registry, obtain the resulting
digest, and replace the base image with that immutable registry reference in a deployment-specific
Kustomize overlay. Add provider, DNS, and telemetry egress rules only for exact destinations.
[`deploy/gateway/README.md`](../deploy/gateway/README.md) contains the separately rendered Envoy
Gateway 1.8.3 edge example and its secret-safe verification commands.

### Helm

The chart exposes replicas, image tag or digest, resources, probes, provider configuration, an
existing Secret, and optional HPA/PDB objects while preserving the non-root, read-only,
cluster-internal defaults:

```bash
helm lint deploy/helm/humorvibes
helm template demo deploy/helm/humorvibes
helm upgrade --install humorvibes deploy/helm/humorvibes \
  --set image.repository=humorvibes-research \
  --set image.tag=0.7.1
```

Use `existingSecret` for keys. The chart intentionally does not create an Ingress or accept
literal secrets as values. See [`deploy/helm/humorvibes/README.md`](../deploy/helm/humorvibes/README.md)
for digest-pinned registry installation.

## Configuration reference

| Variable | Meaning | Default |
| --- | --- | --- |
| `HUMORVIBES_API_KEY` | inbound API Bearer key | unset |
| `HUMORVIBES_HOST` | API listen address | `127.0.0.1` (`0.0.0.0` in the container) |
| `HUMORVIBES_PORT` | API listen port | `8080` |
| `OLLAMA_HOST` | local or cloud Ollama base URL | local, or `https://ollama.com` when a key is set |
| `OLLAMA_API_KEY` | outbound Ollama cloud Bearer key | unset |
| `HUMORVIBES_OLLAMA_MODELS` | comma-separated generation allowlist | `GEMMA_MODEL` or `gemma3:4b` |
| `HUMORVIBES_OLLAMA_EMBED_MODELS` | comma-separated embedding allowlist | six built-in model names |
| `HUMORVIBES_OPENAI_BASE_URL` | OpenAI-compatible `/v1` base | `https://api.openai.com/v1` |
| `HUMORVIBES_OPENAI_API_KEY` | outbound OpenAI-compatible Bearer key | `OPENAI_API_KEY` or unset |
| `HUMORVIBES_OPENAI_MODELS` | comma-separated generation allowlist | empty |
| `HUMORVIBES_OPENAI_EMBED_MODELS` | comma-separated embedding allowlist | empty |
| `HUMORVIBES_SENTENCE_TRANSFORMER_MODELS` | comma-separated local model allowlist | empty |
| `HUMORVIBES_LLM_DEFAULT` | exact default model ID | `offline` unless Ollama is configured |
| `HUMORVIBES_EMBEDDING_DEFAULT` | exact default embedding model ID | `hash:128` |
| `HUMORVIBES_CORS_ORIGINS` | comma-separated browser origins | empty |
| `HUMORVIBES_MAX_REQUEST_BYTES` | whole HTTP body limit | `1000000` |
| `HUMORVIBES_MAX_BATCH_ITEMS` | embedding item limit | `64` |
| `HUMORVIBES_RATE_LIMIT_PER_MINUTE` | per-process client-IP limit; `0` disables | `0` |
| `HUMORVIBES_STRICT_READINESS` | make readiness call configured providers | `false` |
| `HUMORVIBES_ALLOW_INSECURE_REMOTE` | allow plain HTTP to a public integration host | `false` |
| `HUMORVIBES_STATSD_HOST` / `HUMORVIBES_STATSD_PORT` | optional external low-cardinality StatsD sink | unset / `8125` |
| `HUMORVIBES_OTEL_TRACES_ENDPOINT` | optional OTLP/HTTP per-signal traces URL | unset |
| `HUMORVIBES_OTEL_SERVICE_NAME` | OpenTelemetry service identity | `humorvibes-api` |
| `HUMORVIBES_OTEL_SAMPLE_RATIO` | parent-based root trace sample ratio | `0.1` |

Do not enable strict live readiness on a frequent Kubernetes probe: it calls the configured model
providers and can add latency and inference cost. Use `humorvibes doctor --live` for an explicit
dependency check instead.

## Production boundaries

- The in-process rate limiter and counters are per replica. Use the rendered Envoy Gateway policy
  with a healthy Redis-backed rate-limit service (or an equivalent gateway) for a global quota.
- The service does not terminate TLS, issue user identities, or implement model-level billing.
- Provider hosts and models are operator configuration, never caller-provided values.
- Outbound plain HTTP is accepted only for local/private/cluster hosts unless the operator opts in.
- Responses are bounded and decoded as JSON objects; embedding count, numeric type, finiteness,
  nonzero norm, consistent dimensions, response indices, and per-model dimension stability are
  validated before results reach an application.
- Generation and model judging are application features, not published Gemma measurements or
  human evaluation.
- Audience-facing personalization requires explicit, revocable input and a real consent and data
  lifecycle. The service does not infer audience traits or supply that governance layer.

Product fit and model quality are separate from deployment correctness. The persona workflows,
success measures, and human-evidence gates are specified in
[`PRODUCT_AND_RESEARCH_USE_CASES.md`](PRODUCT_AND_RESEARCH_USE_CASES.md).
