# Open Controls release descriptor

The current public artifact is [Humor Genome Open Controls](https://www.kaggle.com/datasets/taylorsamarel/humor-genome-open-controls):
Kaggle version 4 is ready, CC0-1.0, and a fresh download passes all 14 independent verifier
checks across 24 manifested files. The release now includes an entity- and pivot-masked hard
retrieval track with frozen TF-IDF and `hash:128` baselines; those qrels encode generator lineage,
not human relevance judgments.

`build_open_controls.py` creates the complete Kaggle payload in `kaggle_open_controls/`.
The generated directory is intentionally ignored by Git because its canonical public copy is the
Kaggle dataset; source, schemas, a 32-row sample, tests, and verification code remain in Git.

Rebuild the committed sample with:

```bash
python3 open_controls_dataset/build_sample.py
```

```bash
python3 build_open_controls.py --reference-dir corpora
python3 verify_open_controls_release.py --root kaggle_open_controls
kaggle datasets create --public -p kaggle_open_controls
```

For an existing public dataset, replace the final command with:

```bash
kaggle datasets version -p kaggle_open_controls -m "Rebuild deterministic Open Controls release"
```

Kaggle consumes the reserved `dataset-metadata.json` upload control instead of returning it in a
download. The builder therefore adds the same evidence as the manifested
`release-metadata.json`, allowing `verify_open_controls_release.py` to run on a fresh download
without owner credentials.

The release command must stop if the reference-overlap screen or any semantic gate fails.
