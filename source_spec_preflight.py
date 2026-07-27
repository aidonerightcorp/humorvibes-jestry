"""Fail-closed, no-write preflight for one proposed Hugging Face source spec.

The default command runs entirely from a tiny committed fixture. ``--live`` performs two bounded
read-only requests (dataset metadata and first rows) and never invokes the harvest writer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Mapping

import corpus_census
import harvest_wave2


ROOT = Path(__file__).resolve().parent
DEFAULT_SPEC = ROOT / "fixtures" / "source_preflight" / "colbert_humor" / "source_spec.json"
DEFAULT_FIXTURE = ROOT / "fixtures" / "source_preflight" / "colbert_humor" / "upstream_fixture.json"
DEFAULT_EXPECTED = ROOT / "fixtures" / "source_preflight" / "colbert_humor" / "expected_normalized.json"
USER_AGENT = "HumorVibes-Source-Preflight/1.0 (+https://github.com/aidonerightcorp/humorvibes-jestry)"

REQUIRED_SPEC_FIELDS = {
    "source_key",
    "provider",
    "repo",
    "config",
    "split",
    "text",
    "labels",
    "lang",
    "license",
    "license_id",
    "license_evidence_url",
    "verified",
}
ALLOWED_SPEC_FIELDS = REQUIRED_SPEC_FIELDS | {
    "grade",
    "translation",
    "language_field",
    "offset",
    "pace",
    "revision",
}


class PreflightError(ValueError):
    def __init__(self, code: str, message: str, *, detail: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = dict(detail or {})

    def public(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.detail:
            payload["detail"] = self.detail
        return payload


def _digest(value: Any) -> str:
    rendered = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _load_json_bytes(raw: bytes, *, source: str) -> Any:
    try:
        decoded = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise PreflightError(
            "invalid_upstream_encoding",
            "Upstream response is not strict UTF-8.",
            detail={"source": source, "byte_offset": exc.start},
        ) from exc
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise PreflightError(
            "invalid_upstream_json",
            "Upstream response is not valid JSON.",
            detail={"source": source, "line": exc.lineno, "column": exc.colno},
        ) from exc


def _load_json_file(path: Path) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PreflightError(
            "unreadable_preflight_file", "Preflight input could not be read.", detail={"path": str(path)}
        ) from exc
    return _load_json_bytes(raw, source=str(path))


def validate_source_spec(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PreflightError("invalid_source_spec", "Source spec must be a JSON object.")
    missing = sorted(REQUIRED_SPEC_FIELDS - set(value))
    unknown = sorted(set(value) - ALLOWED_SPEC_FIELDS)
    if missing:
        raise PreflightError(
            "missing_source_spec_fields", "Source spec is incomplete.", detail={"missing": missing}
        )
    if unknown:
        raise PreflightError(
            "unknown_source_spec_fields", "Source spec contains unknown fields.", detail={"unknown": unknown}
        )
    spec = dict(value)
    for field in (
        "source_key",
        "provider",
        "repo",
        "config",
        "split",
        "lang",
        "license",
        "license_id",
        "license_evidence_url",
        "verified",
    ):
        if not isinstance(spec[field], str) or not spec[field].strip():
            raise PreflightError(
                "invalid_source_spec_field", f"Source spec field {field} must be a non-empty string."
            )
        spec[field] = spec[field].strip()
    if spec["provider"] != "huggingface":
        raise PreflightError(
            "unsupported_source_provider", "This first preflight contract supports provider=huggingface."
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", spec["repo"]) is None:
        raise PreflightError(
            "invalid_huggingface_repo", "Hugging Face repo must be an exact owner/name identifier."
        )
    parsed_evidence = urllib.parse.urlsplit(spec["license_evidence_url"])
    if parsed_evidence.scheme != "https" or not parsed_evidence.hostname:
        raise PreflightError(
            "invalid_license_evidence_url", "License evidence must be an absolute HTTPS URL."
        )
    text_fields = spec["text"] if isinstance(spec["text"], list) else [spec["text"]]
    if not text_fields or any(not isinstance(field, str) or not field for field in text_fields):
        raise PreflightError(
            "invalid_source_text_fields", "Source spec text must be a field name or non-empty list."
        )
    if not isinstance(spec["labels"], list) or any(
        not isinstance(field, str) or not field for field in spec["labels"]
    ):
        raise PreflightError("invalid_source_labels", "Source spec labels must be a string list.")
    if not spec["license"].strip():
        raise PreflightError("missing_source_license", "Source spec requires an exact license string.")
    return spec


def _bounded_fetch(url: str, *, timeout: float, maximum_bytes: int = 2_000_000) -> tuple[bytes, dict[str, Any]]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "huggingface.co",
        "datasets-server.huggingface.co",
    }:
        raise PreflightError(
            "unapproved_preflight_host", "Live preflight only contacts the two pinned Hugging Face hosts."
        )
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(maximum_bytes + 1)
            status = int(getattr(response, "status", 200))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PreflightError(
            "live_preflight_fetch_failed",
            "Bounded live preflight request failed.",
            detail={"url": url, "error_type": type(exc).__name__},
        ) from exc
    if len(raw) > maximum_bytes:
        raise PreflightError(
            "live_preflight_response_too_large",
            "Live preflight response exceeded the two-megabyte cap.",
            detail={"url": url, "maximum_bytes": maximum_bytes},
        )
    if "json" not in content_type.casefold():
        raise PreflightError(
            "live_preflight_non_json_content_type",
            "Live preflight requires a JSON content type.",
            detail={"url": url, "content_type": content_type},
        )
    return raw, {
        "url": url,
        "status": status,
        "content_type": content_type,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _live_payload(spec: Mapping[str, Any], *, timeout: float, limit: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    repo_query = urllib.parse.quote(str(spec["repo"]), safe="")
    repo_path = urllib.parse.quote(str(spec["repo"]), safe="/")
    config = urllib.parse.quote(str(spec["config"]), safe="")
    split = urllib.parse.quote(str(spec["split"]), safe="")
    metadata_url = f"https://huggingface.co/api/datasets/{repo_path}"
    rows_url = (
        "https://datasets-server.huggingface.co/first-rows"
        f"?dataset={repo_query}&config={config}&split={split}"
    )
    metadata_raw, metadata_observation = _bounded_fetch(metadata_url, timeout=timeout)
    rows_raw, rows_observation = _bounded_fetch(rows_url, timeout=timeout)
    metadata = _load_json_bytes(metadata_raw, source=metadata_url)
    first_rows = _load_json_bytes(rows_raw, source=rows_url)
    if isinstance(first_rows, dict) and isinstance(first_rows.get("rows"), list):
        first_rows = dict(first_rows)
        first_rows["rows"] = first_rows["rows"][:limit]
    return {
        "dataset_metadata": metadata,
        "first_rows": first_rows,
    }, [metadata_observation, rows_observation]


def _validate_upstream_shape(payload: Any, spec: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(payload, dict):
        raise PreflightError("invalid_upstream_shape", "Fixture/live payload must be a JSON object.")
    metadata = payload.get("dataset_metadata")
    first_rows = payload.get("first_rows")
    if not isinstance(metadata, dict) or not isinstance(first_rows, dict):
        raise PreflightError(
            "invalid_upstream_shape", "Payload requires dataset_metadata and first_rows objects."
        )
    if not isinstance(metadata.get("cardData"), dict):
        raise PreflightError(
            "invalid_upstream_metadata", "Dataset metadata requires a cardData object."
        )
    features = first_rows.get("features")
    wrapped_rows = first_rows.get("rows")
    if not isinstance(features, list) or not isinstance(wrapped_rows, list):
        raise PreflightError(
            "invalid_upstream_shape", "first_rows requires features and rows arrays."
        )
    if not wrapped_rows:
        raise PreflightError("empty_upstream_response", "Upstream first_rows response contains no rows.")
    columns: list[str] = []
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("name"), str):
            raise PreflightError("invalid_upstream_features", "Every feature requires a string name.")
        columns.append(feature["name"])
    required_columns = set(spec["text"] if isinstance(spec["text"], list) else [spec["text"]])
    required_columns.update(spec.get("labels", []))
    for optional_mapping in ("grade", "translation", "language_field"):
        if spec.get(optional_mapping):
            required_columns.add(str(spec[optional_mapping]))
    missing_columns = sorted(required_columns - set(columns))
    if missing_columns:
        raise PreflightError(
            "source_schema_drift",
            "Observed columns do not satisfy the source spec.",
            detail={"missing_columns": missing_columns, "observed_columns": columns},
        )
    rows: list[dict[str, Any]] = []
    row_ids: set[int] = set()
    for position, wrapped in enumerate(wrapped_rows):
        if not isinstance(wrapped, dict) or type(wrapped.get("row_idx")) is not int:
            raise PreflightError(
                "invalid_upstream_row", "Each upstream row requires an integer row_idx."
            )
        row_id = wrapped["row_idx"]
        if row_id in row_ids:
            raise PreflightError(
                "duplicate_upstream_row_id",
                "Upstream sample contains duplicate row IDs.",
                detail={"row_idx": row_id},
            )
        row_ids.add(row_id)
        if not isinstance(wrapped.get("row"), dict):
            raise PreflightError(
                "invalid_upstream_row", "Each upstream wrapper requires a row object."
            )
        rows.append({"row_idx": row_id, "row": wrapped["row"], "position": position})
    return rows, columns


def run_preflight(
    spec_value: Any,
    payload: Any,
    *,
    mode: str,
    expected_normalized: Any | None = None,
    network_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    spec = validate_source_spec(spec_value)
    rows, columns = _validate_upstream_shape(payload, spec)
    metadata = payload["dataset_metadata"]
    observed_license_id = (metadata.get("cardData") or {}).get("license")
    observed_repo = metadata.get("id")
    observed_revision = metadata.get("sha")
    license_matches = observed_license_id == spec["license_id"]
    repository_matches = observed_repo == spec["repo"]
    revision_matches = not spec.get("revision") or observed_revision == spec["revision"]

    normalized: list[dict[str, Any]] = []
    dropped = 0
    normalized_texts: set[str] = set()
    for item in rows:
        record = harvest_wave2._record_from_hf_row(
            spec,
            spec["repo"],
            spec["config"],
            spec["split"],
            item["row"],
            item["row_idx"],
        )
        if record is None:
            dropped += 1
            continue
        canonical_text = record["text"].casefold()
        if canonical_text in normalized_texts:
            raise PreflightError(
                "duplicate_normalized_text", "Normalized sample contains duplicate text."
            )
        normalized_texts.add(canonical_text)
        normalized.append(record)
    if not normalized:
        raise PreflightError(
            "no_normalized_rows", "No upstream rows survived normalization and screening."
        )

    expected_match: bool | None = None
    expected_digest: str | None = None
    if expected_normalized is not None:
        if not isinstance(expected_normalized, list) or any(
            not isinstance(row, dict) for row in expected_normalized
        ):
            raise PreflightError(
                "invalid_expected_normalized", "Expected normalized fixture must be a JSON array."
            )
        expected_digest = _digest(expected_normalized)
        expected_match = normalized == expected_normalized
        if not expected_match:
            raise PreflightError(
                "normalized_fixture_mismatch",
                "Parser output does not match the committed expected rows.",
                detail={
                    "expected_digest": expected_digest,
                    "observed_digest": _digest(normalized),
                },
            )

    licence_class = corpus_census.classify_licence(spec["license"])
    explicit_export_grant = corpus_census.may_redistribute_text(spec["license"])
    export_eligible = bool(
        explicit_export_grant
        and license_matches
        and repository_matches
        and revision_matches
        and normalized
        and (expected_match is not False)
    )
    receipt = {
        "receipt_type": "humorvibes_source_spec_preflight",
        "receipt_version": 1,
        "mode": mode,
        "source": {
            "source_key": spec["source_key"],
            "provider": spec["provider"],
            "repo": spec["repo"],
            "config": spec["config"],
            "split": spec["split"],
            "candidate_rows_url": (
                "https://datasets-server.huggingface.co/first-rows"
                f"?dataset={urllib.parse.quote(spec['repo'], safe='')}"
                f"&config={urllib.parse.quote(spec['config'], safe='')}"
                f"&split={urllib.parse.quote(spec['split'], safe='')}"
            ),
            "observed_repo": observed_repo,
            "observed_revision": observed_revision,
            "declared_revision": spec.get("revision"),
        },
        "observed_response": {
            "columns": columns,
            "input_rows": len(rows),
            "normalized_rows": len(normalized),
            "screened_rows": dropped,
            "row_ids_unique": True,
            "normalized_rows_sha256": _digest(normalized),
            "network_requests": network_observations or [],
        },
        "parser": {
            "implementation": "harvest_wave2._record_from_hf_row",
            "success": True,
            "expected_fixture_checked": expected_match is not None,
            "expected_fixture_match": expected_match,
            "expected_fixture_sha256": expected_digest,
        },
        "license_evidence": {
            "declared_license": spec["license"],
            "declared_license_id": spec["license_id"],
            "evidence_url": spec["license_evidence_url"],
            "observed_license_id": observed_license_id,
            "license_id_matches": license_matches,
            "repository_identity_matches": repository_matches,
            "revision_matches": revision_matches,
            "licence_class": licence_class,
        },
        "release_decision": {
            "export_eligible": export_eligible,
            "policy": "deny-first: explicit redistributable class plus matching live/fixture license and repository evidence",
            "failed_gates": [
                name
                for name, passed in {
                    "explicit_redistribution_grant": explicit_export_grant,
                    "license_evidence_matches": license_matches,
                    "repository_identity_matches": repository_matches,
                    "revision_matches": revision_matches,
                    "normalized_rows_present": bool(normalized),
                    "expected_fixture_matches": expected_match is not False,
                }.items()
                if not passed
            ],
        },
        "safety": {
            "writes_corpus": False,
            "maximum_live_rows": len(rows) if mode == "live" else 0,
            "raw_text_in_receipt": False,
            "network_disabled_by_default": True,
        },
        "ok": True,
    }
    receipt["preflight_digest"] = _digest(receipt)
    return receipt


def execute(
    *,
    spec_path: Path = DEFAULT_SPEC,
    fixture_path: Path = DEFAULT_FIXTURE,
    expected_path: Path = DEFAULT_EXPECTED,
    live: bool = False,
    limit: int = 5,
    timeout: float = 15.0,
) -> dict[str, Any]:
    if type(limit) is not int or not 1 <= limit <= 25:
        raise PreflightError("invalid_live_limit", "Live limit must be an integer from 1 through 25.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout):
        raise PreflightError("invalid_live_timeout", "Live timeout must be finite numeric seconds.")
    if not 1.0 <= float(timeout) <= 30.0:
        raise PreflightError("invalid_live_timeout", "Live timeout must be from 1 through 30 seconds.")
    spec = _load_json_file(spec_path)
    if live:
        validated = validate_source_spec(spec)
        payload, observations = _live_payload(validated, timeout=float(timeout), limit=limit)
        return run_preflight(
            validated,
            payload,
            mode="live",
            network_observations=observations,
        )
    payload = _load_json_file(fixture_path)
    expected = _load_json_file(expected_path)
    return run_preflight(spec, payload, mode="fixture", expected_normalized=expected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    parser.add_argument("--live", action="store_true", help="perform bounded read-only HF requests")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        receipt = execute(
            spec_path=args.spec,
            fixture_path=args.fixture,
            expected_path=args.expected,
            live=args.live,
            limit=args.limit,
            timeout=args.timeout,
        )
    except PreflightError as exc:
        receipt = {
            "receipt_type": "humorvibes_source_spec_preflight",
            "receipt_version": 1,
            "ok": False,
            "error": exc.public(),
            "safety": {"writes_corpus": False, "raw_text_in_receipt": False},
        }
        exit_code = 2
    else:
        exit_code = 0
    rendered = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
