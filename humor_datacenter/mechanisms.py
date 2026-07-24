"""Comedy mechanisms and concrete rewrite moves."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ComedyMechanism:
    mechanism_id: str
    name: str
    description: str
    best_when: tuple[str, ...]
    rewrite_moves: tuple[str, ...]
    risk_notes: tuple[str, ...]
    study_hooks: tuple[str, ...]
    keywords: tuple[str, ...]
    priority: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


COMEDY_MECHANISMS: tuple[ComedyMechanism, ...] = (
    ComedyMechanism(
        "script_opposition",
        "Script Opposition",
        "A setup activates one interpretation, then the punchline reveals a compatible opposing script.",
        ("classic jokes", "headline edits", "clean expectation shifts"),
        (
            "name the assumed script before the punchline",
            "make the second script arrive at the last content word",
            "preserve compatibility between both interpretations",
        ),
        ("fails when the second script is random or unresolved",),
        ("SSTH/GTVH", "incongruity-resolution", "Humicroedit"),
        ("script", "opposition", "incongruity", "reinterpretation", "punchline"),
        10,
    ),
    ComedyMechanism(
        "false_analogy",
        "False Analogy",
        "Treats two things as equivalent in a way that is locally legible but logically strained.",
        ("satire", "topical jokes", "political or institutional humor"),
        (
            "map the serious topic onto a mundane process",
            "keep one shared property and exaggerate the mismatch",
            "make the analogy collapse in the punchline",
        ),
        ("can become misinformation if the analogy implies a false factual claim",),
        ("Reverse-Engineering Satire", "GTVH logical mechanism"),
        ("analogy", "satire", "metaphor", "political", "institution"),
        8,
    ),
    ComedyMechanism(
        "wordplay_pun",
        "Wordplay / Pun",
        "Uses sound, spelling, ambiguity, or double meaning as the turn.",
        ("short jokes", "family-safe humor", "language play"),
        (
            "identify a keyword with a second sense or sound neighbor",
            "keep the setup short enough that the wordplay lands",
            "avoid explaining the pun after it lands",
        ),
        ("often weak for audiences that dislike groan-heavy humor", "translation risk is high"),
        ("computational pun generation", "Witscript", "word humor embeddings"),
        ("pun", "wordplay", "double meaning", "sound", "rhyme"),
        7,
    ),
    ComedyMechanism(
        "misdirection_reversal",
        "Misdirection / Reversal",
        "Guides the audience toward one expectation, then flips the direction at the end.",
        ("one-liners", "workplace jokes", "observational humor"),
        (
            "hide the turn until the last phrase",
            "replace a generic ending with a specific reversed object",
            "cut setup clauses that reveal the reversal early",
        ),
        ("can feel manipulative if the setup withholds essential information unfairly",),
        ("setup/punchline surprisal", "Humor Mechanics multistep reasoning"),
        ("misdirection", "reversal", "twist", "surprise", "one-liner"),
        10,
    ),
    ComedyMechanism(
        "rule_of_three",
        "Rule Of Three / AAB",
        "Builds two matching beats, then makes the third beat deviate.",
        ("lists", "speeches", "clean rhythm", "audience warmups"),
        (
            "make beats one and two structurally parallel",
            "make beat three shorter or more specific",
            "put the strongest concrete noun in the third beat",
        ),
        ("too many beats dull the expectation",),
        ("AAB humor pattern", "punchline narrative structure"),
        ("three", "list", "aab", "rhythm", "beat"),
        8,
    ),
    ComedyMechanism(
        "callback_tag",
        "Callback / Tag",
        "Reuses a previous joke object after the audience has learned its comic meaning.",
        ("live sets", "successful previous jokes", "audience rapport"),
        (
            "reuse the strongest image from the prior laugh",
            "shorten the callback compared with the original",
            "tag only after laughter has peaked",
        ),
        ("callbacks fail when the original joke did not land",),
        ("standup timing", "live response adaptation"),
        ("callback", "tag", "previous", "laughter", "set"),
        8,
    ),
    ComedyMechanism(
        "specificity_concreteness",
        "Specificity / Concreteness",
        "Makes a joke funnier by replacing abstract labels with vivid objects, roles, or actions.",
        ("confused audiences", "generic AI output", "low laughter after vague wording"),
        (
            "replace abstract nouns with visible objects",
            "name a role, place, or tiny behavior",
            "make the punchline imageable",
        ),
        ("over-specific references can exclude audiences without shared context",),
        ("Jokeasy source material workflow", "semantic language delivery"),
        ("specific", "concrete", "image", "generic", "vague"),
        9,
    ),
    ComedyMechanism(
        "hyperbole_understatement",
        "Hyperbole / Understatement",
        "Scales a normal fact absurdly up or down.",
        ("observational humor", "low-stakes topics", "self-enhancing humor"),
        (
            "exaggerate only one dimension",
            "keep the emotional truth recognizable",
            "use understatement after a high-stakes setup",
        ),
        ("can become bad surprise if exaggeration attacks a protected audience model",),
        ("incongruity", "relief", "humor style research"),
        ("hyperbole", "understatement", "scale", "absurd", "tiny"),
        7,
    ),
    ComedyMechanism(
        "anthropomorphism",
        "Anthropomorphism",
        "Gives human motives to tools, systems, animals, or abstractions.",
        ("AI jokes", "technology jokes", "workplace systems"),
        (
            "give the system one petty human desire",
            "make the motive bureaucratic or emotionally familiar",
            "avoid implying false technical claims",
        ),
        ("can blur factual understanding if framed as literal capability",),
        ("AI humor generation", "human-computer interaction humor"),
        ("ai", "robot", "tool", "system", "calendar", "computer"),
        8,
    ),
    ComedyMechanism(
        "status_inversion",
        "Status Inversion",
        "Makes the high-status actor or system briefly low-status.",
        ("authority jokes", "bureaucracy", "political bridge jokes"),
        (
            "target a process or role rather than voter identity",
            "make the powerful thing reveal a petty weakness",
            "keep the audience out of the butt position unless requested",
        ),
        ("political and workplace audiences can read this as identity attack if target is too broad",),
        ("superiority theory", "political portability", "humor styles"),
        ("status", "power", "authority", "manager", "political", "institution"),
        8,
    ),
    ComedyMechanism(
        "shared_frustration",
        "Shared Frustration",
        "Turns a widely felt irritation into a shared comic object.",
        ("mixed audiences", "political bridge goals", "local observational humor"),
        (
            "choose a frustration both sides recognize",
            "target the friction instead of the group",
            "make the audience feel seen before surprising them",
        ),
        ("fails if only one subgroup recognizes the frustration",),
        ("audience preference", "political portability", "affiliative humor"),
        ("shared", "frustration", "bipartisan", "bridge", "audience", "local"),
        9,
    ),
    ComedyMechanism(
        "self_deprecation",
        "Self-Deprecation",
        "Places the speaker, not the audience, in the vulnerable comic position.",
        ("warmups", "trust building", "high-sensitivity audiences"),
        (
            "make the flaw low-stakes and specific",
            "avoid making the speaker seem incompetent in a critical context",
            "pivot from self-target to shared insight",
        ),
        ("repeated self-defeating humor can lower perceived confidence",),
        ("Humor Styles Questionnaire", "workplace/education humor"),
        ("self", "self-deprecating", "trust", "speaker", "warmup"),
        7,
    ),
    ComedyMechanism(
        "irony_sarcasm",
        "Irony / Sarcasm",
        "Says one thing while intending a contrasting stance that must be inferred from context.",
        ("known audiences", "parody", "voice-driven material"),
        (
            "make the intended stance recoverable",
            "add context before the ironic line",
            "avoid sarcasm for low-context or mixed audiences",
        ),
        ("high bad-surprise risk when the audience cannot infer stance",),
        ("SARC", "MUStARD", "political parody detection"),
        ("sarcasm", "irony", "parody", "stance", "voice"),
        6,
    ),
    ComedyMechanism(
        "bathos_anti_joke",
        "Bathos / Anti-Joke",
        "Sets up importance and ends with a deliberately mundane or anticlimactic resolution.",
        ("alt comedy", "audiences comfortable with form play"),
        (
            "inflate the setup, then end with a tiny literal detail",
            "signal playful form-breaking if audience tolerance is low",
            "use sparingly inside a set",
        ),
        ("can read as simply unfunny if audience expects conventional punchlines",),
        ("anti-joke structure", "incongruity without full resolution"),
        ("anti-joke", "bathos", "anticlimax", "mundane", "literal"),
        5,
    ),
)


def rank_mechanisms(prompt: str, audience: str = "", preferences: str = "", limit: int = 8) -> list[ComedyMechanism]:
    text = " ".join([prompt, audience, preferences]).lower()
    scored: list[tuple[int, ComedyMechanism]] = []
    for mechanism in COMEDY_MECHANISMS:
        score = mechanism.priority
        haystack = " ".join(
            [
                mechanism.name,
                mechanism.description,
                " ".join(mechanism.best_when),
                " ".join(mechanism.rewrite_moves),
                " ".join(mechanism.keywords),
            ]
        ).lower()
        for term in text.replace("/", " ").replace("-", " ").split():
            if len(term) >= 4 and term in haystack:
                score += 3
        if any(term in text for term in ["political", "partisan", "liberal", "conservative", "bridge"]):
            if mechanism.mechanism_id in {"shared_frustration", "status_inversion", "false_analogy"}:
                score += 7
            if mechanism.mechanism_id == "irony_sarcasm":
                score -= 2
        if any(term in text for term in ["ai", "robot", "tool", "software", "calendar"]):
            if mechanism.mechanism_id in {"anthropomorphism", "misdirection_reversal", "specificity_concreteness"}:
                score += 6
        if any(term in text for term in ["confused", "confusion", "silence", "vague", "generic"]):
            if mechanism.mechanism_id in {"specificity_concreteness", "script_opposition"}:
                score += 6
        if any(term in text for term in ["tag", "callback", "worked", "laughter"]):
            if mechanism.mechanism_id == "callback_tag":
                score += 8
        scored.append((score, mechanism))
    scored.sort(key=lambda item: (item[0], item[1].priority, item[1].mechanism_id), reverse=True)
    return [mechanism for _, mechanism in scored[:limit]]


def mechanism_context_block(prompt: str, audience: str = "", preferences: str = "", limit: int = 5) -> str:
    lines = []
    for mechanism in rank_mechanisms(prompt, audience, preferences, limit=limit):
        moves = "; ".join(mechanism.rewrite_moves[:2])
        risk = "; ".join(mechanism.risk_notes[:1])
        lines.append(f"- {mechanism.name}: {moves}. Risk: {risk}")
    return "\n".join(lines)
