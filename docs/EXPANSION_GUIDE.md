# Expansion guide

*Role: the layer-by-layer contribution playbook. Audience: contributors.*

This guide is for extending Humor Genome Wave 2 without weakening its provenance, licensing, or
evidence boundaries. All commands are run from the repository root.

## 1. Choose the layer you are changing

| Layer | Primary files | Required evidence |
| --- | --- | --- |
| Source acquisition | `wave2_specs.json`, `harvest_wave2.py`, `harvest_supply.py` | Live schema/licence check, sample receipt, parser fixtures |
| Rights and census | `corpus_census.py`, `build_kaggle_export.py` | Licence-class tests, exclusion counts, deterministic export |
| Form/domain/style | `style_taxonomy.py`, `STYLES.md` | Positive/negative fixtures, coverage and false-positive audit |
| Human labels | `caption_*.py`, `humor_features.py` | Group-held-out split, reliability, uncertainty, provenance |
| Multimodal labels | `humorvibes/multimodal_benchmark.py`, image/caption manifests | Rights, image hashes, contest groups, identical-arm row digest |
| Gemma measurement | `form_signal_study.py`, `mesh_signals.py`, `wave2_notebook/` | Pinned calibration, model identity, token accounting, controls |
| Public release | `wave2_dataset/`, `wave2_notebook/`, `verify_wave2_release.py` | Hash and semantic gates, COMPLETE notebook, publication receipt |

Do not change multiple layers in one first pull request. A new source plus a new taxonomy plus a
new model makes any observed difference uninterpretable.

## 2. Add or validate a source

Start with a real upstream fetch, its dataset card or terms, and the exact served fields. A source
enters `wave2_specs.json` only after those checks.

Run the committed no-network preflight before learning the large harvest pipeline:

```bash
python3 source_spec_preflight.py
```

That command validates the four-row CC BY 2.0 fixture in
`fixtures/source_preflight/colbert_humor/`, compares the shared parser output byte-for-byte with
the committed expectation, checks unique upstream row IDs, applies the deny-first licence policy,
prints a body-free receipt, and writes nothing to `corpora/`. The expected final gates are
`ok: true`, `parser.expected_fixture_match: true`, and
`release_decision.export_eligible: true`.

After the fixture passes, explicitly opt into a bounded live check:

```bash
python3 source_spec_preflight.py --live --limit 4 --timeout 15 \
  --out jestry_out/source_spec_preflight_live.json
```

Live mode contacts only `huggingface.co` and `datasets-server.huggingface.co`, accepts at most 25
rows and two megabytes per response, uses strict UTF-8/JSON decoding, compares the observed
dataset identity and licence ID with the source spec, records response hashes, and still never
adds corpus rows. Research-only sources may pass parser/provenance validation while correctly
returning `export_eligible: false`. Missing or contradictory licence evidence, schema drift,
empty data, duplicate row IDs, malformed JSON, invalid encoding, or expectation drift fail closed.

For a new Hugging Face source, copy that three-file fixture shape into a directory named for the
actual source key, replace it with a bounded observed response and exact expected normalized rows,
and pass those three concrete paths through `--spec`, `--fixture`, and `--expected`. Attach the
resulting receipt to the pull request, then register the reviewed spec in `wave2_specs.json`.

The existing `chinese_memes` lane is a concrete smoke-test example.

```bash
python3 harvest_wave2.py list
python3 harvest_wave2.py hf --arg chinese_memes --limit 25
python3 -m pytest -q tests/test_wave2.py
```

For a new Hugging Face source:

1. Record repository, config, split, text field, label fields, language, translation field when
   present, exact upstream licence text, and a dated verification note in `wave2_specs.json`.
2. If redistribution is not explicit, label it accurately. The source may support local research,
   but its text must not enter the public payload.
3. Add a tiny synthetic or openly redistributable fixture that exercises its schema. Do not make a
   live API response the only test.
4. Run a bounded harvest before a large one. After registration, set the shell variable to the
   new spec key:

```bash
source_key=chinese_memes
python3 harvest_wave2.py hf --arg "$source_key" --limit 200
```

5. Inspect the resulting JSONL header and several records. Confirm `text`, `source`, `license`,
   `language`, upstream labels, and translation metadata survived ingestion.
6. Run exact deduplication through the shared harvester. Do not add a one-off writer that bypasses
   checkpointing, screening, or provenance.

Source acceptance checklist:

- the offline source-spec preflight and, when applicable, bounded live preflight pass;
- a live response was observed and dated;
- field mapping matches the response, including headerless or nested schemas;
- per-row provenance and licence are preserved;
- partial downloads and malformed rows fail visibly;
- duplicate handling is deterministic;
- a committed fixture covers the parser;
- public redistribution is allowed by evidence, not inferred from availability.

## 3. Add a native humor form

Form is structural, domain is lexical, and source-declared style is provenance. Keep the axes
separate.

```bash
python3 style_taxonomy.py selftest
python3 style_taxonomy.py report
python3 -m pytest -q tests/test_wave2.py
```

Add the most specific structural rule before a broader rule in `FORM_RULES`. Add positive fixtures
that include spelling and punctuation variation, plus negative fixtures containing the same key
words outside the form. Inspect a deterministic sample of matches from the real language corpus.
Report both coverage and sample precision; a higher match count is not automatically an
improvement.

