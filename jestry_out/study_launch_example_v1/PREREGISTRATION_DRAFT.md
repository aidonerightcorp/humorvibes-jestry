# Preregistration draft: Within-writer HumorVibes assistance crossover

Status: **not registered**. This complete draft must be submitted to a timestamped registry and
approved through the applicable ethics process before observations begin. Its protocol digest is
`cbf0c3d5572b5179ae80eac87a62b9e4e8113cad8ebf06b2e7854a64bba80751`.

## Research question and comparison

For Consenting comedy writers and held-out consenting audience members, compare HumorVibes-assisted and control material within the
same writer and paired premise. The single primary outcome is `audience_rating`;
positive effects follow the direction declared in the frozen analyzer.

## Primary hypothesis and useful-effect threshold

The confirmatory alternative is that the writer-clustered assisted-minus-control effect on the
primary outcome exceeds 0.25. The rating scale is
1.0 to 5.0. All other outcomes are secondary.

## Design, randomization, and blinding

This is a paired within-writer crossover. Each analyzable writer contributes
2 paired premises. Assignment uses seed
    20260726 plus a separately stored private key committed by SHA-256;
condition mappings live only in the restricted map. Audience panel
members receive one version of each writer-premise block, never both, through blind material IDs.

## Prospective planning assumptions

- Two-sided alpha: 0.05
- Target power: 0.8
- Anticipated effect: 0.5
- Claim threshold: 0.25
- Effect above the claim threshold used for planning: 0.25
- Between-writer SD: 0.45
- Within-writer premise SD: 0.6
- Analyzable writers: 49
- Writers to recruit after declared attrition: 62
- Planned probability of retaining the analyzable writer count:
  0.927
- Minimum paired writer-premise blocks: 98

These are prospective assumptions, not observed power. The generated hierarchical sensitivity
analysis did not automatically authorize registration or recruitment. Its most conservative
checked scenario is `conservative_rating_noise` and its normal-approximation advisory calls for
80 analyzable writers,
99 recruited writers, and
1280 ratings. A statistician and the
responsible ethics process must choose and freeze the governing scenario before registration.

## Inclusion, exclusion, and stopping

Include only permission-confirmed material and consent-confirmed, held-out audience responses that
validate against schema 1.0. Exclude malformed records, incomplete paired
blocks, non-finite or out-of-range outcomes, duplicate IDs, unconsented responses, and material
without a rating. Stop after the frozen minimum counts and collection window are met; do not inspect
condition effects to choose the stopping point. Report exclusions by machine-readable reason.

## Analysis

Pair control and assisted material within writer and premise; aggregate audience ratings to material before comparison; bootstrap writer-level effects; report all outcomes and gate claims on the preregistered minimally important difference. Use 5000 bootstrap repetitions and seed
20260726. Report the point estimate, 95% interval, minimum useful effect,
sample units, secondary descriptives, harm/regret outcomes, and every failed claim gate.

## Privacy, consent, and retention

Pseudonymous outcomes only; no raw joke text or direct identity in the analysis export; delete the linkage table on the consent schedule. Raw material, prompts, direct identity, contact information,
protected-trait inference, and linkage tables remain outside the analysis export. Withdrawal and
deletion requests are resolved against the separate linkage store by the authorized study team.

## Deviations and reporting

Publish all deviations as dated amendments before the affected analysis when possible. Label any
analysis changed after outcome inspection as exploratory. A passing gate authorizes only a bounded
claim about the named population, context, outcome, comparison, effect, and interval; it never
authorizes a universal claim that material is funny.
