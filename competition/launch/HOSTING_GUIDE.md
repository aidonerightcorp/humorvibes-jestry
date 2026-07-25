# Humor Vibes Open — Hosting Guide (Kaggle Community Competition)

Everything a host needs to launch Track A with zero additional authoring.
Companion files in this folder: `DESCRIPTION_PASTE.md` (participant-facing text,
ready to paste), `build_starter_notebook.py` → `starter_notebook.ipynb` (verified
starter kit), `solution_kaggle.csv` (trimmed solution file for Kaggle's
evaluation setup). Design rationale: `../HUMOR-VIBES-OPEN-COMPETITION-DESIGN.md`.
Canonical scorer: `../metric_humor_vibes.py`. UI wording below is accurate as of
mid-2026; Kaggle moves buttons occasionally, but every concept (data upload,
solution file, metric dropdown, Usage split) is stable.

## 0. What you are hosting (30 seconds)

Binary separation task: given (`setup`, `punchline`), score how likely the item
is a genuine human joke vs a constructed control (shuffled punchline from a
different setup, or a deliberately boring continuation). Leaderboard metric:
ROC AUC of `humor_score` against `is_genuine`. One CSV submission per entry
(`id,humor_score`).

## 1. Rebuild and verify the data

From the repo root (`build-with-gemma-humor-genome-nyc/`):

```bash
python3 competition/make_competition_data.py
```

Same corpora + same seed (20260723) → byte-identical rebuild. The builder
self-attacks on every run (punchline-reuse cap, genuine/control text overlap = 0,
boring-tail diversity) and refuses to write exploitable data. To scale up first:
`python3 harvest_supply.py keyless --limit 200` (network), then rebuild.

Current verified build (2026-07-24):

| file | sha256 | rows (CSV records) |
|---|---|---|
| `data/train.csv` | `a2ee47c0550ad48bf2712a5ac40403b1c30e49fb81f40fc4758aa081702e2286` | 155 |
| `data/test.csv` | `6afe456d86ca4e079d9981a89cbd82602819d5f88560a447f93614b272a3caa9` | 319 |
| `data/solution.csv` | `2da01f46a1832d833dbc754ff83d4d51440b3970744b951f321a8c33ec55e5a1` | 319 |
| `data/sample_submission.csv` | `f69d2650019d57745de367003e234aa13c69fe06fc76ae4f4cf03d2de4983e21` | 319 |
| `data/manifest.json` | `bba55b723bff074c7f563caa92fda868fe20207f33bf5e330ee4c265e4cbac74` | — |

Composition: test = 136 genuine + 136 shuffled + 47 boring; Usage = 195 Public /
124 Private (61.1% public). Train = 67 genuine + 67 shuffled + 21 boring, labels
visible. A few text fields contain quoted embedded newlines — standard CSV;
Kaggle and the `csv` module both handle it (`wc -l` will overcount; count
records with a CSV reader).

## 2. Create the competition (click-path)

1. Go to **kaggle.com/competitions** → click **Host a Competition** (also
   reachable via **Create** → **New Competition**, direct URL
   `kaggle.com/competitions/new`).
2. Pick the **Community Competition** option (free, self-service) → **Create**.
3. Fill the creation form: title **Humor Vibes Open**, URL slug
   `humor-vibes-open`, subtitle "Separate genuine jokes from constructed
   controls — surprise is not enough", visibility **Public**.
4. The competition is created in **draft** mode. You land on the host console —
   a tab strip / sidebar with sections: **Overview**, **Data**, **Evaluation**
   (or "Scoring"), **Rules**, **Schedule**, **Prizes**, **Host settings**.
   Nothing is live until you press **Launch/Publish**.

## 3. Upload the files

**Data section (participant-visible):** upload

- `data/train.csv` — labeled training split
- `data/test.csv` — items to score
- `data/sample_submission.csv` — valid all-0.5 submission (scores 0.500000)
- `metric_humor_vibes.py` — ship it in the data bundle; it is the canonical
  offline scorer (dependency-free) and lets entrants self-score on train
- optionally `data/manifest.json` — build receipt (seed, self-attack readouts);
  it leaks nothing

**Evaluation section (host-only):** upload the solution file. Use
`launch/solution_kaggle.csv` — columns `id,is_genuine,Usage` exactly (Kaggle's
solution checker rejects unknown extra columns; the full `data/solution.csv`
additionally carries `control_type` and `setup_key`, which are for offline
diagnostics only). Regenerate any time with:

```bash
python3 - <<'EOF'
import csv
rows = list(csv.DictReader(open('competition/data/solution.csv')))
with open('competition/launch/solution_kaggle.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['id', 'is_genuine', 'Usage'])
    w.writeheader()
    w.writerows({k: r[k] for k in ('id', 'is_genuine', 'Usage')} for r in rows)
EOF
```

**Never** attach `solution.csv`/`solution_kaggle.csv` in the Data section.

## 4. Evaluation setup — the honest part

**Kaggle Community Competitions only offer Kaggle's built-in metric list.** You
select from a dropdown; there is no facility to upload custom metric code on the
community tier (custom Python metrics exist only for Kaggle-run competitions).
The design doc's step "paste `metric_humor_vibes.py` as the evaluation metric"
is therefore not literally available. The honest, recommended path:

