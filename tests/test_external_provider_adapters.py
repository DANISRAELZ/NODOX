from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.nodos_funcionales.external_evidence_normalization import write_external_evidence_package
from src.nodos_funcionales.external_provider_adapters import (
    normalize_bvbrc_records,
    normalize_deg_records,
    normalize_vfdb_records,
)
from tests.helpers import PROJECT_ROOT


FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "external_providers"
CONTEXT = {
    "organism_label": "Escherichia coli",
    "taxon_id": 562,
    "query_used": "taxon_id:562",
    "source_url": "https://provider.example/records",
    "checked_at": "2026-06-22T00:00:00Z",
}


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _score_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((PROJECT_ROOT / "src" / "nodos_funcionales" / name).read_bytes()).hexdigest()
        for name in ("scoring.py", "scoring_components.py")
    }


def test_vfdb_valid_empty_and_schema_error_are_conservative() -> None:
    valid = normalize_vfdb_records(_fixture("vfdb_minimal_response.json"), **CONTEXT)
    empty = normalize_vfdb_records(_fixture("vfdb_empty_response.json"), **CONTEXT)
    invalid = normalize_vfdb_records(_fixture("vfdb_schema_error_response.json"), **CONTEXT)

    assert (valid[0]["evidence_type"], valid[0]["evidence_status"]) == ("virulence_association", "supported")
    assert empty[0]["evidence_status"] == "not_found"
    assert "not be interpreted as absence" in empty[0]["interpretation_warning"]
    assert invalid[0]["evidence_status"] in {"unresolved", "provider_failed"}


def test_deg_valid_empty_and_schema_error_are_conservative() -> None:
    valid = normalize_deg_records(_fixture("deg_minimal_response.json"), **CONTEXT)
    empty = normalize_deg_records(_fixture("deg_empty_response.json"), **CONTEXT)
    invalid = normalize_deg_records(_fixture("deg_schema_error_response.json"), **CONTEXT)

    assert (valid[0]["evidence_type"], valid[0]["evidence_status"]) == ("essentiality_association", "supported")
    assert empty[0]["evidence_status"] == "not_found"
    assert "not be interpreted as absence" in empty[0]["interpretation_warning"]
    assert invalid[0]["evidence_status"] in {"unresolved", "provider_failed"}


def test_bvbrc_annotation_amr_empty_and_schema_error_are_conservative() -> None:
    valid = normalize_bvbrc_records(_fixture("bvbrc_minimal_response.json"), **CONTEXT)
    empty = normalize_bvbrc_records(_fixture("bvbrc_empty_response.json"), **CONTEXT)
    invalid = normalize_bvbrc_records(_fixture("bvbrc_schema_error_response.json"), **CONTEXT)

    assert any(row["evidence_type"] == "protein_annotation" and row["evidence_status"] == "supported" for row in valid)
    assert any(row["evidence_type"] == "resistance_association" and row["evidence_status"] == "supported" for row in valid)
    assert empty[0]["evidence_status"] == "not_found"
    assert "not be interpreted as absence" in empty[0]["interpretation_warning"]
    assert invalid[0]["evidence_status"] in {"unresolved", "provider_failed"}


def test_all_records_preserve_provenance_and_never_affect_scores() -> None:
    before = _score_hashes()
    rows = []
    for adapter, fixture in (
        (normalize_vfdb_records, "vfdb_minimal_response.json"),
        (normalize_deg_records, "deg_empty_response.json"),
        (normalize_bvbrc_records, "bvbrc_schema_error_response.json"),
    ):
        rows.extend(adapter(_fixture(fixture), **CONTEXT))

    assert all(row["affects_score"] is False for row in rows)
    assert all(row["provider_name"] and (row["source_record_id"] or row["query_used"]) for row in rows)
    assert all(row["interpretation_warning"] for row in rows)
    assert all(row["experimental_validation_supported"] is False for row in rows)
    assert _score_hashes() == before


def test_phase_7d_optionally_writes_phase_7e_artifacts(tmp_path: Path) -> None:
    payloads = {
        "VFDB": {"payload": _fixture("vfdb_minimal_response.json"), **CONTEXT},
        "DEG": {"payload": _fixture("deg_empty_response.json"), **CONTEXT},
        "BV-BRC": {"payload": _fixture("bvbrc_minimal_response.json"), **CONTEXT},
    }
    result = write_external_evidence_package([], [], tmp_path, provider_payloads=payloads)

    for filename in (
        "external_provider_records_normalized.csv",
        "external_provider_records_normalized.json",
        "vfdb_normalized_records.csv",
        "deg_normalized_records.csv",
        "bvbrc_normalized_records.csv",
        "EXTERNAL_PROVIDER_ADAPTERS_REVIEW.md",
    ):
        assert (tmp_path / filename).exists()
    assert result["manifest"]["phase_7e_provider_adapters_enabled"] is True
    assert result["manifest"]["affects_score"] is False
    assert all(row["affects_score"] is False for row in result["rows"])
