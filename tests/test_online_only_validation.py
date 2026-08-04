from __future__ import annotations

import gzip
import json
import ssl
import shutil
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.human_homology_diamond import materialize_candidate_fasta
from src.nodos_funcionales.online_sources import effective_online_source_mode, fetch_layer_external_source
from src.nodos_funcionales.online_http import get_ssl_context
from src.nodos_funcionales.online_only_validation import (
    build_explicit_diamond_run_config,
    build_online_only_candidate_interpretation,
    build_online_only_provider_audit,
    build_online_only_provenance_summary,
    build_online_only_review_package,
    enrich_online_only_downstream_layers,
    default_online_only_run_dir,
    run_online_only_validation,
    run_pseudomonas_online_only_validation,
    seed_candidate_essentiality_from_uniprot,
    _attempt_string_enrichment,
    _materialize_unresolved_required_external_layers,
    _write_online_only_config,
)
from tests.helpers import PROJECT_ROOT


class _EmptyFastaResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return b""


@pytest.fixture(autouse=True)
def _block_unmocked_candidate_fasta_network():
    with patch("src.nodos_funcionales.human_homology_diamond.urlopen", return_value=_EmptyFastaResponse()):
        yield


def test_online_http_ssl_context_uses_certifi_ca_bundle() -> None:
    with patch("src.nodos_funcionales.online_http.certifi.where", return_value="C:/certifi/cacert.pem") as where_mock:
        with patch("src.nodos_funcionales.online_http.ssl.create_default_context") as context_mock:
            context = get_ssl_context()

    where_mock.assert_called_once_with()
    context_mock.assert_called_once_with()
    context.load_verify_locations.assert_called_once_with(cafile="C:/certifi/cacert.pem")


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "config").mkdir(parents=True)
    (workspace / "data_raw").mkdir()
    (workspace / "data_external").mkdir()
    (workspace / "results").mkdir()
    shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
    return workspace


