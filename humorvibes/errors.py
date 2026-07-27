"""Sanitized errors shared by transports, SDK calls, and the HTTP API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IntegrationError(Exception):
    code: str
    message: str
    status_code: int = 502
    retryable: bool = False
    detail: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def public(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload
