# HumorVibes Research 0.8.0

Version 0.8.0 is the formal closeout release for the initial Humor Genome Wave 2 build phase. It
packages the final research-infrastructure work without upgrading synthetic, model, software, or
deployment evidence into a human-outcome claim. The canonical Kaggle measurements and their
negative results are unchanged.

## What is new

- The writer crossover workbench now separates anticipated effect from the claim threshold,
  computes exact retention assurance, and reports hierarchical writer, premise, rating, and
  attrition sensitivity. Its conservative plan requires 80 analyzable writers, 99 recruits, and
  1,280 blinded audience ratings.
- `source_spec_preflight.py` validates one proposed source offline before any network or corpus
  write, using a pinned licensed fixture, exact expected normalization, deny-first release policy,
  and an optional bounded live upstream check.
- Native-language contributions are restricted to one language and one form per pull request,
  with rights evidence, immutable snapshots and digests, at least 20 positives and 20 hard
  negatives, a privacy-minimized native/fluent human attestation, and coverage/error reporting.
- The human multimodal contract checks asset rights, consent and rating-protocol evidence, exact
  and perceptual identity, near duplicates, scene/contest leakage, synthetic targets, identical
  evaluation arms, contest uncertainty, calibration, and failure slices.
- The provider matrix records five successful model/interface arms across pinned Ollama and TEI
  implementations on the same 300-query hard-retrieval task and balanced 490-pair,
  seven-language crosslingual task. It retains model/server identities, failures, throughput,
  bootstrap intervals, language slices, and a secret scan.
- The DOI tooling reconstructs the immutable v0.7.0 release, verifies all 510 tracked files with
  a canonical per-file inventory, and validates exact deposition metadata without treating
  toolchain-dependent ZIP bytes as source identity.

## Release gates

- 221 tests pass, including packaging, API, source, native-review, multimodal, provider, study,
  release, and DOI contracts.
- The network-free adversarial suite passes all 27 checks without model downloads or provider
  calls.
- Clean wheel installs are tested on Python 3.10, 3.11, 3.12, 3.13, and 3.14.
- The OpenAPI document, Python package, Docker label, Compose image, Kubernetes base, Helm chart,
  citation metadata, and release notes agree on version 0.8.0.
- Tagged container publication builds `linux/amd64` and `linux/arm64`, produces BuildKit
  provenance and SPDX SBOM attestations, and adds a GitHub registry attestation. The immutable
  digest must be anonymously pulled and runtime-probed before it is promoted into the checked-in
  GHCR overlay.

## What closeout means

The source, public datasets, executable notebooks, application package, deployment contracts,
contribution paths, research limitations, and machine-readable receipts are ready for long-term
reading, reproduction, and extension. Routine feature expansion is no longer part of the initial
delivery phase. Maintenance, security fixes, reproductions, and bounded contributor pull requests
remain welcome.

Closeout does not mean that the core product hypothesis is established. The writer pilot,
rights-cleared human multimodal benchmark, and native-language reviews still require real people,
consent, rights, and independent response measurements. A null human result remains a successful
outcome when the preregistered protocol is followed.

## Evidence boundaries

- Gemma surprisal is not funniness.
- Retrieval quality is not audience preference or writer benefit.
- The provider matrix does not establish one universal embedding default.
- Synthetic controls validate software and recovery behavior, not human response.
- No hosted production API or hosted production Kubernetes deployment is claimed.
- No completed writer/audience trial, native review, or rights-cleared human multimodal cohort is
  claimed.
- A DOI is not fabricated; the archive is deposit-ready and the public DOI gate remains open.
