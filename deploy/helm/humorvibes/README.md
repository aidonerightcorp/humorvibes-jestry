# HumorVibes Helm chart

This chart packages the same non-root, read-only API workload as the Kustomize base while exposing
image, replicas, resources, probes, provider/observability configuration, an existing Secret,
default-deny NetworkPolicy, optional HPA, and optional PodDisruptionBudget values.

Render without a cluster:

```bash
docker run --rm -v "$PWD:/work" -w /work alpine/helm:4.2.0 \
  template demo deploy/helm/humorvibes
```

Install a locally or registry-published image:

```bash
helm upgrade --install humorvibes deploy/helm/humorvibes \
  --set image.repository=humorvibes-research \
  --set image.tag=0.8.0
```

For a registry image, resolve its real digest first and pass it without storing a mutable tag in
the rendered workload:

```bash
IMAGE_REPOSITORY=registry.example/humorvibes-research
IMAGE_DIGEST=$(docker buildx imagetools inspect "$IMAGE_REPOSITORY:0.8.0" \
  --format '{{json .Manifest.Digest}}' | tr -d '"')
test -n "$IMAGE_DIGEST"
helm upgrade --install humorvibes deploy/helm/humorvibes \
  --set-string image.repository="$IMAGE_REPOSITORY" \
  --set-string image.digest="$IMAGE_DIGEST"
```

The independently verified public 0.8.0 identity can be installed directly:

```bash
helm upgrade --install humorvibes deploy/helm/humorvibes \
  --set-string image.repository=ghcr.io/aidonerightcorp/humorvibes-jestry \
  --set-string image.digest=sha256:95568eb899c1a3aa51d8dc1a0884212390f9cc4e85c3aa643477a6355673f4e7
```

For inbound API authentication or provider keys, create a Secret separately and pass only its
name:

```bash
kubectl create secret generic humorvibes-secrets \
  --from-literal=HUMORVIBES_API_KEY="$HUMORVIBES_API_KEY"
helm upgrade --install humorvibes deploy/helm/humorvibes \
  --set existingSecret=humorvibes-secrets
```

The chart never templates literal secret values. It defaults to an internal ClusterIP and does not
create an Ingress; TLS, identity, egress policy, and global rate limiting belong in a named
environment-specific gateway or overlay.
