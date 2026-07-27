"""Whole-tag archive determinism, provenance, and fail-closed verification."""

from __future__ import annotations

import io
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from humorvibes.doi_archive import (
    DoiArchiveError,
    REQUIRED_RELATED_URLS,
    audit_public_zenodo_record,
    build_doi_archive,
    inventory_archive,
    verify_doi_archive,
)


ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repository(tmp_path: Path, *, creator: str = "Amarel, Taylor S.") -> Path:
    root = tmp_path / "source"
    root.mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Archive Fixture")
    _git(root, "config", "user.email", "archive@example.invalid")
    (root / "CITATION.cff").write_text(
        """cff-version: 1.2.0
title: "Humor Genome Wave 2: reproducible humor-structure research and integration toolkit"
type: software
authors:
  - family-names: Amarel
    given-names: "Taylor S."
version: 1.2.3
date-released: 2026-07-27
repository-code: "https://github.com/aidonerightcorp/humorvibes-jestry"
url: "https://github.com/aidonerightcorp/humorvibes-jestry/releases/tag/v1.2.3"
license: Apache-2.0
""",
        encoding="utf-8",
    )
    zenodo = {
        "title": "Humor Genome Wave 2: reproducible humor-structure research and integration toolkit",
        "description": "Archive fixture",
        "creators": [{"name": creator}],
        "license": "Apache-2.0",
        "upload_type": "software",
        "access_right": "open",
        "keywords": ["reproducibility"],
        "related_identifiers": [
            {"identifier": url, "relation": "isSupplementedBy", "scheme": "url"}
            for url in sorted(REQUIRED_RELATED_URLS)
        ],
    }
    (root / ".zenodo.json").write_text(
        json.dumps(zenodo, indent=2) + "\n", encoding="utf-8"
    )
    (root / "README.md").write_text("exact tagged source\n", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    (nested / "unicode.txt").write_text("¿sorpresa?\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture release")
    _git(root, "tag", "-a", "v1.2.3", "-m", "fixture v1.2.3")
    return root


def test_whole_tag_archive_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    receipt = build_doi_archive(root, tag="v1.2.3", out_dir=first)
    build_doi_archive(root, tag="v1.2.3", out_dir=second)
    archive_name = receipt["artifacts"]["source_archive"]["filename"]
    assert (first / archive_name).read_bytes() == (second / archive_name).read_bytes()
    assert (first / "SHA256SUMS").read_bytes() == (second / "SHA256SUMS").read_bytes()
    inventory = json.loads((first / "source_inventory.json").read_text())
    assert [row["path"] for row in inventory["files"]] == [
        ".zenodo.json",
        "CITATION.cff",
        "README.md",
        "nested/unicode.txt",
    ]
    assert receipt["archive_state"] == "deposit_ready_not_published"
    assert receipt["external_publication"]["doi_claimed"] is False
    assert verify_doi_archive(first)["ok"] is True


def test_tampering_and_unsafe_members_fail_closed(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    out = tmp_path / "bundle"
    receipt = build_doi_archive(root, tag="v1.2.3", out_dir=out)
    archive = out / receipt["artifacts"]["source_archive"]["filename"]
    with archive.open("ab") as handle:
        handle.write(b"tampered")
    assert verify_doi_archive(out)["ok"] is False

    hostile = tmp_path / "hostile.zip"
    with zipfile.ZipFile(hostile, "w") as value:
        value.writestr("../escape.txt", "blocked")
    with pytest.raises(DoiArchiveError, match="unsafe archive member"):
        inventory_archive(hostile)


def test_metadata_drift_and_unpublished_record_ids_are_rejected(tmp_path: Path) -> None:
    root = _repository(tmp_path, creator="Different, Person")
    with pytest.raises(DoiArchiveError, match="metadata_creators_match"):
        build_doi_archive(root, tag="v1.2.3", out_dir=tmp_path / "bad")

    good_root = _repository(tmp_path / "second")
    bundle = tmp_path / "second-bundle"
    build_doi_archive(good_root, tag="v1.2.3", out_dir=bundle)
    with pytest.raises(DoiArchiveError, match="digits only"):
        audit_public_zenodo_record(bundle, record_id="reserved-not-published")


def test_anonymous_record_requires_dois_metadata_and_exact_download(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    bundle = tmp_path / "bundle"
    preflight = build_doi_archive(root, tag="v1.2.3", out_dir=bundle)
    inventory = json.loads((bundle / "source_inventory.json").read_text())
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        for row in inventory["files"]:
            member = zipfile.ZipInfo(f"humorvibes-jestry-1.2.3/{row['path']}")
            member.external_attr = (0o100000 | int(row["mode"], 8)) << 16
            archive.writestr(member, (root / row["path"]).read_bytes())
    archive_bytes = archive_buffer.getvalue()
    download_url = "https://zenodo.org/api/records/123/files/source.zip/content"
    record = {
        "id": 123,
        "pids": {"doi": {"identifier": "10.5281/zenodo.123"}},
        "parent": {"pids": {"doi": {"identifier": "10.5281/zenodo.122"}}},
        "metadata": {
            "title": preflight["metadata"]["title"],
            "version": "1.2.3",
            "creators": [
                {"person_or_org": {"name": name}}
                for name in preflight["metadata"]["creators"]
            ],
            "license": {"id": "apache-2.0"},
            "related_identifiers": [
                {"identifier": url} for url in sorted(REQUIRED_RELATED_URLS)
            ],
        },
        "files": {
            "entries": {
                "source.zip": {
                    "size": len(archive_bytes),
                    "links": {"content": download_url},
                }
            }
        },
    }

    def fetch(url: str, _maximum_bytes: int) -> bytes:
        return json.dumps(record).encode() if url.endswith("/123") else archive_bytes

    audit = audit_public_zenodo_record(bundle, record_id="123", fetcher=fetch)
    assert audit["ok"] is True
    assert audit["doi"] == "10.5281/zenodo.123"
    assert audit["concept_doi"] == "10.5281/zenodo.122"


def test_checked_in_preflight_is_complete_but_does_not_claim_a_doi() -> None:
    root = ROOT / "jestry_out" / "doi_v0_7_0_preflight"
    receipt = json.loads((root / "doi_archive_preflight.json").read_text())
    inventory = json.loads((root / "source_inventory.json").read_text())
    assert receipt["ok"] is True
    assert receipt["source"]["tag"] == "v0.7.0"
    assert receipt["source"]["tree_sha1"] == "3208dc48e7c36a7696520f7c3044c6d3bbf29890"
    assert inventory["file_count"] == 510
    assert inventory["files_digest"] == "20296c5cbfd7960a8000b545ff6e28f2cbd21082301129d8e6f9f194e499cdbc"
    computed_files_digest = hashlib.sha256(
        json.dumps(
            inventory["files"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    assert computed_files_digest == inventory["files_digest"]
    inventory_sha = hashlib.sha256((root / "source_inventory.json").read_bytes()).hexdigest()
    assert inventory_sha == receipt["artifacts"]["source_inventory"]["sha256"]
    assert receipt["external_publication"]["doi_claimed"] is False
    assert "no DOI is claimed" in (ROOT / "docs" / "DOI_ARCHIVE.md").read_text()
    workflow = (ROOT / ".github" / "workflows" / "app-contracts.yml").read_text()
    assert "tools/build_doi_archive.py" in workflow
    assert "tools/verify_doi_archive.py" in workflow
    assert "doi_v0_7_0_preflight/SHA256SUMS" in workflow
