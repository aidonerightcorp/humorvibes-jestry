# HumorVibes: Humor as Affordable Surprise, Measured with Gemma

## Subtitle

A theory-first humor engine. Gemma reads surprise off its own logits, tests jokes as prediction
errors with cheap permitted repairs, quantifies "vibe," compiles validation-gated material, and
adapts live sets to measured laughter.

## Track

Humor Understanding, with a creation studio, format library, compiled-performance layer, and
live-set controller.

## The theory

We started from Karl Friston's *"Your Brain Is a Detective Minimizing Surprise"*
(youtube.com/watch?v=g69Lj3huRvw): the brain is a mesh with weighted edges and sparse
ATP-budgeted firing, supervised by a meta-model that minimizes surprise. Our hypothesis:
**a joke is a controlled prediction error with a cheap, permitted repair.** The setup commits
the supervisor to a dominant path. The punchline is low-probability under it (surprise, S). A
hidden frame exists under which it snaps into place (resolution, R). The re-route must be
affordable (efficiency, E: one line of frame, not a paragraph) and permitted (bad surprise, B)
under the controlling definition, kept verbatim:

> Bad surprise is poorly defined, a bad surprise is a surprise that contradicts with internal
> models within a human brain that are so strong they override logic and are some of the primary
> drivers of a person's perception, understanding, and good/bad/moral/ethical views of the world.
> So basically, a surprise is not good if it disagrees with something that is already overriding
> logic or a surprise is not good it if disagrees with a nearly overwhelming generalization engine
> in a human mind that has significant overriding power to override logic, promote other false
> generalizations, and is the primary feature used to reduce surprise in that person's mind.

B is not a synonym for "offensive." It is audience-relative, so every check is persona-conditioned.
Each failure mode becomes diagnosable: predictable (low S), nonsense (high S, no frame), dissected
frog (frame too expensive), offense (B collision). Falsifiable predictions: THEORY.md.

## Gemma as instrument, not oracle

A causal LM is itself a predictive mesh, so we never ask Gemma to rate surprise. We read it off
the logits, teacher-forced. S = NLL(punchline | setup). R = the collapse a stated frame produces.
E = R per frame token. B = a persona-conditioned collision judged under the canonical definition.
One gemma-2-2b-it plays five roles: generator, instrument, frame-guesser, persona judge, editor.
The stack is Gemma end to end: Gemma 2 is the certified instrument, Gemma 4 generates candidates
and judges personas, EmbeddingGemma powers both retrieval channels, Gemma 3 enters the
frame-writer leaderboard.

The instrument survived three adversarial audits of its own design. First: asked for the frame of
nonsense, models confabulate, and conditioning on any text lowers NLL, so raw frame-collapse
credits a shuffled control. Raw R measured 2.37; the fix is a decoy-hint null control (R = raw
minus null), and the decoy measures 2.67 on that same nonsense, netting it to 0.00 while real
jokes keep their resolution. Second: a confabulated frame that lexically contains the punchline
predicts its text without reframing anything, and it beat the generic decoy in the zoo lab's
first run (2.23 on nonsense). The fix is a leak guard on frame/punchline overlap; in the verified
rerun all four frame-writers score the nonsense control 0.0.

Third, and measured tonight: on 30 native setup/punchline jokes with **model-written** frames,
resolution reversed, shuffled pairs beating genuine ones (AUC 0.41). Asked to explain a punchline
that does not belong to its setup, the model builds an elaborate bridge that collapses surprisal
harder than a real joke needs, and a fixed decoy cannot absorb a per-item confabulation. So R is
trustworthy exactly when the frame's provenance is. Our acceptance gate already required curated
frames; it now rests on a population, not one probe.

## Measured results (private verified Kaggle runs; RESULTS.md has the ledger)

- With given frames, jokes separate from controls as predicted. Boring continuations measure R
  0.07, nonsense dies under the nulls, and ground-truth frames measure R = 0.35 to 1.29 net of
  controls.
- Cross-instrument invariance, reproduced across kernel versions: Gemma-2 and Llama-3.2,
  measuring independently, produce the identical resolution ordering on the three fixed jokes.
  This is n=3 mechanism evidence, not a population-level claim.
- Frame-writing leaderboard across four keyless families: Llama-3.2-3B best (explanation deficit
  0.36 leak-guarded vs 0.47 for Gemma-2-2B and Qwen2.5-1.5B, 0.50 for Gemma-3-1B). Explanation
  quality scored in nats, not votes.
- Internet corpus census (30 jokes from public APIs): 8 puns break the naive S band (S up to 8.9)
  with R up to 2.32. A strong frame absorbs excess error, so the scorer judges the inverted-U on
  residual surprise (S minus R).
