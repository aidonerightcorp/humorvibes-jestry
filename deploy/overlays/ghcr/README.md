# Public GHCR release overlay

This overlay changes only the base workload image. It pins the public HumorVibes Research 0.8.0
multi-architecture manifest by digest:

```text
ghcr.io/aidonerightcorp/humorvibes-jestry@sha256:95568eb899c1a3aa51d8dc1a0884212390f9cc4e85c3aa643477a6355673f4e7
```

The manifest contains `linux/amd64` and `linux/arm64`, was anonymously pulled and run, and has
per-platform SPDX/SLSA attestation layers plus a GitHub provenance attestation resolving to source
tag `v0.8.0` and commit `5ca7b020a8a4b9d7ca3d82f85dc87aff704254d0`. The controlling receipt is
[`../../../jestry_out/v0_8_0_publication.json`](../../../jestry_out/v0_8_0_publication.json).

Render or apply it with:

```bash
kubectl kustomize deploy/overlays/ghcr
kubectl apply -k deploy/overlays/ghcr
kubectl rollout status deployment/humorvibes
```

This exact overlay renders successfully, and the public image passed the hardened standalone API
probe. The unchanged deployment contract was last applied through both Kustomize and Helm in the
v0.7.1 ephemeral `kind` proof at
[`../../../jestry_out/v0_7_1_kind_smoke.json`](../../../jestry_out/v0_7_1_kind_smoke.json). No
v0.8.0 cluster apply or hosted-production deployment is claimed. The overlay deliberately
preserves the base offline/hash configuration and deny-all egress. Add gateway, DNS, certificate,
secret, provider, and telemetry policy only in a separate overlay for a named target cluster.
