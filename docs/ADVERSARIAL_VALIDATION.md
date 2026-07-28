# Adversarial validation

*Role: tested attack classes and their boundaries. Audience: reviewers. A passing suite is a software contract, not a security certification or a model-quality result.*

The integration layer is tested against hostile configuration, malformed provider responses, and
abusive HTTP inputs. This is fail-closed contract testing, not a security certification or a model
quality benchmark.

## Run it

The deterministic audit makes zero network calls and downloads no models:

```bash
humorvibes adversarial
humorvibes adversarial --out jestry_out/adversarial_integration_audit.json
```

The fuller pytest battery exercises the transport, registries, API, and packaging:

```bash
python3 -m pytest -q \
  tests/test_integrations.py \
  tests/test_api.py \
  tests/test_packaging.py
python3 verify_deployment.py --docker \
  --kustomize-image registry.k8s.io/kubectl:v1.36.2 \
  --helm-image alpine/helm:4.2.0@sha256:af08f75a3130d666a50b9fc150f40987ef20b885cf67659aabf4b83a5f2c5501
```

Use `humorvibes doctor --live` separately when a real provider is configured. A live provider check
answers availability; it does not establish model quality, correctness, or funniness.

## Attack classes covered

- secrets in URLs, public settings, upstream errors, caches, and response bodies;
- embedded URL credentials, query/fragment injection, plain HTTP to public hosts, and redirects;
- caller attempts to provide a host or other forbidden request field;
- unallowlisted LLM and embedding model IDs;
- oversized fixed-length and chunked HTTP bodies;
- oversized, invalid-JSON, and non-object upstream responses;
- missing generation content and unsupported content shapes;
- embedding count mismatch, duplicate/invalid indices, mixed dimensions, dimension drift,
  booleans, NaN/infinity, and zero vectors;
- cosine dimension, finiteness, and nonzero-norm preconditions;
- prompt/body non-reflection in validation errors and generic internal errors;
- invalid request IDs, inbound Bearer auth, per-process rate limits, and security headers;
- container/Kubernetes/Helm non-root identity, read-only filesystems, dropped capabilities,
  probes, bounded resources, internal-only Service type, and absence of literal secrets;
- retired Ollama singular embedding endpoint regression;
- synthetic positive effects attempting to cross a human-evidence claim gate;
- study exports containing raw material or direct identity, unknown fields, duplicate IDs,
  non-finite ratings, missing permission/consent/holdout, or incomplete paired blocks.
- prospective launch packs attempting to claim observations, condition labels leaking into blinded
  schedules, short assignment keys, and reconstruction from the public assignment seed alone.

## Deliberate boundaries

The suite does not claim coverage of provider-side compromise, model prompt injection, semantic
embedding quality, distributed denial-of-service, TLS termination, identity lifecycle, supply-chain
signing, or human safety/funniness validation. Study-contract tests do not replace ethics review,
recruitment, consent operations, randomization delivery, or external replication. The base
Kubernetes manifests do not include an
Ingress, global rate limiter, external secret operator, or network policy because those depend on
the target cluster. Add them in a deployment-specific overlay rather than pretending one generic
manifest fits every environment.

The operator controls provider base URLs and allowlists. API callers cannot turn HumorVibes into an
arbitrary HTTP proxy. Private and single-label hosts are accepted for container and Kubernetes
service discovery; do not let untrusted users mutate process environment or ConfigMaps.

## Adding an integration

An integration is ready only when it has:

1. an exact model-ID allowlist and secret-safe public capability record;
2. bounded time, request size, and response size;
3. schema validation with explicit failure codes;
4. adversarial fixtures for empty, missing, oversized, duplicated, non-finite, and dimension-drift
   responses where relevant;
5. a live diagnostic that is opt-in and truthfully scoped;
6. operator documentation and a no-network test path;
7. no change to the immutable Kaggle measurement route unless a new research release is explicitly
   designed, executed, and published.
