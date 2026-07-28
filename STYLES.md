# Styles of joke: the three axes

*Role: the three style axes (form / domain / declared) and the form-study verdict — separation is
NOT established. Numbers here trace to `jestry_out/` receipts; tenet placement in
`docs/THESIS_AND_EVIDENCE.md`.*

The corpus began with no style axis at all. It could not answer the question anyone actually asks
about humor — does a military joke work differently from a dad joke? — because nothing in it said
which was which.

Three axes now exist, and they are deliberately independent, because they answer different
questions and have very different reliability.

| axis | what it captures | how it is assigned | trust |
| --- | --- | --- | --- |
| `form` | the structural template: what shape the expectation-and-turn takes | 41 regex templates, most-specific-first | high — templates are near-unambiguous |
| `domain` | what the joke is *about* | 25 keyword lexicons | low — a guess, reported with a match count |
| `style_category` / `style` | the genre the source itself declares | curated single-subject volumes and category APIs | highest — not inferred at all |

## Why the third axis matters most

A classifier guesses. A source declares. Project Gutenberg publishes single-subject humor
volumes — a book of army jokes is a book of army jokes — and several APIs ship a category on
every item. Where that label exists, no inference is involved and no error rate applies.

Sources with a declared style:

- **26 public-domain categories** from curated volumes: military, medical, legal, Jewish,
  Russian, German, Irish, Scottish, French, Spanish, Dutch, Italian, Finnish, Nasreddin,
  clerihew, spoonerism, parody, riddles, limerick/nonsense, epigram, epitaph, jest-book,
  wit-anthology, burlesque, wellerism, toasts.
- **18 subreddits** via arctic-shift, where the community name is the label: r/dadjokes,
  r/MilitaryHumor, r/ProgrammerHumor, r/cleanjokes, r/AntiJokes, r/punny, r/oneliners,
  r/MedicalHumor, r/lawyerjokes, r/mathjokes, r/AviationHumor and others.
- **16 Chuck Norris categories**, **6 JokeAPI categories × 6 languages**, **4
  official-joke-api types** (including knock-knock and dad), and an icanhazdadjoke topic sweep.

## Form templates

Beyond the obvious English templates (knock-knock, what-do-you-call, what's-the-difference,
walks-into-a-bar, light-bulb, how-many, doctor-doctor, waiter, yo-mama, Tom Swifty, wellerism,
limerick), the table now covers:

**Joke cycles and ritual openers** — Chuck Norris, blonde, elephant, Confucius-say,
In-Soviet-Russia, roses-are-red, take-my-wife, that's-what-she-said, what's-worse-than,
how-is-X-like-Y, rule-of-three rosters, anti-joke, shaggy-dog markers, paraprosdokian.

**Non-English native forms** — German `Treffen sich zwei` and `Kommt ein Mann zum Arzt` and
Beamtenwitz; Russian `Штирлиц`, `Вовочка`, and the stock anekdot opener; French
`Monsieur et Madame`; Spanish `¿Qué le dice`; Portuguese `O que é, o que é`; Italian national
rosters; Chinese xiehouyu; Japanese dajare; Korean ajae-gag; Hebrew joke markers.

That last group exists because of a measurement, not a hunch. Before those templates, non-English
**specific-form coverage was approximately zero**: every non-English item fell into a generic
bucket while the naive coverage number read 99%+ for several languages.

### The templates were not the bottleneck — the data was

The first 2,664,398-row pass corrected the original diagnosis: adding native regexes did almost
nothing because the multilingual supply was overwhelmingly proverbs and idioms rather than jokes.
A proverb has no punchline, so no joke template can match it, and none should.

The sourcing fix has now landed, and the final **3,164,600-row** pass shows the difference. Russian
specific-form coverage is **2.9%** (4,489 rows), Bulgarian **6.2%** (3,454), Polish **2.9%**
(433), Chinese **1.0%** (257), and Spanish **0.6%** (43). The Russian joke cycles now fire at
scale: Vovochka 1,433, stock anekdot openers 625, and Shtirlitz 522. Chinese remains dominated by
phrase supply, so all 257 of its specific rows are xiehouyu; Portuguese, Greek, Amharic, Japanese,
Italian, Arabic and Turkish remain at effectively zero specific coverage.

