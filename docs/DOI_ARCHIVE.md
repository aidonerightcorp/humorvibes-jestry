# DOI archive: exact source, current state, and publication gate

*Role: deposit-readiness for the frozen v0.7.0 tag (issue #9). Audience: the repository owner. No DOI is claimed.*

## Executive summary

The v0.7.0 software release is ready for an owner-controlled archive deposit, but it does **not**
yet have a DOI. v0.7.0 remains the deposit target because its per-file inventory digest is already
frozen and CI-verified; v0.8.0 gets archived after issue
[#9](https://github.com/aidonerightcorp/humorvibes-jestry/issues/9) closes on the earlier tag.
An anonymous Zenodo search on 2026-07-27 returned zero matching records, no Zenodo
credential is available in the project environment, and repository-account linking cannot be
honestly inferred from source files. Issue
[#9](https://github.com/aidonerightcorp/humorvibes-jestry/issues/9) therefore remains open.

The reproducibility work before that external action is complete. The archive builder reads 100%
of the immutable `v0.7.0` Git tag—not the current checkout—validates `CITATION.cff` and
`.zenodo.json`, creates one source ZIP, inventories every file, and emits checksums and
deposit-ready metadata. The verifier reopens the archive without extracting it and compares every
file digest. Its live mode also downloads a published Zenodo archive anonymously and accepts ZIP
or TAR packaging only when its normalized file inventory is identical to the tag.

## Frozen v0.7.0 identity

| field | verified value |
| --- | --- |
| annotated tag | `v0.7.0` (historical tag is unsigned; it was not rewritten) |
| tag object | `19c5f54c37cf2e05423941b7f7cd2eb911b70d35` |
| commit | `9a58dac4a81fbb512e1c939dce1a979facc7a078` |
| Git tree | `3208dc48e7c36a7696520f7c3044c6d3bbf29890` |
| tracked source | 510 files; 60,695,692 bytes |
| normalized inventory digest | `20296c5cbfd7960a8000b545ff6e28f2cbd21082301129d8e6f9f194e499cdbc` |
| reference ZIP build | 23,308,329 bytes; SHA-256 `5b62f01ffb89d5e8bb67a5572fac687e406aecc01f57458a6a19b27929cbe526` |
| creator metadata | `Amarel, Taylor S.` in both metadata files |
| licence | Apache-2.0 in both metadata files |

The compact checked-in evidence is in
[`jestry_out/doi_v0_7_0_preflight`](../jestry_out/doi_v0_7_0_preflight). The 23.3 MB archive is
intentionally rebuilt rather than nested inside later source releases.

The outer ZIP checksum records the exact reference container built for deposit; it is not the
cross-toolchain source identity. Git/ZIP versions may package identical files into different
container bytes. The controlling identity is the normalized 510-file digest above, and CI compares
that complete inventory plus deposition metadata. The local verifier still checks each build's
own outer checksum before checking every member.

## Rebuild and verify every tagged file

```bash
uv sync --frozen --extra dev
uv run --frozen --extra dev python tools/build_doi_archive.py \
  --tag v0.7.0 \
  --out-dir dist/doi/v0.7.0
uv run --frozen --extra dev python tools/verify_doi_archive.py \
  --root dist/doi/v0.7.0 \
  --out dist/doi/v0.7.0/verification.json
```

The build refuses lightweight tags, metadata/version drift, incomplete Kaggle related identifiers,
unsafe archive paths, missing files, duplicate normalized paths, or an existing output unless
`--force` is explicit. The verifier fails on outer checksum drift or any per-file difference.

## The one owner-account action that remains

Zenodo's official GitHub flow requires the repository owner to link the GitHub account, sync and
enable the repository, then archive the release. The integration and release controls live inside
the owner's Zenodo session; GitHub repository permission alone cannot perform that account action.

1. Open [Zenodo's repository-enablement page](https://help.zenodo.org/docs/github/enable-repository/)
   while signed in as the repository owner, select **GitHub**, choose **Sync now**, find
   `aidonerightcorp/humorvibes-jestry`, and enable it.
2. Because Zenodo documents automatic ingestion for **new** releases and `v0.7.0` already exists,
   first check whether the enabled-repository page offers an archive action for that release. If
   it does, use it. If it does not, follow Zenodo's
   [manual software upload](https://help.zenodo.org/docs/github/archive-software/manual-upload/):
   create one Software record containing only the generated
   `humorvibes-jestry-v0.7.0-source.zip`, then enter the exact values from
   `zenodo_deposition_metadata.json`. Do not move or recreate the Git tag.
3. Wait until the record is public and the page shows a DOI. A reserved DOI or draft is not enough.
4. Copy the numeric record ID, run the anonymous verifier below, and only continue if every gate
   passes.

```bash
read -r HUMORVIBES_ZENODO_RECORD_ID
uv run --frozen --extra dev python tools/verify_doi_archive.py \
  --root dist/doi/v0.7.0 \
  --record-id "${HUMORVIBES_ZENODO_RECORD_ID}" \
  --out jestry_out/v0_7_0_archive_publication.json
```

The live audit requires a registered DOI, exact title/version/creator metadata, one anonymously
downloadable source archive, and all 510 file digests. It does not trust a record page or filename
alone.

## Final source update after the live audit

Open a new pull request that adds the audit receipt and the returned concept/version DOI to
`CITATION.cff`, README, and release notes. Link the DOI to the exact archived v0.7.0 version and
retain the Kaggle dataset/notebook identifiers. Close issue #9 only after an anonymous rerun of the
receipt succeeds.

Until then the precise claim is: **the exact v0.7.0 file inventory is deposit-ready; no DOI is
claimed.**
