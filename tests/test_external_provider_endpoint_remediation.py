from __future__ import annotations

import hashlib
import json

from src.nodos_funcionales.external_provider_capture import normalize_sanitized_capture, validate_sanitized_provider_capture
from src.nodos_funcionales.external_provider_endpoints import (
    ENDPOINT_SPEC_VERSION,
    get_bvbrc_endpoint_specs,
    get_deg_endpoint_specs,
    get_vfdb_endpoint_specs,
)
from tests.helpers import PROJECT_ROOT


CAPTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "external_providers" / "real_captures_sanitized"


def _capture(name: str) -> dict:
    return json.loads((CAPTURE_DIR / name).read_text(encoding="utf-8"))


def _score_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((PROJECT_ROOT / "src" / "nodos_funcionales" / name).read_bytes()).hexdigest()
        for name in ("scoring.py", "scoring_components.py")
    }


def test_bvbrc_uses_resolved_genome_id_and_nonempty_json_capture() -> None:
    spec = get_bvbrc_endpoint_specs()
    capture = _capture("bvbrc_real_capture_sanitized_002.json")
    rows = normalize_sanitized_capture(capture)

    assert spec["endpoint_status"] == "verified_structured_payload"
    assert spec["expected_format"] == "application_json"
    assert "discovery_url_template" in spec
    assert capture["record_count"] == 2
    assert len(rows) == 2
    assert all(row["evidence_status"] == "supported" and row["affects_score"] is False for row in rows)


def test_deg_uses_official_nonempty_download_but_requires_format_adapter() -> None:
    spec = get_deg_endpoint_specs()
    capture = _capture("deg_real_capture_sanitized_002.json")

    assert spec["endpoint_status"] == "requires_format_adapter"
    assert spec["stable_download_url"].endswith("deg_annotation_p.csv.zip")
    assert spec["expected_format"] == "zip_semicolon_delimited_csv"
    assert capture["record_count"] == 3
    assert validate_sanitized_provider_capture(capture)["valid"] is True
    assert capture["affects_score"] is False


def test_vfdb_requires_manual_download_without_invented_alternative_url() -> None:
    spec = get_vfdb_endpoint_specs()
    capture = _capture("vfdb_real_capture_sanitized_002.json")

    assert spec["endpoint_status"] == "requires_manual_download"
    assert spec["stable_download_url"] is None
    assert spec["query_url_template"].endswith("/cgi-bin/VFs/v5/main.cgi")
    assert capture["raw_payload_sanitized"]["portal_review"]["stable_programmatic_download_verified"] is False
    assert "not evidence of absence" in capture["interpretation_warning"]


def test_phase_7h_is_versioned_and_scoring_remains_intact() -> None:
    before = _score_hashes()

    assert ENDPOINT_SPEC_VERSION == "7H-2026-06-22"
    assert _score_hashes() == before
