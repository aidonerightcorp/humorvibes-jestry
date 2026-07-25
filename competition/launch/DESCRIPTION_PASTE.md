# Humor Vibes Open — description paste pack

Each block below maps to a Kaggle description field. Paste as-is (Kaggle
description fields render Markdown). Derived from the public-safe sections of
`../HUMOR-VIBES-OPEN-COMPETITION-DESIGN.md` (Tracks + Anti-gaming rules);
discloses methods, never the solution mapping.

---

## PASTE INTO: Overview → Description

### Can your model tell a joke from a non-joke?

Every item in this competition is an explicit **setup → punchline** pair. Some
are genuine human jokes, harvested with provenance from public joke APIs. The
rest are constructed controls:

- **shuffled** — a real punchline attached to the wrong setup: *surprise
  without a re-route is nonsense, not comedy*;
- **boring** — a deliberately flat continuation of a real setup: *no surprise
  at all*.

Your job: submit a `humor_score` per test item — higher means "genuine joke",
lower means "constructed control". The metric is rank-based **AUC**, so only
the *ordering* of your scores matters.

**Why this shape?** The hosts' theory says a joke is a controlled prediction
error with a cheap, permitted repair: the punchline must be surprising under
the setup's dominant reading (S), yet snap into place under a hidden frame (R)
at low cost (E). Both control types delete exactly one of those conditions —
so separating jokes from controls is testable ground truth with **zero
annotation budget**. Labels here are structural facts (joke vs constructed
non-joke), not funniness opinions.

**The honest bar.** A Gemma-based scorer that reads surprise and resolution
off teacher-forced logits (with a null control and a leak guard) reached
Spearman ρ = 0.115 against human humor grades on a prior benchmark — weak,
honestly reported, and exactly the kind of baseline you should beat. A
pure-stdlib surface heuristic (see the starter notebook) reaches AUC ≈ 0.60
here and is near chance on the shuffled controls — that gap is the
competition.

**Scope, stated up front.** This leaderboard measures joke-vs-control
separation on explicit setup/punchline items. It does not certify a general
funniness oracle; the hosts' own ablation evidence shows fixed humor scalars
fail on other formats (e.g. headline edits). Bounded claims only.

### Tracks beyond the leaderboard

This hosted leaderboard is **Track A (humor understanding)**. Two community
side-events run in the forums under the protocol in the design doc, judged,
not auto-scored:

- **Track B — constrained generation**: jokes for (topic, audience) briefs,
  scored by a frozen measurement protocol on a certified instrument
  (Kaggle-hosted Gemma with full logprobs; model self-ratings inadmissible;
  per-item generation receipts required).
- **Track C — been-done detection**: classify text pairs as
  `surface_retell` / `same_frame_new_words` / `different_bit`.

---

## PASTE INTO: Overview → Evaluation

Submissions are scored by **ROC AUC**: the probability that a randomly chosen
genuine joke receives a higher `humor_score` than a randomly chosen control
(ties handled by rank-averaging).

- Submit a CSV with header `id,humor_score` — one row per test id, every id
  exactly once, scores finite numbers. Any monotone transform of your scores
  gives the same AUC.
- `sample_submission.csv` (all 0.5) is valid and scores exactly 0.5.
- The **canonical scorer ships in the data bundle**: `metric_humor_vibes.py`,
  dependency-free (`score(solution, submission, "id")`). The platform
  leaderboard uses Kaggle's built-in AUC, which equals the canonical metric's
  primary score; the canonical scorer additionally reports a **matched-pair
  diagnostic** (does the genuine punchline outscore the shuffled one *for the
  same setup*?) which the hosts compute offline and will publish in the
  wrap-up. You can self-score on the labeled train split without burning
  submissions.
- The test set has a **public/private split**. The public leaderboard is
  guidance while the competition runs; final standings come from the private
  split. Public-leaderboard tuning is public-leaderboard-guided development,
  not a population estimate — the split is the guard.

---

## PASTE INTO: Data → Description

| file | columns | what it is |
|---|---|---|
| `train.csv` | `id, setup, punchline, is_genuine, control_type, source, license` | labeled training split (155 rows): genuine jokes and both control types, with provenance |
| `test.csv` | `id, setup, punchline` | 319 items to score |
| `sample_submission.csv` | `id, humor_score` | valid all-0.5 submission |
| `metric_humor_vibes.py` | — | canonical offline scorer (stdlib only) |
| `manifest.json` | — | build receipt: seed, counts, anti-gaming self-check readouts |

