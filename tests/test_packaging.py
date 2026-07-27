"""Static deployment contracts that do not require Docker or Kubernetes daemons."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str) -> dict:
    value = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_dockerfile_is_multi_stage_nonroot_and_health_checked() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert " AS builder" in text and " AS runtime" in text
    assert "USER 10001:10001" in text
    assert "HEALTHCHECK" in text and "/health/live" in text
    assert 'ENTRYPOINT ["humorvibes-api"]' in text
    assert "HUMORVIBES_HOST=0.0.0.0" in text
    assert "requirements-api.lock" in text and "--requirement requirements-api.lock" in text
    assert "python:3.12-slim@sha256:" in text
    assert "COPY ." not in text
    assert "OLLAMA_API_KEY" not in text


def test_docker_context_is_allowlist_shaped() -> None:
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "**"
    assert "!humorvibes/**" in lines
    assert "!requirements-api.lock" in lines
    assert "!formats.py" in lines and "!humor_mesh.py" in lines and "!mesh_signals.py" in lines


def test_compose_defaults_are_local_offline_and_hardened() -> None:
    compose = load_yaml("compose.yaml")
    api = compose["services"]["api"]
    assert api["ports"][0].startswith("${HUMORVIBES_BIND_ADDRESS:-127.0.0.1}")
    assert api["environment"]["HUMORVIBES_LLM_DEFAULT"] == "offline"
    assert api["environment"]["HUMORVIBES_EMBEDDING_DEFAULT"] == "hash:128"
    assert api["read_only"] is True
    assert "ALL" in api["cap_drop"]
    assert "no-new-privileges:true" in api["security_opt"]


def test_ollama_compose_uses_batch_capable_model_and_no_literal_key() -> None:
    local = load_yaml("compose.ollama.yaml")
    assert local["services"]["api"]["environment"]["OLLAMA_HOST"] == "http://ollama:11434"
    assert local["services"]["ollama"]["image"] == "ollama/ollama:0.32.4"
    assert local["services"]["model-loader"]["image"] == "ollama/ollama:0.32.4"
    assert "embeddinggemma" in local["services"]["api"]["environment"]["HUMORVIBES_OLLAMA_EMBED_MODELS"]
    cloud_text = (ROOT / "compose.ollama-cloud.yaml").read_text(encoding="utf-8")
    assert "https://ollama.com" in cloud_text
    assert "${OLLAMA_API_KEY:?" in cloud_text
    assert not re.search(r"OLLAMA_API_KEY:\s+[A-Za-z0-9_-]{16,}\s*$", cloud_text, re.MULTILINE)


def test_kubernetes_deployment_has_probes_resources_and_restricted_identity() -> None:
    deployment = load_yaml("deploy/kubernetes/deployment.yaml")
    assert deployment["kind"] == "Deployment"
    spec = deployment["spec"]["template"]["spec"]
    assert spec["automountServiceAccountToken"] is False
    assert spec["securityContext"]["runAsNonRoot"] is True
    assert spec["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
    container = spec["containers"][0]
    assert container["startupProbe"]["httpGet"]["path"] == "/health/live"
    assert container["livenessProbe"]["httpGet"]["path"] == "/health/live"
    assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"
    assert container["resources"]["requests"] and container["resources"]["limits"]
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]


def test_kubernetes_base_is_default_deny_on_egress() -> None:
    policy = load_yaml("deploy/kubernetes/networkpolicy.yaml")
    assert policy["kind"] == "NetworkPolicy"
    assert set(policy["spec"]["policyTypes"]) == {"Ingress", "Egress"}
    assert policy["spec"]["egress"] == []
    kustomization = load_yaml("deploy/kubernetes/kustomization.yaml")
    assert "networkpolicy.yaml" in kustomization["resources"]


def test_envoy_gateway_example_has_tls_identity_global_limit_and_no_secrets() -> None:
    text = (ROOT / "deploy/gateway/envoy-gateway.yaml").read_text(encoding="utf-8")
    rows = list(yaml.safe_load_all(text))
    by_kind = {row["kind"]: row for row in rows}
    assert set(by_kind) == {
        "Gateway",
        "HTTPRoute",
        "SecurityPolicy",
        "BackendTrafficPolicy",
        "ClientTrafficPolicy",
    }
    listener = by_kind["Gateway"]["spec"]["listeners"][0]
    assert listener["protocol"] == "HTTPS" and listener["tls"]["mode"] == "Terminate"
    assert by_kind["SecurityPolicy"]["spec"]["apiKeyAuth"]["extractFrom"][0]["headers"] == ["x-api-key"]
    rate = by_kind["BackendTrafficPolicy"]["spec"]["rateLimit"]
    assert rate["local"]["rules"] and rate["global"]["rules"]
    assert by_kind["ClientTrafficPolicy"]["spec"]["tls"]["minVersion"] == "1.3"
    assert "stringData:" not in text and "supersecret" not in text


def test_container_publish_workflow_is_multiarch_sbom_and_attested() -> None:
    text = (ROOT / ".github/workflows/publish-container.yml").read_text(encoding="utf-8")
    assert "linux/amd64,linux/arm64" in text
    assert "provenance: mode=max" in text and "sbom: true" in text
    assert "packages: write" in text and "attestations: write" in text and "id-token: write" in text
    assert "subject-digest: ${{ steps.build.outputs.digest }}" in text
    assert "@v" not in "\n".join(line for line in text.splitlines() if "uses:" in line)


def test_kubernetes_config_contains_no_secret_values_and_stays_cluster_internal() -> None:
    config = load_yaml("deploy/kubernetes/configmap.yaml")
    assert all("KEY" not in key and "SECRET" not in key for key in config["data"])
    service = load_yaml("deploy/kubernetes/service.yaml")
    assert service["spec"]["type"] == "ClusterIP"
    deployment_text = (ROOT / "deploy/kubernetes/deployment.yaml").read_text(encoding="utf-8")
    assert "optional: true" in deployment_text
    assert "value: sk-" not in deployment_text


def test_helm_chart_preserves_secure_defaults_and_supports_image_digests() -> None:
    chart = load_yaml("deploy/helm/humorvibes/Chart.yaml")
    values = load_yaml("deploy/helm/humorvibes/values.yaml")
    schema = load_yaml("deploy/helm/humorvibes/values.schema.json")
    deployment = (ROOT / "deploy/helm/humorvibes/templates/deployment.yaml").read_text(
        encoding="utf-8"
    )
    templates = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "deploy/helm/humorvibes/templates").glob("*.yaml"))
    )
    assert chart["version"] == "0.7.0" and chart["appVersion"] == "0.7.0"
    assert values["replicaCount"] == 2
    assert values["service"]["type"] == "ClusterIP"
    assert values["podSecurityContext"]["runAsNonRoot"] is True
    assert values["securityContext"]["readOnlyRootFilesystem"] is True
    assert values["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert values["image"]["tag"] == "0.7.0" and values["image"]["digest"] == ""
    digest_schema = schema["properties"]["image"]["properties"]["digest"]
    assert "sha256" in digest_schema["pattern"]
    assert "@{{ .Values.image.digest }}" in deployment
    assert "automountServiceAccountToken: false" in deployment
    assert "existingSecret" in deployment
    assert "kind: Ingress" not in templates and "kind: Secret" not in templates
    assert "HUMORVIBES_API_KEY" not in templates and "OLLAMA_API_KEY" not in templates


def test_helm_documentation_has_no_unresolved_release_placeholder() -> None:
    text = (ROOT / "deploy/helm/humorvibes/README.md").read_text(encoding="utf-8")
    assert "REPLACE_WITH" not in text
    assert "image.digest" in text and "docker buildx imagetools inspect" in text


def test_legacy_ollama_embedding_scripts_no_longer_use_singular_endpoint() -> None:
    retired_endpoint = "/api/" + "embeddings"
    offenders = []
    for path in ROOT.rglob("*.py"):
        if any(part in {".venv", ".git"} for part in path.parts):
            continue
        if retired_endpoint in path.read_text(encoding="utf-8", errors="replace"):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_container_runtime_lock_matches_uv_export() -> None:
    import subprocess

    rendered = subprocess.run(
        [
            "uv", "export", "--frozen", "--extra", "api", "--extra", "telemetry", "--no-dev",
            "--no-emit-project", "--no-hashes",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    assert rendered == (ROOT / "requirements-api.lock").read_text(encoding="utf-8")


def test_deployment_verifier_builds_current_source_by_default() -> None:
    text = (ROOT / "verify_deployment.py").read_text(encoding="utf-8")
    assert 'command("docker", "build", "--tag", image, ".")' in text
    assert '"built_from_current_source": build' in text
    assert '"--no-build"' in text
    assert '"--helm-image"' in text
    assert '"helm_render_executed"' in text


def test_ci_container_audit_reuses_the_compose_image_without_version_drift() -> None:
    workflow = (ROOT / ".github/workflows/app-contracts.yml").read_text(encoding="utf-8")
    assert "docker compose run --rm --no-deps --entrypoint humorvibes api adversarial" in workflow
    assert not re.search(r"--entrypoint humorvibes humorvibes-research:[^ ]+ adversarial", workflow)


def test_release_metadata_is_versioned_citable_and_archive_ready() -> None:
    citation = load_yaml("CITATION.cff")
    archive = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    release = (ROOT / "RELEASE_NOTES_v0.7.0.md").read_text(encoding="utf-8")
    assert citation["cff-version"] == "1.2.0"
    assert citation["version"] == "0.7.0" and citation["license"] == "Apache-2.0"
    assert citation["repository-code"] == "https://github.com/aidonerightcorp/humorvibes-jestry"
    assert archive["license"] == "Apache-2.0" and archive["upload_type"] == "software"
    assert archive["creators"] and archive["related_identifiers"]
    assert "0.7.x" in security and "Python 3.10-3.14" in security
    assert "186 tests pass" in release and "DOI is not fabricated" in release


def test_release_candidate_receipt_resolves_every_recorded_digest() -> None:
    candidate = json.loads(
        (ROOT / "jestry_out/v0_7_0_release_candidate.json").read_text(encoding="utf-8")
    )
    deployment = json.loads(
        (ROOT / "jestry_out/deployment_validation.json").read_text(encoding="utf-8")
    )
    assert candidate["ok"] is True
    assert candidate["release"]["state"] == "validated_release_candidate"
    assert candidate["verification"]["deployment"]["source_tree_sha256"] == deployment[
        "source"
    ]["source_tree_sha256"]
    recorded: dict[str, str] = {}
    recorded.update(candidate["verification"]["clean_install"]["receipt_sha256"])
    recorded["jestry_out/deployment_validation.json"] = candidate["verification"][
        "deployment"
    ]["receipt_sha256"]
    recorded["jestry_out/provider_compatibility_offline.json"] = candidate["verification"][
        "provider_compatibility"
    ]["offline_receipt_sha256"]
    recorded["jestry_out/provider_compatibility_live.json"] = candidate["verification"][
        "provider_compatibility"
    ]["live_receipt_sha256"]
    for relative, expected in recorded.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
