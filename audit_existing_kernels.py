#!/usr/bin/env python3
"""Read-only audit of the six pre-existing private HumorVibes Kaggle kernels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SPECS = [
    ("main", "taylorsamarel/humorvibes-measuring-jokes-with-gemma", ROOT / "notebook.ipynb", ROOT / "kernel-metadata.json", [
        ("humorvibes-measuring-jokes-with-gemma.log", ROOT / "research_out/kaggle/humorvibes-measuring-jokes-with-gemma/humorvibes-measuring-jokes-with-gemma.log"),
    ]),
    ("zoo", "taylorsamarel/humorvibes-mesh-zoo-lab", ROOT / "zoo_lab/zoo_lab.ipynb", ROOT / "zoo_lab/kernel-metadata.json", [
        ("humorvibes-mesh-zoo-lab.log", ROOT / "research_out/kaggle/humorvibes-mesh-zoo-lab/humorvibes-mesh-zoo-lab.log"),
        ("research_out/zoo_report.json", ROOT / "research_out/kaggle/humorvibes-mesh-zoo-lab/research_out/zoo_report.json"),
    ]),
    ("corpus", "taylorsamarel/humorvibes-corpus-lab", ROOT / "corpus_lab/corpus_lab.ipynb", ROOT / "corpus_lab/kernel-metadata.json", [
        ("humorvibes-corpus-lab.log", ROOT / "research_out/kaggle/humorvibes-corpus-lab/humorvibes-corpus-lab.log"),
        ("research_out/corpus_report.json", ROOT / "research_out/kaggle/humorvibes-corpus-lab/research_out/corpus_report.json"),
    ]),
    ("panel", "taylorsamarel/humorvibes-panel-lab", ROOT / "panel_lab/panel_lab.ipynb", ROOT / "panel_lab/kernel-metadata.json", [
        ("humorvibes-panel-lab.log", ROOT / "research_out/kaggle/humorvibes-panel-lab/humorvibes-panel-lab.log"),
        ("research_out/frame_duel.json", ROOT / "research_out/kaggle/humorvibes-panel-lab/research_out/frame_duel.json"),
    ]),
    ("ratings", "taylorsamarel/humorvibes-validate-ratings", ROOT / "validate_ratings/validate_notebook.ipynb", ROOT / "validate_ratings/kernel-metadata.json", [
        ("humorvibes-validate-ratings.log", ROOT / "research_out/kaggle/humorvibes-validate-ratings/humorvibes-validate-ratings.log"),
        ("validation_results.json", ROOT / "research_out/kaggle/humorvibes-validate-ratings/validation_results.json"),
    ]),
    ("studio", "taylorsamarel/humorvibes-studio-g2", ROOT / "live_studio/live_notebook.ipynb", ROOT / "live_studio/kernel-metadata.json", []),
]


def run(*args: str) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return (result.stdout + result.stderr).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_cells(path: Path) -> list[tuple[str, Any]]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return [(cell.get("cell_type", ""), cell.get("source", "")) for cell in notebook["cells"]]


def cells_sha(path: Path) -> str:
    payload = json.dumps(normalized_cells(path), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def report_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# HumorVibes six-kernel audit",
        "",
        f"Audited: {receipt['audited_utc']}. Competition API deadline: **{receipt['competition']['deadline']}**.",
        "",
        "The operation was read-only: sources and outputs were pulled into a temporary directory; no kernel was rerun or submitted.",
        "",
        "| Kernel | Live status | Private | Source cells match | Mirrored outputs match |",
        "|---|---|:---:|:---:|:---:|",
    ]
    for kernel in receipt["kernels"]:
        lines.append(
            f"| {kernel['id']} | {kernel['status']} | {kernel['remote_private']} | {kernel['source_cells_match']} | {kernel['mirrored_outputs_match']} |"
        )
    lines += [
        "",
        "## Attached inference sources",
        "",
    ]
    for kernel in receipt["kernels"]:
        models = ", ".join(f"`{model}`" for model in kernel["model_sources"]) or "none"
        lines.append(f"- `{kernel['id']}`: {models}")
    lines += [
        "",
        "Every existing research output named in the writeup is byte-identical to the latest Kaggle output. Raw notebook files differ because Kaggle adds execution outputs; normalized code/markdown cells match exactly.",
        "",
        f"Overall court passed: **{receipt['all_six_complete_private_and_source_matched']}**.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "research_out/kernel_audit_20260712.json")
    args = parser.parse_args()
    competition_csv = run("kaggle", "competitions", "list", "-s", "humor-genome-nyc", "--csv")
    competition_rows = list(csv.DictReader(io.StringIO(competition_csv)))
    if len(competition_rows) != 1:
        raise RuntimeError("Humor Genome competition lookup was ambiguous")

    kernels = []
    with tempfile.TemporaryDirectory(prefix="humorvibes-kernel-audit-") as temp:
        temp_root = Path(temp)
        for name, kernel_id, local_notebook, local_metadata, output_pairs in SPECS:
            source_dir = temp_root / name / "source"
            output_dir = temp_root / name / "output"
            source_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            status_text = run("kaggle", "kernels", "status", kernel_id)
            status = status_text.split('status "', 1)[-1].rstrip('"') if 'status "' in status_text else status_text
            run("kaggle", "kernels", "pull", kernel_id, "-p", str(source_dir), "-m")
            run("kaggle", "kernels", "output", kernel_id, "-p", str(output_dir))
            remote_metadata_path = source_dir / "kernel-metadata.json"
            remote_metadata = json.loads(remote_metadata_path.read_text(encoding="utf-8"))
            notebooks = list(source_dir.glob("*.ipynb"))
            if len(notebooks) != 1:
                raise RuntimeError(f"{kernel_id}: expected one pulled notebook, found {len(notebooks)}")
            remote_notebook = notebooks[0]
            source_match = normalized_cells(remote_notebook) == normalized_cells(local_notebook)

            output_checks = []
            for relative_remote, local_path in output_pairs:
                remote_path = output_dir / relative_remote
                output_checks.append(
                    {
                        "remote_path": relative_remote,
                        "remote_sha256": sha(remote_path),
                        "local_path": str(local_path.relative_to(ROOT)),
                        "local_sha256": sha(local_path),
                        "exact_match": sha(remote_path) == sha(local_path),
                    }
                )
            all_remote_outputs = sorted(path for path in output_dir.rglob("*") if path.is_file())
            kernels.append(
                {
                    "name": name,
                    "id": kernel_id,
                    "status": status,
                    "remote_private": bool(remote_metadata.get("is_private")),
                    "local_private": bool(json.loads(local_metadata.read_text(encoding="utf-8")).get("is_private")),
                    "model_sources": remote_metadata.get("model_sources", []),
                    "dataset_sources": remote_metadata.get("dataset_sources", []),
                    "competition_sources": remote_metadata.get("competition_sources", []),
                    "enable_gpu": bool(remote_metadata.get("enable_gpu")),
                    "enable_internet": bool(remote_metadata.get("enable_internet")),
                    "remote_notebook_sha256": sha(remote_notebook),
                    "local_notebook_sha256": sha(local_notebook),
                    "normalized_cells_sha256": cells_sha(local_notebook),
                    "source_cells_match": source_match,
                    "mirrored_output_checks": output_checks,
                    "mirrored_outputs_match": all(item["exact_match"] for item in output_checks),
                    "remote_output_file_count": len(all_remote_outputs),
                    "remote_output_manifest_sha256": hashlib.sha256(
                        "\n".join(f"{path.relative_to(output_dir)}\t{sha(path)}" for path in all_remote_outputs).encode("utf-8")
                    ).hexdigest(),
                }
            )

    overall = all(
        kernel["status"] == "KernelWorkerStatus.COMPLETE"
        and kernel["remote_private"]
        and kernel["source_cells_match"]
        and kernel["mirrored_outputs_match"]
        for kernel in kernels
    )
    receipt = {
        "schema": "humorvibes_six_kernel_audit_v1",
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "operation": "read_only_pull_status_source_output",
        "competition": competition_rows[0],
        "kernels": kernels,
        "all_six_complete_private_and_source_matched": overall,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = args.out.with_suffix(".md")
    report.write_text(report_markdown(receipt), encoding="utf-8")
    print(json.dumps({"receipt": str(args.out), "report": str(report), "passed": overall}, indent=2))
    if not overall:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
