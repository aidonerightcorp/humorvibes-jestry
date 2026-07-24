# HumorVibes: Humor as Affordable Surprise, Measured with Gemma

## Subtitle

A theory-first humor engine: Gemma reads surprise off its own logits, tests jokes as prediction
errors with cheap permitted repairs, quantifies "vibe," compiles validation-gated material, and
adapts live sets to measured laughter.

## Track

Humor Understanding — with a creation studio, format library, compiled-performance layer, and
live-set controller built on the understanding engine.

## The theory

Derived from Karl Friston's *"Your Brain Is a Detective Minimizing Surprise"*
(youtube.com/watch?v=g69Lj3huRvw): the brain is a mesh of dynamic neural networks — weighted
edges, sparse ATP-budgeted firing, tunable paths — supervised by a meta-model that minimizes
surprise. Our hypothesis: **a joke is a controlled prediction error with a cheap, permitted
repair.** The setup commits the supervisor to a dominant path; the punchline is low-probability
under it (**surprise S**); a hidden frame exists under which it snaps into place (**resolution
R**); the re-route must be affordable (**efficiency E** — one line of frame, not a paragraph);
and it must be permitted (**bad surprise B**) under the controlling definition, kept verbatim:

> Bad surprise is poorly defined, a bad surprise is a surprise that contradicts with internal
> models within a human brain that are so strong they override logic and are some of the primary
> drivers of a person's perception, understanding, and good/bad/moral/ethical views of the world.
> So basically, a surprise is not good if it disagrees with something that is already overriding
> logic or a surprise is not good it if disagrees with a nearly overwhelming generalization engine
> in a human mind that has significant overriding power to override logic, promote other false
> generalizations, and is the primary feature used to reduce surprise in that person's mind.

This is not "offensive/edgy": B is audience-relative, so every check is persona-conditioned. Each
failure mode becomes diagnosable — predictable (low S), nonsense (high S, no frame), dissected
frog (frame too expensive), offense (B collision). Full theory, with falsifiable predictions:
THEORY.md (§8 defines **vibe** = the mesh's tuning state — register axes, openness entropy,
drift; §9 de-escalation; §10 callbacks/canon; §11 temporal mechanics).

## Gemma as instrument, not oracle

A causal LM *is* a predictive mesh, so we never ask Gemma to rate surprise — we read it off the
logits, teacher-forced: S = NLL(punchline | setup); R = the collapse a stated frame produces;
E = R per frame token; B = persona-conditioned collision judged under the canonical definition.
One gemma-2-2b-it plays five roles: generator, instrument, frame-guesser, persona judge, editor.

