#!/usr/bin/env python3
"""Build the private HumorVibes ablation-court Kaggle notebook."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main() -> None:
    pipeline = (HERE / "ablation_pipeline.py").read_text(encoding="utf-8")
    project = HERE.parent
    mesh_signals = (project / "mesh_signals.py").read_text(encoding="utf-8")
    humor_mesh = (project / "humor_mesh.py").read_text(encoding="utf-8")
    vendor_cell = (
        "import os\n"
        "from pathlib import Path\n"
        "source_dir = Path('/kaggle/working/humorvibes_source')\n"
        "source_dir.mkdir(parents=True, exist_ok=True)\n"
        f"(source_dir / 'mesh_signals.py').write_text({mesh_signals!r}, encoding='utf-8')\n"
        f"(source_dir / 'humor_mesh.py').write_text({humor_mesh!r}, encoding='utf-8')\n"
        "os.environ['HUMORVIBES_SOURCE_DIR'] = str(source_dir)\n"
        "print('vendored exact HumorVibes signal source:', source_dir)\n"
    )
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "cells": [
            {
                "cell_type": "markdown",
                "id": "scope",
                "metadata": {},
                "source": (
                    "# HumorVibes S/R/E/B ablation court\n\n"
                    "A fail-closed judge-evidence run: fixed component ablations against real "
                    "Humicroedit human grades, paired original/shuffled controls, explicit failure "
                    "cases, and a runtime/provenance receipt. Gemma-2-2B supplies teacher-forced "
                    "log-probabilities and the declared bad-surprise persona judgment."
                ),
            },
            {
                "cell_type": "code",
                "id": "vendor-exact-source",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": vendor_cell,
            },
            {
                "cell_type": "code",
                "id": "run-court",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": pipeline,
            },
        ],
    }
    path = HERE / "ablation_notebook.ipynb"
    path.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    print(f"wrote {path} ({len(notebook['cells'])} cells; exact signal source embedded)")


if __name__ == "__main__":
    main()
