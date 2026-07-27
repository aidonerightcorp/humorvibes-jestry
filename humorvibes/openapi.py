"""Generate the versioned OpenAPI contract used by non-Python applications."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import Settings


def openapi_schema() -> dict[str, Any]:
    from .api import create_app

    return create_app(Settings.from_env({})).openapi()


def export_openapi(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(openapi_schema(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", nargs="?", default="docs/openapi.json", type=Path)
    args = parser.parse_args()
    print(export_openapi(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
