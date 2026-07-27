"""Prospective planning and deterministic launch artifacts for the writer study.

The module prepares a privacy-minimized operational pack. It does not recruit people,
obtain ethics approval, register a protocol, collect observations, or authorize a claim.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import math
import os
import random
import secrets
import stat
from pathlib import Path
from statistics import NormalDist
from typing import Any

from .errors import IntegrationError
from .studies import validate_protocol


def _error(code: str, message: str) -> IntegrationError:
    return IntegrationError(code, message, 422)


def _bounded_number(
    value: float,
    name: str,
    *,
    minimum: float,
    maximum: float,
    inclusive_minimum: bool = True,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error("invalid_launch_assumption", f"{name} must be numeric.")
    rendered = float(value)
    valid_minimum = rendered >= minimum if inclusive_minimum else rendered > minimum
    if not math.isfinite(rendered) or not valid_minimum or rendered > maximum:
        qualifier = "at least" if inclusive_minimum else "greater than"
        raise _error(
            "invalid_launch_assumption",
            f"{name} must be finite, {qualifier} {minimum}, and at most {maximum}.",
        )
    return rendered


def _bounded_integer(value: int, name: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _error(
            "invalid_launch_assumption",
            f"{name} must be an integer from {minimum} through {maximum}.",
        )
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def prospective_precision_plan(
    *,
    target_effect: float = 0.25,
    between_writer_sd: float = 0.45,
    within_writer_premise_sd: float = 0.60,
    premises_per_writer: int = 2,
    alpha: float = 0.05,
    power: float = 0.80,
    writer_attrition_rate: float = 0.15,
    minimum_writers: int = 12,
) -> dict[str, Any]:
    """Plan a two-sided paired writer-level test under declared assumptions.

    The approximation treats each writer's mean paired effect as independent. Between-writer
    variation remains after premise averaging; within-writer premise variation shrinks with the
    declared number of paired premises. The result is a planning calculation, not observed power.
    """

    effect = _bounded_number(target_effect, "target_effect", minimum=0.0, maximum=4.0, inclusive_minimum=False)
    between_sd = _bounded_number(
        between_writer_sd, "between_writer_sd", minimum=0.0, maximum=10.0
    )
    within_sd = _bounded_number(
        within_writer_premise_sd, "within_writer_premise_sd", minimum=0.0, maximum=10.0
    )
    premises = _bounded_integer(premises_per_writer, "premises_per_writer", minimum=1, maximum=100)
    alpha_value = _bounded_number(alpha, "alpha", minimum=0.0, maximum=0.25, inclusive_minimum=False)
    power_value = _bounded_number(power, "power", minimum=0.50, maximum=0.999)
    attrition = _bounded_number(writer_attrition_rate, "writer_attrition_rate", minimum=0.0, maximum=0.75)
    minimum = _bounded_integer(minimum_writers, "minimum_writers", minimum=2, maximum=100_000)

    writer_mean_sd = math.sqrt(between_sd**2 + within_sd**2 / premises)
    if writer_mean_sd == 0:
        raise _error("invalid_launch_assumption", "At least one variance assumption must be positive.")
    z_alpha = NormalDist().inv_cdf(1.0 - alpha_value / 2.0)
    z_power = NormalDist().inv_cdf(power_value)
    calculated = math.ceil(((z_alpha + z_power) * writer_mean_sd / effect) ** 2)
    analyzable = max(minimum, calculated)
    recruit = math.ceil(analyzable / (1.0 - attrition))
    half_width = z_alpha * writer_mean_sd / math.sqrt(analyzable)
    result = {
        "receipt_type": "humorvibes_prospective_precision_plan",
        "receipt_version": 1,
        "method": "normal approximation over independent writer-level mean paired effects",
        "design": {
            "two_sided_alpha": alpha_value,
            "target_power": power_value,
            "target_effect": effect,
            "premises_per_writer": premises,
            "independent_unit": "writer",
        },
        "variance_assumptions": {
            "between_writer_sd": between_sd,
            "within_writer_premise_sd": within_sd,
            "derived_writer_mean_effect_sd": writer_mean_sd,
        },
        "attrition_assumption": {"writer_attrition_rate": attrition},
        "planned_counts": {
            "calculated_analyzable_writers": calculated,
            "minimum_analyzable_writers": analyzable,
            "writers_to_recruit": recruit,
            "paired_premises_per_analyzable_writer": premises,
            "paired_blocks_at_minimum": analyzable * premises,
        },
        "expected_95_percent_half_width_at_minimum": half_width,
        "truth_boundary": {
            "prospective_not_observed_power": True,
            "assumptions_require_domain_review": True,
            "hierarchical_simulation_still_recommended": True,
            "authorizes_human_claim": False,
        },
    }
    result["plan_digest"] = _digest(result)
    return result


def create_assignment_key(path: Path) -> dict[str, Any]:
    """Create a randomization key without printing or embedding the secret in a pack."""

    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise _error("assignment_key_exists", "Refusing to replace an existing assignment key.") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(key + "\n")
    return {
        "receipt_type": "humorvibes_assignment_key_created",
        "path": str(path),
        "key_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
        "secret_printed": False,
        "posix_permissions": "0600",
    }


def read_assignment_key(path: Path) -> str:
    """Read a bounded private key and reject permissive POSIX file modes."""

    if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise _error(
            "assignment_key_permissions",
            "Assignment key must not be readable or writable by group or other users.",
        )
    key = path.read_text(encoding="utf-8").strip()
    if not 32 <= len(key) <= 256:
        raise _error("invalid_assignment_key", "Assignment key must contain 32 to 256 characters.")
    return key


def deterministic_randomization(
    *, writer_count: int, premises_per_writer: int, seed: int, assignment_key: str
) -> dict[str, Any]:
    """Create balanced crossover and blinded audience schedules from pseudonyms only."""

    writers = _bounded_integer(writer_count, "writer_count", minimum=2, maximum=100_000)
    premises = _bounded_integer(premises_per_writer, "premises_per_writer", minimum=1, maximum=100)
    seed_value = _bounded_integer(seed, "seed", minimum=0, maximum=2**31 - 1)
    if not isinstance(assignment_key, str) or not 32 <= len(assignment_key) <= 256:
        raise _error("invalid_assignment_key", "Assignment key must contain 32 to 256 characters.")
    key_bytes = assignment_key.encode("utf-8")
    key_digest = hashlib.sha256(key_bytes).hexdigest()
    block_count = writers * premises
    private_seed = int.from_bytes(
        hmac.new(key_bytes, f"randomization|{seed_value}".encode("utf-8"), hashlib.sha256).digest()[:16],
        "big",
    )
    rng = random.Random(private_seed)
    writing_sequences = ["control_then_assisted", "assisted_then_control"] * math.ceil(block_count / 2)
    panel_conditions = ["control", "assisted"] * math.ceil(block_count / 2)
    rng.shuffle(writing_sequences)
    rng.shuffle(panel_conditions)

    restricted: list[dict[str, Any]] = []
    blinded_writing: list[dict[str, Any]] = []
    blinded_audience: list[dict[str, Any]] = []
    block_number = 0
    for writer_number in range(1, writers + 1):
        for premise_number in range(1, premises + 1):
            block_number += 1
            writer_id = f"writer-{writer_number:04d}"
            premise_id = f"{writer_id}-premise-{premise_number:02d}"
            block_id = f"block-{block_number:06d}"
            blind_ids = {
                condition: "material-"
                + hmac.new(
                    key_bytes,
                    f"blind-id|{seed_value}|{block_id}|{condition}".encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()[:16]
                for condition in ("control", "assisted")
            }
            sequence = writing_sequences[block_number - 1]
            first_condition = "control" if sequence == "control_then_assisted" else "assisted"
            second_condition = "assisted" if first_condition == "control" else "control"
            panel_one_condition = panel_conditions[block_number - 1]
            panel_two_condition = "assisted" if panel_one_condition == "control" else "control"
            restricted.append(
                {
                    "block_id": block_id,
                    "writer_id": writer_id,
                    "premise_id": premise_id,
                    "writing_sequence": sequence,
                    "session_1_condition": first_condition,
                    "session_2_condition": second_condition,
                    "control_blind_material_id": blind_ids["control"],
                    "assisted_blind_material_id": blind_ids["assisted"],
                    "audience_panel_01_condition": panel_one_condition,
                    "audience_panel_02_condition": panel_two_condition,
                }
            )
            blinded_writing.append(
                {
                    "block_id": block_id,
                    "writer_id": writer_id,
                    "premise_id": premise_id,
                    "session_1_material_id": blind_ids[first_condition],
                    "session_2_material_id": blind_ids[second_condition],
                }
            )
            blinded_audience.extend(
                [
                    {
                        "block_id": block_id,
                        "audience_panel_id": "audience-panel-01",
                        "blind_material_id": blind_ids[panel_one_condition],
                    },
                    {
                        "block_id": block_id,
                        "audience_panel_id": "audience-panel-02",
                        "blind_material_id": blind_ids[panel_two_condition],
                    },
                ]
            )

    result = {
        "receipt_type": "humorvibes_study_randomization",
        "receipt_version": 1,
        "seed": seed_value,
        "assignment_key_sha256": key_digest,
        "counts": {"writers": writers, "premises_per_writer": premises, "blocks": block_count},
        "restricted_assignment_map": restricted,
        "blinded_writing_schedule": blinded_writing,
        "blinded_audience_schedule": blinded_audience,
        "balance": {
            "control_first_blocks": sum(row["session_1_condition"] == "control" for row in restricted),
            "assisted_first_blocks": sum(row["session_1_condition"] == "assisted" for row in restricted),
            "panel_01_control_blocks": sum(
                row["audience_panel_01_condition"] == "control" for row in restricted
            ),
            "panel_01_assisted_blocks": sum(
                row["audience_panel_01_condition"] == "assisted" for row in restricted
            ),
        },
        "operational_boundary": {
            "identities_present": False,
            "condition_mapping_is_restricted": True,
            "one_panel_sees_both_versions_of_a_block": False,
        },
    }
    result["assignment_digest"] = _digest(restricted)
    result["blinded_schedule_digest"] = _digest(
        {"writing": blinded_writing, "audience": blinded_audience}
    )
    return result


def _preregistration_markdown(protocol: dict[str, Any], precision: dict[str, Any], receipt: dict[str, Any]) -> str:
    counts = precision["planned_counts"]
    variance = precision["variance_assumptions"]
    return f"""# Preregistration draft: {protocol['title']}

