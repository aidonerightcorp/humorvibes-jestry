"""The committed static ceiling-demo notebook is reproducible from its builder.

The published kernel (taylorsamarel/humorvibes-what-the-label-can-support) is
built by ``ceiling_demo/build_demo_notebook.py --static``. These tests pin the
contract: deterministic bytes, no live-session machinery in the static
edition, and embedded receipt stamps that match the committed receipts.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "ceiling_demo" / "build_demo_notebook.py"
NOTEBOOK = ROOT / "ceiling_demo" / "humorvibes_ceiling_demo_static.ipynb"


def _rebuild() -> bytes:
    subprocess.run([sys.executable, str(BUILDER), "--static"],
                   check=True, cwd=ROOT, capture_output=True)
    return NOTEBOOK.read_bytes()


def test_static_build_is_deterministic_and_matches_committed(tmp_path) -> None:
    committed = NOTEBOOK.read_bytes()
    first = _rebuild()
    second = _rebuild()
    assert first == second, "static build is not deterministic"
    assert first == committed, "committed static notebook drifted from its builder"


def test_static_edition_has_no_live_machinery() -> None:
    nb = json.loads(NOTEBOOK.read_text())
    sources = ["".join(c["source"]) for c in nb["cells"]]
    joined = "\n".join(sources)
    for banned in ("cloudflared", "ntfy", "KEEPALIVE", "trycloudflare"):
        assert banned not in joined, banned
    assert any("static public edition" in s for s in sources)
    assert any("Where this sits" in s for s in sources)
    assert any("controlled prediction " in s for s in sources)


def test_embedded_receipt_stamps_match_disk() -> None:
    nb = json.loads(NOTEBOOK.read_text())
    code = next(s for s in ("".join(c["source"]) for c in nb["cells"])
                if "RECEIPTS = json.loads" in s)
    blob = code.split("json.loads(r'''", 1)[1].rsplit("''')", 1)[0]
    receipts = json.loads(blob)
    stamps = receipts["_provenance"]["receipt_files"]
    assert stamps, "no receipt stamps embedded"
    for fname, stamp in stamps.items():
        path = ROOT / "jestry_out" / fname
        assert path.exists(), fname
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        assert digest == stamp["sha256_12"], (
            f"{fname}: committed receipt changed after the notebook was built — "
            "rebuild with build_demo_notebook.py --static")
