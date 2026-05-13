from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.online_organism_enrichment import run_organism_online_enrichment
from tests.helpers import PROJECT_ROOT


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _config() -> dict:
    return load_config(PROJECT_ROOT / "config" / "params.yaml")


def _uniprot_payload() -> dict:
    return {
        "results": [
            {
                "primaryAccession": "Q00001",
                "uniProtkbId": "PLD_CORPS",
                "organism": {"scientificName": "Corynebacterium pseudotuberculosis"},
                "genes": [{"geneName": {"value": "pld"}}],
                "proteinDescription": {"recommendedName": {"fullName": {"value": "Phospholipase D toxin"}}},
                "comments": [
                    {
                        "commentType": "SUBCELLULAR LOCATION",
                        "subcellularLocations": [{"location": {"value": "Secreted"}}],
                    }
                ],
            },
            {
                "primaryAccession": "Q00002",
                "uniProtkbId": "DTXR_CORPS",
                "organism": {"scientificName": "Corynebacterium pseudotuberculosis"},
                "genes": [{"geneName": {"value": "dtxR"}}],
                "proteinDescription": {"recommendedName": {"fullName": {"value": "Iron-dependent regulator"}}},
                "comments": [],
            },
        ]
    }


def test_organism_first_enrichment_generates_candidate_universe_and_localization(tmp_path: Path) -> None:
    workspace = tmp_path / "online_demo"
    with patch("src.nodos_funcionales.online_organism_enrichment.urlopen", return_value=FakeResponse(_uniprot_payload())):
        result = run_organism_online_enrichment(
            workspace=workspace,
            organism_name="Corynebacterium pseudotuberculosis",
            strain=None,
            taxon_id="1719",
            config=_config(),
            sources=["uniprot"],
            mode="online_optional",
            force_refresh=True,
        )

    candidates = pd.read_csv(workspace / "data_raw" / "candidate_universe.csv")
    localization = pd.read_csv(workspace / "data_raw" / "localization.csv")
    virulence = pd.read_csv(workspace / "data_raw" / "virulence.csv")
    assert len(candidates) == 2
    assert "real_external_online" in set(candidates["provenance_status"])
    assert localization.loc[localization["gene"] == "pld", "localization"].iloc[0] == "extracellular"
    assert set(virulence["provenance_status"]) == {"inferred_proxy"}
    assert (workspace / "results" / "online_enrichment_report.md").exists()
    assert "uniprot" in result["manifest"]["sources_successful"]


def test_organism_first_enrichment_generates_string_network_from_mock(tmp_path: Path) -> None:
    workspace = tmp_path / "online_demo"
    network = pd.DataFrame(
        {
            "protein_id": ["Q00001", "Q00002"],
            "gene": ["pld", "dtxR"],
            "network_centrality": [1.0, 1.0],
            "pathway_bottleneck_score": [0.0, 0.0],
            "redundancy_penalty": [0.0, 0.0],
            "functional_dependency_score": [0.8, 0.8],
            "database": ["computed_string_api_v1", "computed_string_api_v1"],
        }
    )
    with patch("src.nodos_funcionales.online_organism_enrichment.urlopen", return_value=FakeResponse(_uniprot_payload())):
        with patch(
            "src.nodos_funcionales.online_organism_enrichment.fetch_string_functional_network",
            return_value={"functional_network": network, "manifest": {"notes": []}},
        ):
            run_organism_online_enrichment(
                workspace=workspace,
                organism_name="Corynebacterium pseudotuberculosis",
                strain=None,
                taxon_id="1719",
                config=_config(),
                sources=["uniprot", "string"],
                mode="online_optional",
                force_refresh=True,
            )

    escape = pd.read_csv(workspace / "data_raw" / "evolutionary_escape_risk.csv")
    assert len(escape) == 2
    assert "network_centrality_proxy" in escape.columns


def test_uniprot_failure_writes_empty_candidate_universe(tmp_path: Path) -> None:
    workspace = tmp_path / "online_demo"
    with patch("src.nodos_funcionales.online_organism_enrichment.urlopen", side_effect=TimeoutError("timeout")):
        result = run_organism_online_enrichment(
            workspace=workspace,
            organism_name="Example organism",
            strain=None,
            taxon_id="999999",
            config=_config(),
            sources=["uniprot"],
            mode="online_optional",
            force_refresh=True,
        )

    candidates = pd.read_csv(workspace / "data_raw" / "candidate_universe.csv")
    assert candidates.empty
    assert "uniprot" in result["manifest"]["sources_failed"]


def test_string_failure_does_not_break_enrichment(tmp_path: Path) -> None:
    workspace = tmp_path / "online_demo"
    with patch("src.nodos_funcionales.online_organism_enrichment.urlopen", return_value=FakeResponse(_uniprot_payload())):
        with patch(
            "src.nodos_funcionales.online_organism_enrichment.fetch_string_functional_network",
            side_effect=ValueError("STRING unavailable"),
        ):
            result = run_organism_online_enrichment(
                workspace=workspace,
                organism_name="Corynebacterium pseudotuberculosis",
                strain=None,
                taxon_id="1719",
                config=_config(),
                sources=["uniprot", "string"],
                mode="online_optional",
                force_refresh=True,
            )

    network = pd.read_csv(workspace / "data_raw" / "functional_network.csv")
    assert network.empty
    assert "string" in result["manifest"]["sources_failed"]


def test_operational_docs_do_not_reference_mexican_isolate_project() -> None:
    docs_to_scan = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "docs" / "generic_annotation_import.md",
        PROJECT_ROOT / "docs" / "online_organism_enrichment.md",
        PROJECT_ROOT / "docs" / "project_boundaries.md",
    ]
    forbidden = [
        "cpseudo" + "_mexico",
        "Mexican " + "isolates",
        "aislados " + "mexicanos",
        "17 " + "isolates",
        "pangenome " + "mexicano",
    ]
    for path in docs_to_scan:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for term in forbidden:
            assert term not in text
