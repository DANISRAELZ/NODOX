from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.online.online_utils import describe_online_mode, mode_allows_network, normalize_online_mode
from src.nodos_funcionales.online.provider_modes import accepted_provider_modes, normalize_provider_mode
from src.nodos_funcionales.online.provenance import provider_provenance
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
    return workspace


def _write_json(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
