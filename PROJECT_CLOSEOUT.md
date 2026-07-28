# Project closeout and continuation handoff

HumorVibes Research 0.8.0 closes the initial build phase of Humor Genome Wave 2. The project is a
public research and integration artifact, not a completed claim that a model understands humor or
improves human writing. This document defines what can be treated as stable, what remains open,
and how another contributor can continue without reconstructing the project history.

## Stable public surfaces

| Surface | Stable identity | Use |
| --- | --- | --- |
| Wave 2 study | Kaggle notebook v15, source tag `humor-genome-wave2-v10` (v14 stays pinned to v9) | Canonical executable observational write-up |
| Wave 2 data | Kaggle dataset v7 | Rights-filtered public corpus, census, frames, aligned phrases, and manifest |
| Open Controls | Kaggle dataset v4 and notebook v4, source tag `humor-genome-open-controls-v2` | CC0 procedural controls and frozen retrieval tasks |
| Application | GitHub release `v0.8.0` | SDK, FastAPI, CLI, Docker, Compose, Kubernetes, Helm, and integration contracts |
| Research infrastructure | GitHub `main` plus source-controlled receipts | Writer-study, multilingual, multimodal, provider, source, and archive gates |

The immutable Kaggle source tags remain the authority for published notebook measurements.
Application releases do not rewrite notebook results, and notebook completion does not establish a
human product outcome.

## Controlling conclusions

- The form study does not establish separation: zero of ten joke-form confidence intervals sit
  strictly above the proverb control interval, and all ten overlap it.
- The caption study is weak on text alone and does not bound a system that can see the drawing.
- Structural features that fit one corpus are not humor features: the within-Humicroedit 0.5075
  model transfers at −0.0091, and the sole three-corpus survivor (`punch_rarity_max`) carries a
  negative sign. Post-closeout wave 1 (2026-07-27) reinforced rather than moved these boundaries
  — declared-style S regimes: 0/7 separate but underpowered at n=12 (among-styles p = 0.45);
  divisiveness: reliable overall, not easier to predict; word-level demographic gaps: not
  detectable at these per-word n. Scoreboard: `docs/THESIS_AND_EVIDENCE.md`.
- The surprise-reduction account is a falsifiable design framework, not a completed brain model.
- Synthetic controls and provider benchmarks establish executable contracts and proxy-task
  behavior. They do not establish funniness, audience suitability, cultural validity, or writer
  benefit.
- The highest-value scientific continuation is the preregistered writer crossover pilot with
  consented writers and blinded, opt-in audience evaluation.

## Maintenance state

The initial delivery phase is closed. The v0.8.0 source, wheel, sdist, two-platform container,
provenance/SBOM, anonymous-pull, hardened-runtime, and public Kaggle gates passed; the independent
read-back is recorded in
[`jestry_out/v0_8_0_publication.json`](jestry_out/v0_8_0_publication.json). The repository remains
public and accepts:

- security and dependency maintenance;
- reproducibility fixes with before/after evidence;
- one-language native-review pull requests;
- rights-cleared human-study receipts;
- narrowly scoped adapters that satisfy the existing conformance and evidence boundaries;
- documentation corrections that preserve negative results and provenance.

New speculative model architectures, dashboards, dataset harvests, or product claims should not be
added merely to keep the project active. They belong in a bounded proposal with a user, decision,
baseline, rights/consent plan, primary metric, uncertainty method, and machine-readable receipt.

## Open work is intentionally not release debt

| Lane | Public issue | External evidence required |
| --- | --- | --- |
| Writer benefit | [#3](https://github.com/aidonerightcorp/humorvibes-jestry/issues/3) | Ethics/IRB determination, preregistration, consented writers, blinded audience ratings |
| Human multimodal value | [#4](https://github.com/aidonerightcorp/humorvibes-jestry/issues/4) | Rights-cleared images, consented captions, rating protocol, independent evaluation |
| Native-language validity | [#5](https://github.com/aidonerightcorp/humorvibes-jestry/issues/5) and [#20-#26](https://github.com/aidonerightcorp/humorvibes-jestry/issues?q=is%3Aissue%20state%3Aopen%20label%3Amultilingual) | Native/fluent reviewers and permission-confirmed fixtures, one language per PR |
| Academic DOI | [#9](https://github.com/aidonerightcorp/humorvibes-jestry/issues/9) | Repository-owner Zenodo publication and anonymous public-record verification |
| Product expansion | [#7](https://github.com/aidonerightcorp/humorvibes-jestry/issues/7), [#8](https://github.com/aidonerightcorp/humorvibes-jestry/issues/8), [#10](https://github.com/aidonerightcorp/humorvibes-jestry/issues/10) | Streaming, vector storage, or named production-environment evidence |

These issues remain open because their evidence does not exist yet. Closing the initial build phase
does not permit simulated participants, model-authored native attestations, inferred rights, or a
fabricated DOI. They are grouped under the
[`Post-closeout research and ecosystem`](https://github.com/aidonerightcorp/humorvibes-jestry/milestone/2)
milestone, separate from delivered v0.8.0 work.

## Reproduce the closeout state

```bash
git clone --branch v0.8.0 https://github.com/aidonerightcorp/humorvibes-jestry.git
cd humorvibes-jestry
uv sync --frozen --extra dev
uv run --frozen pytest -q
uv run --frozen humorvibes adversarial
uv run --frozen python tools/public_release_audit.py
```

For application use, build the local container or install the wheel attached to the GitHub
release. Pin public containers by immutable digest, not by `latest`. For research use, cite the
software release and the exact Kaggle dataset/notebook version used in the analysis.

## Post-closeout maintenance record

Bounded maintenance waves since v0.8.0 (PRs #34–#36 plus the closeout wave) added
receipted studies, figures, the `docs/THESIS_AND_EVIDENCE.md` scoreboard, a full
documentation reconciliation, refreshed public notebooks (wave2 v15, Open Controls v4,
ceiling explainer v4 — all terminal COMPLETE and independently read back), and made every
published notebook reproducible from this repository. None of it moved a claim boundary:
the nulls stayed visible, no human evidence was produced, and the application release
remains v0.8.0. The project is closed, maintained, reproducible, and consistent across
every public surface.

## Reopening active development

Reopen the active phase only when at least one of these is true:

1. A consented human study is ready to collect or publish observations.
2. A native reviewer has supplied a compliant one-language fixture bundle.
3. A rights-cleared multimodal cohort is available.
4. A repository owner is ready to publish and verify the DOI archive.
5. A concrete integrator has a named deployment or storage target and will supply real conformance
   evidence.

Until then, the correct state is maintained, public, reproducible, and open to bounded
contributions—not perpetually unfinished.