Status: **not registered**. This complete draft must be submitted to a timestamped registry and
approved through the applicable ethics process before observations begin. Its protocol digest is
`{receipt['protocol_digest']}`.

## Research question and comparison

For {protocol['target_population']}, compare HumorVibes-assisted and control material within the
same writer and paired premise. The single primary outcome is `{protocol['primary_outcome']}`;
positive effects follow the direction declared in the frozen analyzer.

## Primary hypothesis and useful-effect threshold

The confirmatory alternative is that the writer-clustered assisted-minus-control effect on the
primary outcome exceeds {protocol['minimally_important_difference']}. The rating scale is
{protocol['rating_scale_min']} to {protocol['rating_scale_max']}. All other outcomes are secondary.

## Design, randomization, and blinding

This is a paired within-writer crossover. Each analyzable writer contributes
{counts['paired_premises_per_analyzable_writer']} paired premises. Assignment uses seed
    {protocol['assignment_seed']} plus a separately stored private key committed by SHA-256;
condition mappings live only in the restricted map. Audience panel
members receive one version of each writer-premise block, never both, through blind material IDs.

## Prospective planning assumptions

- Two-sided alpha: {precision['design']['two_sided_alpha']}
- Target power: {precision['design']['target_power']}
- Target effect: {precision['design']['target_effect']}
- Between-writer SD: {variance['between_writer_sd']}
- Within-writer premise SD: {variance['within_writer_premise_sd']}
- Analyzable writers: {counts['minimum_analyzable_writers']}
- Writers to recruit after declared attrition: {counts['writers_to_recruit']}
- Minimum paired writer-premise blocks: {counts['paired_blocks_at_minimum']}

