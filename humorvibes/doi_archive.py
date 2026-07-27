"""Deterministic source-archive construction and DOI-record verification.

The builder operates on an immutable annotated Git tag, not the working tree. The
verifier compares every source file by digest so a Zenodo ZIP and a local TAR.GZ
can prove the same tree even though their container bytes differ.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse


REPOSITORY_URL = "https://github.com/aidonerightcorp/humorvibes-jestry"
TAG_PATTERN = re.compile(r"v(?P<version>\d+\.\d+\.\d+)")
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ZENODO_HOSTS = {"zenodo.org", "www.zenodo.org"}
REQUIRED_RELATED_URLS = {
    "https://www.kaggle.com/datasets/taylorsamarel/humor-genome-wave2",
    "https://www.kaggle.com/code/taylorsamarel/humor-genome-wave-2-reproducible-gemma-study",
    "https://www.kaggle.com/datasets/taylorsamarel/humor-genome-open-controls",
}
PINNED_RELEASE_IDENTITIES = {
    "v0.7.0": {
        "tag_object_sha1": "19c5f54c37cf2e05423941b7f7cd2eb911b70d35",
        "commit_sha1": "9a58dac4a81fbb512e1c939dce1a979facc7a078",
        "tree_sha1": "3208dc48e7c36a7696520f7c3044c6d3bbf29890",
    }
}


class DoiArchiveError(ValueError):
    """A release archive or public record failed a fail-closed gate."""


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo_root: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=not binary,
        timeout=180,
    )
    if completed.returncode != 0:
        stderr = (
            completed.stderr.decode("utf-8", errors="replace")
            if binary
            else completed.stderr
        )
        raise DoiArchiveError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    value = _git(repo_root, *args)
    assert isinstance(value, str)
    return value.strip()


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    value = _git(repo_root, *args, binary=True)
    assert isinstance(value, bytes)
    return value


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


def _safe_member_path(raw_name: str) -> PurePosixPath:
    name = raw_name.rstrip("/")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "" in path.parts:
        raise DoiArchiveError(f"unsafe archive member path: {raw_name!r}")
    return path


def _strip_single_prefix(entries: list[tuple[PurePosixPath, bytes, str, int]]) -> list[dict[str, Any]]:
    if not entries:
        raise DoiArchiveError("source archive contains no files")
    first_parts = {entry[0].parts[0] for entry in entries}
    if len(first_parts) != 1 or any(len(entry[0].parts) < 2 for entry in entries):
        raise DoiArchiveError("every source file must be inside one archive root directory")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path, payload, kind, mode in entries:
        relative = PurePosixPath(*path.parts[1:]).as_posix()
        if relative in seen:
            raise DoiArchiveError(f"duplicate archive member after prefix normalization: {relative}")
        seen.add(relative)
        normalized_mode = "0777" if kind == "symlink" else "0755" if mode & 0o111 else "0644"
        output.append(
            {
                "path": relative,
                "type": kind,
                "mode": normalized_mode,
                "bytes": len(payload),
                "sha256": _sha256_bytes(payload),
            }
        )
    return sorted(output, key=lambda row: row["path"])


def inventory_archive(path: Path) -> dict[str, Any]:
    """Inventory a ZIP/TAR source archive without extracting it."""

    path = Path(path)
    entries: list[tuple[PurePosixPath, bytes, str, int]] = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                safe = _safe_member_path(member.filename)
                mode = (member.external_attr >> 16) & 0o7777 or 0o644
                entries.append((safe, archive.read(member), "file", mode))
        container = "zip"
    else:
        try:
            archive = tarfile.open(path, mode="r:*")
        except tarfile.TarError as exc:
            raise DoiArchiveError("source archive must be a readable ZIP or TAR archive") from exc
        with archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                safe = _safe_member_path(member.name)
                if member.isfile():
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise DoiArchiveError(f"could not read archive member: {member.name}")
                    payload = handle.read()
                    kind = "file"
                elif member.issym():
                    payload = member.linkname.encode("utf-8")
                    kind = "symlink"
                else:
                    raise DoiArchiveError(f"unsupported archive member type: {member.name}")
                entries.append((safe, payload, kind, member.mode))
        container = "tar"
    files = _strip_single_prefix(entries)
    return {
        "container": container,
        "file_count": len(files),
        "tracked_bytes": sum(row["bytes"] for row in files),
        "files_digest": _canonical_digest(files),
        "files": files,
    }


def _load_citation(payload: bytes) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised by clean environment use
        raise DoiArchiveError(
            "PyYAML is required; run this maintainer tool with the locked dev environment"
        ) from exc
    value = yaml.safe_load(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise DoiArchiveError("CITATION.cff must parse to an object")
    return value


def _creator_names(citation: dict[str, Any]) -> list[str]:
    creators: list[str] = []
    for row in citation.get("authors", []):
        if not isinstance(row, dict):
            raise DoiArchiveError("CITATION.cff authors must be objects")
        family = str(row.get("family-names", "")).strip()
        given = str(row.get("given-names", "")).strip()
        if not family or not given:
            raise DoiArchiveError("every CITATION.cff author needs family and given names")
        creators.append(f"{family}, {given}")
    if not creators:
        raise DoiArchiveError("at least one release creator is required")
    return creators


def _metadata_at_tag(repo_root: Path, tag: str, version: str) -> dict[str, Any]:
    citation_bytes = _git_bytes(repo_root, "show", f"{tag}:CITATION.cff")
    zenodo_bytes = _git_bytes(repo_root, "show", f"{tag}:.zenodo.json")
    citation = _load_citation(citation_bytes)
    try:
        zenodo = json.loads(zenodo_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoiArchiveError(".zenodo.json at the tag is not valid UTF-8 JSON") from exc
    if not isinstance(zenodo, dict):
        raise DoiArchiveError(".zenodo.json must contain one metadata object")

    release_date = citation.get("date-released")
    release_date_text = (
        release_date.isoformat() if hasattr(release_date, "isoformat") else str(release_date)
    )
    creators = _creator_names(citation)
    zenodo_creators = [str(row.get("name", "")).strip() for row in zenodo.get("creators", [])]
    related = {
        str(row.get("identifier", ""))
        for row in zenodo.get("related_identifiers", [])
        if isinstance(row, dict)
    }
    checks = {
        "citation_version_matches_tag": str(citation.get("version")) == version,
        "citation_repository_matches": citation.get("repository-code") == REPOSITORY_URL,
        "citation_release_url_matches": citation.get("url") == f"{REPOSITORY_URL}/releases/tag/{tag}",
        "citation_license_matches": citation.get("license") == "Apache-2.0",
        "metadata_title_matches": citation.get("title") == zenodo.get("title"),
        "metadata_creators_match": creators == zenodo_creators,
        "zenodo_license_matches": zenodo.get("license") == "Apache-2.0",
        "zenodo_type_matches": zenodo.get("upload_type") == "software",
        "zenodo_access_is_open": zenodo.get("access_right") == "open",
        "related_kaggle_urls_complete": REQUIRED_RELATED_URLS.issubset(related),
        "release_date_is_iso": bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", release_date_text)),
    }
    if not all(checks.values()):
        failed = sorted(name for name, ok in checks.items() if not ok)
        raise DoiArchiveError(f"tag metadata failed: {', '.join(failed)}")
    deposition = {
        "metadata": {
            **zenodo,
            "version": version,
            "publication_date": release_date_text,
        }
    }
    return {
        "citation": citation,
        "citation_sha256": _sha256_bytes(citation_bytes),
        "zenodo": zenodo,
        "zenodo_sha256": _sha256_bytes(zenodo_bytes),
        "creators": creators,
        "release_date": release_date_text,
        "checks": checks,
        "deposition": deposition,
    }


def _tag_facts(repo_root: Path, tag: str) -> dict[str, Any]:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise DoiArchiveError("release tag must have the exact form vMAJOR.MINOR.PATCH")
    if _git_text(repo_root, "cat-file", "-t", tag) != "tag":
        raise DoiArchiveError("release ref must be an annotated tag")
    tag_object = _git_text(repo_root, "rev-parse", tag)
    commit = _git_text(repo_root, "rev-parse", f"{tag}^{{commit}}")
    tree = _git_text(repo_root, "rev-parse", f"{tag}^{{tree}}")
    tag_payload = _git_bytes(repo_root, "cat-file", "-p", tag)
    signature_present = b"BEGIN PGP SIGNATURE" in tag_payload or b"BEGIN SSH SIGNATURE" in tag_payload
    signature_verified = False
    if signature_present:
        completed = subprocess.run(
            ["git", "verify-tag", tag],
            cwd=repo_root,
            check=False,
            capture_output=True,
            timeout=60,
        )
        signature_verified = completed.returncode == 0
        if not signature_verified:
            raise DoiArchiveError("tag contains a signature that does not verify")
    facts = {
        "tag": tag,
        "version": match.group("version"),
        "annotated": True,
        "tag_object_sha1": tag_object,
        "commit_sha1": commit,
        "tree_sha1": tree,
        "commit_time": _git_text(repo_root, "show", "-s", "--format=%cI", commit),
        "signature": "verified" if signature_verified else "unsigned",
    }
    expected = PINNED_RELEASE_IDENTITIES.get(tag)
    if expected is not None and any(facts[key] != value for key, value in expected.items()):
        raise DoiArchiveError("local release identity does not match the pinned public v0.7.0 tag")
    facts["pinned_identity_match"] = expected is not None
    return facts


def _build_git_archive(repo_root: Path, commit: str, prefix: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    try:
        with temporary.open("wb") as output:
            completed = subprocess.run(
                [
                    "git",
                    "archive",
                    "--format=zip",
                    f"--prefix={prefix}/",
                    commit,
                ],
                cwd=repo_root,
                check=False,
                stdout=output,
                stderr=subprocess.PIPE,
                timeout=180,
            )
            if completed.returncode != 0:
                raise DoiArchiveError(
                    "git archive failed: "
                    + completed.stderr.decode("utf-8", errors="replace").strip()
                )
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_doi_archive(
    repo_root: Path,
    *,
    tag: str,
    out_dir: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build a deterministic whole-tag archive and deposit-ready metadata bundle."""

    repo_root = Path(repo_root).resolve()
    out_dir = Path(out_dir).resolve()
    facts = _tag_facts(repo_root, tag)
    metadata = _metadata_at_tag(repo_root, tag, facts["version"])
    slug = f"humorvibes-jestry-{tag}"
    archive_name = f"{slug}-source.zip"
    names = {
        "archive": archive_name,
        "inventory": "source_inventory.json",
        "metadata": "zenodo_deposition_metadata.json",
        "receipt": "doi_archive_preflight.json",
        "checksums": "SHA256SUMS",
    }
    targets = {key: out_dir / name for key, name in names.items()}
    existing = [path for path in targets.values() if path.exists()]
    if existing and not overwrite:
        raise DoiArchiveError(
            "refusing to overwrite DOI artifacts: " + ", ".join(path.name for path in existing)
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    _build_git_archive(repo_root, facts["commit_sha1"], slug, targets["archive"])
    observed = inventory_archive(targets["archive"])
    tracked_paths = sorted(
        line
        for line in _git_text(repo_root, "ls-tree", "-r", "--name-only", facts["commit_sha1"]).splitlines()
        if line
    )
    observed_paths = [row["path"] for row in observed["files"]]
    if observed_paths != tracked_paths:
        raise DoiArchiveError("git archive inventory does not match every tracked tag path")

    inventory = {
        "receipt_type": "humorvibes_source_inventory",
        "receipt_version": 1,
        "tag": tag,
        "commit_sha1": facts["commit_sha1"],
        "tree_sha1": facts["tree_sha1"],
        "file_count": observed["file_count"],
        "tracked_bytes": observed["tracked_bytes"],
        "files_digest": observed["files_digest"],
        "files": observed["files"],
    }
    targets["inventory"].write_bytes(_json_bytes(inventory))
    targets["metadata"].write_bytes(_json_bytes(metadata["deposition"]))
    receipt = {
        "receipt_type": "humorvibes_doi_archive_preflight",
        "receipt_version": 1,
        "ok": True,
        "archive_state": "deposit_ready_not_published",
        "source": facts,
        "metadata": {
            "title": metadata["citation"]["title"],
            "creators": metadata["creators"],
            "license": "Apache-2.0",
            "publication_date": metadata["release_date"],
            "citation_cff_sha256": metadata["citation_sha256"],
            "zenodo_json_sha256": metadata["zenodo_sha256"],
            "checks": metadata["checks"],
        },
        "artifacts": {
            "source_archive": {
                "filename": names["archive"],
                "media_type": "application/zip",
                "bytes": targets["archive"].stat().st_size,
                "sha256": _sha256_path(targets["archive"]),
            },
            "source_inventory": {
                "filename": names["inventory"],
                "bytes": targets["inventory"].stat().st_size,
                "sha256": _sha256_path(targets["inventory"]),
                "file_count": inventory["file_count"],
                "tracked_bytes": inventory["tracked_bytes"],
                "files_digest": inventory["files_digest"],
            },
            "deposition_metadata": {
                "filename": names["metadata"],
                "bytes": targets["metadata"].stat().st_size,
                "sha256": _sha256_path(targets["metadata"]),
            },
        },
        "external_publication": {
            "doi_claimed": False,
            "record_id_claimed": False,
            "anonymous_download_verified": False,
            "required_next_gate": "publish the exact tag through the owner-controlled Zenodo integration, then run the anonymous verifier",
        },
        "truth_boundary": {
            "archive_preflight_is_doi": False,
            "reserved_doi_is_published_doi": False,
            "allowed_claim": "the exact tagged source and metadata are deterministically deposit-ready",
        },
    }
    targets["receipt"].write_bytes(_json_bytes(receipt))
    checksum_paths = [targets[key] for key in ("archive", "inventory", "metadata", "receipt")]
    checksum_text = "".join(
        f"{_sha256_path(path)}  {path.name}\n" for path in checksum_paths
    )
    targets["checksums"].write_text(checksum_text, encoding="utf-8")
    return receipt


def _read_checksums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)", line)
        if not match or match.group(2) in values:
            raise DoiArchiveError("SHA256SUMS contains an invalid or duplicate row")
        values[match.group(2)] = match.group(1)
    return values