That before/after is the useful result. Regex breadth was not enough; adding actual Russian,
Bulgarian, Polish and multilingual joke sources moved the coverage. The corpus still contains
different objects—jokes, proverbs, idioms, puzzles—and the per-language coverage table keeps that
difference visible rather than averaging it away.

## Two numbers reported instead of one

`coverage()` reports both an any-form share and a specific-form share, per language. The any-form
number counts generic buckets — `one_liner`, `setup_punchline`, `q_and_a`, `dialogue` — which any
short text falls into. A Swedish proverb is a single short assertion, so it lands in `one_liner`
and reads as "labelled" while telling us nothing about mechanism.

**The specific-form share is the honest column.** Over the final 3,164,600-item corpus it is
**2.5% (80,246 rows)**. The forms that fire most often are: `what_do_you_call` 20,583;
`shaggy_dog` 17,110; `walks_into_bar` 8,445; `whats_the_difference` 7,276; `chuck_norris`
6,545; `light_bulb` 3,143; `knock_knock` 2,706; `blonde_joke` 2,242; `yo_mama` 1,950;
`paraprosdokian` 1,902; rule-of-three rosters 1,555; Vovochka 1,433; `how_many_x` 805;
`wellerism` 755; stock Russian anekdot openers 625; Shtirlitz 522; `doctor_doctor` 363;
and xiehouyu 257.

The other 97.5% is not relabelled as mechanism by wishful thinking: 63.8% is `one_liner`, 21.7%
unknown, 5.2% declared setup/punchline, 3.7% generic Q&A, and 3.1% dialogue.

## Domain is a guess, and says so

Domains come from keyword lexicons and are returned with the match count that produced them. A
joke mentioning a doctor is not necessarily a medical joke. Military is additionally split by
branch — `mil_army`, `mil_navy`, `mil_air`, `mil_marines` — because "military humor" is not one
register: a boot-camp joke and a submarine joke share almost no vocabulary.

The final rerun caught a lexical bug before these counts were published: the old compiled patterns
had a leading word boundary but no trailing one, so `car` matched **carpet** and `cat` matched
**category**. Every domain term now requires both boundaries; regression tests also pin intended
overlaps such as `flight deck` contributing to both air and nautical vocabulary.

## What the measurement showed

Running the certified Gemma-2 instrument over a deterministic sample per form, measuring S (mean
NLL of the punchline given the setup):

| form | mean S |
| --- | --- |
| what_do_you_call | 6.68 |
| whats_the_difference | 4.69 |
| walks_into_bar | 4.48 |
| light_bulb | 4.23 |
| knock_knock | 3.73 |

The ordering tracks how ritualised the form is. Knock-knock is the most formulaic and is the
least surprising to the model; forms whose turn is a pun on a requested *name* are the most
surprising. That is the direction the theory predicts, since a more rigid frame constrains the
ending more tightly.

### The separation is NOT established, and that matters

The full run — 8 items per arm, 88 measurements, deterministic sampling, bootstrap 95% CIs:

| form | n | mean S | 95% CI |
| --- | --- | --- | --- |
| what_do_you_call | 8 | 6.680 | [4.759, 8.855] |
| doctor_doctor | 8 | 4.703 | [3.654, 5.884] |
| whats_the_difference | 8 | 4.693 | [3.905, 5.446] |
| walks_into_bar | 8 | 4.479 | [3.172, 5.809] |
| yo_mama | 8 | 4.178 | [3.309, 5.025] |
| setup_punchline | 8 | 4.082 | [3.085, 5.127] |
| q_and_a | 8 | 3.874 | [3.119, 4.555] |
| limerick | 8 | 3.856 | [3.262, 4.486] |
| light_bulb | 8 | 3.815 | [3.051, 4.682] |
| knock_knock | 8 | 3.728 | [2.915, 4.461] |
| **control_proverb** | 8 | 3.652 | [2.298, 5.198] |

