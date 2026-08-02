from __future__ import annotations

import shutil
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.nodos_funcionales.bvbrc_api import fetch_bvbrc_strain_conservation
from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.deg_api import fetch_deg_essentiality
from src.nodos_funcionales.human_essentiality_api import fetch_human_essentiality_annotations
from src.nodos_funcionales.interpro_api import fetch_interpro_host_annotation
from src.nodos_funcionales.online_only_validation import run_online_only_validation
from src.nodos_funcionales.provider_response_audit import ProviderResponse
from src.nodos_funcionales.vfdb_api import fetch_vfdb_virulence
from tests.helpers import PROJECT_ROOT


def _workspace(tmp_path: Path) -> tuple[Path, dict]:
    workspace = tmp_path / "workspace"
    for dirname in ("config", "data_raw", "data_external", "results"):
        (workspace / dirname).mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
    (workspace / "data_raw" / "human_homologs.csv").write_text(
        "protein_id,gene,human_gene,human_uniprot_accession\nP1,geneA,GENEA,\n",
        encoding="utf-8",
    )
    (workspace / "data_external" / "human_essentiality.csv").write_text(
        "human_gene,human_essential,human_essentiality_score,database\nGENEA,1,1.0,test_local\n",
        encoding="utf-8",
    )
    return workspace, load_config(workspace / "config" / "params.yaml")


def _call_provider(provider: str, workspace: Path, config: dict, mode: str) -> dict:
    if provider == "bvbrc":
        config["online_sources"]["bvbrc"]["enabled"] = False
        return fetch_bvbrc_strain_conservation(workspace, "Test bacterium", "123", config, mode)["manifest"]
    if provider == "deg":
        config["online_sources"]["deg"]["enabled"] = False
        return fetch_deg_essentiality(workspace, "Test bacterium", "123", config, mode)["manifest"]
    if provider == "human_essentiality":
        return fetch_human_essentiality_annotations(workspace, config, mode)["manifest"]
    if provider == "interpro":
        return fetch_interpro_host_annotation(workspace, "Test bacterium", "123", config, mode)["manifest"]
    if provider == "vfdb":
        config["online_sources"]["vfdb"]["enabled"] = False
        return fetch_vfdb_virulence(workspace, "Test bacterium", "123", config, mode)["manifest"]
    raise AssertionError(f"unknown test provider: {provider}")


@pytest.mark.parametrize("provider", ["bvbrc", "deg", "human_essentiality", "interpro", "vfdb"])
@pytest.mark.parametrize(
    ("requested", "canonical"),
    [("online_strict", "online_strict"), ("online_only", "online_strict"), ("hybrid_curated", "hybrid_curated")],
)
def test_each_provider_uses_central_mode_contract(
    tmp_path: Path, provider: str, requested: str, canonical: str
) -> None:
    workspace, config = _workspace(tmp_path)

    # No call is mocked: execution enters the provider, crosses its mode
    # normalization boundary, and exits through a deterministic local branch.
    manifest = _call_provider(provider, workspace, config, requested)

    assert manifest["mode"] == canonical


def test_online_strict_runner_reaches_all_enabled_providers_with_simulated_network(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    reached: dict[str, str] = {}

    def fake_discovery(**kwargs):
        workspace = Path(kwargs["workspace"])
        for dirname in ("config", "data_raw", "data_external", "results"):
            (workspace / dirname).mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        return {"profile": {"organism_canonical_name": "Test bacterium", "taxon_id": "123"}, "manifest": {}}

    def fake_seed(**kwargs):
        workspace = Path(kwargs["workspace"])
        pd.DataFrame([{"protein_id": "P1", "gene": "geneA", "candidate_seed_accession": "P1"}]).to_csv(
            workspace / "data_external" / "essentiality.csv", index=False
        )
        (workspace / "results" / "online_only_uniprot_seed_records.json").write_text(
            json.dumps({"results": []}), encoding="utf-8"
        )
        return {
            "api_attempted": True, "api_success": True, "retrieved_record_count": 1,
            "matched_candidate_count": 1, "candidate_count": 1, "source_used": "api_real",
            "retrieval_status": "api_real", "evidence_level": "computational_online_annotation",
        }

    def fake_pipeline(*, base_dir, config_path, **_kwargs):
        workspace = Path(base_dir)
        config = load_config(config_path)
        mode = config["online_sources"]["source_mode_effective"]
        assert all(config["online_sources"][key]["enabled"] for key in ("string", "interpro", "vfdb", "deg", "bvbrc"))
        (workspace / "data_raw" / "human_homologs.csv").write_text(
            "protein_id,gene,human_gene,human_uniprot_accession\nP1,geneA,GENEA,\n", encoding="utf-8"
        )
        (workspace / "data_external" / "human_essentiality.csv").write_text(
            "human_gene,human_essential,human_essentiality_score,database\nGENEA,1,1.0,test_local\n",
            encoding="utf-8",
        )
        reached["bvbrc"] = fetch_bvbrc_strain_conservation(workspace, "Test bacterium", "123", config, mode)["manifest"]["mode"]
        reached["deg"] = fetch_deg_essentiality(workspace, "Test bacterium", "123", config, mode)["manifest"]["mode"]
        reached["human_essentiality"] = fetch_human_essentiality_annotations(workspace, config, mode)["manifest"]["mode"]
        reached["interpro"] = fetch_interpro_host_annotation(workspace, "Test bacterium", "123", config, mode)["manifest"]["mode"]
        reached["vfdb"] = fetch_vfdb_virulence(workspace, "Test bacterium", "123", config, mode)["manifest"]["mode"]
        return {"ok": True}

    response = ProviderResponse([], "https://example.test/bvbrc", 200, "application/json", "json", "", "", {})
    string_result = {
        "functional_network": pd.DataFrame(),
        "manifest": {"api_success": True, "edge_count": 0, "protein_count_mapped": 0, "mode": "online_strict"},
    }
    fasta_manifest = {"retrieval_status": "candidate_fasta_not_required_for_mode_contract_test"}

    with patch("src.nodos_funcionales.online_only_validation.prepare_discovery_workspace", side_effect=fake_discovery):
        with patch("src.nodos_funcionales.online_only_validation.seed_candidate_essentiality_from_uniprot", side_effect=fake_seed):
            with patch("src.nodos_funcionales.online_only_validation.fetch_string_functional_network", return_value=string_result):
                with patch("src.nodos_funcionales.online_only_validation.urlopen_json", return_value={"results": []}):
                    with patch("src.nodos_funcionales.online_only_validation.materialize_candidate_fasta", return_value=fasta_manifest):
                        with patch("src.nodos_funcionales.bvbrc_api._api_get_json", return_value=({"results": []}, [], response)):
                            with patch("src.nodos_funcionales.online_only_validation.run_pipeline", side_effect=fake_pipeline):
                                result = run_online_only_validation(
                                    project_root=PROJECT_ROOT,
                                    organism="Test bacterium",
                                    organism_slug="test_bacterium",
                                    taxon_id="123",
                                    run_dir=run_dir,
                                    online_source_mode="online_strict",
                                    enable_string=True,
                                    enable_interpro=True,
                                    enable_vfdb=True,
                                    enable_deg=True,
                                    enable_bvbrc=True,
                                )

    assert result["pipeline_status"] == "completed"
    assert reached == {provider: "online_strict" for provider in ("bvbrc", "deg", "human_essentiality", "interpro", "vfdb")}
