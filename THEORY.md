# The Humor Genome Theory: Comedy as Affordable Surprise in a Mesh of Predictive Networks

*The theoretical foundation of HumorVibes. This document is the canonical statement of the theory;
the writeup summarizes it, `mesh_signals.py` implements it, and the Kaggle notebook demonstrates it.*

## 1. Origin: the brain as a surprise-minimizing mesh

This work is a derivative of the framing in Karl Friston's talk **"Your Brain Is a Detective Minimizing
Surprise"** (https://www.youtube.com/watch?v=g69Lj3huRvw) and the free-energy principle behind it,
restated in network terms:

- The brain is **a network of dynamic neural networks** — meshes of sub-networks, not one monolith.
- Connections carry **strengths**; not all nodes fire at once. Activation is **sparse**, because dense
  firing in a 3D volume of tissue is metabolically impossible — **ATP is the budget**, so the system
  routes cheap, narrow paths through the mesh rather than lighting everything up.
- These meshes are **tunable**: paths and connections get strengthened by use and prediction success,
  minimized or broken by disuse and prediction failure. Communication between meshes is itself learned.
- Above the meshes sits a **supervisor — a model of models (a meta-model) whose objective is to reduce
  surprise**. It continuously predicts what the sub-networks will report next, and it treats prediction
  error as a cost to be minimized, either by updating the model or by acting on the world.

Two consequences matter for humor:

1. **Every moment of comprehension is a bet.** The supervisor pre-activates the expected continuation —
   a narrow, cheap, high-strength path. That bet is what a joke's setup manipulates.
2. **Some meshes outrank others.** Deep meta-meshes — identity, morality, worldview, the frames a person
   uses to interpret everything else — have such strong connection weights that they can **override
   logic itself**. They are the primary machinery a mind uses to reduce surprise. The supervisor will
   not accept an interpretation that contradicts them, no matter how locally clever it is.

## 2. The theory: a joke is a controlled prediction error with a cheap, permitted repair

A joke has two parts: a **setup** C and a **punchline** P.

- The setup drives the supervisor down a dominant path: it predicts a continuation distribution.
- The punchline is **deliberately low-probability under that dominant path** — a real prediction error.
  This is **surprise (S)**.
- But a working punchline is not noise. There exists an **alternate frame F** — a second path through
  the mesh that was weakly, sparsely pre-activated by the setup — under which P is suddenly
  high-probability. The "getting it" moment is the supervisor **re-routing** from the dominant path to
  F. This is **resolution (R)**.
- The re-route must be **affordable**. If reaching F takes too many hops — too much explanation, too
  much working memory, too much ATP — the error resolves as confusion or as a joke that dies when
  explained. This is **efficiency (E)**: the resolution per unit of repair work.
- Finally the re-route must be **permitted**. If frame F collides with a high-authority meta-mesh —
  the ones with override power over logic — the supervisor refuses the reframe. The prediction error
  never resolves as play; it resolves as threat, offense, or anger. This is **bad surprise (B)**.

**Laughter is the reward signal for a cheap, successful, permitted re-route after a deliberate
prediction error.** All four conditions are necessary:

| Condition fails | Experience | Signal signature |
|---|---|---|
| No prediction error (S low) | boring, predictable, "saw it coming" | punchline tokens near-zero surprisal |
| Error but no alternate frame (R ≈ 0) | nonsense, random, "I don't get it" | surprisal stays high even given hints |
| Frame exists but is expensive (E low) | "I get it" without laughing; dissected frog | resolution only after long explanation |
| Frame collides with a meta-mesh (B high) | offense, anger, walk-out | persona-conditioned collision flags |

The comedy sweet spot is an **inverted U in S** (enough error to register, not so much that no frame can
absorb it), **high R**, **high E**, **low B** — *surprise that agrees with the wider mesh*.

### The canonical bad-surprise definition (controlling text)

> Bad surprise is poorly defined, a bad surprise is a surprise that contradicts with internal models
> within a human brain that are so strong they override logic and are some of the primary drivers of a
> person's perception, understanding, and good/bad/moral/ethical views of the world. So basically, a
> surprise is not good if it disagrees with something that is already overriding logic or a surprise is
> not good it if disagrees with a nearly overwhelming generalization engine in a human mind that has
> significant overriding power to override logic, promote other false generalizations, and is the
> primary feature used to reduce surprise in that person's mind.