**0 of 10 joke forms have a confidence interval strictly above the proverb control's upper bound
(5.198). All ten overlap it.**

A separate smaller run comparing six *declared style* arms (military, medical, legal, dad-joke,
jest-book, riddles) put all six above the control **on the mean** — but that comparison used
point estimates with no uncertainty and left no receipt, and ranking means at n=6 manufactures a
separation the data does not contain. The interval-based verdict is the one to believe — and the
receipted follow-up agrees, with its power stated honestly: the 2026-07-27 declared-style study
(`jestry_out/declared_style_study.json`; seven subreddit-declared styles × 12 items on the
certified instrument, same proverb-control recipe) found **0/7 style CIs separated from the
control in either direction — but at n=12/group the separation criterion could not have fired
(it requires a group CI-low above 5.999; the largest observed is 4.740), so this is
'underpowered, not established' rather than a tested absence.** A separate any-difference test
among the seven styles (control excluded) gives p = 0.45, and token length is an uncontrolled
covariate (r ≈ −0.63 across groups).

So: the ordering is a hypothesis worth more measurement, not a finding. S is model surprisal,
**not funniness** — these items carry no human grade, so nothing here says any form is funnier.

## Do different subjects recruit different forms?

Cross-tabulating form against domain over all 3,164,600 labelled rows says yes — but only after
removing a confound that would otherwise have produced a wrong answer.

**The confound.** `shaggy_dog` is assigned by length alone (over 900 characters), not by a
template. On a first pass it dominated military, religion and medical. Checking where those items
came from showed they were overwhelmingly taivop Reddit dumps — long reddit posts. The label was
tracking **source verbosity, not genre**. Any conclusion drawn from that pass would have been
about where the text came from.

With the length proxy excluded, real domain–form pairings appear:

| domain | n | top template forms |
| --- | --- | --- |
| medical | 976 | **doctor_doctor 357**, what_do_you_call 178, blonde_joke 99 |
| science | 376 | **walks_into_bar 191**, walk_into_group 79, what_do_you_call 42 |
| religion | 1,483 | what_do_you_call 387, **walks_into_bar 347**, **walk_into_group 239** |
| nautical | 500 | walks_into_bar 239, what_do_you_call 174, walk_into_group 21 |
| music | 462 | what_do_you_call 168, **whats_the_difference 96**, walks_into_bar 87 |
| military | 198 | what_do_you_call 77, whats_the_difference 28, chuck_norris 24 |
| tech | 452 | what_do_you_call 157, chuck_norris 78, whats_the_difference 64 |
| legal | 322 | what_do_you_call 71, whats_the_difference 65, walks_into_bar 53 |

The pairings are interpretable rather than arbitrary. Medicine is the one domain that has its
**own** form (`doctor_doctor`). Science and religion both recruit the entry frame — "a neutron
walks into a bar", "a priest, a rabbi and a minister walk into…" — and religion is the top user of
the rule-of-three roster, which is exactly the shape of that genre's stock joke. Music skews to
comparison forms, which is what viola jokes are. Technology still contains 37 light-bulb forms,
but the corrected full-corpus table does not support calling it that frame's heaviest user.

Caveats: `domain` is a keyword guess, counts are small once the length proxy is removed, and
`chuck_norris` appearing under military is a topical artifact of that cycle's vocabulary rather
than evidence about military humor. One pairing is worth flagging rather than celebrating —
`blonde_joke` ranking in aviation and medical reflects a stereotype cluster in the source data,
not a structural fact about those domains.

## Screening, and what it does not catch

A slur regex runs before any record is indexed, and its length floor is script-aware (three
characters for Han/kana/hangul, eight for alphabetic — a chengyu is four characters, and an
English-shaped floor was silently deleting most Chinese content).

It is not sufficient. Two minstrel joke books were excluded **by id rather than by keyword**,
because their slurs are written in dialect spelling that the regex does not match. And a random
sample surfaced ethnic-stereotype jokes containing no slurs at all. A stereotype-level screen is
a different and unsolved problem from a slur-level one; only the latter exists here.
