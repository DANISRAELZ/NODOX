from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales import online_sources
from src.nodos_funcionales.layer_resolver import resolve_layer_inputs
from src.nodos_funcionales.online_sources import fetch_layer_external_source
from src.nodos_funcionales.online.online_utils import describe_online_mode, mode_allows_network, normalize_online_mode
from src.nodos_funcionales.online.provider_modes import accepted_provider_modes, normalize_provider_mode
from src.nodos_funcionales.online.provenance import provider_provenance
from run_pipeline import main as run_pipeline_main
from src.nodos_funcionales.string_api import (
    _build_cache_served_manifest as build_string_cache_manifest,
    _cache_key as string_cache_key,
    _get_candidate_proteins as string_candidate_proteins,
    fetch_string_functional_network,
)
from src.nodos_funcionales.uniprot_api import (
    _build_cache_served_manifest as build_uniprot_cache_manifest,
    _cache_key as uniprot_cache_key,
    _get_candidate_proteins as uniprot_candidate_proteins,
    fetch_uniprot_annotations,
)
from tests.helpers import PROJECT_ROOT

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("requested", "effective", "network"),
    [
        ("offline_only", "offline_only", False),
        ("local", "offline_only", False),
        ("cache_first", "cache_first", False),
        ("online_optional", "online_optional", True),
        ("auto", "cache_first", False),
        ("api_stub", "offline_only", False),
    ],
)
def test_online_modes_are_explicit(requested: str, effective: str, network: bool) -> None:
    assert normalize_online_mode(requested) == effective
    assert mode_allows_network(requested) is network
    description = describe_online_mode(requested)
    assert description["requested_mode"] == requested
    assert description["effective_mode"] == effective


def test_provider_provenance_caps_incomplete_confidence() -> None:
    provenance = provider_provenance(
        "UniProt",
        "partial_response",
        0.90,
        retrieval_mode="cache_first",
        cache_status="cache_miss",
        incomplete=True,
    )

    assert provenance["confidence"] == 0.50
    assert provenance["source_version"]
    assert "incomplete=True" in provenance["provenance"]


def test_provider_modes_respect_config_and_aliases() -> None:
    config = {"online_sources": {"accepted_modes": {"offline_only": True, "cache_first": True}}}

    assert normalize_provider_mode("local", config) == "offline_only"
    assert normalize_provider_mode("auto", config) == "cache_first"
    assert "api_stub" in accepted_provider_modes(config)


@pytest.mark.parametrize("mode", ["offline_only", "local", "api_stub"])
def test_layer_human_homologs_offline_modes_do_not_open_network(tmp_path, mode: str) -> None:
    workspace = _workspace_with_candidates(tmp_path, protein_count=2)
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    config["online_sources"]["source_mode_effective"] = mode

    with patch("src.nodos_funcionales.online_sources.urlopen", side_effect=AssertionError("network opened")):
        result = fetch_layer_external_source(
            layer_key="human_homologs",
            workspace=workspace,
            filename="human_homologs.csv",
            config=config,
            provider_name="uniprot_human_gene_lookup",
        )

    assert result["status"] == "api_not_requested_offline_mode"
    assert result["source_name"] == "configurable_stub_human_homologs_v1"
    assert result["confidence"] == config["online_sources"]["human_homologs_lookup"]["confidence_stub_fallback"]
    assert "stub fallback" in result["provenance"]
    assert "no negative homology evidence inferred" in result["provenance"]
    assert "api_real" not in result["status"]
    assert result["path"]


@pytest.mark.parametrize(
    ("layer_key", "filename", "provider_name", "patch_target"),
    [
        ("functional_network", "functional_network.csv", "string_real", "src.nodos_funcionales.string_api.urlopen"),
        ("localization", "localization.csv", "uniprot_real", "src.nodos_funcionales.uniprot_api.urlopen"),
    ],
)
def test_layer_real_providers_offline_only_do_not_open_network(
    tmp_path,
    layer_key: str,
    filename: str,
    provider_name: str,
    patch_target: str,
) -> None:
    workspace = _workspace_with_candidates(tmp_path, protein_count=2)
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    config["online_sources"]["source_mode_effective"] = "offline_only"

    with patch(patch_target, side_effect=AssertionError("network opened")):
        result = fetch_layer_external_source(
            layer_key=layer_key,
            workspace=workspace,
            filename=filename,
            config=config,
            provider_name=provider_name,
        )

    assert result["status"] == "api_not_requested_offline_mode"
    assert result["path"] is None


