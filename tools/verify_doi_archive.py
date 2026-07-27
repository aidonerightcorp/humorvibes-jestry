#!/usr/bin/env python3
"""Verify local DOI artifacts and, optionally, a published Zenodo record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from humorvibes.doi_archive import (
    DoiArchiveError,
    audit_public_zenodo_record,
    verify_doi_archive,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--record-id",
        help="published numeric Zenodo record ID; omitted for deterministic local verification",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        local = verify_doi_archive(args.root)
        payload = (
            {"local": local, "public": audit_public_zenodo_record(args.root, record_id=args.record_id)}
            if args.record_id
            else local
        )
        ok = local["ok"] and (not args.record_id or payload["public"]["ok"])
    except (DoiArchiveError, OSError, json.JSONDecodeError, KeyError) as exc:
        payload = {"ok": False, "error": str(exc)}
        ok = False
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