def test_online_only_string_requires_usable_edge_before_materializing_layer(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    candidates = pd.DataFrame(
        [{"protein_id": "P1", "gene": "gene1"}]
    )
    diagnostic = pd.DataFrame(
        [
            {
                "protein_id": "P1",
                "gene": "gene1",
                "network_centrality": 0.0,
                "pathway_bottleneck_score": 0.0,
                "functional_dependency_score": 0.0,
                "mapping_status": "synonym_match",
                "usable_for_network": True,
            }
        ]
    )
    provider_manifest = {
        "api_success": True,
        "connectivity_success": True,
        "retrieval_success": True,
        "mapping_success": True,
        "usable_evidence": False,
        "affects_score": False,
        "edge_count": 1,
        "usable_edge_count": 0,
        "usable_mapping_count": 1,
        "degraded_mapping_count": 0,
        "retrieval_status": "degraded_no_usable_edge",
        "fallback_reason": "api_response_no_usable_edge",
        "source_used": "api_real",
        "network_taxon_id": "85962",
    }

    with patch(
        "src.nodos_funcionales.online_only_validation.fetch_string_functional_network",
        return_value={
            "functional_network": diagnostic,
            "manifest": provider_manifest,
        },
    ):
        result = _attempt_string_enrichment(
            workspace=workspace,
            organism_name="Helicobacter pylori",
            taxon_id="210",
            config=config,
            mode="online_strict",
            candidates=candidates,
        )

    assert result["retrieval_success"] is True
    assert result["mapping_success"] is True
    assert result["usable_evidence"] is False
    assert result["affects_score"] is False
    assert result["usable_edge_count"] == 0
    assert result["retrieval_status"] == "degraded_no_usable_edge"
    assert not (
        workspace / "data_external" / "functional_network.csv"
    ).exists()

    audit = build_online_only_provider_audit(workspace, {})
    network = audit.loc[
        audit["layer_key"].astype(str).eq("functional_network")
    ].iloc[0]
    assert int(network["retrieved_record_count"]) == 1
    assert int(network["matched_candidate_count"]) == 1
    assert int(network["raw_edge_count"]) == 1
    assert int(network["usable_edge_count"]) == 0
    assert bool(network["usable_evidence"]) is False
    assert bool(network["affects_score"]) is False


def test_generic_entrypoint_and_pseudomonas_wrapper_remain_available(tmp_path: Path) -> None:
    assert callable(run_online_only_validation)
    with patch("src.nodos_funcionales.online_only_validation.run_online_only_validation", return_value={"ok": True}) as generic:
        result = run_pseudomonas_online_only_validation(tmp_path, max_seed_candidates=7)

    assert result == {"ok": True}
    generic.assert_called_once_with(
        project_root=tmp_path,
        organism="Pseudomonas aeruginosa",
        organism_slug="pseudomonas_aeruginosa",
        taxon_id=287,
        run_dir=None,
        max_candidates=7,
        online_source_mode="online_strict",
        taxon_resolution_mode="online_optional",
        refresh_taxon_cache=False,
        no_write_taxon_cache=True,
        materialize_unresolved_required_fallback=False,
    )


def test_online_only_config_preserves_complete_diamond_execution_settings(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config_path = workspace / "config" / "params.yaml"
    before = load_config(config_path)["online_sources"]["human_homology_diamond"]

    _write_online_only_config(config_path, "online_optional")

    after_config = load_config(config_path)
    after = after_config["online_sources"]["human_homology_diamond"]
    preserved_keys = {
        "enabled",
        "execution_mode",
        "allow_execution",
        "diamond_executable",
        "reference_fasta_path",
        "database_prefix",
        "reuse_cache",
        "strong_homology_thresholds",
        "partial_similarity_thresholds",
    }
    assert {key: after[key] for key in preserved_keys} == {key: before[key] for key in preserved_keys}
    assert after_config["online_sources"]["source_mode_effective"] == "online_optional"
    assert after_config["layer_resolution"]["layers"]["human_homologs"]["external_provider"] == "human_homology_diamond"


@pytest.mark.parametrize(
    ("requested", "canonical"),
    [("online_strict", "online_strict"), ("online_only", "online_strict"), ("hybrid_curated", "hybrid_curated")],
)
def test_generated_online_only_config_survives_internal_mode_validation(
    tmp_path: Path, requested: str, canonical: str
) -> None:
    workspace = _workspace(tmp_path)
    config_path = workspace / "config" / "params.yaml"

    _write_online_only_config(config_path, requested)
    reloaded = load_config(config_path)

    assert reloaded["online_sources"]["source_mode_effective"] == canonical
    assert effective_online_source_mode(reloaded) == canonical


def test_online_only_config_propagates_every_provider_switch_and_dataset_path(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config_path = workspace / "config" / "params.yaml"
    vfdb_dataset = tmp_path / "vfdb.csv"
    deg_dataset = tmp_path / "deg.csv"
    vfdb_dataset.write_text("gene,category\nvacA,toxin\n", encoding="utf-8")
    deg_dataset.write_text("gene,evidence\ngyrB,knockout\n", encoding="utf-8")

    _write_online_only_config(
        config_path,
        "online_optional",
        enable_string=False,
        enable_interpro=False,
        enable_vfdb=False,
        enable_deg=False,
        enable_bvbrc=False,
        vfdb_dataset_path=vfdb_dataset,
        deg_dataset_path=deg_dataset,
    )

    config = load_config(config_path)
    for provider in ("string", "interpro", "vfdb", "deg", "bvbrc"):
        assert config["online_sources"][provider]["enabled"] is False
    assert config["online_sources"]["vfdb"]["local_dataset_path"] == str(vfdb_dataset)
    assert config["online_sources"]["deg"]["local_dataset_path"] == str(deg_dataset)


def test_layer_resolver_does_not_call_disabled_network_provider(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config_path = workspace / "config" / "params.yaml"
    _write_online_only_config(config_path, "online_optional", enable_string=False)
    config = load_config(config_path)
    (workspace / "results" / "organism_profile.json").write_text(
        json.dumps({"organism_canonical_name": "Escherichia coli", "taxon_id": "562"}),
        encoding="utf-8",
    )

    with patch("src.nodos_funcionales.online_sources.fetch_string_functional_network") as provider:
        result = fetch_layer_external_source(
            "functional_network",
            workspace,
            "functional_network.csv",
            config,
            "string_real",
        )

    provider.assert_not_called()
    assert result["status"] == "provider_disabled_by_configuration"


def test_explicit_diamond_cache_only_profile_requires_existing_tsv(tmp_path: Path) -> None:
    cached_tsv = tmp_path / "cached_diamond.tsv"
    cached_tsv.write_text(
        "P12345|SEEDA_BACT\tsp|Q02880|TOP2B_HUMAN\t30.0\t4\t4\t150\t1\t4\t1\t4\t1e-20\t80\n",
        encoding="utf-8",
    )

    profile = build_explicit_diamond_run_config(
        tmp_path,
        enabled=True,
        execution_mode="cache_only",
        cached_tsv_path=cached_tsv,
    )

    assert profile is not None
    assert profile["enabled"] is True
    assert profile["execution_mode"] == "cache_only"
    assert profile["allow_execution"] is False
    assert profile["allow_download"] is False
    assert profile["reference_fasta_path"] == ""
    assert profile["database_prefix"] == ""
    assert profile["cached_tsv_path"] == str(cached_tsv.resolve())


def test_explicit_diamond_profile_rejects_implicit_or_incomplete_activation(tmp_path: Path) -> None:
    cached_tsv = tmp_path / "cached_diamond.tsv"
    cached_tsv.write_text("cached\n", encoding="utf-8")

    with pytest.raises(ValueError, match="explicit enable_diamond"):
        build_explicit_diamond_run_config(
            tmp_path,
            enabled=False,
            cached_tsv_path=cached_tsv,
        )

    with pytest.raises(ValueError, match="requires reference_fasta_path and database_prefix"):
        build_explicit_diamond_run_config(
            tmp_path,
            enabled=True,
            execution_mode="execute",
        )


def test_online_only_materializer_then_explicit_diamond_execution(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config_path = workspace / "config" / "params.yaml"
    reference_fasta = workspace / "data_external" / "human_reference_UP000005640.faa.gz"
    fixture_text = (
        PROJECT_ROOT
        / "tests"
        / "fixtures"
        / "human_homology_synthetic"
        / "synthetic_human_reference_fixture.faa"
    ).read_text(encoding="utf-8")
    with gzip.open(reference_fasta, "wt", encoding="utf-8") as handle:
        handle.write(fixture_text)

    diamond_run_config = build_explicit_diamond_run_config(
        workspace,
        enabled=True,
        execution_mode="execute",
        reference_fasta_path=reference_fasta,
        database_prefix=workspace / "data_external" / "human_reference_UP000005640.dmnd",
    )
    assert diamond_run_config is not None
    _write_online_only_config(
        config_path,
        "online_optional",
        diamond_run_config=diamond_run_config,
    )
    config = load_config(config_path)
    diamond_cfg = config["online_sources"]["human_homology_diamond"]
    assert diamond_cfg["enabled"] is True
    assert diamond_cfg["execution_mode"] == "execute"
    assert diamond_cfg["allow_execution"] is True
    assert diamond_cfg["allow_download"] is False
    assert diamond_cfg["reference_fasta_path"] == str(reference_fasta.resolve())
    assert diamond_cfg["database_prefix"] == str(
        (workspace / "data_external" / "human_reference_UP000005640").resolve()
    )

    candidates = pd.DataFrame([{"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"}])
    candidate_manifest = materialize_candidate_fasta(
        workspace,
        diamond_cfg,
        candidates=candidates,
        mode="online_optional",
        seed_records={
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "SEEDA_BACT",
                    "sequence": {"value": "MAAA"},
                }
            ]
        },
    )
    assert candidate_manifest["candidate_sequence_count"] == 1

    tsv_path = workspace / "data_external" / "human_homology_diamond.tsv"

    def fake_run(command: list[str], **_kwargs: object):
        class Result:
            stdout = "diamond version 2.1.9"
            stderr = ""
            returncode = 0

        if len(command) > 1 and command[1] == "blastp":
            tsv_path.write_text(
                "P12345|SEEDA_BACT\tsp|Q02880|TOP2B_HUMAN\t30.0\t4\t4\t150\t1\t4\t1\t4\t1e-20\t80\n",
                encoding="utf-8",
            )
        return Result()

    with patch("src.nodos_funcionales.human_homology_diamond.subprocess.run", side_effect=fake_run):
        result = fetch_layer_external_source(
            layer_key="human_homologs",
            workspace=workspace,
            filename="human_homologs.csv",
            config=config,
            provider_name="human_homology_diamond",
        )

    manifest = json.loads((workspace / "results" / "human_homology_diamond_manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "diamond_blastp_executed"
    assert manifest["execution_status"] == "executed"
    assert manifest["execution_started"] is True
    assert manifest["execution_completed"] is True
    assert manifest["execution_failed"] is False
    assert manifest["affects_score"] is True
    assert manifest["query_fasta_path"] == str(workspace / "data_external" / "candidate_proteins.faa")
    assert manifest["database_path"].endswith("human_reference_UP000005640.dmnd")
    assert manifest["tsv_path"] == str(tsv_path)

    # A retry fallback caused by an unrelated provider must not overwrite valid DIAMOND evidence.
    canonical_path = workspace / "data_external" / "human_homologs.csv"
    before_fallback = pd.read_csv(canonical_path)
    _materialize_unresolved_required_external_layers(
        workspace,
        config,
        {"source_used": "api_real"},
        fallback_reason="recoverable_provider_failure:not_found",
    )
    after_fallback = pd.read_csv(canonical_path)
    pd.testing.assert_frame_equal(after_fallback, before_fallback, check_dtype=False)
    assert after_fallback.loc[0, "source_database"] == "computed_diamond_human_homology_v1"
    assert after_fallback.loc[0, "homology_lookup_status"] == "diamond_hit"
    assert not after_fallback["source_database"].astype(str).eq("provider_not_found").any()
    fallback_audit = json.loads(
        (workspace / "results" / "online_only_unresolved_required_fallback_manifest.json").read_text(encoding="utf-8")
    )
    assert fallback_audit["preserved_valid_layers"] == ["human_homologs"]


def test_organism_slug_changes_default_online_only_output_path(tmp_path: Path) -> None:
    pseudomonas = default_online_only_run_dir(tmp_path, "pseudomonas_aeruginosa", "20260619")
    ecoli = default_online_only_run_dir(tmp_path, "escherichia_coli", "20260619")

    assert pseudomonas != ecoli
    assert ecoli == tmp_path / "results" / "online_only_runs" / "escherichia_coli_20260619"


def test_strain_slug_can_keep_strain_run_paths_distinct(tmp_path: Path) -> None:
    species = default_online_only_run_dir(tmp_path, "mycobacterium_tuberculosis", "20260619")
    strain = default_online_only_run_dir(tmp_path, "mycobacterium_tuberculosis_h37rv", "20260619")

    assert species != strain
    assert strain.name == "mycobacterium_tuberculosis_h37rv_20260619"


def test_uniprot_seed_materializes_external_unresolved_candidates(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    payload = {
        "results": [
            {
                "primaryAccession": "P12345",
                "uniProtkbId": "TEST_PSEAE",
                "genes": [{"geneName": {"value": "seedA"}}],
            }
        ]
    }
    with patch("src.nodos_funcionales.online_only_validation.urlopen_json", return_value=payload) as helper_mock:
        manifest = seed_candidate_essentiality_from_uniprot(
            workspace=workspace,
            organism_name="Pseudomonas aeruginosa",
            taxon_id="287",
            config=config,
            max_candidates=1,
            mode="online_optional",
        )

    helper_mock.assert_called_once()
    assert manifest["api_success"] is True
    assert manifest["source_used"] == "api_real"
    assert manifest["retrieval_status"] == "api_real"
    assert manifest["retrieved_record_count"] == 1
    assert manifest["matched_candidate_count"] == 1
    assert manifest["data_realism_flag"] == "computed_online"
    assert manifest["evidence_level"] == "computational_online_annotation"
    assert manifest["http_helper_used"] == "nodos_funcionales.online_http.urlopen_json"
    assert manifest["provider_function"] == "seed_candidate_essentiality_from_uniprot->_query_uniprot_seed"
    assert "provider_url" in manifest
    assert "certifi_path" in manifest
    assert "openssl_version" in manifest
    assert "sys_executable" in manifest
    seed = pd.read_csv(workspace / "data_external" / "essentiality.csv")
    assert seed.loc[0, "protein_id"] == "P12345"
    assert pd.isna(seed.loc[0, "essential"])
    assert seed.loc[0, "essentiality_status"] == "unresolved_online_seed"
    assert seed.loc[0, "evidence_source_type"] == "online_external_candidate_discovery"
    assert "experimentally validated" in seed.loc[0, "candidate_seed_note"]


def test_uniprot_seed_tls_failure_is_recorded_as_unresolved_fallback(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    error = ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED")

    with patch("src.nodos_funcionales.online_only_validation.urlopen_json", side_effect=error):
        manifest = seed_candidate_essentiality_from_uniprot(
            workspace=workspace,
            organism_name="Pseudomonas aeruginosa",
            taxon_id="287",
            config=config,
            max_candidates=1,
            mode="online_optional",
        )

    assert manifest["api_attempted"] is True
    assert manifest["api_success"] is False
    assert manifest["fallback_used"] is True
    assert "tls_certificate_verification_failed" in manifest["fallback_reason"]
    assert manifest["evidence_level"] == "unresolved"
    seed = pd.read_csv(workspace / "data_external" / "essentiality.csv")
    assert seed.empty


def test_online_only_404_pipeline_failure_retries_with_unresolved_layers(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"

    def fake_discovery(**kwargs):
        workspace = Path(kwargs["workspace"])
        (workspace / "config").mkdir(parents=True, exist_ok=True)
        (workspace / "data_external").mkdir(parents=True, exist_ok=True)
        (workspace / "data_raw").mkdir(parents=True, exist_ok=True)
        (workspace / "results").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", workspace / "config" / "params.yaml")
        profile = {
            "organism_input_name": "Pseudomonas aeruginosa",
            "organism_canonical_name": "Pseudomonas aeruginosa",
            "taxon_id": 287,
            "taxon_resolution_status": "test_profile",
            "taxon_resolution_notes": "test profile",
        }
        return {"profile": profile, "manifest": {}, "workspace": workspace}

    def fake_seed(**kwargs):
        workspace = Path(kwargs["workspace"])
        pd.DataFrame(
            [{"protein_id": "P12345", "gene": "seedA", "essential": pd.NA, "database": "uniprot_seed"}]
        ).to_csv(workspace / "data_external" / "essentiality.csv", index=False)
        return {
            "source_used": "api_real",
            "retrieval_status": "api_real",
            "api_attempted": True,
            "api_success": True,
            "candidate_count": 1,
            "matched_candidate_count": 1,
            "retrieved_record_count": 1,
            "evidence_level": "computational_online_annotation",
        }

    with patch("src.nodos_funcionales.online_only_validation.prepare_discovery_workspace", side_effect=fake_discovery):
        with patch("src.nodos_funcionales.online_only_validation.seed_candidate_essentiality_from_uniprot", side_effect=fake_seed):
            with patch("src.nodos_funcionales.online_only_validation.enrich_online_only_downstream_layers", return_value={}):
                with patch(
                    "src.nodos_funcionales.online_only_validation.run_pipeline",
                    side_effect=[Exception("not_found: HTTP 404"), {"ok": True}],
                ):
                    result = run_online_only_validation(
                        project_root=PROJECT_ROOT,
                        organism="Pseudomonas aeruginosa",
                        organism_slug="pseudomonas_aeruginosa",
                        taxon_id=287,
                        run_dir=run_dir,
                        max_candidates=1,
                    )

    workspace = run_dir / "workspace"
    assert result["pipeline_status"] == "completed_after_unresolved_fallback"
    assert "not_found: HTTP 404" in result["pipeline_error"]
    virulence = pd.read_csv(workspace / "data_external" / "virulence.csv")
    assert virulence.loc[0, "source_database"] == "provider_not_found"
    assert virulence.loc[0, "evidence"] == "unresolved"
    assert pd.isna(virulence.loc[0, "virulence_score"])
    audit = json.loads((workspace / "results" / "online_only_unresolved_required_fallback_manifest.json").read_text(encoding="utf-8"))
    assert audit["retrieval_status"] == "unresolved"
    assert audit["source_database"] == "provider_not_found"
    assert audit["evidence"] == "unresolved"
    assert "recoverable_provider_failure:not_found" in audit["fallback_reason"]


def test_uniprot_seed_empty_success_is_not_tls_failure(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")

    with patch("src.nodos_funcionales.online_only_validation.urlopen_json", return_value={"results": []}):
        manifest = seed_candidate_essentiality_from_uniprot(
            workspace=workspace,
            organism_name="Pseudomonas aeruginosa",
            taxon_id="287",
            config=config,
            max_candidates=1,
            mode="online_optional",
        )

    assert manifest["api_attempted"] is True
    assert manifest["api_success"] is True
    assert manifest["source_used"] == "api_real"
    assert manifest["candidate_count"] == 0
    assert manifest["fallback_reason"] == "api_success_no_candidate_records"
    assert "tls_certificate_verification_failed" not in manifest["fallback_reason"]
    assert manifest["data_realism_flag"] == "computed_online"


def test_online_only_provenance_summary_flags_user_curated_as_invalid(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    manifest = {
        "essentiality": {
            "source_type": "external",
            "source_name": "uniprot_candidate_seed",
            "retrieval_status": "resolved_from_external",
            "is_user_supplied": False,
            "is_external": True,
            "is_cached": False,
            "is_proxy": False,
            "confidence": 0.60,
        },
        "virulence": {
            "source_type": "missing",
            "source_name": "missing",
            "retrieval_status": "missing_optional_layer",
            "is_user_supplied": False,
            "is_external": False,
            "is_cached": False,
            "is_proxy": False,
            "confidence": 0.0,
        },
        "human_homologs": {
            "source_type": "user",
            "source_name": "human_homologs.csv",
            "retrieval_status": "resolved_from_user",
            "is_user_supplied": True,
            "is_external": False,
            "is_cached": False,
            "is_proxy": False,
            "confidence": 0.95,
        },
    }
    (workspace / "results" / "layer_resolution_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    summary = build_online_only_provenance_summary(workspace)

    by_layer = summary.set_index("layer_key")
    assert by_layer.loc["essentiality", "online_evidence_availability"] == "unresolved_or_missing"
    assert by_layer.loc["virulence", "online_evidence_availability"] == "unresolved_or_missing"
    assert by_layer.loc["human_homologs", "online_evidence_availability"] == "invalid_user_curated_detected"
    assert bool(by_layer.loc["human_homologs", "experimental_validation_supported"]) is False


def test_online_only_candidate_interpretation_never_claims_experimental_validation(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    pd.DataFrame(
        [
            {
                "protein_id": "PA0001",
                "gene": "seedA",
                "therapeutic_priority_score": 0.7,
                "evidence_confidence_score": 0.2,
                "therapeutic_role": "low_priority_candidate",
                "data_realism_flag": "external_only_unresolved",
                "missing_evidence_flags": "missing_essentiality",
            }
        ]
    ).to_csv(workspace / "results" / "ranking_nodos.csv", index=False)

    interpretation = build_online_only_candidate_interpretation(workspace)

    assert bool(interpretation.loc[0, "experimental_validation_supported"]) is False
    assert interpretation.loc[0, "online_only_validation_status"] == "computational_hypothesis_only"
    assert "did not retrieve experimental validation" in interpretation.loc[0, "interpretation_note"]


def test_provider_audit_records_explicit_fields_for_external_layers(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    seed_manifest = {
        "layer_key": "candidate_seed",
        "provider_name": "uniprot_rest",
        "provider_endpoint_or_mode": "https://rest.uniprot.org/uniprotkb/search",
        "api_attempted": True,
        "api_success": True,
        "retrieved_record_count": 2,
        "matched_candidate_count": 2,
        "fallback_used": False,
        "fallback_reason": "",
        "retrieval_status": "api_real",
        "source_used": "api_real",
        "data_realism_flag": "computed_online",
        "evidence_level": "computational_online_annotation",
        "candidate_count": 2,
        "generated_at_utc": "2026-06-12T00:00:00+00:00",
    }
    layer_manifest = {
        "localization": {
            "source_type": "external",
            "source_name": "uniprot_rest",
            "retrieval_status": "external_not_requested",
            "is_user_supplied": False,
            "is_external": True,
            "confidence": 0.0,
        },
        "functional_network": {
            "source_type": "missing",
            "source_name": "missing",
            "retrieval_status": "missing_optional_layer",
            "is_user_supplied": False,
            "is_external": False,
            "confidence": 0.0,
        },
    }
    (workspace / "results" / "layer_resolution_manifest.json").write_text(json.dumps(layer_manifest), encoding="utf-8")

    audit = build_online_only_provider_audit(workspace, seed_manifest)

    required = {
        "layer_key",
        "provider_name",
        "provider_endpoint_or_mode",
        "provider_function",
        "provider_mode",
        "provider_attempted",
        "provider_success",
        "api_attempted",
        "api_success",
        "retrieved_record_count",
        "matched_candidate_count",
        "fallback_used",
        "fallback_reason",
        "retrieval_status",
        "source_used",
        "data_realism_flag",
        "evidence_level",
        "affects_score",
        "inherited_from_candidate_seed",
        "generated_at_utc",
    }
    assert required.issubset(audit.columns)
    by_layer = audit.set_index("layer_key")
    assert bool(by_layer.loc["candidate_seed", "api_success"]) is True
    assert by_layer.loc["candidate_seed", "evidence_level"] == "computational_online_annotation"
    assert bool(by_layer.loc["localization", "api_success"]) is False
    assert by_layer.loc["localization", "retrieval_status"] == "provider_unavailable_or_not_implemented"
    assert by_layer.loc["functional_network", "evidence_level"] == "unresolved"


def test_provider_audit_prefers_final_dedicated_manifest_over_preliminary_marker(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "results" / "layer_resolution_manifest.json").write_text(
        json.dumps(
            {
                "strain_conservation": {
                    "source_name": "bvbrc_real",
                    "retrieval_status": "api_real",
                }
            }
        ),
        encoding="utf-8",
    )
    (workspace / "results" / "online_only_strain_conservation_manifest.json").write_text(
        json.dumps(
            {
                "provider_name": "bvbrc",
                "retrieval_status": "deferred_to_layer_resolver",
                "source_used": "deferred_to_layer_resolver",
                "api_attempted": False,
                "api_success": False,
            }
        ),
        encoding="utf-8",
    )
    (workspace / "results" / "bvbrc_conservation_manifest.json").write_text(
        json.dumps(
            {
                "provider_name": "bvbrc_real",
                "provider_url": "https://www.bv-brc.org/api/genome_feature/",
                "retrieval_status": "api_real",
                "source_used": "api_real",
                "provider_attempted": True,
                "provider_success": True,
                "api_attempted": True,
                "api_success": True,
                "feature_records_retrieved": 12,
                "protein_count_mapped": 2,
                "evidence_level": "computational_online_evidence",
            }
        ),
        encoding="utf-8",
    )

    audit = build_online_only_provider_audit(workspace, {})
    bvbrc = audit.set_index("layer_key").loc["strain_conservation"]

    assert bool(bvbrc["provider_attempted"]) is True
    assert bool(bvbrc["provider_success"]) is True
    assert bool(bvbrc["api_success"]) is True
    assert bvbrc["retrieval_status"] == "api_real"
    assert bvbrc["matched_candidate_count"] == 2


def test_provider_audit_uses_dedicated_diamond_manifest_semantics(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "results" / "human_homology_diamond_manifest.json").write_text(
        json.dumps(
            {
                "provider_name": "human_homology_diamond",
                "provider_mode": "local_executable",
                "retrieval_status": "diamond_blastp_executed",
                "execution_status": "executed",
                "provider_attempted": True,
                "provider_success": True,
                "result_row_count": 25,
                "hit_count": 7,
                "no_hit_count": 18,
                "matched_candidate_count": 7,
                "evidence_level": "sequence_alignment",
                "data_realism_flag": "computed_local",
                "affects_score": False,
            }
        ),
        encoding="utf-8",
    )

    audit = build_online_only_provider_audit(workspace, {})
    diamond = audit.set_index("layer_key").loc["human_homologs"]

    assert diamond["provider_name"] == "human_homology_diamond"
    assert diamond["provider_endpoint_or_mode"] == "local_executable"
    assert bool(diamond["provider_attempted"]) is True
    assert bool(diamond["provider_success"]) is True
    assert bool(diamond["api_attempted"]) is False
    assert bool(diamond["api_success"]) is False
    assert diamond["retrieved_record_count"] == 25
    assert diamond["matched_candidate_count"] == 7
    assert diamond["retrieval_status"] == "diamond_blastp_executed"
    assert bool(diamond["retrieval_success"]) is True
    assert bool(diamond["mapping_success"]) is True
    assert bool(diamond["usable_evidence"]) is True
    assert bool(diamond["affects_score"]) is True


def test_online_only_enrichment_attempts_string_and_materializes_network(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    pd.DataFrame(
        [
            {"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"},
            {"protein_id": "Q12345", "gene": "seedB", "candidate_seed_accession": "Q12345"},
        ]
    ).to_csv(workspace / "data_external" / "essentiality.csv", index=False)
    (workspace / "results" / "online_only_uniprot_seed_records.json").write_text('{"results":[]}', encoding="utf-8")
    network = pd.DataFrame(
        [
            {
                "protein_id": "P12345",
                "gene": "seedA",
                "network_centrality": 0.7,
                "pathway_bottleneck_score": 0.2,
                "redundancy_penalty": 0.1,
                "functional_dependency_score": 0.6,
                "database": "string",
            }
        ]
    )
    fake_result = {
        "functional_network": network,
        "manifest": {
            "api_success": True,
            "connectivity_success": True,
            "retrieval_success": True,
            "mapping_success": True,
            "usable_evidence": True,
            "affects_score": True,
            "source_used": "api_real",
            "retrieval_status": "connected_structured_payload",
            "edge_count": 3,
            "usable_edge_count": 3,
            "usable_mapping_count": 1,
            "degraded_mapping_count": 0,
            "fallback_used": False,
            "fallback_reason": "",
        },
    }

    with patch("src.nodos_funcionales.online_only_validation.fetch_string_functional_network", return_value=fake_result):
        with patch("src.nodos_funcionales.online_only_validation.urlopen_json", side_effect=URLError("offline")):
            result = enrich_online_only_downstream_layers(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                seed_result={"api_attempted": True, "api_success": True, "retrieved_record_count": 2, "matched_candidate_count": 2},
                mode="online_optional",
            )

    assert (workspace / "data_external" / "functional_network.csv").exists()
    assert result["string"]["api_attempted"] is True
    assert result["string"]["api_success"] is True
    assert result["string"]["evidence_level"] == "computational_online_interaction"
    assert result["string"]["experimental_validation_supported"] is False


def test_disabled_online_providers_are_explicitly_unresolved_without_network(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    pd.DataFrame(columns=["protein_id", "gene", "candidate_seed_accession"]).to_csv(
        workspace / "data_external" / "essentiality.csv", index=False
    )

    with patch("src.nodos_funcionales.online_only_validation.fetch_string_functional_network") as string_mock:
        with patch("src.nodos_funcionales.online_only_validation.urlopen_json") as http_mock:
            result = enrich_online_only_downstream_layers(
                workspace=workspace,
                organism_name="Escherichia coli",
                taxon_id="562",
                config=config,
                seed_result={"api_attempted": False, "api_success": False},
                mode="online_optional",
                enable_string=False,
                enable_interpro=False,
                enable_literature=False,
            )

    string_mock.assert_not_called()
    http_mock.assert_not_called()
    for provider in ("string", "interpro", "literature"):
        assert result[provider]["retrieval_status"] == "provider_disabled"
        assert result[provider]["api_success"] is False
        assert result[provider]["evidence_level"] == "unresolved"


def test_online_only_enrichment_interpro_empty_records_are_unresolved_success(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    pd.DataFrame(
        [{"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"}]
    ).to_csv(workspace / "data_external" / "essentiality.csv", index=False)
    (workspace / "results" / "online_only_uniprot_seed_records.json").write_text('{"results":[]}', encoding="utf-8")

    with patch("src.nodos_funcionales.online_only_validation.fetch_string_functional_network", side_effect=ValueError("mapping failed")):
        with patch("src.nodos_funcionales.online_only_validation.urlopen_json", return_value={"results": []}):
            result = enrich_online_only_downstream_layers(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                seed_result={"api_attempted": True, "api_success": True, "retrieved_record_count": 1, "matched_candidate_count": 1},
                mode="online_optional",
            )

    assert result["interpro"]["api_attempted"] is True
    assert result["interpro"]["api_success"] is True
    assert result["interpro"]["matched_candidate_count"] == 0
    assert result["interpro"]["fallback_reason"] == "api_success_no_domain_records"
    assert result["interpro"]["evidence_level"] == "unresolved"


def test_online_only_enrichment_literature_metadata_is_not_experimental(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    pd.DataFrame(
        [{"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"}]
    ).to_csv(workspace / "data_external" / "essentiality.csv", index=False)
    (workspace / "results" / "online_only_uniprot_seed_records.json").write_text('{"results":[]}', encoding="utf-8")
    payloads = [
        {"results": [{"metadata": {"accession": "IPR000001"}}]},
        {"resultList": {"result": [{"title": "seedA in Pseudomonas aeruginosa", "pmid": "1", "pubYear": "2024"}]}},
    ]

    with patch("src.nodos_funcionales.online_only_validation.fetch_string_functional_network", side_effect=ValueError("mapping failed")):
        with patch("src.nodos_funcionales.online_only_validation.urlopen_json", side_effect=payloads):
            result = enrich_online_only_downstream_layers(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                seed_result={"api_attempted": True, "api_success": True, "retrieved_record_count": 1, "matched_candidate_count": 1},
                mode="online_optional",
            )

    literature = pd.read_csv(workspace / "data_external" / "literature_support.csv")
    assert result["literature"]["api_attempted"] is True
    assert result["literature"]["api_success"] is True
    assert result["literature"]["evidence_level"] == "literature_metadata_only"
    assert result["literature"]["experimental_validation_supported"] is False
    assert literature.loc[0, "evidence_type"] == "literature_metadata_only"


def test_online_only_enrichment_reuses_uniprot_seed_for_localization(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    pd.DataFrame(
        [{"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"}]
    ).to_csv(workspace / "data_external" / "essentiality.csv", index=False)
    seed_payload = {
        "results": [
            {
                "primaryAccession": "P12345",
                "uniProtkbId": "SEEDA_PSEAE",
                "genes": [{"geneName": {"value": "seedA"}}],
                "comments": [
                    {
                        "commentType": "SUBCELLULAR LOCATION",
                        "subcellularLocations": [{"location": {"value": "Cell membrane"}}],
                    }
                ],
            }
        ]
    }
    (workspace / "results" / "online_only_uniprot_seed_records.json").write_text(json.dumps(seed_payload), encoding="utf-8")

    with patch("src.nodos_funcionales.online_only_validation.fetch_string_functional_network", side_effect=ValueError("mapping failed")):
        with patch("src.nodos_funcionales.online_only_validation.urlopen_json", return_value={"results": []}):
            result = enrich_online_only_downstream_layers(
                workspace=workspace,
                organism_name="Pseudomonas aeruginosa",
                taxon_id="287",
                config=config,
                seed_result={"api_attempted": True, "api_success": True, "retrieved_record_count": 1, "matched_candidate_count": 1},
                mode="online_optional",
            )

    localization = pd.read_csv(workspace / "data_external" / "localization.csv")
    assert result["uniprot_downstream"]["inherited_from_candidate_seed"] is True
    assert result["uniprot_downstream"]["api_success"] is True
    assert localization.loc[0, "localization"] == "inner_membrane"
    assert bool(localization.loc[0, "experimental_validation_supported"]) is False


def test_online_only_enrichment_materializes_candidate_fasta_for_diamond(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    config = load_config(workspace / "config" / "params.yaml")
    config["online_sources"]["human_homology_diamond"]["execution_mode"] = "execute"
    pd.DataFrame(
        [
            {"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"},
            {"protein_id": "Q12345", "gene": "seedB", "candidate_seed_accession": "Q12345"},
        ]
    ).to_csv(workspace / "data_external" / "essentiality.csv", index=False)
    seed_payload = {
        "results": [
            {"primaryAccession": "P12345", "uniProtkbId": "SEEDA_BACT", "genes": [{"geneName": {"value": "seedA"}}]},
            {"primaryAccession": "Q12345", "uniProtkbId": "SEEDB_BACT", "genes": [{"geneName": {"value": "seedB"}}]},
        ]
    }
    (workspace / "results" / "online_only_uniprot_seed_records.json").write_text(json.dumps(seed_payload), encoding="utf-8")

    fasta_text = (
        ">sp|P12345|SEEDA_BACT Protein A OS=Bacterium GN=seedA\nMAAA\n"
        ">tr|Q12345|SEEDB_BACT Protein B OS=Bacterium GN=seedB\nMBBB\n"
    )

    class FakeFastaResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return fasta_text.encode("utf-8")

    with patch("src.nodos_funcionales.online_only_validation.fetch_string_functional_network", side_effect=ValueError("mapping failed")):
        with patch("src.nodos_funcionales.online_only_validation.urlopen_json", return_value={"results": []}):
            with patch("src.nodos_funcionales.human_homology_diamond.urlopen", return_value=FakeFastaResponse()):
                result = enrich_online_only_downstream_layers(
                    workspace=workspace,
                    organism_name="Pseudomonas aeruginosa",
                    taxon_id="287",
                    config=config,
                    seed_result={"api_attempted": True, "api_success": True, "retrieved_record_count": 2, "matched_candidate_count": 2},
                    mode="online_optional",
                )

    fasta_path = workspace / "data_external" / "candidate_proteins.faa"
    manifest = json.loads((workspace / "results" / "human_homology_candidate_fasta_manifest.json").read_text(encoding="utf-8"))
    assert fasta_path.exists()
    assert result["human_homology_candidate_fasta"]["retrieval_status"] == "candidate_fasta_materialized"
    assert manifest["provider_name"] == "human_homology_diamond"
    assert manifest["candidate_sequence_count"] == 2
    assert manifest["missing_sequence_count"] == 0


def test_review_package_sanitizes_overstrong_ranking_labels(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    run_dir = tmp_path / "run"
    (workspace / "results" / "ranking_nodos.csv").write_text(
        "\n".join(
            [
                "protein_id,gene,therapeutic_priority_score,evidence_confidence_score,confidence_evidence_tier,provenance_status,retrieval_mode,data_realism_flag,clinical_impact_evidence_reference",
                "PA0001,seedA,0.7,0.2,experimental,external_real_stable,real_external_online,demo_only,not_experimental",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "results" / "ranking_nodos_phase3.csv").write_text(
        (workspace / "results" / "ranking_nodos.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (workspace / "results" / "layer_resolution_manifest.json").write_text("{}", encoding="utf-8")
    seed_manifest = {
        "source_used": "api_real",
        "api_attempted": True,
        "api_success": True,
        "candidate_count": 1,
        "retrieved_record_count": 1,
        "matched_candidate_count": 1,
        "data_realism_flag": "computed_online",
        "evidence_level": "computational_online_annotation",
        "generated_at_utc": "2026-06-12T00:00:00+00:00",
    }

    package = build_online_only_review_package(
        run_dir=run_dir,
        workspace=workspace,
        organism="Escherichia coli",
        seed_result=seed_manifest,
        pipeline_status="completed",
        pipeline_error="",
        pipeline_result={},
        online_source_mode="online_optional",
        organism_slug="escherichia_coli",
        taxon_id="562",
        strain="K-12",
        strain_slug="k_12",
    )

    ranking = pd.read_csv(package["ranking_nodos.csv"])
    assert ranking.loc[0, "confidence_evidence_tier"] == "partial_online_computational"
    assert ranking.loc[0, "confidence_source_class"] == "partial_online_computational"
    assert ranking.loc[0, "provenance_status"] == "partial_external_online"
    assert ranking.loc[0, "retrieval_mode"] == "online_optional_partial"
    assert ranking.loc[0, "data_realism_flag"] == "computed_online"
    assert ranking.loc[0, "evidence_level"] == "computational_online_annotation"
    assert bool(ranking.loc[0, "experimental_validation_supported"]) is False
    assert ranking.loc[0, "clinical_impact_evidence_reference"] == "not_experimental"
    review = Path(package["ONLINE_ONLY_REVIEW.md"]).read_text(encoding="utf-8")
    assert review.startswith("# Escherichia coli Online-Only Validation Review")
    assert "Organism slug: `escherichia_coli`" in review
    assert "Taxon id: `562`" in review
    assert "Strain: `K-12`" in review


def test_provider_audit_separates_string_http_success_from_usable_mapping(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "results" / "string_functional_network_manifest.json").write_text(
        json.dumps({
            "provider": "string_db", "api_attempted": True, "api_success": True,
            "connectivity_success": True, "edge_count": 4, "protein_count_mapped": 0,
            "evidence_level": "computational_online_interaction", "source_used": "api_real",
        }),
        encoding="utf-8",
    )

    row = build_online_only_provider_audit(workspace, {}).set_index("layer_key").loc["functional_network"]
    assert bool(row["connectivity_success"]) is True
    assert bool(row["retrieval_success"]) is True
    assert bool(row["mapping_success"]) is False
    assert bool(row["usable_evidence"]) is False
    assert bool(row["affects_score"]) is False
    assert row["retrieval_status"] == "degraded_no_usable_mapping"


def test_candidate_seed_and_inherited_essentiality_are_not_essentiality_evidence(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    seed = {
        "api_attempted": True, "api_success": True, "retrieved_record_count": 2,
        "matched_candidate_count": 2, "evidence_level": "computational_online_annotation",
        "source_used": "api_real",
    }
    (workspace / "results" / "online_only_essentiality_manifest.json").write_text(
        json.dumps({**seed, "inherited_from_candidate_seed": True, "provider_name": "uniprot_rest_candidate_seed"}),
        encoding="utf-8",
    )

    audit = build_online_only_provider_audit(workspace, seed).set_index("layer_key")
    assert bool(audit.loc["candidate_seed", "usable_evidence"]) is False
    assert bool(audit.loc["essentiality", "usable_evidence"]) is False


def test_online_only_sanitizer_preserves_phase3_real_counts_when_raw_columns_are_not_exported(
    tmp_path: Path,
) -> None:
    from src.nodos_funcionales.online_only_validation import (
        _sanitize_online_only_ranking,
    )

    ranking_path = tmp_path / "ranking_nodos.csv"
    pd.DataFrame(
        [
            {
                "protein_id": "P12345",
                "real_evidence_layer_count": 3,
                "phase3_real_evidence_layer_count": 3,
                "proxy_layer_count": 2,
                "missing_layer_count": 4,
                "negative_evidence_layer_count": 0,
                "evidence_mixture_label": "real_plus_proxy",
            }
        ]
    ).to_csv(ranking_path, index=False)

    provider_audit = pd.DataFrame(
        [
            {
                "layer_key": "localization",
                "usable_evidence": True,
                "affects_score": True,
            },
            {
                "layer_key": "strain_conservation",
                "usable_evidence": True,
                "affects_score": True,
            },
            {
                "layer_key": "host_annotation",
                "usable_evidence": True,
                "affects_score": True,
            },
        ]
    )

    _sanitize_online_only_ranking(
        ranking_path,
        {
            "api_success": True,
            "source_used": "api_real",
        },
        "online_strict",
        provider_audit,
    )

    result = pd.read_csv(ranking_path).iloc[0]

    assert int(result["real_evidence_layer_count"]) == 3
    assert int(result["phase3_real_evidence_layer_count"]) == 3
    assert result["evidence_mixture_label"] != "demo_proxy_only"
