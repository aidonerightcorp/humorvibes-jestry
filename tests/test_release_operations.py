from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_surface_audit_offline_preserves_truth_boundaries() -> None:
    module = _load("public_release_audit", ROOT / "tools" / "public_release_audit.py")
    receipt = module.audit(live=False)
    assert receipt["ok"] is True
    assert receipt["mode"] == {
        "live": False,
        "manifest_downloads": False,
        "mutates_remote_state": False,
    }
    assert {row["name"] for row in receipt["checks"]} == {
        "wave2.local_receipt",
        "open_controls.local_receipt",
    }
    assert "human funniness" in receipt["truth_boundary"]["not_verified"]


def test_clean_install_matrix_matches_declared_python_range() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/app-contracts.yml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.10"' in project
    assert 'python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]' in workflow
    assert "tools/clean_install_smoke.py" in workflow
    assert "${{ matrix.python-version }}" in workflow


def test_publication_receipts_remain_machine_readable() -> None:
    for relative in (
        "jestry_out/wave2_publication.json",
        "jestry_out/open_controls_publication.json",
    ):
        payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert payload["receipt_type"].startswith("humor_genome_")
