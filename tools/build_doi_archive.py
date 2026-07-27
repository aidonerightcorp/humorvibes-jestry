#!/usr/bin/env python3
"""Build a whole-tag DOI bundle with a canonical per-file source identity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from humorvibes.doi_archive import DoiArchiveError, build_doi_archive


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--tag", default="v0.7.0")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        receipt = build_doi_archive(
            args.repo_root, tag=args.tag, out_dir=args.out_dir, overwrite=args.force
        )
    except (DoiArchiveError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
