from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.layer_registry import get_layer_definition
from src.nodos_funcionales.layer_resolver import _resolve_single_layer
from src.nodos_funcionales.online_only_validation import (
    build_online_only_provider_audit,
    build_online_only_review_package,
    run_online_only_validation,
)
from src.nodos_funcionales.online_sources import fetch_layer_external_source
from src.nodos_funcionales.scoring import _evidence_mixture_label
from tests.helpers import PROJECT_ROOT


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    for dirname in ("config", "data_raw", "data_external", "results"):
        (workspace / dirname).mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
    return workspace


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_v3_manifests(workspace: Path) -> dict:
    results = workspace / "results"
    seed = {
        "provider_name": "uniprot_rest", "api_attempted": True, "api_success": True,
        "retrieved_record_count": 2, "matched_candidate_count": 2, "candidate_count": 2,
        "source_used": "api_real", "retrieval_status": "api_real",
        "evidence_level": "computational_online_annotation", "data_realism_flag": "computed_online",
    }
    _write_json(results / "online_only_candidate_seed_manifest.json", seed)
    _write_json(results / "online_only_run_manifest.json", {"online_source_mode": "online_strict"})
    _write_json(results / "online_only_essentiality_manifest.json", {
        **seed, "provider_name": "uniprot_rest_candidate_seed", "inherited_from_candidate_seed": True,
        "retrieval_status": "candidate_seed_only_not_essentiality_evidence", "evidence_level": "unresolved",
    })
    _write_json(results / "string_functional_network_manifest.json", {
        "provider": "string_db", "provider_success": True, "api_attempted": True, "api_success": True,
        "connectivity_success": True, "edge_count": 4, "protein_count_mapped": 0,
        "retrieval_status": "api_real", "source_used": "api_real",
        "evidence_level": "computational_online_interaction", "data_realism_flag": "computed_online",
    })
    _write_json(results / "human_homology_diamond_manifest.json", {
        "provider_name": "human_homology_diamond", "provider_mode": "local_executable",
        "execution_status": "executed", "retrieval_status": "diamond_blastp_executed",
        "provider_attempted": True, "provider_success": True, "api_attempted": False, "api_success": False,
        "result_row_count": 2, "hit_count": 2, "matched_candidate_count": 2,
        "evidence_level": "sequence_alignment", "data_realism_flag": "computed_local",
        "fallback_used": False, "fallback_reason": "", "affects_score": False,
    })
    _write_json(results / "uniprot_annotation_manifest.json", {
        "provider_name": "uniprot_rest", "api_attempted": True, "api_success": True,
        "records_retrieved": 2, "protein_count_mapped": 2, "retrieval_status": "inherited_from_candidate_seed",
        "source_used": "api_real", "evidence_level": "computational_online_annotation",
        "fallback_used": False, "fallback_reason": "", "data_realism_flag": "computed_online",
    })
    _write_json(results / "interpro_host_annotation_manifest.json", {
        "provider_name": "interpro_api", "api_attempted": True, "api_success": True,
        "accessions_queried": 2, "paired_domain_rows": 2, "retrieval_status": "api_real",
        "source_used": "api_real", "evidence_level": "computational_online_domain_annotation",
        "fallback_used": False, "fallback_reason": "", "data_realism_flag": "computed_online",
    })
    _write_json(results / "online_only_literature_support_manifest.json", {
        "provider_name": "pubmed_or_europepmc", "api_attempted": True, "api_success": True,
        "retrieved_record_count": 2, "matched_candidate_count": 2, "retrieval_status": "api_real",
        "source_used": "api_real", "evidence_level": "literature_metadata_only",
        "fallback_used": False, "fallback_reason": "", "data_realism_flag": "computed_online",
    })
    _write_json(results / "bvbrc_conservation_manifest.json", {
        "provider_name": "bvbrc_real", "api_attempted": True, "api_success": True,
        "feature_records_retrieved": 2, "protein_count_mapped": 2, "retrieval_status": "api_real",
        "source_used": "api_real", "evidence_level": "computational_online_evidence",
        "fallback_used": False, "fallback_reason": "", "data_realism_flag": "computed_online",
    })
    layer_manifest = {
        layer: {
            "source_type": "external", "source_name": source, "retrieval_status": "resolved_from_external",
            "is_user_supplied": False, "is_external": True, "is_cached": False, "is_proxy": False, "confidence": 0.8,
        }
        for layer, source in {
            "essentiality": "uniprot_candidate_seed", "functional_network": "string_real",
            "human_homologs": "human_homology_diamond", "localization": "uniprot_real",
            "host_annotation": "interpro_domain_overlap", "literature_support": "europe_pmc",
            "strain_conservation": "bvbrc_real",
            "clinical_impact": "controlled_therapeutic_context_v2",
            "curated_disease_context": "controlled_therapeutic_context_v2",
            "therapy_site_context": "controlled_therapeutic_context_v2",
            "evidence_quality": "missing",
        }.items()
    }
    for layer in ["clinical_impact", "curated_disease_context", "therapy_site_context", "evidence_quality"]:
        layer_manifest[layer].update({
            "source_type": "missing", "source_name": "missing", "retrieval_status": "missing_optional_layer",
            "is_external": False, "confidence": 0.0,
        })
    _write_json(results / "layer_resolution_manifest.json", layer_manifest)
    return seed


