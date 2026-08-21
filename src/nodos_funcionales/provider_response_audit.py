from __future__ import annotations

import gzip
import json
import os
import ssl
import sys
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProviderResponse:
    payload: Any | None
    url: str
    http_status: int | str
    content_type: str
    payload_type: str
    rejection_reason: str
    error_status: str
    headers: dict[str, str] = field(default_factory=dict)


def request_provider_payload(
    url: str,
    *,
    timeout: float,
    user_agent: str,
    accept: str,
    opener: Any = urlopen,
    data: bytes | None = None,
) -> ProviderResponse:
    """Fetch a provider URL and classify the payload without making biological claims."""
    try:
        context = None
        if opener is urlopen and sys.platform == "win32" and os.environ.get("NODOS_ALLOW_WINDOWS_REAL_HTTPS") != "1":
            return ProviderResponse(None, url, "", "", "ssl_error", "ssl_error:windows_real_https_requires_diagnostic_opt_in", "ssl_error")
        if opener is urlopen and sys.platform != "win32":
            from .online_http import get_ssl_context

            context = get_ssl_context()
        headers = {"User-Agent": user_agent, "Accept": accept}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=data, headers=headers)
        with opener(request, timeout=timeout, context=context) as response:
            raw = response.read()
            status = _response_status(response)
            content_type = _response_content_type(response)
            final_url = _response_url(response, url)
            response_headers = _response_headers(response)
        payload, payload_type, reason = classify_payload(raw, content_type)
        return ProviderResponse(
            payload=payload,
            url=final_url,
            http_status=status,
            content_type=content_type,
            payload_type=payload_type,
            rejection_reason=reason,
            error_status="",
            headers=response_headers,
        )
    except HTTPError as exc:
        content_type = ""
        raw = b""
        try:
            content_type = str(exc.headers.get("Content-Type", "") if exc.headers else "")
            raw = exc.read()
        except Exception:  # noqa: BLE001 - best-effort provenance for failed providers.
            pass
        _, payload_type, reason = classify_payload(raw, content_type)
        status = "not_found" if exc.code == 404 else ("auth_or_permission_error" if exc.code in {401, 403} else "http_error")
        return ProviderResponse(
            None,
            url,
            int(exc.code),
            content_type,
            payload_type,
            reason or f"HTTP {exc.code}",
            status,
            headers={str(key).lower(): str(value) for key, value in (exc.headers.items() if exc.headers else [])},
        )
    except ssl.SSLError as exc:
        return ProviderResponse(None, url, "", "", "ssl_error", f"ssl_error:{exc}", "ssl_error")
    except URLError as exc:
        return ProviderResponse(None, url, "", "", "network_error", f"network_error:{exc.reason}", "unresolved")
    except TimeoutError:
        return ProviderResponse(None, url, "", "", "timeout", "timeout", "unresolved")
    except UnicodeDecodeError as exc:
        return ProviderResponse(None, url, "", "", "undecodable", f"undecodable_response:{exc}", "unresolved")


def classify_payload(raw: bytes, content_type: str = "") -> tuple[Any | None, str, str]:
    if not raw:
        return None, "empty", "empty_payload"
    if raw.startswith(b"PK\x03\x04"):
        return None, "zip", "unsupported_structured_archive"
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass
    text = raw.decode("utf-8")
    lowered_type = str(content_type or "").lower()
    stripped = text.lstrip()
    if "html" in lowered_type or stripped.lower().startswith(("<!doctype html", "<html")):
        return None, "html", "html_instead_of_structured_payload"
    if "xml" in lowered_type or stripped.startswith("<?xml") or stripped.startswith("<"):
        return text, "xml", ""
    try:
        return json.loads(text), "json", ""
    except json.JSONDecodeError:
        pass
    if "\t" in text and len([line for line in text.splitlines() if line.strip()]) >= 2:
        return text, "tabular_text", ""
    return text, "unexpected_text", "unexpected_payload_type"


def response_audit_fields(response: ProviderResponse, *, affects_score: bool = False) -> dict[str, Any]:
    return {
        "provider_url": response.url,
        "http_status": response.http_status,
        "content_type": response.content_type,
        "payload_type": response.payload_type,
        "rejection_reason": response.rejection_reason,
        "content_range": response.headers.get("content-range", ""),
        "affects_score": bool(affects_score),
    }


def _response_status(response: Any) -> int | str:
    if hasattr(response, "status"):
        return int(response.status)
    if hasattr(response, "getcode"):
        value = response.getcode()
        return int(value) if value is not None else ""
    return 200


def _response_content_type(response: Any) -> str:
    if hasattr(response, "headers") and response.headers:
        value = response.headers.get("Content-Type", "")
        if value:
            return str(value)
    if hasattr(response, "getheader"):
        return str(response.getheader("Content-Type", "") or "")
    return ""


def _response_url(response: Any, fallback: str) -> str:
    if hasattr(response, "url") and response.url:
        return str(response.url)
    if hasattr(response, "geturl"):
        value = response.geturl()
        return str(value) if value else fallback
    return fallback


def _response_headers(response: Any) -> dict[str, str]:
    if hasattr(response, "headers") and response.headers:
        try:
            return {str(key).lower(): str(value) for key, value in response.headers.items()}
        except AttributeError:
            pass
    headers = {}
    if hasattr(response, "getheader"):
        for name in ("Content-Range", "Content-Length", "ETag"):
            value = response.getheader(name, "")
            if value:
                headers[name.lower()] = str(value)
    return headers

