"""Small hardened JSON transport used by every hosted integration."""

from __future__ import annotations

import ipaddress
import json
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .errors import IntegrationError

_SAFE_ERROR = re.compile(r"[^\x20-\x7e]+")


def normalize_base_url(value: str, *, allow_insecure_remote: bool = False) -> str:
    raw = value.strip().rstrip("/")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise IntegrationError("invalid_base_url", "Integration base URL must use http or https.", 500)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise IntegrationError(
            "invalid_base_url",
            "Integration base URL cannot contain credentials, a query, or a fragment.",
            500,
        )
    if "\\" in parsed.path or "//" in parsed.path or any(
        segment in {".", ".."} for segment in parsed.path.split("/")
    ):
        raise IntegrationError("invalid_base_url", "Integration base URL path is invalid.", 500)
    host = parsed.hostname.lower()
    if parsed.scheme == "http" and not allow_insecure_remote and not _is_internal_host(host):
        raise IntegrationError(
            "insecure_remote_url",
            "Plain HTTP is allowed only for local or private-network integrations.",
            500,
        )
    clean_netloc = f"[{host}]" if ":" in host else host
    if parsed.port:
        clean_netloc = f"{clean_netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, clean_netloc, parsed.path.rstrip("/"), "", ""))


def base_url_is_internal(value: str) -> bool:
    """Report location without DNS resolution; configuration remains operator-trusted."""

    host = urlsplit(value).hostname
    return bool(host and _is_internal_host(host.lower()))


def _is_internal_host(host: str) -> bool:
    if host in {"localhost", "host.docker.internal"} or host.endswith((".local", ".svc", ".cluster.local")):
        return True
    if "." not in host:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class JsonHttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str = "",
        timeout: float = 120.0,
        max_response_bytes: int = 10_000_000,
        allow_insecure_remote: bool = False,
        opener: Any = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url, allow_insecure_remote=allow_insecure_remote)
        self._api_key = api_key
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self._opener = opener or urllib.request.build_opener(_NoRedirect())

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key)

    def request(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        method: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if (
            not path.startswith("/")
            or "//" in path
            or "?" in path
            or "#" in path
            or "\\" in path
            or "%" in path
            or any(segment in {".", ".."} for segment in path.split("/"))
        ):
            raise IntegrationError("invalid_endpoint", "Integration endpoint path is invalid.", 500)
        headers = {
            "Accept": "application/json",
            "User-Agent": "HumorVibes/0.3",
            **(extra_headers or {}),
        }
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method or ("POST" if payload is not None else "GET"),
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                length = response.headers.get("Content-Length") if getattr(response, "headers", None) else None
                if length:
                    try:
                        announced_length = int(length)
                    except (TypeError, ValueError):
                        raise IntegrationError(
                            "invalid_upstream_headers",
                            "Upstream returned an invalid Content-Length header.",
                            502,
                        ) from None
                    if announced_length < 0:
                        raise IntegrationError(
                            "invalid_upstream_headers",
                            "Upstream returned an invalid Content-Length header.",
                            502,
                        )
                    if announced_length > self.max_response_bytes:
                        raise IntegrationError("upstream_response_too_large", "Upstream response exceeded the configured limit.", 502)
                raw = response.read(self.max_response_bytes + 1)
        except IntegrationError:
            raise
        except urllib.error.HTTPError as exc:
            raw = exc.read(min(self.max_response_bytes, 4096))
            message = self._error_message(raw, f"HTTP {exc.code}")
            raise IntegrationError(
                "upstream_http_error",
                message,
                502,
                retryable=exc.code in {408, 409, 425, 429, 500, 502, 503, 504},
                detail={"upstream_status": exc.code},
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise IntegrationError(
                "upstream_unreachable",
                self._redact(f"{type(exc).__name__}: {exc}"),
                503,
                retryable=True,
            ) from None
        if not isinstance(raw, bytes):
            raise IntegrationError("invalid_upstream_body", "Upstream response body must be bytes.", 502)
        if len(raw) > self.max_response_bytes:
            raise IntegrationError("upstream_response_too_large", "Upstream response exceeded the configured limit.", 502)
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise IntegrationError("invalid_upstream_json", "Upstream returned invalid JSON.", 502) from None
        if not isinstance(decoded, dict):
            raise IntegrationError("invalid_upstream_shape", "Upstream JSON must be an object.", 502)
        return decoded

    def _error_message(self, raw: bytes, fallback: str) -> str:
        try:
            decoded = json.loads(raw.decode("utf-8", "replace"))
            if isinstance(decoded, dict):
                value = decoded.get("error", decoded.get("message", fallback))
                if isinstance(value, dict):
                    value = value.get("message", fallback)
                return self._redact(str(value))
        except json.JSONDecodeError:
            pass
        return self._redact(raw.decode("utf-8", "replace") or fallback)

    def _redact(self, value: str) -> str:
        text = _SAFE_ERROR.sub(" ", value).strip()[:500]
        if self._api_key:
            text = text.replace(self._api_key, "[REDACTED]")
        return text or "Upstream request failed."
