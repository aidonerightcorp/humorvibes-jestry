"""Joke FORM and DOMAIN labels over the whole corpus.

The corpus grew to millions of items with no style axis at all, so questions like
"does a military joke resolve differently from a dad joke?" or "do knock-knock
jokes sit in a different S/R region than one-liners?" could not even be asked.
This module assigns two independent labels to any item:

    FORM    the structural template — what shape the expectation-and-turn takes
            (knock_knock, walks_into_bar, how_many_x, q_and_a, one_liner,
            tom_swifty, wellerism, doctor_doctor, shaggy_dog, xiehouyu, ...)
    DOMAIN  what the joke is ABOUT (military, medical, legal, tech, animal,
            food, family, school, sport, religion, money_work, ...)

Deliberate design choices, each one a thing that would otherwise produce a
confident wrong number:

* FORM IS STRUCTURAL, DOMAIN IS LEXICAL. Form comes from templates that are
  nearly unambiguous ("knock knock"); domain comes from a keyword lexicon and is
  therefore reported as a GUESS with a match count, never as ground truth.
* ORDER MATTERS. Rules are tried most-specific first: a light-bulb joke is also
  a how-many joke, and "doctor, doctor" is also q_and_a. First match wins and
  the runner-ups are kept in `form_all` so the ambiguity stays visible.
* ENGLISH BIAS IS DECLARED, NOT HIDDEN. Most templates are English. Non-English
  items get `form: unknown` unless a native pattern fires (xiehouyu, Radio
  Yerevan, Beamtenwitz), and `coverage()` reports labelled-share PER LANGUAGE so
  the gap is legible instead of being averaged away.
* NO SILENT DEFAULT. `one_liner` is only assigned when the item really is a
  single short assertion. Everything unmatched stays `unknown`; inflating the
  biggest bucket with leftovers is how a taxonomy starts lying.

    python3 style_taxonomy.py selftest
    python3 style_taxonomy.py label --out dataset_out/style_labels.jsonl
    python3 style_taxonomy.py report
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
CORPORA = ROOT / "corpora"

# ---------------------------------------------------------------------------
# FORM rules — most specific first; first match wins.
# Each: (name, compiled pattern, note on the expectation/turn structure)
# ---------------------------------------------------------------------------
FORM_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("knock_knock", re.compile(r"\bknock[,!.\s]+knock\b", re.I),
     "ritual opening buys compliance; the turn is a forced mishearing of a name"),
    ("light_bulb", re.compile(r"how many .{1,40} (does|do) it take to (screw|change) .{0,20}bulb", re.I),
     "counting frame; the turn replaces the count with a group stereotype"),
    ("how_many_x", re.compile(r"\bhow many .{1,40} (does|do) it take\b", re.I),
     "counting frame; turn substitutes a non-quantitative answer"),
    ("doctor_doctor", re.compile(r"\bdoctor[,!\s]+doctor\b", re.I),
     "complaint frame; the turn takes the symptom literally"),
    ("waiter", re.compile(r"\bwaiter[,!\s]+(there'?s|there is)\b", re.I),
     "complaint frame; the turn reframes the defect as a feature"),
    ("walks_into_bar", re.compile(r"\bwalk(s|ed)? in(to)? a (bar|pub|cafe|café)\b", re.I),
     "canonical setup promising a social scene; turn breaks the frame's own logic"),
    ("yo_mama", re.compile(
        # The genre is not "a joke that mentions your mother" — that fires on
        # thousands of Chuck Norris facts (measured 2026-07-26: 5,773 of 7,177
        # raw "your mother" hits were not the genre). Two things identify it:
        # the dialectal spelling, and the comparison-escalation frame.
        r"\byo\s+(mama|mamma|momma|mom)\b"
        # `so` here takes an ADJECTIVE ("yo mama so fat"). The negative
        # lookahead drops the adverb reading, which was the one surviving false
        # positive in the 2026-07-26 sample: "...as your Mother so nicely asked".
        r"|\byo(ur)?\s+(mama|mamma|momma|mom|mother)('s)?\s+(is\s+|was\s+)?(so\s+(?!\w+ly\b)|such\b|like\b)", re.I),
     "ritual insult; turn escalates a comparison to absurd scale"),
    ("whats_the_difference", re.compile(r"\bwhat'?s the difference between\b", re.I),
     "promises a category distinction; turn answers on an unexpected axis"),
    ("what_do_you_call", re.compile(r"\bwhat do you call\b", re.I),
     "promises a name; turn delivers a pun as the name"),
    ("tom_swifty", re.compile(r"[\"'”]\s*,?\s*(said|replied)\s+\w+\s+\w+ly\s*[.\"']", re.I),
     "adverb retroactively puns on the quoted line"),
    ("wellerism", re.compile(r"[\"'”]\s*,?\s*(as|said)\s+the\s+\w+.{0,40}(said|when|as)\b", re.I),
     "proverb-shaped quote reattributed to a speaker who makes it literal"),
    ("xiehouyu", re.compile(r"[一-鿿].{0,30}(——|—{2}|--)"),
     "two-part allegorical saying: image sets the trap, tag springs it"),
    ("radio_yerevan", re.compile(r"(radio\s+yerevan|армянское радио|в принципе,? да)", re.I),
     "mock-official Q&A; the turn concedes then negates"),
    # -- ritual openers and joke cycles -------------------------------------
    ("walk_into_group", re.compile(
        r"\b(a|an|two|three)\s+\w+(\s*,\s*(a|an)\s+\w+)+\s*,?\s+and\s+(a|an)\s+\w+\b", re.I),
     "rule-of-three roster; the third member breaks the pattern the first two set"),
    ("confucius_say", re.compile(r"\bconfucius\s+say\b", re.I),
     "mock-aphorism frame; the turn lands a pun inside fake wisdom"),
    ("soviet_russia", re.compile(r"\bin\s+soviet\s+russia\b", re.I),
     "syntactic inversion IS the joke: subject and object swap roles"),
    ("chuck_norris", re.compile(r"\bchuck\s+norris\b", re.I),
     "hyperbole cycle; the turn asserts an impossibility as flat fact"),
    ("blonde_joke", re.compile(r"\b(a|the|this)\s+blonde\b", re.I),
     "stereotype cycle; the turn confirms the stereotype literally"),
    ("elephant_joke", re.compile(
        r"\b(how (do|can) you (tell|fit|know).{0,30}\belephant|why do(es)? .{0,20}elephant)\b", re.I),
     "absurd-premise cycle; the turn answers a nonsense question earnestly"),
    ("whats_worse_than", re.compile(r"\bwhat'?s worse than\b", re.I),
     "promises escalation; the turn escalates on an unexpected axis"),
    ("how_is_x_like_y", re.compile(r"\b(why|how) (is|are) (a|an|the)? ?\w+ like\b", re.I),
     "forced analogy; the turn finds a shared property that recontextualises both"),
    ("roses_are_red", re.compile(r"\broses are red\b", re.I),
     "rhyme scheme sets an expectation of sentiment; the turn refuses it"),
    ("thats_what_she_said", re.compile(r"\bthat'?s what she said\b", re.I),
     "retroactive reframing: an innocent line is re-read as innuendo"),
    ("take_my_wife", re.compile(r"\btake my wife\b[\s.,—-]*please", re.I),
     "syntactic ambiguity: 'take' as example versus as removal"),
    ("anti_joke", re.compile(
        r"\b(anti[- ]?joke)\b|\bwhy did the chicken cross the road\?\s*to get to the other side\b", re.I),
     "the turn REFUSES to resolve; the failure to repair is the payload"),
    ("shaggy_dog_marker", re.compile(r"\b(long story short|to make a long story short)\b", re.I),
     "narrative investment flagged explicitly; the payoff is disproportionate"),
    ("paraprosdokian", re.compile(
        r"\b(until I|but that'?s not|then I realis|then I realiz)\w*\b.{0,40}$", re.I),
     "the final clause forces reinterpretation of everything before it"),

    # -- non-English native forms -------------------------------------------
    # Fixes a measured gap: before these, specific-form coverage outside English
    # was approximately zero, so every non-English item fell into a generic
    # bucket and the taxonomy silently described only English humor.
    ("de_treffen_sich", re.compile(r"\btreffen sich (zwei|drei)\b", re.I),
     "German roster opener; the turn breaks the enumerated pattern"),
    ("de_arzt", re.compile(r"\bkommt ein (mann|patient) zum arzt\b", re.I),
     "German doctor frame; the turn takes the complaint literally"),
    ("de_beamten", re.compile(r"\bbeamt(er|en)\b.{0,60}\b(witz|arbeit|schlaf)", re.I),
     "civil-servant cycle; the turn confirms institutional inertia"),
    ("ru_shtirlitz", re.compile(r"\bштирлиц\b", re.I),
     "Russian cycle built on deadpan literalisation of a spy-film register"),
    ("ru_vovochka", re.compile(r"\bвовочк[аиуе]\b", re.I),
     "child-narrator cycle; the turn voices what adults will not"),
    ("ru_anekdot_open", re.compile(r"^\s*(приходит|заходит|встречаются)\s+(мужик|два|три)\b", re.I),
     "anekdot opener; a stock scene whose logic the turn violates"),
    ("fr_monsieur_madame", re.compile(
        r"\bmonsieur et madame\b.{0,60}\b(ont un fils|ont une fille|comment)", re.I),
     "the child's full name is a phonetic pun on a sentence"),
    ("es_que_le_dice", re.compile(r"¿?\s*qué le dice\b|\bva un \w+ y le dice\b", re.I),
     "Spanish stock dialogue opener; the reply puns on the setup"),
    ("pt_o_que_e", re.compile(r"\bo que é,? o que é\b", re.I),
     "Portuguese riddle formula; the answer resolves by wordplay"),
    ("it_roster", re.compile(
        r"\bci sono un(a)? \w+,? un(a)? \w+ e un(a)? \w+\b", re.I),
     "Italian national-roster opener; the third breaks the pattern"),
    ("ja_dajare", re.compile(r"(だじゃれ|ダジャレ|親父ギャグ|おやじギャグ)"),
     "Japanese sound-pun; the turn reuses a homophone in a new sense"),
    ("ko_ajae", re.compile(r"(아재\s*개그|아재개그)"),
     "Korean 'uncle gag'; a groan-inducing homophone pun"),
    ("he_pun_marker", re.compile(r"\bבדיחה\b"),
     "Hebrew joke marker"),

    # NOTE: limerick is NOT in this table. The opener alone ("There was a fly
    # in my soup") is not the form — the form IS the AABBA rhyme, so it is
    # checked by _is_limerick() below, after a rhyme verification.
    ("dialogue", re.compile(r"^\s*[-–—\"']|\b(he|she|they) (said|asked|replied)\b.*[\"']", re.I),
     "reported speech; turn is a reply that reinterprets the line"),
]


def _rule_trigger(rules: Iterable[tuple[str, re.Pattern[str], str]]) -> re.Pattern[str]:
    """One exact OR prefilter for an otherwise linear regex rule table.

    Most of the multi-million-row corpus matches no named form. Scanning all 41
    expressions in that overwhelmingly negative case cost nearly a second per
    thousand captions. Inline flags preserve each rule's original case
    sensitivity; a positive trigger still runs the original rules so
    precedence and `form_all` remain byte-for-byte unchanged.
    """
    arms = []
    for _, pattern, _ in rules:
        body = pattern.pattern
        arms.append(f"(?i:{body})" if pattern.flags & re.I else f"(?:{body})")
    return re.compile("|".join(arms))


_FORM_TRIGGER = _rule_trigger(FORM_RULES)

# Question-answer forms are checked after the named templates above.
_Q_OPEN = re.compile(r"^\s*(why|what|when|where|who|how|which|did you hear|"
                     r"do you know)\b", re.I)
_QMARK = re.compile(r"\?")


_LIM_OPEN = re.compile(r"^\s*there\s+(once\s+)?(was|were)\s+an?\b", re.I)
_UNIT_SPLIT = re.compile(r"[\n;,.!?]+")
_RHYME_TAIL = re.compile(r"([aeiouy]+[^aeiouy]*)$", re.I)


def _rhyme_key(word: str) -> str:
    """Last vowel-cluster plus its coda, orthographic. 'Hunt'/'shunt' -> 'unt'.

    Orthographic, not phonetic: it will miss rhymes the ear accepts and accept
    a few it rejects. One systematic English case is normalised because it cost
    a real detection: `front` rhymes with `hunt`, but spells its /ʌ/ with an o
    (so does son, come, love, done, none, month). Nothing else is normalised —
    a longer table would be guessing.
    """
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    m = _RHYME_TAIL.search(w)
    key = m.group(1) if m else w[-2:]
    key = re.sub(r"^o([nmv])", r"u\1", key)      # front/hunt, come/hum, love/dove
    return key


def _is_limerick(raw: str) -> bool:
    """AABBA end-rhyme over five units, verified rather than assumed.

    Measured on this corpus 2026-07-26: the bare opener regex matched 652 items
    of which a manual read put roughly a quarter in the form ("There was a fly
    in my soup" is not a limerick). Requiring the rhyme scheme is the whole
    difference between a template and a shape.
    """
    if not _LIM_OPEN.match(raw):
        return False
    # A limerick is a five-LINE form. When the text carries line breaks, they
    # are the ground truth and punctuation is not: splitting the fourth line
    # `and by yelling out 'duck!',` on punctuation produced a stray "'" unit,
    # pushed line five out of position, and rejected a genuine limerick.
    if "\n" in raw:
        units = [u.strip() for u in raw.split("\n") if re.search(r"[A-Za-z]", u)]
    else:
        # No line breaks (most of this corpus is space-joined), so fall back to
        # punctuation. Units must carry a letter: splitting `out 'duck!',` on
        # punctuation leaves a stray quote that is not a line and would
        # otherwise push line five out of position and sink a real match.
        units = [u.strip() for u in _UNIT_SPLIT.split(raw) if re.search(r"[A-Za-z]", u)]
    if len(units) < 5:
        return False
    keys = []
    for u in units[:5]:
        # A token must START with a letter: `[A-Za-z']+` happily matches the
        # orphan apostrophe left by `out 'duck!',` and then the rhyme word of
        # line four is a quote mark with no rhyme at all.
        words = re.findall(r"[A-Za-z][A-Za-z']*", u)
        keys.append(_rhyme_key(words[-1]) if words else "")
    if not all(keys):
        return False
    a1, a2, b1, b2, a3 = keys
    # The two couplets are required; the fifth line is NOT, because an
    # orthographic key cannot be trusted over five chances to disagree with the
    # ear. Both rhyming pairs landing in the right positions, behind the
    # opener, is already a strong conjunction.
    return a1 == a2 and b1 == b2 and a1 != b1


def _looks_two_part(text: str, meta: dict[str, Any]) -> bool:
    if meta.get("setup") and meta.get("punchline"):
        return True
    return bool(_QMARK.search(text) and not text.rstrip().endswith("?"))


# ---------------------------------------------------------------------------
# DOMAIN lexicon — a GUESS, reported with its match count.
# ---------------------------------------------------------------------------
DOMAIN_LEXICON: dict[str, tuple[str, ...]] = {
    "military": ("army", "navy", "soldier", "sergeant", "general", "marine",
                 "colonel", "platoon", "barracks", "recruit", "veteran",
                 "air force", "military", "commander", "captain", "corporal",
                 "battalion", "drill instructor", "boot camp", "salute"),
    "medical": ("doctor", "nurse", "patient", "hospital", "surgeon", "medicine",
                "prescription", "dentist", "therapist", "surgery", "clinic",
                "diagnosis", "pharmacist", "x-ray", "symptom"),
    "legal": ("lawyer", "attorney", "judge", "court", "jury", "lawsuit",
              "prosecutor", "verdict", "testimony", "defendant", "litigation"),
    # Branch-level military, because "military humor" is not one register:
    # a boot-camp joke and a submarine joke share almost no vocabulary.
    "mil_army": ("army", "infantry", "platoon", "barracks", "sergeant",
                 "drill instructor", "boot camp", "grunt", "foxhole", "fatigues"),
    "mil_navy": ("navy", "sailor", "submarine", "destroyer", "frigate", "admiral",
                 "starboard", "port side", "swab", "seaman", "aircraft carrier"),
    "mil_air": ("air force", "pilot", "airman", "squadron", "cockpit", "fighter jet",
                "hangar", "wingman", "flight deck", "afterburner"),
    "mil_marines": ("marine corps", "marines", "jarhead", "semper fi", "devil dog"),
    "aviation": ("airline", "cockpit", "stewardess", "flight attendant", "runway",
                 "turbulence", "altitude", "co-pilot", "air traffic control",
                 "boarding", "layover"),
    "nautical": ("ship", "boat", "captain", "crew", "anchor", "harbour", "harbor",
                 "deck", "mast", "pirate", "sail", "voyage", "shipwreck"),
    "farming": ("farmer", "barn", "tractor", "harvest", "crop", "cattle", "plough",
                "plow", "livestock", "silo", "pasture"),
    "retail_service": ("customer", "cashier", "waiter", "waitress", "barista",
                       "receipt", "refund", "manager", "complaint", "tip",
                       "shift", "checkout"),
    "politics": ("politician", "senator", "congress", "president", "election",
                 "campaign", "vote", "parliament", "governor", "mayor",
                 "diplomat", "bureaucrat"),
    "music": ("guitar", "drummer", "violin", "orchestra", "banjo", "piano",
              "trumpet", "band", "conductor", "singer", "accordion", "viola"),
    "tech": ("computer", "programmer", "software", "code", "developer", "bug",
             "server", "database", "python", "javascript", "algorithm",
             "internet", "wifi", "password", "keyboard", "sysadmin", "api",
             "compile", "byte", "binary", "git", "linux"),
    "science": ("physicist", "chemist", "biologist", "atom", "molecule",
                "neutron", "electron", "quantum", "gravity", "experiment",
                "laboratory", "hypothesis", "scientist", "helium"),
    "animal": ("dog", "cat", "horse", "cow", "chicken", "duck", "bear", "fish",
               "bird", "elephant", "penguin", "rabbit", "mouse", "pig", "sheep",
               "monkey", "lion", "tiger", "snake", "frog"),
    "food": ("bread", "cheese", "pizza", "coffee", "beer", "egg", "potato",
             "sandwich", "restaurant", "cook", "chef", "bacon", "soup", "cake",
             "butter", "tomato", "onion", "wine"),
    "family": ("wife", "husband", "mother", "father", "son", "daughter",
               "marriage", "married", "divorce", "grandma", "grandpa", "kids",
               "baby", "in-law", "spouse"),
    "school": ("teacher", "student", "school", "class", "homework", "exam",
               "principal", "professor", "university", "college", "pupil",
               "grade", "textbook"),
    "sport": ("football", "soccer", "basketball", "baseball", "golf", "tennis",
              "coach", "referee", "hockey", "boxing", "marathon", "olympic"),
    "religion": ("priest", "rabbi", "pastor", "church", "heaven", "god",
                 "monk", "nun", "prayer", "temple", "mosque", "imam", "saint"),
    "money_work": ("boss", "office", "salary", "meeting", "employee", "manager",
                   "bank", "money", "invoice", "deadline", "promotion",
                   "interview", "resume", "startup", "budget"),
    "police_crime": ("police", "cop", "officer", "thief", "prison", "arrest",
                     "detective", "burglar", "criminal", "jail"),
    "transport": ("car", "train", "plane", "pilot", "bus", "taxi", "bicycle",
                  "traffic", "driver", "boat", "ship", "sailor"),
    "dark": ("funeral", "death", "died", "grave", "corpse", "coffin",
             "cremat", "widow", "morgue", "obituary"),
}
_DOMAIN_RE = {d: re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b",
                            re.I)
              for d, words in DOMAIN_LEXICON.items()}

_DOMAIN_TERMS = sorted(
    {word.casefold() for words in DOMAIN_LEXICON.values() for word in words},
    key=lambda word: (-len(word), word),
)
_DOMAIN_WORD_RE = re.compile(r"[a-z]+", re.I)
_DOMAIN_ANCHORS = {
    re.match(r"[a-z]+", term).group()  # every domain term is ASCII and word-led
    for term in _DOMAIN_TERMS
}


def classify_form(text: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return {form, form_all, why}. `form_all` keeps every template that fired
    so an ambiguous item stays visibly ambiguous."""
    meta = meta or {}
    t = " ".join(text.split())
    hits = ([(name, why) for name, pat, why in FORM_RULES if pat.search(t)]
            if _FORM_TRIGGER.search(t) else [])
    # limerick sits where it always sat in the precedence order — after every
    # named template, ahead of `dialogue` — but it is verified on the RAW text,
    # because the rhyme scheme lives in the line breaks that `t` just discarded.
    if not hits or hits[0][0] == "dialogue":
        if _is_limerick(text):
            return {"form": "limerick",
                    "form_all": ["limerick"] + [h[0] for h in hits],
                    "why": "metrical AABBA frame; the turn lands on the forced final rhyme"}
    if hits:
        return {"form": hits[0][0], "form_all": [h[0] for h in hits],
                "why": hits[0][1]}
    # Q&A vs one-liner, only for clearly-Latin-script text
    if len(t) > 900:
        return {"form": "shaggy_dog", "form_all": ["shaggy_dog"],
                "why": "long narrative investment; the turn refuses the payoff"}
    if _Q_OPEN.match(t) and _looks_two_part(t, meta):
        return {"form": "q_and_a", "form_all": ["q_and_a"],
                "why": "explicit question sets a search; the turn answers off-axis"}
    if meta.get("setup") and meta.get("punchline"):
        return {"form": "setup_punchline", "form_all": ["setup_punchline"],
                "why": "declared two-part structure"}
    if len(t) <= 240 and not _QMARK.search(t) and t.count(".") <= 2:
        return {"form": "one_liner", "form_all": ["one_liner"],
                "why": "single assertion; the turn is inside the sentence"}
    return {"form": "unknown", "form_all": [], "why": ""}


def classify_domain(text: str) -> dict[str, Any]:
    # Exact negative prefilter: an actual keyword match must contain its first
    # word as a token. Most caption/proverb rows have none, so they avoid 25
    # regex scans. A possible false positive merely runs the original rules;
    # it cannot alter a label. The original per-domain scans remain the source
    # of truth so overlapping domains are preserved.
    if _DOMAIN_ANCHORS.isdisjoint(
            word.casefold() for word in _DOMAIN_WORD_RE.findall(text)):
        return {"domain": "general", "domain_all": [], "domain_hits": 0}
    counts = {d: len(rx.findall(text)) for d, rx in _DOMAIN_RE.items()}
    counts = {d: c for d, c in counts.items() if c}
    if not counts:
        return {"domain": "general", "domain_all": [], "domain_hits": 0}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"domain": ranked[0][0],
            "domain_all": [d for d, _ in ranked],
            "domain_hits": ranked[0][1]}


