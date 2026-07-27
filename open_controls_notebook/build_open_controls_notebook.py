#!/usr/bin/env python3
"""Build the public Open Controls Kaggle notebook deterministically.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "humor_genome_open_controls.ipynb"


CELLS: list[tuple[str, str]] = [
    (
        "markdown",
        "# Humor Genome Open Controls\n\n"
        "### A deterministic causal-design lab for surprise, resolution, and over-explanation\n\n"
        "> **Executive summary.** This notebook verifies and analyzes 120,000 openly reusable "
        "procedural controls. It does not claim that any row is funny, human-authored, culturally "
        "representative, or evidence about a brain mechanism.\n\n"
        "| Question | Answer |\n|---|---|\n"
        "| What problem is addressed? | Existing joke corpora rarely contain matched alternatives "
        "that separate expected continuation, unresolved surprise, compact repair, and explicit explanation. |\n"
        "| What is the proposed solution? | Generate four arms from the same premise and configuration, "
        "preserve their group IDs, isolate templates across splits, and publish every build/audit receipt. |\n"
        "| What can this notebook conclude? | The release bytes, grouping, balance, and retrieval contract "
        "are reproducible. It can measure generator artifacts and benchmark models against declared relations. |\n"
        "| What can it not conclude? | Human funniness, audience benefit, safety, originality worldwide, "
        "or neural surprise reduction. Those require different evidence. |\n\n"
        "The corpus operationalizes the project hypothesis `expectation -> violation -> optional repair`. "
        "That is a falsifiable starting point, not a result. Source and methods: "
        "[aidonerightcorp/humorvibes-jestry](https://github.com/aidonerightcorp/humorvibes-jestry).",
    ),
    (
        "markdown",
        "## 1. Verify the mounted release before reading it\n\n"
        "Kaggle uploads can succeed while carrying stale or partial files. This cell discovers the dataset by "
        "its declared ID, verifies every SHA-256 and byte length, then loads the controlling summary.",
    ),
    (
        "code",
        "from pathlib import Path\n"
        "import glob, hashlib, json, os\n"
        "\n"
        "def find_release():\n"
        "    candidates = [Path(p).parent for p in glob.glob('/kaggle/input/**/release_summary.json', recursive=True)]\n"
        "    candidates += [Path('../kaggle_open_controls'), Path('kaggle_open_controls')]\n"
        "    for root in candidates:\n"
        "        try:\n"
        "            summary = json.loads((root / 'release_summary.json').read_text(encoding='utf-8'))\n"
        "        except (FileNotFoundError, json.JSONDecodeError):\n"
        "            continue\n"
        "        if summary.get('dataset_id') == 'humor-genome-open-controls':\n"
        "            return root.resolve(), summary\n"
        "    raise FileNotFoundError('Attach taylorsamarel/humor-genome-open-controls')\n"
        "\n"
        "DATA_DIR, SUMMARY = find_release()\n"
        "manifest = json.loads((DATA_DIR / 'manifest.json').read_text(encoding='utf-8'))\n"
        "for name, expected in manifest['files'].items():\n"
        "    path = DATA_DIR / name\n"
        "    assert path.is_file(), f'missing manifest payload: {name}'\n"
        "    digest = hashlib.sha256()\n"
        "    with path.open('rb') as fh:\n"
        "        while chunk := fh.read(1024 * 1024):\n"
        "            digest.update(chunk)\n"
        "    assert path.stat().st_size == expected['bytes'], f'byte mismatch: {name}'\n"
        "    assert digest.hexdigest() == expected['sha256'], f'hash mismatch: {name}'\n"
        "print('dataset:', DATA_DIR)\n"
        "print('verified payload files:', len(manifest['files']))\n"
        "print('generator commit:', SUMMARY['generator_commit'])\n"
        "assert SUMMARY['human_authored_rows'] == 0\n"
        "assert SUMMARY['human_rated_rows'] == 0",
    ),
    (
        "markdown",
        "## 2. Load the controlled rows\n\n"
        "The Parquet and JSONL files carry the same records. Parquet is used here for speed. The assertions "
        "below make the experimental unit and leakage boundary visible before any chart is drawn.",
    ),
    (
        "code",
        "import pandas as pd\n"
        "rows = pd.read_parquet(DATA_DIR / 'open_controls.parquet')\n"
        "assert len(rows) == SUMMARY['rows'] == 120_000\n"
        "assert rows['item_id'].is_unique\n"
        "assert rows.groupby('premise_id')['split'].nunique().max() == 1\n"
        "assert rows.groupby('template_family_id')['split'].nunique().max() == 1\n"
        "assert not rows['human_authored'].any()\n"
        "assert not rows['human_rated'].any()\n"
        "assert rows['funniness_label'].isna().all()\n"
        "\n"
        "counts = rows.groupby(['counterfactual_arm', 'surface_variant']).size().unstack()\n"
        "print(f\"{len(rows):,} rows; {rows['premise_id'].nunique()} premise families; \"\n"
        "      f\"{rows['template_family_id'].nunique()} isolated lexical templates\")\n"
        "display(counts)\n"
        "display(rows.groupby('split').size().rename('rows').to_frame())",
    ),
    (
        "markdown",
        "## 3. Inspect one matched group\n\n"
        "All four arms below share a premise, slot configuration, split, and surface variant. Only the type "
        "of continuation changes. `intended_mechanism` describes how the generator was constructed; it is not "
        "an observed psychological label.",
    ),
    (
        "code",
        "example_id = sorted(rows['configuration_id'].unique())[0]\n"
        "example = rows[(rows['configuration_id'] == example_id) & (rows['surface_variant'] == 0)]\n"
        "display(example[['counterfactual_arm', 'setup', 'punchline', 'repair_type']].sort_values('counterfactual_arm'))",
    ),
    (
        "markdown",
        "## 4. Adversarial artifact audit\n\n"
        "A corpus can accidentally encode its labels through length or punctuation. The release builder groups "
        "rows by coarse surface signatures and asks how accurately the majority arm in each group predicts the "
        "label. Chance is 25%. This is intentionally a hostile diagnostic. Passing the release threshold does "
        "not mean the text is artifact-free.",
    ),
    (
        "code",
        "import re\n"
        "from collections import Counter, defaultdict\n"
        "\n"
        "surface = defaultdict(Counter)\n"
        "for text, arm in zip(rows['text'], rows['counterfactual_arm']):\n"
        "    words = re.findall(r'\\b\\w+\\b', text)\n"
        "    signature = (min(len(words)//5, 20), min(len(text)//30, 20), text.count('.'), text.count(','), text.count(':'))\n"
        "    surface[signature][arm] += 1\n"
        "accuracy = sum(max(group.values()) for group in surface.values()) / len(rows)\n"
        "published_audit = json.loads((DATA_DIR / 'audit.json').read_text(encoding='utf-8'))\n"
        "assert abs(accuracy - published_audit['adversarial']['surface_only_arm_accuracy']) < 1e-12\n"
        "print(f'surface-only arm accuracy: {accuracy:.1%} (chance 25.0%)')\n"
        "print('release threshold: <80%; status:', 'PASS' if accuracy < .80 else 'FAIL')\n"
        "print('Important: residual predictability is a limitation to report, not a model-quality result.')",
    ),
    (
        "markdown",
        "## 5. A fully executable retrieval baseline\n\n"
        "The dataset includes one query and one relevant compact-repair document per premise. This baseline "
        "uses TF-IDF, evaluates each split independently, and reports MRR and Recall@k. The qrels are generator "
        "relations—not human relevance judgments—so this tests pipeline correctness and model sensitivity only.",
    ),
    (
        "code",
        "import numpy as np\n"
        "from sklearn.feature_extraction.text import TfidfVectorizer\n"
        "from sklearn.metrics.pairwise import cosine_similarity\n"
        "\n"
        "docs = pd.read_json(DATA_DIR / 'retrieval_documents.jsonl', lines=True)\n"
        "queries = pd.read_json(DATA_DIR / 'retrieval_queries.jsonl', lines=True)\n"
        "qrels = pd.read_json(DATA_DIR / 'retrieval_qrels.jsonl', lines=True)\n"
        "truth = dict(zip(qrels.query_id, qrels.document_id))\n"
        "\n"
        "def evaluate_split(split):\n"
        "    d = docs[docs.split == split].reset_index(drop=True)\n"
        "    q = queries[queries.split == split].reset_index(drop=True)\n"
        "    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)\n"
        "    matrix = vectorizer.fit_transform(pd.concat([d.text, q.text], ignore_index=True))\n"
        "    scores = cosine_similarity(matrix[len(d):], matrix[:len(d)])\n"
        "    ranks = []\n"
        "    for i, query in q.iterrows():\n"
        "        order = np.argsort(-scores[i], kind='stable')\n"
        "        relevant = truth[query.query_id]\n"
        "        rank = int(np.where(d.document_id.to_numpy()[order] == relevant)[0][0]) + 1\n"
        "        ranks.append(rank)\n"
        "    return {'split': split, 'queries': len(ranks), 'MRR': sum(1/r for r in ranks)/len(ranks),\n"
        "            'Recall@1': sum(r <= 1 for r in ranks)/len(ranks),\n"
        "            'Recall@10': sum(r <= 10 for r in ranks)/len(ranks)}\n"
        "\n"
        "retrieval_results = pd.DataFrame(evaluate_split(split) for split in ('train', 'validation', 'test'))\n"
        "display(retrieval_results.round(4))\n"
        "assert len(docs) == len(queries) == len(qrels) == 300",
    ),
    (
        "markdown",
        "### Use another embedding model without changing the benchmark\n\n"
        "Export document and query vectors in the existing row order, compute cosine similarity, and reuse the "
        "same qrels and split loop. The repository API already supports deterministic hash vectors, multiple "
        "allowlisted Ollama embedding models, OpenAI-compatible embedding endpoints, and optional "
        "sentence-transformers. Always report the exact provider, model revision, dimensions, normalization, "
        "and split. Embedding similarity is not proof of originality, equivalence, or funniness.",
    ),
    (
        "markdown",
        "## 6. The harder retrieval track changes the conclusion\n\n"
        "The original query repeats the occupation and setting, so it can reward lexical matching. "
        "The hard query removes the entity and both pivot words, describes their two senses and "
        "situation indirectly, and supplies same-frame and same-context negatives inside each split. "
        "This cell recomputes the frozen lexical baseline rather than merely trusting its receipt. "
        "A lower result here is useful evidence that the new benchmark is harder—not a claim that "
        "semantic models understand humor.",
    ),
    (
        "code",
        "hard_docs = pd.read_json(DATA_DIR / 'hard_retrieval_documents.jsonl', lines=True)\n"
        "hard_queries = pd.read_json(DATA_DIR / 'hard_retrieval_queries.jsonl', lines=True)\n"
        "hard_qrels = pd.read_json(DATA_DIR / 'hard_retrieval_qrels.jsonl', lines=True)\n"
        "hard_negatives = pd.read_json(DATA_DIR / 'hard_retrieval_negatives.jsonl', lines=True)\n"
        "hard_manifest = json.loads((DATA_DIR / 'hard_retrieval_manifest.json').read_text())\n"
        "published_hard_tfidf = json.loads((DATA_DIR / 'hard_retrieval_tfidf_baseline.json').read_text())\n"
        "published_hard_hash = json.loads((DATA_DIR / 'hard_retrieval_hash_128_baseline.json').read_text())\n"
        "assert len(hard_docs) == len(hard_queries) == len(hard_qrels) == len(hard_negatives) == 300\n"
        "assert hard_manifest['leakage_audit']['entity_or_pivot_leaks'] == 0\n"
        "assert hard_manifest['leakage_audit']['template_family_crosses_splits'] is False\n"
        "assert hard_manifest['leakage_audit']['maximum_content_token_jaccard_to_relevant_document'] < .11\n"
        "hard_truth = dict(zip(hard_qrels.query_id, hard_qrels.document_id))\n"
        "hard_negative_map = hard_negatives.set_index('query_id').to_dict(orient='index')\n"
        "hard_token_re = re.compile(r\"[^\\W_]+(?:['’-][^\\W_]+)*\", re.UNICODE)\n"
        "\n"
        "def hard_tokens(text):\n"
        "    return hard_token_re.findall(text.casefold())\n"
        "\n"
        "def evaluate_hard_split(split):\n"
        "    d = hard_docs[hard_docs.split == split].sort_values('document_id').reset_index(drop=True)\n"
        "    q = hard_queries[hard_queries.split == split].reset_index(drop=True)\n"
        "    vectorizer = TfidfVectorizer(tokenizer=hard_tokens, preprocessor=None, token_pattern=None,\n"
        "                                 lowercase=False, min_df=1, sublinear_tf=True)\n"
        "    matrix = vectorizer.fit_transform(pd.concat([d.text, q.text], ignore_index=True))\n"
        "    scores = cosine_similarity(matrix[len(d):], matrix[:len(d)])\n"
        "    ranks, beats_frame, beats_context = [], [], []\n"
        "    document_ids = d.document_id.to_numpy()\n"
        "    for i, query in q.iterrows():\n"
        "        order = np.argsort(-scores[i], kind='stable')\n"
        "        ranked = document_ids[order].tolist()\n"
        "        relevant = hard_truth[query.query_id]\n"
        "        rank = ranked.index(relevant) + 1\n"
        "        negative = hard_negative_map[query.query_id]\n"
        "        ranks.append(rank)\n"
        "        beats_frame.append(rank < ranked.index(negative['same_frame_different_context_document_id']) + 1)\n"
        "        beats_context.append(rank < ranked.index(negative['same_context_different_frame_document_id']) + 1)\n"
        "    return {'split': split, 'queries': len(ranks), 'MRR': sum(1/r for r in ranks)/len(ranks),\n"
        "            'Recall@1': sum(r <= 1 for r in ranks)/len(ranks),\n"
        "            'Recall@5': sum(r <= 5 for r in ranks)/len(ranks),\n"
        "            'Recall@10': sum(r <= 10 for r in ranks)/len(ranks),\n"
        "            'median_rank': float(np.median(ranks)),\n"
        "            'beats_same_frame_hard_negative_rate': sum(beats_frame)/len(ranks),\n"
        "            'beats_same_context_hard_negative_rate': sum(beats_context)/len(ranks)}\n"
        "\n"
        "hard_results = pd.DataFrame(evaluate_hard_split(split) for split in ('train', 'validation', 'test'))\n"
        "for row in hard_results.to_dict(orient='records'):\n"
        "    expected = published_hard_tfidf['metrics_by_split'][row['split']]\n"
        "    for key in ('MRR', 'Recall@1', 'Recall@5', 'Recall@10', 'median_rank',\n"
        "                'beats_same_frame_hard_negative_rate', 'beats_same_context_hard_negative_rate'):\n"
        "        assert abs(row[key] - expected[key]) < 1e-12, (row['split'], key, row[key], expected[key])\n"
        "display(hard_results.round(4))\n"
        "comparison = pd.DataFrame({\n"
        "    'track': ['original lexical query', 'entity/pivot-masked hard query', 'hard query hash:128'],\n"
        "    'overall_MRR': [float(retrieval_results.MRR.mul(retrieval_results.queries).sum() / retrieval_results.queries.sum()),\n"
        "                    published_hard_tfidf['overall']['MRR'], published_hard_hash['overall']['MRR']],\n"
        "    'human_judgments': [False, False, False],\n"
        "})\n"
        "display(comparison.round(4))\n"
        "print('Hard-track verdict: surface repetition no longer produces a strong baseline.')",
    ),
    (
        "markdown",
        "## 7. What useful conclusions require next\n\n"
        "The next research release should preregister a blinded, randomized rating study and collect the supplied "
        "fields separately: expectedness, surprise, resolution, funniness, familiarity, comprehensibility, and "
        "offensiveness. Analyze people—not generated rows—as the independent unit, preserve writer/rater clustering, "
        "and hold premise families out. A useful finding would be an interaction such as compact resolution improving "
        "funniness relative to unresolved surprise, with uncertainty and audience context reported.\n\n"
        "Until then, this corpus is already useful for deterministic application fixtures, grouped-split regression "
        "tests, retrieval bakeoffs, experimental-design teaching, and preparing a consented human study. It is not a "
        "shortcut around that study.",
    ),
    (
        "code",
        "receipt = {\n"
        "    'dataset_id': SUMMARY['dataset_id'],\n"
        "    'generator_commit': SUMMARY['generator_commit'],\n"
        "    'manifest_files_verified': len(manifest['files']),\n"
        "    'rows': len(rows),\n"
        "    'premise_families': int(rows['premise_id'].nunique()),\n"
        "    'surface_only_arm_accuracy': accuracy,\n"
        "    'retrieval_baseline': retrieval_results.to_dict(orient='records'),\n"
        "    'hard_retrieval_digest': hard_manifest['content_digest'],\n"
        "    'hard_retrieval_max_content_jaccard': hard_manifest['leakage_audit']['maximum_content_token_jaccard_to_relevant_document'],\n"
        "    'hard_retrieval_tfidf': hard_results.to_dict(orient='records'),\n"
        "    'hard_retrieval_hash_128': published_hard_hash['overall'],\n"
        "    'human_authored_rows': 0,\n"
        "    'human_rated_rows': 0,\n"
        "    'claim_ready_for_human_funniness': False,\n"
        "    'status': 'VERIFIED_SYNTHETIC_CONTROL_RELEASE',\n"
        "}\n"
        "output_root = Path('/kaggle/working') if Path('/kaggle/working').is_dir() else Path('.')\n"
        "(output_root / 'OPEN_CONTROLS_NOTEBOOK_RECEIPT.json').write_text(\n"
        "    json.dumps(receipt, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
        "print(json.dumps(receipt, indent=2, sort_keys=True))",
    ),
]


def build() -> Path:
    notebook_cells = []
    for index, (kind, source) in enumerate(CELLS):
        cell = {
            "id": f"{kind}-{index:02d}",
            "cell_type": kind,
            "metadata": {},
            "source": [line + "\n" for line in source.splitlines()],
        }
        if kind == "code":
            cell.update({"execution_count": None, "outputs": []})
        notebook_cells.append(cell)
    notebook = {
        "cells": notebook_cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return OUTPUT


if __name__ == "__main__":
    print(build())
