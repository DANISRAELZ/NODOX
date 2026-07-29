from __future__ import annotations

import json
import os
import ssl
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import certifi


def get_ssl_context() -> ssl.SSLContext:
    """Return a verified context that trusts both the system store and certifi."""
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def urlopen_json(url: str, timeout: float = 30, headers: dict[str, str] | None = None) -> Any:
    if sys.platform == "win32" and os.environ.get("NODOS_ALLOW_WINDOWS_REAL_HTTPS") != "1":
        raise URLError("windows_real_https_requires_diagnostic_opt_in")
    request = Request(url, headers=headers or {})
    context = None if sys.platform == "win32" else get_ssl_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def urlopen_text(url: str, timeout: float = 30, headers: dict[str, str] | None = None) -> str:
    if sys.platform == "win32" and os.environ.get("NODOS_ALLOW_WINDOWS_REAL_HTTPS") != "1":
        raise URLError("windows_real_https_requires_diagnostic_opt_in")
    request = Request(url, headers=headers or {})
    context = None if sys.platform == "win32" else get_ssl_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        return response.read().decode("utf-8")


def requests_get_json(
    url: str,
    timeout: float = 30,
    params: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    import requests

    response = requests.get(
        url,
        timeout=timeout,
        params=params,
        headers=headers,
        verify=certifi.where(),
    )
    response.raise_for_status()
    return response.json()


def classify_provider_failure(message: object) -> str:
    text = str(message or "").lower()
    if "not_found" in text or "not found" in text or "http 404" in text or "404" in text:
        return "not_found"
    if "certificate_verify_failed" in text or "ssl:" in text or "ssl_error" in text or "cert" in text:
        return "tls_certificate_verification_failed"
    if "timed out" in text or "timeout" in text:
        return "timeout"
    if "http " in text:
        return "http_error"
    if "mapping" in text:
        return "mapping_failed"
    if "not implemented" in text:
        return "provider_not_implemented"
    if "network" in text or "urlerror" in text:
        return "provider_unavailable"
    return "provider_unavailable"
