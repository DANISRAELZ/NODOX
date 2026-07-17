from __future__ import annotations

import json

import pytest

from src.nodos_funcionales.external_provider_capture import (
    capture_bvbrc_response,
    capture_deg_response,
    capture_vfdb_response,
    validate_sanitized_provider_capture,
)


METADATA = {
    "provider_url": "https://provider.example/records",
    "query_used": "taxon_id:562",
    "organism_label": "Escherichia coli",
    "taxon_id": 562,
    "schema_observed": "fixture_records_v1",
    "captured_at": "2026-06-22T00:00:00Z",
}


@pytest.mark.parametrize("capture_function", [capture_vfdb_response, capture_deg_response, capture_bvbrc_response])
def test_valid_capture_is_sanitized_and_written(capture_function, tmp_path) -> None:
    path = tmp_path / "capture.json"
    capture = capture_function({"records": [], "token": "sensitive"}, path, **METADATA)

    assert path.exists()
    assert capture["capture_type"] == "sanitized_external_capture"
    assert capture["raw_payload_sanitized"]["token"] == "[REDACTED]"
    assert capture["affects_score"] is False
    assert validate_sanitized_provider_capture(json.loads(path.read_text(encoding="utf-8")))["valid"] is True


@pytest.mark.parametrize("missing", ["provider_name", "query_used", "interpretation_warning"])
def test_missing_required_capture_metadata_fails_controlled(missing) -> None:
    capture = {
        "provider_name": "VFDB",
        "query_used": "query",
        "capture_type": "sanitized_external_capture",
        "raw_payload_sanitized": {"records": []},
        "interpretation_warning": "limited external query",
        "affects_score": False,
    }
    del capture[missing]

    with pytest.raises(ValueError, match=missing):
        validate_sanitized_provider_capture(capture)


def test_capture_rejects_score_effect_and_automatic_claims() -> None:
    capture = {
        "provider_name": "DEG",
        "query_used": "query",
        "capture_type": "sanitized_external_capture",
        "raw_payload_sanitized": {"records": []},
        "interpretation_warning": "limited external query",
        "affects_score": True,
        "biological_absence": "confirmed",
    }
    result = validate_sanitized_provider_capture(capture, raise_on_error=False)

    assert result["valid"] is False
    assert any("affects_score=true" in error for error in result["errors"])
    assert any("biological claim" in error for error in result["errors"])