Note what this is **not**: it is not "offensive," "unsafe," "false," or "edgy." A joke can be perfectly
clean and still be a bad surprise for an audience whose dominant interpretive mesh it contradicts; a
sharp political joke can be a *good* surprise for an audience whose meta-meshes leave it a permitted
re-route. Bad surprise is **audience-relative by construction**, which is why every measurement below
is persona-conditioned.

## 3. Why a language model makes this computable

A causal language model **is** a predictive mesh: its next-token distribution is exactly the
supervisor's bet about what comes next, and its negative log-probabilities are **measured surprise**,
token by token. This turns the theory's quantities from metaphors into numbers we read off Gemma's
logits — we never ask the model "was that surprising?", we **measure** it:

- **S — surprise**: mean/max token surprisal (negative log-probability, in nats) of the punchline
  given the setup: `S = NLL(P | C)`. High S = real prediction error.
- **R — resolution**: how much the punchline's surprisal collapses when the alternate frame is made
  explicit: `R = NLL(P | C) − NLL(P | C + F)`, where F is a one-line statement of the frame. A real
  joke has a frame that *explains its own punchline*; noise does not. R is the measured existence of
  the re-route.
- **E — efficiency**: resolution per token of repair: `E = R / len(F)`. The ATP constraint: a joke
  whose frame needs a paragraph is a joke that costs too much to get.
- **B — bad surprise**: persona-conditioned. Each audience is a differently-tuned mesh; we condition
  the same measurements on a persona preamble (their values, context, in-group knowledge) and ask the
  model — under the canonical definition above — whether the *frame itself* collides with a
  high-authority internal model for that audience. B combines the judged collision with the measured
  persona shift in S.

Small Gemma models are the right instrument: a 2B–4B model running sparsely on a single GPU is,
by construction, **a predictive mesh on a metabolic budget** — the same regime the theory describes.

### Multiple meshes: model-audiences and portability

No single mesh defines "funny." Different personas (and different judge models — Gemma variants,
frontier LLMs when available) are **differently-tuned audience meshes**. A joke's quality profile is
therefore a **matrix**: signals × audiences. A joke that keeps high R and low B across many meshes is
*portable*; one that only works in one mesh is *insider material* — neither is wrong, but they are
different products, and the tool should say which one you have.

## 4. Falsifiable predictions (what the notebook tests)

1. **Jokes vs. matched non-jokes**: real punchlines show higher S than boring continuations *and*
   higher R (their frame hint collapses surprisal; a boring line's "hint" changes little).
2. **Shuffled control**: pairing a setup with an unrelated punchline keeps S high but kills R —
   surprise without a re-route, which the theory says is nonsense, not comedy.
3. **Explanation asymmetry**: for real jokes, a one-line frame hint produces most of the surprisal
   collapse (high E); non-sequiturs need long explanations for small collapse (low E).
4. **Persona dependence**: the same joke shows different B (and different S) under different persona
   preambles — bad surprise is audience-relative, as the canonical definition requires.

## 5. Design consequences for the product

- **Generation is search under the theory**: sample many candidate punchlines (divergent, sparse
  exploration), then keep the ones whose measured (S, R, E, B) land in the laugh region. The scorer is
  the theory; Gemma is both the imagination and the instrument.
- **Criticism is diagnosis, not a number**: a critique names *which condition failed* (predictable /
  no frame / too expensive / meta-mesh collision) and repairs the specific failure while preserving
  the comic turn.
- **Formats are timing envelopes**: a one-liner, a meme caption, and a 45-second bit are different
  budgets for where surprisal is allowed to accumulate and where it must spike. Format presets tune
  length, beat placement, and signal weightings — the same theory, different envelopes.
- **Audience tuning is mesh tuning**: personas, live reactions, and preference notes adjust which
  meshes score the joke — never a global "safety filter," always a specific audience model.

## 6. Compiled comedy: amortizing the mesh

The "Compiled AI" paradigm (Trooskens et al., *Compiled AI: Deterministic Code Generation for
LLM-Based Workflow Automation*) moves the model to **compile time**: the LLM generates validated,
executable artifacts once; the workflow then runs deterministically with zero model invocations.
Applied to humor, this is not just an efficiency trick — it is what comedians already do:

- **A bit is a compiled artifact.** Material is explored, measured against live audiences, edited,
  and *frozen* before the tour. Nobody improvises their closer.
- **A template is a paid-for frame.** Once an audience's mesh has cached a frame (a character, a
  running gag, a game), each re-use is a cheap re-route — high E by construction. Compilation makes
  that explicit: Gemma explores frames and word banks offline; the runtime fills slots with a seeded
  RNG and pure string operations.
