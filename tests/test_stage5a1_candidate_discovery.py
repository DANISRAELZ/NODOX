from __future__ import annotations

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.nodos_funcionales.stage5a1_candidate_discovery import (
    fetch_scoped_records,
    select_records,
    strict_benchmark_match,
)


def _record(accession: str, gene: str, protein_name: str) -> dict[str, object]:
    return {
        "primaryAccession": accession,
        "uniProtkbId": f"{gene.upper()}_HELPY",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "genes": [{"geneName": {"value": gene}}],
        "proteinDescription": {"recommendedName": {"fullName": {"value": protein_name}}},
        "sequence": {"value": "MAAA"},
    }


def _config() -> dict[str, object]:
    return {
        "online_sources": {
            "uniprot": {
                "provider_name": "uniprot_rest",
                "provider_base_url": "https://rest.uniprot.org/uniprotkb/search",
                "provider_timeout_seconds": 15,
                "provider_max_retries": 1,
                "provider_backoff_seconds": 0.0,
                "provider_user_agent": "stage5a1-test",
                "database_label": "computed_uniprot_api_v1",
                "fields": "accession,id,protein_name,gene_names,reviewed",
            }
        }
    }


class _Headers(dict):
    pass


def test_strict_match_does_not_confuse_gyra_with_gyrase_or_gyrb() -> None:
    gyrb = _record("P56005", "gyrB", "DNA gyrase subunit B")
    assert strict_benchmark_match(gyrb, "gyrA") == (False, "")
    assert strict_benchmark_match(gyrb, "gyrB") == (True, "gene_exact")


def test_strict_match_accepts_exact_accession() -> None:
    gyra = _record("P48370", "gyrA", "DNA gyrase subunit A")
    assert strict_benchmark_match(gyra, "P48370") == (True, "accession")


def test_proteome_scope_is_embedded_in_uniprot_query() -> None:
    page = ({"results": [_record("P48370", "gyrA", "DNA gyrase subunit A")]}, _Headers({"x-total-results": "1"}))
    with patch("src.nodos_funcionales.stage5a1_candidate_discovery._http_json", return_value=page) as provider:
        records, stats = fetch_scoped_records(
            taxon_id="85962",
            proteome_id="UP000000429",
            config=_config(),
            max_candidates=0,
        )
    assert len(records) == 1
    query = parse_qs(urlparse(provider.call_args.args[0]).query)["query"][0]
    assert "organism_id:85962" in query
    assert "proteome:UP000000429" in query
    assert stats["candidate_scope"] == "proteome_strain_specific"
    assert stats["proteome_id"] == "UP000000429"


def test_blind_benchmark_marks_gyra_and_gyrb_separately() -> None:
    gyra = _record("P48370", "gyrA", "DNA gyrase subunit A")
    gyrb = _record("P56005", "gyrB", "DNA gyrase subunit B")
    selected, audit, summary = select_records(
        natural_records=[gyrb, gyra],
        benchmark_mode="blind",
        benchmark_candidates=["gyrA", "gyrB"],
        max_candidates=0,
        total_uniprot_results=2,
    )
    assert len(selected) == 2
    gyra_row = audit.loc[audit["candidate_seed_accession"].eq("P48370")].iloc[0]
    gyrb_row = audit.loc[audit["candidate_seed_accession"].eq("P56005")].iloc[0]
    assert gyra_row["benchmark_token"] == "gyrA"
    assert gyrb_row["benchmark_token"] == "gyrB"
    assert summary["unresolved_benchmark_candidates"] == []


def test_ambiguous_exact_gene_identifier_is_not_silently_resolved() -> None:
    first = _record("P1", "pbp1A", "Penicillin-binding protein 1A")
    second = _record("P2", "pbp1A", "Penicillin-binding protein 1A")
    _, audit, summary = select_records(
        natural_records=[first, second],
        benchmark_mode="blind",
        benchmark_candidates=["pbp1A"],
        max_candidates=0,
        total_uniprot_results=2,
    )
    unresolved = audit.loc[audit["exclusion_reason"].eq("ambiguous_exact_benchmark_identifier")]
    assert len(unresolved) == 1
    assert summary["ambiguous_benchmark_candidates"] == ["pbp1A"]