**The instrument survived two adversarial audits of its own design.** First, asked for the frame
of *nonsense*, models confabulate — and conditioning on any text lowers NLL — so raw frame-collapse
credits a shuffled control: raw R=2.37 in the verified run. Fix: a decoy-hint **null control**
(R = raw − null) — the decoy measures 2.67 on the same nonsense, netting it to 0.00 while real
jokes keep their resolution (first caught in this notebook's v4→v5 history: 1.60 → 0.34). Second,
a confabulated frame that lexically contains the punchline predicts its text without reframing
anything and beat the generic decoy in the zoo lab's first run (2.23 on nonsense). Fix: a **leak
guard** discounting frame/punchline overlap — in the verified rerun, all four frame-writers score
the nonsense control 0.0. Measurement plus controls, twice over.

## Measured results (private verified Kaggle runs; RESULTS.md has the ledger)

- **Jokes separate from controls** as predicted: boring continuations measure near-zero R (0.07);
  nonsense dies under the nulls (raw 2.37 − null 2.67 → 0.00); ground-truth frames measure
  R = 0.35–1.29 net of controls.
- **Cross-instrument invariance (reproduced across kernel versions)**: Gemma-2 and Llama-3.2,
  measuring independently, produce the *identical* resolution ordering on the three fixed jokes.
  This is n=3 mechanism evidence, not a population-level invariance claim.
- **Frame-writing leaderboard** across four keyless families: Llama-3.2-3B best (explanation
  deficit 0.36 leak-guarded vs 0.47 for Gemma-2-2B and Qwen2.5-1.5B, 0.50 for Gemma-3-1B; in the
  earlier unguarded run it beat hand-written ground-truth frames on 2 of 3 jokes) — explanation
  quality scored in nats, not votes.
- **Internet corpus census** (30 jokes from public APIs): 8 puns break the naive S band (S up to
  8.9) with R up to 2.32; a strong frame absorbs excess error, so the scorer judges the inverted-U
  on **residual surprise (S − R)**. Format-transfer remixing kept 3 of 6 transfers (an all-caps
  pun survived as a meme caption, R 2.32→1.37) and correctly failed the rest.
- **Century portability**: 12 jests sampled from a 1916 public-domain jest book, frames written
  keylessly by Llama-3.2 and measured by Gemma — 3 still resolve today (top R = 0.73). Whether
  century-old humor is alive is measured, not assumed.

## What the system does

**Generate as search**: divergent candidates, kept only if measured (S,R,E,B) lands in the laugh
region. **Eleven short-form formats** as timing envelopes (one-liners, memes, 15-second beat
sheets, stand-up bits with tags-as-cheap-re-routes, crowdwork, roasts with consent doctrine…).
**Critic mode** names which condition failed and repairs only that. **Vibe instrumentation**
(§8): register coordinates on six contrast axes, openness as continuation entropy (the room's
risk budget), and vibe-shift ΔV — "killed the vibe" as a measurement; off-vibe (reword) is
diagnosed separately from bad surprise (reframe). **Compiled comedy** (after the Compiled-AI
paradigm): a four-stage pipeline — Gemma drafts a slotted template; static lint (a banned-target
rule structurally forbids identity-mesh punching — it correctly rejected a malformed template in
the attached run); measured probe validation; frozen artifact with content hash. Runtime is a
seeded RNG: zero model calls, reproducible, auditable before it is ever performed — you cannot
let a model improvise a bad surprise on stage. **Live set controller**: audience "audit clips"
(WAV) scored by a 3–6 Hz laughter-burst detector; Thompson sampling over frozen artifacts
exploits hot frames (callbacks are cheap re-routes through a frame the room cached) and explores
cold rooms; adaptation changes the order, never the material, with a JSONL show log.
**De-escalation** (§9): humor off-ramps for hostile comments — five strategies, an escalation
lint, and the gate no comeback tool has: B measured under the *attacker's* persona (a zinger at
them is escalation with better production values), plus "fix the ticket, then the vibe" when a
real grievance is detected.
**Callbacks & canon** (§10): mine a speaker's distinctive prior lines, then *prove* a callback in
nats — quoting the source must collapse the punchline's surprisal — with a dignity gate
(vulnerable disclosures are never material). **Temporal mechanics** (§11): the self-containedness
gap measures which cache a joke rents — canonical jokes resolve from what a culture durably
knows; topical jokes die with the news cycle — predicting the comedic sweet-spot curve from the
primitives. **Licensing-clean ingestion**: Wikiquote, public-domain 1916 jest books (a
century-portability test), RSS headlines, user transcripts, meme-template APIs — every record
carries provenance and passes the persona gates before remixing.

## Multi-mesh scaling

Different judge models are differently-tuned audience meshes. The panel layer runs one judge per
family — locally (four Kaggle-hosted families, no keys) or hosted (Ollama Cloud, NVIDIA, Mistral,
Gemini via Kaggle's built-in credits, OpenRouter) — reporting convergence per dimension and a
portability matrix; divergence on bad-surprise risk is signal (insider material), not noise.

## What we learned

Humor diagnosis beats humor generation; measurement beats self-report — but only with adversarial
controls, which failed twice and taught us the most both times. We also report our hardest
number: a predeclared, source-pinned court of 120 human-rated headline edits and 40 paired control
triplets completed 200/200 Gemma measurements. Fixed S/R/E/B reached only ρ=0.033 (95% bootstrap
CI [-0.126, 0.207]); E alone was highest at ρ=0.099, also crossing zero. Human edits did not
significantly beat shuffled edits on the full score. Benign B did separate them (+0.100,
p=0.00216) yet did not track funniness (ρ=-0.072): safety is a constraint, not the objective.
That falsifies this fixed scalar as a general headline-humor ranker while pinpointing the
format boundary: headline substitutions often defeat setup/punchline inference. Next we test
format-aware R/E on explicit setups and keep B separate.

## Demo

Live studio (Streamlit over a Kaggle kernel tunnel; Vibe, Live Set, Compiled, Measured Signals
tabs) — current URL announced per session. Planned public notebook attachments: measurement demo, mesh-zoo lab
(invariance + frame duel + century test), corpus lab (census + remixing), panel lab (frame duel;
hosted-panel harness, keys-gated), validation lab (Humicroedit human-grades check), and the v4
ablation court. Every number
above traces to a run artifact mirrored in the repo's `research_out/`. CLI:
`mesh_cli.py {signals|vibe|generate|critique|compile|run-compiled|live|deescalate|callback|
history-remix|temporal|ingest|panel}`.
