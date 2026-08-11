from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.nodos_funcionales.stage5a_candidate_discovery import (
    fetch_high_recall_uniprot_records,
    finalize_stage5a_audit,
    select_stage5a_records,
    write_stage5a_candidate_seed_snapshot,
)


def _record(
    accession: str,
    gene: str,
    sequence: str = "MAAA",
    protein_name: str | None = None,
) -> dict[str, object]:
    return {
        "primaryAccession": accession,
        "uniProtkbId": f"{gene.upper()}_TEST",
        "entryType": "UniProtKB unreviewed (TrEMBL)",
        "genes": [{"geneName": {"value": gene}}],
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": protein_name or f"{gene} protein"}}
        },
        "sequence": {"value": sequence},
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
                "provider_user_agent": "stage5a-test",
                "database_label": "computed_uniprot_api_v1",
                "fields": "accession,id,protein_name,gene_names,reviewed",
            }
        }
    }


class _Headers(dict):
    pass


def test_high_recall_seed_uses_cursor_pagination_until_exhausted() -> None:
    pages = [
        (
            {"results": [_record("P1", "a"), _record("P2", "b")]},
            _Headers(
                {
                    "Link": '<https://rest.uniprot.org/uniprotkb/search?cursor=next>; rel="next"',
                    "x-total-results": "3",
                }
            ),
        ),
        ({"results": [_record("P3", "c")]}, _Headers({})),
    ]

    with patch(
        "src.nodos_funcionales.stage5a_candidate_discovery._http_json",
        side_effect=pages,
    ) as provider:
        records, stats = fetch_high_recall_uniprot_records(
            taxon_id="210",
            config=_config(),
            max_candidates=0,
            page_size=500,
        )

    assert [item["primaryAccession"] for item in records] == ["P1", "P2", "P3"]
    assert provider.call_count == 2
    assert stats["page_count"] == 2
    assert stats["natural_record_count"] == 3
    assert stats["total_uniprot_results"] == 3
    assert stats["full_result_set_requested"] is True


def test_blind_benchmark_never_forces_missing_expected_target() -> None:
    selected, audit, summary = select_stage5a_records(
        natural_records=[_record("P1", "gyrA"), _record("P2", "gyrB")],
        benchmark_mode="blind",
        benchmark_candidates=["pbp1A"],
        max_candidates=2,
        total_uniprot_results=1500,
    )

    assert [item["primaryAccession"] for item in selected] == ["P1", "P2"]
    assert summary["forced_candidate_count"] == 0
    benchmark = audit.loc[audit["benchmark_token"].eq("pbp1A")].iloc[0]
    assert bool(benchmark["selected_for_scoring"]) is False
    assert bool(benchmark["benchmark_forced_candidate"]) is False
    assert benchmark["exclusion_reason"] == "not_observed_within_bounded_seed"


def test_conditional_benchmark_forces_target_and_marks_displaced_tail() -> None:
    forced = _record("P3", "pbp1A", protein_name="Penicillin-binding protein 1A")
    selected, audit, summary = select_stage5a_records(
        natural_records=[_record("P1", "gyrA"), _record("P2", "gyrB")],
        benchmark_mode="conditional",
        benchmark_candidates=["pbp1A"],
        max_candidates=2,
        resolved_benchmark_records={"pbp1A": forced},
        total_uniprot_results=1500,
    )

    assert [item["primaryAccession"] for item in selected] == ["P1", "P3"]
    assert summary["forced_candidate_count"] == 1
    assert summary["forced_candidate_accessions"] == ["P3"]

    forced_row = audit.loc[audit["candidate_seed_accession"].eq("P3")].iloc[0]
    assert bool(forced_row["benchmark_requested"]) is True
    assert bool(forced_row["benchmark_forced_candidate"]) is True
    assert bool(forced_row["discovered_naturally"]) is False
    assert bool(forced_row["selected_for_scoring"]) is True

    displaced = audit.loc[audit["candidate_seed_accession"].eq("P2")].iloc[0]
    assert bool(displaced["selected_for_scoring"]) is False
    assert displaced["exclusion_reason"] == "displaced_by_conditional_benchmark_candidate"


