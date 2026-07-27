"""Fail-closed contracts for real-world HumorVibes evaluation.

The workbench stores identifiers and outcomes, never joke text or direct identity.
It treats writers, not repeated audience ratings, as the independent bootstrap unit.
Synthetic fixtures exercise the contract but can never authorize a human claim.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from .errors import IntegrationError

SCHEMA_VERSION = "1.0"
CONDITIONS = ("control", "assisted")
DATA_ORIGINS = ("synthetic_contract_fixture", "human_observed")
PRIMARY_OUTCOMES = ("audience_rating", "minutes_to_draft")

PROTOCOL_FIELDS = {
    "schema_version",
    "study_id",
    "title",
    "data_origin",
    "target_population",
    "primary_outcome",
    "rating_scale_min",
    "rating_scale_max",
    "minimally_important_difference",
    "assignment_seed",
    "bootstrap_repetitions",
    "preregistered",
    "preregistration_uri",
    "external_replication",
    "minimum_writers",
    "minimum_premises",
    "minimum_audiences",
    "minimum_ratings",
    "requires_consent",
    "requires_held_out_audience",
    "retention_policy",
    "analysis_plan",
}
BUNDLE_FIELDS = {
    "schema_version",
    "study_id",
    "data_origin",
    "collection_window",
    "assignment_digest",
    "source_snapshot_digest",
    "materials",
    "audience_responses",
}
WINDOW_FIELDS = {"opened_at", "closed_at"}
MATERIAL_FIELDS = {
    "material_id",
    "writer_id",
    "premise_id",
    "condition",
    "material_version",
    "minutes_to_draft",
    "selected",
    "performed",
    "voice_preservation_rating",
    "language",
    "context_version",
    "model_config_digest",
    "permission_confirmed",
}
RESPONSE_FIELDS = {
    "response_id",
    "material_id",
    "audience_id",
    "venue_id",
    "rating",
    "laughed",
    "harm_or_regret",
    "consent_confirmed",
    "held_out",
    "recorded_at",
}
FORBIDDEN_KEYS = {
    "name",
    "full_name",
    "email",
    "phone",
    "address",
    "ip_address",
    "raw_text",
    "text",
    "prompt",
    "joke",
    "punchline",
    "demographic",
    "protected_trait",
}


def _error(code: str, message: str, *, detail: dict[str, Any] | None = None) -> IntegrationError:
    return IntegrationError(code, message, 422, detail=detail)


def _strict_keys(value: Any, expected: set[str], location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error("invalid_study_record", f"{location} must be an object.")
    keys = set(value)
    unknown = sorted(keys - expected)
    missing = sorted(expected - keys)
    if unknown:
        raise _error(
            "unknown_study_field",
            f"{location} contains fields outside the frozen schema.",
            detail={"location": location, "fields": unknown},
        )
    if missing:
        raise _error(
            "missing_study_field",
            f"{location} is missing required fields.",
            detail={"location": location, "fields": missing},
        )
    return value


def _string(value: Any, location: str, *, maximum: int = 512, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()) or len(value) > maximum:
        raise _error("invalid_study_value", f"{location} must be a bounded string.")
    return value


def _bool(value: Any, location: str) -> bool:
    if type(value) is not bool:
        raise _error("invalid_study_value", f"{location} must be a boolean.")
    return value


def _integer(value: Any, location: str, *, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _error("invalid_study_value", f"{location} must be an integer in range.")
    return value


def _number(
    value: Any,
    location: str,
    *,
    minimum: float = -1_000_000.0,
    maximum: float = 1_000_000.0,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error("invalid_study_value", f"{location} must be numeric.")
    observed = float(value)
    if not math.isfinite(observed) or not minimum <= observed <= maximum:
        raise _error("invalid_study_value", f"{location} must be finite and in range.")
    return observed


def _timestamp(value: Any, location: str) -> str:
    rendered = _string(value, location, maximum=64)
    try:
        parsed = datetime.fromisoformat(rendered.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _error("invalid_study_value", f"{location} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise _error("invalid_study_value", f"{location} must include a timezone.")
    return rendered


def _digest(value: Any, location: str) -> str:
    rendered = _string(value, location, maximum=64)
    if len(rendered) != 64 or any(char not in "0123456789abcdef" for char in rendered):
        raise _error("invalid_study_value", f"{location} must be a lowercase SHA-256 digest.")
    return rendered


def _scan_forbidden_keys(value: Any, location: str = "bundle") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_KEYS:
                raise _error(
                    "forbidden_study_field",
                    "Study exports must not contain raw material, direct identity, or inferred traits.",
                    detail={"location": f"{location}.{key}"},
                )
            _scan_forbidden_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, f"{location}[{index}]")


def default_study_protocol(*, data_origin: str = "synthetic_contract_fixture") -> dict[str, Any]:
    """Return the frozen default writer-assistance crossover protocol."""

    if data_origin not in DATA_ORIGINS:
        raise _error("invalid_data_origin", "Unsupported study data origin.")
    return {
        "schema_version": SCHEMA_VERSION,
        "study_id": "writer-assistance-crossover-v1",
        "title": "Within-writer HumorVibes assistance crossover",
        "data_origin": data_origin,
        "target_population": "Consenting comedy writers and held-out consenting audience members",
        "primary_outcome": "audience_rating",
        "rating_scale_min": 1.0,
        "rating_scale_max": 5.0,
        "minimally_important_difference": 0.25,
        "assignment_seed": 20260726,
        "bootstrap_repetitions": 5_000,
        "preregistered": False,
        "preregistration_uri": "",
        "external_replication": False,
        "minimum_writers": 12,
        "minimum_premises": 24,
        "minimum_audiences": 40,
        "minimum_ratings": 192,
        "requires_consent": True,
        "requires_held_out_audience": True,
        "retention_policy": (
            "Pseudonymous outcomes only; no raw joke text or direct identity in the analysis export; "
            "delete the linkage table on the consent schedule."
        ),
        "analysis_plan": (
            "Pair control and assisted material within writer and premise; aggregate audience ratings "
            "to material before comparison; bootstrap writer-level effects; report all outcomes and "
            "gate claims on the preregistered minimally important difference."
        ),
    }


def study_template() -> dict[str, Any]:
    """Return protocol plus exact privacy-minimized row contracts for discovery clients."""

    zero = "0" * 64
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol": default_study_protocol(),
        "material_record": {
            "material_id": "material-pseudonym",
            "writer_id": "writer-pseudonym",
            "premise_id": "paired-premise-pseudonym",
            "condition": "control",
            "material_version": "v1",
            "minutes_to_draft": 0.0,
            "selected": False,
            "performed": False,
            "voice_preservation_rating": 1.0,
            "language": "en",
            "context_version": "rehearsal-v1",
            "model_config_digest": zero,
            "permission_confirmed": True,
        },
        "audience_response_record": {
            "response_id": "response-pseudonym",
            "material_id": "material-pseudonym",
            "audience_id": "audience-pseudonym",
            "venue_id": "venue-pseudonym",
            "rating": 1.0,
            "laughed": False,
            "harm_or_regret": False,
            "consent_confirmed": True,
            "held_out": True,
            "recorded_at": "2026-01-01T00:00:00Z",
        },
        "privacy_boundary": {
            "accepted": "pseudonymous grouping IDs, condition, versions, outcomes, digests",
            "rejected": "raw joke text, prompts, names, contact details, inferred protected traits",
            "analysis_upload_endpoint": False,
        },
        "truth_boundary": {
            "synthetic_fixture_can_authorize_claim": False,
            "model_measurement_is_human_outcome": False,
            "human_claim_requires_preregistered_held_out_evidence": True,
        },
    }


def validate_protocol(protocol: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_strict_keys(protocol, PROTOCOL_FIELDS, "protocol"))
    if row["schema_version"] != SCHEMA_VERSION:
        raise _error("unsupported_study_schema", "Unsupported study protocol schema version.")
    _string(row["study_id"], "protocol.study_id", maximum=128)
    _string(row["title"], "protocol.title", maximum=256)
    if row["data_origin"] not in DATA_ORIGINS:
        raise _error("invalid_data_origin", "Unsupported study data origin.")
    _string(row["target_population"], "protocol.target_population", maximum=2_000)
    if row["primary_outcome"] not in PRIMARY_OUTCOMES:
        raise _error("invalid_primary_outcome", "Unsupported primary outcome.")
    scale_min = _number(row["rating_scale_min"], "protocol.rating_scale_min")
    scale_max = _number(row["rating_scale_max"], "protocol.rating_scale_max")
    if scale_max <= scale_min:
        raise _error("invalid_rating_scale", "rating_scale_max must exceed rating_scale_min.")
    _number(
        row["minimally_important_difference"],
        "protocol.minimally_important_difference",
        minimum=0.0,
        maximum=scale_max - scale_min if row["primary_outcome"] == "audience_rating" else 1_000_000,
    )
    _integer(row["assignment_seed"], "protocol.assignment_seed", maximum=2**31 - 1)
    _integer(row["bootstrap_repetitions"], "protocol.bootstrap_repetitions", minimum=200, maximum=100_000)
    _bool(row["preregistered"], "protocol.preregistered")
    _string(row["preregistration_uri"], "protocol.preregistration_uri", maximum=2_000, allow_empty=True)
    if row["preregistered"] and not str(row["preregistration_uri"]).startswith("https://"):
        raise _error("invalid_preregistration", "A preregistered study requires an HTTPS record URI.")
    _bool(row["external_replication"], "protocol.external_replication")
    for field in ("minimum_writers", "minimum_premises", "minimum_audiences", "minimum_ratings"):
        _integer(row[field], f"protocol.{field}", minimum=1)
    _bool(row["requires_consent"], "protocol.requires_consent")
    _bool(row["requires_held_out_audience"], "protocol.requires_held_out_audience")
    _string(row["retention_policy"], "protocol.retention_policy", maximum=4_000)
    _string(row["analysis_plan"], "protocol.analysis_plan", maximum=8_000)
    return row


def validate_study_bundle(protocol: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a study export without retaining extra fields."""

    plan = validate_protocol(protocol)
    _scan_forbidden_keys(bundle)
    root = dict(_strict_keys(bundle, BUNDLE_FIELDS, "bundle"))
    if root["schema_version"] != SCHEMA_VERSION:
        raise _error("unsupported_study_schema", "Unsupported study bundle schema version.")
    if root["study_id"] != plan["study_id"] or root["data_origin"] != plan["data_origin"]:
        raise _error("study_protocol_mismatch", "Bundle identity or origin does not match the protocol.")
    window = _strict_keys(root["collection_window"], WINDOW_FIELDS, "bundle.collection_window")
    opened = _timestamp(window["opened_at"], "bundle.collection_window.opened_at")
    closed = _timestamp(window["closed_at"], "bundle.collection_window.closed_at")
    if datetime.fromisoformat(closed.replace("Z", "+00:00")) < datetime.fromisoformat(opened.replace("Z", "+00:00")):
        raise _error("invalid_collection_window", "Collection close must not precede open.")
    _digest(root["assignment_digest"], "bundle.assignment_digest")
    _digest(root["source_snapshot_digest"], "bundle.source_snapshot_digest")
    if not isinstance(root["materials"], list) or not root["materials"]:
        raise _error("invalid_study_materials", "Bundle must contain material records.")
    if not isinstance(root["audience_responses"], list) or not root["audience_responses"]:
        raise _error("invalid_study_responses", "Bundle must contain audience responses.")

    materials: list[dict[str, Any]] = []
    material_ids: set[str] = set()
    block_conditions: dict[tuple[str, str], set[str]] = defaultdict(set)
    scale_min = float(plan["rating_scale_min"])
    scale_max = float(plan["rating_scale_max"])
    for index, value in enumerate(root["materials"]):
        location = f"bundle.materials[{index}]"
        row = dict(_strict_keys(value, MATERIAL_FIELDS, location))
        for field in ("material_id", "writer_id", "premise_id", "material_version", "language", "context_version"):
            _string(row[field], f"{location}.{field}", maximum=128)
        if row["material_id"] in material_ids:
            raise _error("duplicate_material_id", "Material IDs must be unique.")
        material_ids.add(row["material_id"])
        if row["condition"] not in CONDITIONS:
            raise _error("invalid_study_condition", "Condition must be control or assisted.")
        block = (row["writer_id"], row["premise_id"])
        if row["condition"] in block_conditions[block]:
            raise _error("duplicate_block_condition", "Each writer-premise block needs one record per condition.")
        block_conditions[block].add(row["condition"])
        _number(row["minutes_to_draft"], f"{location}.minutes_to_draft", minimum=0.0)
        _bool(row["selected"], f"{location}.selected")
        _bool(row["performed"], f"{location}.performed")
        _number(row["voice_preservation_rating"], f"{location}.voice_preservation_rating", minimum=scale_min, maximum=scale_max)
        _digest(row["model_config_digest"], f"{location}.model_config_digest")
        if not _bool(row["permission_confirmed"], f"{location}.permission_confirmed"):
            raise _error("material_permission_missing", "Every analyzed material record requires confirmed permission.")
        materials.append(row)
    incomplete = [f"{writer}/{premise}" for (writer, premise), arms in sorted(block_conditions.items()) if arms != set(CONDITIONS)]
    if incomplete:
        raise _error(
            "incomplete_paired_block",
            "Each writer-premise block must contain control and assisted material.",
            detail={"blocks": incomplete[:20]},
        )

    responses: list[dict[str, Any]] = []
    response_ids: set[str] = set()
    for index, value in enumerate(root["audience_responses"]):
        location = f"bundle.audience_responses[{index}]"
        row = dict(_strict_keys(value, RESPONSE_FIELDS, location))
        for field in ("response_id", "material_id", "audience_id", "venue_id"):
            _string(row[field], f"{location}.{field}", maximum=128)
        if row["response_id"] in response_ids:
            raise _error("duplicate_response_id", "Response IDs must be unique.")
        response_ids.add(row["response_id"])
        if row["material_id"] not in material_ids:
            raise _error("unknown_material_reference", "Audience response references an unknown material.")
        _number(row["rating"], f"{location}.rating", minimum=scale_min, maximum=scale_max)
        _bool(row["laughed"], f"{location}.laughed")
        _bool(row["harm_or_regret"], f"{location}.harm_or_regret")
        consent = _bool(row["consent_confirmed"], f"{location}.consent_confirmed")
        held_out = _bool(row["held_out"], f"{location}.held_out")
        if plan["requires_consent"] and not consent:
            raise _error("audience_consent_missing", "Unconsented responses cannot enter the analysis export.")
        if plan["requires_held_out_audience"] and not held_out:
            raise _error("audience_not_held_out", "The protocol requires held-out audience responses.")
        _timestamp(row["recorded_at"], f"{location}.recorded_at")
        responses.append(row)
    return {**root, "materials": materials, "audience_responses": responses}


