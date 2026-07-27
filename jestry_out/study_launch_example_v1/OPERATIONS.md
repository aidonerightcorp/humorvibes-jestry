# Human-study launch operations

This pack is technically complete and reproducible. It is not institutional approval, legal
advice, consent, recruitment, or collected evidence. Current launch status:
`READY_FOR_EXTERNAL_ETHICS_AND_REGISTRATION`.

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
`fc9547272d7305c88d015b73fda64ac5cf81f7f261589e11e0c71abc0f716060`, and blinded schedule digest
`f5d23cedd3965e17c482bf8af2a1003563e70be94b97ee4423a9bf92f51b4d3d`. Confirm the analyst remained blinded, the stopping rule was
not outcome-driven, all deviations are published, and the analysis bundle contains no forbidden
fields.