def test_conditional_target_already_natural_is_not_counted_as_forced() -> None:
    selected, audit, summary = select_stage5a_records(
        natural_records=[
            _record("P1", "gyrA"),
            _record("P2", "pbp1A", protein_name="Penicillin-binding protein 1A"),
        ],
        benchmark_mode="conditional",
        benchmark_candidates=["pbp1A"],
        max_candidates=2,
        resolved_benchmark_records={},
        total_uniprot_results=2,
    )

    assert len(selected) == 2
    assert summary["forced_candidate_count"] == 0
    row = audit.loc[audit["candidate_seed_accession"].eq("P2")].iloc[0]
    assert bool(row["benchmark_requested"]) is True
    assert bool(row["discovered_naturally"]) is True
    assert bool(row["benchmark_forced_candidate"]) is False


def test_stage5a_snapshot_matches_existing_versioned_seed_contract(tmp_path: Path) -> None:
    records = [_record("P1", "gyrA"), _record("P2", "pbp1A")]
    snapshot_dir = tmp_path / "snapshot"
    manifest = write_stage5a_candidate_seed_snapshot(
        snapshot_dir=snapshot_dir,
        organism_name="Helicobacter pylori",
        taxon_id="210",
        records=records,
        config=_config(),
        selection_summary={"benchmark_mode": "blind"},
    )

    assert manifest["snapshot_type"] == "versioned_uniprot_candidate_seed"
    assert manifest["candidate_count"] == 2
    assert set(manifest["files"]) == {
        "uniprot_seed_records.json",
        "candidate_seed.csv",
        "candidate_proteins.faa",
    }
    for name, metadata in manifest["files"].items():
        path = snapshot_dir / name
        assert path.exists()
        assert metadata["size_bytes"] == path.stat().st_size
        assert metadata["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    payload = json.loads((snapshot_dir / "uniprot_seed_records.json").read_text(encoding="utf-8"))
    seed = pd.read_csv(snapshot_dir / "candidate_seed.csv")
    fasta = (snapshot_dir / "candidate_proteins.faa").read_text(encoding="utf-8")
    assert len(payload["results"]) == 2
    assert seed["candidate_seed_accession"].tolist() == ["P1", "P2"]
    assert ">tr|P1|GYRA_TEST" in fasta
    assert ">tr|P2|PBP1A_TEST" in fasta


def test_final_audit_records_pipeline_rank_without_changing_scores(tmp_path: Path) -> None:
    audit = pd.DataFrame(
        [
            {
                "candidate_seed_accession": "P1",
                "protein_id": "P1",
                "gene": "gyrA",
                "selected_for_scoring": True,
            },
            {
                "candidate_seed_accession": "P2",
                "protein_id": "P2",
                "gene": "pbp1A",
                "selected_for_scoring": True,
            },
        ]
    )
    ranking_path = tmp_path / "ranking_nodos.csv"
    pd.DataFrame(
        [
            {"protein_id": "P2", "gene": "pbp1A", "final_score": 0.81, "functional_node_theory_score": 0.72},
            {"protein_id": "P1", "gene": "gyrA", "final_score": 0.74, "functional_node_theory_score": 0.91},
        ]
    ).to_csv(ranking_path, index=False)

    result = finalize_stage5a_audit(audit, ranking_path)
    p1 = result.loc[result["candidate_seed_accession"].eq("P1")].iloc[0]
    p2 = result.loc[result["candidate_seed_accession"].eq("P2")].iloc[0]

    assert bool(p1["ranking_match"]) is True
    assert int(p1["final_rank"]) == 2
    assert float(p1["final_score"]) == 0.74
    assert int(p1["functional_node_theory_rank"]) == 1
    assert int(p2["final_rank"]) == 1
    assert float(p2["final_score"]) == 0.81
