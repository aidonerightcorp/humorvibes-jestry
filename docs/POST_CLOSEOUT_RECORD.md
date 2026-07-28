# Post-closeout record: the maintenance era, end to end (2026-07-27 → 2026-07-28)

*Role: the single narrative record of everything that happened after the v0.8.0 closeout —
what each wave did, why, and where its evidence lives. Audience: anyone (human or agent)
reconstructing this period without reading six pull requests. Numbers are deliberately NOT
restated here; every number lives in its receipt and in
[`THESIS_AND_EVIDENCE.md`](THESIS_AND_EVIDENCE.md), so this file cannot become a drift surface.
The per-PR one-line log is in
[`../CLAUDE_CODE_HANDOFF.md`](../CLAUDE_CODE_HANDOFF.md) ("Post-closeout maintenance log").*

*Motivating frame, project-wide: “the brain is a surprise-reduction engine” (predictive processing) — held as a falsifiable framework, never as a settled conclusion; the thesis and its evidence status live in [`THESIS_AND_EVIDENCE.md`](THESIS_AND_EVIDENCE.md).*

## Why the closed project moved at all

The v0.8.0 closeout froze the claims, not the repository. The maintainer then asked for a full
expansion review (repository, research tree, and both agent-session histories), and the review
found that the highest-value continuations needed no new permissions: finished-but-unpublished
receipts, data already on disk, and documentation that had drifted during the build. Everything
below stayed inside the closeout's own rule — bounded maintenance and reproducibility work, no
speculative expansion — and none of it changed the application package, which remains 0.8.0.

## The waves

**#34 — Post-closeout wave 1** (studies, figures, scoreboard, reconciliation).
Three new receipted studies on data already on disk (declared-style surprisal, caption
divisiveness, demographic word norms — all honest negatives or bounded results); the previously
computed word-type and three-corpus receipts ported and documented; three receipt-backed figures
(ceiling waterfall, transfer matrix, genome atlas); [`THESIS_AND_EVIDENCE.md`](THESIS_AND_EVIDENCE.md)
created as the tenet → instrument → receipt → status scoreboard; and a two-audit reconciliation
sweep applied across every public document (stale census figures requoted, a superseded receipt
no longer presented as the release index, the transfer null added to every entry-point document,
archive banners and role banners throughout). The static ceiling explainer went public on Kaggle.

**#35 — Notebook refresh** (thesis first, new immutable tag).
All three public notebooks gained an opening thesis statement calibrated to their role — the
frame-not-claim, the six tenets, the S/R/E/B instruments, and the scoreboard pointer. The
canonical Wave 2 notebook added a markdown-only "receipted follow-ups" section and moved to the
new immutable source tag `humor-genome-wave2-v10` (v9 untouched, still pinning the v14 run).

**#36 — Publication record.**
The refreshed kernels were pushed and verified to the project's read-back standard: terminal
COMPLETE, served cell sources byte-compared against the committed notebooks, executed outputs
independently downloaded (the in-run instrument check and the preserved form null), anonymous
visibility confirmed. Receipt: [`../jestry_out/notebook_refresh_publication.json`](../jestry_out/notebook_refresh_publication.json).

**#37 — Closeout wave** (repo-reproducible publications).
`ceiling_demo/` was ported into the repository so the repo can rebuild its own published kernel:
a static edition deterministic from receipt content alone, kernel metadata, the committed
notebook, and tests. CI caught a real defect on the way in — checkout mtimes had leaked into the
build — and the fix (content-only provenance) is itself receipted in the tests. The maintenance
log and closeout record were added to the operator documents.

**#38 — Adversarial referee round** (the correction wave).
At the maintainer's request, two independent reviewer agents audited everything above, including
recomputing every quoted number from receipts and source data. Verdict: major revision. The full
verbatim reports are preserved in
[`REFEREE_REPORT_2026-07-28.md`](REFEREE_REPORT_2026-07-28.md); the corrections — invalid
Spearman–Brown uses withheld, Welch-t gap tests, two underpowered designs relabeled with
receipted power analyses, reliability-zero ranked word lists removed, exact regression pins —
are narrated in the correction-trail entry in [`../RESULTS.md`](../RESULTS.md). Transcription
integrity across every quoted number was perfect; the defects were estimator- and label-level.
No study's conclusion reversed. The corrected Wave 2 notebook was pushed and read back again.

**#39 — Final polish.**
The version references and maintenance-log rows the referee round itself had staled were swept
and fixed — the last instance of the drift class this era spent so much effort closing.

## Final verified state

- `main` green under the full locked suite and the network-free adversarial contracts; zero open
  pull requests.
- The live public-surface audit passes against the current tag and all Kaggle surfaces.
- All three public notebooks are terminal COMPLETE, byte-verified served-vs-committed, and
  reproducible from this repository alone.
- Every public document agrees with the scoreboard, and the scoreboard cites a receipt for every
  row. The current notebook/dataset versions are in the
  [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) surfaces table — that table, not this file, is
  where versions live.

## What remains, and why it is not here

Four actions only a human can take, unchanged from the closeout and deliberately not simulated:

1. **Hosting the community competition** — the verified pack and click-path are in
   `../competition/launch/HOSTING_GUIDE.md`.
2. **The Zenodo DOI** — owner-account action; deposit-ready per [`DOI_ARCHIVE.md`](DOI_ARCHIVE.md)
   (issue #9).
3. **Native-language review** — one language per PR, contract in
   [`NATIVE_LANGUAGE_CONTRIBUTIONS.md`](NATIVE_LANGUAGE_CONTRIBUTIONS.md) (issues #5, #20–#26).
4. **A named deployment target** — if a permanent hosted demo is ever wanted (issue #10).

The deeper human gates — the preregistered writer crossover pilot (#3) and the rights-cleared
multimodal cohort (#4) — remain the project's declared path to any product claim.

## Durable lessons this era paid for

Methodological (from the referee round; details and dispositions in the report):

- Spearman–Brown is undefined for non-positive split-half correlations — withhold it, report raw,
  mark the cell not estimable.
- A "null" label requires a design whose criterion could have fired; compute and receipt the
  power analysis, or label the result "underpowered / not detectable".
- Never publish rankings from a statistic whose implied reliability is ~0 (check
  var(observed) against mean sampling variance first).
- Normal-z references on tiny per-group n inflate significance; use Welch t.
- Binning by a variable that tracks the outcome (votes ↔ mean) conditions on the outcome; name
  strata as strata.
- Check the attenuation ceiling √(rel₁·rel₂) before interpreting any cross-dataset agreement.
- Pin regression tests to the exact quoted values; loose bands let claims drift silently.

Operational:

- Generated artifacts must be deterministic from CONTENT (checkout mtimes are not content).
- A builder that writes outputs before its own self-attack asserts can leave a verified freeze
  corrupted — restore from the tracked copy, and treat the refusal as the control working.
- Anonymous kernel pages are JS shells; content read-back needs authenticated source pulls plus
  executed-output downloads.
- Kernel source tags must exist on the default branch before the kernel that clones them is
  pushed.
- Untracked files pass `git diff --check` silently; the day generated SVGs become tracked they
  need a whitespace attribute.

## Provenance of this record

Written 2026-07-28 by the maintainer's agent at the close of the maintenance era, as the last
documentation act of the engagement. If a later wave lands, extend the log table in the handoff
and add a section here — do not rewrite the history above.
