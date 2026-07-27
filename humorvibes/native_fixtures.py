"""Fail-closed contract for one-language, human-reviewed humor-form fixtures."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .errors import IntegrationError


SCHEMA_VERSION = "1.0"
MINIMUM_PER_ARM = 20
TOP_LEVEL_FIELDS = {
    "schema_version",
    "language",
    "locale",
    "form_id",
    "rule_pattern",
    "rule_note",
    "source_snapshot",
    "review",
    "fixtures",
    "coverage",
    "aligned_pair_consistency",
}
SOURCE_FIELDS = {
    "source_url",
    "source_revision",
    "retrieved_at",
    "license_id",
    "license_evidence_url",
    "redistribution_permission_confirmed",
    "source_digest",
}
REVIEW_FIELDS = {
    "status",
    "reviewer_id",
    "fluency_basis",
    "conflicts",
    "reviewed_at",
    "machine_translation_used_for_acceptance",
    "consent_to_publish_attestation",
}
FIXTURE_FIELDS = {
    "fixture_id",
    "text",
    "expected_match",
    "rationale",
    "source_ref",
    "permission_confirmed",
}
COVERAGE_FIELDS = {
    "corpus_rows",
    "matches_before",
    "matches_after",
    "reviewed_match_sample",
    "false_positives_in_sample",
    "corpus_digest",
}
ALIGNMENT_FIELDS = {"applicable", "pairs_reviewed", "mechanism_consistent", "notes"}
REDISTRIBUTABLE_LICENSE_IDS = {
    "CC0-1.0",
    "CC-BY-2.0",
    "CC-BY-3.0",
    "CC-BY-4.0",
    "CC-BY-SA-3.0",
    "CC-BY-SA-4.0",
    "Apache-2.0",
    "MIT",
    "Public-Domain",
}
FORBIDDEN_IDENTITY_KEYS = {
    "name",
    "email",
    "phone",
    "address",
    "ip",
    "ip_address",
    "social_handle",
    "employer",
}


def _error(code: str, message: str, *, detail: dict[str, Any] | None = None) -> IntegrationError:
    return IntegrationError(code, message, 422, detail=detail)


def _strict(value: Any, expected: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise _error("invalid_native_fixture_schema", f"{location} must be an object.")
    keys = set(value)
    if keys != expected:
        raise _error(
            "invalid_native_fixture_schema",
            f"{location} fields do not match the schema.",
            detail={"missing": sorted(expected - keys), "unknown": sorted(keys - expected)},
        )
    return dict(value)


def _string(value: Any, location: str, *, minimum: int = 1, maximum: int = 2_000) -> str:
    if not isinstance(value, str):
        raise _error("invalid_native_fixture_value", f"{location} must be a string.")
    rendered = value.strip()
    if not minimum <= len(rendered) <= maximum:
        raise _error(
            "invalid_native_fixture_value",
            f"{location} must contain {minimum} through {maximum} characters.",
        )
    return rendered


def _integer(value: Any, location: str, *, minimum: int = 0, maximum: int = 100_000_000) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _error(
            "invalid_native_fixture_value",
            f"{location} must be an integer from {minimum} through {maximum}.",
        )
    return value


def _boolean(value: Any, location: str) -> bool:
    if type(value) is not bool:
        raise _error("invalid_native_fixture_value", f"{location} must be boolean.")
    return value


def _sha256(value: Any, location: str) -> str:
    rendered = _string(value, location, minimum=64, maximum=64).lower()
    if re.fullmatch(r"[0-9a-f]{64}", rendered) is None:
        raise _error("invalid_native_fixture_value", f"{location} must be lowercase SHA-256.")
    return rendered


def _iso_date(value: Any, location: str) -> str:
    rendered = _string(value, location, minimum=10, maximum=10)
    try:
        date.fromisoformat(rendered)
    except ValueError as exc:
        raise _error("invalid_native_fixture_value", f"{location} must be YYYY-MM-DD.") from exc
    return rendered


def _scan_identity_keys(value: Any, location: str = "bundle") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_IDENTITY_KEYS:
                raise _error(
                    "native_review_identity_forbidden",
                    "Native-review bundles accept a reviewer pseudonym, not direct identity fields.",
                    detail={"location": f"{location}.{key}"},
                )
            _scan_identity_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_identity_keys(child, f"{location}[{index}]")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def validate_native_fixture_bundle(value: Any) -> dict[str, Any]:
    """Validate one language/form contribution and return a body-free receipt."""

    _scan_identity_keys(value)
    root = _strict(value, TOP_LEVEL_FIELDS, "bundle")
    if root["schema_version"] != SCHEMA_VERSION:
        raise _error("unsupported_native_fixture_schema", "Unsupported native fixture schema.")
    language = _string(root["language"], "bundle.language", minimum=2, maximum=12).casefold()
    if re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})?", language) is None:
        raise _error("invalid_native_language", "Language must be an ISO-like language code.")
    locale = _string(root["locale"], "bundle.locale", minimum=2, maximum=24)
    form_id = _string(root["form_id"], "bundle.form_id", minimum=3, maximum=80)
    if re.fullmatch(r"[a-z][a-z0-9_]+", form_id) is None:
        raise _error("invalid_native_form_id", "Form ID must use lowercase snake_case.")
    rule_pattern = _string(root["rule_pattern"], "bundle.rule_pattern", maximum=1_000)
    rule_note = _string(root["rule_note"], "bundle.rule_note", minimum=20, maximum=1_000)
    try:
        rule = re.compile(rule_pattern, re.IGNORECASE)
    except re.error as exc:
        raise _error(
            "invalid_native_rule_pattern", "Native form rule is not a valid Python regex."
        ) from exc

    source = _strict(root["source_snapshot"], SOURCE_FIELDS, "bundle.source_snapshot")
    for field in ("source_url", "license_evidence_url"):
        url = _string(source[field], f"bundle.source_snapshot.{field}", maximum=1_000)
        if not url.startswith("https://"):
            raise _error("invalid_native_source_url", f"{field} must be an HTTPS URL.")
    _string(source["source_revision"], "bundle.source_snapshot.source_revision", maximum=200)
    _iso_date(source["retrieved_at"], "bundle.source_snapshot.retrieved_at")
    license_id = _string(source["license_id"], "bundle.source_snapshot.license_id", maximum=80)
    if license_id not in REDISTRIBUTABLE_LICENSE_IDS:
        raise _error(
            "native_fixture_not_redistributable",
            "Committed native fixtures require an explicitly allowlisted redistributable license ID.",
            detail={"license_id": license_id},
        )
    if not _boolean(
        source["redistribution_permission_confirmed"],
        "bundle.source_snapshot.redistribution_permission_confirmed",
    ):
        raise _error(
            "native_fixture_permission_missing", "Fixture redistribution permission must be confirmed."
        )
    source_digest = _sha256(source["source_digest"], "bundle.source_snapshot.source_digest")

    review = _strict(root["review"], REVIEW_FIELDS, "bundle.review")
    if review["status"] != "human_reviewed":
        raise _error(
            "native_human_review_missing", "Review status must be exactly human_reviewed."
        )
    reviewer_id = _string(review["reviewer_id"], "bundle.review.reviewer_id", minimum=8, maximum=80)
    if re.fullmatch(r"reviewer-[a-z0-9][a-z0-9-]+", reviewer_id) is None:
        raise _error(
            "invalid_native_reviewer_pseudonym", "Reviewer ID must be a reviewer- pseudonym."
        )
    _string(review["fluency_basis"], "bundle.review.fluency_basis", minimum=20, maximum=1_000)
    _string(review["conflicts"], "bundle.review.conflicts", minimum=4, maximum=1_000)
    _iso_date(review["reviewed_at"], "bundle.review.reviewed_at")
    if _boolean(
        review["machine_translation_used_for_acceptance"],
        "bundle.review.machine_translation_used_for_acceptance",
    ):
        raise _error(
            "machine_translation_cannot_accept_native_fixture",
            "Machine translation cannot be the acceptance reviewer.",
        )
    if not _boolean(
        review["consent_to_publish_attestation"],
        "bundle.review.consent_to_publish_attestation",
    ):
        raise _error(
            "native_review_attestation_permission_missing",
            "Reviewer must consent to publishing the pseudonymous attestation.",
        )

    if not isinstance(root["fixtures"], list):
        raise _error("invalid_native_fixture_schema", "bundle.fixtures must be an array.")
    positives = negatives = 0
    fixture_ids: set[str] = set()
    fixture_texts: set[str] = set()
    normalized_fixtures: list[dict[str, Any]] = []
    for index, value_row in enumerate(root["fixtures"]):
        location = f"bundle.fixtures[{index}]"
        row = _strict(value_row, FIXTURE_FIELDS, location)
        fixture_id = _string(row["fixture_id"], f"{location}.fixture_id", maximum=100)
        if fixture_id in fixture_ids:
            raise _error("duplicate_native_fixture_id", "Fixture IDs must be unique.")
        fixture_ids.add(fixture_id)
        text = _string(row["text"], f"{location}.text", minimum=3, maximum=2_000)
        text_key = text.casefold()
        if text_key in fixture_texts:
            raise _error("duplicate_native_fixture_text", "Fixture text must be unique.")
        fixture_texts.add(text_key)
        expected = _boolean(row["expected_match"], f"{location}.expected_match")
        observed = bool(rule.search(text))
        if observed != expected:
            raise _error(
                "native_fixture_rule_mismatch",
                "A fixture does not produce its human-reviewed expected rule result.",
                detail={"fixture_id": fixture_id, "expected": expected, "observed": observed},
            )
        _string(row["rationale"], f"{location}.rationale", minimum=12, maximum=1_000)
        _string(row["source_ref"], f"{location}.source_ref", maximum=300)
        if not _boolean(row["permission_confirmed"], f"{location}.permission_confirmed"):
            raise _error("native_fixture_permission_missing", "Every fixture needs permission.")
        positives += int(expected)
        negatives += int(not expected)
        normalized_fixtures.append(row)
    if positives < MINIMUM_PER_ARM or negatives < MINIMUM_PER_ARM:
        raise _error(
            "native_fixture_arm_too_small",
            "Each language PR requires at least 20 positive and 20 hard-negative fixtures.",
            detail={"positives": positives, "negatives": negatives},
        )

    coverage = _strict(root["coverage"], COVERAGE_FIELDS, "bundle.coverage")
    corpus_rows = _integer(coverage["corpus_rows"], "bundle.coverage.corpus_rows", minimum=1)
    before = _integer(coverage["matches_before"], "bundle.coverage.matches_before")
    after = _integer(coverage["matches_after"], "bundle.coverage.matches_after")
    reviewed_sample = _integer(
        coverage["reviewed_match_sample"], "bundle.coverage.reviewed_match_sample"
    )
    false_positives = _integer(
        coverage["false_positives_in_sample"], "bundle.coverage.false_positives_in_sample"
    )
    if before > corpus_rows or after > corpus_rows or reviewed_sample > after:
        raise _error("invalid_native_coverage", "Coverage counts are internally inconsistent.")
    if reviewed_sample < min(20, after):
        raise _error(
            "native_false_positive_review_too_small",
            "Manually review at least 20 matches, or every match when fewer than 20 exist.",
        )
    if false_positives > reviewed_sample:
        raise _error("invalid_native_coverage", "False positives cannot exceed the reviewed sample.")
    corpus_digest = _sha256(coverage["corpus_digest"], "bundle.coverage.corpus_digest")

    alignment = _strict(
        root["aligned_pair_consistency"], ALIGNMENT_FIELDS, "bundle.aligned_pair_consistency"
    )
    applicable = _boolean(alignment["applicable"], "bundle.aligned_pair_consistency.applicable")
    pairs_reviewed = _integer(
        alignment["pairs_reviewed"], "bundle.aligned_pair_consistency.pairs_reviewed"
    )
    consistent = _integer(
        alignment["mechanism_consistent"],
        "bundle.aligned_pair_consistency.mechanism_consistent",
    )
    _string(alignment["notes"], "bundle.aligned_pair_consistency.notes", minimum=8, maximum=1_000)
    if consistent > pairs_reviewed or (applicable and pairs_reviewed < 1):
        raise _error("invalid_native_alignment_review", "Aligned-pair review counts are inconsistent.")
    if not applicable and (pairs_reviewed or consistent):
        raise _error(
            "invalid_native_alignment_review", "Non-applicable alignment review must use zero counts."
        )

    false_positive_rate = false_positives / reviewed_sample if reviewed_sample else math.nan
    receipt = {
        "receipt_type": "humorvibes_native_fixture_review",
        "receipt_version": 1,
        "schema_version": SCHEMA_VERSION,
        "language": language,
        "locale": locale,
        "form_id": form_id,
        "rule_pattern_sha256": hashlib.sha256(rule_pattern.encode("utf-8")).hexdigest(),
        "rule_note_sha256": hashlib.sha256(rule_note.encode("utf-8")).hexdigest(),
        "fixtures": {
            "positives": positives,
            "hard_negatives": negatives,
            "fixture_digest": _digest(normalized_fixtures),
            "raw_text_in_receipt": False,
        },
        "source": {
            "license_id": license_id,
            "source_digest": source_digest,
            "redistribution_permission_confirmed": True,
        },
        "review": {
            "status": "human_reviewed",
            "reviewer_id": reviewer_id,
            "fluency_basis_recorded": True,
            "conflicts_recorded": True,
            "machine_translation_accepted_the_fixture": False,
            "attestation_publication_consented": True,
        },
        "coverage": {
            "corpus_rows": corpus_rows,
            "matches_before": before,
            "matches_after": after,
            "reviewed_match_sample": reviewed_sample,
            "false_positives_in_sample": false_positives,
            "sample_false_positive_rate": false_positive_rate,
            "corpus_digest": corpus_digest,
        },
        "aligned_pair_consistency": {
            "applicable": applicable,
            "pairs_reviewed": pairs_reviewed,
            "mechanism_consistent": consistent,
        },
        "claim_gate": {
            "fixture_ready_for_taxonomy_pr": True,
            "one_language": True,
            "human_review_attestation_present": True,
        },
        "truth_boundary": {
            "attestation_identity_independently_verified": False,
            "fixture_review_is_human_funniness_evidence": False,
            "machine_translation_or_model_is_native_review": False,
            "rule_generalizes_beyond_reviewed_source_snapshot": False,
        },
    }
    receipt["review_digest"] = _digest(receipt)
    return receipt


def validate_native_fixture_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("invalid_native_fixture_file", "Native fixture file is not readable UTF-8 JSON.") from exc
    return validate_native_fixture_bundle(value)


def write_native_fixture_receipt(path: Path, receipt: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
