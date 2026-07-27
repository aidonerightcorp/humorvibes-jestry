"""Static deployment contracts that do not require Docker or Kubernetes daemons."""

from __future__ import annotations

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
    assert chart["version"] == "0.6.0" and chart["appVersion"] == "0.6.0"
    assert values["replicaCount"] == 2
    assert values["service"]["type"] == "ClusterIP"
    assert values["podSecurityContext"]["runAsNonRoot"] is True
    assert values["securityContext"]["readOnlyRootFilesystem"] is True
    assert values["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert values["image"]["tag"] == "0.6.0" and values["image"]["digest"] == ""
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
            "uv", "export", "--frozen", "--extra", "api", "--no-dev",
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