def _build_v4_equivalent_package(tmp_path: Path) -> dict[str, str]:
    workspace = _workspace(tmp_path)
    seed = _write_v3_manifests(workspace)
    layer_manifest = json.loads((workspace / "results" / "layer_resolution_manifest.json").read_text(encoding="utf-8"))
    pd.DataFrame([
        {"layer": layer, **payload}
        for layer, payload in layer_manifest.items()
    ]).to_csv(workspace / "results" / "layer_resolution_summary.csv", index=False)
    (workspace / "results" / "layer_resolution_summary.md").write_text("# stale summary", encoding="utf-8")

    rows = []
    for index in range(25):
        rows.append({
            "protein_id": f"P{index:05d}", "gene": f"gene{index}",
            "therapeutic_priority_score": 0.7, "evidence_confidence_score": 0.6,
            "selectivity_score": 0.8,
            "real_evidence_layer_count": 9, "phase3_real_evidence_layer_count": 9,
            "demo_or_default_layer_count": 0, "proxy_layer_count": 3,
            "missing_layer_count": 7, "negative_evidence_layer_count": 2 if index < 7 else 0,
            "evidence_mixture_label": "stale_label",
        })
    ranking = pd.DataFrame(rows)
    phase3 = ranking.sample(frac=1.0, random_state=7).reset_index(drop=True)
    phase3["real_evidence_layer_count"] = 0
    phase3["phase3_real_evidence_layer_count"] = 0
    ranking.to_csv(workspace / "results" / "ranking_nodos.csv", index=False)
    phase3.to_csv(workspace / "results" / "ranking_nodos_phase3.csv", index=False)

    return build_online_only_review_package(
        run_dir=tmp_path / "run", workspace=workspace, organism="Test bacterium", seed_result=seed,
        pipeline_status="completed", pipeline_error="", pipeline_result={"ok": True},
        online_source_mode="online_strict",
    )