1. **Metric:** select **AUC** ("Area Under Receiver Operating Characteristic
   Curve").
2. **Solution mapping:** ground-truth column `is_genuine` (0/1), row id column
   `id`, public/private from the `Usage` column.
3. **Submission format:** `id,humor_score` — Kaggle infers/validates it from
   `sample_submission.csv`.
4. **Declare `metric_humor_vibes.py` canonical** in the description (the paste
   text already does): end-of-competition verification is running it offline
   against `data/solution.csv`.

**Exactly what differs between built-in AUC and `metric_humor_vibes.py`** (per
the metric source):

- The custom metric's leaderboard number **is** Mann–Whitney rank AUC with
  tie-averaging — mathematically identical to standard ROC AUC on `is_genuine`.
  Built-in AUC therefore reproduces the custom primary score exactly (the
  custom metric rounds to 6 decimals; verified in this checkout: both score the
  sample submission 0.5 and the starter baseline 0.604207).
- **Advisory-only when hosted this way:** `matched_pair_accuracy` (does the
  genuine punchline outscore the shuffled one *for the same setup* — needs
  `setup_key`/`control_type`, which stay offline), and the per-control-type AUC
  readouts. Kaggle will not compute these; run them host-side with the last
  cells of `starter_notebook.ipynb`, and use them in the wrap-up post / winner
  verification.
- **Validation errors:** the custom metric raises participant-visible errors
  for duplicate ids, missing ids, non-numeric and non-finite scores. Kaggle's
  generic submission validation covers the same failure classes with its own
  messages; entrants self-scoring locally get the precise custom errors.

Nothing about the *ranking* changes — only the diagnostics move offline.

## 5. Leaderboard split

Set the public/private split from the solution file's `Usage` column
(Public/Private per row — Kaggle's standard mechanism). This build ships
195 Public / 124 Private (61.1%). If your UI variant only offers a percentage
slider instead of a Usage column, set **60%** — but the Usage column is the
correct, reproducible route and matches `manifest.json`.

## 6. Recommended default configuration (concrete, edit only if you disagree)

| Setting | Recommended default |
|---|---|
| Duration | **6 weeks**: open 2026-07-27 00:00 UTC → final deadline 2026-09-07 23:59 UTC |
| Prizes | **Kudos only, no cash** (community default): winner interview + pinned write-up, "certified funny scorer" badge in the wrap-up post |
| Submissions per day | **5** |
| Final submissions selectable | **2** |
| Team size | max **3**; merges allowed until 1 week before close |
| Eligibility | public, anyone with a Kaggle account |
| External data | allowed if public + license-compatible and disclosed in the forum |
| Models | any; Gemma encouraged (the intended baseline is Gemma-as-instrument) |
| Leaderboard | public split live; private revealed at close |

## 7. Starter notebook

`starter_notebook.ipynb` (built by `build_starter_notebook.py`, verified
end-to-end in this checkout on 2026-07-24): pure stdlib, loads data with the
`csv` module, EDA counts, punctuation/length/setup-echo baseline, writes a valid
submission, self-scores with `metric_humor_vibes.py`. Verified numbers:

- baseline AUC — train 0.612025, **test 0.604207** (public 0.579740 / private 0.640491)
- vs shuffled controls only 0.471967 (chance — the real problem), vs boring only 0.986859
- matched-pair accuracy 0.466912 (chance — the hard diagnostic)
- all-constant submission 0.500000; seed-7 score shuffle 0.486238 (gaming smoke test)

After launch: create a Kaggle Notebook attached to the competition, **File →
Import Notebook** → upload `starter_notebook.ipynb`, add the competition data
source, run, **Share → Public**, and pin it in a welcome thread. (CLI
alternative: `kaggle kernels push` with a kernel-metadata.json naming the
competition as data source.) On Kaggle it auto-finds `/kaggle/input/*/test.csv`;
the solution-dependent cells skip themselves for participants.

## 8. Launch checklist

- [ ] `python3 competition/make_competition_data.py` — manifest self-attack shows
      `max_punchline_occurrence` ≤ 2, `genuine_control_overlap` 0, `distinct_boring_tails` ≥ 8
- [ ] sha256 of the four CSVs matches the table above (or re-record after a re-harvest)
- [ ] local sanity: metric scores `sample_submission.csv` at exactly 0.5
- [ ] create draft competition (§2); paste all fields from `DESCRIPTION_PASTE.md`
- [ ] upload public files (§3); upload `solution_kaggle.csv` in Evaluation; select AUC; map `id`/`is_genuine`/`Usage`
- [ ] set schedule, prizes, submission limits (§6)
- [ ] dry-run while in draft: submit `sample_submission.csv` → leaderboard shows 0.500;
      submit the starter notebook's submission → public ≈ 0.580
- [ ] publish; pin welcome thread (anti-gaming note included in the paste pack)
- [ ] at close: verify top submissions offline with `metric_humor_vibes.py`
      (primary AUC + `matched_pair_accuracy` + per-control readouts) before declaring winners

## 9. Honesty notes for the host (known surfaces, by design)

- **Boring tails are still stylistically detectable** (casing/setup-echo — the
  starter's vs-boring AUC is 0.987) but they are capped: 47 of 183 test
  negatives, so a *perfect* boring-detector that is blind on shuffled controls
  lands ≈ 0.63 overall. The builder's adversarial pass accepted this ceiling
  when it removed the fixed-string tails; the shuffled controls (starter AUC
  0.47) carry the real signal. Say this out loud if someone plateaus at 0.63 —
  the paste pack's FAQ already does.
- **Public/private baseline gap** (0.580 vs 0.640) is small-sample variance,
  not leakage: the split is by row over a setup-disjoint test set.
- The public leaderboard is guidance, not a population estimate — the private
  split is the guard (design doc, Anti-gaming rules).
