# Styles of joke: the three axes

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

- **24 public-domain categories** from curated volumes: military, medical, legal, Jewish,
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

Adding them, then re-labelling all 2,664,398 items, produced a result that corrects the original
diagnosis. Non-English specific coverage is *still* near zero: zh 1.4%, ru 0.8%, es 0.6%, and
de / pl / tr / it / pt / fi / nl / sv all **0.0%**.

The native templates work — they fire on 257 xiehouyu, 32 Vovochka, 22 anekdot openers, 22
Spanish `¿Qué le dice`, 20 Shtirlitz. There is simply almost nothing for them to fire on, because
**the non-English corpus is overwhelmingly proverbs and idioms, not jokes.** Of 18,394 Chinese
items, 18,384 are Wiktionary idiom entries; the German, Polish, Turkish, Italian, Portuguese,
Finnish, Dutch and Swedish holdings are near-entirely proverb lists.

A proverb has no punchline, so no joke template can match it, and none should. The honest
statement is therefore not "the taxonomy is English-biased" but "**the multilingual half of this
corpus is a phrase collection, and the English half is a joke collection**". Those are different
objects and should not be compared as though the same labels apply.

The fix is a sourcing fix, not a regex fix: ingest non-English *jokes* — Bulgarian (93,968),
Russian (150,553), Greek (9,999), Spanish sarcasm (19,096), Romanian satire (13,873) — all
verified live and queued.

## Two numbers reported instead of one

`coverage()` reports both an any-form share and a specific-form share, per language. The any-form
number counts generic buckets — `one_liner`, `setup_punchline`, `q_and_a`, `dialogue` — which any
short text falls into. A Swedish proverb is a single short assertion, so it lands in `one_liner`
and reads as "labelled" while telling us nothing about mechanism.

**The specific-form share is the honest column.** Over the full 2,664,398-item corpus it is
**2.2%** — and it went *down* as the corpus grew, because the bulk additions (ranked captions,
reddit dumps, proverb lists) are largely formless with respect to these templates. A coverage
number that improves only when you stop adding data is a number worth distrusting.

The forms that do fire, at corpus scale: what_do_you_call 15,015 · shaggy_dog 10,985 ·
walks_into_bar 6,807 · chuck_norris 6,249 · whats_the_difference 5,765 · light_bulb 2,427 ·
blonde 1,858 · knock_knock 1,846 · paraprosdokian 1,618 · yo_mama 1,534 · rule-of-three rosters
1,424 · how_many 649 · wellerism 556 · xiehouyu 257 · roses_are_red 210 · doctor_doctor 187 ·
soviet_russia 95 · confucius_say 81 · elephant 59 · Tom Swifty 20 · limerick 9.

## Domain is a guess, and says so

Domains come from keyword lexicons and are returned with the match count that produced them. A
joke mentioning a doctor is not necessarily a medical joke. Military is additionally split by
branch — `mil_army`, `mil_navy`, `mil_air`, `mil_marines` — because "military humor" is not one
register: a boot-camp joke and a submarine joke share almost no vocabulary.

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

A separate smaller run comparing *declared style* arms (military, medical, legal, dad-joke,
jest-book, riddles) put all ten joke arms above the control **on the mean** — but that comparison
used point estimates with no uncertainty, and ranking means at n=6 manufactures a separation the
data does not contain. The interval-based verdict is the one to believe.

So: the ordering is a hypothesis worth more measurement, not a finding. S is model surprisal,
**not funniness** — these items carry no human grade, so nothing here says any form is funnier.

## Do different subjects recruit different forms?

Cross-tabulating form against domain over all 2,664,398 labelled rows says yes — but only after
removing a confound that would otherwise have produced a wrong answer.

**The confound.** `shaggy_dog` is assigned by length alone (over 900 characters), not by a
template. On a first pass it dominated military, religion and medical. Checking where those items
came from showed they were overwhelmingly taivop Reddit dumps — long reddit posts. The label was
tracking **source verbosity, not genre**. Any conclusion drawn from that pass would have been
about where the text came from.

With the length proxy excluded, real domain–form pairings appear:

| domain | n | top template forms |
| --- | --- | --- |
| medical | 783 | **doctor_doctor 183**, what_do_you_call 150, blonde_joke 89 |
| science | 448 | **walks_into_bar 194**, walk_into_group 74, what_do_you_call 53 |
| religion | 1,211 | **walks_into_bar 281**, what_do_you_call 275, **walk_into_group 217** |
| nautical | 534 | what_do_you_call 215, walks_into_bar 196 |
| music | 361 | what_do_you_call 136, **whats_the_difference 72** |
| military | 186 | what_do_you_call 66, chuck_norris 31, whats_the_difference 26 |
| tech | 402 | what_do_you_call 113, chuck_norris 76, **light_bulb 56** |
| legal | 336 | what_do_you_call 82, whats_the_difference 59 |

The pairings are interpretable rather than arbitrary. Medicine is the one domain that has its
**own** form (`doctor_doctor`). Science and religion both recruit the entry frame — "a neutron
walks into a bar", "a priest, a rabbi and a minister walk into…" — and religion is the top user of
the rule-of-three roster, which is exactly the shape of that genre's stock joke. Music skews to
comparison forms, which is what viola jokes are. Technology is the heaviest user of the light-bulb
frame.

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