- **Live performance demands determinism.** On stage (the NYC showcase's Track 3 setting), you
  cannot let a model improvise a bad surprise. The compile pipeline measures S/R/E and runs persona
  collision checks on probe instantiations *before* freezing; the frozen artifact is auditable —
  you know every joke it can emit before it is ever performed.
- **Media rendering compiles the timing envelope.** A shorts script compiles to a deterministic
  timeline (beat windows, caption overlays, the SNAP timestamp with landing room); any dumb renderer
  (ffmpeg, moviepy, a template editor, a human) can execute it. The model decides *nothing* at
  render time.

`compiled_humor.py` implements the four-stage pipeline (generate → static lint → measured
validation → freeze) for `JokeProgram` text artifacts and `ClipPlan` video timelines, with the
banned-target lint enforcing the meta-mesh rule structurally: identity meshes are never valid slot
fillers.

## 7. Multi-mesh measurement: many models, one theory

If audiences are differently-tuned meshes, then a *panel of unrelated model families* (Gemma,
Mistral, NVIDIA Nemotron, DeepSeek, GLM — reachable through one Ollama Cloud endpoint) is a cheap
population of artificial audiences. `research_panel_study.py` runs the panel persona-conditioned
over real jokes plus a shuffled-nonsense control, with four pre-registered questions:

- **Q1 validity** — every mesh must rate nonsense below every real joke (surprise without a
  re-route is not comedy, in any mesh).
- **Q2 convergence** — structural dimensions should converge across meshes; `bad_surprise_risk`
  should diverge the most, because it is audience-relative *by construction*. Divergence there is
  signal, not noise.
- **Q3 portability** — persona spread should flag insider and political material; low spread =
  travels across meshes.
- **Q4 instrument vs. rater** — the panel's stated "surprise" is a *self-report*; the notebook's
  teacher-forced surprisal is a *measurement*. Where they disagree (the nonsense control has the
  highest measured S and should get the lowest quality rating), the measurement wins — raters who
  track raw S are conflating surprise with quality.

The follow-up experiment ("hosted frame-writers × local instrument") inverts the roles: each
hosted mesh writes its best one-line frame for each joke; the small local Gemma measures the
surprisal collapse each frame produces (net of the decoy null). Explanation quality becomes a
measured leaderboard — which mesh understands *why* the joke works, scored in nats, not vibes.

## 8. What a "vibe" is, and how to measure one

People use "vibe" for the thing they can feel instantly but cannot articulate: the ambient state
of a room, a chat, a page. In mesh terms it stops being mysterious:

> **A vibe is the current tuning state of a predictive mesh — the shape of its expectation
> distribution *before* any specific content arrives.** Not what the supervisor predicts next,
> but the prior it predicts *from*: which sub-networks are pre-activated and at what gains.

That definition decomposes into three measurable components:

1. **Register — *where* the probability mass sits.** Project the context's representation onto
   interpretable contrast axes (formal↔casual, warm↔hostile, sincere↔ironic, high↔low energy,
   safe↔edgy, insider↔public), each axis built from small anchor-text sets. The coordinates are
   the vibe's *address*; two rooms with different surface content but nearby coordinates have the
   same vibe, which is exactly how people use the word.
2. **Openness — *how concentrated* the mass is.** The entropy of acceptable continuations. A
   tight vibe (a board meeting) licenses few continuations; a loose vibe (an improv warm-up)
   licenses many. Openness is the room's *risk budget*: the same joke is a delight at high
   entropy and a violation at low entropy. Timing is largely openness-surfing.
3. **Drift — *how fast* the tuning is moving.** Vibe shift `ΔV` between the room before and after
   a line: its projection on the axes says what the line did to the room ("killed the vibe" = a
   large negative move on warmth/energy), and its magnitude says how much steering happened.
   Crowd work is deliberate `ΔV` before landing material that needs the new tuning.

**Vibe failure ≠ bad surprise.** An *off-vibe* joke is in the wrong register — its own coordinates
sit far from the room's — and is fixable by rewording (same frame, new address). A *bad surprise*
collides with an override-authority meta-mesh and no rewording saves it. The tooling keeps these
diagnoses separate because their repairs differ: vibe-repair rewrites the *surface*; bad-surprise
repair replaces the *frame*.

Falsifiable predictions: (i) vibe-matched rewordings of the same frame improve panel
`audience_fit` while leaving measured R roughly unchanged (register moved, mechanism intact);
(ii) openness measured before the punchline correlates with how much S the room tolerates (the
band widens at high entropy); (iii) "read the room" failures cluster at large joke-vs-room
distance on register axes even when B is low.

## 9. De-escalation: comedy as a conflict off-ramp

A hostile comment tightens the mesh — cold register, near-zero openness, one licensed
continuation: fight. Escalation is *accepting the attacker's frame* and fighting inside it. The
humor off-ramp is the theory's whole apparatus pointed at peace:

> **A de-escalating reply is a re-route out of the conflict frame that the attacker's own
> meta-meshes can accept.** S in the laugh band; the frame targets the *situation* or the
> *speaker themselves*, never the attacker's identity; B ≈ 0 under the **attacker's** persona
> (not just the audience's); and the measured vibe shift runs toward warmth and higher openness.

This yields a distinction no "rate my comeback" toy can make: a zinger and an off-ramp can be
equally funny — same S, same R — but the zinger fails the attacker-persona benign gate (it is a
bad surprise *for them*, i.e. escalation with better production values), while the off-ramp
passes it and measurably warms the register. `deescalate.py` implements five strategies (absorb
self-deprecating, absurd literalization, shared-enemy redirect, agree-and-amplify, warm
deflection + boundary), an escalation lint, and one non-negotiable rule: if the attack contains
a legitimate grievance, **fix the ticket, then the vibe** — substance first, joke second.

Prediction: replies selected by the off-ramp score (laugh × attacker-benign × audience-benign ×
warmth gain) produce fewer follow-up hostile turns than replies selected by laugh score alone —
testable on any public thread corpus.

## 10. Remixing memory: callbacks and the shared canon

The cheapest re-routes run through paths the audience has **already paid to build**. Two supplies
of pre-cached frames:

1. **A person's own earlier statements.** Everyone present encoded them; a callback punchline that
   re-frames an earlier line buys maximal R at near-zero E — which is why callbacks and in-jokes
   out-hit objectively "better" jokes. This is measurable and *provable per joke*:
   `R_callback = NLL(punchline | now) − NLL(punchline | now + the earlier statement)`. If quoting
   the source collapses the punchline's surprisal, the joke demonstrably runs on the shared
   history. Mining is measurable too: the lines a room actually caches are the *distinctive* ones
   (high surprisal under a bland prior), so memorability is ranked before remixing.
2. **Historically known knowledge.** The canon (public-domain quotes, events, myths) is the
   population-level cache: the setup happened years ago in everyone's head, so a canonical remix
   is the highest-efficiency format that exists — and precisely as portable as the canon itself
   (`R_canon` high for those who share it, noise for those who don't; the public↔insider vibe
   axis, measured).

**The dignity gate.** Remixing someone's words *at them* is affection or humiliation depending on
one thing: whether the reframe collides with their identity meshes. So the quoted person gets the
same benign gate as any audience (B under *their* persona), plus a hard block: vulnerable
disclosures (grief, illness, shame, confession) are never material. The roast doctrine is the
test: **the quoted person should want to repeat the line.**

Prediction: for true callbacks, quoting the source collapses punchline surprisal more than the
joke's own best frame-hint does for matched fresh jokes — the cache outperforms any explanation
that must be paid for at delivery time.

## 12. Two diagnostic joke classes: partisan asymmetry and causal-inference humor

Two joke families are natural experiments that make "bad surprise is audience-relative" (§1) and
"resolution depends on the audience's mesh" (§2) *falsifiable by construction*.

### 12a. The reversal test: partisan weapon vs. bridge

Take a joke that targets a political belief, then build its **mirror** — the same structure with
the target swapped (left↔right, and any partisan signifiers flipped). Measure laugh and B under a
left-mesh persona and a right-mesh persona, for *both* the original and the mirror. Two outcomes:

- **Partisan weapon**: funny to the in-group, a bad surprise to the out-group, and the mirror
  *flips* which side laughs. The joke rents ONE mesh's permission — its reframe confirms the
  in-group's model of the out-group as absurd (a permitted, even rewarded re-route) while colliding
  with the out-group's identity mesh (offense, not laughter). High, *sign-flipping* asymmetry.
- **Bridge**: funny to both, because the target is a **shared-process absurdity** (the printer, the
  committee, the form) rather than either group's identity. The mirror barely changes the scores.
  Low asymmetry, mirror-stable. ("Congress found a bipartisan solution: both sides agreed the
  printer was the real problem" targets no one's mesh.)

The measurable is the **asymmetry magnitude** `|laugh_left − laugh_right|` and whether it **flips
sign** under mirroring. A bridge joke is low-asymmetry AND mirror-stable; a partisan joke is
high-asymmetry AND sign-flipping. Repair is directional: retarget the identity-mesh collision to
the shared process, preserving the comic turn — this is the de-escalation doctrine (§9) applied to
tribe instead of individual.

### 12b. Correlation/causation jokes: the frame is a reasoning error

A whole class of jokes has a **causal-inference fallacy as the hidden frame**: a spurious
correlation dressed as causation ("I've worn my lucky socks to every exam I passed"), a confounder
played straight (ice cream sales and drownings both peak in summer), or reversed causation ("every
time I carry an umbrella it doesn't rain — I've solved droughts"). Here the re-route (R) *is* the
audience recognizing the fallacy, so resolution depends on the audience's **causal-reasoning
mesh** — and this splits jokes into two opposite sub-types:

- **Spot-the-fallacy** (irony): funny *because* you correctly model cause≠correlation; the humor is
  watching the speaker not. Requires causal literacy — measurable as: stating the causal correction
  (the confounder / the reversed arrow) collapses the punchline's surprisal (high R). A persona who
  takes correlations at face value gets less.
- **Believe-the-fallacy** (naive): the joke only lands if you *don't* question the causation — the
  moment you name the confounder it dies. Measurable as the mirror image: the causal correction
  does NOT increase R, and a causally-careful persona finds it flat.

So the tool can classify a causal joke by whether the causal-structure hint raises or leaves R, and
persona-condition on causal sophistication — a second axis of audience-relativity orthogonal to
politics.

`symmetry_probe.py` implements both: `partisan_asymmetry` (mirror generation + two-persona laugh/B
measurement + partisan-vs-bridge verdict + retarget repair) and `causal_structure_probe`
(fallacy-structure detection + causal-correction R test + causal-literacy persona split).

Predictions: (i) partisan jokes show high, sign-flipping left−right asymmetry that their mirrors
invert, while bridge jokes stay flat under mirroring; (ii) spot-the-fallacy jokes gain R from the
causal-correction hint and lose laugh under a correlation-credulous persona, while
believe-the-fallacy jokes do the opposite — cause≠correlation understanding is a measurable
audience axis.

## 11. Temporal mechanics: cache depth, topicality half-life, and the too-soon curve

"Should you joke about old things or current events?" is a question about **which cache the joke
rents**:

- **Old / canonical material** rents deep, consolidated, population-wide paths (myth, classics,
  proverbial history). Coverage is near-universal within a culture and stable for decades, but
  the path is *dormant* — the setup must spend a beat re-activating it. Low variance, durable,
  portable: evergreen material. A touring hour must rent caches whose half-life exceeds the tour.
- **Current events** rent shallow, *hot* paths: the audience's supervisors are already predicting
  about this week's story (doomscrolling is surprise-minimization in progress), so activation is
  free — two words spike S. But the cache evicts in weeks (**topicality half-life**), and a live
  event can still be a threat, so B is elevated: "too soon" is the vulnerable-disclosure rule at
  population scale. High variance: the biggest laughs (relief = benign resolution of live
  tension) and the biggest bombs.
- **The sweet-spot curve falls out of the primitives**: funny(t) rides S-activation (decays slowly
  for big events) times benignness (B decays as threat resolves). B decays faster than the cache
  ⇒ inverted-U in temporal distance — jokes about a tragedy peak at intermediate remove (Titanic
  is material; this week's disaster is not), which matches the empirical comedic-sweet-spot
  literature without new assumptions.

**Measured quantities** (`temporal.py`): the **self-containedness gap** = R(fact stated) −
R(fact unstated). A frozen LM is a snapshot of the population cache — it knows Icarus but not
last week's headline — so a canonical joke resolves *without* stating its fact (small gap), while
a topical joke is unresolvable without its headline (large gap): the gap measures how much shared
cache the joke rents, i.e. its temporal portability. The **evergreen score** combines R-without
(deep-cache resolution) with a small gap. The **too-soon probe** re-judges the same frame at
different stated temporal distances and reads the collision decay.

Predictions: (i) Gutenberg-1916 jokes split cleanly — universal-mechanics frames (puns, money,
marriage) keep R today while dead-cache frames (streetcars, period norms) lose it (**the century
test**); (ii) headline jokes show large self-containedness gaps that shrink as events age into
canon; (iii) persona "someone who missed this week's news" tanks topical jokes but not canonical
ones; (iv) judged collision for tragedy-adjacent frames falls monotonically with stated distance.
