from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ENDPOINT_SPEC_VERSION = "7H-2026-06-22"
ALLOWED_ENDPOINT_STATUSES = {
    "verified_structured_payload",
    "verified_empty_payload",
    "html_instead_of_structured_payload",
    "not_found_404",
    "unavailable",
    "requires_manual_download",
    "requires_format_adapter",
    "deprecated_or_changed",
    "unresolved",
}
REQUIRED_FIELDS = {
    "provider_name", "base_url", "query_url_template", "expected_format", "method",
    "required_parameters", "optional_parameters", "stable_download_url", "documentation_url",
    "last_verified_at", "endpoint_status", "notes", "interpretation_warning",
}
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "external_provider_endpoints.json"


def _load_specs(config_path: Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("endpoint_spec_version") != ENDPOINT_SPEC_VERSION:
        raise ValueError(
            f"endpoint specification version mismatch: expected {ENDPOINT_SPEC_VERSION}, "
            f"found {payload.get('endpoint_spec_version')}"
        )
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        raise ValueError("external provider endpoint configuration requires a providers object")
    for provider, spec in providers.items():
        validate_external_provider_endpoint_spec(spec, expected_provider=provider)
    return payload


def validate_external_provider_endpoint_spec(
    spec: Any, *, expected_provider: str | None = None, raise_on_error: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(spec, dict):
        errors.append("endpoint specification must be an object")
        spec = {}
    missing = sorted(field for field in REQUIRED_FIELDS if field not in spec)
    errors.extend(f"missing required field: {field}" for field in missing)
    if expected_provider and spec.get("provider_name") != expected_provider:
        errors.append("provider_name does not match configuration key")
    if spec.get("endpoint_status") not in ALLOWED_ENDPOINT_STATUSES:
        errors.append("endpoint_status is not allowed")
    if spec.get("method") not in {"GET", "POST"}:
        errors.append("method must be GET or POST")
    for field in ("base_url", "query_url_template"):
        value = str(spec.get(field, ""))
        if urlparse(value).scheme not in {"http", "https"}:
            errors.append(f"{field} must be an HTTP(S) URL")
    for field in ("required_parameters", "optional_parameters"):
        if field in spec and not isinstance(spec[field], list):
            errors.append(f"{field} must be a list")
    if _contains_true_score_effect(spec):
        errors.append("affects_score=true is forbidden in endpoint specifications")
    result = {"valid": not errors, "errors": sorted(set(errors))}
    if errors and raise_on_error:
        raise ValueError("invalid external provider endpoint specification: " + "; ".join(result["errors"]))
    return result


def _contains_true_score_effect(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            (str(key).lower() == "affects_score" and item is True) or _contains_true_score_effect(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_true_score_effect(item) for item in value)
    return False


def list_external_provider_endpoint_specs(config_path: Path | None = None) -> list[dict[str, Any]]:
    payload = _load_specs(config_path)
    return [
        {"endpoint_spec_version": payload["endpoint_spec_version"], **copy.deepcopy(spec)}
        for spec in payload["providers"].values()
    ]


def _get(provider: str, config_path: Path | None = None) -> dict[str, Any]:
    specs = {item["provider_name"]: item for item in list_external_provider_endpoint_specs(config_path)}
    if provider not in specs:
        raise KeyError(f"missing endpoint specification for {provider}")
    return specs[provider]


def get_vfdb_endpoint_specs(config_path: Path | None = None) -> dict[str, Any]:
    return _get("VFDB", config_path)


def get_deg_endpoint_specs(config_path: Path | None = None) -> dict[str, Any]:
    return _get("DEG", config_path)


def get_bvbrc_endpoint_specs(config_path: Path | None = None) -> dict[str, Any]:
    return _get("BV-BRC", config_path)
