from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .external_provider_adapters import normalize_bvbrc_records, normalize_deg_records, normalize_vfdb_records
from .external_provider_endpoints import ENDPOINT_SPEC_VERSION, list_external_provider_endpoint_specs
from .online_provider_connectivity import CONSERVATIVE_WARNING


CAPTURE_TYPES = {"raw_external_capture", "sanitized_external_capture"}
SENSITIVE_KEYS = {"api_key", "apikey", "authorization", "cookie", "password", "secret", "session", "token"}
AUTOMATIC_CLAIM_KEYS = {"biological_claim", "biological_absence", "absence_claim", "therapeutic_claim"}
ADAPTERS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "VFDB": normalize_vfdb_records,
    "DEG": normalize_deg_records,
    "BV-BRC": normalize_bvbrc_records,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_external_payload(value: Any) -> Any:
    """Return a JSON-compatible copy with common credential fields redacted."""
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else sanitize_external_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_external_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _record_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("results", "data", "records", "entries"):
            if isinstance(payload.get(key), list):
                return len(payload[key])
        response = payload.get("response")
        if isinstance(response, dict) and isinstance(response.get("docs"), list):
            return len(response["docs"])
    return 0


def _capture_response(
    provider_name: str,
    payload: Any,
    output_path: Path,
    *,
    provider_url: str,
    query_used: str,
    organism_label: str,
    taxon_id: str | int | None,
    schema_observed: str,
    captured_at: str = "",
    capture_type: str = "sanitized_external_capture",
) -> dict[str, Any]:
    if capture_type not in CAPTURE_TYPES:
        raise ValueError(f"invalid capture_type: {capture_type}")
    sanitized = sanitize_external_payload(payload)
    now = _now()
    capture = {
        "provider_name": provider_name,
        "provider_url": provider_url,
        "query_used": query_used,
        "organism_label": organism_label,
        "taxon_id": taxon_id or "",
        "captured_at": captured_at or now,
        "sanitized_at": now,
        "capture_type": capture_type,
        "schema_observed": schema_observed,
        "record_count": _record_count(sanitized),
        "raw_payload_sanitized": sanitized,
        "interpretation_warning": CONSERVATIVE_WARNING,
        "affects_score": False,
        "experimental_validation_supported": False,
    }
    validate_sanitized_provider_capture(capture)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(capture, indent=2, ensure_ascii=True), encoding="utf-8")
    return capture


def capture_vfdb_response(payload: Any, output_path: Path, **metadata: Any) -> dict[str, Any]:
    return _capture_response("VFDB", payload, output_path, **metadata)


def capture_deg_response(payload: Any, output_path: Path, **metadata: Any) -> dict[str, Any]:
    return _capture_response("DEG", payload, output_path, **metadata)


def capture_bvbrc_response(payload: Any, output_path: Path, **metadata: Any) -> dict[str, Any]:
    return _capture_response("BV-BRC", payload, output_path, **metadata)


