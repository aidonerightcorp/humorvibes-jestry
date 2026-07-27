#!/usr/bin/env python3
"""Build, install, and exercise HumorVibes in a disposable virtual environment.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return completed.stdout.strip()


def smoke(python: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="humorvibes-clean-install-") as temporary:
        root = Path(temporary)
        distribution = root / "dist"
        environment = root / "venv"
        _run(["uv", "build", "--wheel", "--out-dir", str(distribution)], cwd=ROOT)
        wheels = sorted(distribution.glob("humorvibes_research-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        _run(["uv", "venv", "--python", python, str(environment)], cwd=root)
        executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        _run(
            ["uv", "pip", "install", "--python", str(executable), f"{wheels[0]}[api]"],
            cwd=root,
        )
        isolated_env = dict(os.environ, PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
        probe = _run(
            [
                str(executable),
                "-c",
                (
                    "import importlib.metadata as m,json; "
                    "from humorvibes.api import app; "
                    "from humorvibes.open_controls import sample_rows; "
                    "files=[str(x) for x in m.files('humorvibes-research')]; "
                    "rows=sample_rows(4,arm='surprising_resolved',split='test'); "
                    "assert len(rows)==4 and app is not None; "
                    "assert any(x.endswith('licenses/LICENSE') for x in files); "
                    "assert any(x.endswith('licenses/LICENSE-DATA-OPEN-CONTROLS') for x in files); "
                    "print(json.dumps({'version':m.version('humorvibes-research'),'rows':len(rows)}))"
                ),
            ],
            cwd=root,
            env=isolated_env,
        )
        binary = environment / ("Scripts/humorvibes.exe" if os.name == "nt" else "bin/humorvibes")
        doctor = json.loads(_run([str(binary), "doctor"], cwd=root, env=isolated_env))
        controls = json.loads(_run([str(binary), "controls-info"], cwd=root, env=isolated_env))
        details = json.loads(probe)
        return {
            "ok": doctor["ok"] is True and controls["maximum_rows"] == 120_000,
            "python_requested": python,
            "python_runtime": _run(
                [str(executable), "-c", "import platform; print(platform.python_version())"],
                cwd=root,
                env=isolated_env,
            ),
            "package_version": details["version"],
            "sample_rows": details["rows"],
            "api_import": True,
            "licenses_present": True,
            "doctor_ok": doctor["ok"],
            "open_controls_maximum_rows": controls["maximum_rows"],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python executable or version for uv")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = smoke(args.python)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
