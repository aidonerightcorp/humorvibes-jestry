# Jestry: a Verified Laugh-Reuse Layer, Built with Gemma

## Subtitle

Comedy already runs on reuse: bits, callbacks, formats, the canon. Jestry makes that
reuse visible, licensed, measured, and receipted. It is a constitution-governed layer
over the HumorVibes engine where Gemma 4 generates only the residual twist, every
claim carries a receipt, and "has this joke been done before?" is a first-class,
multilingual query.

## The idea in one paragraph

Software teams rediscovered this the hard way: the expensive part of building is
re-building what already works, and the dishonest part is claiming credit without
provenance. Jestry applies a verified work-reuse constitution (18 laws, machine-encoded
in `jestry.py`) to humor. A request is normalized, checked against hard policy (persona
B-gate, banned identity targets, dignity gate, roast consent), then routed down a cost
ladder: replay an accepted bit, else replay a validated compiled program, else remix a
licensed corpus item, else compose with retrieved mechanisms, else frontier-compose,
else clarify or abstain. Replays cost zero model calls. Remixes spend one Gemma 4
adapter call and carry the source's attribution forward. Fresh composition rides on
retrieved mechanism cards so the model writes only the residual. Every run emits a
receipt with a nine-stage contribution funnel, exact bit digests, model usage (unknown
counts reported as unknown, never zero), and a truth-boundary block. Rejected
candidates become groaners, hard negatives tagged with the theory's failure taxonomy,
and they steer future routes away.

## Has this joke been done before?

The precedent engine answers comedy's oldest provenance dispute (parallel thinking vs.
theft) the way a prior-art search should: at two levels, with scoped verdicts.
Surface similarity catches re-tellings. Frame similarity, computed over
Gemma-4-extracted one-line frames, catches the same comic engine in new words. The
index spans every on-disk corpus item: harvested public jokes with per-record
licenses, Wikiquote wit, Gutenberg jest books and anecdote collections, meme
templates, per-language proverb collections, and a curated multilingual canon of
proverbs and classic joke formats (public-domain folk material across 40+ languages).
The embedding backend is embeddinggemma, a Gemma-family multilingual embedder, so the
canon bridges languages. The query "Even the most senior monkey falls out of the tree
sometimes" retrieves the Korean (0.71) and Japanese (0.70) "even monkeys fall from
trees" as top neighbors, and "Man plans and God laughs." resolves as a surface match
with the Yiddish *Der mentsh trakht un got lakht* at 0.849. Every verdict is
open-world honest: "no precedent found within the indexed supply of N items", and the
offline hash backend states outright that paraphrase precedent is not detectable in
that mode. Accepted outcomes get a precedent annotation in their receipt. Reuse is
the point; hidden reuse is the only sin.

## Gemma 4 everywhere, honestly labeled

Generation, remixing, labeling, and persona-B judging all run on real `gemma4`
through local Ollama, with token usage and prompt/output digests in every receipt.

Measured S/R/E arrives via forced NLL. Ollama now exposes top-K logprobs, and
`gemma4_nll.py` reconstructs teacher-forced surprisal stepwise (maximal-munch path
discovery, aligned replays for the frame and decoy-null passes, per-step censoring
flags). The shakedown produced two receipted instrument findings. Gemma4's copy-head
parrots suffix-placed frame hints, so the provider rewrites them to prefix layout
with the null control matched. And under top-20 censoring the reference jokes do not
separate from controls on R, so the calibration receipt says `certified: false` and
Jestry refuses to use this instrument's S/R/E for acceptance. Measured acceptance
stays gated on the certified full-logprob instrument (the Kaggle transformers Gemma
path). An instrument that documents its own disqualification is the credibility
covenant working as designed.

Supply growth runs through `harvest_supply.py`, which orchestrates the existing
licensing-clean ingest lanes plus keyless joke APIs, bulk community corpora passed
through a profanity/slur screen, a clearly-stamped synthetic lane (Gemma 4's own
output is indexed for self-precedent, so the layer catches the generator repeating
itself), and a session-authored multilingual/industry canon recalled from Claude's
training knowledge, stamped "traditional/anonymous (Claude-recalled)" per record.
API lanes are precedent-deduped on fetch.

## Live portal

`jestry_portal.py` is a stdlib-only web portal, no pip installs: a Run tab (route
compile plus live loop with per-candidate verdicts), the Been-done tab, Registry
census and card search, the full charter, and the groaner and north-star ledgers. The
`live_portal/` notebook boots it inside a Kaggle kernel and exposes it through a
Cloudflare quick tunnel (`*.trycloudflare.com`), announcing the URL on a
session-scoped ntfy channel, the same recipe as the verified studio kernel.

## The certified instrument, and the receipt that proves the thesis

Round three closed the measurement gap. A llama.cpp worker over the public
gemma-2-2b-it GGUF computes full-vocabulary teacher-forced NLL locally, the same
instrument family as the pinned Kaggle evidence, and it reproduces the pinned
speed-bumps measurement exactly (S=3.19). The certification protocol (reference jokes
must land inside a derived joint S/R region, controls must land outside) passed, so
this instrument is allowed to gate acceptance. The top-K-censored gemma4 readout is
not; its failed certification stays receipted beside it.

The first live accepted outcome followed immediately, and it landed exactly where the
charter predicts: not on frontier generation, whose dense one-liners the instrument
kept honestly rejecting, but on the remix route. A provenance-carrying canon item
(traditional/anonymous, recalled from model knowledge and stamped "verify attribution
before republication") was format-transferred by Gemma 4, carried its source's frame
and attribution, and was accepted and preserved as a reusable registry card whose
precedent annotation names its own source. Reuse beat generation, on the record.

An adversarial audit then caught the first acceptance's persona gate passing
vacuously (the judge model tag was absent). The record was corrected by an
append-only correction receipt, the gate now requires measured judgments, and the
outcome was re-earned at `persona_permitted` with four real persona judgments.

## Verification

`verify_jestry.py` gates the layer: the full offline test suite (42 tests, of which
30 pin the Jestry layer: registry census, policy gates, ladder selection, carried
acceptance, groaner incompatibility edges, governed bandit promotion, funnel
receipts, forced-NLL discovery/censoring/replay, open-world precedent verdicts, the
frame-provenance trust gate; the other 12 are the pre-existing pinned-evidence
suites), registry digest determinism twice over, charter/code sync (the 18 laws are
pinned by test), a zero-model replay route, receipt schema, a live Gemma end-to-end
route, live cross-lingual precedent, harvest provenance, portal boot, and
byte-deterministic notebook builds. Every run appends its gate table to
`jestry_out/verify_receipts.jsonl`, so "ALL GREEN" is a receipt, not a memory.

## What this adds to HumorVibes

The pinned competition evidence (seven private COMPLETE kernels, the honest-negative
v4 ablation court, Humicroedit ρ=0.115) is untouched; its source hashes are pinned by
tests this layer must keep green. Jestry adds the missing economics on top: the reuse
ledger, the provenance discipline, the precedent index, and a governed path from
"Gemma said it's funny" (never sufficient) to "a measured room laughed" (the only
summit).
