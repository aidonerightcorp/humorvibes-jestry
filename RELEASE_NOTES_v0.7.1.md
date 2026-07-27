# HumorVibes Research 0.7.1

Version 0.7.1 is a deployment-correctness patch. It does not change the canonical Kaggle
measurements, corpus releases, research findings, or the central evidence boundary: model
surprisal is not human funniness.

## Why this patch exists

An actual disposable Kubernetes run found a failure that static Kustomize and Helm rendering did
not. A Service named `humorvibes` caused Kubernetes to inject
`HUMORVIBES_PORT=tcp://<cluster-ip>:80`, shadowing the image's numeric listen-port setting. Both
replicas entered `CrashLoopBackOff` before readiness.

The Kustomize base and Helm template now set `enableServiceLinks: false`. This prevents Service
environment injection, preserves the numeric port, and reduces unnecessary environment discovery.
A regression test protects both installation paths.

## Verified for this patch

- 188 tests pass locally and in the public application-contract workflow.
- Clean wheel installs pass on Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- The exact public v0.7.0 image digest was applied with the corrected manifests to a disposable
  `kind` v0.32.0 / Kubernetes v1.36.1 cluster.
- Kustomize and Helm each reached two ready, zero-restart replicas after remediation.
- Fourteen live Service requests passed across health, version, capabilities, hash embeddings,
  similarity, research signals, study-template, and Open Controls endpoints.
- Runtime checks observed UID/GID 10001, a read-only root filesystem, dropped capabilities,
  `RuntimeDefault` seccomp, no mounted service-account token, and default-deny egress.
- The disposable cluster was deleted and its absence verified.
- The source version, Python package, OpenAPI contract, Docker label default, Compose image,
  Kustomize base, and Helm chart now agree on 0.7.1.

The detailed pre-patch failure, remediation, rollout, requests, security checks, and teardown are
recorded in `jestry_out/v0_7_0_kind_smoke.json`. The v0.7.1 tag triggers the pinned
multi-architecture container workflow; the GitHub release records the resulting immutable digest
and attestations.

## Evidence boundaries

- This proves local ephemeral Kubernetes execution, not a hosted production deployment.
- DNS, TLS, gateway/controller installation, external Secrets, authenticated edge behavior,
  global rate limiting, trace export, load/autoscaling, restart/rollback drills, and cost remain
  environment-specific work tracked in public issue #10.
- The configured provider audit did not quality-validate a semantic model.
- No model score, embedding, synthetic control, or deployment receipt establishes that a person or
  audience will find an output funny.
- No completed human writer/audience trial is claimed.
- A DOI is not fabricated; archive-ready metadata exists, and real DOI minting remains tracked in
  public issue #9.
