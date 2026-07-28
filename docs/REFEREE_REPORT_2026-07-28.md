# Referee reports — adversarial review of the post-closeout waves (2026-07-28)

*Role: the preserved, verbatim review record for PRs #34–#37. Audience: anyone auditing how the
2026-07-28 corrections (PR #38) were decided. Provenance: two independent AI reviewer agents
(fresh contexts, read-only) — a methods/statistics referee that re-ran the mathematics against
committed receipts and source data, and a consistency referee that swept the merged end state.
Every finding was verified by the maintainer-agent before any fix was applied; the applied
revision is PR #38 and the correction-trail entry in [`../RESULTS.md`](../RESULTS.md). Nothing
in this file was edited after the fact beyond formatting; where a finding was contested or
accepted as-is, the disposition is recorded in the PR #38 description.*

Dispositions in brief: every MUST-FIX item was applied; SHOULD-FIX items were applied except
where noted in PR #38; the ACCEPTED-AS-IS lists below are the audit trail of what was checked
and found sound. None of the three studies' conclusions reversed.

---

## Report 1 — methods/statistics referee

Verified by re-running the math against committed receipts and the source data in `data_cache/`
(research tree). Nothing written or modified.

### (a) MUST-FIX before accepting

**1. [critical] `divisiveness_study.py` — Spearman–Brown applied to negative split-half r; the
low-vote bin reliabilities have the wrong sign and an amplified magnitude.**
`2*r/(1+r)` is only a reliability correction for parallel halves with r ∈ (0,1]. It is unbounded
below −1 for raw r < −1/3 (r=−0.5 → −2.0), and the only guard was `r > -1`. Re-running the exact
estimator on the parquet: in the 40–80 bin the disjoint complementary split gives raw r ≈ −0.234
→ SB −0.610, but independent half-samples of the same captions give raw r ≈ +0.254 → SB +0.405.
The receipt's `by_vote_bin["40-80"].mean.median_spearman_brown = -0.2854` was therefore not a low
reliability but a sign-flipped artifact of complementary dealing under range restriction,
magnified ~2.6× by the SB step. Affected 6 of 9 bin×statistic cells. *Fix applied:* SB withheld
for r ≤ 0; raw split-half r always reported; affected bins marked "not estimable"; the
disjoint-split downward bias stated in the receipt.

**2. [critical] `demographic_norms_study.py` — unshrunken top-15 word lists from a statistic with
~zero reliability.**
Recomputed from `engelthaler_humor_norms.csv`: var(sex_gap) = 0.1937 vs mean sampling variance
E[SE²] = 0.1826 → implied per-word gap reliability **0.058**; for age_gap the implied true
variance is negative (reliability ≈ 0). The receipt nonetheless published 60 words ranked by raw
gap, with no n, no SE, no q — demographically loaded noise ("giggle" F>M, "bondage"/"orgy" M>F,
"bitch"/"squaw" young>old) that reads as findings. The one item in the wave with reputational as
well as statistical risk. *Fix applied:* lists removed; reliabilities receipted beside the tests.

**3. [major] `declared_style_study.py` — the "0/7 separate" criterion cannot fire; labelling it
"Null" overstates.**
Separation requires a group's bootstrap CI lower bound to exceed the control CI upper bound
(5.999) against a control mean of 4.144 whose own CI is 3.39 wide at n=12. The largest observed
group CI lower bound is 4.740; the minimum detectable difference ≈ +1.9 nats — larger than the
entire observed spread of the seven group means (2.15). The scoreboard legend defines null =
"tested and not found"; this design could not find anything. *Fix applied:* relabeled
"Underpowered — not established (n=12/group)" with the criterion analysis in the receipt.

**4. [major] The permutation p did not test what the prose implied.**
`permutation_p` is passed the style groups only; the control is excluded. Documents rendered it
as if it tested the control comparison. *Fix applied:* scoped everywhere as "a separate
any-difference test among the seven style groups (control excluded)".

**5. [major] Selective reporting of the declared-style screen.**
The receipt's screening block was built from the already-filtered dict, so a reader could not
tell that arms were dropped or by how much they missed. *Fix applied:* pre-filter candidate
counts receipted (including `legal` 10 and `medical` 9 below the 150 threshold).

**6. [major] `demographic_norms_study.py` — normal-z reference on per-word n as small as 3.**
Recomputed with Welch–Satterthwaite t: BH-significant sex gaps drop from 9 to 2 (`county`,
`deathbed`). The inflated 9 was pinned in five documents and a test. Direction of the overall
conclusion unchanged (it strengthens), but a quoted number was 4.5× too large. *Fix applied:*
Welch t; receipt and all quoting sites re-emitted.

**7. [major] The cross-dataset gap arm has no attainable signal, and "CIs include zero" was
reported as if it were evidence.**
Recomputed reliabilities put the attenuation ceiling near or below the observed values (sex
ceiling ≈ 0.09–0.16 vs observed 0.1418; age ceiling ≈ 0 with the observed point negative,
−0.1536, CI [−0.3064, 0.0069] — leaning toward cross-crowd disagreement). As built, this arm
could not return a phenomenon under any truth. *Fix applied:* reliabilities and attenuation
ceilings receipted; the arm restated as "no attainable measurement"; the negative age point
reported rather than absorbed.

**8. [major] "At matched votes" was not what the by-vote-bin numbers measured.**
Within a contest, Spearman(votes, mean rating) ≈ +0.99 in this index — vote count is a
near-deterministic rank proxy for the label, so binning by votes conditions on the outcome.
Corroborating signature: the pooled overall reliability exceeded every individual bin. *Fix
applied:* phrase dropped everywhere; the votes↔mean coupling (median 0.928) receipted; bins
named as outcome strata.

### (b) SHOULD-FIX (wording, caveats, transparency) — applied unless noted

9. "Mostly null at word level" → "not detectable at these per-word n" (the legend's null =
   "tested and not found" requires a test that could find).
10. "24% of standing travels with the words" restored its qualifier: 24% of what the label's
    reliability allows; ~17% of observed standing.
11. The predicted/ceiling ratio's population mismatch (votes ≥ 20 numerator vs ≥ 40 denominator,
    ~6.8% of rows) documented in the receipt; ρ-convention (not variance share) stated.
