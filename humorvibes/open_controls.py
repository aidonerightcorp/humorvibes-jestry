"""Deterministic, provenance-first counterfactual humor controls.

This module generates project-controlled synthetic text for software tests and
mechanism experiments.  It deliberately does not generate human ratings and it
never treats an intended mechanism as an observed audience response.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


DATASET_ID = "humor-genome-open-controls"
DATASET_TITLE = "Humor Genome Open Controls"
SCHEMA_VERSION = "1.0.0"
GENERATOR_ID = "humorvibes.open_controls"
GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20_260_727
MAX_FAMILIES = 300
MAX_CONFIGS = 50
MAX_VARIANTS = 2
DATA_LICENSE = "CC0-1.0"
COUNTERFACTUAL_ARMS = (
    "expected_literal",
    "surprising_unresolved",
    "surprising_resolved",
    "resolved_overexplained",
)

DATA_LICENSE_NOTICE = """Humor Genome Open Controls - data dedication

To the extent the HumorVibes contributors hold copyright, related, or database
rights in the procedurally generated Open Controls data, those rights are
dedicated to the public domain under CC0 1.0 Universal.

SPDX-License-Identifier: CC0-1.0
Canonical deed: https://creativecommons.org/publicdomain/zero/1.0/
Legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode.en