def _check(name: str, ok: bool, evidence: Any) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "evidence": evidence}


def verify_doi_archive(root: Path) -> dict[str, Any]:
    """Verify local artifact bytes, per-file inventory, metadata, and tag identity."""

    root = Path(root)
    receipt_path = root / "doi_archive_preflight.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    inventory_path = root / receipt["artifacts"]["source_inventory"]["filename"]
    archive_path = root / receipt["artifacts"]["source_archive"]["filename"]
    metadata_path = root / receipt["artifacts"]["deposition_metadata"]["filename"]
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    checksums = _read_checksums(root / "SHA256SUMS")
    checks: list[dict[str, Any]] = []
    for path in (archive_path, inventory_path, metadata_path, receipt_path):
        observed = _sha256_path(path)
        checks.append(
            _check(
                f"checksum.{path.name}",
                checksums.get(path.name) == observed,
                {"expected": checksums.get(path.name), "observed": observed},
            )
        )
    observed_archive = inventory_archive(archive_path)
    checks.extend(
        [
            _check(
                "archive.sha256",
                _sha256_path(archive_path) == receipt["artifacts"]["source_archive"]["sha256"],
                receipt["artifacts"]["source_archive"]["sha256"],
            ),
            _check(
                "archive.file_inventory",
                observed_archive["files"] == inventory["files"],
                {
                    "expected_files_digest": inventory["files_digest"],
                    "observed_files_digest": observed_archive["files_digest"],
                    "file_count": observed_archive["file_count"],
                },
            ),
            _check(
                "source.identity",
                inventory["tag"] == receipt["source"]["tag"]
                and inventory["commit_sha1"] == receipt["source"]["commit_sha1"]
                and inventory["tree_sha1"] == receipt["source"]["tree_sha1"],
                {
                    "tag": inventory["tag"],
                    "commit_sha1": inventory["commit_sha1"],
                    "tree_sha1": inventory["tree_sha1"],
                },
            ),
        ]
    )
    by_path = {row["path"]: row for row in observed_archive["files"]}
    checks.extend(
        [
            _check(
                "archive.citation_metadata",
                by_path.get("CITATION.cff", {}).get("sha256")
                == receipt["metadata"]["citation_cff_sha256"],
                by_path.get("CITATION.cff", {}).get("sha256"),
            ),
            _check(
                "archive.zenodo_metadata",
                by_path.get(".zenodo.json", {}).get("sha256")
                == receipt["metadata"]["zenodo_json_sha256"],
                by_path.get(".zenodo.json", {}).get("sha256"),
            ),
            _check(
                "publication.truth_boundary",
                receipt["external_publication"]["doi_claimed"] is False
                and receipt["external_publication"]["anonymous_download_verified"] is False,
                receipt["external_publication"],
            ),
        ]
    )
    return {
        "receipt_type": "humorvibes_doi_archive_verification",
        "receipt_version": 1,
        "ok": all(row["ok"] for row in checks),
        "checks": checks,
        "source": receipt["source"],
        "truth_boundary": receipt["truth_boundary"],
    }


