# The Jestry Charter and Constitution v1.0

**The HumorVibes verified laugh-reuse and construction layer**
**Charter date:** 2026-07-23
**Status:** canonical layer charter; implementation choices remain versioned
**Lineage:** a humor-native instantiation of the Taedri Charter and Constitution v2.0
(universal verified work-reuse), composed over the existing HumorVibes theory
(THEORY.md), instrument (`mesh_signals.py`), compiled-comedy pipeline
(`compiled_humor.py`), datacenter (`humor_datacenter/`), and live-set bandit
(`live_set_controller.py`). The normative machine-readable encoding of this
charter is `jestry.py` (`LAWS`, `FUNNEL_STAGES`, `ACCEPTANCE_LEVELS`); this
document explains it and must not drift from it.

> **Canonical motto**
> Find the laugh that already landed. Do not rebuild it. Compose any valid bit.
> Verify it against a measured audience. Learn from every bomb.

> **Strategic compact form**
> Jestry makes previously landed humor reusable and genuinely new humor
> progressively less expensive.

> **Comedian's compact form**
> Comedy already runs on reuse — bits, callbacks, formats, the canon. Jestry
> makes that reuse *visible, licensed, measured, and receipted.*

## 0. Version and scope statement

This charter governs the Jestry layer only. It does **not** amend, rescore, or
reinterpret the pinned HumorVibes competition evidence (the seven private
Kaggle kernels, `RESULTS.md`, `JUDGE_EVIDENCE.md`, the v4 ablation court). It
composes additively beside them (Law: evolution is additive and reversible).

Supersedes nothing; it is v1.0. Implementation choices that remain versioned,
not constitutional: the Ollama transport, the `gemma4` model tag, the
`embeddinggemma` backend, thresholds (`S_BAND`, collision ceiling 5.0,
precedent thresholds), the ladder ordering inside `RouteProfile`, and every
prompt string.

## 1. Constitutional purpose