12. Length features standardized per fold (test-fold leakage removed); the untuned shared
    Ridge(α=2.0) stated as a conditional in the receipt.
13. Token length receipted as the strongest visible declared-style covariate
    (Pearson(mean_tokens, mean_S) = −0.631 across groups) — no length-matched control exists.
14. First-file-wins dedup (cross-posted jokes assigned to the alphabetically first style file)
    noted in the receipt.
15. T4 (hint-dose) and the persona-shift half of T5 given explicit "Untested" scoreboard rows.
16. Loose test bands replaced with exact pins; figure values cross-checked against source
    receipts; the thesis doc cross-checked against receipts rather than substrings.
17. The genome atlas labeled as a language/source map of the corpus, not a humor-structure
    result; t-SNE non-metricity stated; "All items" underlay darkened.
18. Operator-machine absolute paths removed from the committed figures receipt.
19. The transfer matrix moved to a diverging colormap centered at 0; the r/Jokes-trained arm's
    56% retention stated beside the title's asymmetric claim.
20. BH families declared separately (6 sanity anchors vs 12 gap hypotheses; the sexc→age_gap
    survivor holds at q = 0.008 in the gaps-only family).
21. The cockamamie batch-union double-count (909/120,000 words, ~0.76%) noted in the receipt.
22. The vote-bin lookup made total (no StopIteration at votes ≥ 100,000).

### (c) ACCEPTED AS-IS — checked and sound

- **Transcription integrity was perfect**: all 27 numbers in the anti-drift appendix and
  scoreboard matched their receipts exactly. The problems were estimator and status-label
  problems, not bookkeeping.
- The divisiveness integrity screen reproduces exactly (2,186,939 → 7,061 → 5,544 → 2,068,094).
- No GroupKFold leakage; HashingVectorizer is stateless; 0 caption texts appear in more than one
  contest in this index.
- The declared-style permutation test is valid: with equal group sizes, between-group variance of
  means is monotone in the one-way F — an exact permutation F test with the unbiased
  `(1+hits)/(1+iters)` estimator.
- sha256-ordered sampling is an unbiased, deterministic PRF over content.
- `bh_qvalues` is a correct BH step-up with monotone enforcement.
- The Fisher-z Spearman CI (SE = 1.06/√(n−3)) is the standard approximation.
- Cross-dataset values reproduce from source data; only their interpretation needed fixing.
- Transfer-matrix orientation and figure-value provenance are correct to full float precision.
- **`caption_ceiling.json`'s 0.8262 is conservative**: its strata are contest-level (no
  outcome-conditioning), and its disjoint split-half arm is biased downward (independent-halves
  check: 0.775 vs 0.699) — which independently explains the receipt's own flagged
  estimator-disagreement warning of 0.1088.
- The project's standards hold in the new work: tied-midrank Spearman throughout, BH wherever
  multiple tests run, CIs beside every point estimate, negative results visible, truth boundaries
  on every receipt, and no corpus text in public receipts (hash-only, test-enforced).

**Recommendation: major revision** — applied in full as PR #38.

---

## Report 2 — consistency referee (summary of findings; all applied in PR #38)

Scope: the merged end state after PRs #34–#37 (~70 files touched).

- [HIGH] `docs/NOTEBOOKS.md` — a spliced sentence gave the display-only ceiling explainer the
  canonical notebook's antecedents ("runs the synthetic study-contract gate"); unspliced and
  moved to its own paragraph.
- [HIGH] `PROJECT_STATUS.md` — the ceiling v4 claim cited the v1-era receipt; now cites
  `notebook_refresh_publication.json` with the v1 record labeled historical.
- [HIGH] `PROJECT_STATUS.md` — internal contradiction on the Open Controls notebook version
  (table v4 vs prose v3); fixed.
- [MED] `JUDGE_EVIDENCE.md` — a "Current public release" heading still naming v14/tag v9;
  reworded as historical with the superseding versions.
- [MED] `tools/public_release_audit.py` — the recommended live audit still pinned tag v9; now
  audits v10 (re-run green, 16/16).
- [MED] ceiling builder docstring led with the unpublished live edition; README's "no
  live-session machinery" overclaimed the directory; both scoped precisely.
- [MED] `CHANGELOG.md` had an empty Unreleased section spanning four merged PRs; stanza added.
- [LOW] maintenance-log rows keyed/superseded correctly; palette-validator path reference
  removed; `RESULTS.md` v1 pointer forwarded; `.zenodo.json` version pinned with an explanatory
  note; the supporting-notebook table gained the ceiling notebook's row.
- VERIFIED CLEAN: all relative links (0 broken), all three committed notebooks (valid nbformat,
  no duplicate cell ids, well-formed tables, sections 1–9 unique and ordered), tag reality
  (v10 → the recorded merge commit), receipt paths, handoff command blocks, kernel metadata,
  and the 0.8.0 application-version sweep.
