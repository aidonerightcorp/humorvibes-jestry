# Styles of joke: the three axes

*Historical snapshot: the mid-sweep 2,664,398-row labeling pass of 2026-07-26, kept because a
published kernel bundle shipped it. The final pass and current numbers are in ../STYLES.md
(3,164,600 rows); where the two disagree, that file wins.*

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

Read the ordering, not the individual means: n is small per arm, and S is model surprisal, **not
funniness**. These items carry no human grade, so nothing here says a form is funnier.

## Screening, and what it does not catch

A slur regex runs before any record is indexed, and its length floor is script-aware (three
characters for Han/kana/hangul, eight for alphabetic — a chengyu is four characters, and an
English-shaped floor was silently deleting most Chinese content).

It is not sufficient. Two minstrel joke books were excluded **by id rather than by keyword**,
because their slurs are written in dialect spelling that the regex does not match. And a random
sample surfaced ethnic-stereotype jokes containing no slurs at all. A stereotype-level screen is
a different and unsolved problem from a slur-level one; only the latter exists here.