For non-English additions, include a note from a competent speaker or reviewer. Machine-translated
English templates are not evidence of a native form. Script-aware minimum length and Unicode word
boundaries need explicit regression cases.

Use the complete one-language review contract in
[`NATIVE_LANGUAGE_CONTRIBUTIONS.md`](NATIVE_LANGUAGE_CONTRIBUTIONS.md). The validator requires 20
positives, 20 hard negatives, explicit fixture rights, a pseudonymous human attestation,
before/after coverage, manual false-positive review, and aligned-pair consistency when applicable:

```bash
humorvibes native-fixture-validate /tmp/native-review.json \
  --out /tmp/native-review-receipt.json
```

Do not use `shaggy_dog` in domain-by-form analysis: it is a length proxy. Exclude generic forms
when claiming a meaningful domain/form pairing.

## 4. Add a human-label experiment

Before training, write down:

1. the unit of analysis;
2. what the label records and who produced it;
3. shared contexts that define groups;
4. the held-out split;
5. the primary metric and interval;
6. label reliability or disagreement;
7. baselines and leakage checks;
8. the receipt path and stopping rule.

Caption experiments must hold out entire contests. Similar structures apply to authors, source
families, prompts, audiences, or repeated items. A row-random split is invalid when these groups
cross train and test.

The existing public baselines can be rebuilt from the full local caption inventory with:

```bash
python3 caption_ceiling.py
python3 caption_portability.py
python3 caption_model.py
```

These are long-running research jobs and are not required for a documentation contribution. Keep
core results atomically checkpointed before optional transfer arms. Never replace a previous
receipt if the protocol changes; version the new result and explain the difference.

### 4a. Add rights-cleared drawings and multimodal features

Run the complete synthetic contract before touching human or third-party material:

```bash
humorvibes multimodal-fixture --out-dir /tmp/humorvibes-mm --contests 30
humorvibes multimodal-benchmark --root /tmp/humorvibes-mm
humorvibes multimodal-human-contract --out /tmp/human-mm-contract.json
```

Then follow [`MULTIMODAL_BENCHMARK.md`](MULTIMODAL_BENCHMARK.md). Preserve its manifest fields,
stable contest IDs, split membership, exact image hashes, canonical scene signatures, three arm
names, feature dimensions, and held-out row digest. Replace `target_origin` with an explicit
human-observed target only after consent, rights, raw vote provenance, and the label protocol are
reviewable. Never copy a third-party drawing into the repository just because it is reachable on
the web. A real run requires its own versioned receipt; it must not overwrite the procedural
positive-control receipt.

For a real cohort, install `.[multimodal]` and run `multimodal-human-validate` before
`multimodal-human-benchmark`. The former recomputes image byte and perceptual hashes, verifies
every local rights/evidence digest, rejects direct participant identity, and holds the external
rights-and-research-review gate closed. A dataset-level licence is not a substitute for one
rights-ledger row per asset.

## 5. Add or compare a model instrument

An instrument comparison must keep the item sample, setup/punchline split, token mask, aggregation,
and controls fixed. Record the exact model source, revision, precision, quantization, device, and
library versions.

The canonical Gemma path lives in `wave2_notebook/build_wave2_notebook.py`. Rebuild the notebook
deterministically and run its local structural checks with:

```bash
python3 wave2_notebook/build_wave2_notebook.py
python3 -m pytest -q tests/test_wave2.py
git diff --exit-code -- wave2_notebook/humor_genome_wave2.ipynb
```

The Kaggle run must pass the pinned `S = 3.19` reference before downstream values are accepted.
Changing the tokenizer, checkpoint, split, or averaging convention requires a new calibration
receipt, not a wider tolerance chosen after seeing the result.

For a larger form study, pre-register the arm sizes, sampling strata, exclusion rules, bootstrap
method, separation criterion, and source-held-out sensitivity analysis. Preserve the current null
result as the original small-sample run.

## 6. Build and verify a public dataset candidate

This step requires the full local `corpora/` inventory. It does not publish anything by itself.

```bash
python3 build_kaggle_export.py --per-family 12000 \
  --corpora-dir corpora --out-dir kaggle_wave2 \
  --metadata-template wave2_dataset/dataset-metadata.json
python3 verify_wave2_release.py --root kaggle_wave2
```

Review `export_summary.json`, `census.json`, `DATA_CARD.md`, and `manifest.json`. Investigate every
unexpected change in counts, licence classes, largest-family share, languages, aligned pairs, or
frames. Rebuild twice and compare hashes when selection or serialization changes.

Only a maintainer publishes the candidate:

```bash
kaggle datasets version -p kaggle_wave2 -m "Explain the verified dataset change"
```

Publication is not complete until the remote file list is checked, the canonical notebook runs
COMPLETE against that version, anonymous URLs load, and `jestry_out/wave2_publication.json` is
updated from observed evidence.

## 7. Definition of done

An expansion is done when:

- the hypothesis or maintenance outcome is stated;
- provenance and redistribution rights are explicit;
- fixtures cover both success and failure cases;
- the relevant local tests pass;
- group leakage and confounds were checked;
- uncertainty accompanies measured comparisons;
- negative or null results remain in the artifact;
- generated payloads are kept out of Git;
- reader-facing claims link to a receipt;
- public status is claimed only after live verification.

Use [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the pull-request contract and
[`ROADMAP.md`](../ROADMAP.md) to choose the next bounded contribution.
