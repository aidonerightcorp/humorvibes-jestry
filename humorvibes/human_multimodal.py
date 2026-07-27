"""Fail-closed intake and evaluation for human-observed multimodal humor data.

This module deliberately separates machine-checkable consistency from facts that
software cannot establish: consent, human authorship, and legal rights.  A passing
receipt means the declared evidence is complete and internally consistent.  It is
not legal advice and it does not independently authenticate the declarations.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .errors import IntegrationError
from .multimodal_benchmark import (
    ARM_NAMES,
    _calibration,
    _canonical_digest,
    _metrics,
    _predict,
    _slices,
    _solve_linear,
)


SCHEMA_VERSION = 1
MANIFEST_NAME = "human_multimodal_manifest.json"
CAPTIONS_NAME = "caption_candidates.jsonl"
RIGHTS_NAME = "rights_ledger.jsonl"
SPLITS = {"train", "validation", "test"}
RIGHTS_BASES = {"spdx_license", "public_domain", "creator_permission"}
DISALLOWED_LICENSES = {"", "NOASSERTION", "NONE", "UNKNOWN", "UNLICENSED"}
DIRECT_IDENTITY_FIELDS = {
    "email",
    "full_name",
    "legal_name",
    "participant_id",
    "phone",
    "postal_address",
    "username",
}


def _error(code: str, message: str, *, detail: dict[str, Any] | None = None) -> IntegrationError:
    return IntegrationError(code, message, 422, detail=detail)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _error("missing_human_multimodal_file", f"Missing required file: {path.name}.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("invalid_human_multimodal_json", f"Invalid JSON in {path.name}.") from exc
    if not isinstance(value, dict):
        raise _error("invalid_human_multimodal_json", f"{path.name} must contain one JSON object.")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise _error(
                        "invalid_human_multimodal_jsonl",
                        f"Malformed JSON on line {line_number} of {path.name}.",
                    ) from exc
                if not isinstance(value, dict):
                    raise _error(
                        "invalid_human_multimodal_row",
                        f"Line {line_number} of {path.name} must be an object.",
                    )
                rows.append(value)
    except FileNotFoundError as exc:
        raise _error("missing_human_multimodal_file", f"Missing required file: {path.name}.") from exc
    except UnicodeDecodeError as exc:
        raise _error("invalid_human_multimodal_jsonl", f"{path.name} is not valid UTF-8.") from exc
    return rows


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_file(root: Path, relative: Any, *, code: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise _error(code, "Evidence paths must be non-empty relative paths.")
    root_resolved = root.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root_resolved) or not candidate.is_file():
        raise _error(code, "Evidence paths must resolve to files inside the bundle.")
    return candidate


def _verify_file_digest(root: Path, record: dict[str, Any], *, path_key: str, digest_key: str, code: str) -> str:
    path = _safe_file(root, record.get(path_key), code=code)
    observed = _sha256_bytes(path.read_bytes())
    declared = record.get(digest_key)
    if not isinstance(declared, str) or observed != declared:
        raise _error(code, f"The SHA-256 declaration for {path.name} does not match its bytes.")
    return observed


def _dhash64(image_bytes: bytes) -> str:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - exercised by clean-install users
        raise _error(
            "missing_multimodal_image_dependency",
            "Install the 'multimodal' extra to verify perceptual image hashes.",
        ) from exc
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            grayscale = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(grayscale.tobytes())
    except Exception as exc:
        raise _error("invalid_human_multimodal_image", "An image could not be decoded safely.") from exc
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return f"{bits:016x}"


def _hamming_hex(left: str, right: str) -> int:
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError as exc:
        raise _error("invalid_perceptual_hash", "Perceptual hashes must be hexadecimal.") from exc


def human_multimodal_contract() -> dict[str, Any]:
    """Return the complete file and evidence contract without pretending data exist."""

    return {
        "receipt_type": "humorvibes_human_multimodal_contract",
        "schema_version": SCHEMA_VERSION,
        "required_files": [MANIFEST_NAME, CAPTIONS_NAME, RIGHTS_NAME],
        "required_manifest_sections": [
            "cohort_id",
            "data_origin",
            "source_snapshot",
            "label_protocol",
            "feature_names",
            "feature_provenance",
            "images",
            "content_digest",
        ],
        "required_image_evidence": [
            "image_sha256",
            "perceptual_hash=dhash-64-v1",
            "canonical_scene_group_id",
            "asset-specific rights ledger row",
        ],
        "required_human_evidence": [
            "human_observed target origin",
            "rating count and standard error per caption",
            "protocol and consent evidence digests",
            "declared audience population and collection dates",
        ],
        "automatic_failures": [
            "missing or unknown asset licence",
            "rights evidence or source snapshot hash mismatch",
            "exact image duplication",
            "near-duplicate image crossing a split",
            "canonical scene group crossing a split",
            "synthetic or model-derived target",
            "direct participant identity field",
            "feature dimension or content digest drift",
        ],
        "truth_boundary": {
            "machine_validation_authenticates_human_identity": False,
            "machine_validation_is_legal_advice": False,
            "machine_validation_proves_consent": False,
            "external_rights_and_research_review_required": True,
        },
    }


def human_multimodal_content_digest(
    *, images: list[dict[str, Any]], captions: list[dict[str, Any]], rights: list[dict[str, Any]]
) -> str:
    """Compute the bundle digest used by the manifest."""

    return _canonical_digest({"images": images, "captions": captions, "rights": rights})


def _validate_label_protocol(root: Path, protocol: Any) -> dict[str, Any]:
    if not isinstance(protocol, dict) or protocol.get("human_observed") is not True:
        raise _error("invalid_human_label_protocol", "The label protocol must declare human-observed targets.")
    if protocol.get("target_unit") != "mean_funniness_rating_per_caption":
        raise _error("invalid_human_label_protocol", "The frozen target unit must be mean funniness per caption.")
    scale = protocol.get("scale")
    if (
        not isinstance(scale, list)
        or len(scale) != 2
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in scale)
        or float(scale[0]) >= float(scale[1])
    ):
        raise _error("invalid_human_label_protocol", "The label protocol needs a finite ascending scale.")
    minimum_raters = protocol.get("minimum_raters_per_caption")
    if isinstance(minimum_raters, bool) or not isinstance(minimum_raters, int) or minimum_raters < 3:
        raise _error("invalid_human_label_protocol", "At least three human ratings per caption are required.")
    for field in ("audience_population", "collection_started", "collection_ended", "aggregation"):
        if not isinstance(protocol.get(field), str) or not protocol[field].strip():
            raise _error("invalid_human_label_protocol", f"The label protocol requires {field}.")
    _verify_file_digest(
        root,
        protocol,
        path_key="protocol_evidence_path",
        digest_key="protocol_evidence_sha256",
        code="invalid_human_protocol_evidence",
    )
    _verify_file_digest(
        root,
        protocol,
        path_key="consent_evidence_path",
        digest_key="consent_evidence_sha256",
        code="invalid_human_consent_evidence",
    )
    return {"scale": [float(scale[0]), float(scale[1])], "minimum_raters": minimum_raters}


def _validate_rights(root: Path, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not rows:
        raise _error("missing_multimodal_rights", "The per-asset rights ledger cannot be empty.")
    by_asset: dict[str, dict[str, Any]] = {}
    for row in rows:
        asset_id = row.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in by_asset:
            raise _error("invalid_multimodal_rights", "Rights ledger asset IDs must be unique and non-empty.")
        if row.get("rights_basis") not in RIGHTS_BASES:
            raise _error("invalid_multimodal_rights", "Every asset needs a recognized rights basis.")
        license_spdx = row.get("license_spdx")
        if not isinstance(license_spdx, str) or license_spdx.upper() in DISALLOWED_LICENSES:
            raise _error("invalid_multimodal_rights", "Unknown, absent, or asserted-without-licence assets fail closed.")
        if any(row.get(flag) is not True for flag in ("redistribution_allowed", "research_allowed", "derivatives_allowed")):
            raise _error("invalid_multimodal_rights", "Rights must explicitly cover redistribution, research, and derivatives.")
        if not isinstance(row.get("source_url"), str) or not row["source_url"].startswith(("https://", "http://")):
            raise _error("invalid_multimodal_rights", "Every rights row needs an auditable source URL.")
        _verify_file_digest(
            root,
            row,
            path_key="evidence_path",
            digest_key="evidence_sha256",
            code="invalid_multimodal_rights_evidence",
        )
        by_asset[asset_id] = row
    return by_asset


def _validate_features(feature_names: Any, provenance: Any) -> dict[str, list[str]]:
    if not isinstance(feature_names, dict) or set(feature_names) != set(ARM_NAMES):
        raise _error("invalid_human_multimodal_features", "Feature names must define text, image, and fusion arms.")
    if not isinstance(provenance, dict) or set(provenance) != set(ARM_NAMES):
        raise _error("invalid_human_multimodal_features", "Every feature arm needs exact model provenance.")
    normalized: dict[str, list[str]] = {}
    for arm in ARM_NAMES:
        names = feature_names[arm]
        details = provenance[arm]
        if not isinstance(names, list) or not names or any(not isinstance(value, str) or not value for value in names):
            raise _error("invalid_human_multimodal_features", "Feature names must be non-empty strings.")
        if len(names) != len(set(names)):
            raise _error("invalid_human_multimodal_features", "Feature names must be unique within each arm.")
        if not isinstance(details, dict) or details.get("executed") is not True:
            raise _error("invalid_human_multimodal_features", "Feature provenance must describe an executed arm.")
        for field in ("provider", "model", "revision", "preprocessing"):
            if not isinstance(details.get(field), str) or not details[field].strip():
                raise _error("invalid_human_multimodal_features", f"Feature provenance requires {field}.")
        if details.get("dimensions") != len(names):
            raise _error("invalid_human_multimodal_features", "Declared feature dimensions do not match names.")
        normalized[arm] = names
    return normalized


def validate_human_multimodal_bundle(root: Path) -> dict[str, Any]:
    """Validate a local cohort without returning caption bodies or participant identities."""

    root = Path(root)
    manifest = _read_json(root / MANIFEST_NAME)
    captions = _read_jsonl(root / CAPTIONS_NAME)
    rights = _read_jsonl(root / RIGHTS_NAME)
    if manifest.get("receipt_type") != "humorvibes_human_multimodal_manifest" or manifest.get("schema_version") != SCHEMA_VERSION:
        raise _error("invalid_human_multimodal_manifest", "Unknown manifest type or schema version.")
    if manifest.get("data_origin") != "human_observed":
        raise _error("invalid_human_multimodal_origin", "Human bundles cannot contain synthetic or model-derived targets.")
    if not isinstance(manifest.get("cohort_id"), str) or not manifest["cohort_id"].strip():
        raise _error("invalid_human_multimodal_manifest", "A stable cohort ID is required.")
    source = manifest.get("source_snapshot")
    if not isinstance(source, dict):
        raise _error("invalid_human_source_snapshot", "A local immutable source snapshot is required.")
    for field in ("source_url", "immutable_revision", "retrieved_at"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise _error("invalid_human_source_snapshot", f"The source snapshot requires {field}.")
    _verify_file_digest(
        root,
        source,
        path_key="snapshot_path",
        digest_key="snapshot_sha256",
        code="invalid_human_source_snapshot",
    )
    label = _validate_label_protocol(root, manifest.get("label_protocol"))
    rights_by_asset = _validate_rights(root, rights)
    feature_names = _validate_features(manifest.get("feature_names"), manifest.get("feature_provenance"))
    images = manifest.get("images")
    if not isinstance(images, list) or not images or not captions:
        raise _error("invalid_human_multimodal_manifest", "Images and caption rows are required.")
    threshold = manifest.get("near_duplicate_hamming_threshold", 4)
    if isinstance(threshold, bool) or not isinstance(threshold, int) or not 0 <= threshold <= 16:
        raise _error("invalid_perceptual_hash_threshold", "The dHash threshold must be an integer from 0 through 16.")

    contests: dict[str, dict[str, Any]] = {}
    exact_hashes: dict[str, str] = {}
    perceptual: list[tuple[str, str, str, str]] = []
    scene_splits: dict[str, str] = {}
    for image in images:
        if not isinstance(image, dict):
            raise _error("invalid_human_multimodal_image", "Every image manifest row must be an object.")
        contest_id = image.get("contest_id")
        split = image.get("split")
        scene_group = image.get("canonical_scene_group_id")
        asset_id = image.get("rights_asset_id")
        if not isinstance(contest_id, str) or not contest_id or contest_id in contests or split not in SPLITS:
            raise _error("invalid_human_multimodal_image", "Contest IDs must be unique and use frozen splits.")
        if not isinstance(scene_group, str) or not scene_group:
            raise _error("invalid_human_multimodal_image", "Every image needs a canonical scene group.")
        if scene_group in scene_splits and scene_splits[scene_group] != split:
            raise _error("human_multimodal_scene_split_leakage", "A canonical scene group crosses splits.")
        scene_splits[scene_group] = split
        right = rights_by_asset.get(str(asset_id))
        if right is None or right.get("asset_type") != "image" or right.get("contest_id") != contest_id:
            raise _error("invalid_multimodal_rights", "Each image needs its matching asset-level rights row.")
        path = _safe_file(root, image.get("image_path"), code="missing_human_multimodal_image")
        payload = path.read_bytes()
        exact = _sha256_bytes(payload)
        if image.get("image_sha256") != exact or right.get("asset_sha256") != exact:
            raise _error("human_multimodal_image_hash_mismatch", "Image and rights-ledger hashes must match local bytes.")
        if exact in exact_hashes:
            raise _error(
                "human_multimodal_exact_duplicate",
                "An exact image is assigned to more than one contest.",
                detail={"first": exact_hashes[exact], "second": contest_id},
            )
        if image.get("perceptual_hash_algorithm") != "dhash-64-v1":
            raise _error("invalid_perceptual_hash", "Only the pinned dhash-64-v1 algorithm is accepted.")
        observed_dhash = _dhash64(payload)
        if image.get("perceptual_hash") != observed_dhash:
            raise _error("human_multimodal_perceptual_hash_mismatch", "The declared dHash does not match the image.")
        for prior_hash, prior_contest, prior_split, prior_group in perceptual:
            if split != prior_split and scene_group != prior_group and _hamming_hex(observed_dhash, prior_hash) <= threshold:
                raise _error(
                    "human_multimodal_near_duplicate_split_leakage",
                    "Near-duplicate images from different scene groups cross splits.",
                    detail={"first": prior_contest, "second": contest_id, "threshold": threshold},
                )
        exact_hashes[exact] = contest_id
        perceptual.append((observed_dhash, contest_id, split, scene_group))
        contests[contest_id] = image

    caption_rights = {
        asset_id
        for asset_id, row in rights_by_asset.items()
        if row.get("asset_type") == "caption_cohort"
    }
    row_ids: set[str] = set()
    caption_counts: Counter[str] = Counter()
    for row in captions:
        identity = DIRECT_IDENTITY_FIELDS.intersection(row)
        if identity:
            raise _error(
                "human_multimodal_direct_identity",
                "Caption rows must be privacy-minimized and exclude direct identity fields.",
                detail={"fields": sorted(identity)},
            )
        row_id = row.get("row_id")
        contest_id = row.get("contest_id")
        contest = contests.get(str(contest_id))
        if not isinstance(row_id, str) or not row_id or row_id in row_ids or contest is None:
            raise _error("invalid_human_multimodal_row", "Rows need unique IDs and known contests.")
        if row.get("split") != contest.get("split"):
            raise _error("human_multimodal_contest_split_leakage", "A caption split disagrees with its contest.")
        if row.get("target_origin") != "human_observed":
            raise _error("invalid_human_multimodal_target", "Every target must remain explicitly human-observed.")
        if row.get("caption_rights_id") not in caption_rights:
            raise _error("invalid_multimodal_rights", "Every caption must reference the reviewed caption-cohort rights row.")
        if not isinstance(row.get("caption"), str) or not row["caption"].strip():
            raise _error("invalid_human_multimodal_row", "Caption text cannot be empty.")
        count = row.get("rating_count")
        target = row.get("target")
        standard_error = row.get("target_standard_error")
        if isinstance(count, bool) or not isinstance(count, int) or count < label["minimum_raters"]:
            raise _error("invalid_human_multimodal_target", "Rating counts do not meet the frozen minimum.")
        if (
            isinstance(target, bool)
            or not isinstance(target, (int, float))
            or not math.isfinite(target)
            or not label["scale"][0] <= float(target) <= label["scale"][1]
        ):
            raise _error("invalid_human_multimodal_target", "Targets must be finite and inside the frozen scale.")
        if isinstance(standard_error, bool) or not isinstance(standard_error, (int, float)) or not math.isfinite(standard_error) or standard_error < 0:
            raise _error("invalid_human_multimodal_target", "Every target needs a finite non-negative standard error.")
        features = row.get("features")
        if not isinstance(features, dict) or set(features) != set(ARM_NAMES):
            raise _error("invalid_human_multimodal_features", "Every row needs exactly the three frozen feature arms.")
        for arm in ARM_NAMES:
            vector = features[arm]
            if not isinstance(vector, list) or len(vector) != len(feature_names[arm]):
                raise _error("invalid_human_multimodal_features", "Feature vectors must match declared dimensions.")
            if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in vector):
                raise _error("invalid_human_multimodal_features", "Features must be finite numeric vectors.")
        row_ids.add(row_id)
        caption_counts[str(contest_id)] += 1

    minimum_captions = manifest.get("minimum_captions_per_contest", 5)
    if isinstance(minimum_captions, bool) or not isinstance(minimum_captions, int) or minimum_captions < 2:
        raise _error("invalid_human_multimodal_manifest", "The caption minimum must be at least two.")
    if set(caption_counts) != set(contests) or any(value < minimum_captions for value in caption_counts.values()):
        raise _error("insufficient_human_multimodal_captions", "Every contest must meet the frozen caption minimum.")
    split_counts = Counter(str(image["split"]) for image in images)
    if any(split_counts.get(split, 0) < 2 for split in SPLITS):
        raise _error("insufficient_human_multimodal_splits", "Every split needs at least two whole contests.")
    digest = human_multimodal_content_digest(images=images, captions=captions, rights=rights)
    if manifest.get("content_digest") != digest:
        raise _error("human_multimodal_content_digest_mismatch", "Manifested content changed after freezing.")
    return {
        "receipt_type": "humorvibes_human_multimodal_preflight",
        "receipt_version": 1,
        "status": "MACHINE_VALIDATED_EXTERNAL_REVIEW_REQUIRED",
        "ok": True,
        "cohort_id": manifest["cohort_id"],
        "counts": {
            "contests": len(contests),
            "captions": len(captions),
            "rights_rows": len(rights),
            "splits": dict(sorted(split_counts.items())),
        },
        "checks": {
            "source_snapshot_digest": True,
            "rights_evidence_digests": len(rights),
            "image_byte_hashes": len(images),
            "image_perceptual_hashes": len(images),
            "exact_duplicate_images": 0,
            "near_duplicate_split_crossings": 0,
            "canonical_scene_split_crossings": 0,
            "direct_identity_fields": 0,
            "human_target_rows": len(captions),
            "feature_arms": list(ARM_NAMES),
            "content_digest": digest,
        },
        "truth_boundary": {
            "human_observations_declared": True,
            "software_independently_authenticated_observers": False,
            "software_established_legal_rights": False,
            "software_established_consent": False,
            "claim_ready_for_multimodal_humor": False,
            "external_rights_and_research_review_required": True,
        },
    }


def evaluate_human_multimodal_bundle(root: Path) -> dict[str, Any]:
    """Evaluate three executed arms after the human-data preflight passes."""

    validation = validate_human_multimodal_bundle(root)
    root = Path(root)
    manifest = _read_json(root / MANIFEST_NAME)
    rows = _read_jsonl(root / CAPTIONS_NAME)
    train = [row for row in rows if row["split"] == "train"]
    test = [row for row in rows if row["split"] == "test"]
    if not train or not test:
        raise _error("missing_human_multimodal_split", "Train and held-out test rows are required.")
    evaluated_digest = _canonical_digest([row["row_id"] for row in test])
    slice_rows = [
        {
            **row,
            "strategy": row.get("caption_strategy", "unclassified"),
            "vote_count": row["rating_count"],
            "repeated_caption": bool(row.get("repeated_caption", False)),
        }
        for row in test
    ]
    arms: dict[str, Any] = {}
    for arm in ARM_NAMES:
        weights = _solve_linear(
            [[float(value) for value in row["features"][arm]] for row in train],
            [float(row["target"]) for row in train],
        )
        predictions = [
            _predict(weights, [float(value) for value in row["features"][arm]]) for row in test
        ]
        arms[arm] = {
            "feature_provenance": manifest["feature_provenance"][arm],
            "evaluated_row_digest": evaluated_digest,
            "metrics": _metrics(test, predictions),
            "calibration": _calibration(test, predictions),
            "error_slices": _slices(slice_rows, predictions),
        }
    return {
        "receipt_type": "humorvibes_human_multimodal_benchmark",
        "receipt_version": 1,
        "status": "ANALYSIS_COMPLETE_EXTERNAL_EVIDENCE_REVIEW_REQUIRED",
        "cohort_id": manifest["cohort_id"],
        "fixture_validation": validation,
        "arms": arms,
        "comparability": {
            "identical_held_out_rows": len({value["evaluated_row_digest"] for value in arms.values()}) == 1,
            "evaluated_row_digest": evaluated_digest,
            "grouping_unit": "contest_id",
            "whole_contest_splits": True,
        },
        "reference_bounds": {
            "real_caption_label_ceiling": 0.8262,
            "real_caption_text_only_bound": 0.4110,
            "text_only_bound_applies_to": ["text_only"],
            "bounds_are_contextual_references_not_acceptance_thresholds": True,
        },
        "truth_boundary": validation["truth_boundary"],
    }


def write_human_multimodal_receipt(path: Path, payload: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path
