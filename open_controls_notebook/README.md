# Open Controls notebook

The notebook is generated from `build_open_controls_notebook.py` so its prose, code, and public
metadata remain reviewable. It makes no network or model call. It verifies every mounted payload,
recomputes the surface-artifact audit, runs a TF-IDF retrieval baseline, and writes one compact
receipt.

```bash
python3 open_controls_notebook/build_open_controls_notebook.py
kaggle kernels push -p open_controls_notebook
```

Kaggle must report `COMPLETE`, the notebook must remain public, and the downloaded receipt must be
checked before the URL is described as a working release.