def test_layer_online_optional_can_call_network_when_requested(tmp_path) -> None:
    workspace = _workspace_with_candidates(tmp_path, protein_count=2)
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    config["online_sources"]["source_mode_effective"] = "online_optional"

    with patch("src.nodos_funcionales.online_sources._query_uniprot_human_gene") as gene_mock:
        gene_mock.side_effect = [(None, [])] * 4
        with patch("src.nodos_funcionales.online_sources._query_uniprot_human_protein_name", return_value=(None, [])):
            fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="uniprot_human_gene_lookup",
            )

    assert gene_mock.called


def test_layer_cache_first_uses_layer_cache_before_string_network(tmp_path) -> None:
    workspace = _workspace_with_candidates(tmp_path, protein_count=2)
    (workspace / "results").mkdir(parents=True, exist_ok=True)
    (workspace / "data_cache").mkdir(parents=True, exist_ok=True)
    (workspace / "data_cache" / "functional_network.csv").write_text(
        "\n".join(
            [
                "protein_id,gene,network_centrality,pathway_bottleneck_score,redundancy_penalty,functional_dependency_score,database",
                "PA0001,gyrB,0.7,0.6,0.2,0.8,cache_layer",
            ]
        ),
        encoding="utf-8",
    )
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    config["online_sources"]["source_mode_effective"] = "cache_first"

    def guarded_fetch(**kwargs):
        if kwargs.get("layer_key") == "functional_network":
            raise AssertionError("functional_network external fetch requested")
        return online_sources.fetch_layer_external_source(**kwargs)

    with patch("src.nodos_funcionales.layer_resolver.fetch_layer_external_source", side_effect=guarded_fetch):
        manifest = resolve_layer_inputs(workspace, config)

    assert manifest["functional_network"]["resolved_from"] == "cache"
    assert manifest["functional_network"]["retrieval_status"] == "resolved_from_cache"


@pytest.mark.parametrize(
    ("builder", "provider"),
    [
        (build_string_cache_manifest, "string_db"),
        (build_uniprot_cache_manifest, "uniprot_rest"),
    ],
)
def test_cache_served_manifests_keep_traceability_fields(builder, provider: str) -> None:
    manifest = builder(
        {
            "provider": provider,
            "generated_at_utc": "2026-05-05T00:00:00+00:00",
            "confidence": 0.91,
        },
        "cache_first",
    )

    for field in ["source_name", "source_version", "retrieval_mode", "cache_status", "provenance", "confidence"]:
        assert field in manifest
    assert manifest["source_name"] == provider
    assert manifest["retrieval_mode"] == "cache_first"
    assert manifest["cache_status"] == "cache_hit"


@pytest.mark.parametrize("mode", ["offline_only", "local", "api_stub", "cache_first"])
def test_string_cache_modes_do_not_open_network(tmp_path, mode: str) -> None:
    workspace = _workspace_with_candidates(tmp_path, protein_count=2)
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    proteins = string_candidate_proteins(workspace)
    cache_key = string_cache_key("208964", proteins, config)
    _write_json(
        workspace / "config" / config["online_sources"]["string"]["cache_filename"],
        {
            "schema_version": 1,
            "updated_at_utc": "2026-05-05T00:00:00+00:00",
            "entries": {
                cache_key: {
                    "functional_network_rows": [
                        {
                            "protein_id": "PA0001",
                            "gene": "gyrB",
                            "network_centrality": 0.5,
                            "pathway_bottleneck_score": 0.5,
                            "redundancy_penalty": 0.5,
                            "functional_dependency_score": 0.5,
                            "database": "computed_string_api_v1",
                        }
                    ],
                    "manifest": {
                        "provider": "string_db",
                        "generated_at_utc": "2026-05-05T00:00:00+00:00",
                        "confidence": 0.78,
                    },
                }
            },
        },
    )

    with patch("src.nodos_funcionales.string_api._request_json", side_effect=AssertionError("network opened")):
        result = fetch_string_functional_network(
            workspace=workspace,
            organism_name="Pseudomonas aeruginosa",
            taxon_id="208964",
            config=config,
            mode=mode,
        )

    assert result["manifest"]["source_used"] == "cache"
    assert result["manifest"]["retrieval_mode"] in {"offline_only", "cache_first"}
    assert result["manifest"]["cache_status"] == "cache_hit"


