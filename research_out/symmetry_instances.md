# Exploring instances: partisan asymmetry & causal-inference humor

Curated instance sets for the two THEORY.md §12 probes, each annotated with the mechanism and the
**predicted measurement signature** (what `symmetry_probe.py` should report). This is the
"find and explore instances" artifact; `corpora/symmetry_seed.jsonl` is the machine-readable seed
the probes and the Kaggle notebook consume.

---

## A. Partisan asymmetry — the reversal test

The test: build each joke's **mirror** (same structure, target swapped), then measure laugh + bad-
surprise (B) under a left-mesh and a right-mesh persona for BOTH versions. The diagnostic is not
"is it offensive" — it's whether the **asymmetry sign-flips under mirroring**.

### A1. Partisan weapon (predicted: high, SIGN-FLIPPING asymmetry)

> "How many [PARTY-A] politicians does it take to change a lightbulb? None — they just declare
> the darkness a feature and fundraise off it."

- Mechanism: the reframe confirms the *out-group's* model of PARTY-A as absurd — a **permitted,
  rewarded re-route** for the opposing mesh, a **B-collision** for PARTY-A's identity mesh.
- Mirror (swap to PARTY-B): the SAME structure now flatters the other tribe.
- Predicted signature: `laugh_left ≫ laugh_right` on the original, `laugh_right ≫ laugh_left` on
  the mirror → **sign_flips = True**, high `asymmetry` AND high `mirror_asymmetry`, `b` elevated on
  the targeted side. Verdict: **partisan weapon.**

> "My [PARTY-A] uncle explained the economy to me using a chart he drew on a napkin. The napkin
> had a better grasp of it."

- Same family: targets a tribe's competence. Mirror-flips. Weapon.

### A2. Bridge (predicted: LOW asymmetry, MIRROR-STABLE)

> "Congress found a bipartisan solution: both sides agreed the printer was the real problem."

- Mechanism: target is the **shared-process absurdity** (institutional dysfunction), not either
  identity mesh. Nobody's supervisor has to defend their tribe.
- Mirror: there is nothing to swap — the joke doesn't name a side. `mirror ≈ joke`.
- Predicted signature: `laugh_left ≈ laugh_right`, low `asymmetry` AND low `mirror_asymmetry`,
  `b ≈ 0` both sides. Verdict: **bridge.**

> "A politician promised to fix the potholes. The potholes formed a committee to study the
> politician."

> "Both parties agree the other side is why we can't have nice things — which is the one thing
> they've ever agreed on, so technically it's progress."

- The last one is a **meta-bridge**: it targets the *symmetry of the fight itself*, so it reads
  even-handed. Low asymmetry by construction.

### A3. Leans-partisan (asymmetry without a clean flip)

> "Thoughts and prayers have a great track record — every problem they've been applied to still
> exists, undefeated."

- Targets a *rhetorical move* associated with one side more than the other. Predicted: moderate
  asymmetry, weak/absent sign-flip (the mirror doesn't have an equally-loaded counterpart).
  Verdict: **leans partisan** — the honest middle bucket the probe should surface, not force.

**What the exploration teaches:** "is this joke partisan?" is not a vibe call — it's whether the
laugh **moves to the other side when you mirror the target**. Bridge jokes are the portable
product (they rent no single mesh's permission); the repair path for a weapon is to retarget its
punch to the shared process (§9 de-escalation applied to a tribe).

---

## B. Correlation/causation humor — spot vs. believe

The frame IS a causal-inference error; the re-route is the audience catching it. Diagnostic:
does stating the **causal correction** (the confounder / reversed arrow) *raise* R (spot) or leave
it flat (believe), and does a causally-literate persona laugh more (spot) or less (believe)?

### B1. Spot-the-fallacy (predicted: correction RAISES R; careful persona laughs MORE)

> "Ice cream sales and shark attacks both peak in July, so clearly ice cream is chumming the water."

- Structure: classic **confounder** (summer drives both). The joke = watching the speaker mistake
  correlation for causation; WE are above it.
- Predicted: naming the confounder ("both are caused by summer, not each other") *collapses* the
  punchline's surprisal → `correction_lift > 0`; `laugh_careful > laugh_credulous`. **Spot.**

> "Nicolas Cage's film releases correlate with pool drownings, so for public safety we're placing
> him under a swim-season release embargo."

- A real spurious-correlation meme. Same signature; funnier the more you *know* the correlation is
  meaningless. **Spot.**

> "Every CEO I've studied drinks water. If we ban water, we end capitalism by Tuesday."

- Reversed/absurd necessary-condition reasoning. **Spot.**

### B2. Believe-the-fallacy (predicted: correction does NOT raise R; careful persona laughs LESS)

> "I wore my lucky socks and we won, so I'm never washing them — the team is depending on me now."

- The payoff lives *inside* the superstitious premise. Naming "socks don't cause wins" doesn't
  sharpen it — it deflates it. The joke asks you to inhabit the magic-thinking, not audit it.
- Predicted: `correction_lift ≈ 0`; a causally-credulous persona finds it *warmer* (they share the
  premise), a hyper-literal persona finds it flat. **Believe.**

> "Mercury's in retrograde, which explains why my toast burned, my ex texted, and the printer jammed
> — all clearly one cosmic event."

- Astrology-logic told straight. Lands warmer for those who don't demand the confounder; explaining
  the base-rate kills it. **Believe.**

**What the exploration teaches:** causal-reasoning is a *measurable audience axis* orthogonal to
politics. The same "correlation joke" can be funny for opposite reasons — because you catch the
error, or because you don't question it — and the correction-lift + literacy-persona split tells
which. A comedy tool that knows the difference can aim a joke at the room it will actually land in.

---

## Cross-cutting note

Both classes are, at bottom, the §1 claim made testable: **the same surprise is good for one mesh
and bad for another.** Politics swaps the *identity* mesh; causal literacy swaps the *reasoning*
mesh. Measuring the swap — mirror sign-flip for one, correction-lift for the other — is what turns
"know your audience" from a platitude into an instrument reading.
