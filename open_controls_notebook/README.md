# Open Controls notebook

The current public run is [Humor Genome Open Controls - Causal Design Lab](https://www.kaggle.com/code/taylorsamarel/humor-genome-open-controls-causal-design-lab):
Kaggle version 3 is public and `COMPLETE`. Its independently downloaded receipt verifies 24
manifested files, recomputes both frozen hard-retrieval baselines, and preserves
`claim_ready_for_human_funniness=false`. All 16 remote source cells match the local generated
notebook exactly after normalizing notebook metadata and outputs.

The notebook is generated from `build_open_controls_notebook.py` so its prose, code, and public
metadata remain reviewable. It makes no network or model call. It verifies every mounted payload,
recomputes the surface-artifact audit, runs the easy and entity-masked hard retrieval baselines,
and writes one compact receipt.

```bash
python3 open_controls_notebook/build_open_controls_notebook.py
kaggle kernels push -p open_controls_notebook
```

Kaggle must report `COMPLETE`, the notebook must remain public, and the downloaded receipt must be
checked before the URL is described as a working release.