def _percentile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        return math.nan
    position = (len(sorted_values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _writer_clustered_effects(
    block_effects: Mapping[str, Sequence[float]], *, seed: int, repetitions: int
) -> tuple[float, list[float]]:
    writers = sorted(block_effects)
    writer_means = {
        writer: sum(block_effects[writer]) / len(block_effects[writer]) for writer in writers
    }
    estimate = sum(writer_means.values()) / len(writer_means)
    rng = random.Random(seed)
    bootstrapped: list[float] = []
    for _ in range(repetitions):
        selected = [writers[rng.randrange(len(writers))] for _ in writers]
        bootstrapped.append(sum(writer_means[writer] for writer in selected) / len(selected))
    return estimate, sorted(bootstrapped)


def analyze_study(protocol: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Analyze paired writer blocks and return an evidence-gated receipt."""

    plan = validate_protocol(protocol)
    data = validate_study_bundle(plan, bundle)
    materials = {row["material_id"]: row for row in data["materials"]}
    ratings: dict[str, list[float]] = defaultdict(list)
    for row in data["audience_responses"]:
        ratings[row["material_id"]].append(float(row["rating"]))
    missing_ratings = sorted(material_id for material_id in materials if not ratings[material_id])
    if missing_ratings:
        raise _error(
            "material_without_rating",
            "Every material must have at least one audience rating.",
            detail={"material_ids": missing_ratings[:20]},
        )

    by_block: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in materials.values():
        by_block[(row["writer_id"], row["premise_id"])][row["condition"]] = row
    block_effects: dict[str, list[float]] = defaultdict(list)
    for (writer, _premise), arms in sorted(by_block.items()):
        control, assisted = arms["control"], arms["assisted"]
        if plan["primary_outcome"] == "audience_rating":
            control_value = sum(ratings[control["material_id"]]) / len(ratings[control["material_id"]])
            assisted_value = sum(ratings[assisted["material_id"]]) / len(ratings[assisted["material_id"]])
            effect = assisted_value - control_value
        else:
            effect = float(control["minutes_to_draft"]) - float(assisted["minutes_to_draft"])
        block_effects[writer].append(effect)

    estimate, distribution = _writer_clustered_effects(
        block_effects,
        seed=int(plan["assignment_seed"]),
        repetitions=int(plan["bootstrap_repetitions"]),
    )
    lower = _percentile(distribution, 0.025)
    upper = _percentile(distribution, 0.975)
    writers = sorted(block_effects)
    premises = sorted({row["premise_id"] for row in materials.values()})
    audiences = sorted({row["audience_id"] for row in data["audience_responses"]})
    venues = sorted({row["venue_id"] for row in data["audience_responses"]})
    ratings_count = len(data["audience_responses"])
    mde = float(plan["minimally_important_difference"])

    gates = {
        "human_observed": plan["data_origin"] == "human_observed",
        "preregistered": bool(plan["preregistered"] and plan["preregistration_uri"]),
        "consent_required": bool(plan["requires_consent"]),
        "held_out_required": bool(plan["requires_held_out_audience"]),
        "minimum_writers": len(writers) >= int(plan["minimum_writers"]),
        "minimum_premises": len(premises) >= int(plan["minimum_premises"]),
        "minimum_audiences": len(audiences) >= int(plan["minimum_audiences"]),
        "minimum_ratings": ratings_count >= int(plan["minimum_ratings"]),
        "lower_interval_exceeds_minimum_effect": lower > mde,
    }
    claim_ready = all(gates.values())
    if plan["data_origin"] == "synthetic_contract_fixture":
        evidence_level = "L1_OFFLINE_CONTRACT"
        allowed_claim = "The deterministic study contract and analyzer executed on synthetic data."
    elif claim_ready and plan["external_replication"]:
        evidence_level = "L4_EXTERNAL_REPLICATION"
        allowed_claim = (
            "The preregistered outcome met its gate in this study marked as an external replication; "
            "the populations, contexts, effect, and interval must remain attached."
        )
    elif claim_ready:
        evidence_level = "L3_PREREGISTERED_HELD_OUT"
        allowed_claim = (
            "For the preregistered population and context, the named primary outcome exceeded the "
            "minimum effect with the reported writer-clustered interval."
        )
    else:
        evidence_level = "L2_HUMAN_PILOT"
        allowed_claim = "Human observations were analyzed as an exploratory pilot; no product advantage is established."

    material_level_ratings = {
        material_id: sum(values) / len(values) for material_id, values in sorted(ratings.items())
    }
    condition_materials: dict[str, list[str]] = defaultdict(list)
    for material_id, row in sorted(materials.items()):
        condition_materials[row["condition"]].append(material_id)
    secondary = {}
    for condition in CONDITIONS:
        ids = condition_materials[condition]
        secondary[condition] = {
            "materials": len(ids),
            "mean_material_rating": sum(material_level_ratings[item] for item in ids) / len(ids),
            "mean_minutes_to_draft": sum(float(materials[item]["minutes_to_draft"]) for item in ids) / len(ids),
            "selection_rate": sum(bool(materials[item]["selected"]) for item in ids) / len(ids),
            "performance_rate": sum(bool(materials[item]["performed"]) for item in ids) / len(ids),
        }
    harm_count = sum(bool(row["harm_or_regret"]) for row in data["audience_responses"])
    receipt = {
        "receipt_type": "humorvibes_real_world_study_analysis",
        "receipt_version": 1,
        "schema_version": SCHEMA_VERSION,
        "study_id": plan["study_id"],
        "data_origin": plan["data_origin"],
        "primary_outcome": plan["primary_outcome"],
        "effect_direction": "assisted_minus_control" if plan["primary_outcome"] == "audience_rating" else "control_minus_assisted_minutes",
        "estimate": estimate,
        "confidence_interval_95": [lower, upper],
        "minimally_important_difference": mde,
        "bootstrap": {
            "method": "percentile writer-cluster bootstrap over writer-level mean paired effects",
            "seed": plan["assignment_seed"],
            "repetitions": plan["bootstrap_repetitions"],
            "independent_unit": "writer",
        },
        "units": {
            "writers": len(writers),
            "paired_writer_premise_blocks": len(by_block),
            "materials": len(materials),
            "audiences": len(audiences),
            "venues": len(venues),
            "ratings": ratings_count,
        },
        "secondary_descriptives": secondary,
        "harm_or_regret": {"count": harm_count, "rate": harm_count / ratings_count},
        "claim_gate": {
            "claim_ready": claim_ready,
            "checks": gates,
            "failed": [name for name, passed in gates.items() if not passed],
        },
        "evidence_level": evidence_level,
        "allowed_claim": allowed_claim,
        "truth_boundary": {
            "synthetic_data_authorizes_human_claim": False,
            "ratings_are_aggregated_before_writer_cluster_bootstrap": True,
            "raw_material_or_identity_accepted": False,
            "universal_funniness_claim_authorized": False,
        },
    }
    receipt["analysis_digest"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return receipt


def synthetic_study_bundle(protocol: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a deterministic, clearly synthetic end-to-end contract fixture."""

    plan = validate_protocol(protocol or default_study_protocol())
    if plan["data_origin"] != "synthetic_contract_fixture":
        raise _error("invalid_synthetic_protocol", "Synthetic fixture requires synthetic_contract_fixture origin.")
    digest = hashlib.sha256(b"humorvibes-synthetic-study-v1").hexdigest()
    materials: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    # Enough rows to exercise repeated ratings and grouping; intentionally below the human protocol gate.
    for writer_number in range(1, 7):
        writer = f"writer-{writer_number:02d}"
        for premise_number in range(1, 3):
            premise = f"{writer}-premise-{premise_number:02d}"
            for condition in CONDITIONS:
                material_id = f"{premise}-{condition}"
                assisted = condition == "assisted"
                materials.append({
                    "material_id": material_id,
                    "writer_id": writer,
                    "premise_id": premise,
                    "condition": condition,
                    "material_version": "v1",
                    "minutes_to_draft": float(42 - (8 if assisted else 0) + premise_number),
                    "selected": assisted or premise_number == 1,
                    "performed": assisted and premise_number == 1,
                    "voice_preservation_rating": 4.0 if assisted else 3.8,
                    "language": "en",
                    "context_version": "synthetic-rehearsal-v1",
                    "model_config_digest": digest,
                    "permission_confirmed": True,
                })
                for audience_number in range(1, 9):
                    base = 3.0 + ((writer_number + premise_number + audience_number) % 3 - 1) * 0.1
                    rating = base + (0.45 if assisted else 0.0)
                    responses.append({
                        "response_id": f"response-{material_id}-{audience_number:02d}",
                        "material_id": material_id,
                        "audience_id": f"audience-{audience_number:02d}",
                        "venue_id": f"venue-{1 + audience_number % 2}",
                        "rating": round(rating, 2),
                        "laughed": rating >= 3.3,
                        "harm_or_regret": False,
                        "consent_confirmed": True,
                        "held_out": True,
                        "recorded_at": f"2026-07-{1 + premise_number:02d}T{audience_number:02d}:00:00Z",
                    })
    return {
        "schema_version": SCHEMA_VERSION,
        "study_id": plan["study_id"],
        "data_origin": plan["data_origin"],
        "collection_window": {
            "opened_at": "2026-07-01T00:00:00Z",
            "closed_at": "2026-07-31T23:59:59Z",
        },
        "assignment_digest": digest,
        "source_snapshot_digest": hashlib.sha256(b"synthetic-no-source-corpus").hexdigest(),
        "materials": materials,
        "audience_responses": responses,
    }


def synthetic_demo_receipt() -> dict[str, Any]:
    protocol = default_study_protocol()
    return analyze_study(protocol, synthetic_study_bundle(protocol))