def test_v3_audit_review_and_interpretation_are_coherent(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    seed = _write_v3_manifests(workspace)
    ranking = pd.DataFrame([{
        "protein_id": "P1", "gene": "geneA", "therapeutic_priority_score": 0.7,
        "evidence_confidence_score": 0.6, "human_homolog": 1, "localization": "outer_membrane",
        "domain_overlap_score": 0.5, "core_genome_presence": 0.8, "strain_coverage_score": 0.9,
        "network_centrality": 0.0, "real_evidence_layer_count": 9,
        "demo_or_default_layer_count": 0, "proxy_layer_count": 1,
        "evidence_mixture_label": "mixed_real_demo_proxy",
    }])
    ranking.to_csv(workspace / "results" / "ranking_nodos.csv", index=False)
    ranking.to_csv(workspace / "results" / "ranking_nodos_phase3.csv", index=False)

    package = build_online_only_review_package(
        run_dir=tmp_path / "run", workspace=workspace, organism="Test bacterium", seed_result=seed,
        pipeline_status="completed", pipeline_error="", pipeline_result={"ok": True},
        online_source_mode="online_strict",
    )

    audit = pd.read_csv(package["online_only_provider_audit.csv"]).set_index("layer_key")
    diamond = audit.loc["human_homologs"]
    assert bool(diamond["retrieval_success"])
    assert bool(diamond["mapping_success"])
    assert bool(diamond["usable_evidence"])
    assert bool(diamond["affects_score"])
    assert bool(diamond["technical_success"])
    assert not bool(diamond["connectivity_success"])
    string = audit.loc["functional_network"]
    assert not bool(string["usable_evidence"])
    assert string["fallback_reason"] == "api_response_no_usable_mapping"
    assert string["retrieval_status"] == "degraded_no_usable_mapping"
    assert not bool(audit.loc["essentiality", "usable_evidence"])
    assert not bool(audit.loc["literature_support", "affects_score"])
    assert bool(audit.loc["localization", "affects_score"])
    assert bool(audit.loc["host_annotation", "affects_score"])
    assert bool(audit.loc["strain_conservation", "affects_score"])
    assert not bool(audit.loc["host_annotation", "fallback_used"])
    assert not bool(audit.loc["literature_support", "fallback_used"])

    review = Path(package["ONLINE_ONLY_REVIEW.md"]).read_text(encoding="utf-8")
    assert "Providers contacted successfully" in review
    assert "Providers with usable evidence" in review
    assert "Providers degraded" in review
    assert "Providers failed" in review
    assert "Providers not implemented" in review
    resolved_line = next(line for line in review.splitlines() if "Layers resolved with usable evidence" in line)
    assert "essentiality" not in resolved_line
    assert "functional_network" not in resolved_line
    unresolved_line = next(line for line in review.splitlines() if "Layers unresolved/missing" in line)
    assert "essentiality" in unresolved_line

    packaged_ranking = pd.read_csv(package["ranking_nodos.csv"])
    phase3 = pd.read_csv(package["ranking_nodos_phase3.csv"])
    interpretation = pd.read_csv(package["online_only_candidate_interpretation.csv"])
    for frame in (packaged_ranking, phase3, interpretation):
        assert frame.loc[0, "confidence_evidence_tier"] == "partial_online_computational"
        assert frame.loc[0, "provenance_status"] == "partial_external_online"
        assert frame.loc[0, "retrieval_mode"] == "online_strict_partial"
        assert frame.loc[0, "data_realism_flag"] == "computed_online"
    assert "string_api" not in interpretation.loc[0, "providers_succeeded"]
    assert packaged_ranking.loc[0, "evidence_mixture_label"] == "mixed_real_proxy"
    assert packaged_ranking.loc[0, "real_evidence_layer_count"] < 9


@pytest.mark.parametrize("layer_key", ["clinical_impact", "curated_disease_context", "therapy_site_context"])
def test_online_strict_blocks_controlled_context_and_proxy_materialization(tmp_path: Path, layer_key: str) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    config["online_sources"]["source_mode_effective"] = "online_strict"
    result = fetch_layer_external_source(
        layer_key, workspace, f"{layer_key}.csv", config, "controlled_therapeutic_context_v2"
    )
    resolution = _resolve_single_layer(workspace, config, get_layer_definition(layer_key))

    assert result["status"] == "disabled_by_online_strict_policy"
    assert result["path"] is None
    assert not (workspace / "data_external" / f"{layer_key}.csv").exists()
    assert resolution.resolved_from == "missing"
    assert resolution.retrieval_status == "missing_optional_layer"


def test_online_strict_rejects_explicit_unresolved_fallback(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no es compatible con online_strict"):
        run_online_only_validation(
            project_root=tmp_path, organism="Test bacterium", taxon_id="123",
            online_source_mode="online_strict", materialize_unresolved_required_fallback=True,
        )


def test_real_proxy_label_excludes_demo_when_demo_count_is_zero() -> None:
    assert _evidence_mixture_label(real=2, demo_default=0, proxy=1, missing=0, negative=0) == "mixed_real_proxy"


def test_v4_rankings_share_canonical_provenance_by_protein_id(tmp_path: Path) -> None:
    package = _build_v4_equivalent_package(tmp_path)
    provenance_columns = [
        "real_evidence_layer_count", "phase3_real_evidence_layer_count", "proxy_layer_count",
        "missing_layer_count", "negative_evidence_layer_count", "evidence_mixture_label",
    ]
    ranking = pd.read_csv(package["ranking_nodos.csv"]).set_index("protein_id").sort_index()
    phase3 = pd.read_csv(package["ranking_nodos_phase3.csv"]).set_index("protein_id").sort_index()

    pd.testing.assert_frame_equal(ranking[provenance_columns], phase3[provenance_columns])
    assert ranking["real_evidence_layer_count"].eq(1).all()
    assert ranking["phase3_real_evidence_layer_count"].eq(1).all()
    assert ranking["proxy_layer_count"].eq(3).all()
    assert ranking["evidence_mixture_label"].value_counts().to_dict() == {
        "mixed_real_proxy": 18,
        "real_evidence_with_negative_signal": 7,
    }
    diamond_manifest = json.loads(Path(package["human_homology_diamond_manifest.json"]).read_text(encoding="utf-8"))
    assert diamond_manifest["affects_score"] is True


def test_v4_unresolved_layers_match_audit_review_and_interpretation(tmp_path: Path) -> None:
    package = _build_v4_equivalent_package(tmp_path)
    audit = pd.read_csv(package["online_only_provider_audit.csv"])
    audit_unresolved = audit.loc[
        ~audit["usable_evidence"].astype(bool) & audit["layer_key"].ne("candidate_seed"), "layer_key"
    ].astype(str).tolist()
    interpretation = pd.read_csv(package["online_only_candidate_interpretation.csv"])
    interpretation_unresolved = interpretation.loc[0, "unresolved_layers"].split(";")
    review = Path(package["ONLINE_ONLY_REVIEW.md"]).read_text(encoding="utf-8")
    unresolved_line = next(line for line in review.splitlines() if "Layers unresolved/missing" in line)
    review_unresolved = unresolved_line.split("`")[1].split(";")

    assert len(audit_unresolved) == 12
    assert audit_unresolved == review_unresolved == interpretation_unresolved
    assert "functional_network" in audit_unresolved
    failed_line = next(line for line in review.splitlines() if "Providers failed" in line)
    assert "uniprot_rest" not in failed_line
    for line in [line for line in review.splitlines() if line.startswith("- Providers ")]:
        providers = [value.strip() for value in line.split("`")[1].split(";") if value.strip() != "none"]
        assert len(providers) == len(set(providers))

    summary = pd.read_csv(package["layer_resolution_summary.csv"]).set_index("layer")
    expected_status = {
        "essentiality": "candidate_seed_only_not_essentiality_evidence",
        "functional_network": "degraded_no_usable_mapping",
        "host_annotation": "api_real",
        "literature_support": "api_real",
        "localization": "inherited_from_candidate_seed",
    }
    assert summary.loc[list(expected_status), "retrieval_status"].to_dict() == expected_status
    assert summary.loc["clinical_impact", "source_type"] == "missing"
    assert summary.loc["therapy_site_context", "source_type"] == "missing"
    summary_markdown = Path(package["layer_resolution_summary.md"]).read_text(encoding="utf-8")
    for status in expected_status.values():
        assert status in summary_markdown