def label_item(rec: dict[str, Any]) -> dict[str, Any]:
    text = rec.get("text", "")
    meta = rec.get("meta", {}) or {}
    out = classify_form(text, meta) | classify_domain(text)
    # The exported/flattened schema lifts `language` to the top level while the
    # raw corpus keeps it under `meta`. Reading only one of the two made every
    # exported row read as "unknown" — silently, since unknown is a valid value.
    out["language"] = meta.get("language") or rec.get("language") or "unknown"
    out["source"] = rec.get("source", "")
    # a declared style from the API beats an inferred one
    if meta.get("style"):
        out["declared_style"] = meta["style"]
    return out


# ---------------------------------------------------------------------------
def iter_corpus(paths: Iterable[Path] | None = None, *, strict: bool = False):
    """Yield corpus records.

    Interactive analysis keeps the historical best-effort default. Release
    builders pass ``strict=True`` so a truncated JSONL line or unreadable file
    cannot silently disappear from published counts.
    """
    for p in sorted(paths or CORPORA.glob("*.jsonl")):
        try:
            with p.open(encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        if strict:
                            raise ValueError(
                                f"malformed JSON in {p}:{line_no}: {exc.msg}"
                            ) from exc
                        continue
                    if "_meta" in rec or not rec.get("text"):
                        continue
                    yield rec
        except OSError:
            if strict:
                raise
            continue


# Buckets that any short text falls into. They are real forms, but they carry
# almost no information: a Swedish proverb is a single short assertion, so it
# lands in `one_liner` and a naive coverage number then reads 99.8% for Swedish.
# Coverage is therefore reported twice, and the SPECIFIC number is the honest one.
GENERIC_FORMS = {"one_liner", "setup_punchline", "q_and_a", "dialogue"}


def _coverage_report(per_lang: dict[str, Counter]) -> dict[str, Any]:
    return {lang: {"n": c["n"], "labelled": c["labelled"],
                   "share": round(c["labelled"] / c["n"], 3) if c["n"] else 0.0,
                   "specific": c["specific"],
                   "specific_share": round(c["specific"] / c["n"], 3) if c["n"] else 0.0}
            for lang, c in sorted(per_lang.items(), key=lambda kv: -kv[1]["n"])}


def coverage(labels: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Labelled share PER LANGUAGE, split into any-form and specific-form.

    `share` counts every non-unknown form and will look high everywhere.
    `specific_share` counts only named templates (knock_knock, xiehouyu, ...)
    and is the number that actually says whether the taxonomy sees a language.
    """
    per_lang: dict[str, Counter] = {}
    for lab in labels:
        c = per_lang.setdefault(lab.get("language", "unknown"), Counter())
        c["n"] += 1
        if lab["form"] != "unknown":
            c["labelled"] += 1
        if lab["form"] not in GENERIC_FORMS and lab["form"] != "unknown":
            c["specific"] += 1
    return _coverage_report(per_lang)


SELFTEST_CASES: list[tuple[str, str]] = [
    ("Knock knock. Who's there? Boo. Boo who? Don't cry, it's just a joke.", "knock_knock"),
    ("How many programmers does it take to change a light bulb? None, that's a hardware problem.", "light_bulb"),
    ("How many surrealists does it take to change a lightbulb? A fish.", "light_bulb"),
    ("Doctor, doctor, I feel like a pair of curtains! Pull yourself together.", "doctor_doctor"),
    ("Waiter, there's a fly in my soup! Don't worry sir, the spider on the bread will get it.", "waiter"),
    ("A horse walks into a bar. The bartender says, why the long face?", "walks_into_bar"),
    ("What's the difference between a lawyer and a leech? The leech stops sucking after you die.", "whats_the_difference"),
    ("What do you call a fish with no eyes? A fsh.", "what_do_you_call"),
    ("\"I've lost all my flowers,\" said Tom lackadaisically.", "tom_swifty"),
    ("泥菩萨过江——自身难保", "xiehouyu"),
    ("Why did the scarecrow win an award? He was outstanding in his field.", "q_and_a"),
    ("I told my wife she was drawing her eyebrows too high. She looked surprised.", "one_liner"),
    # 2026-07-26 precision fixes. Each negative case is a REAL corpus item that
    # the previous rules mislabelled, kept verbatim so the fix cannot regress.
    ("There once was a driver named Hunt,\nwho was given an engine to shunt.\n"
     "Saw an oncoming truck,\nand by yelling out 'duck!',\nsaved the lives of the men up front.", "limerick"),
    ("There was a fly in my soup", "one_liner"),                      # was: limerick
    ("There was a snake in his boot.", "one_liner"),                  # was: limerick
    ("There was a regime change and Truman is a cat person.", "one_liner"),   # was: limerick
    ("Yo mama so fat she has her own area code.", "yo_mama"),
    ("Your momma is so stupid she stared at a juice box because it said concentrate.", "yo_mama"),
    ("Okay, you win! We'll give it to your mother.", "one_liner"),    # was: yo_mama
    # Kept from the yo_mama tightening (it must never read as yo_mama), but the
    # expectation moved once a chuck_norris template existed: naming the cycle
    # it actually belongs to is more informative than the generic bucket.
    ("When Chuck Norris has an erection lasting more than four hours "
     "he doesn't call your doctor, he calls your mother.", "chuck_norris"),
    # non-English forms — before these existed, every one of these fell into a
    # generic bucket and non-English specific coverage measured ~0%
    ("Treffen sich zwei Jäger. Beide tot.", "de_treffen_sich"),
    ("Штирлиц шёл по коридору. По коридору — это по-шведски.", "ru_shtirlitz"),
    ("Monsieur et Madame Térieur ont un fils. Comment s'appelle-t-il ? Alex.",
     "fr_monsieur_madame"),
    ("O que é, o que é? Cai em pé e corre deitado.", "pt_o_que_e"),
    ("In Soviet Russia, car drives you!", "soviet_russia"),
    ("Confucius say man who run behind car get exhausted.", "confucius_say"),
]


def selftest() -> int:
    bad = 0
    for text, want in SELFTEST_CASES:
        got = classify_form(text)["form"]
        ok = got == want
        bad += not ok
        print(f"  {'ok ' if ok else 'FAIL'} {want:<22} got={got:<22} {text[:52]!r}")
    dom = classify_domain("The sergeant told the recruit to salute the colonel.")
    ok = dom["domain"] == "military"
    bad += not ok
    print(f"  {'ok ' if ok else 'FAIL'} domain military          got={dom['domain']}")
    dom2 = classify_domain("just a sentence about nothing at all")
    ok2 = dom2["domain"] == "general"
    bad += not ok2
    print(f"  {'ok ' if ok2 else 'FAIL'} domain general           got={dom2['domain']}")
    print(f"\n{len(SELFTEST_CASES) + 2 - bad}/{len(SELFTEST_CASES) + 2} passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["selftest", "label", "report"])
    ap.add_argument("--out", default="dataset_out/style_labels.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    if a.cmd == "selftest":
        return selftest()

    # Stream labels and aggregate counters in one pass. The previous version
    # wrote a checkpoint but ALSO retained every label in a list and rewrote
    # the whole output afterwards. At 2.7M rows that defeated the checkpoint's
    # purpose and made memory, rather than classification, the bottleneck.
    out_path = ROOT / a.out
    stream = out_path.with_suffix(".partial.jsonl")
    sfh = None
    if a.cmd == "label":
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sfh = stream.open("w", encoding="utf-8")
    forms: Counter = Counter()
    domains: Counter = Counter()
    # Keep the publishable cross-tab in the same pass as labelling. Generic
    # shapes and the length-only shaggy_dog proxy are excluded here because
    # neither supports a domain-by-form claim; the complete marginal counts
    # remain in `forms` above.
    domain_specific_forms: dict[str, Counter] = {}
    per_lang: dict[str, Counter] = {}
    n_labels = 0
    try:
        for i, rec in enumerate(iter_corpus()):
            if a.limit and i >= a.limit:
                break
            lab = label_item(rec)
            n_labels += 1
            forms[lab["form"]] += 1
            domains[lab["domain"]] += 1
            if (lab["domain"] != "general" and
                    lab["form"] not in GENERIC_FORMS | {"unknown", "shaggy_dog"}):
                domain_specific_forms.setdefault(lab["domain"], Counter())[lab["form"]] += 1
            lang_counts = per_lang.setdefault(lab.get("language", "unknown"), Counter())
            lang_counts["n"] += 1
            if lab["form"] != "unknown":
                lang_counts["labelled"] += 1
            if lab["form"] not in GENERIC_FORMS and lab["form"] != "unknown":
                lang_counts["specific"] += 1
            if sfh is not None:
                sfh.write(json.dumps(lab, ensure_ascii=False) + "\n")
            if i and i % 250_000 == 0:
                if sfh is not None:
                    sfh.flush()
                print(f"  ... {i:,} labelled", flush=True)
    finally:
        if sfh is not None:
            sfh.close()

    print(f"items labelled: {n_labels}\n")
    print("FORM distribution:")
    for k, v in forms.most_common():
        print(f"  {k:<22} {v:>7}  {v / n_labels:>6.1%}")
    print("\nDOMAIN distribution:")
    for k, v in domains.most_common():
        print(f"  {k:<22} {v:>7}  {v / n_labels:>6.1%}")
    spec = sum(v for k, v in forms.items()
               if k not in GENERIC_FORMS and k != "unknown")
    print(f"\nspecific (non-generic) forms: {spec} = {spec / n_labels:.1%} "
          f"— the rest sit in the catch-all buckets {sorted(GENERIC_FORMS)}")
    print("\nFORM coverage by language (top 15) — 'spec' is the honest column:")
    cov = _coverage_report(per_lang)
    for lang, c in list(cov.items())[:15]:
        print(f"  {lang:<10} n={c['n']:>7}  any={c['share']:>6.1%}  "
              f"spec={c['specific']:>6} {c['specific_share']:>6.1%}")

    print("\nDOMAIN x specific FORM (generic and length-proxy forms excluded):")
    for domain, counts in sorted(domain_specific_forms.items(),
                                 key=lambda kv: -sum(kv[1].values())):
        top = ", ".join(f"{form} {count}" for form, count in counts.most_common(3))
        print(f"  {domain:<22} n={sum(counts.values()):>6}  {top}")

    if a.cmd == "label":
        assembled = out_path.with_suffix(".assembled.tmp")
        with assembled.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"_meta": {"n": n_labels,
                                           "forms": dict(forms),
                                           "domains": dict(domains),
                                           "coverage_by_language": cov,
                                           "domain_specific_forms": {
                                               domain: dict(counts)
                                               for domain, counts in
                                               sorted(domain_specific_forms.items())
                                           }}},
                                ensure_ascii=False) + "\n")
            with stream.open(encoding="utf-8") as rows:
                shutil.copyfileobj(rows, fh, length=1024 * 1024)
        assembled.replace(out_path)
        stream.unlink()
        print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