def _record_files(record: dict[str, Any]) -> list[dict[str, Any]]:
    files = record.get("files")
    output: list[dict[str, Any]] = []
    if isinstance(files, dict) and isinstance(files.get("entries"), dict):
        for name, row in files["entries"].items():
            if isinstance(row, dict):
                output.append(
                    {
                        "name": str(name),
                        "url": (row.get("links") or {}).get("content"),
                        "checksum": row.get("checksum"),
                        "bytes": row.get("size"),
                    }
                )
    elif isinstance(files, list):
        for row in files:
            if isinstance(row, dict):
                output.append(
                    {
                        "name": str(row.get("key") or row.get("filename") or ""),
                        "url": (row.get("links") or {}).get("download")
                        or (row.get("links") or {}).get("self"),
                        "checksum": row.get("checksum"),
                        "bytes": row.get("size") or row.get("filesize"),
                    }
                )
    return output


def _anonymous_bytes(url: str, *, maximum_bytes: int = 250_000_000) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ZENODO_HOSTS:
        raise DoiArchiveError("public record downloads must use an official HTTPS Zenodo URL")
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "humorvibes-doi-audit/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > maximum_bytes:
                raise DoiArchiveError("public archive exceeds the verifier download limit")
            payload = response.read(maximum_bytes + 1)
    except urllib.error.HTTPError as exc:
        raise DoiArchiveError(f"anonymous Zenodo request failed with HTTP {exc.code}") from exc
    if len(payload) > maximum_bytes:
        raise DoiArchiveError("public archive exceeds the verifier download limit")
    return payload