**Provenance & licensing.** Genuine jokes come from public joke APIs that ship
native setup/punchline fields (official-joke-api, JokeAPI in safe mode) plus
three canonical reference jokes; every train row keeps `source` and `license`.
Controls are constructed (`license: derived`).

**Construction facts you may rely on** (and their anti-gaming intent):

- The train/test split is at the **setup level** — no setup appears on both
  sides.
- **Shuffled controls draw punchlines from a donor pool that is
  punchline-text-disjoint from the genuine items in the data.** No punchline
  string appears both as genuine and as a control anywhere — verbatim string
  matching and constraint propagation solve nothing. (An earlier internal
  build without this property was solvable at AUC 0.986 with zero humor
  modeling; the hosts attacked their own data and rebuilt it.)
- **Boring controls are template-varied with setup-derived words** — there is
  no fixed list of tail strings to regex. (Also an adversarial finding:
  constant tails were separable at AUC 0.63 with zero humor modeling.)
- Every build re-runs these self-attacks; the readouts are published in
  `manifest.json`.

A few text fields contain quoted embedded newlines — standard CSV; use a CSV
parser, not line splitting.

---

## PASTE INTO: Rules (or a pinned "Rules & honesty notes" section)

1. **Submissions**: up to 5 per day; select up to 2 for final scoring. Every
   test id exactly once, finite numeric `humor_score`.
2. **Teams**: max 3; mergers allowed until one week before the deadline; one
   Kaggle account per participant; no private sharing of code or predictions
   outside your team (public forum/notebook sharing is encouraged).
3. **External data and models**: allowed if publicly available,
   license-compatible, and disclosed in the forums. Gemma is encouraged — the
   intended baseline reads humor signals off logits rather than asking a model
   to rate funniness.
4. **No hand-labeling of the test set.** Scores must come from a method, not
   from humans annotating test items.
5. **Null controls are load-bearing.** A fraction of test items are
   constructed controls; a scorer that credits confabulated "resolution"
   (raw plausibility without a null/decoy comparison) loses AUC exactly there.
6. **Known ceiling, stated honestly**: a detector that only spots the boring
   tails' style is mathematically capped around AUC ≈ 0.63 on this build and
   is chance on the shuffled half. The leaderboard is won on setup↔punchline
   coherence.
7. **Winner verification**: hosts re-score finalists offline with the
   canonical `metric_humor_vibes.py` (including the matched-pair diagnostic)
   and may request a brief method description consistent with the scores.
   Track B side-event entries must carry per-item generation receipts (model,
   prompt digest); hidden-fallback generation (a human writing "model" jokes)
   is a rules violation.
8. **Spirit of the rules**: this is a measurement competition. Exploits
   against the data construction are in-bounds to *report* (post them!) and
   the hosts will credit them, but standings come from the private split and
   winner verification.

---

## PASTE INTO: FAQ (pinned forum post or Overview → FAQ)

**Q: Isn't humor subjective? How can there be ground truth?**
A: Track A labels are structural, not aesthetic: an item is either a
provenance-carrying human joke or a constructed non-joke (wrong punchline, or
deliberately flat tail). Whether a joke is *good* is not what the leaderboard
measures — see "Scope, stated up front".

**Q: Can I use an LLM? Which ones?**
A: Any public model. Gemma is encouraged (and is the intended baseline
instrument). Asking a model "is this funny, 1–10?" tends to underperform
reading surprisal directly off logits — the hosts' measurements say so.

**Q: I found that the boring tails look template-y. Is that a bug?**
A: It's a disclosed, deliberately capped surface (see Data notes and Rules #6).
Detecting them perfectly gets you to ≈ 0.63; the other 136 negatives are real
punchlines on wrong setups, and style features are chance there
(the starter notebook demonstrates both numbers).

**Q: My local metric score differs from the leaderboard.**
A: Make sure you scored against the labeled *train* split with
`metric_humor_vibes.py` (test labels are host-only), used every id exactly
once, and finite scores. The platform AUC and the canonical metric's primary
score are the same quantity (rank AUC with tie-averaging, rounded to 6
decimals offline).

**Q: What's the prize?**
A: Kudos: winner interview + pinned write-up in the wrap-up post. This is a
measurement community, not a cash comp.

**Q: Where do Track B / Track C run?**
A: Forum side-events with judged protocols (see Overview → Tracks). The
leaderboard here scores Track A only.

**Q: How was the data built? Can I audit it?**
A: A deterministic seeded builder over provenance-carrying harvests; every
build re-runs anti-gaming self-attacks and publishes the readouts in
`manifest.json`. The construction *methods* are fully disclosed above; the
per-item solution mapping is host-only until the competition closes.
