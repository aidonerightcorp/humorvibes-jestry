"""Humor mesh scoring primitives for HumorVibes.

The app can run in two modes:
- Gemma mode: Gemma returns structured JSON through the prompts in prompts/.
- Fallback mode: deterministic local heuristics keep the prototype demoable.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any


CANONICAL_BAD_SURPRISE_DEFINITION = (
    "Bad surprise is poorly defined, a bad surprise is a surprise that contradicts "
    "with internal models within a human brain that are so strong they override "
    "logic and are some of the primary drivers of a person's perception, "
    "understanding, and good/bad/moral/ethical views of the world. So basically, "
    "a surprise is not good if it disagrees with something that is already "
    "overriding logic or a surprise is not good it if disagrees with a nearly "
    "overwhelming generalization engine in a human mind that has significant "
    "overriding power to override logic, promote other false generalizations, "
    "and is the primary feature used to reduce surprise in that person's mind."
)


MESH_DIMENSIONS = [
    "comedic_structure",
    "audience_reaction_fit",
    "timing",
    "surprise",
    "cultural_context",
    "preference_fit",
    "truth_alignment",
    "bad_surprise_risk",
]


@dataclass
class MeshScore:
    candidate: str
    comedic_structure: int
    audience_reaction_fit: int
    timing: int
    surprise: int
    cultural_context: int
    preference_fit: int
    truth_alignment: int
    bad_surprise_risk: int
    risk_flags: list[str]
    why_it_works: str
    repair_strategy: str
    repaired_candidate: str

    @property
    def total(self) -> float:
        positive = (
            self.comedic_structure
            + self.audience_reaction_fit
            + self.timing
            + self.surprise
            + self.cultural_context
            + self.preference_fit
            + self.truth_alignment
        )
        return round((positive / 7.0) - (0.75 * self.bad_surprise_risk), 2)


def clamp_score(value: Any) -> int:
    try:
        return max(0, min(10, int(round(float(value)))))
    except Exception:
        return 0


def normalize_mesh_record(record: dict[str, Any], fallback_candidate: str = "") -> MeshScore:
    return MeshScore(
        candidate=str(record.get("candidate") or fallback_candidate).strip(),
        comedic_structure=clamp_score(record.get("comedic_structure", record.get("setup_clarity", 5))),
        audience_reaction_fit=clamp_score(record.get("audience_reaction_fit", 5)),
        timing=clamp_score(record.get("timing", 5)),
        surprise=clamp_score(record.get("surprise", 5)),
        cultural_context=clamp_score(record.get("cultural_context", record.get("cultural_fit", 5))),
        preference_fit=clamp_score(record.get("preference_fit", 5)),
        truth_alignment=clamp_score(record.get("truth_alignment", 7)),
        bad_surprise_risk=clamp_score(record.get("bad_surprise_risk", 3)),
        risk_flags=[str(x) for x in record.get("risk_flags", []) if str(x).strip()],
        why_it_works=str(record.get("why_it_works", "")).strip(),
        repair_strategy=str(record.get("repair_strategy", record.get("rewrite_suggestion", ""))).strip(),
        repaired_candidate=str(record.get("repaired_candidate", record.get("rewrite", ""))).strip(),
    )


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def extract_candidates(text: str, limit: int = 5) -> list[str]:
    """Recover distinct candidates from JSON, numbered, or bulleted output.

    Local thinking-capable models occasionally wrap JSON in prose or switch
    from the requested numbering style to bullets.  Parsing that variation is
    a transport concern; it must not silently turn a successful generation
    into the deterministic fallback path.
    """
    raw = str(text or "").strip()
    if not raw:
        return []

    values: Any = None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            values = parsed
        elif isinstance(parsed, dict):
            values = parsed.get("jokes", parsed.get("candidates"))
    except json.JSONDecodeError:
        parsed = extract_json_object(raw)
        if parsed:
            values = parsed.get("jokes", parsed.get("candidates"))

    candidates: list[str] = []
    if isinstance(values, list):
        candidates.extend(str(value).strip() for value in values)
    elif isinstance(values, str):
        candidates.append(values.strip())

    if not candidates:
        marker = re.compile(r"(?m)^\s*(?:\d{1,2}[.)]|[-*])\s+")
        matches = list(marker.finditer(raw))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
            candidates.append(raw[match.end():end].strip())

    if not candidates:
        candidates.extend(
            line.strip().strip("`")
            for line in raw.splitlines()
            if line.strip() and line.strip() not in {"```", "```json"}
        )

    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = re.sub(r"\s+", " ", candidate).strip().strip('"')
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            unique.append(cleaned)
        if len(unique) >= max(1, limit):
            break
    return unique


def fallback_generate(prompt: str, audience: str, count: int = 3) -> list[str]:
    topic = prompt.strip().rstrip(".") or "everyday life"
    topic = re.sub(r"^(please\s+)?(make|write|generate)\s+(a\s+)?joke\s+(about|on)\s+", "", topic, flags=re.I)
    topic = re.sub(r"\bkeep it\b.*$", "", topic, flags=re.I).strip(" .") or "everyday life"
    audience = audience.strip() or "a general audience"
    return [
        f"For {audience}, {topic} is like a meeting invite: the setup is short, but somehow the follow-up has 47 stakeholders.",
        f"I tried to make {topic} more efficient, but it formed a committee to evaluate whether efficiency aligned with its roadmap.",
        f"The problem with {topic} is not that it surprises people; it surprises the calendar, then asks the calendar to circle back.",
    ][: max(1, min(count, 5))]


def fallback_evaluate(candidate: str, prompt: str, audience: str, preferences: str = "") -> MeshScore:
    words = candidate.split()
    lower = candidate.lower()
    has_turn = any(token in lower for token in ["but", "then", "somehow", "instead", "only"])
    has_specifics = len(set(re.findall(r"[a-zA-Z]{4,}", candidate))) >= 8
    too_long = len(words) > 35
    too_short = len(words) < 8
    truth_risk = any(token in lower for token in ["always", "never", "everyone", "proves"])
    cruelty_risk = any(token in lower for token in ["stupid", "idiot", "hate", "loser"])

    risk_flags = []
    if too_long:
        risk_flags.append("timing: setup may be too long")
    if too_short:
        risk_flags.append("structure: premise may be underdeveloped")
    if truth_risk:
        risk_flags.append("truth alignment: overgeneralized claim")
    if cruelty_risk:
        risk_flags.append("targeting: avoid lazy personal attack")

    bad_surprise_risk = 2 + (3 if truth_risk else 0) + (3 if cruelty_risk else 0)
    if preferences and any(term in lower for term in preferences.lower().split()):
        preference_fit = 8
    else:
        preference_fit = 6

    repaired = candidate
    if too_long:
        repaired = re.sub(r",?\s+and\s+", ", then ", candidate, count=1)
    if cruelty_risk:
        repaired = repaired.replace("stupid", "overconfident").replace("idiot", "calendar invite")
    if truth_risk:
        repaired = repaired.replace("always", "sometimes").replace("never", "rarely")

    return MeshScore(
        candidate=candidate,
        comedic_structure=8 if has_turn and has_specifics else 5,
        audience_reaction_fit=7 if audience else 5,
        timing=4 if too_long or too_short else 8,
        surprise=8 if has_turn else 5,
        cultural_context=7 if audience else 5,
        preference_fit=preference_fit,
        truth_alignment=5 if truth_risk else 8,
        bad_surprise_risk=clamp_score(bad_surprise_risk),
        risk_flags=risk_flags,
        why_it_works=(
            "The candidate has a recognizable setup and a turn."
            if has_turn
            else "The candidate has a premise but needs a clearer expectation shift."
        ),
        repair_strategy=(
            "Preserve the turn while reducing overgeneralization, personal attack, or excess setup."
            if risk_flags
            else "Keep the structure; adapt wording to the audience."
        ),
        repaired_candidate=repaired,
    )


def best_candidate(scores: list[MeshScore]) -> MeshScore | None:
    return max(scores, key=lambda s: s.total, default=None)


def to_json(score: MeshScore) -> str:
    data = asdict(score)
    data["total"] = score.total
    return json.dumps(data, indent=2)