These are prospective assumptions, not observed power. A hierarchical simulation sensitivity
analysis should accompany institutional review before recruitment.

## Inclusion, exclusion, and stopping

Include only permission-confirmed material and consent-confirmed, held-out audience responses that
validate against schema {protocol['schema_version']}. Exclude malformed records, incomplete paired
blocks, non-finite or out-of-range outcomes, duplicate IDs, unconsented responses, and material
without a rating. Stop after the frozen minimum counts and collection window are met; do not inspect
condition effects to choose the stopping point. Report exclusions by machine-readable reason.

## Analysis

{protocol['analysis_plan']} Use {protocol['bootstrap_repetitions']} bootstrap repetitions and seed
{protocol['assignment_seed']}. Report the point estimate, 95% interval, minimum useful effect,
sample units, secondary descriptives, harm/regret outcomes, and every failed claim gate.

## Privacy, consent, and retention

{protocol['retention_policy']} Raw material, prompts, direct identity, contact information,
protected-trait inference, and linkage tables remain outside the analysis export. Withdrawal and
deletion requests are resolved against the separate linkage store by the authorized study team.

## Deviations and reporting

Publish all deviations as dated amendments before the affected analysis when possible. Label any
analysis changed after outcome inspection as exploratory. A passing gate authorizes only a bounded
claim about the named population, context, outcome, comparison, effect, and interval; it never
authorizes a universal claim that material is funny.
"""


def _operations_markdown(receipt: dict[str, Any]) -> str:
    return f"""# Human-study launch operations

