# Security policy

Please report suspected credential exposure, request-boundary bypasses, dependency vulnerabilities,
or unsafe deployment defaults through the repository's
[private vulnerability form](https://github.com/aidonerightcorp/humorvibes-jestry/security/advisories/new)
before opening a public issue. Do not include active keys, private model responses, or unpublished
corpus rows in a public report.

## Supported surface

The current deployable integration package is `humorvibes-research` 0.8.x on Python 3.10-3.14.
The historical research scripts remain auditable, but only the `humorvibes` SDK/API, Dockerfile,
Compose files, `deploy/kubernetes` manifests, and `deploy/helm` chart are treated as an
application-serving boundary.

## Deployment expectations

- Set `HUMORVIBES_API_KEY` before exposing `/v1/*` beyond a trusted private network.
- Terminate TLS at a trusted proxy, ingress, or service mesh.
- Store provider keys in a secret manager or Kubernetes Secret, never in an image, ConfigMap,
  committed environment file, URL, or client payload.
- Restrict provider hosts and model allowlists to operator-controlled configuration.
- Use a gateway-level distributed rate limiter for multi-replica or public deployments.
- Keep OpenTelemetry and StatsD export disabled unless the collector is operator-controlled; do
  not add bodies, authorization values, provider URLs, or user identifiers as telemetry fields.
- Pin the container by digest and run image/dependency scanning in the target registry.
- Keep the canonical Kaggle notebook and public dataset verification independent from the app
  deployment.

See `docs/API_AND_DEPLOYMENT.md` for concrete configuration and
`docs/ADVERSARIAL_VALIDATION.md` for tested and untested threat classes.
