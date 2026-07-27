# Kubernetes base

This Kustomize base runs the locally built `humorvibes-research:0.7.1` image in offline/hash mode.
It is intentionally a `ClusterIP` service with no Ingress and no committed Secret. Its
NetworkPolicy allows port 8080 from same-namespace pods and denies all egress, matching the
default offline/hash profile. Service-link environment injection is disabled so the Service name
cannot overwrite the application's numeric `HUMORVIBES_PORT` setting with a `tcp://...` value.

```bash
docker build -t humorvibes-research:0.7.1 .
kind load docker-image humorvibes-research:0.7.1
kubectl apply -k deploy/kubernetes
kubectl rollout status deployment/humorvibes
kubectl port-forward service/humorvibes 8080:80
```

Create the optional `humorvibes-secrets` Secret before any external exposure. Use a
deployment-specific Kustomize overlay to set an immutable registry digest, gateway/TLS,
external-secret integration, exact provider/telemetry egress, autoscaling, and provider
configuration. Full commands and
the environment reference are in [`../../docs/API_AND_DEPLOYMENT.md`](../../docs/API_AND_DEPLOYMENT.md).

For the public 0.7.0 image, the checked-in [`../overlays/ghcr`](../overlays/ghcr) pins the independently
verified multi-architecture manifest digest while preserving the base offline/default-deny
contract:

```bash
kubectl kustomize deploy/overlays/ghcr
kubectl apply -k deploy/overlays/ghcr
```

The public digest overlay has also been applied to a disposable `kind` cluster and exercised through
the live Service; see [`../../jestry_out/v0_7_0_kind_smoke.json`](../../jestry_out/v0_7_0_kind_smoke.json).
That local smoke proof is not a claim that a hosted production cluster exists.
