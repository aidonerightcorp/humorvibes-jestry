# Jestry: a Verified Laugh-Reuse Layer, Built with Gemma

## Subtitle

Comedy already runs on reuse — bits, callbacks, formats, the canon. Jestry makes that
reuse visible, licensed, measured, and receipted: a constitution-governed layer over
the HumorVibes engine where Gemma 4 generates only the residual twist, every claim
carries a receipt, and "has this joke been done before?" is a first-class, multilingual
query.

## The idea in one paragraph

Software teams rediscovered this the hard way: the expensive part of building is
re-building what already works, and the dishonest part is claiming credit without
provenance. Jestry applies a verified work-reuse constitution (18 laws, machine-encoded
in `jestry.py`) to humor. A request is normalized, checked against hard policy (persona
B-gate, banned identity targets, dignity gate, roast consent), then routed down a
cost ladder: **replay an accepted bit → replay a validated compiled program → remix a
licensed corpus item → compose with retrieved mechanisms → frontier-compose → clarify
or abstain**. Replays cost zero model calls. Remixes spend one Gemma 4 adapter call and
carry the source's attribution forward. Fresh composition rides on retrieved mechanism
cards so the model writes only the residual. Every run emits a receipt with a
nine-stage contribution funnel, exact bit digests, model usage (unknown counts reported
as unknown, never zero), and a truth-boundary block. Rejected candidates become
groaners — hard negatives with the theory's failure taxonomy — that steer future
routes away.

## Has this joke been done before?

The precedent engine answers comedy's oldest provenance dispute (parallel thinking vs.
theft) the way a prior-art search should: at two levels, with scoped verdicts.
*Surface* similarity catches re-tellings; *frame* similarity — over Gemma-4-extracted
one-line frames — catches the same comic engine in new words. The index spans every
on-disk corpus item: harvested public jokes (three keyless APIs, per-record license),
Wikiquote wit, meme templates, and a curated multilingual proverb canon (20+
languages, public-domain folk material). The embedding backend is **embeddinggemma**
— a Gemma-family multilingual embedder — so the canon bridges languages: the query
"Even the most senior monkey falls out of the tree sometimes" retrieves the Korean
(0.71) and Japanese (0.70) "even monkeys fall from trees" as top neighbors, and "Man
plans and God laughs." resolves as a surface match with the Yiddish *Der mentsh trakht
un got lakht* at 0.849. Every verdict is open-world honest: "no precedent found
**within the indexed supply of N items**", and the offline hash backend states
outright that paraphrase precedent is not detectable in that mode. Accepted outcomes
get a precedent annotation in their receipt — reuse is the point; hidden reuse is the
only sin.

## Gemma 4 everywhere, honestly labeled

- **Generation, remixing, labeling, persona-B judging**: real `gemma4` through local
  Ollama, with token usage and prompt/output digests in every receipt.
- **Measured S/R/E via forced NLL**: Ollama now exposes top-K logprobs, and
  `gemma4_nll.py` reconstructs teacher-forced surprisal stepwise (maximal-munch path
  discovery, aligned replays for the frame and decoy-null passes, per-step censoring
  flags). The shakedown produced two receipted instrument findings: gemma4's
  copy-head **parrots suffix-placed frame hints** (the provider rewrites them to
  prefix layout, null control matched), and under top-20 censoring the reference
  jokes **do not separate from controls on R** — so the calibration receipt says
  `certified: false` and Jestry refuses to use this instrument's S/R/E for
  acceptance. Measured acceptance stays gated on the certified full-logprob
  instrument (the Kaggle transformers Gemma path). An instrument that documents its
  own disqualification is the credibility covenant working as designed.
- **Supply growth**: `harvest_supply.py` orchestrates the existing licensing-clean
  ingest lanes plus three keyless joke APIs and a clearly-stamped synthetic lane
  (Gemma 4's own output is indexed for *self*-precedent — the layer catches the
  generator repeating itself).

## Live portal

`jestry_portal.py` is a stdlib-only web portal (no pip installs): Run tab (route
compile + live loop with per-candidate verdicts), Been-done tab, Registry census and
card search, the full charter, and the groaner/north-star ledgers. The
`live_portal/` notebook boots it inside a Kaggle kernel and exposes it through a
Cloudflare quick tunnel (`*.trycloudflare.com`), announcing the URL on a
session-scoped ntfy channel — the same recipe as the verified studio kernel.

## The certified instrument, and the receipt that proves the thesis

Round three closed the measurement gap: a llama.cpp worker over the public
gemma-2-2b-it GGUF computes **full-vocabulary teacher-forced NLL locally** — the
same instrument family as the pinned Kaggle evidence, and it reproduces the
pinned speed-bumps measurement exactly (S=3.19). The certification protocol
(reference jokes must land inside a derived joint S/R region, controls must land
outside) **passed**, so this instrument — unlike the top-K-censored gemma4
readout, whose failed certification stays receipted beside it — is allowed to
gate acceptance. The first live accepted outcome followed immediately, and it
landed exactly where the charter predicts: not on frontier generation (whose
dense one-liners the instrument kept honestly rejecting) but on the **remix
route** — a licensed canon item, format-transferred by Gemma 4, carrying its
source's frame and attribution, accepted at `persona_permitted` and preserved as
a reusable registry card whose precedent annotation names its own source.
Reuse beat generation, on the record.

## Verification

`verify_jestry.py` gates the layer: 40 offline deterministic tests (registry census,
policy gates, ladder selection, carried acceptance, groaner incompatibility edges,
governed bandit promotion, funnel receipts, forced-NLL discovery/censoring/replay,
open-world precedent verdicts), registry digest determinism ×2, charter/code sync
(the 18 laws are pinned by test), a zero-model replay route, receipt schema, live
gemma4 end-to-end route, live cross-lingual precedent, harvest provenance, portal
boot, and byte-deterministic notebook builds. Latest run: **ALL GREEN (10/10)**.

## What this adds to HumorVibes

The pinned competition evidence (seven private COMPLETE kernels, the honest-negative
v4 ablation court, Humicroedit ρ=0.115) is untouched — its source hashes are pinned
by tests this layer must keep green. Jestry adds the missing economics on top: the
reuse ledger, the provenance discipline, the precedent index, and a governed path
from "Gemma said it's funny" (never sufficient) to "a measured room laughed"
(the only summit).
