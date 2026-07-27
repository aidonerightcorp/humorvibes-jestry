# Wave 2 Kaggle dataset publication

This directory holds the small, reviewable publication metadata for the public dataset:

https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2

The payload is intentionally not committed to Git. `build_kaggle_export.py` generates the
rights-filtered JSONL files, full census, data card, summary, and SHA-256 manifest in the ignored
`kaggle_wave2/` directory. It copies `dataset-metadata.json` from this directory so the public
title and visibility remain source-controlled.

```bash
python3 build_kaggle_export.py --per-family 12000 \
  --corpora-dir corpora --out-dir kaggle_wave2 \
  --metadata-template wave2_dataset/dataset-metadata.json
python3 verify_wave2_release.py --root kaggle_wave2
kaggle datasets version -p kaggle_wave2 -m "Clarify public dataset documentation"
```

The exporter publishes verbatim text only when the normalized per-record licence class is
`redistributable`. Rows classified as research-only, noncommercial, or unclassified remain in the
local census and are excluded from the public text payload.