This pack is technically complete and reproducible. It is not institutional approval, legal
advice, consent, recruitment, or collected evidence. Current launch status:
`{receipt['status']}`.

## Required external gates before recruitment

- Obtain and archive the applicable ethics/IRB determination.
- Submit the preregistration draft and record its permanent HTTPS URI in the frozen protocol.
- Have the responsible institution approve accessible consent, withdrawal, compensation,
  complaint, adverse-event, and early-stop procedures.
- Assign named data-controller roles outside this public analysis pack.
- Put the identity-to-pseudonym linkage table in a separately access-controlled store.
- Confirm encryption, least-privilege access, retention timers, backups, and deletion tests.
- Pilot the blinded presentation flow without recording outcome-bearing human observations.

## Separation of duties

The facilitator may access the restricted condition map but must not rate outcomes. Writers receive
only their scheduled session instructions. Audience facilitators use the blinded audience schedule
and never the condition mapping. The analyst receives only the privacy-minimized bundle after the
collection window closes.

## Withdrawal and incident handling

The authorized study team resolves a withdrawal pseudonym through the separate linkage store,
deletes eligible source and export records, records the deletion event without direct identity, and
reruns validation. Pause collection after a consent failure, mapping disclosure, unauthorized
access, or material harm signal until the responsible reviewer documents a disposition.

## Pre-analysis integrity checks

