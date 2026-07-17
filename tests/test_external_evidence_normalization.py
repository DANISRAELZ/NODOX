from __future__ import annotations

from src.nodos_funcionales.external_evidence_normalization import normalize_external_evidence, write_external_evidence_package


def _source(provider: str, status: str, scope: str) -> dict:
    return {
        "provider_name": provider, "provider_url": "https://example.test", "organism_label": "E. coli",
        "taxon_id": 562, "status": status, "records_found": 1 if status == "success" else 0,
        "evidence_scope": scope, "query_used": "taxon:562", "checked_at": "2026-01-01T00:00:00Z",
    }


def test_conservative_status_mapping_and_score_isolation(tmp_path) -> None:
    sources = [
        _source("UniProt", "success", "seed_candidate"),
        _source("Europe PMC", "no_results", "literature_support"),
        _source("VFDB", "timeout", "virulence_association"),
        _source("DEG", "schema_error", "essentiality_association"),
        _source("BV-BRC", "http_error", "resistance_association"),
    ]
    rows = normalize_external_evidence(sources, [{"organism_label": "E. coli", "taxon_id": 562, "candidate_gene": "gyrA", "protein_id": "P0A7I3"}])

    assert rows[0]["evidence_status"] == "supported"
    assert rows[0]["evidence_type"] == "seed_candidate"
    assert "not experimental validation" in rows[0]["interpretation_warning"]
    assert rows[1]["evidence_status"] == "not_found"
    assert "limited query" in rows[1]["interpretation_warning"]
    assert [row["evidence_status"] for row in rows[2:]] == ["unresolved", "unresolved", "provider_failed"]
    assert all(row["evidence_type"] == "unresolved_provider" for row in rows[2:])
    assert all(row["affects_score"] is False for row in rows)
    assert all(row["experimental_validation_supported"] is False for row in rows)

    package = write_external_evidence_package(sources, [{"organism_label": "E. coli", "taxon_id": 562, "protein_id": "P0A7I3"}], tmp_path)
    assert package["manifest"]["phase"].startswith("7D")
    assert package["manifest"]["scores_modified"] is False
    assert (tmp_path / "unresolved_external_evidence.csv").exists()