- Century portability: 12 jests from a 1916 jest book, frames written keylessly by Llama-3.2 and
  measured by Gemma. 3 still resolve today (top R = 0.73). Whether century-old humor is alive is
  measured, not assumed.

## What the system does

Generation is search: divergent candidates, kept only if measured (S,R,E,B) lands in the laugh
region. Eleven short-form formats act as timing envelopes, from one-liners and memes to beat
sheets, crowdwork, and roasts with a consent doctrine. Critic mode names which condition failed
and repairs only that.

Vibe instrumentation treats openness as continuation entropy (the room's risk budget) and measures
vibe-shift ΔV, so "killed the vibe" becomes a number. Off-vibe (reword) is diagnosed separately
from bad surprise (reframe). The live controller scores audience "audit clips" (WAV) with a
3-6 Hz laughter-burst detector; Thompson sampling exploits hot frames while exploring cold rooms.

Compiled comedy follows the Compiled-AI paradigm: Gemma drafts a slotted template; a static lint
whose banned-target rule structurally forbids identity-mesh punching rejected a malformed
template in the attached run; measured probe validation; then a frozen artifact with a content
hash. Runtime is a seeded RNG: zero model calls, auditable before it is ever performed. You
cannot let a model improvise a bad surprise on stage.

Adaptation changes the order, never the material, and writes an auditable show log.

De-escalation builds humor off-ramps for hostile comments: five strategies, an escalation lint,
and the gate no comeback tool has, B measured under the attacker's persona. A zinger is escalation
with better production values; when a real grievance is detected, fix the ticket first.

Callbacks are proved in nats, since quoting the source must collapse the punchline's surprisal,
and a dignity gate keeps vulnerable disclosures out of the material. The self-containedness gap
measures which cache a joke rents: canonical jokes resolve from what a culture durably knows,
topical jokes die with the news cycle. Ingestion stays licensing-clean, every record carrying
provenance and passing the persona gates.

## Multi-mesh scaling

Different judge models are differently-tuned audience meshes. The panel layer runs one judge per
family, reporting convergence per dimension. Divergence on bad-surprise risk is signal (insider
material), not noise.

## The genome, exported

The apparatus is also a dataset generator, so we ship what it produced: 14 comedy mechanisms and
11 format specs as primitives, 23,779 licensed items in 43 languages with 768-dimensional
**dual-channel** EmbeddingGemma vectors (surface wording and, separately, the comic frame), 270
Gemma-labeled frames, and 309 rows of teacher-forced S/R/E. Licensing is per record, and text is
withheld (metadata, labels and vectors kept) wherever a source's own terms say verify before
redistribution, so half the rows ship without text on purpose. Embedding the frame apart from the
words lets an English paraphrase retrieve the Korean and Japanese "even monkeys fall from trees"
at 0.89, and the Tamil elephant proverb at 0.63 with no shared surface words.

## What we learned

Humor diagnosis beats humor generation, and measurement beats self-report, but only with
adversarial controls. Ours failed three times and taught us the most every time. We also report
our hardest number. A predeclared, source-pinned court of 120 human-rated headline edits and 40
paired control triplets completed 200/200 Gemma measurements. Fixed S/R/E/B reached only
ρ=0.033 (95% bootstrap CI [-0.126, 0.207]); E alone was highest at ρ=0.099, also crossing zero.
Human edits did not significantly beat shuffled edits. Benign B did separate them (+0.100,
p=0.00216) yet did not track funniness (ρ=-0.072): safety is a constraint, not the objective.
That falsifies this fixed scalar as a general headline-humor ranker while pinpointing the
format boundary. So we ran that predeclared follow-up. Re-splitting each item at the edited word,
against the old splitter and a placebo cut (n=83), doubled how often resolution registered at
all, 19% of items to 31%, while the placebo moved nothing, and still predicted funniness no
better. The boundary is not a splitting artifact. Separately, the pinned S=3.19 held to 0.01
across a fourfold change in instrument precision, so it is not a quantization artifact either.

## Demo

Live studio (Streamlit over a Kaggle kernel tunnel), URL announced per session. Public notebooks:
measurement demo, mesh-zoo lab (invariance, frame duel, century test), corpus lab, panel lab,
validation lab, and the v4 ablation court. Every number above traces to an artifact in
`research_out/` or `jestry_out/`. A 13-gate verifier reproves the stack on demand; the portal is
browser-tested end to end. CLI: `mesh_cli.py {signals|vibe|generate|compile|live|...}`.