@pytest.mark.parametrize("mode", ["offline_only", "local", "api_stub", "cache_first"])
def test_uniprot_cache_modes_do_not_open_network(tmp_path, mode: str) -> None:
    workspace = _workspace_with_candidates(tmp_path, protein_count=1)
    config = load_config(PROJECT_ROOT / "config" / "params.yaml")
    proteins = uniprot_candidate_proteins(workspace)
    cache_key = uniprot_cache_key("208964", proteins)
    _write_json(
        workspace / "config" / config["online_sources"]["uniprot"]["cache_filename"],
        {
            "schema_version": 1,
            "updated_at_utc": "2026-05-05T00:00:00+00:00",
            "entries": {
                cache_key: {
                    "annotations": [
                        {
                            "protein_id": "PA0001",
                            "gene": "gyrB",
                            "uniprot_accession": "P00001",
                            "uniprot_match_status": "exact_gene_match",
                            "database": "computed_uniprot_api_v1",
                        }
                    ],
                    "manifest": {
                        "provider": "uniprot_rest",
                        "generated_at_utc": "2026-05-05T00:00:00+00:00",
                        "confidence": 0.80,
                    },
                }
            },
        },
    )

    with patch("src.nodos_funcionales.uniprot_api._request_json", side_effect=AssertionError("network opened")):
        result = fetch_uniprot_annotations(
            workspace=workspace,
            organism_name="Pseudomonas aeruginosa",
            taxon_id="208964",
            config=config,
            mode=mode,
        )

    assert result["manifest"]["source_used"] == "cache"
    assert result["manifest"]["retrieval_mode"] in {"offline_only", "cache_first"}
    assert result["manifest"]["cache_status"] == "cache_hit"


def test_pipeline_pao1_compare_offline_only_completes_without_network(tmp_path) -> None:
    workspace = tmp_path / "pao1_offline_pipeline"
    network_error = AssertionError("network opened")

    patches = [
        patch("src.nodos_funcionales.online_sources.urlopen", side_effect=network_error),
        patch("src.nodos_funcionales.string_api.urlopen", side_effect=network_error),
        patch("src.nodos_funcionales.uniprot_api.urlopen", side_effect=network_error),
        patch("src.nodos_funcionales.interpro_api.urlopen", side_effect=network_error),
        patch("src.nodos_funcionales.deg_api.urlopen", side_effect=network_error),
        patch("src.nodos_funcionales.vfdb_api.urlopen", side_effect=network_error),
        patch("src.nodos_funcionales.bvbrc_api.urlopen", side_effect=network_error),
    ]
    for item in patches:
        item.start()
    try:
        exit_code = run_pipeline_main(
            [
                "--organism",
                "Pseudomonas aeruginosa",
                "--strain",
                "PAO1",
                "--allow-demo-data",
                "--mode",
                "compare",
                "--workspace",
                str(workspace),
                "--taxon-resolution-mode",
                "offline_only",
            ]
        )
    finally:
        for item in reversed(patches):
            item.stop()

    assert exit_code == 0
    expected_outputs = [
        "results/ranking_nodos_legacy.csv",
        "data_processed/phase2_features.csv",
        "data_processed/scored_nodes.csv",
        "results/ranking_nodos.csv",
        "results/phase_comparison.csv",
        "results/sensitivity_analysis.csv",
        "results/report_phase2.md",
        "results/top10_scientific_audit.csv",
        "results/top10_scientific_audit.md",
        "results/top10_scientific_audit.json",
        "results/ranking_snapshot.csv",
    ]
    for relative_path in expected_outputs:
        assert (workspace / relative_path).exists(), relative_path


def _workspace_with_candidates(tmp_path, protein_count: int):
    workspace = tmp_path / "workspace"
    raw_dir = workspace / "data_raw"
    (workspace / "config").mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    rows = ["protein_id,gene", "PA0001,gyrB"]
    if protein_count >= 2:
        rows.append("PA0002,rpoB")
    for filename in ["essentiality.csv", "virulence.csv", "human_homologs.csv", "localization.csv"]:
        (raw_dir / filename).write_text("\n".join(rows) + "\n", encoding="utf-8")
    external_dir = workspace / "data_external"
    external_dir.mkdir(parents=True, exist_ok=True)
    for filename in ["host_annotation.csv", "literature_support.csv"]:
        source = PROJECT_ROOT / "data_demo" / filename
        if source.exists():
            (external_dir / filename).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return workspace


def _write_json(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
