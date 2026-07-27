# HumorVibes Research 0.7.0

Version 0.7.0 turns the public Humor Genome work into a reproducible research-and-integration
release without changing its central evidence boundary: model surprisal is not human funniness.

## What is usable now

- Read and rerun the canonical Wave 2 Gemma notebook and its rights-filtered multilingual data.
- Use the separate 120,000-row CC0 Open Controls dataset and COMPLETE causal-design notebook.
- Query bounded generation, embedding, similarity, research-signal, Open Controls, and study
  endpoints through the Python SDK or FastAPI service.
- Build a non-root, read-only Docker image or render the two-replica default-deny Kubernetes base,
  Helm chart, and optional Envoy Gateway edge.
- Run the hard-retrieval, multimodal, writer-study, provider, clean-install, deployment, and
  adversarial contracts from checked-in receipts and commands.

## Verified for this release

- 186 tests pass.
- 26 of 26 adversarial contracts pass.
- Clean wheel installs pass on Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- The current-source container runs as `10001:10001` with a read-only root filesystem and answers
  all nine probed service endpoints.
- Compose, Kustomize with kubectl 1.36.2, and Helm 4.2.0 lint/render checks pass.
- Open Controls dataset v4 and notebook v3 are public, anonymously reachable, and independently
  verified; all 14 release checks pass.

## What is not established

- No model, embedding, retrieval score, or synthetic positive control establishes that a person
  or audience will find material funny.
- The configured live provider audit did not quality-validate any semantic model.
- No public hosted API, live Kubernetes cluster, or completed human writer/audience trial is
  claimed by the source release.
- A DOI is not fabricated: `CITATION.cff` and `.zenodo.json` make the snapshot archive-ready, but
  DOI minting remains an external repository-owner action until an archive integration is present.

See `PROJECT_STATUS.md`, `PROJECT_WRITEUP.md`, `ROADMAP.md`, and the machine-readable receipts in
`jestry_out/` for the controlling details.