Verify the protocol digest `{receipt['protocol_digest']}`, assignment digest
`{receipt['assignment_digest']}`, and blinded schedule digest
`{receipt['blinded_schedule_digest']}`. Confirm the analyst remained blinded, the stopping rule was
not outcome-driven, all deviations are published, and the analysis bundle contains no forbidden
fields.
"""


def build_launch_pack(
    protocol: dict[str, Any],
    *,
    assignment_key: str,
    target_effect: float | None = None,
    between_writer_sd: float = 0.45,
    within_writer_premise_sd: float = 0.60,
    premises_per_writer: int = 2,
    alpha: float = 0.05,
    power: float = 0.80,
    writer_attrition_rate: float = 0.15,
) -> dict[str, Any]:
    """Build a deterministic, non-claim-ready precollection pack in memory."""

    plan = validate_protocol(protocol)
    if plan["data_origin"] != "human_observed":
        raise _error("launch_requires_human_protocol", "Study launch requires a human_observed protocol.")
    precision = prospective_precision_plan(
        target_effect=float(
            target_effect if target_effect is not None else plan["minimally_important_difference"]
        ),
        between_writer_sd=between_writer_sd,
        within_writer_premise_sd=within_writer_premise_sd,
        premises_per_writer=premises_per_writer,
        alpha=alpha,
        power=power,
        writer_attrition_rate=writer_attrition_rate,
        minimum_writers=int(plan["minimum_writers"]),
    )
    counts = precision["planned_counts"]
    frozen = copy.deepcopy(plan)
    required_writers = int(counts["minimum_analyzable_writers"])
    required_premises = int(counts["paired_blocks_at_minimum"])
    if plan["preregistered"]:
        compatible = (
            int(plan["minimum_writers"]) >= required_writers
            and int(plan["minimum_premises"]) >= required_premises
        )
    else:
        frozen["minimum_writers"] = required_writers
        frozen["minimum_premises"] = required_premises
        compatible = True
    frozen = validate_protocol(frozen)
    randomization = deterministic_randomization(
        writer_count=int(counts["writers_to_recruit"]),
        premises_per_writer=premises_per_writer,
        seed=int(frozen["assignment_seed"]),
        assignment_key=assignment_key,
    )
    receipt = {
        "receipt_type": "humorvibes_human_study_launch_pack",
        "receipt_version": 1,
        "status": (
            "AWAITING_ETHICS_AND_OPERATIONAL_APPROVAL"
            if frozen["preregistered"]
            else "READY_FOR_EXTERNAL_ETHICS_AND_REGISTRATION"
        ),
        "study_id": frozen["study_id"],
        "protocol_digest": _digest(frozen),
        "precision_plan_digest": precision["plan_digest"],
        "assignment_digest": randomization["assignment_digest"],
        "blinded_schedule_digest": randomization["blinded_schedule_digest"],
        "assignment_key_sha256": randomization["assignment_key_sha256"],
        "protocol_minimums_compatible_with_precision_plan": compatible,
        "external_gates": {
            "ethics_or_irb_determination_archived": False,
            "preregistration_recorded": bool(frozen["preregistered"]),
            "institutional_consent_operations_approved": False,
            "secure_linkage_store_verified": False,
            "recruitment_completed": False,
            "observations_collected": False,
        },
        "claim_gate": {
            "claim_ready": False,
            "reason": "This is a prospective launch pack with no human observations.",
        },
        "truth_boundary": {
            "synthetic_or_planned_counts_are_observed_people": False,
            "technical_readiness_is_ethics_approval": False,
            "registration_or_recruitment_performed": False,
            "authorizes_product_advantage_claim": False,
        },
    }
    receipt["pack_digest"] = _digest(receipt)
    return {
        "protocol": frozen,
        "precision_plan": precision,
        "randomization": randomization,
        "launch_receipt": receipt,
        "preregistration_markdown": _preregistration_markdown(frozen, precision, receipt),
        "operations_markdown": _operations_markdown(receipt),
    }


def write_launch_pack(output_directory: Path, pack: dict[str, Any], *, overwrite: bool = False) -> dict[str, Any]:
    """Write separated blinded/restricted artifacts and return the launch receipt."""

    targets = {
        "protocol.json": pack["protocol"],
        "precision_plan.json": pack["precision_plan"],
        "restricted_assignment_map.json": {
            "warning": "RESTRICT ACCESS; condition mapping must stay hidden from raters and analysts",
            "assignment_digest": pack["randomization"]["assignment_digest"],
            "rows": pack["randomization"]["restricted_assignment_map"],
        },
        "blinded_writing_schedule.json": {
            "blinded_schedule_digest": pack["randomization"]["blinded_schedule_digest"],
            "rows": pack["randomization"]["blinded_writing_schedule"],
        },
        "blinded_audience_schedule.json": {
            "blinded_schedule_digest": pack["randomization"]["blinded_schedule_digest"],
            "rows": pack["randomization"]["blinded_audience_schedule"],
        },
        "launch_receipt.json": pack["launch_receipt"],
        "PREREGISTRATION_DRAFT.md": pack["preregistration_markdown"],
        "OPERATIONS.md": pack["operations_markdown"],
    }
    existing = sorted(name for name in targets if (output_directory / name).exists())
    if existing and not overwrite:
        raise _error(
            "launch_pack_exists",
            "Refusing to overwrite an existing launch pack; pass overwrite=True intentionally.",
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    for name, value in targets.items():
        target = output_directory / name
        if isinstance(value, str):
            target.write_text(value.rstrip() + "\n", encoding="utf-8")
        else:
            target.write_text(
                json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    return pack["launch_receipt"]
