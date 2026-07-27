#!/usr/bin/env python3
"""Read-only cross-surface audit for the two public Humor Genome releases.

The default mode uses anonymous HTTP for visibility, the Kaggle CLI for terminal
status and manifest retrieval, and git ls-remote for public tag resolution. It
never mutates GitHub or Kaggle state.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/aidonerightcorp/humorvibes-jestry"
SURFACES = (
    {
        "name": "wave2",
        "receipt": "jestry_out/wave2_publication.json",
        "dataset": "taylorsamarel/humor-genome-wave2",
        "notebook": "taylorsamarel/humor-genome-wave-2-reproducible-gemma-study",
        "tag": "humor-genome-wave2-v9",
    },
    {
        "name": "open_controls",
        "receipt": "jestry_out/open_controls_publication.json",
        "dataset": "taylorsamarel/humor-genome-open-controls",
        "notebook": "taylorsamarel/humor-genome-open-controls-causal-design-lab",
        "tag": "humor-genome-open-controls-v2",
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _command(*args: str, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        list(args), cwd=cwd, check=True, capture_output=True, text=True, timeout=180
    )
    return completed.stdout.strip()


def _anonymous_json(url: str) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "humorvibes-public-audit/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return int(response.status), payload
    except urllib.error.HTTPError as exc:
        return int(exc.code), {}


def _anonymous_status(url: str) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "humorvibes-public-audit/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _manifest_hash_from_download(dataset: str) -> tuple[str, int]:
    with tempfile.TemporaryDirectory(prefix="humorvibes-public-audit-") as temporary:
        target = Path(temporary)
        _command(
            "kaggle",
            "datasets",
            "download",
            "-q",
            "-d",
            dataset,
            "-f",
            "manifest.json",
            "-p",
            str(target),
            "--force",
        )
        direct = target / "manifest.json"
        if direct.is_file():
            return _sha256(direct), direct.stat().st_size
        archives = sorted(target.glob("*.zip"))
        if len(archives) != 1:
            raise RuntimeError("Kaggle manifest download produced neither manifest.json nor one ZIP")
        with zipfile.ZipFile(archives[0]) as archive:
            names = [name for name in archive.namelist() if Path(name).name == "manifest.json"]
            if len(names) != 1:
                raise RuntimeError("Kaggle manifest archive does not contain exactly one manifest.json")
            payload = archive.read(names[0])
        return hashlib.sha256(payload).hexdigest(), len(payload)


def _receipt_facts(surface: dict[str, str], receipt: dict[str, Any]) -> tuple[str, bool]:
    if surface["name"] == "wave2":
        expected_hash = str(receipt["dataset"]["manifest_sha256"])
        public = receipt["dataset"]["is_private"] is False
    else:
        expected_hash = str(receipt["dataset"]["manifest_sha256"])
        public = receipt["dataset"]["public"] is True
    if len(expected_hash) != 64:
        raise ValueError(f"{surface['name']} publication receipt has an invalid manifest hash")
    return expected_hash, public


def audit(*, live: bool = True, download_manifests: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, evidence: Any) -> None:
        checks.append({"name": name, "ok": bool(ok), "evidence": evidence})

    for surface in SURFACES:
        receipt_path = ROOT / surface["receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        expected_manifest, receipt_public = _receipt_facts(surface, receipt)
        check(
            f"{surface['name']}.local_receipt",
            receipt_public,
            {"path": surface["receipt"], "manifest_sha256": expected_manifest},
        )
        if not live:
            continue

        dataset_status, dataset_payload = _anonymous_json(
            f"https://www.kaggle.com/api/v1/datasets/view/{surface['dataset']}"
        )
        check(
            f"{surface['name']}.anonymous_dataset",
            dataset_status == 200 and dataset_payload.get("isPrivate") is False,
            {"http_status": dataset_status, "is_private": dataset_payload.get("isPrivate")},
        )
        notebook_status = _anonymous_status(f"https://www.kaggle.com/code/{surface['notebook']}")
        check(
            f"{surface['name']}.anonymous_notebook",
            notebook_status == 200,
            {"http_status": notebook_status},
        )
        tag_status = _anonymous_status(f"{REPOSITORY}/tree/{surface['tag']}")
        check(
            f"{surface['name']}.anonymous_source_tag",
            tag_status == 200,
            {"http_status": tag_status, "tag": surface["tag"]},
        )

        status = json.loads(
            _command("kaggle", "datasets", "status", surface["dataset"], "--format", "json")
        )
        check(
            f"{surface['name']}.dataset_ready",
            status.get("status") == "ready",
            status,
        )
        kernel_status = _command("kaggle", "kernels", "status", surface["notebook"])
        check(
            f"{surface['name']}.notebook_complete",
            "KernelWorkerStatus.COMPLETE" in kernel_status,
            kernel_status,
        )
        remote_tags = _command(
            "git",
            "ls-remote",
            "--tags",
            REPOSITORY + ".git",
            f"refs/tags/{surface['tag']}",
            f"refs/tags/{surface['tag']}^{{}}",
        )
        check(
            f"{surface['name']}.remote_tag_resolves",
            bool(remote_tags.strip()),
            {"tag": surface["tag"], "refs": remote_tags.splitlines()},
        )
        if download_manifests:
            observed_hash, observed_bytes = _manifest_hash_from_download(surface["dataset"])
            check(
                f"{surface['name']}.downloaded_manifest",
                observed_hash == expected_manifest,
                {
                    "expected_sha256": expected_manifest,
                    "observed_sha256": observed_hash,
                    "bytes": observed_bytes,
                },
            )

    return {
        "receipt_type": "humorvibes_public_surface_audit",
        "receipt_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": {
            "live": live,
            "manifest_downloads": live and download_manifests,
            "mutates_remote_state": False,
        },
        "ok": all(row["ok"] for row in checks),
        "checks": checks,
        "truth_boundary": {
            "verified": "visibility, terminal service state, public tag resolution, and declared manifest identity",
            "not_verified": "scientific validity, human funniness, provider quality, or future availability",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="validate local publication receipts only")
    parser.add_argument(
        "--skip-manifest-download",
        action="store_true",
        help="skip the two small public manifest downloads",
    )
    parser.add_argument("--out", type=Path, help="optional JSON receipt path")
    args = parser.parse_args()
    result = audit(live=not args.offline, download_manifests=not args.skip_manifest_download)
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
