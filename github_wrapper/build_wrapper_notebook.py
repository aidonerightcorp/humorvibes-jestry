"""Thin competition wrapper: clone the public GitHub repo, run the Jestry demo.

The Kaggle notebook carries no logic of its own — the single source of truth is
https://github.com/aidonerightcorp/humorvibes-jestry — it clones at session
start and runs a deterministic, judge-facing pass:

1. charter + honest registry census;
2. a zero-model replay route with its funnel receipt;
3. measured S/R/E on the canonical jokes + controls with the ATTACHED Gemma
   checkpoint (true teacher-forced logprobs, the certified instrument family);
4. the been-done precedent demo (offline hash backend, honestly labeled);
5. the competition pack's metric self-test + data build with self-attack checks.

Rebuild with `python3 build_wrapper_notebook.py`; push with
`kaggle kernels push -p github_wrapper/` (attached to humor-genome-nyc via
kernel-metadata competition_sources).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "https://github.com/aidonerightcorp/humorvibes-jestry"

CELLS: list[tuple[str, str]] = [
    ("markdown",
     "# HumorVibes / Jestry — competition demo (thin GitHub wrapper)\n\n"
     "All code lives in the public repo **" + REPO + "** — this notebook only "
     "clones it and runs the deterministic demo pass: the Jestry charter and registry, "
     "a zero-model replay route with its contribution-funnel receipt, measured "
     "S/R/E signals on canonical jokes and controls using the **attached Gemma** "
     "checkpoint (true teacher-forced log-probabilities), the multilingual "
     "been-done precedent check, and the Humor Vibes Open competition pack's "
     "metric self-test and anti-gaming data build.\n\n"
     "Theory: THEORY.md · Charter: JESTRY-CHARTER-AND-CONSTITUTION-2026-07-23.md · "
     "Writeups: WRITEUP.md, JESTRY_WRITEUP.md (all in the repo)."),
    ("code",
     "import os, subprocess, sys\n"
     "subprocess.run(['git', 'clone', '--depth', '1',\n"
     "                '" + REPO + "', '/kaggle/working/src'], check=True)\n"
     "os.chdir('/kaggle/working/src')\n"
     "os.environ['GEMMA_PROVIDER'] = 'transformers'   # attached checkpoint = real logprobs\n"
     "print('cloned', open('.git/HEAD').read().strip() if os.path.exists('.git/HEAD') else '')\n"
     "print(subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True,\n"
     "                     text=True).stdout.strip())\n"),
    ("code",
     "# 1) the charter and the honest registry census\n"
     "import subprocess, sys\n"
     "print(subprocess.run([sys.executable, 'jestry_cli.py', 'charter'],\n"
     "                     capture_output=True, text=True).stdout[:2600])\n"
     "print(subprocess.run([sys.executable, 'jestry_cli.py', 'cards'],\n"
     "                     capture_output=True, text=True).stdout)\n"),
    ("code",
     "# 2) zero-model replay route with a full contribution-funnel receipt\n"
     "print(subprocess.run([sys.executable, 'jestry_cli.py', 'run',\n"
     "                      'a joke about work deadlines', '--offline'],\n"
     "                     capture_output=True, text=True).stdout)\n"),
    ("code",
     "# 3) measured S/R/E with the attached Gemma (teacher-forced, full vocab)\n"
     "from mesh_signals import get_provider, compute_signals\n"
     "p = get_provider()\n"
     "print('instrument:', p.name)\n"
     "cases = [\n"
     "    ('I told my therapist about my fear of speed bumps.',\n"
     "     \"She said I'm slowly getting over it.\",\n"
     "     \"'Getting over it' is literal — the car physically drives over the speed bumps slowly.\"),\n"
     "    ('I told my therapist about my fear of speed bumps.',\n"
     "     'The quarterly cheese fondue regatta sailed backwards.', ''),\n"
     "    ('I told my therapist about my fear of speed bumps.',\n"
     "     'She said we can talk about it next week.', ''),\n"
     "]\n"
     "for setup, punch, frame in cases:\n"
     "    sig = compute_signals(p, setup, punch, frame_hint=frame or None)\n"
     "    print(f'S={sig.surprise_mean:5.2f} R_net={sig.resolution:5.2f} '\n"
     "          f'E={sig.efficiency:6.3f} measured={sig.measured} :: {punch[:44]}')\n"),
    ("code",
     "# 4) been-done precedent (offline hash backend — it says so itself)\n"
     "print(subprocess.run([sys.executable, 'jestry_cli.py', 'beendone',\n"
     "                      'Man plans and God laughs.', '--offline'],\n"
     "                     capture_output=True, text=True).stdout[:1800])\n"),
    ("code",
     "# 5) competition pack: metric self-test + anti-gaming data build\n"
     "print(subprocess.run([sys.executable, 'metric_humor_vibes.py'], cwd='competition',\n"
     "                     capture_output=True, text=True).stdout)\n"
     "print(subprocess.run([sys.executable, 'make_competition_data.py'], cwd='competition',\n"
     "                     capture_output=True, text=True).stdout[-900:])\n"),
]


def build() -> Path:
    cells = []
    for kind, src in CELLS:
        cell: dict = {"cell_type": kind, "metadata": {}, "source": src}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                      "name": "python3"},
                       "language_info": {"name": "python", "version": "3.11"}},
          "cells": cells}
    out = HERE / "jestry_demo_notebook.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
