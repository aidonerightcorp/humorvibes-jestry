# Notebook guide

*Role: which notebook is canonical and what a promoted notebook must show. Audience: readers choosing where to start.*

## The observational notebook to read first

[`wave2_notebook/humor_genome_wave2.ipynb`](../wave2_notebook/humor_genome_wave2.ipynb) is the
canonical executable Wave 2 study and the notebook published publicly on Kaggle as
[Humor Genome Wave 2 Reproducible Gemma Study](https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study)
(version 15, COMPLETE; public dataset version 7; opens with the thesis in one screen and a receipted follow-ups section).. A third public surface, the display-only label-ceiling explainer [HumorVibes: What the Label Can Support](https://www.kaggle.com/code/taylorsamarel/humorvibes-what-the-label-can-support) (version 3, COMPLETE), is built deterministically from `ceiling_demo/` with receipts embedded at build time — it displays stored results and never re-measures. It
states the problem, proposed exploration, controlling findings, outputs, practical uses, and
limitations before exposing implementation detail. It also names the predictive-processing
starting point, cites its scientific lineage, renders the model-to-human evidence boundary, and
runs the synthetic study-contract gate. Its final machine-readable executive summary
asserts the controlling values and writes a JSON artifact on Kaggle.

The source of that notebook is
[`wave2_notebook/build_wave2_notebook.py`](../wave2_notebook/build_wave2_notebook.py). Edit the
builder, rebuild the notebook, and commit both; do not hand-edit generated cells.

The separate [Open Controls Causal Design Lab](https://www.kaggle.com/code/taylorsamarel/humor-genome-open-controls-causal-design-lab)
is the promoted executable for the synthetic four-arm corpus. It verifies all mounted payloads,
reports generator artifacts, runs both the easy and entity-masked hard retrieval baselines, and
explicitly stops short of human funniness or brain-mechanism claims.

## Supporting notebooks

The remaining notebooks are retained because they answer narrower questions or preserve the
project's development history. They do not override the canonical Wave 2 conclusions.

| Path | Role |
| --- | --- |
| `notebook.ipynb` | Original measuring-jokes prototype |
| `ablation_lab/ablation_notebook.ipynb` | S/R/E/B ablation experiment and negative result |
| `competition/launch/starter_notebook.ipynb` | Historical competition starter |
| `corpus_lab/corpus_lab.ipynb` | Corpus scanning and remix exploration |
| `github_wrapper/jestry_demo_notebook.ipynb` | Thin GitHub demonstration wrapper |
| `live_portal/jestry_portal_notebook.ipynb` | Thin portal launcher |
| `live_studio/live_notebook.ipynb` | Thin studio launcher |
| `panel_lab/panel_lab.ipynb` | Panel and frame comparison experiment |
| `validate_ratings/validate_notebook.ipynb` | Model signals compared with available human ratings |
| `zoo_lab/zoo_lab.ipynb` | Multi-model-family and invariance exploration |
| [`open_controls_notebook/humor_genome_open_controls.ipynb`](../open_controls_notebook/humor_genome_open_controls.ipynb) | [Public Open Controls](https://www.kaggle.com/code/taylorsamarel/humor-genome-open-controls-causal-design-lab) integrity, artifact, and retrieval lab; synthetic evidence only |

## Clarity contract

A promoted research notebook must make these items visible without requiring readers to infer
them from code:

1. What problem is being solved?
2. What solution or exploration is proposed?
3. What was measured, on what units, with which controls and uncertainty?
4. What did the run actually learn—including null results and corrections?
5. What files or machine-readable outputs were produced?
6. What can a writer, audience member, academic, educator, curator, or builder safely use now?
7. What evidence is still required before a stronger claim is allowed?
8. Which claims are prior literature, project hypotheses, model measurements, or human outcomes?

The controlling conclusion must appear before secondary observations. Point-estimate rankings do
not supersede interval results, model surprisal does not become funniness, and successful execution
does not become external validation.

## Verification

```bash
python3 wave2_notebook/build_wave2_notebook.py
python3 -m pytest -q tests/test_wave2.py
git diff --exit-code -- wave2_notebook/humor_genome_wave2.ipynb

python3 open_controls_notebook/build_open_controls_notebook.py
python3 -m pytest -q tests/test_open_controls.py
git diff --exit-code -- open_controls_notebook/humor_genome_open_controls.ipynb
```

Kaggle publication additionally requires a terminal `COMPLETE` run and a downloaded independent
log/output audit. The source checkout must live outside `/kaggle/working`, or Kaggle will publish
the checkout as output; the canonical builder uses a tag-specific `/tmp` directory and leaves only
the executive-summary receipt in the working directory. A successful source upload alone is not
an executed public result.
