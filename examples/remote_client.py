#!/usr/bin/env python3
"""Call a running HumorVibes API through the packaged typed client."""

from __future__ import annotations

import json

from humorvibes import HumorVibesClient


def main() -> None:
    client = HumorVibesClient.from_env()
    result = {
        "ready": client.ready(),
        "capabilities": client.capabilities(),
        "similarity": client.similarity(
            ["Even experts make mistakes."],
            ["A grandmaster can still blunder.", "The soup is cold."],
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
