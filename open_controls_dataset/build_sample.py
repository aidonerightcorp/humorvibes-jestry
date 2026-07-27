#!/usr/bin/env python3
"""Rebuild the committed 32-row Open Controls sample.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from humorvibes.open_controls import iter_rows, write_jsonl  # noqa: E402


OUTPUT = Path(__file__).resolve().parent / "sample_open_controls.jsonl"


def build() -> Path:
    count = write_jsonl(
        OUTPUT,
        iter_rows(families=4, configs=1, variants=2, generator_commit=None),
    )
    if count != 32:
        raise RuntimeError(f"expected 32 sample rows, wrote {count}")
    return OUTPUT


if __name__ == "__main__":
    print(build())
