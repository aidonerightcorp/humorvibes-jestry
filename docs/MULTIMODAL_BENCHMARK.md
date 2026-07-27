# Multimodal caption benchmark

## Executive summary

Humor in a caption contest is a relation between words, a drawing, and an audience. A text-only
model cannot observe the drawing, and a random row split can leak the same drawing into training
and evaluation. This project now ships the complete experiment contract needed to avoid both
errors: whole-contest splits, rights metadata, exact and canonical-scene image hashes, identical
held-out rows for text-only/image-only/fusion arms, contest-level uncertainty, calibration, error
slices, and a machine-readable claim gate.

The checked-in run uses 30 project-generated SVG scenes and 600 deterministic synthetic captions.
It is a software and leakage test, not evidence that fusion improves humor prediction. There are
zero human captions, zero human ratings, and zero copyrighted cartoon drawings in the fixture.

![Multimodal evidence lanes and claim gate](figures/multimodal-evidence-lanes.svg)

## The problem this contract solves

A valid caption-plus-drawing comparison has to hold five things constant:

1. Every caption from one drawing belongs to exactly one train, validation, or test group.
2. Exact or canonically equivalent images cannot cross groups.
3. Text-only, image-only, and fusion systems must score the same held-out caption IDs.
4. The primary metric must compare captions within their own contest before aggregating contests.
5. Synthetic labels, model scores, and human judgments must remain separate evidence classes.

[`humorvibes/multimodal_benchmark.py`](../humorvibes/multimodal_benchmark.py) enforces those
conditions. It also reports five-bin calibration and error slices by caption strategy, synthetic
vote-count band, and repeated-caption status.

## Reproduce the rights-safe contract

The command below creates all SVGs, feature rows, hashes, grouped splits, and the final benchmark
receipt. It needs no network, model download, or proprietary data.

```bash
humorvibes multimodal-fixture \
  --out-dir jestry_out/multimodal_contract_v1 \
  --contests 30 \
  --force

humorvibes multimodal-benchmark \
  --root jestry_out/multimodal_contract_v1 \
  --out /tmp/multimodal-recheck.json
```

The committed example has 30 unique image hashes, 30 unique canonical scene signatures, 480
training rows, 60 validation rows, and 60 held-out test rows. All three arms share the held-out row
digest `f27ed4c97de1766046a88e33ed9ec36234ef1bd5a796d9b9f9ec9f860fb0218c`.

Its fusion arm scores higher than the text arm because the synthetic target was deliberately
constructed from text-by-scene interactions. That is a positive-control expectation and proves
the pipeline can recover its own known signal. It must not be quoted as a result about human
humor, model quality, or real drawings. The image-only arm has zero within-contest rank
correlation by construction: one fixed image cannot rank captions against itself.

## Replace the fixture with a real, rights-cleared study

Keep the file and receipt contracts, then replace only the evidence-bearing inputs:

- obtain drawing redistribution or research-use rights and record one licence/provenance row per
  image;
- hash the original image bytes and compute a reviewed near-duplicate signature before splitting;
- group every submission, vote, and image derivative by the stable contest ID;
- freeze the contests and primary metric before fitting any arm;
- derive the target from raw within-contest human votes, retaining vote counts and disagreement;
- generate text, image, and fusion features from declared model/version/dimension combinations;
- fit each arm on the same training contests and score the exact same held-out caption IDs;
- preserve failed arms, repeated captions, missing images, opt-outs, and exclusions in the receipt.

The existing caption analysis measured a real within-contest label ceiling of 0.8262 and an
estimated text portability bound of 0.4110. A real multimodal study should report every arm against
the label ceiling. The 0.4110 bound belongs only to the text-only arm; applying it to image or
fusion arms would be a category error. Neither real-data bound applies to the synthetic fixture.

## Acceptance gate for a real conclusion

A real run is still non-claim-ready until all of these are true:

- the image rights and source snapshot can be independently audited;
- whole-contest and image-identity leakage checks pass;
- the target is human-observed and its uncertainty is reported;
- model and feature provenance is exact, including preprocessing and dimensions;
- contest-level confidence intervals and predeclared error slices are complete;
- the run is reproduced from downloaded public or access-controlled research bytes;
- the receipt says exactly which population, drawings, and audience the conclusion covers.

Until then, the defensible claim is narrower: the project has a fully executable multimodal study
contract and a rights-safe positive-control fixture.
