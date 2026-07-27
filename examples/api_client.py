#!/usr/bin/env python3
"""Call a running HumorVibes API using only the Python standard library."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

BASE_URL = os.environ.get("HUMORVIBES_URL", "http://127.0.0.1:8080").rstrip("/")
API_KEY = os.environ.get("HUMORVIBES_API_KEY", "")


def request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(call, timeout=30) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError("API response was not a JSON object")
    return parsed


def main() -> None:
    result = {
        "live": request("/health/live"),
        "capabilities": request("/v1/capabilities"),
        "embedding": request("/v1/embed", {"texts": ["comic timing", "timing a joke"]}),
        "similarity": request(
            "/v1/similarity",
            {"left": ["Even experts slip."], "right": ["A master can blunder.", "Warm soup."]},
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
