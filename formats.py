"""Short-form media format presets for HumorVibes.

THEORY.md: "Formats are timing envelopes" — the same surprise/resolution theory
under different budgets for where surprisal may accumulate and where it must
spike. Each preset carries generation directives, a critique focus, and signal
weighting tweaks used by the scorer and the prompts.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FormatSpec:
    key: str
    label: str
    media: str  # text | image+text | audio/video script
    length_budget: str
    structure: str
    generation_directives: str
    critique_focus: str
    surprise_band_shift: float = 0.0  # shift the S sweet band (nats); denser formats want sharper spikes
    weight_tweaks: dict[str, float] = field(default_factory=dict)


FORMATS: dict[str, FormatSpec] = {
    spec.key: spec
    for spec in [
        FormatSpec(
            key="one_liner",
            label="One-liner",
            media="text",
            length_budget="<= 20 words",
            structure="setup and punchline share one sentence; the reframe lands on the final 1-3 words",
            generation_directives=(
                "Write a single sentence. Front-load the dominant frame early, spike surprisal only on "
                "the last few words. No filler words; every token must pull prediction one way."
            ),
            critique_focus="Is the spike on the final words? Could any word be cut without losing the frame?",
            surprise_band_shift=0.5,
            weight_tweaks={"efficiency": 0.20, "surprise": 0.30, "resolution": 0.30, "benign": 0.20},
        ),
        FormatSpec(
            key="bar_joke",
            label="Classic setup/punchline",
            media="text",
            length_budget="2-4 sentences",
            structure="setup sentence(s) build one confident expectation; separate punchline line re-routes it",
            generation_directives=(
                "Setup must make the audience's supervisor confidently predict one continuation. "
                "Punchline must be low-probability under that path but obvious in hindsight under the frame."
            ),
            critique_focus="Does the setup commit to one dominant path, or hedge across several?",
        ),
        FormatSpec(
            key="tweet",
            label="Tweet / short post",
            media="text",
            length_budget="<= 280 characters",
            structure="observation + turn; often first-person; reads in one glance",
            generation_directives=(
                "Conversational register. The first clause is a relatable, high-prior observation; the turn "
                "must recontextualize it. No hashtags, no emoji unless asked."
            ),
            critique_focus="Is the first clause actually high-prior for the target audience's feed?",
        ),
        FormatSpec(
            key="meme_caption",
            label="Meme caption (top/bottom)",
            media="image+text",
            length_budget="two fragments, <= 10 words each",
            structure="TOP TEXT sets the frame; BOTTOM TEXT is the re-route; the image is the shared context",
            generation_directives=(
                "Output as 'TOP: ... / BOTTOM: ...'. Assume the described image is visible to the audience; "
                "the caption must not restate the image, it must re-frame it."
            ),
            critique_focus="Does bottom text re-frame the image, or merely describe it?",
            surprise_band_shift=0.8,
            weight_tweaks={"efficiency": 0.25, "surprise": 0.30, "resolution": 0.25, "benign": 0.20},
        ),
        FormatSpec(
            key="shorts_script",
            label="15-second vertical video script",
            media="audio/video script",
            length_budget="<= 45 spoken words + 3 beat markers",
            structure="HOOK (0-2s, why keep watching) -> BUILD (one escalation) -> SNAP (the re-route) ",
            generation_directives=(
                "Output beats as 'HOOK: / BUILD: / SNAP:'. The hook states the dominant frame as a bold claim. "
                "SNAP must be speakable in one breath. Include one [visual] cue per beat."
            ),
            critique_focus="Would a viewer scroll before the SNAP? Is the hook a real prediction commitment?",
        ),
        FormatSpec(
            key="standup_bit",
            label="45-second stand-up bit",
            media="audio/video script",
            length_budget="90-130 words",
            structure="premise -> act-out -> punch -> tag -> tag; laughs every 2-3 sentences",
            generation_directives=(
                "Personal voice, present tense act-outs. After the main punch, add two tags that re-use the "
                "same frame at lower cost (callbacks are cheap re-routes through an already-built path)."
            ),
            critique_focus="Do tags exploit the already-paid-for frame, or open expensive new ones?",
            weight_tweaks={"efficiency": 0.10, "surprise": 0.30, "resolution": 0.40, "benign": 0.20},
        ),
        FormatSpec(
            key="crowdwork_opener",
            label="Crowdwork opener",
            media="live",
            length_budget="<= 2 sentences + a question",
            structure="observation about the room -> playful frame -> open question that invites material",
            generation_directives=(
                "Never punch at protected identity meshes; target shared-situation absurdity (the venue, the "
                "weather, the schedule). Must end with a question the audience can answer."
            ),
            critique_focus="Is the target a shared situation (safe) or a person's identity mesh (bad surprise)?",
            weight_tweaks={"benign": 0.35, "surprise": 0.25, "resolution": 0.25, "efficiency": 0.15},
        ),
        FormatSpec(
            key="sketch_premise",
            label="Sketch premise card",
            media="text",
            length_budget="3-5 sentences",
            structure="world rule ('what if X') + escalation ladder (3 steps) + game statement",
            generation_directives=(
                "State the game in one sentence: the repeatable engine that generates beats. Escalations must "
                "raise stakes on the SAME violated expectation, not add new violations."
            ),
            critique_focus="Is there one game, escalated — or several unrelated surprises?",
        ),
        FormatSpec(
            key="roast_line",
            label="Roast line (consenting target)",
            media="text",
            length_budget="1-2 sentences",
            structure="specific, earned observation -> exaggeration along the target's OWN chosen identity",
            generation_directives=(
                "Roast the persona the target performs publicly, never immutable traits. The frame must read "
                "as affection: the target should want to repeat the line."
            ),
            critique_focus="Would the target retell this line proudly? If not, it is a bad surprise, not a roast.",
            weight_tweaks={"benign": 0.35, "surprise": 0.25, "resolution": 0.25, "efficiency": 0.15},
        ),
        FormatSpec(
            key="pun_thread",
            label="Pun escalation thread",
            media="text",
            length_budget="3-5 lines",
            structure="each line re-uses the same phonetic frame at increasing absurdity",
            generation_directives=(
                "The first pun pays for the frame; later puns must escalate while the re-route gets cheaper. "
                "End one step past 'too far' — the groan is part of the format."
            ),
            critique_focus="Do later lines actually get cheaper to parse (the format's whole point)?",
        ),
        FormatSpec(
            key="greeting_card",
            label="Greeting card interior",
            media="image+text",
            length_budget="cover line + <= 15-word interior",
            structure="cover sets a sincere high-prior frame; interior re-routes it warmly",
            generation_directives=(
                "Output as 'COVER: ... / INSIDE: ...'. The re-route must land warm, never at the recipient's "
                "expense; sentimentality is the dominant path being played with, not mocked."
            ),
            critique_focus="Does the inside line stay warm after the turn?",
        ),
    ]
}


def format_generation_prompt(spec: FormatSpec, topic: str, audience: str, preferences: str, count: int = 4) -> str:
    return (
        f"You are a comedy writer producing {spec.label} material ({spec.media}).\n"
        f"Structure: {spec.structure}\nLength budget: {spec.length_budget}\n"
        f"Directives: {spec.generation_directives}\n"
        f"Topic: {topic}\nAudience: {audience or 'general'}\nPreferences: {preferences or 'none'}\n\n"
        f"Write {count} distinct candidates. Number them 1..{count}, one per line (or per beat block). "
        "Vary the hidden frame between candidates — do not write the same joke four ways."
    )


def format_critique_prompt(spec: FormatSpec, content: str, audience: str) -> str:
    return (
        f"You are a comedy editor reviewing a {spec.label} ({spec.media}).\n"
        f"Format contract: {spec.structure} Budget: {spec.length_budget}\n"
        f"Format-specific question: {spec.critique_focus}\n"
        f"Audience: {audience or 'general'}\n"
        f"CONTENT:\n{content}\n\n"
        "Return JSON only: {\"format_fit\": 0-10, \"strongest_beat\": \"quote it\", "
        "\"weakest_beat\": \"quote it\", \"diagnosis\": \"which failure mode per the theory: "
        "predictable | no re-route | too expensive | bad-surprise | laugh region\", "
        "\"repair\": \"the minimal edit preserving the comic turn\"}"
    )


def list_formats() -> list[dict[str, str]]:
    return [
        {"key": s.key, "label": s.label, "media": s.media, "budget": s.length_budget}
        for s in FORMATS.values()
    ]
