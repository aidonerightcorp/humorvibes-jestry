# Open Controls release descriptor

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
kaggle datasets create -p kaggle_open_controls
```

For an existing public dataset, replace the final command with:

```bash
kaggle datasets version -p kaggle_open_controls -m "Rebuild deterministic Open Controls release"
```

The release command must stop if the reference-overlap screen or any semantic gate fails.