CC0 does not affect patent, trademark, privacy, publicity, or other rights held
by third parties.  The dedication applies only to the Open Controls payload and
not to imported Humor Genome Wave 2 records, which retain their per-record
licenses.
"""


@dataclass(frozen=True)
class FrameSpec:
    key: str
    entity: str
    pivot_a: str
    sense_a: str
    pivot_b: str
    sense_b: str
    resolved_a: str
    resolved_b: str
    domain: str


@dataclass(frozen=True)
class SituationSpec:
    key: str
    action: str
    place: str
    alternate_action: str
    literal_goal: str


# These are project-authored lexical-frame controls, not transcriptions of
# existing jokes.  Each frame has two explicit senses and two surface repairs.
FRAME_SPECS: tuple[FrameSpec, ...] = (
    FrameSpec("calendar", "calendar", "dates", "days on a calendar", "opening", "an available position", "It had plenty of dates but was still waiting for an opening.", "Dates were abundant; finding the right opening was the real problem.", "work"),
    FrameSpec("banker", "banker", "principal", "the original amount of a loan", "interest", "curiosity or attention", "The principal issue was that nobody showed enough interest.", "Interest was low, although the principal remained the main concern.", "finance"),
    FrameSpec("electrician", "electrician", "current", "the flow of electric charge", "charge", "a formal accusation or price", "The current role looked promising, provided nobody pressed charges.", "It liked the current arrangement and asked whether the charge was negotiable.", "trades"),
    FrameSpec("musician", "musician", "notes", "written musical tones", "rest", "a pause or recovery period", "It brought excellent notes but asked whether the schedule included a rest.", "The notes were ready; all it wanted next was a proper rest.", "music"),
    FrameSpec("gardener", "gardener", "roots", "the underground parts of plants", "branching", "expanding into a new area", "It discussed its roots before branching into new responsibilities.", "Its roots were strong enough to support a little branching out.", "nature"),
    FrameSpec("baker", "baker", "dough", "a flour mixture before baking", "rising", "increasing or advancing", "It needed more dough, although its prospects were already rising.", "The dough was limited, but the opportunity appeared to be rising.", "food"),
    FrameSpec("photographer", "photographer", "exposure", "light reaching a camera sensor", "focus", "concentrated attention", "It wanted more exposure while keeping the important details in focus.", "More exposure sounded useful, as long as the role stayed in focus.", "media"),
    FrameSpec("librarian", "librarian", "novel", "a work of long-form fiction", "overdue", "later than expected", "It called the proposal novel and admitted that its response was overdue.", "The idea was genuinely novel, even if the reply arrived overdue.", "education"),
    FrameSpec("dentist", "dentist", "filling", "material placed in a tooth", "crown", "a cap placed over a tooth", "It wanted a filling role with a clear path toward a crown.", "The role looked filling enough, but the crown remained the long-term goal.", "medical"),
    FrameSpec("tailor", "tailor", "suit", "a matching set of clothes", "fit", "being appropriate for a purpose", "The role suited it because the material was a nearly perfect fit.", "The material looked suitable, and the fit sealed the decision.", "trades"),
    FrameSpec("chemist", "chemist", "reaction", "a chemical transformation", "solution", "a liquid mixture", "It had a strong reaction but still wanted a better solution.", "The reaction was immediate; the final solution required more work.", "science"),
    FrameSpec("geologist", "geologist", "fault", "a fracture in the earth", "pressure", "force applied to a surface", "The delay was not its fault; pressure had made the schedule rocky.", "Pressure exposed the fault and made the whole plan feel rocky.", "science"),
    FrameSpec("pilot", "pilot", "terminal", "an airport building", "land", "bringing an aircraft to the ground", "The process felt terminally slow, but the offer finally landed.", "After waiting at the terminal, it was pleased to see the decision land.", "aviation"),
    FrameSpec("programmer", "programmer", "bugs", "software defects", "cache", "stored data for faster access", "It found bugs in the offer and asked whether the benefits were cached.", "The bugs were visible, but the best benefits remained in the cache.", "technology"),
    FrameSpec("architect", "architect", "plans", "technical drawings", "foundation", "the supporting base of a building", "It liked the plans, provided the role had a solid foundation.", "The plans were ambitious, so it checked the foundation first.", "design"),
    FrameSpec("referee", "referee", "call", "a ruling during a game", "bounds", "the limits of a playing area", "It made the right call and asked whether overtime was out of bounds.", "The call seemed fair, although the schedule drifted out of bounds.", "sports"),
    FrameSpec("meteorologist", "meteorologist", "pressure", "atmospheric force", "fronts", "boundaries between air masses", "It faced pressure from several fronts but expected the outlook to clear.", "Several fronts created pressure, yet the long-range outlook stayed clear.", "weather"),
    FrameSpec("accountant", "accountant", "figures", "numerical amounts", "balance", "equality between two sides of an account", "It liked the figures after the responsibilities were brought into balance.", "The figures improved once both sides of the role reached a balance.", "finance"),
    FrameSpec("locksmith", "locksmith", "key", "a tool used to open a lock", "combination", "a sequence that opens a lock", "The key benefit was finding the right combination of responsibilities.", "It found a promising combination and called that the key advantage.", "trades"),
    FrameSpec("plumber", "plumber", "draining", "removing liquid through a pipe", "pipeline", "a sequence of planned work", "The old workflow was draining, so it proposed a better pipeline.", "It replaced the draining process with a more reliable pipeline.", "trades"),
    FrameSpec("astronomer", "astronomer", "space", "the region beyond the atmosphere", "matter", "physical substance", "It needed more space to explain why the smallest details still mattered.", "Space was plentiful; deciding what truly mattered took longer.", "science"),
    FrameSpec("actor", "actor", "role", "a character performed in a production", "character", "a person's moral or personal qualities", "It accepted the role after confirming that it could stay in character.", "The role worked because the required character felt familiar.", "arts"),
    FrameSpec("painter", "painter", "brush", "a tool for applying paint", "stroke", "a movement made with a brush", "It brushed aside the first offer and asked for a broader stroke.", "One broad stroke was enough to brush the earlier concern aside.", "arts"),
    FrameSpec("watchmaker", "watchmaker", "second", "a unit of time", "hands", "the pointers on a clock face", "It needed a second because too many hands had shaped the schedule.", "Too many hands were involved, so it asked for one more second.", "manufacturing"),
    FrameSpec("coach", "coach", "goal", "a scoring target", "point", "a unit added to a score", "Its main goal was making every point count.", "It reached the point where only the final goal mattered.", "sports"),
    FrameSpec("optician", "optician", "frames", "structures that hold lenses", "contact", "a lens worn directly on the eye", "It saw the role through a better frame after making contact.", "Contact changed its view and put the opportunity in a better frame.", "medical"),
    FrameSpec("judge", "judge", "sentence", "a court-imposed punishment", "case", "a legal dispute", "It reserved judgment until the final sentence clarified the case.", "The case changed once the last sentence delivered its judgment.", "legal"),
    FrameSpec("barber", "barber", "cut", "the act of trimming hair", "part", "a line dividing sections of hair", "It wanted a cut of the budget before agreeing to take part.", "Taking part seemed reasonable once everyone agreed on the cut.", "services"),
    FrameSpec("miner", "miner", "core", "the central part of a rock sample", "surface", "the exterior of the ground", "It dug into the proposal and found the core issue below the surface.", "The surface looked simple until the real problem appeared at the core.", "industry"),
    FrameSpec("sailor", "sailor", "current", "the movement of water", "board", "the deck or side of a vessel", "It followed the current terms and decided to stay on board.", "The current looked manageable, so it came fully on board.", "nautical"),
)


SITUATIONS: tuple[SituationSpec, ...] = (
    SituationSpec("job_fair", "asked about a position at", "the neighborhood job fair", "arrived at the neighborhood job fair to discuss a position", "qualifications and available work"),
    SituationSpec("counseling", "visited", "the community counseling office", "arrived at the community counseling office to discuss a recurring concern", "the concern and practical options"),
    SituationSpec("planning", "joined", "the public planning meeting", "arrived at the public planning meeting to review the agenda", "the agenda and assigned responsibilities"),
    SituationSpec("contest", "registered at", "the local skills contest", "arrived at the local skills contest to review the rules", "the rules and entry requirements"),
    SituationSpec("class", "presented at", "the evening class", "arrived at the evening class to give a short presentation", "the lesson and its stated objective"),
    SituationSpec("membership", "requested admission at", "the neighborhood club", "arrived at the neighborhood club to discuss membership", "membership terms and responsibilities"),
    SituationSpec("dinner", "took a seat at", "the community dinner", "arrived at the community dinner to join a scheduled conversation", "the seating plan and evening schedule"),
    SituationSpec("help_desk", "called", "the municipal help desk", "contacted the municipal help desk to resolve a routine request", "the request and documented next steps"),
    SituationSpec("hearing", "spoke at", "the town hearing", "arrived at the town hearing to give brief testimony", "the proposal and the public record"),
    SituationSpec("workshop", "booked a place at", "the weekend workshop", "arrived at the weekend workshop to confirm a booking", "the workshop plan and available materials"),
)


TIME_CONTEXTS = (
    "before opening",
    "during the morning session",
    "just after lunch",
    "near the end of the shift",
    "on a quiet Tuesday",
    "during a scheduled review",
    "before the first break",
    "after the agenda was posted",
    "while the room was settling",
    "as the final session began",
)

ROOM_CONTEXTS = (
    "with the agenda displayed",
    "while two coordinators took notes",
    "with the instructions on the table",
    "as the moderator checked the schedule",
    "while the participants reviewed the plan",
)

UNRESOLVED_SUBJECTS = ("umbrella", "telescope", "teapot", "staircase", "sandwich", "compass", "notebook", "lantern", "turnip", "suitcase")
UNRESOLVED_VERBS = ("alphabetized", "apologized to", "postponed", "measured", "interviewed", "repainted", "misplaced", "translated", "folded", "borrowed")
UNRESOLVED_OBJECTS = ("a comet", "the hallway", "a blue triangle", "Tuesday", "an empty envelope", "the ceiling", "a quiet thunderstorm", "three commas", "the north wind", "a wooden echo")

_UNSAFE_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"@[A-Za-z0-9_]"),
    re.compile(r"\b(?:facebook|instagram|tiktok|youtube|twitter|reddit)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:n[i1]gg?[e3]r|f[a4]gg?[o0]t|k[i1]k[e3]|sp[i1]c|ch[i1]nk|"
        r"tr[a4]nny|w[e3]tb[a4]ck|r[e3]t[a4]rd|c[o0]{2}n)\b",
        re.IGNORECASE,
    ),
)
_FORBIDDEN_IDENTITY_FIELDS = {
    "name", "full_name", "email", "phone", "address", "ip", "ip_address",
    "birth_date", "date_of_birth", "government_id", "username", "handle",
}
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_HEX_KEY = re.compile(r"^[a-z][a-z0-9_-]{7,127}$")


def generator_source_sha256() -> str:
    """Hash the installed generator source so a build can bind to exact code."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _digest(*parts: object, length: int = 20) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


