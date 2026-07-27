"""Reproducible semantic-provider compatibility and retrieval-quality matrix."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from .config import Settings
from .embeddings import EmbeddingRegistry
from .errors import IntegrationError
from .http import JsonHttpClient
from .retrieval_benchmark import evaluate_retrieval, load_retrieval_dataset


SPEC_VERSION = 1
BACKENDS = {"ollama", "openai-compatible", "sentence-transformers"}
REQUEST_SCHEMAS = {
    "ollama": "ollama:/api/embed:v1",
    "openai-compatible": "openai:/v1/embeddings:v1",
    "sentence-transformers": "sentence-transformers:encode:v1",
}


def _error(code: str, message: str, *, detail: dict[str, Any] | None = None) -> IntegrationError:
    return IntegrationError(code, message, 422, detail=detail)


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _safe_error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, IntegrationError):
        public = exc.public()
        return {
            "type": "IntegrationError",
            "code": public["code"],
            "retryable": bool(public.get("retryable", False)),
            "upstream_status": (public.get("detail") or {}).get("upstream_status"),
        }
    return {"type": type(exc).__name__, "code": "provider_matrix_internal_error", "retryable": False}


def load_provider_matrix_spec(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _error("missing_provider_matrix_spec", "The provider matrix spec is missing.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("invalid_provider_matrix_spec", "The provider matrix spec is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise _error("invalid_provider_matrix_spec", "The provider matrix spec must be an object.")
    return value


def validate_provider_matrix_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if spec.get("receipt_type") != "humorvibes_provider_matrix_spec" or spec.get("spec_version") != SPEC_VERSION:
        raise _error("invalid_provider_matrix_spec", "Unknown provider matrix type or version.")
    benchmarks = spec.get("benchmarks")
    runs = spec.get("runs")
    if not isinstance(benchmarks, list) or not benchmarks or not isinstance(runs, list) or not runs:
        raise _error("invalid_provider_matrix_spec", "At least one benchmark and provider run are required.")
    benchmark_ids: set[str] = set()
    for benchmark in benchmarks:
        if not isinstance(benchmark, dict):
            raise _error("invalid_provider_matrix_spec", "Benchmark rows must be objects.")
        benchmark_id = benchmark.get("benchmark_id")
        if not isinstance(benchmark_id, str) or not benchmark_id or benchmark_id in benchmark_ids:
            raise _error("invalid_provider_matrix_spec", "Benchmark IDs must be unique and non-empty.")
        if not isinstance(benchmark.get("root"), str) or not benchmark["root"]:
            raise _error("invalid_provider_matrix_spec", "Benchmark roots must be relative paths.")
        if Path(benchmark["root"]).is_absolute() or ".." in Path(benchmark["root"]).parts:
            raise _error("invalid_provider_matrix_spec", "Benchmark roots cannot escape the spec directory.")
        if not re.fullmatch(r"[0-9a-f]{64}", str(benchmark.get("expected_digest", ""))):
            raise _error("invalid_provider_matrix_spec", "Each benchmark needs its frozen content digest.")
        benchmark_ids.add(benchmark_id)

    run_ids: set[str] = set()
    for run in runs:
        if not isinstance(run, dict):
            raise _error("invalid_provider_matrix_spec", "Provider rows must be objects.")
        run_id = run.get("run_id")
        backend = run.get("backend")
        if not isinstance(run_id, str) or not run_id or run_id in run_ids or backend not in BACKENDS:
            raise _error("invalid_provider_matrix_spec", "Provider run IDs and backend kinds must be valid and unique.")
        for forbidden in ("api_key", "token", "secret", "authorization"):
            if forbidden in run:
                raise _error("provider_matrix_secret_in_spec", "Specs may name a secret environment variable but never contain credentials.")
        for field in (
            "remote_model",
            "model_digest",
            "model_license",
            "server_implementation",
            "server_version",
            "server_artifact",
            "request_schema",
            "hardware_class",
        ):
            if not isinstance(run.get(field), str) or not run[field].strip():
                raise _error("invalid_provider_matrix_spec", f"Provider rows require exact {field} metadata.")
        if run["request_schema"] != REQUEST_SCHEMAS[backend]:
            raise _error("invalid_provider_matrix_spec", "The request schema does not match the backend kind.")
        if run["server_version"].lower() in {"latest", "unknown", "unversioned"}:
            raise _error("invalid_provider_matrix_spec", "Server versions must be exact, not floating labels.")
        if not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}|[0-9a-f]{7,40}", run["model_digest"]):
            raise _error("invalid_provider_matrix_spec", "Model digests must be immutable hexadecimal identities.")
        dimensions = run.get("expected_dimensions")
        if isinstance(dimensions, bool) or not isinstance(dimensions, int) or not 1 <= dimensions <= 65_536:
            raise _error("invalid_provider_matrix_spec", "Expected embedding dimensions must be a positive integer.")
        timeout = run.get("timeout_seconds")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 300:
            raise _error("invalid_provider_matrix_spec", "Provider timeouts must be between 1 and 300 seconds.")
        if backend != "sentence-transformers":
            if not isinstance(run.get("base_url"), str) or not run["base_url"]:
                raise _error("invalid_provider_matrix_spec", "Network providers require a base URL.")
            if run.get("readiness_base_url") is not None and (
                not isinstance(run["readiness_base_url"], str)
                or not run["readiness_base_url"]
            ):
                raise _error("invalid_provider_matrix_spec", "Readiness base URLs must be non-empty URLs.")
            readiness_path = run.get("readiness_path")
            if readiness_path is not None and (
                not isinstance(readiness_path, str)
                or not re.fullmatch(r"/[A-Za-z0-9._/-]+", readiness_path)
                or ".." in readiness_path.split("/")
            ):
                raise _error("invalid_provider_matrix_spec", "Readiness paths must be fixed safe paths.")
        elif run.get("base_url") not in (None, ""):
            raise _error("invalid_provider_matrix_spec", "In-process sentence-transformers runs do not use a base URL.")
        api_key_env = run.get("api_key_env", "")
        if api_key_env and (not isinstance(api_key_env, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", api_key_env)):
            raise _error("invalid_provider_matrix_spec", "Secret environment variable names must be uppercase identifiers.")
        run_ids.add(run_id)
    return {
        "ok": True,
        "benchmarks": len(benchmark_ids),
        "runs": len(run_ids),
        "spec_digest": _canonical_digest(spec),
    }


def _settings_for_run(run: dict[str, Any], environment: Mapping[str, str]) -> tuple[Settings, str, list[str]]:
    backend = str(run["backend"])
    model = str(run["remote_model"])
    timeout = str(run["timeout_seconds"])
    key_name = str(run.get("api_key_env") or "")
    secret = environment.get(key_name, "") if key_name else ""
    common = {
        "HUMORVIBES_REQUEST_TIMEOUT": timeout,
        "HUMORVIBES_MAX_BATCH_ITEMS": str(run.get("batch_size", 64)),
    }
    secrets = [secret] if secret else []
    if backend == "ollama":
        values = {
            **common,
            "OLLAMA_HOST": str(run["base_url"]),
            "OLLAMA_API_KEY": secret,
            "HUMORVIBES_OLLAMA_EMBED_MODELS": model,
            "HUMORVIBES_EMBEDDING_DEFAULT": f"ollama:{model}",
        }
        return Settings.from_env(values), f"ollama:{model}", secrets
    if backend == "openai-compatible":
        values = {
            **common,
            "HUMORVIBES_OPENAI_BASE_URL": str(run["base_url"]),
            "HUMORVIBES_OPENAI_API_KEY": secret,
            "HUMORVIBES_OPENAI_EMBED_MODELS": model,
            "HUMORVIBES_EMBEDDING_DEFAULT": f"openai:{model}",
        }
        return Settings.from_env(values), f"openai:{model}", secrets
    values = {
        **common,
        "HUMORVIBES_SENTENCE_TRANSFORMER_MODELS": model,
        "HUMORVIBES_EMBEDDING_DEFAULT": f"sentence-transformers:{model}",
    }
    return Settings.from_env(values), f"sentence-transformers:{model}", secrets


def _readiness(run: dict[str, Any], settings: Settings) -> dict[str, Any]:
    backend = str(run["backend"])
    if backend == "sentence-transformers":
        return {"checked": True, "reachable": True, "method": "in_process_import_deferred_to_operation"}
    base_url = str(run.get("readiness_base_url") or run["base_url"])
    key = settings.ollama_api_key if backend == "ollama" else settings.openai_api_key
    client = JsonHttpClient(
        base_url,
        api_key=key,
        timeout=float(run["timeout_seconds"]),
        max_response_bytes=1_000_000,
    )
    path = str(run.get("readiness_path") or ("/api/version" if backend == "ollama" else "/models"))
    try:
        response = client.request(path)
        public: dict[str, Any] = {
            "checked": True,
            "reachable": True,
            "method": f"GET {path}",
            "response_shape": sorted(response),
        }
        if backend == "ollama" and isinstance(response.get("version"), str):
            public["observed_server_version"] = response["version"]
        return public
    except IntegrationError as exc:
        return {"checked": True, "reachable": False, "method": f"GET {path}", "error": _safe_error(exc)}


def _verify_server_artifact(run: dict[str, Any]) -> dict[str, Any]:
    artifact = str(run["server_artifact"])
    if run["server_implementation"] == "ollama" and artifact.startswith("sha256:"):
        executable = shutil.which("ollama")
        if not executable:
            return {"checked": True, "verified": False, "error": {"code": "ollama_binary_missing"}}
        observed = hashlib.sha256(Path(executable).read_bytes()).hexdigest()
        return {
            "checked": True,
            "method": "local executable SHA-256",
            "verified": artifact == f"sha256:{observed}",
            "observed_sha256": observed,
        }
    if (
        run["server_implementation"] == "huggingface-text-embeddings-inference"
        and artifact.startswith("sha256:")
    ):
        docker = shutil.which("docker")
        if not docker:
            return {"checked": True, "verified": False, "error": {"code": "docker_binary_missing"}}
        completed = subprocess.run(
            [docker, "image", "inspect", artifact, "--format", "{{.Id}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        observed = completed.stdout.strip()
        return {
            "checked": True,
            "method": "local Docker image ID",
            "verified": completed.returncode == 0 and observed == artifact,
            "observed_image_id": observed or None,
        }
    return {
        "checked": False,
        "verified": False,
        "method": "declared immutable artifact; independent registry verification required",
    }


def run_provider_matrix(
    spec: dict[str, Any],
    *,
    spec_dir: Path,
    environment: Mapping[str, str] | None = None,
    registry_factory: Callable[[dict[str, Any], Settings], Any] | None = None,
    readiness_probe: Callable[[dict[str, Any], Settings], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run every declared provider against every identical frozen benchmark."""

    validation = validate_provider_matrix_spec(spec)
    env = dict(os.environ if environment is None else environment)
    spec_dir = Path(spec_dir)
    benchmarks: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in spec["benchmarks"]:
        root = (spec_dir / str(row["root"])).resolve()
        if not root.is_relative_to(spec_dir.resolve()):
            raise _error("invalid_provider_matrix_spec", "A benchmark root escaped the spec directory.")
        dataset = load_retrieval_dataset(root)
        observed = dataset.get("manifest", {}).get("content_digest")
        if observed != row["expected_digest"]:
            raise _error(
                "provider_matrix_benchmark_drift",
                "A benchmark digest changed after the matrix was frozen.",
                detail={"benchmark_id": row["benchmark_id"], "expected": row["expected_digest"], "observed": observed},
            )
        benchmarks.append((row, dataset))

    matrix_rows: list[dict[str, Any]] = []
    configured_secrets: list[str] = []
    for run in spec["runs"]:
        settings, model_id, secrets = _settings_for_run(run, env)
        configured_secrets.extend(secrets)
        public_run = {
            key: value
            for key, value in run.items()
            if key != "api_key_env"
        }
        row: dict[str, Any] = {
            **public_run,
            "model_id": model_id,
            "configured": True,
            "credential_configured": bool(secrets),
            "readiness": {},
            "server_artifact_verification": _verify_server_artifact(run),
            "bounded_operation": {"executed": False},
            "quality_benchmarks": {},
            "quality_validated": False,
        }
        readiness = (readiness_probe or _readiness)(run, settings)
        row["readiness"] = readiness
        observed_version = readiness.get("observed_server_version")
        if observed_version is not None and observed_version != run["server_version"]:
            row["failure"] = {
                "stage": "server_version_gate",
                "error": {
                    "code": "provider_matrix_server_version_mismatch",
                    "expected": run["server_version"],
                    "observed": observed_version,
                },
            }
            matrix_rows.append(row)
            continue
        artifact_check = row["server_artifact_verification"]
        if artifact_check["checked"] and not artifact_check["verified"]:
            row["failure"] = {
                "stage": "server_artifact_gate",
                "error": {"code": "provider_matrix_server_artifact_mismatch"},
            }
            matrix_rows.append(row)
            continue
        registry = (registry_factory or (lambda _run, current: EmbeddingRegistry(current)))(run, settings)
        try:
            probe = registry.probe(model_id)
            row["bounded_operation"] = {
                "executed": bool(probe.get("ok")),
                "response": probe,
            }
            if not probe.get("ok"):
                row["failure"] = {
                    "stage": "bounded_operation",
                    "error": probe.get("error", {"code": "provider_probe_failed"}),
                }
                matrix_rows.append(row)
                continue
            dimensions = probe.get("dimensions")
            if dimensions != run["expected_dimensions"]:
                row["failure"] = {
                    "stage": "dimension_gate",
                    "error": {
                        "code": "provider_matrix_dimension_mismatch",
                        "expected": run["expected_dimensions"],
                        "observed": dimensions,
                    },
                }
                matrix_rows.append(row)
                continue
            for benchmark, dataset in benchmarks:
                benchmark_id = str(benchmark["benchmark_id"])
                try:
                    result = evaluate_retrieval(dataset, model_id=model_id, registry=registry)
                    row["quality_benchmarks"][benchmark_id] = {
                        "executed": True,
                        "benchmark_digest": result["benchmark_digest"],
                        "model": result["model"],
                        "overall": result["overall"],
                        "metrics_by_split": result["metrics_by_split"],
                        "metrics_by_language": result["metrics_by_language"],
                        "failure_slices": result["failure_slices"],
                        "frozen_input_digests": result["frozen_input_digests"],
                        "duration_seconds": result.get("duration_seconds"),
                        "receipt_digest": result["receipt_digest"],
                        "truth_boundary": result["truth_boundary"],
                    }
                except Exception as exc:  # preserve failed provider arms in the public matrix
                    row["quality_benchmarks"][benchmark_id] = {
                        "executed": False,
                        "error": _safe_error(exc),
                    }
            row["quality_validated"] = all(
                value.get("executed") is True for value in row["quality_benchmarks"].values()
            )
        except Exception as exc:  # defensive: one provider cannot erase the matrix
            row["failure"] = {"stage": "bounded_operation", "error": _safe_error(exc)}
        matrix_rows.append(row)

    successful = sum(row["quality_validated"] for row in matrix_rows)
    receipt: dict[str, Any] = {
        "receipt_type": "humorvibes_semantic_provider_matrix",
        "receipt_version": 1,
        "spec_validation": validation,
        "runtime": {
            "platform": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "hardware_class": spec.get("hardware_class", "declared_per_run"),
        },
        "benchmarks": [
            {
                "benchmark_id": row["benchmark_id"],
                "benchmark_digest": row["expected_digest"],
            }
            for row, _ in benchmarks
        ],
        "runs": matrix_rows,
        "summary": {
            "configured_runs": len(matrix_rows),
            "readiness_passed": sum(bool(row["readiness"].get("reachable")) for row in matrix_rows),
            "bounded_operations_executed": sum(bool(row["bounded_operation"].get("executed")) for row in matrix_rows),
            "quality_validated_runs": successful,
            "quality_failed_or_incomplete_runs": len(matrix_rows) - successful,
            "independent_server_implementations": len(
                {row["server_implementation"] for row in matrix_rows if row["quality_validated"]}
            ),
        },
        "truth_boundary": {
            "availability_is_quality": False,
            "retrieval_alignment_is_funniness": False,
            "historical_translation_alignment_is_modern_native_review": False,
            "default_provider_recommendation_made": False,
            "allowed_claim": "provider compatibility and retrieval quality on the exact frozen proxy tasks only",
        },
    }
    serialized = json.dumps(receipt, sort_keys=True, ensure_ascii=False)
    receipt["secret_scan"] = {
        "configured_secret_count": len(configured_secrets),
        "secrets_absent": all(secret not in serialized for secret in configured_secrets),
    }
    receipt["ok"] = receipt["secret_scan"]["secrets_absent"] and successful > 0
    receipt["receipt_digest"] = _canonical_digest(
        {
            **receipt,
            "runs": [
                {
                    **row,
                    "quality_benchmarks": {
                        benchmark_id: {
                            key: value
                            for key, value in benchmark.items()
                            if key != "duration_seconds" and key != "model"
                        }
                        for benchmark_id, benchmark in row["quality_benchmarks"].items()
                    },
                }
                for row in receipt["runs"]
            ],
        }
    )
    return receipt


def write_provider_matrix(path: Path, receipt: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path