Humor tooling fails in two directions: it **rebuilds** what the culture already
built (every "joke generator" reinvents misdirection nightly), and it
**overclaims** (a model's self-rated funniness presented as a laugh). This
constitution exists to prevent both:

1. Before generating, account for what already works — mechanisms, formats,
   validated programs, licensed corpora, the multilingual canon, previously
   accepted bits.
2. After generating, accept nothing without an independent oracle — measured
   S/R/E/B off real logits, the persona B-gate, and ultimately human laughter.

The value unit is **a landed laugh whose route can be reconstructed**: request,
retrieved supply, exact bindings, model usage, measured signals, persona
permission, and acceptance level — all in one receipt.

## 2. Canonical layer description

Jestry receives a humor request and:

1. normalizes it into a `WorkSpec` (topic, audience, format contract, personas,
   consent, unknowns);
2. checks hard policy first (`HumorPolicy`) — banned identity targets, the
   dignity gate for vulnerable disclosures, roast consent;
3. searches body-free `BitCard`s over the unified supply registry;
4. compiles the cheapest eligible route on the ladder:
   `replay_accepted → replay_program → remix_corpus → compose_residual →
   frontier_compose`, else clarifies or abstains;
5. executes it — replays cost **zero model calls**; remixes spend one adapter
   call; only genuine residuals spend fresh Gemma 4 reasoning;
6. verifies candidates against the instrument (teacher-forced S/R/E/B when the
   forced-NLL provider is up) and the persona B-gate;
7. checks precedent — *has this been done?* — at surface and frame level, and
   records the verdict in the receipt rather than hiding the reuse;
8. ledgers every rejected candidate as a groaner with its failure mode;
9. preserves every accepted outcome as a new reusable bit, so the next related
   request is cheaper; and
10. reports cost as a failure-inclusive **vector** (runs, escalations, calls,
    tokens, unknown-usage counts, wall time), never a lone scalar.

## 3. The three pillars, humor-native

### Pillar 1 — The value unit is a landed laugh

Not a generated joke, a retrieval hit, a mesh score, or a model's self-report.
An outcome counts when an independent oracle accepted it at a named level, and
its receipt reconstructs the route that produced it.

### Pillar 2 — Search proposes; contracts compose; laughter decides

```text
retrieval and Gemma propose
  -> format contracts decide what can compose
  -> HumorPolicy decides what is permitted (never traded away)
  -> exact bit ids + digests decide what executes
  -> measured S/R/E/B decides what survives the instrument
  -> the persona B-gate decides what is permitted for THIS audience
  -> laughter (live bandit reward) decides what is true
```

Similarity is not compatibility (a Twain quote is not a meme caption until the
adapter passes the format contract). A Gemma judgment is not a human laugh
(`truth_boundary.model_judgment_is_not_human_laughter` is stamped on every
receipt).

### Pillar 3 — Escalate the bit before the model

Replay costs nothing. A seeded template costs nothing. A remix costs one
adapter call. Fresh composition is last, and even then the prompt carries the
retrieved mechanism moves so Gemma writes **only the residual twist** (Law 2).
Escalations between rungs are explicit receipt entries, never silent.

## 4. Credibility covenant

Product-breaking defects, inherited verbatim from Taedri and enforced here:

- a self-rated score presented as measurement;
- an offline-stub number presented as a Gemma measurement (`measured=False`
  flags are load-bearing);
- a censored logprob presented as exact (`nll_may_be_lower_bound` rides the
  receipt);
- hidden reuse — a retold bit without its precedent named (that is the theft
  side of the parallel-thinking line);
- unrecorded model usage (unknown token counts are reported as unknown, never
  as zero);
- a replay claimed as fresh construction, or construction claimed as replay;
- a "no precedent" verdict stated without its index scope ("within the indexed
  supply of N items" is the only honest form); and
- rewriting pinned historical evidence.

## 5. The eighteen laws

The normative text lives in `jestry.py::LAWS` (18 entries; the test suite pins
the count). Names, in constitutional order:

1. **Find the funny that already works** — supply first; ignorance is a defect.
2. **Generate only the residual twist** — retrieved mechanisms ride the prompt.
3. **Reuse is selective, not compulsory** — replay, remix, fresh, clarify, and
   abstain are all valid outcomes.
4. **The value unit is a landed laugh** — Pillar 1.
5. **Search proposes; contracts compose; laughter decides** — Pillar 2.
6. **Escalate the bit before the model** — Pillar 3.
7. **Preference and permission are separate** — the B-gate, banned-target lint,
   dignity gate, and consent are not tunable preferences.
8. **Identity is exact and versioned** — bit ids, digests, model tags, prompt
   hashes; a remix names its source and license.
9. **Contribution must be traced** — the nine-stage funnel
   (`discovered → retrieved → selected → resolved → composed → told →
   instrument_scored → persona_gated → accepted`); invocation ≠ contribution.
10. **External laughter is the final authority** — instrument acceptance is a
    stage, not the summit; `human_laughed` and `crowd_accepted` sit above it.
11. **Evolution is additive and reversible** — new rungs and providers arrive
    beside working paths; pinned evidence is never rewritten.
12. **Every bomb becomes reusable knowledge** — the groaner ledger records the
    theory's failure taxonomy (predictable / no re-route / too expensive /
    bad surprise) and mints incompatibility edges that steer future routes.
13. **Self-tuning is governed** — laughter updates a shadow posterior; serving
    order changes only through an explicit, receipted `promote()`.
14. **No hidden fallback** — every escalation, stub, substitution, and censored
    measurement is named in the receipt.
15. **Originals remain reconstructable** — remix receipts carry the source
    text; artifacts keep probe history; prompts and outputs are hashed.
16. **Clarification is a first-class route** — unknowns (missing audience,
    missing consent) surface as questions or explicit assumptions.
17. **The room is a registered context, not the core** — Kaggle, a NYC
    showcase, a Slack channel: each supplies personas, formats, and oracles;
    the loop stays universal.
18. **Honest abstention beats confident bombing** — policy-prohibited,
    instrument-unavailable, and no-compatible-supply are first-class receipts.

## 6. Canonical object ontology

| Taedri object | Jestry object | Where |
|---|---|---|
| `SourceSnapshot` / `WorkSpec` | `WorkSpec` (topic, audience, format, personas, consent, unknowns) | `jestry.py` |
| `PolicyContext` | `HumorPolicy` (hard gates) | `jestry.py` |
| `ProfileIntent` | `RouteProfile` (ladder, temperatures, require_measured) | `jestry.py` |
| `CapabilityCard` | `BitCard` (body-free; kind ∈ mechanism, format, corpus_item, joke_program, joke) | `jestry.py` |
| `Primitive` | comedy mechanism (14 registered) | `humor_datacenter/mechanisms.py` |
| Contract | format timing envelope (11 registered) | `formats.py` |
| `Route capsule` | frozen `JokeProgram` (compile-time Gemma, seeded zero-model runtime) | `compiled_humor.py` |
| `Adapter` | format-transfer remix (licensed source + attribution) | `jestry.py::REMIX_PROMPT` |
| `RouteIR` | `RouteIR` (rung, compat verdict, nodes with digests and bindings) | `jestry.py` |
| `Validator` / oracle | `compute_signals` S/R/E/B + persona B-gate + laughter reward | `mesh_signals.py`, `live_set_controller.py` |
| Instrument | forced-NLL Gemma 4 provider (top-K teacher forcing, censoring flagged) | `gemma4_nll.py` |
| `Receipt` | route receipt with funnel, usage, truth boundary | `jestry_out/receipts.jsonl` |
| Failure certificate | groaner ledger entry + incompatibility edge | `jestry_out/groaners.jsonl` |
| `AcceptedOutcome` | preserved bit (compounding supply) | `jestry_out/accepted_bits.jsonl` |
| Prior-work search | precedent index (surface + frame channels, multilingual) | `precedent.py` |
| Governed learner | `LaughLoop` (shadow vs serving, receipted promotion) | `jestry.py` |

Compatibility verdicts are Taedri's, verbatim: `EXACTLY_COMPATIBLE`,
`COMPATIBLE_WITH_BINDING`, `COMPATIBLE_WITH_ADAPTER`, `REQUIRES_RUNTIME_PROBE`,
`INCOMPATIBLE`, `PROHIBITED_BY_POLICY`, `UNKNOWN`.

## 7. The precedent doctrine ("has this joke been done?")

Comedy's oldest provenance dispute — parallel thinking vs. joke theft — is a
**visibility** problem, and Jestry treats it exactly as Taedri treats prior
work:

- **Two channels.** *Surface* similarity catches re-tellings of the same
  wording. *Frame* similarity (over Gemma-4-extracted one-line frames) catches
  the same comic engine in new words — which is still precedent, and often
  still fine, provided it is *named*.
- **Multilingual canon.** The supply registry carries traditional proverbs and
  idioms across 20+ languages (public-domain folk material with per-record
  license and gloss). The semantic backend (`embeddinggemma`, a Gemma-family
  multilingual embedder) bridges languages: the Korean and Japanese
  "even monkeys fall from trees" resolve as neighbors of an English paraphrase.
  Canonical material rents a population-wide cache (THEORY.md §10–11); the
  index makes that cache searchable.
- **Labeling is selective enrichment.** Gemma 4 labels items on demand
  (mechanisms, frame, language, cultural cache, taboo topics) with the labeler
  recorded; labels are derived data, never a precondition for indexing
  (Taedri §20.3).
- **Open-world honesty.** Every verdict is scoped to the indexed supply and
  names its backend; the offline hash backend states that paraphrase precedent
  is *not detectable* in that mode. A novelty claim beyond the index is a
  defect.
- **Precedent annotates; it does not veto.** Reuse is the point of the whole
  layer. The check exists so reuse is *visible* in the receipt and the
  preserved bit — hidden reuse is the only sin.

## 8. Acceptance levels and evidence maturity

Acceptance labels stay distinct (never collapsed):

```text
drafted < lint_passed < instrument_scored < persona_permitted
        < human_laughed < crowd_accepted
```

- `instrument_scored` — measured S/R/E/B in the laugh region (real logits only;
  offline stubs cannot reach this level).
- `persona_permitted` — B-gate evaluated under the request's personas and
  passed.
- `human_laughed` — a live laughter reward was measured for this bit.
- `crowd_accepted` — repeated acceptance across distinct rooms.

Evidence maturity (claims stay inside their level):

| Level | Humor meaning |
|---|---|
| L0 | Infrastructure fact (the portal boots; the tunnel answers). |
| L1 | One measured observation (this joke's S/R/E/B on this instrument). |
| L2 | Replicated on one frozen set (the three fixed jokes, twice). |
| L3 | A task family (a format, an audience type). |
| L4 | Held-out human-rated portfolio. |
| L5 | Cross-audience, cross-format estimate. |

The strongest human-validation number in this repository remains **negative**
(v4 ablation court: fixed S/R/E/B ρ=0.033, CI crossing zero, on headline
edits) and is carried forward, not buried: it is why acceptance levels above
`persona_permitted` require *human* signal, and why the format boundary
(explicit setup/punchline vs. headline edits) is written into the competition
design below.

## 9. Measurement constitution

Report the vector; never one scalar (`Jestry.north_star_vector()`):

- runs, accepted runs, abstained runs, escalations;
- route-kind mix (how often replay beat construction);
- zero-model-call accepts (the reuse dividend);
- oracle calls (NLL / judge / generate) and forced-NLL API calls;
- generation tokens with `calls_with_unknown_usage` counted, never zeroed;
- measured-signal runs vs. total; wall time; groaners recorded.

A savings claim requires the same frozen request set, the same instrument, and
both arms accepted — attempts stay in the denominator.

## 10. Dated evidence snapshot — not constitutional law

Repository-local measurements as of 2026-07-23. Superseded by later receipts;
never generalized beyond stated scope.

1. **The 2026-07-11 transport boundary closed; certification honestly failed
   (L1).** Ollama now returns per-token `logprobs` (top-K ≤ 20), and
   `gemma4_nll.py` reconstructs teacher-forced continuation NLL by stepwise
   top-K readout — maximal-munch tokenization with degenerate-whitespace
   rejection, path caching for aligned framed/null replays, retry-hardened
   transport (zero errors in the final runs), and per-step censoring flags.
   Two instrument findings came out of the shakedown, both receipted:
   (a) **the copy-attractor** — gemma4's copy-head parrots a suffix-placed
   frame hint (framed `' the'` = 0.00 nats, all else ≈10), so the provider
   rewrites hint contexts to prefix layout, decoy null included; and
   (b) **certification failure** — under top-20 censoring the reference jokes
   do not separate from controls on R (jokes 0.00/0.31/0.00 vs boring control
   0.73 via a confabulated frame; nonsense 0.00), so
   `jestry_out/gemma4_calibration.json` records `certified: false` and Jestry
   never uses this instrument's S/R/E for acceptance decisions. Gemma 4
   generation, persona-B judging, and labeling remain real and receipted;
   measured S/R/E **acceptance** stays gated on a certified full-logprob
   instrument (the Kaggle transformers Gemma path, where the original bands
   were validated). An earlier same-day smoke that read net R=0.44 for the
   speed-bumps joke is superseded: its discovery path used the fragmented
   tokenization later fixed, and it is retained only as version history.
2. **Semantic cross-lingual precedent works (L1).** With `embeddinggemma`
   (125 indexed items), the paraphrase "Even the most senior monkey falls out
   of the tree sometimes" retrieves the Korean (0.71) and Japanese (0.70)
   originals as top neighbors; "Man plans and God laughs." resolves as
   `surface_match` with the Yiddish `Der mentsh trakht un got lakht` at 0.849.
   Thresholds are calibrated per backend and remain versioned choices.
3. **The layer's loop is test-pinned (L0).** 28 offline deterministic tests
   cover the registry census, policy gates, ladder selection, carried
   acceptance on replay, groaner edges steering retrieval, governed bandit
   promotion, funnel receipts, forced-NLL discovery/censoring/replay, and
   open-world precedent verdicts.
4. **Carried forward unchanged:** the seven private COMPLETE kernels, the v4
   ablation court's honest negative, the Humicroedit ρ=0.115 weak positive,
   and the 2026-07-11 `gemma4` generation receipt with its truth-boundary
   block. This charter adds routes and receipts *around* that evidence.
5. **2026-07-24 — a certified local instrument and the first live accepted
   outcome (L1/L2).** `gemma2_full_nll.py` restores the certified measurement
   regime locally: full-vocab teacher forcing on the public gemma-2-2b-it
   GGUF (llama.cpp worker), reproducing the pinned Kaggle measurement of the
   speed-bumps joke exactly (S=3.19), zero censoring. Certification PASSED
   under the joint region with the residual-surprise rule (jokes R
   0.08/0.12/0.44 vs controls 0.00/0.00) —
   `jestry_out/gemma2_full_nll_calibration.json`, `certified: true`.
   Challenger sweeps on the gemma4 top-K readout remain negative and
   retained; `gemma4:e2b` is receipted as transport-unusable (EOS-boundary
   logprob omission). With the certified instrument judging, the first live
   accepted outcome landed on the **remix route** — a canon item's format
   transfer accepted at `persona_permitted` (laugh 51.8, measured), preserved
   as a registry card, its precedent correctly annotated as a surface match
   of its own attributed source — while frontier generation kept honestly
   rejecting. Reuse beat generation, on the record.

## 11. What Jestry is not

- not a joke generator (generation is its **last** rung);
- not a funniness oracle (the instrument selects; laughter accepts);
- not a plagiarism accuser (precedent verdicts are scoped, two-channel, and
  informational);
- not a safety filter (the B-gate is audience-relative permission under the
  canonical bad-surprise definition, not a topic blocklist);
- not a replacement for the pinned HumorVibes evidence (it composes beside it).

## 12. Constitutional test for every feature

Before adding or defaulting a feature, ask (fail any → do not ship):

1. Does it help land an accepted laugh, or make the next one cheaper?
2. Does it find or reuse material that already works?
3. Does it preserve exact identity, license, and provenance?
4. Can its contribution be traced in the funnel?
5. Does it keep permission separate from preference?
6. Does it flag every unmeasured, censored, or stubbed value?
7. Does it leave reusable knowledge behind on failure?
8. Can it clarify or abstain honestly?

## 13. Amendment rule

Clarify-and-extend, never casually. An amendment must preserve the three
pillars, the credibility covenant, and the permission/preference separation;
must version itself; must state which prior language it changes; and must not
invalidate historical receipts. Model tags, thresholds, prompts, backends, and
ladder orderings are versioned implementation choices and do not require
amendments — changing `jestry.py::LAWS`, `FUNNEL_STAGES`, or
`ACCEPTANCE_LEVELS` does.