def audit_public_zenodo_record(
    root: Path,
    *,
    record_id: str,
    fetcher: Callable[[str, int], bytes] | None = None,
) -> dict[str, Any]:
    """Verify a published Zenodo record and anonymously downloaded source archive."""

    if not re.fullmatch(r"[1-9][0-9]*", record_id):
        raise DoiArchiveError("Zenodo record ID must contain digits only")
    root = Path(root)
    preflight = json.loads((root / "doi_archive_preflight.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (root / preflight["artifacts"]["source_inventory"]["filename"]).read_text(
            encoding="utf-8"
        )
    )
    def fetch(url: str, maximum_bytes: int) -> bytes:
        return (
            fetcher(url, maximum_bytes)
            if fetcher is not None
            else _anonymous_bytes(url, maximum_bytes=maximum_bytes)
        )

    record_url = f"https://zenodo.org/api/records/{record_id}"
    record = json.loads(fetch(record_url, 5_000_000))
    doi = str(record.get("doi") or record.get("pids", {}).get("doi", {}).get("identifier") or "")
    concept_doi = str(
        record.get("conceptdoi")
        or record.get("parent", {}).get("pids", {}).get("doi", {}).get("identifier")
        or ""
    )
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    creators = []
    for row in metadata.get("creators", []):
        if not isinstance(row, dict):
            continue
        person = row.get("person_or_org") if isinstance(row.get("person_or_org"), dict) else row
        creators.append(str(person.get("name", "")))
    candidates = [
        row
        for row in _record_files(record)
        if row["name"].lower().endswith((".zip", ".tar.gz", ".tgz"))
    ]
    if len(candidates) != 1 or not isinstance(candidates[0].get("url"), str):
        raise DoiArchiveError("published record must expose exactly one source archive")
    selected = candidates[0]
    payload = fetch(selected["url"], 250_000_000)
    suffix = ".zip" if selected["name"].lower().endswith(".zip") else ".tar.gz"
    with tempfile.TemporaryDirectory(prefix="humorvibes-doi-audit-") as temporary:
        archive_path = Path(temporary) / f"record{suffix}"
        archive_path.write_bytes(payload)
        observed = inventory_archive(archive_path)
    record_license = metadata.get("license")
    if isinstance(record_license, dict):
        record_license = record_license.get("id") or record_license.get("title")
    normalized_license = re.sub(r"[^a-z0-9]", "", str(record_license).lower())
    related = {
        str(row.get("identifier", ""))
        for row in metadata.get("related_identifiers", [])
        if isinstance(row, dict)
    }
    checks = [
        _check("record.version_doi", bool(DOI_PATTERN.fullmatch(doi)), doi or None),
        _check(
            "record.concept_doi",
            bool(DOI_PATTERN.fullmatch(concept_doi)),
            concept_doi or None,
        ),
        _check("record.title", metadata.get("title") == preflight["metadata"]["title"], metadata.get("title")),
        _check("record.version", str(metadata.get("version")) == preflight["source"]["version"], metadata.get("version")),
        _check("record.creators", creators == preflight["metadata"]["creators"], creators),
        _check(
            "record.license",
            normalized_license in {"apache20", "apache2license"},
            record_license,
        ),
        _check(
            "record.related_kaggle_urls",
            REQUIRED_RELATED_URLS.issubset(related),
            sorted(related),
        ),
        _check(
            "record.source_inventory",
            observed["files"] == inventory["files"],
            {
                "expected_files_digest": inventory["files_digest"],
                "observed_files_digest": observed["files_digest"],
                "anonymous_archive_sha256": _sha256_bytes(payload),
                "anonymous_archive_bytes": len(payload),
            },
        ),
    ]
    return {
        "receipt_type": "humorvibes_doi_publication_audit",
        "receipt_version": 1,
        "ok": all(row["ok"] for row in checks),
        "record_id": record_id,
        "record_api_url": record_url,
        "doi": doi or None,
        "concept_doi": concept_doi or None,
        "source": preflight["source"],
        "checks": checks,
        "truth_boundary": {
            "verified": "anonymous record metadata, registered DOI presence, download, and exact per-file tag identity",
            "not_verified": "scientific validity, future availability, or identity claims beyond deposited metadata",
        },
    }
