#!/usr/bin/env python3
"""Run the SDK entirely offline; no server, key, or model download required."""

from __future__ import annotations

import json

from humorvibes import HumorVibesService, Settings


def main() -> None:
    service = HumorVibesService(Settings.from_env({}))
    result = {
        "ready": service.ready(),
        "embedding": service.embed(["same comic frame", "different surface words"]),
        "similarity": service.similarity(
            ["Even experts make mistakes."],
            ["A grandmaster can still blunder.", "The soup is cold."],
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
