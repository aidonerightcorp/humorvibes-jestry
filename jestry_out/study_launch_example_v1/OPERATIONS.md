# Human-study launch operations

This pack is technically complete and reproducible. It is not institutional approval, legal
advice, consent, recruitment, or collected evidence. Current launch status:
`REQUIRES_POWER_AND_EXTERNAL_ETHICS_REVIEW`.

## Required external gates before recruitment

- Obtain and archive the applicable ethics/IRB determination.
- Submit the preregistration draft and record its permanent HTTPS URI in the frozen protocol.
- Have the responsible institution approve accessible consent, withdrawal, compensation,
  complaint, adverse-event, and early-stop procedures.
- Assign named data-controller roles outside this public analysis pack.
- Put the identity-to-pseudonym linkage table in a separately access-controlled store.
- Confirm encryption, least-privilege access, retention timers, backups, and deletion tests.
- Pilot the blinded presentation flow without recording outcome-bearing human observations.

## Separation of duties

The facilitator may access the restricted condition map but must not rate outcomes. Writers receive
only their scheduled session instructions. Audience facilitators use the blinded audience schedule
and never the condition mapping. The analyst receives only the privacy-minimized bundle after the
collection window closes.

## Withdrawal and incident handling

The authorized study team resolves a withdrawal pseudonym through the separate linkage store,
deletes eligible source and export records, records the deletion event without direct identity, and
reruns validation. Pause collection after a consent failure, mapping disclosure, unauthorized
access, or material harm signal until the responsible reviewer documents a disposition.

## Pre-analysis integrity checks

Verify the protocol digest `cbf0c3d5572b5179ae80eac87a62b9e4e8113cad8ebf06b2e7854a64bba80751`, assignment digest
`9f57e9c73052dc13c738f1d5448b36f7bac72479595b39c72a5ab03ff4a4cb1e`, and blinded schedule digest
`27b361b0f1ffaa1dcfd8ccfd41d83a9582c2ff06bd0c4e99d04716e68b023dd8`. Confirm the analyst remained blinded, the stopping rule was
not outcome-driven, all deviations are published, and the analysis bundle contains no forbidden
fields.
