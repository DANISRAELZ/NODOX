from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.interpro_human_domain import (
    build_comparison_table,
    build_human_interpro_catalog_url,
    compare_bacterial_entries_to_human_catalog,
    extract_interpro_entry_accessions,
    fetch_human_interpro_catalog,
)


def test_build_human_interpro_catalog_url_targets_human_taxon() -> None:
    url = build_human_interpro_catalog_url(
        "https://www.ebi.ac.uk/interpro/api/",
        page_size=123,
    )
    assert url == (
        "https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/uniprot/"
        "taxonomy/uniprot/9606/?page_size=123"
    )


def test_extract_interpro_entry_accessions_uses_metadata() -> None:
    payload = {
        "results": [
            {"metadata": {"accession": "IPR000001"}},
            {"accession": "IPR000002"},
            {"metadata": {"accession": "PF00001"}},
        ]
    }
    assert extract_interpro_entry_accessions(payload) == {
        "IPR000001",
        "IPR000002",
    }


def test_fetch_human_catalog_follows_same_host_pagination() -> None:
    calls: list[str] = []

    def opener(url: str, **_: object) -> dict:
        calls.append(url)
        if len(calls) == 1:
            return {
                "count": 2,
                "results": [{"metadata": {"accession": "IPR000001"}}],
                "next": "/interpro/api/page2",
            }
        return {
            "count": 2,
            "results": [{"metadata": {"accession": "IPR000002"}}],
            "next": None,
        }

    entries, manifest = fetch_human_interpro_catalog(
        "https://www.ebi.ac.uk/interpro/api",
        opener=opener,
    )
    assert entries == {"IPR000001", "IPR000002"}
    assert manifest["pages_retrieved"] == 2
    assert manifest["unique_interpro_entry_count"] == 2


def test_fetch_human_catalog_rejects_cross_host_pagination() -> None:
    def opener(url: str, **_: object) -> dict:
        return {
            "results": [],
            "next": "https://example.org/escape",
        }

    with pytest.raises(ValueError, match="escaped"):
        fetch_human_interpro_catalog(
            "https://www.ebi.ac.uk/interpro/api",
            opener=opener,
        )


def test_complete_comparison_with_no_shared_domains_is_empirical_zero() -> None:
    result = compare_bacterial_entries_to_human_catalog(
        "IPR000001;IPR000002",
        {"IPR999999"},
    )
    assert result["shared_domain_count"] == 0
    assert result["shared_interpro_entries"] == ""
    assert result["domain_overlap_score_empirical"] == 0.0
    assert result["interpro_human_comparison_status"] == (
        "complete_taxon_catalog_comparison"
    )


def test_complete_comparison_reports_directional_overlap() -> None:
    result = compare_bacterial_entries_to_human_catalog(
        "IPR000001;IPR000002;IPR000003",
        {"IPR000002", "IPR000003", "IPR999999"},
    )
    assert result["human_comparable_interpro_entries"] == (
        "IPR000001;IPR000002;IPR000003"
    )
    assert result["shared_interpro_entries"] == "IPR000002;IPR000003"
    assert result["shared_domain_count"] == 2
    assert result["domain_overlap_score_empirical"] == pytest.approx(2 / 3)


def test_missing_bacterial_annotation_is_not_false_zero() -> None:
    result = compare_bacterial_entries_to_human_catalog(
        pd.NA,
        {"IPR000001"},
    )
    assert pd.isna(result["shared_domain_count"])
    assert pd.isna(result["domain_overlap_score_empirical"])
    assert result["interpro_human_comparison_status"] == (
        "bacterial_interpro_annotation_missing"
    )


def test_comparison_table_does_not_promote_score_to_phase3() -> None:
    host = pd.DataFrame(
        [
            {
                "protein_id": "P1",
                "gene": "a",
                "interpro_bacterial_accession": "P1",
                "interpro_bacterial_entries": "IPR000001;IPR000002",
            }
        ]
    )
    out = build_comparison_table(host, {"IPR000002"})
    assert out.loc[0, "domain_overlap_score_empirical"] == 0.5
    assert bool(out.loc[0, "domain_overlap_score_promoted_to_phase3"]) is False
    assert out.loc[0, "scoring_effect"] == "none_pending_calibration"
