#!/usr/bin/env python3
"""Harvest and verify the completed private HumorVibes ablation kernel."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAB = Path(__file__).resolve().parent
KERNEL_ID = "taylorsamarel/humorvibes-ablation-court"
DESTINATION = ROOT / "research_out/kaggle/humorvibes-ablation-court"
REQUIRED = [
    "ablation_rows.jsonl",
    "ablation_summary.json",
    "failure_cases.csv",
    "failure_cases.md",
    "ablation_failure_figure.png",
    "runtime_receipt.json",
    "humorvibes-ablation-court.log",
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


def normalized_cells(path: Path) -> list[tuple[str, object]]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return [(cell.get("cell_type", ""), cell.get("source", "")) for cell in notebook["cells"]]


def main() -> None:
    status_text = run("kaggle", "kernels", "status", KERNEL_ID)
    if 'status "KernelWorkerStatus.COMPLETE"' not in status_text:
        raise RuntimeError(f"Kernel is not COMPLETE: {status_text}")

    with tempfile.TemporaryDirectory(prefix="humorvibes-ablation-harvest-") as temp:
        temp_root = Path(temp)
        output_dir = temp_root / "output"
        source_dir = temp_root / "source"
        output_dir.mkdir()
        source_dir.mkdir()
        run("kaggle", "kernels", "output", KERNEL_ID, "-p", str(output_dir))
        run("kaggle", "kernels", "pull", KERNEL_ID, "-p", str(source_dir), "-m")
        missing = [name for name in REQUIRED if not (output_dir / name).exists()]
        if missing:
            raise RuntimeError(f"Completed kernel is missing required outputs: {missing}")

        summary = json.loads((output_dir / "ablation_summary.json").read_text(encoding="utf-8"))
        runtime = json.loads((output_dir / "runtime_receipt.json").read_text(encoding="utf-8"))
        if summary.get("status") != "complete" or runtime.get("status") != "complete":
            raise RuntimeError("Internal completion receipt is not complete")
        if summary.get("external_submission_made") is not False or runtime.get("external_submission_made") is not False:
            raise RuntimeError("Unexpected external-submission flag")
        if summary["sample"]["completion_rate"] < 0.95:
            raise RuntimeError("Measurement completion rate gate failed")
        for name, expected in runtime["outputs"].items():
            path = output_dir / name
            if sha(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
                raise RuntimeError(f"Runtime output hash mismatch: {name}")

        pulled_notebooks = list(source_dir.glob("*.ipynb"))
        if len(pulled_notebooks) != 1:
            raise RuntimeError("Expected exactly one pulled notebook")
        source_match = normalized_cells(pulled_notebooks[0]) == normalized_cells(LAB / "ablation_notebook.ipynb")
        if not source_match:
            raise RuntimeError("Pulled kernel source does not match the locally built notebook")
        remote_metadata = json.loads((source_dir / "kernel-metadata.json").read_text(encoding="utf-8"))
        if not remote_metadata.get("is_private"):
            raise RuntimeError("Ablation kernel unexpectedly became public")

        if DESTINATION.exists():
            shutil.rmtree(DESTINATION)
        DESTINATION.mkdir(parents=True)
        for name in REQUIRED:
            shutil.copy2(output_dir / name, DESTINATION / name)

    manifest = {
        "schema": "humorvibes_ablation_harvest_v1",
        "harvested_utc": datetime.now(timezone.utc).isoformat(),
        "kernel_id": KERNEL_ID,
        "kernel_status": "KernelWorkerStatus.COMPLETE",
        "kernel_private": True,
        "source_cells_match": True,
        "model_sources": remote_metadata.get("model_sources", []),
        "dataset_sources": remote_metadata.get("dataset_sources", []),
        "external_submission_made": False,
        "outputs": {
            name: {"bytes": (DESTINATION / name).stat().st_size, "sha256": sha(DESTINATION / name)}
            for name in REQUIRED
        },
    }
    receipt = DESTINATION / "harvest_receipt.json"
    receipt.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "destination": str(DESTINATION),
        "receipt": str(receipt),
        "receipt_sha256": sha(receipt),
        "summary": summary,
        "runtime_seconds": runtime["wall_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
