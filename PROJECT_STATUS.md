# Project status

Humor Genome Wave 2 is a public, reproducible research project. The Build with Gemma: Humor
Genome NYC deadline has passed, and **no competition submission is claimed**. The work continues
as an open project whose current evidence can be read, rerun, challenged, and extended.

## Public release

| Surface | Canonical location | Current contract |
| --- | --- | --- |
| Executable study | [Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study) | Public; latest successful run is the canonical executable write-up |
| Research dataset | [Kaggle dataset](https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2) | Public and ready; only explicitly redistributable text is included |
| Source and evidence | [GitHub repository](https://github.com/aidonerightcorp/humorvibes-jestry) | Public; builders, tests, immutable notebook source tags, and receipts |

The notebook uses the immutable source tag `humor-genome-wave2-v6`. GitHub `main` may move as
documentation and follow-up research improve; the code executed by the public notebook cannot
move underneath an existing run.

## What is complete

- The public dataset is deterministic, source-stratified, and deny-first on redistribution
  rights. It contains 121,670 text rows, 7,913 aligned phrase pairs, 2,581
  expectation/violation frames, a full-corpus census, an export summary, and a SHA-256 manifest.
- The canonical notebook verifies all six mounted payloads before analysis, loads its attached
  Gemma 2 checkpoint, runs the pinned instrument check, and displays the controlling statistical
  results and limitations.
- The full local inventory contains 3,164,600 rows across 217 source families and 62 language
  labels. Text that is research-only, noncommercial, or unclassified remains out of the public
  verbatim payload.
- The form study reports uncertainty rather than ranking bare means: 0 of 10 joke-form intervals
  separate from the proverb control, and all 10 overlap it.
- The caption study holds out entire contests. Its median within-contest Spearman correlation is
  0.1555, compared with a measured text-only bound of 0.4110 and label ceiling of 0.8262.
- The release has source-controlled dataset and notebook metadata, deterministic notebook
  generation, automated tests, semantic release checks, and a machine-readable publication
  receipt at [`jestry_out/wave2_publication.json`](jestry_out/wave2_publication.json).

## What is deliberately not claimed

- `S` is Gemma surprisal, not funniness.
- Source-specific ratings, votes, scores, and labels are not interchangeable human grades.
- The public slice is stratified and rights-filtered, not a random sample of the full inventory.
- Keyword domains are hypotheses; most form rules are English-biased; source-declared style is a
  separate axis.
- A weak text-only caption result does not bound a multimodal system that can see the drawing.
- Public artifacts do not retroactively create a competition submission.
- “Release complete” does not mean the research question is settled. The negative results are a
  starting point for better experiments.

## How to verify the release

```bash
git clone https://github.com/aidonerightcorp/humorvibes-jestry.git
cd humorvibes-jestry
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
python3 wave2_notebook/build_wave2_notebook.py

kaggle datasets download -d taylorsamarel/humor-genome-wave2 \
  --unzip -p kaggle_wave2_public
python3 verify_wave2_release.py --root kaggle_wave2_public
```

The local corpus is not required to read or verify the public release. It is required only to
rebuild the public slice from the complete research inventory.

## Where help is useful

Start with [`ROADMAP.md`](ROADMAP.md) for prioritized work, [`CONTRIBUTING.md`](CONTRIBUTING.md)
for the evidence and pull-request contract, and [`docs/EXPANSION_GUIDE.md`](docs/EXPANSION_GUIDE.md)
for exact extension paths. The best near-term contributions are multimodal caption baselines,
human-annotated setup/frame/punchline data, native-form rules for under-covered languages,
licence-verified sources, and small reproducibility improvements.

## One remaining owner decision

The GitHub repository is public but currently has no repository-level code licence. Public access
does not grant open-source reuse rights. Issues, independent reproductions, and research proposals
can proceed now, but the maintainer should choose and add a code licence before accepting reusable
outside code. The dataset is a separate mixed-provenance artifact: each row retains its recorded
source licence, and the exporter admits text only when redistribution is explicit.
