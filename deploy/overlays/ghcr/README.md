# Public GHCR release overlay

This overlay changes only the base workload image. It pins the public HumorVibes Research 0.7.0
multi-architecture manifest by digest:

```text
ghcr.io/aidonerightcorp/humorvibes-jestry@sha256:012c589ebd3feb59b565ac8e1e36c8322f4f00755299ff7e40cb53f4001d70e8
```

The manifest contains `linux/amd64` and `linux/arm64`, was anonymously pulled and run, and has a
GitHub/Sigstore provenance attestation resolving to source tag `v0.7.0` and commit
`9a58dac4a81fbb512e1c939dce1a979facc7a078`. The controlling receipt is
[`../../../jestry_out/v0_7_0_publication.json`](../../../jestry_out/v0_7_0_publication.json).

Render or apply it with:

```bash
kubectl kustomize deploy/overlays/ghcr
kubectl apply -k deploy/overlays/ghcr
kubectl rollout status deployment/humorvibes
```

This registry-identity overlay was applied to an ephemeral `kind` cluster and the live Service was
smoke-tested; the machine-readable evidence is in
[`../../../jestry_out/v0_7_0_kind_smoke.json`](../../../jestry_out/v0_7_0_kind_smoke.json). This is
local deployment proof, not a hosted-production claim. The overlay deliberately preserves the base
offline/hash configuration and deny-all egress. Add gateway, DNS, certificate, secret, provider,
and telemetry policy only in a separate overlay for a named target cluster.
