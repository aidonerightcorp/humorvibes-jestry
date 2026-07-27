#!/usr/bin/env python3
"""Validate SDK, API, Compose, Kubernetes, and an optional built container."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from humorvibes.adversarial import run_adversarial_suite
from humorvibes.client import HumorVibesClient
from humorvibes.config import Settings
from humorvibes.service import HumorVibesService
from humorvibes.studies import synthetic_demo_receipt

ROOT = Path(__file__).resolve().parent


def source_manifest() -> dict[str, Any]:
    paths = [
        ROOT / ".dockerignore",
        ROOT / "Dockerfile",
        ROOT / "compose.yaml",
        ROOT / "compose.ollama.yaml",
        ROOT / "compose.ollama-cloud.yaml",
        ROOT / "deploy/kubernetes/configmap.yaml",
        ROOT / "deploy/kubernetes/deployment.yaml",
        ROOT / "deploy/kubernetes/kustomization.yaml",
        ROOT / "deploy/kubernetes/service.yaml",
        ROOT / "docs/openapi.json",
        ROOT / "formats.py",
        ROOT / "humor_mesh.py",
        ROOT / "mesh_signals.py",
        ROOT / "pyproject.toml",
        ROOT / "requirements-api.lock",
        ROOT / "uv.lock",
        ROOT / "verify_deployment.py",
        *sorted(
            path
            for path in (ROOT / "deploy/helm/humorvibes").rglob("*")
            if path.is_file()
        ),
        *sorted((ROOT / "humorvibes").glob("*.py")),
    ]
    hashes = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    joined = "".join(f"{name}\0{digest}\n" for name, digest in sorted(hashes.items()))
    return {
        "source_tree_sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
        "files": hashes,
    }


def command(*args: str) -> str:
    result = subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def check(name: str, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return {"name": name, "ok": True, "evidence": action()}
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "evidence": {"error_type": type(exc).__name__, "message": str(exc)[:300]},
        }


def verify_sdk() -> dict[str, Any]:
    service = HumorVibesService(Settings.from_env({}))
    embedded = service.embed(["comic timing", "timing a joke"])
    compared = service.similarity(["same text"], ["same text"])
    study = synthetic_demo_receipt()
    assert service.ready()["ok"]
    assert embedded["model_id"] == "hash:128" and embedded["count"] == 2
    assert compared["cosine_similarity"] == [[1.0]]
    assert study["claim_gate"]["claim_ready"] is False
    return {
        "ready": True,
        "embedding_model": "hash:128",
        "embedding_count": 2,
        "synthetic_study_evidence_level": study["evidence_level"],
        "synthetic_study_claim_ready": False,
    }


def verify_adversarial() -> dict[str, Any]:
    audit = run_adversarial_suite()
    if not audit["ok"]:
        raise RuntimeError("adversarial audit failed")
    return {"passed": audit["passed"], "total": audit["total"]}


def verify_compose() -> dict[str, Any]:
    command("docker", "compose", "-f", "compose.yaml", "config", "--quiet")
    command("docker", "compose", "-f", "compose.yaml", "-f", "compose.ollama.yaml", "config", "--quiet")
    return {"offline_profile": "valid", "local_ollama_overlay": "valid"}


def verify_kubernetes() -> dict[str, Any]:
    paths = [
        ROOT / "deploy/kubernetes/configmap.yaml",
        ROOT / "deploy/kubernetes/deployment.yaml",
        ROOT / "deploy/kubernetes/networkpolicy.yaml",
        ROOT / "deploy/kubernetes/service.yaml",
        ROOT / "deploy/kubernetes/kustomization.yaml",
    ]
    documents = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in paths]
    assert all(isinstance(document, dict) and document.get("apiVersion") for document in documents)
    deployment = next(document for document in documents if document.get("kind") == "Deployment")
    service = next(document for document in documents if document.get("kind") == "Service")
    network_policy = next(
        document for document in documents if document.get("kind") == "NetworkPolicy"
    )
    pod = deployment["spec"]["template"]["spec"]
    container = pod["containers"][0]
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert service["spec"]["type"] == "ClusterIP"
    assert network_policy["spec"]["egress"] == []
    return {
        "objects": [document["kind"] for document in documents],
        "replicas": deployment["spec"]["replicas"],
        "service_type": service["spec"]["type"],
        "nonroot": True,
        "readonly_root": True,
        "default_deny_egress": True,
    }


def verify_kustomize_container(image: str) -> dict[str, Any]:
    rendered = command(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{ROOT}:/workspace:ro",
        "--entrypoint",
        "kubectl",
        image,
        "kustomize",
        "/workspace/deploy/kubernetes",
    )
    documents = list(yaml.safe_load_all(rendered))
    identities = [f"{row['kind']}/{row['metadata']['name']}" for row in documents]
    assert identities == [
        "ConfigMap/humorvibes-config",
        "Service/humorvibes",
        "Deployment/humorvibes",
        "NetworkPolicy/humorvibes-default-deny",
    ]
    return {"image": image, "objects": identities, "rendered": True}


def verify_helm_container(image: str) -> dict[str, Any]:
    chart = "/workspace/deploy/helm/humorvibes"
    command(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{ROOT}:/workspace:ro",
        "--workdir",
        "/workspace",
        image,
        "lint",
        chart,
    )
    rendered = command(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{ROOT}:/workspace:ro",
        "--workdir",
        "/workspace",
        image,
        "template",
        "receipt",
        chart,
    )
    documents = [row for row in yaml.safe_load_all(rendered) if row]
    identities = [f"{row['kind']}/{row['metadata']['name']}" for row in documents]
    assert identities == [
        "NetworkPolicy/receipt-humorvibes",
        "ConfigMap/receipt-humorvibes",
        "Service/receipt-humorvibes",
        "Deployment/receipt-humorvibes",
    ]
    deployment = documents[-1]
    pod = deployment["spec"]["template"]["spec"]
    container = pod["containers"][0]
    assert pod["automountServiceAccountToken"] is False
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["image"] == "humorvibes-research:0.8.0"
    return {
        "image": image,
        "objects": identities,
        "linted": True,
        "rendered": True,
        "nonroot": pod["securityContext"]["runAsNonRoot"],
        "readonly_root": container["securityContext"]["readOnlyRootFilesystem"],
    }


def json_call(base: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base}{path}", data=body, headers=headers, method="POST" if body else "GET"
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        value = json.loads(response.read().decode("utf-8"))
    assert isinstance(value, dict)
    return value


def verify_container(image: str, *, build: bool = True) -> dict[str, Any]:
    built_image_id = ""
    if build:
        command("docker", "build", "--tag", image, ".")
        built_image_id = command(
            "docker", "image", "inspect", "--format", "{{.Id}}", image
        )
    name = f"humorvibes-verify-{os.getpid()}"
    container_id = ""
    try:
        container_id = command(
            "docker", "run", "--rm", "--detach",
            "--name", name,
            "--read-only",
            "--tmpfs", "/tmp:rw,size=64m,mode=1777",
            "--publish", "127.0.0.1::8080",
            image,
        )
        port_text = command("docker", "port", name, "8080/tcp")
        port = int(port_text.rsplit(":", 1)[1])
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 30
        last_error = "not started"
        while time.monotonic() < deadline:
            try:
                if json_call(base, "/health/ready").get("ok"):
                    break
            except Exception as exc:
                last_error = type(exc).__name__
                time.sleep(0.25)
        else:
            raise RuntimeError(f"container readiness timed out: {last_error}")

        remote = HumorVibesClient(base, timeout=5)
        capabilities = remote.capabilities()
        remote_similarity = remote.similarity(["same text"], ["same text"])
        openapi = json_call(base, "/openapi.json")
        embedded = json_call(base, "/v1/embed", {"texts": ["container smoke test"]})
        signals = json_call(
            base,
            "/v1/signals",
            {"setup": "A setup establishes a frame.", "punchline": "Then the frame turns."},
        )
        study_template = json_call(base, "/v1/research/study-template")
        controls_metadata = remote.open_controls_metadata()
        controls_sample = remote.open_controls_sample(
            count=4,
            arm="surprising_resolved",
            split="test",
        )
        inspection = json.loads(command("docker", "inspect", name))[0]
        if built_image_id:
            assert inspection["Image"] == built_image_id
        assert inspection["Config"]["User"] == "10001:10001"
        assert inspection["HostConfig"]["ReadonlyRootfs"] is True
        assert embedded["model_id"] == "hash:128" and embedded["count"] == 1
        assert remote_similarity["cosine_similarity"] == [[1.0]]
        assert openapi["info"]["version"] == "0.8.0"
        assert capabilities["truth_boundary"]["generation_is_not_human_validation"] is True
        assert capabilities["product_use_cases"]["creative_assistance"]["claim_gate"] == (
            "blind_or_live_human_response"
        )
        assert signals["truth_boundary"]["teacher_forced_logprobs_measured"] is False
        assert study_template["privacy_boundary"]["analysis_upload_endpoint"] is False
        assert controls_metadata["maximum_rows"] == 120_000
        assert controls_metadata["truth_boundary"]["human_rated"] is False
        assert controls_sample["count"] == 4
        assert controls_sample["truth_boundary"]["model_generated"] is False
        return {
            "image": image,
            "image_id": inspection["Image"],
            "built_from_current_source": build,
            "user": inspection["Config"]["User"],
            "readonly_root": inspection["HostConfig"]["ReadonlyRootfs"],
            "ready": True,
            "embedding_model": embedded["model_id"],
            "endpoints_checked": [
                "/health/ready",
                "/openapi.json",
                "/v1/capabilities",
                "/v1/embed",
                "/v1/similarity",
                "/v1/signals",
                "/v1/research/study-template",
                "/v1/open-controls/metadata",
                "/v1/open-controls/sample",
            ],
            "offline_signals_measured": False,
        }
    finally:
        if container_id:
            subprocess.run(
                ["docker", "stop", "--time", "3", name],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docker",
        action="store_true",
        help="also build, launch, and probe the image",
    )
    parser.add_argument("--image", default="humorvibes-research:0.8.0")
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="with --docker, probe an existing image instead of building current source",
    )
    parser.add_argument(
        "--kustomize-image",
        default="",
        help="also render the manifests with kubectl from this container image",
    )
    parser.add_argument(
        "--helm-image",
        default="",
        help="also lint and render the Helm chart with this container image",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    checks = [
        check("adversarial_contracts", verify_adversarial),
        check("offline_sdk", verify_sdk),
        check("compose_render", verify_compose),
        check("kubernetes_static_contract", verify_kubernetes),
    ]
    if args.docker:
        checks.append(
            check(
                "container_runtime",
                lambda: verify_container(args.image, build=not args.no_build),
            )
        )
    if args.kustomize_image:
        checks.append(check("kustomize_render", lambda: verify_kustomize_container(args.kustomize_image)))
    if args.helm_image:
        checks.append(check("helm_render", lambda: verify_helm_container(args.helm_image)))
    ok = all(row["ok"] for row in checks)
    receipt = {
        "receipt_type": "humorvibes_deployment_validation",
        "receipt_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "docker_executed": args.docker,
        "docker_build_executed": args.docker and not args.no_build,
        "source": source_manifest(),
        "environment": {
            "python": platform.python_version(),
            "docker_compose": command("docker", "compose", "version", "--short"),
        },
        "checks": checks,
        "truth_boundary": {
            "container_registry_publication_verified": False,
            "container_image_built_from_current_source": args.docker
            and not args.no_build,
            "kubernetes_cluster_apply_executed": False,
            "kustomize_render_executed": bool(args.kustomize_image),
            "helm_render_executed": bool(args.helm_image),
            "live_llm_or_semantic_embedding_called": False,
            "canonical_kaggle_measurement_changed": False,
        },
    }
    rendered = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        target = args.out if args.out.is_absolute() else ROOT / args.out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