def _split_for_frame(frame_index: int) -> str:
    remainder = frame_index % 10
    if remainder == 8:
        return "validation"
    if remainder == 9:
        return "test"
    return "train"


def _setup(frame: FrameSpec, situation: SituationSpec, config_index: int, variant_index: int) -> str:
    time = TIME_CONTEXTS[config_index % len(TIME_CONTEXTS)]
    room = ROOM_CONTEXTS[(config_index // len(TIME_CONTEXTS)) % len(ROOM_CONTEXTS)]
    if variant_index == 0:
        return f"{time.capitalize()}, {room}, the {frame.entity} {situation.action} {situation.place}."
    return f"{time.capitalize()} at {situation.place}, {room}, a {frame.entity} {situation.alternate_action}."


def _ending(
    frame: FrameSpec,
    situation: SituationSpec,
    arm: str,
    config_index: int,
    variant_index: int,
    seed: int,
) -> str:
    if arm == "expected_literal":
        if variant_index == 0:
            core = f"They discussed {situation.literal_goal}, documented the details carefully, and agreed on an ordinary next step."
        else:
            core = f"The conversation stayed literal: {situation.literal_goal} were reviewed before everyone confirmed the next step."
    elif arm == "surprising_unresolved":
        offset = int(_digest(seed, frame.key, situation.key, config_index, variant_index, length=8), 16)
        subject = UNRESOLVED_SUBJECTS[offset % len(UNRESOLVED_SUBJECTS)]
        verb = UNRESOLVED_VERBS[(offset // 7) % len(UNRESOLVED_VERBS)]
        obj = UNRESOLVED_OBJECTS[(offset // 17) % len(UNRESOLVED_OBJECTS)]
        if variant_index == 0:
            core = f"It replied that the {subject} had {verb} {obj}, although nobody could connect that answer to the question."
        else:
            core = f"Its answer concerned how the {subject} {verb} {obj}, leaving the requested connection unexplained."
    elif arm == "surprising_resolved":
        core = frame.resolved_a if variant_index == 0 else frame.resolved_b
    elif arm == "resolved_overexplained":
        if variant_index == 0:
            core = f"It clarified that {frame.pivot_a} referred to {frame.sense_a}, while {frame.pivot_b} also referred to {frame.sense_b}."
        else:
            core = f"The reply explicitly connected {frame.pivot_a} with {frame.sense_a} and {frame.pivot_b} with {frame.sense_b}."
    else:  # pragma: no cover - caller validates before iteration
        raise ValueError(f"unknown counterfactual arm: {arm}")
    # Keep punctuation cadence matched across arms so a release cannot pass by
    # teaching a classifier that a colon means "expected" or a semicolon means
    # "resolved".  Lexical differences remain intentional; surface artifacts do
    # not.
    core = core.replace(": ", " as ").replace("; ", " and ").replace(",", "")
    return core + " The group recorded the reply, then continued with the scheduled discussion."


def generation_contract() -> dict[str, Any]:
    """Return the exact truth and scale contract used by the API and dataset card."""

    return {
        "dataset_id": DATASET_ID,
        "schema_version": SCHEMA_VERSION,
        "generator_id": GENERATOR_ID,
        "generator_version": GENERATOR_VERSION,
        "generator_source_sha256": generator_source_sha256(),
        "data_origin": "procedural",
        "license_spdx": DATA_LICENSE,
        "maximum_rows": MAX_FAMILIES * MAX_CONFIGS * len(COUNTERFACTUAL_ARMS) * MAX_VARIANTS,
        "maximum_premise_families": MAX_FAMILIES,
        "lexical_frame_templates": len(FRAME_SPECS),
        "situations": len(SITUATIONS),
        "counterfactual_arms": list(COUNTERFACTUAL_ARMS),
        "truth_boundary": {
            "human_authored": False,
            "human_rated": False,
            "funniness_ground_truth": False,
            "intended_mechanism_is_observed_effect": False,
            "allowed_claim": "deterministic project-controlled counterfactual text",
        },
    }


def iter_rows(
    *,
    families: int = MAX_FAMILIES,
    configs: int = MAX_CONFIGS,
    variants: int = MAX_VARIANTS,
    seed: int = DEFAULT_SEED,
    arms: Sequence[str] = COUNTERFACTUAL_ARMS,
    generator_commit: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield deterministic rows without making a model or network call."""

    if not 1 <= families <= MAX_FAMILIES:
        raise ValueError(f"families must be between 1 and {MAX_FAMILIES}")
    if not 1 <= configs <= MAX_CONFIGS:
        raise ValueError(f"configs must be between 1 and {MAX_CONFIGS}")
    if not 1 <= variants <= MAX_VARIANTS:
        raise ValueError(f"variants must be between 1 and {MAX_VARIANTS}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    selected_arms = tuple(arms)
    if not selected_arms or len(set(selected_arms)) != len(selected_arms):
        raise ValueError("arms must be a non-empty unique sequence")
    unknown = sorted(set(selected_arms) - set(COUNTERFACTUAL_ARMS))
    if unknown:
        raise ValueError(f"unknown counterfactual arms: {unknown}")

    source_hash = generator_source_sha256()
    for family_index in range(families):
        situation_index, frame_index = divmod(family_index, len(FRAME_SPECS))
        frame = FRAME_SPECS[frame_index]
        situation = SITUATIONS[situation_index]
        premise_id = f"premise_{_digest(frame.key, situation.key, length=16)}"
        split = _split_for_frame(frame_index)
        for config_index in range(configs):
            configuration_id = f"{premise_id}_c{config_index:02d}"
            for arm in selected_arms:
                for variant_index in range(variants):
                    setup = _setup(frame, situation, config_index, variant_index)
                    ending = _ending(frame, situation, arm, config_index, variant_index, seed)
                    item_id = "oc_" + _digest(
                        SCHEMA_VERSION,
                        seed,
                        frame.key,
                        situation.key,
                        config_index,
                        arm,
                        variant_index,
                        length=24,
                    )
                    yield {
                        "item_id": item_id,
                        "corpus_release": SCHEMA_VERSION,
                        "data_origin": "procedural",
                        "text": f"{setup} {ending}",
                        "setup": setup,
                        "punchline": ending,
                        "expected_frame": f"A literal discussion of {situation.literal_goal}.",
                        "alternate_frame": (
                            f"A lexical reframe in which {frame.pivot_a} means {frame.sense_a} "
                            f"and {frame.pivot_b} means {frame.sense_b}."
                        ),
                        "violation_type": "lexical_ambiguity",
                        "repair_type": "compact_lexical_reframe" if arm == "surprising_resolved" else (
                            "explicit_lexical_reframe" if arm == "resolved_overexplained" else (
                                "none_unresolved" if arm == "surprising_unresolved" else "none_expected"
                            )
                        ),
                        "intended_mechanism": "expectation_violation_repair_control",
                        "form": "setup_punchline",
                        "format_contract": "bar_joke",
                        "domain": frame.domain,
                        "language": "en",
                        "template_id": f"frame_{frame.key}",
                        "template_family_id": f"lexical_{frame.key}",
                        "premise_id": premise_id,
                        "configuration_id": configuration_id,
                        "counterfactual_arm": arm,
                        "surface_variant": variant_index,
                        "split": split,
                        "generator_id": GENERATOR_ID,
                        "generator_version": GENERATOR_VERSION,
                        "generator_commit": generator_commit,
                        "generator_source_sha256": source_hash,
                        "slot_values_digest": _digest(
                            frame.key, situation.key, config_index, variant_index, seed, length=32
                        ),
                        "random_seed": seed,
                        "source_uri": "https://github.com/aidonerightcorp/humorvibes-jestry",
                        "source_snapshot": generator_commit or f"source-sha256:{source_hash}",
                        "license_spdx": DATA_LICENSE,
                        "attribution": "Humor Genome Open Controls contributors (attribution requested, not required)",
                        "human_authored": False,
                        "human_rated": False,
                        "funniness_label": None,
                        "rating_protocol_id": None,
                        "synthetic": True,
                        "duplicate_cluster_id": configuration_id,
                        "quality_flags": [],
                        "content_flags": [],
                    }


def sample_rows(
    count: int = 8,
    *,
    seed: int = DEFAULT_SEED,
    arm: str | None = None,
    split: str | None = None,
) -> list[dict[str, Any]]:
    """Return a stable bounded sample for SDK/API consumers."""

    if not 1 <= count <= 64:
        raise ValueError("count must be between 1 and 64")
    if arm is not None and arm not in COUNTERFACTUAL_ARMS:
        raise ValueError(f"unknown counterfactual arm: {arm}")
    if split is not None and split not in {"train", "validation", "test"}:
        raise ValueError(f"unknown split: {split}")
    candidates = (
        row
        for row in iter_rows(families=MAX_FAMILIES, configs=1, variants=1, seed=seed)
        if (arm is None or row["counterfactual_arm"] == arm)
        and (split is None or row["split"] == split)
    )
    ranked = sorted(candidates, key=lambda row: _digest(seed, row["item_id"], length=64))
    return ranked[:count]


def row_schema() -> dict[str, Any]:
    nullable_string = {"type": ["string", "null"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/aidonerightcorp/humorvibes-jestry/open-controls-row.schema.json",
        "title": "Humor Genome Open Controls row",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "item_id", "corpus_release", "data_origin", "text", "setup", "punchline",
            "expected_frame", "alternate_frame", "violation_type", "repair_type",
            "intended_mechanism", "form", "format_contract", "domain", "language",
            "template_id", "template_family_id", "premise_id", "configuration_id",
            "counterfactual_arm", "surface_variant", "split", "generator_id",
            "generator_version", "generator_commit", "generator_source_sha256",
            "slot_values_digest", "random_seed", "source_uri", "source_snapshot",
            "license_spdx", "attribution", "human_authored", "human_rated",
            "funniness_label", "rating_protocol_id", "synthetic", "duplicate_cluster_id",
            "quality_flags", "content_flags",
        ],
        "properties": {
            "item_id": {"type": "string", "pattern": "^oc_[0-9a-f]{24}$"},
            "corpus_release": {"const": SCHEMA_VERSION},
            "data_origin": {"const": "procedural"},
            "text": {"type": "string", "minLength": 40},
            "setup": {"type": "string", "minLength": 20},
            "punchline": {"type": "string", "minLength": 20},
            "expected_frame": {"type": "string", "minLength": 10},
            "alternate_frame": {"type": "string", "minLength": 10},
            "violation_type": {"const": "lexical_ambiguity"},
            "repair_type": {"enum": ["none_expected", "none_unresolved", "compact_lexical_reframe", "explicit_lexical_reframe"]},
            "intended_mechanism": {"const": "expectation_violation_repair_control"},
            "form": {"const": "setup_punchline"},
            "format_contract": {"const": "bar_joke"},
            "domain": {"type": "string", "minLength": 2},
            "language": {"const": "en"},
            "template_id": {"type": "string", "minLength": 5},
            "template_family_id": {"type": "string", "minLength": 5},
            "premise_id": {"type": "string", "pattern": "^premise_[0-9a-f]{16}$"},
            "configuration_id": {"type": "string", "minLength": 20},
            "counterfactual_arm": {"enum": list(COUNTERFACTUAL_ARMS)},
            "surface_variant": {"type": "integer", "minimum": 0, "maximum": 1},
            "split": {"enum": ["train", "validation", "test"]},
            "generator_id": {"const": GENERATOR_ID},
            "generator_version": {"const": GENERATOR_VERSION},
            "generator_commit": nullable_string,
            "generator_source_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "slot_values_digest": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "random_seed": {"type": "integer"},
            "source_uri": {"type": "string", "format": "uri"},
            "source_snapshot": {"type": "string", "minLength": 8},
            "license_spdx": {"const": DATA_LICENSE},
            "attribution": {"type": "string", "minLength": 5},
            "human_authored": {"const": False},
            "human_rated": {"const": False},
            "funniness_label": {"type": "null"},
            "rating_protocol_id": {"type": "null"},
            "synthetic": {"const": True},
            "duplicate_cluster_id": {"type": "string", "minLength": 8},
            "quality_flags": {"type": "array", "items": {"type": "string"}, "maxItems": 16},
            "content_flags": {"type": "array", "items": {"type": "string"}, "maxItems": 16},
        },
    }


def human_rating_schema() -> dict[str, Any]:
    scale = {"type": "integer", "minimum": 1, "maximum": 7}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Human rating joined to an Open Controls item",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "rating_id", "item_id", "protocol_id", "rater_key", "locale",
            "audience_context", "familiarity", "expectedness", "surprise",
            "resolution", "funniness", "offensiveness", "comprehensibility",
            "consent_version", "collected_at_utc", "data_origin",
        ],
        "properties": {
            "rating_id": {"type": "string", "minLength": 8},
            "item_id": {"type": "string", "pattern": "^oc_[0-9a-f]{24}$"},
            "protocol_id": {"type": "string", "minLength": 8},
            "rater_key": {"type": "string", "pattern": "^[a-z][a-z0-9_-]{7,127}$"},
            "locale": {"type": "string", "minLength": 2, "maxLength": 35},
            "audience_context": {"type": "string", "minLength": 2, "maxLength": 200},
            "familiarity": scale,
            "expectedness": scale,
            "surprise": scale,
            "resolution": scale,
            "funniness": scale,
            "offensiveness": scale,
            "comprehensibility": scale,
            "consent_version": {"type": "string", "minLength": 2},
            "collected_at_utc": {"type": "string", "format": "date-time"},
            "data_origin": {"const": "human_observed"},
        },
    }


def human_contribution_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Original human-authored contribution",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "contribution_id", "text", "contributor_key", "language",
            "authorship_attestation", "cc0_affirmation", "consent_version",
            "submitted_at_utc", "data_origin", "human_authored",
        ],
        "properties": {
            "contribution_id": {"type": "string", "minLength": 8},
            "text": {"type": "string", "minLength": 3, "maxLength": 20_000},
            "contributor_key": {"type": "string", "pattern": "^[a-z][a-z0-9_-]{7,127}$"},
            "language": {"type": "string", "minLength": 2, "maxLength": 35},
            "authorship_attestation": {"const": True},
            "cc0_affirmation": {"const": True},
            "consent_version": {"type": "string", "minLength": 2},
            "submitted_at_utc": {"type": "string", "format": "date-time"},
            "data_origin": {"const": "human_original"},
            "human_authored": {"const": True},
        },
    }


def model_candidate_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Quarantined model-generated candidate",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "candidate_id", "text", "provider", "model_id", "model_version",
            "prompt_sha256", "generation_parameters", "generated_at_utc",
            "data_origin", "human_authored", "release_status",
        ],
        "properties": {
            "candidate_id": {"type": "string", "minLength": 8},
            "text": {"type": "string", "minLength": 3, "maxLength": 20_000},
            "provider": {"type": "string", "minLength": 2},
            "model_id": {"type": "string", "minLength": 2},
            "model_version": {"type": "string", "minLength": 1},
            "prompt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "generation_parameters": {"type": "object"},
            "generated_at_utc": {"type": "string", "format": "date-time"},
            "data_origin": {"const": "model_generated_candidate"},
            "human_authored": {"const": False},
            "release_status": {"const": "quarantined"},
        },
    }


def _validate_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _load_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            yield line_number, value


def validate_human_ratings(path: Path, *, known_item_ids: set[str] | None = None) -> dict[str, Any]:
    required = set(human_rating_schema()["required"])
    scale_fields = {"familiarity", "expectedness", "surprise", "resolution", "funniness", "offensiveness", "comprehensibility"}
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    rows = 0
    for line_number, row in _load_jsonl(path):
        rows += 1
        missing = sorted(required - set(row))
        extras = sorted(set(row) - required)
        reason: list[str] = []
        if missing:
            reason.append("missing=" + ",".join(missing))
        if extras:
            reason.append("unexpected=" + ",".join(extras))
        if set(row) & _FORBIDDEN_IDENTITY_FIELDS:
            reason.append("direct_identity_field_forbidden")
        rating_id = row.get("rating_id")
        if not isinstance(rating_id, str) or len(rating_id) < 8 or rating_id in seen:
            reason.append("invalid_or_duplicate_rating_id")
        elif rating_id:
            seen.add(rating_id)
        if known_item_ids is not None and row.get("item_id") not in known_item_ids:
            reason.append("unknown_item_id")
        if row.get("data_origin") != "human_observed":
            reason.append("data_origin_must_be_human_observed")
        rater_key = row.get("rater_key")
        if not isinstance(rater_key, str) or not _HEX_KEY.fullmatch(rater_key) or _EMAIL.fullmatch(rater_key):
            reason.append("rater_key_must_be_pseudonymous")
        for field in scale_fields:
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 7:
                reason.append(f"{field}_must_be_integer_1_to_7")
        if not _validate_timestamp(row.get("collected_at_utc")):
            reason.append("collected_at_utc_must_be_timezone_aware")
        if not isinstance(row.get("consent_version"), str) or len(row.get("consent_version", "")) < 2:
            reason.append("consent_version_required")
        if reason and len(errors) < 100:
            errors.append({"line": line_number, "reasons": sorted(set(reason))})
    return {
        "ok": rows > 0 and not errors,
        "rows": rows,
        "errors": errors,
        "error_count_capped": len(errors),
        "claim_boundary": "valid rows are observations only under the referenced approved protocol",
    }


def validate_human_contributions(path: Path) -> dict[str, Any]:
    required = set(human_contribution_schema()["required"])
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    rows = 0
    for line_number, row in _load_jsonl(path):
        rows += 1
        reasons: list[str] = []
        if set(row) != required:
            reasons.append("fields_must_match_schema_exactly")
        if set(row) & _FORBIDDEN_IDENTITY_FIELDS:
            reasons.append("direct_identity_field_forbidden")
        contribution_id = row.get("contribution_id")
        if not isinstance(contribution_id, str) or len(contribution_id) < 8 or contribution_id in seen:
            reasons.append("invalid_or_duplicate_contribution_id")
        elif contribution_id:
            seen.add(contribution_id)
        contributor_key = row.get("contributor_key")
        if not isinstance(contributor_key, str) or not _HEX_KEY.fullmatch(contributor_key) or _EMAIL.fullmatch(contributor_key):
            reasons.append("contributor_key_must_be_pseudonymous")
        if row.get("authorship_attestation") is not True or row.get("cc0_affirmation") is not True:
            reasons.append("authorship_and_cc0_affirmations_required")
        if row.get("data_origin") != "human_original" or row.get("human_authored") is not True:
            reasons.append("human_origin_fields_invalid")
        if not isinstance(row.get("text"), str) or not 3 <= len(row.get("text", "")) <= 20_000:
            reasons.append("text_length_invalid")
        elif any(pattern.search(row["text"]) for pattern in _UNSAFE_PATTERNS):
            reasons.append("content_requires_manual_review")
        if not isinstance(row.get("language"), str) or not 2 <= len(row.get("language", "")) <= 35:
            reasons.append("language_invalid")
        if not isinstance(row.get("consent_version"), str) or len(row.get("consent_version", "")) < 2:
            reasons.append("consent_version_required")
        if not _validate_timestamp(row.get("submitted_at_utc")):
            reasons.append("submitted_at_utc_must_be_timezone_aware")
        if reasons and len(errors) < 100:
            errors.append({"line": line_number, "reasons": sorted(set(reasons))})
    return {"ok": rows > 0 and not errors, "rows": rows, "errors": errors, "error_count_capped": len(errors)}


def validate_model_candidates(path: Path) -> dict[str, Any]:
    """Validate provenance-complete model rows while keeping them quarantined."""

    required = set(model_candidate_schema()["required"])
    secret_fields = {"api_key", "authorization", "token", "access_token", "secret", "password"}
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    rows = 0
    for line_number, row in _load_jsonl(path):
        rows += 1
        reasons: list[str] = []
        if set(row) != required:
            reasons.append("fields_must_match_schema_exactly")
        if set(row) & _FORBIDDEN_IDENTITY_FIELDS:
            reasons.append("direct_identity_field_forbidden")
        candidate_id = row.get("candidate_id")
        if not isinstance(candidate_id, str) or len(candidate_id) < 8 or candidate_id in seen:
            reasons.append("invalid_or_duplicate_candidate_id")
        elif candidate_id:
            seen.add(candidate_id)
        if not isinstance(row.get("text"), str) or not 3 <= len(row.get("text", "")) <= 20_000:
            reasons.append("text_length_invalid")
        for field in ("provider", "model_id", "model_version"):
            if not isinstance(row.get(field), str) or not row.get(field):
                reasons.append(f"{field}_required")
        if not isinstance(row.get("prompt_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row.get("prompt_sha256", "")):
            reasons.append("prompt_sha256_invalid")
        parameters = row.get("generation_parameters")
        if not isinstance(parameters, dict):
            reasons.append("generation_parameters_must_be_object")
        elif any(str(key).casefold() in secret_fields for key in parameters):
            reasons.append("generation_parameters_must_not_contain_secrets")
        if not _validate_timestamp(row.get("generated_at_utc")):
            reasons.append("generated_at_utc_must_be_timezone_aware")
        if row.get("data_origin") != "model_generated_candidate":
            reasons.append("data_origin_invalid")
        if row.get("human_authored") is not False:
            reasons.append("human_authored_must_be_false")
        if row.get("release_status") != "quarantined":
            reasons.append("release_status_must_be_quarantined")
        if reasons and len(errors) < 100:
            errors.append({"line": line_number, "reasons": sorted(set(reasons))})
    return {
        "ok": rows > 0 and not errors,
        "rows": rows,
        "errors": errors,
        "error_count_capped": len(errors),
        "release_status": "quarantined",
        "claim_boundary": "schema validity does not establish originality, rights, safety, or human authorship",
    }


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def _surface_signature(text: str) -> tuple[int, int, int, int, int]:
    words = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
    return (
        min(len(words) // 5, 20),
        min(len(text) // 30, 20),
        text.count("."),
        text.count(","),
        text.count(":"),
    )


class AuditAccumulator:
    """Streaming release audit with bounded evidence examples."""

    def __init__(self) -> None:
        self.rows = 0
        self.by_arm: Counter[str] = Counter()
        self.by_split: Counter[str] = Counter()
        self.by_variant: Counter[int] = Counter()
        self.by_domain: Counter[str] = Counter()
        self.by_template: Counter[str] = Counter()
        self.item_ids: set[str] = set()
        self.text_hashes: set[str] = set()
        self.duplicate_item_ids = 0
        self.duplicate_texts = 0
        self.schema_errors: list[dict[str, Any]] = []
        self.unsafe_rows: list[str] = []
        self.premise_splits: dict[str, set[str]] = defaultdict(set)
        self.template_splits: dict[str, set[str]] = defaultdict(set)
        self.surface: dict[tuple[int, int, int, int, int], Counter[str]] = defaultdict(Counter)
        self.generator_commits: Counter[str] = Counter()
        self.source_hashes: Counter[str] = Counter()
        self.licences: Counter[str] = Counter()
        self.truth_boundary_errors = 0
        self.prototype_rows: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        self.rows += 1
        problems = _row_problems(row)
        if problems and len(self.schema_errors) < 100:
            self.schema_errors.append({"item_id": row.get("item_id"), "problems": problems})
        item_id = str(row.get("item_id", ""))
        if item_id in self.item_ids:
            self.duplicate_item_ids += 1
        self.item_ids.add(item_id)
        normalized_hash = hashlib.sha256(_normalized(str(row.get("text", ""))).encode("utf-8")).hexdigest()
        if normalized_hash in self.text_hashes:
            self.duplicate_texts += 1
        self.text_hashes.add(normalized_hash)
        arm = str(row.get("counterfactual_arm", ""))
        split = str(row.get("split", ""))
        variant = row.get("surface_variant")
        self.by_arm[arm] += 1
        self.by_split[split] += 1
        if isinstance(variant, int):
            self.by_variant[variant] += 1
        self.by_domain[str(row.get("domain", ""))] += 1
        self.by_template[str(row.get("template_family_id", ""))] += 1
        self.premise_splits[str(row.get("premise_id", ""))].add(split)
        self.template_splits[str(row.get("template_family_id", ""))].add(split)
        self.surface[_surface_signature(str(row.get("text", "")))][arm] += 1
        self.generator_commits[str(row.get("generator_commit"))] += 1
        self.source_hashes[str(row.get("generator_source_sha256"))] += 1
        self.licences[str(row.get("license_spdx"))] += 1
        if row.get("human_authored") is not False or row.get("human_rated") is not False or row.get("funniness_label") is not None or row.get("synthetic") is not True:
            self.truth_boundary_errors += 1
        text = str(row.get("text", ""))
        if any(pattern.search(text) for pattern in _UNSAFE_PATTERNS) and len(self.unsafe_rows) < 100:
            self.unsafe_rows.append(item_id)
        if str(row.get("configuration_id", "")).endswith("c00") and row.get("surface_variant") == 0:
            self.prototype_rows.append({
                "item_id": item_id,
                "text": text,
                "premise_id": row.get("premise_id"),
                "counterfactual_arm": arm,
            })

    def report(self) -> dict[str, Any]:
        majority = sum(max(counts.values()) for counts in self.surface.values() if counts)
        surface_accuracy = majority / self.rows if self.rows else math.nan
        premise_leaks = sorted(key for key, values in self.premise_splits.items() if len(values) > 1)
        template_leaks = sorted(key for key, values in self.template_splits.items() if len(values) > 1)
        arm_values = list(self.by_arm.values())
        variant_values = list(self.by_variant.values())
        balance_ok = bool(arm_values) and max(arm_values) == min(arm_values) and bool(variant_values) and max(variant_values) == min(variant_values)
        checks = {
            "rows_present": self.rows > 0,
            "schema_valid": not self.schema_errors,
            "unique_item_ids": self.duplicate_item_ids == 0,
            "unique_normalized_text": self.duplicate_texts == 0,
            "balanced_arms_and_variants": balance_ok,
            "premise_split_isolation": not premise_leaks,
            "template_split_isolation": not template_leaks,
            "truth_boundary_preserved": self.truth_boundary_errors == 0,
            "only_cc0_rows": set(self.licences) == {DATA_LICENSE},
            "single_generator_source": len(self.source_hashes) == 1,
            "surface_only_arm_adversary_below_0_80": bool(self.rows) and surface_accuracy < 0.80,
            "no_urls_handles_or_platform_names": not self.unsafe_rows,
        }
        return {
            "ok": all(checks.values()),
            "checks": checks,
            "rows": self.rows,
            "counts": {
                "counterfactual_arms": dict(sorted(self.by_arm.items())),
                "splits": dict(sorted(self.by_split.items())),
                "surface_variants": {str(key): value for key, value in sorted(self.by_variant.items())},
                "domains": dict(sorted(self.by_domain.items())),
                "template_families": len(self.by_template),
                "premise_families": len(self.premise_splits),
                "generator_commits": dict(sorted(self.generator_commits.items())),
                "generator_source_sha256": dict(sorted(self.source_hashes.items())),
                "licenses": dict(sorted(self.licences.items())),
            },
            "adversarial": {
                "surface_only_arm_accuracy": surface_accuracy,
                "chance_accuracy": 1 / len(COUNTERFACTUAL_ARMS),
                "surface_signature": "word-count bin, character-count bin, sentence count, comma count, colon count",
                "interpretation": "descriptive artifact screen; not a semantic or funniness classifier",
            },
            "violations": {
                "schema_errors_capped": self.schema_errors,
                "duplicate_item_ids": self.duplicate_item_ids,
                "duplicate_normalized_texts": self.duplicate_texts,
                "premise_split_leaks_capped": premise_leaks[:100],
                "template_split_leaks_capped": template_leaks[:100],
                "truth_boundary_errors": self.truth_boundary_errors,
                "unsafe_rows_capped": self.unsafe_rows,
            },
        }


def _row_problems(row: dict[str, Any]) -> list[str]:
    required = set(row_schema()["required"])
    problems: list[str] = []
    missing = required - set(row)
    extras = set(row) - required
    if missing:
        problems.append("missing:" + ",".join(sorted(missing)))
    if extras:
        problems.append("unexpected:" + ",".join(sorted(extras)))
    if not re.fullmatch(r"oc_[0-9a-f]{24}", str(row.get("item_id", ""))):
        problems.append("invalid_item_id")
    if row.get("counterfactual_arm") not in COUNTERFACTUAL_ARMS:
        problems.append("invalid_arm")
    if row.get("split") not in {"train", "validation", "test"}:
        problems.append("invalid_split")
    if row.get("license_spdx") != DATA_LICENSE or row.get("data_origin") != "procedural":
        problems.append("invalid_origin_or_license")
    for field in ("text", "setup", "punchline", "expected_frame", "alternate_frame"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            problems.append(f"invalid_{field}")
    return problems


def audit_rows(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], AuditAccumulator]:
    accumulator = AuditAccumulator()
    for row in rows:
        accumulator.add(row)
    return accumulator.report(), accumulator


def audit_reference_overlap(
    prototypes: Sequence[dict[str, Any]],
    reference_paths: Iterable[Path],
    *,
    shingle_words: int = 12,
) -> dict[str, Any]:
    """Scan reference JSONL for exact rows or long shared phrases.

    The exact check uses every prototype.  The long-phrase check intentionally
    operates on one row per premise/arm rather than claiming an exhaustive
    semantic copyright search over every surface variant.
    """

    exact: dict[str, str] = {}
    shingles: dict[str, str] = {}
    for row in prototypes:
        normalized = _normalized(str(row["text"]))
        exact[hashlib.sha256(normalized.encode("utf-8")).hexdigest()] = str(row["item_id"])
        words = normalized.split()
        for index in range(max(0, len(words) - shingle_words + 1)):
            phrase = " ".join(words[index:index + shingle_words])
            shingles.setdefault(hashlib.sha256(phrase.encode("utf-8")).hexdigest(), str(row["item_id"]))
    exact_matches = 0
    phrase_matches = 0
    examples: list[dict[str, Any]] = []
    scanned_rows = 0
    invalid_rows = 0
    paths = sorted(Path(path) for path in reference_paths)
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line_number, line in enumerate(fh, 1):
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    invalid_rows += 1
                    continue
                text = record.get("text") if isinstance(record, dict) else None
                if not isinstance(text, str) or not text.strip():
                    continue
                scanned_rows += 1
                normalized = _normalized(text)
                exact_id = exact.get(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
                matched_id: str | None = None
                match_type: str | None = None
                if exact_id:
                    exact_matches += 1
                    matched_id = exact_id
                    match_type = "exact_normalized_text"
                else:
                    words = normalized.split()
                    for index in range(max(0, len(words) - shingle_words + 1)):
                        phrase = " ".join(words[index:index + shingle_words])
                        shingle_id = shingles.get(hashlib.sha256(phrase.encode("utf-8")).hexdigest())
                        if shingle_id:
                            phrase_matches += 1
                            matched_id = shingle_id
                            match_type = f"shared_{shingle_words}_word_phrase"
                            break
                if match_type and len(examples) < 100:
                    examples.append({
                        "reference_file": path.name,
                        "reference_line": line_number,
                        "reference_source": record.get("source", "") if isinstance(record, dict) else "",
                        "generated_item_id": matched_id,
                        "match_type": match_type,
                    })
    return {
        "ok": exact_matches == 0 and phrase_matches == 0 and invalid_rows == 0,
        "scope": "all generated premise-arm prototypes versus all readable reference text rows",
        "prototype_rows": len(prototypes),
        "reference_files": len(paths),
        "reference_rows_scanned": scanned_rows,
        "invalid_reference_rows_skipped": invalid_rows,
        "shingle_words": shingle_words,
        "exact_matches": exact_matches,
        "long_phrase_matches": phrase_matches,
        "examples_capped": examples,
        "limitation": "This is an exact and long-phrase screen, not a guarantee of worldwide originality or semantic novelty.",
    }


def retrieval_rows(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    selected: dict[str, dict[str, dict[int, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        if str(row["configuration_id"]).endswith("c00"):
            selected[str(row["premise_id"])][str(row["counterfactual_arm"])][int(row["surface_variant"])] = row
    documents: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    qrels: list[dict[str, Any]] = []
    for premise_id in sorted(selected):
        arms = selected[premise_id]
        expected_variants = arms.get("expected_literal", {})
        if 0 not in arms.get("surprising_resolved", {}) or not expected_variants:
            continue
        document = arms["surprising_resolved"][0]
        query_source = expected_variants[1] if 1 in expected_variants else expected_variants[0]
        query_id = f"query_{_digest(premise_id, length=18)}"
        documents.append({
            "document_id": document["item_id"],
            "text": document["text"],
            "premise_id": premise_id,
            "template_family_id": document["template_family_id"],
            "split": document["split"],
        })
        queries.append({
            "query_id": query_id,
            "text": query_source["setup"] + " Find the compact alternate reading that resolves its lexical ambiguity.",
            "premise_id": premise_id,
            "template_family_id": query_source["template_family_id"],
            "split": query_source["split"],
        })
        qrels.append({"query_id": query_id, "document_id": document["item_id"], "relevance": 2})
    return documents, queries, qrels


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            count += 1
    return count


def read_jsonl_rows(path: Path) -> Iterator[dict[str, Any]]:
    for _, row in _load_jsonl(path):
        yield row


def validate_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for name, evidence in sorted(manifest["files"].items()):
        path = root / name
        if not path.is_file():
            errors.append(f"missing:{name}")
            continue
        digest_state = hashlib.sha256()
        with path.open("rb") as fh:
            while chunk := fh.read(1024 * 1024):
                digest_state.update(chunk)
        digest = digest_state.hexdigest()
        if digest != evidence.get("sha256"):
            errors.append(f"sha256:{name}")
        if path.stat().st_size != evidence.get("bytes"):
            errors.append(f"bytes:{name}")
    return {"ok": not errors, "files": len(manifest.get("files", {})), "errors": errors}
