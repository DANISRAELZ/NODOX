from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.standard_validation import (
    _candidate_rows_and_records,
    _stream_uniprot_proteome,
    apply_standard_provider_scoring_contracts,
    materialize_exact_proteome_snapshot,
    run_standard_validation,
)
from tests.helpers import PROJECT_ROOT


def _record(accession: str, gene: str, sequence: str = "MAAA") -> dict:
    return {
        "primaryAccession": accession,
        "uniProtkbId": f"{gene.upper()}_BACT",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "genes": [{"geneName": {"value": gene}}],
        "sequence": {"value": sequence},
    }


def test_exact_proteome_query_uses_proteome_not_species_taxon() -> None:
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    payload = {"results": [_record("P00001", "geneA")]}

    with patch(
        "src.nodos_funcionales.standard_validation.urlopen_json",
        return_value=payload,
    ) as request:
        records = _stream_uniprot_proteome(
            proteome_id="UP000000625",
            config=config,
        )

    assert len(records) == 1
    url = request.call_args.args[0]
    parsed = parse_qs(urlparse(url).query)
    assert parsed["query"] == ["(proteome:UP000000625)"]
    assert "organism_id" not in parsed["query"][0]
    assert "/stream" in urlparse(url).path


def test_zero_candidate_limit_preserves_complete_exact_proteome() -> None:
    records = [
        _record("P00001", "geneA"),
        _record("P00002", "geneB"),
        _record("P00003", "geneC"),
    ]

    rows, selected = _candidate_rows_and_records(
        records,
        max_candidates=0,
        database_label="test",
    )

    assert len(rows) == 3
    assert len(selected) == 3
    assert [row["protein_id"] for row in rows] == ["P00001", "P00002", "P00003"]


def test_positive_candidate_limit_is_explicit_smoke_test_truncation() -> None:
    records = [
        _record("P00001", "geneA"),
        _record("P00002", "geneB"),
        _record("P00003", "geneC"),
    ]

    rows, selected = _candidate_rows_and_records(
        records,
        max_candidates=2,
        database_label="test",
    )

    assert len(rows) == 2
    assert len(selected) == 2


def test_materialized_snapshot_records_exact_proteome_identity(tmp_path: Path) -> None:
    records = [
        _record("P00001", "geneA"),
        _record("P00002", "geneB"),
        _record("P00003", "geneC"),
    ]
    snapshot = tmp_path / "snapshot"

    with patch(
        "src.nodos_funcionales.standard_validation._stream_uniprot_proteome",
        return_value=records,
    ):
        manifest = materialize_exact_proteome_snapshot(
            project_root=PROJECT_ROOT,
            snapshot_dir=snapshot,
            organism="Test bacterium",
            taxon_id="12345",
            strain="Reference strain",
            proteome_id="UP000000001",
            max_candidates=0,
        )

    assert manifest["candidate_scope"] == "complete_exact_proteome"
    assert manifest["proteome_id"] == "UP000000001"
    assert manifest["taxon_id"] == "12345"
    assert manifest["candidate_count"] == 3
    assert manifest["requested_max_candidates"] == 0
    assert (snapshot / "candidate_seed.csv").is_file()
    assert (snapshot / "candidate_proteins.faa").is_file()
    assert (snapshot / "uniprot_seed_records.json").is_file()
    persisted = json.loads((snapshot / "snapshot_manifest.json").read_text(encoding="utf-8"))
    assert persisted["query_semantics"] == "proteome_id_exact_no_species_broadening"


def test_complete_universe_requires_proteome_or_exact_snapshot(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires proteome_id"):
        run_standard_validation(
            project_root=PROJECT_ROOT,
            organism="Escherichia coli",
            taxon_id=511145,
            strain="K-12 MG1655",
            run_dir=tmp_path / "run",
            max_candidates=0,
        )


def test_deg_standard_contract_is_positive_only_basal_essentiality(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    external = workspace / "data_external"
    results = workspace / "results"
    external.mkdir(parents=True)
    results.mkdir(parents=True)

    pd.DataFrame(
        [
            {"protein_id": "P1", "gene": "gene1", "essential": pd.NA},
            {"protein_id": "P2", "gene": "gene2", "essential": pd.NA},
        ]
    ).to_csv(external / "essentiality.csv", index=False)
    pd.DataFrame(
        [
            {
                "protein_id": "P1",
                "gene": "gene1",
                "essential": 1,
                "evidence": "knockout",
                "database": "deg_real_v1",
            }
        ]
    ).to_csv(results / "deg_essentiality_matches.csv", index=False)
    (results / "online_only_contextual_essentiality_manifest.json").write_text(
        json.dumps(
            {
                "provider_name": "deg",
                "retrieval_status": "local_dataset_available",
                "matched_candidate_count": 1,
                "usable_evidence": True,
                "affects_score": False,
            }
        ),
        encoding="utf-8",
    )

    manifest = apply_standard_provider_scoring_contracts(
        workspace=workspace,
        online_source_mode="online_strict",
        recompute_scoring=False,
    )

    combined = pd.read_csv(external / "essentiality.csv")
    p1 = combined.loc[combined["protein_id"].eq("P1")].iloc[0]
    p2 = combined.loc[combined["protein_id"].eq("P2")].iloc[0]
    assert float(p1["essential"]) == pytest.approx(1.0)
    assert pd.isna(p2["essential"])
    assert manifest["deg_overlay"]["deg_match_count"] == 1
    assert manifest["negative_evidence_inferred_count"] == 0

    essentiality_manifest = json.loads(
        (results / "online_only_essentiality_manifest.json").read_text(encoding="utf-8")
    )
    contextual_manifest = json.loads(
        (results / "online_only_contextual_essentiality_manifest.json").read_text(encoding="utf-8")
    )
    assert essentiality_manifest["provider_name"] == "deg"
    assert essentiality_manifest["affects_score"] is True
    assert contextual_manifest["affects_score"] is False
    assert contextual_manifest["retrieval_status"] == "reclassified_to_basal_essentiality"


def test_exact_benchmark_registry_profiles_are_available() -> None:
    registry = json.loads(
        (PROJECT_ROOT / "config" / "online_only_organisms.json").read_text(encoding="utf-8")
    )
    expected = {
        "escherichia_coli_k12_mg1655": (511145, "UP000000625"),
        "pseudomonas_aeruginosa_pao1": (208964, "UP000002438"),
        "helicobacter_pylori_26695": (85962, "UP000000429"),
        "mycobacterium_tuberculosis_h37rv": (83332, "UP000001584"),
        "staphylococcus_aureus_newman": (426430, "UP000217322"),
    }
    for key, (taxon_id, proteome_id) in expected.items():
        assert registry[key]["taxon_id"] == taxon_id
        assert registry[key]["proteome_id"] == proteome_id
