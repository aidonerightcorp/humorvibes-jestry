#!/usr/bin/env python3
"""Generate starter_notebook.ipynb for the Humor Vibes Open (Track A).

Mirrors the repo's build_notebook.py pattern (md/code cell helpers -> ipynb
JSON). The generated notebook is pure-stdlib (pandas optional, never required):
it locates the competition data, loads it with the csv module, prints EDA
counts, scores a trivial punctuation/length/overlap baseline, writes a valid
submission.csv, and self-scores with metric_humor_vibes.py imported by path.

Build:  python3 competition/launch/build_starter_notebook.py
Output: competition/launch/starter_notebook.ipynb
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

_counter = {"n": 0}


def _cid() -> str:
    _counter["n"] += 1
    return f"cell-{_counter['n']:02d}"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "id": _cid(), "metadata": {}, "source": source}


def code(source: str) -> dict:
    return {"cell_type": "code", "id": _cid(), "metadata": {}, "execution_count": None,
            "outputs": [], "source": source}


CELLS = [
    md(
        "# Humor Vibes Open — starter notebook (Track A)\n\n"
        "Pure-stdlib starter: no pandas, no torch, no internet required. It\n\n"
        "1. finds the competition data (Kaggle input or a local checkout),\n"
        "2. loads `train.csv` / `test.csv` with the `csv` module and prints quick EDA counts,\n"
        "3. scores a deliberately trivial punctuation/length/overlap heuristic,\n"
        "4. writes a **valid** `submission.csv` (`id,humor_score` for every test id),\n"
        "5. self-scores with the competition's own `metric_humor_vibes.py` on the labeled\n"
        "   train split (and on `solution.csv` when run host-side).\n\n"
        "**Task**: each test item is a (`setup`, `punchline`) pair. Submit a `humor_score`\n"
        "per id — higher = more likely a genuine human joke, lower = constructed control\n"
        "(a shuffled punchline from a different setup, or a deliberately boring tail).\n"
        "The metric is rank-based AUC, so only the *ordering* of your scores matters.\n\n"
        "The intended real baseline is Gemma-as-instrument (teacher-forced surprisal +\n"
        "null control) — see the competition description. This notebook is the floor,\n"
        "not the ceiling."
    ),
    code(
        "import csv, glob, os\n"
        "from pathlib import Path\n\n"
        "def find_data_dir():\n"
        "    hits = glob.glob('/kaggle/input/*/test.csv') + glob.glob('/kaggle/input/*/*/test.csv')\n"
        "    if hits:\n"
        "        return Path(sorted(hits)[0]).parent\n"
        "    for cand in ('competition/data', 'data', '../data', '../competition/data'):\n"
        "        if (Path(cand) / 'test.csv').exists():\n"
        "            return Path(cand)\n"
        "    raise FileNotFoundError('test.csv not found — attach the competition data or run from the repo root')\n\n"
        "def find_metric():\n"
        "    hits = glob.glob('/kaggle/input/**/metric_humor_vibes.py', recursive=True)\n"
        "    if hits:\n"
        "        return Path(sorted(hits)[0])\n"
        "    for cand in ('competition/metric_humor_vibes.py', 'metric_humor_vibes.py',\n"
        "                 '../metric_humor_vibes.py', '../../metric_humor_vibes.py'):\n"
        "        if Path(cand).exists():\n"
        "            return Path(cand)\n"
        "    return DATA_DIR.parent / 'metric_humor_vibes.py'   # repo layout: data/ sits beside the metric\n\n"
        "DATA_DIR = find_data_dir()\n"
        "METRIC_PATH = find_metric()\n"
        "# submission lands in /kaggle/working on Kaggle, cwd locally; HV_OUT overrides\n"
        "OUT_DIR = Path(os.environ.get('HV_OUT') or ('/kaggle/working' if Path('/kaggle/working').exists() else '.'))\n"
        "print('data dir  :', DATA_DIR.resolve())\n"
        "print('metric    :', METRIC_PATH.resolve() if METRIC_PATH.exists() else '(not found — self-scoring cells will skip)')\n"
        "print('output dir:', OUT_DIR.resolve())"
    ),
    code(
        "def load_csv(name):\n"
        "    with (DATA_DIR / name).open(newline='', encoding='utf-8') as fh:\n"
        "        return list(csv.DictReader(fh))\n\n"
        "train = load_csv('train.csv')\n"
        "test = load_csv('test.csv')\n"
        "print(f'train: {len(train)} rows | test: {len(test)} rows')\n"
        "genuine = [r for r in train if r['is_genuine'] == '1']\n"
        "controls = [r for r in train if r['is_genuine'] == '0']\n"
        "print(f'train genuine: {len(genuine)} | controls: {len(controls)}')\n"
        "by_type = {}\n"
        "for r in controls:\n"
        "    by_type[r['control_type']] = by_type.get(r['control_type'], 0) + 1\n"
        "print('control types:', by_type)\n"
        "for label, rows in (('genuine', genuine), ('control', controls)):\n"
        "    lens = [len(r['punchline'].split()) for r in rows]\n"
        "    print(f'{label} punchline words: mean {sum(lens)/len(lens):.1f}, min {min(lens)}, max {max(lens)}')\n"
        "print('\\nsample genuine :', genuine[0]['setup'], '=>', genuine[0]['punchline'])\n"
        "print('sample control :', controls[0]['setup'], '=>', controls[0]['punchline'],\n"
        "      f\"[{controls[0]['control_type']}]\")"
    ),
    md(
        "## A trivial baseline: punctuation, length, and setup-echo\n"
        "No model, no training — three surface signals:\n\n"
        "- **punctuation/casing**: authored punchlines tend to open capitalized and carry\n"
        "  punch marks (`!`, quotes); boring continuation tails read like mid-sentence prose;\n"
        "- **setup echo**: the boring tails re-use a word from the setup by construction, so\n"
        "  content-word overlap with the setup is (weak) evidence *against* a joke;\n"
        "- **length**: punchlines cluster short; very long tails are suspicious.\n\n"
        "This mostly separates *boring* controls and is near-chance on *shuffled* ones —\n"
        "shuffled punchlines are real punchlines attached to the wrong setup, and telling\n"
        "them apart needs actual setup-punchline coherence (e.g. Gemma logits). That gap is\n"
        "the competition."
    ),
    code(
        "STRIP = '.,!?\\\"\\'()[]:;'\n\n"
        "def content_words(text):\n"
        "    return {w.strip(STRIP).lower() for w in text.split() if len(w.strip(STRIP)) > 3}\n\n"
        "def baseline_score(setup, punchline):\n"
        "    p = punchline.strip()\n"
        "    words = p.split()\n"
        "    score = 0.0\n"
        "    if p[:1].isupper():\n"
        "        score += 1.0                                  # authored-punchline casing\n"
        "    score += 0.6 * p.count('!') + 0.3 * p.count('\"')  # punch marks\n"
        "    score -= 0.8 * len(content_words(setup) & content_words(p))   # setup echo\n"
        "    score -= 0.05 * abs(len(words) - 8)               # mild length prior\n"
        "    return round(score, 4)\n\n"
        "preds = {r['id']: baseline_score(r['setup'], r['punchline']) for r in test}\n"
        "print('scored', len(preds), 'test items | score range:',\n"
        "      f\"{min(preds.values()):.2f} .. {max(preds.values()):.2f}\")"
    ),
    code(
        "sub_path = OUT_DIR / 'submission.csv'\n"
        "with sub_path.open('w', newline='', encoding='utf-8') as fh:\n"
        "    w = csv.writer(fh)\n"
        "    w.writerow(['id', 'humor_score'])\n"
        "    for r in test:                       # keep test.csv order; every id exactly once\n"
        "        w.writerow([r['id'], preds[r['id']]])\n"
        "print('wrote', sub_path, f'({len(test)} rows + header)')"
    ),
    md(
        "## Self-scoring with the competition metric\n"
        "`metric_humor_vibes.py` ships in the data bundle — it is the canonical scorer\n"
        "(dependency-free, `score(solution, submission, \"id\")`). The train split has\n"
        "public labels, so you can iterate locally without burning submissions. When the\n"
        "host runs this notebook next to `solution.csv`, the same cell reports the real\n"
        "test AUC plus the control diagnostics."
    ),
    code(
        "import importlib.util\n\n"
        "metric = None\n"
        "if METRIC_PATH.exists():\n"
        "    spec = importlib.util.spec_from_file_location('metric_humor_vibes', str(METRIC_PATH))\n"
        "    metric = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(metric)\n"
        "else:\n"
        "    print('metric_humor_vibes.py not found — skipping self-scoring')\n\n"
        "if metric:\n"
        "    train_sub = [{'id': r['id'], 'humor_score': baseline_score(r['setup'], r['punchline'])}\n"
        "                 for r in train]\n"
        "    train_auc = metric.score(train, train_sub, 'id')\n"
        "    print(f'baseline AUC on labeled train split: {train_auc}')"
    ),
    code(
        "# Host-side extras: with solution.csv present this reports the real test AUC\n"
        "# and the metric's control readouts. Participants: this cell just skips.\n"
        "sol_path = DATA_DIR / 'solution.csv'\n"
        "if metric and sol_path.exists():\n"
        "    with sol_path.open(newline='', encoding='utf-8') as fh:\n"
        "        sol = list(csv.DictReader(fh))\n"
        "    test_sub = [{'id': r['id'], 'humor_score': preds[r['id']]} for r in test]\n"
        "    print('TEST baseline AUC (all controls)   :', metric.score(sol, test_sub, 'id'))\n"
        "    for ctype in ('shuffled', 'boring'):\n"
        "        part = [r for r in sol if r['is_genuine'] == '1' or r['control_type'] == ctype]\n"
        "        print(f'TEST AUC vs {ctype:8s} controls only :', metric.score(part, test_sub, 'id'))\n"
        "    for usage in ('Public', 'Private'):\n"
        "        part = [r for r in sol if r['Usage'] == usage]\n"
        "        print(f'TEST AUC {usage:7s} split            :', metric.score(part, test_sub, 'id'))\n"
        "    print('matched-pair accuracy (genuine vs shuffled, same setup):',\n"
        "          metric.matched_pair_accuracy(sol, test_sub, 'id'))\n"
        "else:\n"
        "    print('solution.csv not available here (as expected for participants) — skipped')"
    ),
    md(
        "## Sanity: the metric resists trivial submissions\n"
        "A constant submission ties every item (AUC 0.5 by rank-average); a random\n"
        "shuffle of the baseline's own scores lands near 0.5. Seeded, so the numbers\n"
        "reproduce."
    ),
    code(
        "import random\n\n"
        "if metric:\n"
        "    ids = [r['id'] for r in train]\n"
        "    const_sub = [{'id': i, 'humor_score': 0.5} for i in ids]\n"
        "    vals = [baseline_score(r['setup'], r['punchline']) for r in train]\n"
        "    random.Random(7).shuffle(vals)\n"
        "    shuf_sub = [{'id': i, 'humor_score': v} for i, v in zip(ids, vals)]\n"
        "    print('train AUC, all-constant submission :', metric.score(train, const_sub, 'id'))\n"
        "    print('train AUC, seed-7 shuffled scores  :', metric.score(train, shuf_sub, 'id'))\n"
        "    if sol_path.exists():\n"
        "        tids = [r['id'] for r in test]\n"
        "        tvals = [preds[i] for i in tids]\n"
        "        random.Random(7).shuffle(tvals)\n"
        "        print('TEST AUC, all-constant submission  :',\n"
        "              metric.score(sol, [{'id': i, 'humor_score': 0.5} for i in tids], 'id'))\n"
        "        print('TEST AUC, seed-7 shuffled scores   :',\n"
        "              metric.score(sol, [{'id': i, 'humor_score': v} for i, v in zip(tids, tvals)], 'id'))"
    ),
    md(
        "## Where to go from here\n"
        "1. **Gemma as the instrument** (the intended baseline): teacher-forced surprisal\n"
        "   of the punchline given the setup, minus a null-control reading — shuffled\n"
        "   punchlines are surprising *without* a cheap re-route, genuine ones resolve.\n"
        "2. **Setup-punchline coherence**: any embedding similarity beats bag-of-words\n"
        "   overlap on the shuffled controls.\n"
        "3. **Don't chase the boring tails**: they are template-varied with setup-derived\n"
        "   words on purpose; a regex list will not generalize (the hosts adversarially\n"
        "   checked). Model the humor, not the artifact.\n\n"
        "Rules note: only the *ordering* of `humor_score` matters; every test id must\n"
        "appear exactly once, scores must be finite numbers."
    ),
]


def main() -> None:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "cells": CELLS,
    }
    out = HERE / "starter_notebook.ipynb"
    out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print("wrote", out, f"({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
