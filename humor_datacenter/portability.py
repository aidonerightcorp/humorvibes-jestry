"""Cross-ideology and dominant-model portability checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass


PARTISAN_TERMS = {
    "liberal",
    "conservative",
    "democrat",
    "democrats",
    "republican",
    "republicans",
    "left",
    "right",
    "maga",
    "woke",
    "progressive",
    "socialist",
    "nationalist",
}

SHARED_TARGET_TERMS = {
    "bureaucracy",
    "printer",
    "calendar",
    "committee",
    "meeting",
    "traffic",
    "paperwork",
    "forms",
    "algorithm",
    "software",
    "wifi",
    "train",
    "process",
    "institution",
}

ABSOLUTE_CLAIMS = {"always", "never", "everyone", "nobody", "all", "none", "evil", "stupid"}


@dataclass(frozen=True)
class PortabilityTest:
    test_id: str
    name: str
    question: str
    fail_signal: str
    repair_move: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PortabilityAssessment:
    score: int
    flags: tuple[str, ...]
    repairs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


PORTABILITY_TESTS: tuple[PortabilityTest, ...] = (
    PortabilityTest(
        "label_swap",
        "Label-Swap Test",
        "Does the mechanism still work if political labels are swapped?",
        "The joke only works as in-group victory over an out-group.",
        "Move the target from identity label to process, institution, incentive, or shared frustration.",
    ),
    PortabilityTest(
        "target_location",
        "Target Location Test",
        "Is the target voter identity, politician, institution, process, or human foible?",
        "The audience itself is made the butt of the joke without permission.",
        "Aim upward, inward, or at a shared system failure.",
    ),
    PortabilityTest(
        "moral_frame",
        "Moral-Frame Test",
        "Does the punchline require one side to accept the other side's moral hierarchy?",
        "A subgroup must surrender a dominant moral model before the joke can resolve.",
        "Use symmetry, tradeoff language, or concrete stakes instead of moral condemnation.",
    ),
    PortabilityTest(
        "shared_frustration",
        "Shared-Frustration Test",
        "Can both sides map the joke onto something they already find absurd?",
        "Only one subgroup recognizes the frustration or the target.",
        "Choose bureaucracy, media incentives, status games, paperwork, technology failure, or local inconvenience.",
    ),
    PortabilityTest(
        "bad_surprise",
        "Bad-Surprise Test",
        "Does the surprise collide with a dominant internal model strongly enough to override the joke's local logic?",
        "Audience reaction becomes moral defense, not surprise resolution.",
        "Preserve local surprise while removing identity-wide claims and broad moral labels.",
    ),
)


def assess_portability(candidate: str, audience: str = "", preferences: str = "") -> PortabilityAssessment:
    text = " ".join([candidate, audience, preferences]).lower()
    terms = {token.strip(".,;:!?()[]{}\"'") for token in text.split()}
    flags: list[str] = []
    repairs: list[str] = []
    score = 8

    partisan_hits = sorted(terms & PARTISAN_TERMS)
    if partisan_hits:
        flags.append(f"contains partisan labels: {', '.join(partisan_hits)}")
        repairs.append("run label-swap and replace labels with process/institution language if bridge is required")
        score -= 2

    absolute_hits = sorted(terms & ABSOLUTE_CLAIMS)
    if absolute_hits:
        flags.append(f"uses high-authority absolute wording: {', '.join(absolute_hits)}")
        repairs.append("replace absolute claims with specific behavior, scene, or incentive")
        score -= 2

    if any(term in text for term in ["voters are", "people like you", "your side", "those people"]):
        flags.append("points at audience identity rather than a shared comic object")
        repairs.append("move the target to a role, institution, process, or speaker self-target")
        score -= 3

    if not (terms & SHARED_TARGET_TERMS):
        flags.append("no obvious shared-frustration object detected")
        repairs.append("add one concrete shared object such as a meeting, form, printer, calendar, or process")
        score -= 1

    if any(term in text for term in ["bridge", "bipartisan", "mixed political", "cross-ideology", "cross ideology"]):
        if partisan_hits:
            repairs.append("prefer symmetrical hypocrisy or shared bureaucracy over partisan label contrast")
            score -= 1
        if not (terms & SHARED_TARGET_TERMS):
            score -= 1

    score = max(0, min(10, score))
    if not flags:
        flags.append("no major portability flags from heuristic scan")
    if not repairs:
        repairs.append("preserve the current target and test one sharper wording variant")
    return PortabilityAssessment(score=score, flags=tuple(dedupe(flags)), repairs=tuple(dedupe(repairs)))


def portability_context_block(prompt: str, audience: str = "", preferences: str = "") -> str:
    text = " ".join([prompt, audience, preferences]).lower()
    if not any(term in text for term in ["politic", "partisan", "liberal", "conservative", "bipartisan", "ideolog", "bridge"]):
        return "No explicit cross-ideology trigger; still avoid broad moral claims about the audience."
    lines = ["Cross-ideology portability tests:"]
    for test in PORTABILITY_TESTS:
        lines.append(f"- {test.name}: {test.question} Repair: {test.repair_move}")
    return "\n".join(lines)


def dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
