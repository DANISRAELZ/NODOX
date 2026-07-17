from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.nodos_funcionales.external_provider_capture import validate_real_provider_captures
from src.nodos_funcionales.external_provider_endpoints import (
    ENDPOINT_SPEC_VERSION,
    get_bvbrc_endpoint_specs,
    get_deg_endpoint_specs,
    get_vfdb_endpoint_specs,
    list_external_provider_endpoint_specs,
    validate_external_provider_endpoint_spec,
)
from tests.helpers import PROJECT_ROOT


CAPTURES = PROJECT_ROOT / "tests" / "fixtures" / "external_providers" / "real_captures_sanitized"


def _score_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((PROJECT_ROOT / "src" / "nodos_funcionales" / name).read_bytes()).hexdigest()
        for name in ("scoring.py", "scoring_components.py")
    }


def _has_true_score_effect(value) -> bool:
    if isinstance(value, dict):
        return any((key == "affects_score" and item is True) or _has_true_score_effect(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_true_score_effect(item) for item in value)
    return False


def test_every_provider_has_a_valid_versioned_endpoint_specification() -> None:
    specs = list_external_provider_endpoint_specs()

    assert {spec["provider_name"] for spec in specs} == {"VFDB", "DEG", "BV-BRC"}
    for spec in specs:
        assert spec["endpoint_spec_version"] == ENDPOINT_SPEC_VERSION
        assert spec["expected_format"]
        assert spec["endpoint_status"]
        assert spec["interpretation_warning"]
        assert validate_external_provider_endpoint_spec(spec)["valid"] is True
        assert _has_true_score_effect(spec) is False


def test_phase_7f_findings_remain_conservative() -> None:
    vfdb = get_vfdb_endpoint_specs()
    deg = get_deg_endpoint_specs()
    bvbrc = get_bvbrc_endpoint_specs()

    assert vfdb["endpoint_status"] != "verified_structured_payload"
    assert vfdb["endpoint_status"] in {"not_found_404", "deprecated_or_changed", "requires_manual_download", "unresolved"}
    assert deg["endpoint_status"] in {"html_instead_of_structured_payload", "requires_format_adapter"}
    assert "json" not in deg["expected_format"].lower()
    assert bvbrc["endpoint_status"] in {"verified_empty_payload", "verified_structured_payload", "requires_format_adapter"}
    assert "must not be interpreted as absence" in bvbrc["interpretation_warning"]


def test_auditable_json_matches_module_version_and_does_not_affect_scores() -> None:
    before = _score_hashes()
    payload = json.loads((PROJECT_ROOT / "config" / "external_provider_endpoints.json").read_text(encoding="utf-8"))

    assert payload["endpoint_spec_version"] == ENDPOINT_SPEC_VERSION
    assert _has_true_score_effect(payload) is False
    assert _score_hashes() == before


def test_phase_7f_manifest_and_report_include_endpoint_stability(tmp_path: Path) -> None:
    result = validate_real_provider_captures(sorted(CAPTURES.glob("*.json")), tmp_path)
    manifest = result["manifest"]
    review = (tmp_path / "EXTERNAL_PROVIDER_REAL_CAPTURE_VALIDATION_REVIEW.md").read_text(encoding="utf-8")

    assert manifest["endpoint_spec_version"] == ENDPOINT_SPEC_VERSION
    assert len(manifest["endpoint_stability"]) >= 3
    assert {item["provider_name"] for item in manifest["endpoint_stability"]} == {"VFDB", "DEG", "BV-BRC"}
    assert all(item["endpoint_status"] and item["expected_format"] and item["last_verified_at"] for item in manifest["endpoint_stability"])
    assert "Endpoint and format stability review" in review
    assert "endpoint failure" in review.lower() or "Provider failure" in review


def test_endpoint_documentation_rejects_biological_absence_claims() -> None:
    text = (PROJECT_ROOT / "docs" / "external_provider_endpoint_stability.md").read_text(encoding="utf-8")

    assert "endpoint failure does not mean biological absence" in text.lower()
    assert "affects_score=false" in text