def validate_sanitized_provider_capture(capture: Any, *, raise_on_error: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(capture, dict):
        errors.append("capture must be a JSON object")
        capture = {}
    for field in ("provider_name", "query_used", "raw_payload_sanitized", "interpretation_warning"):
        if field not in capture or capture[field] in (None, ""):
            errors.append(f"missing required field: {field}")
    if capture.get("provider_name") not in ADAPTERS:
        errors.append("provider_name has no Phase 7E adapter")
    if capture.get("capture_type") not in CAPTURE_TYPES:
        errors.append("capture_type must be raw_external_capture or sanitized_external_capture")
    for key, value in _walk(capture):
        lowered = key.lower()
        if lowered == "affects_score" and value is True:
            errors.append("affects_score=true is forbidden")
        if lowered in AUTOMATIC_CLAIM_KEYS and value not in (None, "", False):
            errors.append(f"automatic biological claim is forbidden: {key}")
    result = {"valid": not errors, "errors": sorted(set(errors))}
    if errors and raise_on_error:
        raise ValueError("invalid sanitized provider capture: " + "; ".join(result["errors"]))
    return result


def _walk(value: Any, parent: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            items.append((str(key), child))
            items.extend(_walk(child, str(key)))
    elif isinstance(value, list):
        for child in value:
            items.extend(_walk(child, parent))
    return items


def normalize_sanitized_capture(capture: dict[str, Any]) -> list[dict[str, Any]]:
    validate_sanitized_provider_capture(capture)
    provider = str(capture["provider_name"])
    return ADAPTERS[provider](
        capture["raw_payload_sanitized"],
        organism_label=str(capture.get("organism_label", "")),
        taxon_id=capture.get("taxon_id", ""),
        query_used=str(capture["query_used"]),
        source_url=str(capture.get("provider_url", "")),
        checked_at=str(capture.get("captured_at", "")),
    )


def validate_real_provider_captures(capture_paths: list[Path], output_dir: Path) -> dict[str, Any]:
    """Validate stored captures and write a non-scoring Phase 7F review package."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    captures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    endpoint_specs = {item["provider_name"]: item for item in list_external_provider_endpoint_specs()}
    endpoint_stability: list[dict[str, Any]] = []
    for path in capture_paths:
        capture = json.loads(Path(path).read_text(encoding="utf-8"))
        validation = validate_sanitized_provider_capture(capture, raise_on_error=False)
        provider_name = str(capture.get("provider_name", ""))
        endpoint_spec = endpoint_specs.get(provider_name, {})
        validation_rows.append({
            "provider_name": provider_name,
            "capture_path": str(path),
            "capture_type": capture.get("capture_type", ""),
            "valid": validation["valid"],
            "errors": "; ".join(validation["errors"]),
            "record_count": capture.get("record_count", 0),
            "endpoint_status": endpoint_spec.get("endpoint_status", "unresolved"),
            "expected_format": endpoint_spec.get("expected_format", "unresolved"),
            "endpoint_spec_version": endpoint_spec.get("endpoint_spec_version", ENDPOINT_SPEC_VERSION),
            "last_verified_at": endpoint_spec.get("last_verified_at", ""),
            "affects_score": False,
        })
        if not validation["valid"]:
            raise ValueError(f"invalid capture {path}: {'; '.join(validation['errors'])}")
        captures.append(capture)
        rows.extend(normalize_sanitized_capture(capture))
        endpoint_stability.append({
            "provider_name": provider_name,
            "endpoint_tested": capture.get("provider_url", ""),
            "expected_format": endpoint_spec.get("expected_format", "unresolved"),
            "observed_format": capture.get("schema_observed", "unresolved"),
            "endpoint_status": endpoint_spec.get("endpoint_status", "unresolved"),
            "endpoint_spec_version": endpoint_spec.get("endpoint_spec_version", ENDPOINT_SPEC_VERSION),
            "last_verified_at": endpoint_spec.get("last_verified_at", ""),
            "recommendation": endpoint_spec.get("recommendation", "Manual endpoint review is required."),
            "interpretation_warning": endpoint_spec.get("interpretation_warning", CONSERVATIVE_WARNING),
            "affects_score": False,
        })
    for provider, filename in (("VFDB", "vfdb_real_capture_validation.csv"), ("DEG", "deg_real_capture_validation.csv"), ("BV-BRC", "bvbrc_real_capture_validation.csv")):
        _write_csv(output_dir / filename, [row for row in rows if row["provider_name"] == provider])
    _write_csv(output_dir / "real_capture_normalized_records.csv", rows)
    (output_dir / "real_capture_normalized_records.json").write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
    manifest = {
        "phase": "7F_sanitized_external_provider_capture_validation",
        "generated_at": _now(),
        "capture_count": len(captures),
        "normalized_record_count": len(rows),
        "capture_types": sorted({str(item["capture_type"]) for item in captures}),
        "affects_score": False,
        "scores_modified": False,
        "network_queries_performed": False,
        "endpoint_spec_version": ENDPOINT_SPEC_VERSION,
        "endpoint_stability": endpoint_stability,
        "generated_artifacts": [
            "vfdb_real_capture_validation.csv", "deg_real_capture_validation.csv",
            "bvbrc_real_capture_validation.csv", "real_capture_normalized_records.csv",
            "real_capture_normalized_records.json", "real_capture_validation_manifest.json",
            "EXTERNAL_PROVIDER_REAL_CAPTURE_VALIDATION_REVIEW.md",
        ],
        "capture_validation": validation_rows,
    }
    (output_dir / "real_capture_validation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    statuses = sorted({str(row["evidence_status"]) for row in rows})
    endpoint_lines = [
        "| Provider | Endpoint tested | Expected format | Observed format | Endpoint status | Recommendation | Warning |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *[
            "| " + " | ".join(
                str(item[field]).replace("|", "\\|").replace("\n", " ")
                for field in (
                    "provider_name", "endpoint_tested", "expected_format", "observed_format",
                    "endpoint_status", "recommendation", "interpretation_warning",
                )
            ) + " |"
            for item in endpoint_stability
        ],
    ]
    review = "\n".join([
        "# External Provider Real Capture Validation Review", "",
        "This package validates sanitized external captures against Phase 7E adapters. It performs no network queries and does not modify scores.", "",
        f"- Captures validated: {len(captures)}",
        f"- Normalized records: {len(rows)}",
        f"- Evidence statuses observed: {', '.join(statuses) or 'none'}", "",
        "## Endpoint and format stability review", "", *endpoint_lines, "",
        CONSERVATIVE_WARNING,
        "`supported` means an explicit external record only. `not_found` is limited to the captured query. `unresolved` records a technical or schema limitation.",
        "Every normalized record has `affects_score=false`; this is adapter validation, not biological or experimental validation.",
    ])
    (output_dir / "EXTERNAL_PROVIDER_REAL_CAPTURE_VALIDATION_REVIEW.md").write_text(review, encoding="utf-8")
    return {"output_dir": str(output_dir), "rows": rows, "manifest": manifest}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
