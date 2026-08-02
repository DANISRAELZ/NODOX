from __future__ import annotations

import gzip
import shutil
from io import StringIO
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.human_homology_diamond import (
    build_human_homologs_with_diamond,
    config_from_mapping,
    classify_hit,
    count_fasta_records,
    diamond_is_available,
    materialize_candidate_fasta,
    parse_diamond_tsv,
    normalize_coverage_value,
    normalize_diamond_coverage_columns,
    parse_fasta_records,
    validate_fasta_has_sequences,
    _split_query_id,
)
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.layer_resolver import resolve_layer_inputs
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.online_sources import fetch_layer_external_source
from src.nodos_funcionales.reporting import export_results
from src.nodos_funcionales.scoring import build_features_and_scores
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT


pytestmark = pytest.mark.unit


SYNTHETIC_FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "human_homology_synthetic"


def test_repository_defaults_keep_diamond_disabled_and_unbound(tmp_path: Path) -> None:
    configured = load_config(PROJECT_ROOT / "config" / "params.yaml")["online_sources"]["human_homology_diamond"]
    assert configured["enabled"] is False
    assert configured["execution_mode"] == "cache_only"
    assert configured["allow_download"] is False
    assert configured["allow_execution"] is False
    assert configured["reference_fasta_path"] == ""
    assert configured["database_prefix"] == ""

    defaults = config_from_mapping({})
    assert defaults.enabled is False
    assert defaults.execution_mode == "cache_only"
    assert defaults.allow_download is False
    assert defaults.allow_execution is False
    assert defaults.reference_fasta_path == ""
    assert defaults.database_prefix == ""

    with patch("src.nodos_funcionales.human_homology_diamond.subprocess.run") as run_mock:
        df, manifest = build_human_homologs_with_diamond(tmp_path, {})
    run_mock.assert_not_called()
    assert df.empty
    assert manifest["status"] == "diamond_provider_disabled"
    assert manifest["diamond_version"] == "not_checked_provider_disabled"


def test_gzip_fasta_is_validated_counted_and_parsed_by_content(tmp_path: Path) -> None:
    fasta = tmp_path / "reference_without_required_extension.data"
    with gzip.open(fasta, "wt", encoding="utf-8") as handle:
        handle.write(">sp|P12345|SEEDA_HUMAN GN=GENEA\nMAAA\n")

    validate_fasta_has_sequences(fasta)
    assert count_fasta_records(fasta) == 1
    records = parse_fasta_records(fasta)
    assert set(records) == {"P12345"}
    assert records["P12345"]["gene"] == "GENEA"


class FastaFakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def __enter__(self) -> "FastaFakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.text.encode("utf-8")


def _make_workspace(name: str) -> Path:
    root = PROJECT_ROOT / ".tmp_tests" / f"{name}_{uuid.uuid4().hex[:8]}"
    for dirname in ["config", "data_raw", "data_external", "data_processed", "results"]:
        (root / dirname).mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "config" / "params.yaml", root / "config" / "params.yaml")
    return root


def _write_minimal_core_layers(workspace: Path) -> None:
    (workspace / "data_raw" / "essentiality.csv").write_text(
        "\n".join(
            [
                "protein_id,gene,essential,evidence,database",
                "P80200,cagA,0,curated,fixture",
                "A0AAC8SAV3,gyrA,1,curated,fixture",
                "A0AAC8MZX9,gyrB,1,curated,fixture",
                "Q933P5,ureA,1,curated,fixture",
                "Q9S0Q5,ureB,1,curated,fixture",
                "Q48245,vacA,0,curated,fixture",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "data_raw" / "virulence.csv").write_text(
        "\n".join(
            [
                "protein_id,gene,virulence_score,virulence_factor,database",
                "P80200,cagA,1.0,1,fixture",
                "A0AAC8SAV3,gyrA,0.2,0,fixture",
                "A0AAC8MZX9,gyrB,0.2,0,fixture",
                "Q933P5,ureA,0.4,0,fixture",
                "Q9S0Q5,ureB,0.4,0,fixture",
                "Q48245,vacA,1.0,1,fixture",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / "data_raw" / "localization.csv").write_text(
        "\n".join(
            [
                "protein_id,gene,localization,database",
                "P80200,cagA,extracellular,fixture",
                "A0AAC8SAV3,gyrA,cytoplasm,fixture",
                "A0AAC8MZX9,gyrB,cytoplasm,fixture",
                "Q933P5,ureA,cytoplasm,fixture",
                "Q9S0Q5,ureB,cytoplasm,fixture",
                "Q48245,vacA,extracellular,fixture",
            ]
        ),
        encoding="utf-8",
    )


def test_parse_diamond_tsv_includes_no_hits_and_classifies_synthetic_fixture() -> None:
    parsed = parse_diamond_tsv(
        SYNTHETIC_FIXTURE_DIR / "synthetic_diamond_results.tsv",
        SYNTHETIC_FIXTURE_DIR / "synthetic_hpylori_candidates.faa",
        config_from_mapping({}),
    )
    by_gene = parsed.set_index("gene")
    assert by_gene.loc["cagA", "homology_evidence_tier"] == "no_detectable_human_similarity"
    assert by_gene.loc["ureA", "homology_evidence_tier"] == "no_detectable_human_similarity"
    assert by_gene.loc["ureB", "homology_evidence_tier"] == "no_detectable_human_similarity"
    assert by_gene.loc["vacA", "homology_evidence_tier"] == "no_detectable_human_similarity"
    assert by_gene.loc["gyrA", "homology_evidence_tier"] == "partial_human_sequence_similarity"
    assert by_gene.loc["gyrB", "homology_evidence_tier"] == "strong_human_sequence_homology"
    assert int(by_gene.loc["gyrA", "human_homolog"]) == 1
    assert int(by_gene.loc["gyrB", "human_homolog"]) == 1
    assert int(by_gene.loc["cagA", "human_homolog"]) == 0
    assert by_gene.loc["cagA", "human_uniprot_accession"] != "P05109"
    assert "S100A8" not in str(by_gene.loc["cagA"].to_dict())
    assert float(by_gene.loc["gyrA", "query_coverage"]) == pytest.approx((210 - 36 + 1) / 827)
    assert float(by_gene.loc["gyrB", "subject_coverage"]) == pytest.approx((556 - 9 + 1) / 1039)
    assert float(by_gene.loc["gyrA", "percent_identity"]) == pytest.approx(30.2)


def test_coverage_normalization_is_idempotent_and_keeps_percent_identity() -> None:
    frame = pd.DataFrame(
        [
            {
                "query_coverage": 75,
                "subject_coverage": 0.75,
                "orthology_query_coverage": 75,
                "orthology_subject_coverage": 0.75,
                "percent_identity": 30.2,
                "homology_missing_flags": "",
                "homology_evidence_note": "DIAMOND test",
            },
            {
                "query_coverage": -1,
                "subject_coverage": 101,
                "orthology_query_coverage": pd.NA,
                "orthology_subject_coverage": pd.NA,
                "percent_identity": 30.2,
                "homology_missing_flags": "",
                "homology_evidence_note": "DIAMOND invalid test",
            },
        ]
    )
    once = normalize_diamond_coverage_columns(frame)
    cached = normalize_diamond_coverage_columns(pd.read_csv(StringIO(once.to_csv(index=False))))
    assert normalize_coverage_value(75) == pytest.approx(0.75)
    assert normalize_coverage_value(0.75) == pytest.approx(0.75)
    assert once.loc[0, "query_coverage"] == pytest.approx(0.75)
    assert once.loc[0, "subject_coverage"] == pytest.approx(0.75)
    assert cached.loc[0, "query_coverage"] == pytest.approx(0.75)
    assert cached.loc[0, "orthology_query_coverage"] == pytest.approx(0.75)
    assert cached.loc[0, "percent_identity"] == pytest.approx(30.2)
    assert pd.isna(once.loc[1, "query_coverage"])
    assert pd.isna(once.loc[1, "subject_coverage"])
    assert "invalid_query_coverage" in once.loc[1, "homology_missing_flags"]


def test_classification_thresholds_use_normalized_coverage() -> None:
    cfg = config_from_mapping({})
    strong = pd.Series({"sseqid": "human", "evalue": 1e-20, "pident": 30.2, "query_coverage": 0.75, "subject_coverage": 0.75})
    partial = pd.Series({"sseqid": "human", "evalue": 1e-8, "pident": 22.0, "query_coverage": 0.30, "subject_coverage": 0.10})
    weak = pd.Series({"sseqid": "human", "evalue": 1e-3, "pident": 18.0, "query_coverage": 0.10, "subject_coverage": 0.10})
    no_hit = pd.Series({"sseqid": "", "evalue": pd.NA, "pident": pd.NA, "query_coverage": pd.NA, "subject_coverage": pd.NA})
    assert classify_hit(strong, cfg) == "strong_human_sequence_homology"
    assert classify_hit(partial, cfg) == "partial_human_sequence_similarity"
    assert classify_hit(weak, cfg) == "weak_low_coverage_similarity"
    assert classify_hit(no_hit, cfg) == "no_detectable_human_similarity"


def test_empty_fasta_is_rejected(tmp_path: Path) -> None:
    fasta = tmp_path / "empty.faa"
    fasta.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="FASTA sin secuencias"):
        validate_fasta_has_sequences(fasta)


def test_parse_fasta_records_supports_sp_tr_and_plain_pipe_headers(tmp_path: Path) -> None:
    fasta = tmp_path / "headers.faa"
    fasta.write_text(
        "\n".join(
            [
                ">sp|P12345|SEEDA_HUMAN Protein A OS=Homo sapiens GN=GENEA",
                "MAAA",
                ">tr|Q12345|SEEDB_HUMAN Protein B OS=Homo sapiens",
                "MBBB",
                ">P80200|cagA",
                "MCCC",
            ]
        ),
        encoding="utf-8",
    )
    records = parse_fasta_records(fasta)
    assert set(records) == {"P12345", "Q12345", "P80200"}
    assert records["P12345"]["gene"] == "GENEA"
    assert records["Q12345"]["gene"] == "SEEDB"
    assert records["P80200"]["gene"] == "cagA"
    assert _split_query_id("sp|P12345|SEEDA_HUMAN")[0] == "P12345"
    assert _split_query_id("tr|Q12345|SEEDB_HUMAN")[0] == "Q12345"
    assert _split_query_id("P80200|cagA") == ("P80200", "cagA")


def test_materialize_candidate_fasta_batches_uniprot_sequences(tmp_path: Path) -> None:
    workspace = _make_workspace("diamond_fasta_materialize")
    try:
        candidates = pd.DataFrame(
            [
                {"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"},
                {"protein_id": "Q12345", "gene": "seedB", "candidate_seed_accession": "Q12345"},
                {"protein_id": "MISSING1", "gene": "missing", "candidate_seed_accession": "MISSING1"},
            ]
        )
        cfg = {"execution_mode": "execute", "sequence_batch_size": 2}
        fasta_payloads = [
            ">sp|P12345|SEEDA_BACT Protein A OS=Bacterium GN=seedA\nMAAA\n",
            ">tr|Q12345|SEEDB_BACT Protein B OS=Bacterium GN=seedB\nMBBB\n",
        ]
        with patch("src.nodos_funcionales.human_homology_diamond.urlopen") as urlopen_mock:
            urlopen_mock.side_effect = [FastaFakeResponse(fasta_payloads[0]), FastaFakeResponse(fasta_payloads[1])]
            manifest = materialize_candidate_fasta(workspace, cfg, candidates=candidates, mode="online_optional")
        fasta_path = workspace / "data_external" / "candidate_proteins.faa"
        assert fasta_path.exists()
        assert manifest["provider_name"] == "human_homology_diamond"
        assert manifest["candidate_sequence_count"] == 2
        assert manifest["missing_sequence_count"] == 1
        assert manifest["missing_accessions"] == ["MISSING1"]
        records = parse_fasta_records(fasta_path)
        assert set(records) == {"P12345", "Q12345"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_online_optional_allows_retrieval_even_when_diamond_is_cache_only() -> None:
    workspace = _make_workspace("diamond_online_optional_cache_only")
    try:
        candidates = pd.DataFrame([{"protein_id": "P12345", "candidate_seed_accession": "P12345"}])
        with patch(
            "src.nodos_funcionales.human_homology_diamond.urlopen",
            return_value=FastaFakeResponse(">sp|P12345|SEEDA_BACT\nMAAA\n"),
        ) as urlopen_mock:
            manifest = materialize_candidate_fasta(
                workspace, {"execution_mode": "cache_only"}, candidates=candidates, mode="online_optional"
            )
        urlopen_mock.assert_called_once()
        assert manifest["download_allowed"] is True
        assert manifest["download_attempted"] is True
        assert manifest["download_successful"] is True
        assert manifest["retrieved_sequence_count"] == 1
        assert manifest["candidate_sequence_count"] == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_two_hundred_seed_sequences_materialize_without_download() -> None:
    workspace = _make_workspace("diamond_200_seed_sequences")
    try:
        candidates = pd.DataFrame(
            [{"protein_id": f"P{idx:05d}", "candidate_seed_accession": f"P{idx:05d}"} for idx in range(200)]
        )
        seed_records = {
            "results": [
                {
                    "primaryAccession": f"P{idx:05d}",
                    "uniProtkbId": f"GENE{idx}_BACT",
                    "sequence": {"value": "MAAA"},
                }
                for idx in range(200)
            ]
        }
        with patch("src.nodos_funcionales.human_homology_diamond.urlopen") as urlopen_mock:
            manifest = materialize_candidate_fasta(
                workspace,
                {"execution_mode": "cache_only"},
                candidates=candidates,
                mode="online_optional",
                seed_records=seed_records,
            )
        urlopen_mock.assert_not_called()
        assert manifest["seed_sequence_count"] == 200
        assert manifest["download_attempted"] is False
        assert manifest["candidate_sequence_count"] == 200
        assert manifest["missing_sequence_count"] == 0
        assert (workspace / "data_external" / "candidate_proteins.faa").stat().st_size > 0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_materialize_candidate_fasta_reuses_existing_in_cache_only() -> None:
    workspace = _make_workspace("diamond_fasta_cache_only")
    try:
        fasta_path = workspace / "data_external" / "candidate_proteins.faa"
        fasta_path.write_text(">sp|P12345|SEEDA_BACT GN=seedA\nMAAA\n", encoding="utf-8")
        candidates = pd.DataFrame([{"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"}])
        with patch("src.nodos_funcionales.human_homology_diamond.urlopen") as urlopen_mock:
            manifest = materialize_candidate_fasta(workspace, {"execution_mode": "cache_only"}, candidates=candidates, mode="offline_only")
        urlopen_mock.assert_not_called()
        assert manifest["retrieval_status"] == "existing_fasta_reused"
        assert manifest["candidate_sequence_count"] == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_materialize_candidate_fasta_degrades_without_network_or_existing_fasta() -> None:
    workspace = _make_workspace("diamond_fasta_missing")
    try:
        candidates = pd.DataFrame([{"protein_id": "P12345", "gene": "seedA", "candidate_seed_accession": "P12345"}])
        manifest = materialize_candidate_fasta(workspace, {"execution_mode": "cache_only"}, candidates=candidates, mode="offline_only")
        assert manifest["retrieval_status"] == "candidate_fasta_unavailable_offline_or_cache_only"
        assert manifest["candidate_sequence_count"] == 0
        assert manifest["missing_sequence_count"] == 1
        assert manifest["download_allowed"] is False
        assert manifest["download_attempted"] is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_diamond_unavailable_returns_false() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError("diamond")):
        assert diamond_is_available("diamond") is False


def test_provider_reuses_cached_tsv_and_materializes_human_homologs() -> None:
    workspace = _make_workspace("diamond_cached")
    try:
        shutil.copytree(SYNTHETIC_FIXTURE_DIR, workspace / "data_external" / "human_homology_synthetic")
        _write_minimal_core_layers(workspace)
        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["human_homology_diamond"]["enabled"] = True
        config["online_sources"]["human_homology_diamond"]["candidate_fasta_path"] = (
            "data_external/human_homology_synthetic/synthetic_hpylori_candidates.faa"
        )
        config["online_sources"]["human_homology_diamond"]["cached_tsv_path"] = (
            "data_external/human_homology_synthetic/synthetic_diamond_results.tsv"
        )
        with patch("subprocess.run") as run_mock:
            run_mock.return_value.stdout = "diamond version 2.1.9"
            run_mock.return_value.stderr = ""
            run_mock.return_value.returncode = 0
            result = fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="human_homology_diamond",
            )
        called_subcommands = [call.args[0][1] for call in run_mock.call_args_list if len(call.args[0]) > 1]
        assert "makedb" not in called_subcommands
        assert "blastp" not in called_subcommands
        assert result["source_name"] == "diamond_human_sequence_alignment"
        assert result["status"] == "diamond_cached_tsv_materialized"
        df = pd.read_csv(result["path"])
        assert set(df["homology_evidence_tier"]) >= {
            "strong_human_sequence_homology",
            "partial_human_sequence_similarity",
            "no_detectable_human_similarity",
        }
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_diamond_executes_from_clean_workspace_with_materialized_fasta() -> None:
    workspace = _make_workspace("diamond_clean_execute")
    try:
        fasta_path = workspace / "data_external" / "candidate_proteins.faa"
        fasta_path.write_text(">sp|P12345|SEEDA_BACT GN=seedA\nMAAA\n", encoding="utf-8")
        tsv_path = workspace / "data_external" / "human_homology_diamond.tsv"
        config = load_config(workspace / "config" / "params.yaml")
        cfg = config["online_sources"]["human_homology_diamond"]
        cfg["enabled"] = True
        cfg["allow_execution"] = True
        cfg["execution_mode"] = "execute"
        cfg["reuse_cache"] = False
        cfg["reference_fasta_path"] = str(SYNTHETIC_FIXTURE_DIR / "synthetic_human_reference_fixture.faa")
        cfg["database_prefix"] = str(workspace / "data_external" / "human_reference_test")

        def fake_run(command: list[str], **_kwargs: object):
            class Result:
                stdout = "diamond version 2.1.9"
                stderr = ""
                returncode = 0

            if len(command) > 1 and command[1] == "makedb":
                (workspace / "data_external" / "human_reference_test.dmnd").write_text("db", encoding="utf-8")
            if len(command) > 1 and command[1] == "blastp":
                tsv_path.write_text(
                    "sp|P12345|SEEDA_BACT\tsp|Q02880|TOP2B_HUMAN\t30.0\t100\t120\t150\t1\t100\t1\t100\t1e-20\t80\n",
                    encoding="utf-8",
                )
            return Result()

        with patch("subprocess.run", side_effect=fake_run):
            df, manifest = build_human_homologs_with_diamond(workspace, cfg)
        assert manifest["provider_name"] == "human_homology_diamond"
        assert manifest["execution_status"] == "executed"
        assert manifest["execution_started"] is True
        assert manifest["execution_completed"] is True
        assert manifest["execution_failed"] is False
        assert manifest["provider_mode"] == "local_executable"
        assert manifest["provider_attempted"] is True
        assert manifest["provider_success"] is True
        assert manifest["result_row_count"] == 1
        assert manifest["hit_count"] == 1
        assert manifest["no_hit_count"] == 0
        assert manifest["matched_candidate_count"] == 1
        assert manifest["affects_score"] is True
        assert manifest["query_fasta_path"] == str(fasta_path)
        assert manifest["candidate_sequence_count"] == 1
        assert manifest["reference_fasta_path"] == str(SYNTHETIC_FIXTURE_DIR / "synthetic_human_reference_fixture.faa")
        assert df.loc[0, "protein_id"] == "P12345"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_diamond_missing_executable_is_explicit_not_completed() -> None:
    workspace = _make_workspace("diamond_missing_executable_explicit")
    try:
        (workspace / "data_external" / "candidate_proteins.faa").write_text(">P12345|seedA\nMAAA\n", encoding="utf-8")
        cfg = {
            "enabled": True,
            "allow_execution": True,
            "execution_mode": "execute",
            "diamond_executable": "definitely-missing-diamond",
        }
        df, manifest = build_human_homologs_with_diamond(workspace, cfg)
        assert df.empty
        assert manifest["status"] == "diamond_executable_unavailable"
        assert manifest["execution_status"] == "executable_unavailable"
        assert manifest["execution_completed"] is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_diamond_missing_database_inputs_records_failed_execution() -> None:
    workspace = _make_workspace("diamond_missing_database_explicit")
    try:
        (workspace / "data_external" / "candidate_proteins.faa").write_text(">P12345|seedA\nMAAA\n", encoding="utf-8")
        cfg = {
            "enabled": True,
            "allow_execution": True,
            "execution_mode": "execute",
            "reference_fasta_path": str(workspace / "missing-human.faa"),
            "database_prefix": str(workspace / "missing-human-db"),
            "allow_download": False,
        }
        with patch("src.nodos_funcionales.human_homology_diamond.diamond_is_available", return_value=True):
            df, manifest = build_human_homologs_with_diamond(workspace, cfg)
        assert df.empty
        assert manifest["status"] == "diamond_execution_failed"
        assert manifest["execution_status"] == "failed"
        assert manifest["execution_started"] is True
        assert manifest["execution_failed"] is True
        assert manifest["execution_completed"] is False
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_relative_reference_paths_resolve_from_project_root() -> None:
    workspace = _make_workspace("diamond_relative_paths")
    try:
        fasta_path = workspace / "data_external" / "candidate_proteins.faa"
        fasta_path.write_text(">sp|P12345|SEEDA_BACT GN=seedA\nMAAA\n", encoding="utf-8")
        cfg = {
            "enabled": True,
            "execution_mode": "cache_only",
            "reference_fasta_path": "data_external/human_reference_proteome_UP000005640.faa",
            "database_prefix": "data_external/human_reference_UP000005640",
        }
        df, manifest = build_human_homologs_with_diamond(workspace, cfg)
        assert df.empty
        assert manifest["query_fasta_path"] == str(fasta_path)
        assert ".." not in config_from_mapping(cfg).reference_fasta_path
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_qseqid_normalization_matches_sp_tr_queries(tmp_path: Path) -> None:
    fasta = tmp_path / "queries.faa"
    fasta.write_text(">sp|P12345|SEEDA_BACT GN=seedA\nMAAA\n>tr|Q12345|SEEDB_BACT GN=seedB\nMBBB\n", encoding="utf-8")
    tsv = tmp_path / "hits.tsv"
    tsv.write_text(
        "\n".join(
            [
                "sp|P12345|SEEDA_BACT\tsp|Q02880|TOP2B_HUMAN\t30.0\t100\t120\t150\t1\t100\t1\t100\t1e-20\t80",
                "tr|Q12345|SEEDB_BACT\tsp|P11388|TOP2A_HUMAN\t30.0\t100\t120\t150\t1\t100\t1\t100\t1e-20\t80",
            ]
        ),
        encoding="utf-8",
    )
    df = parse_diamond_tsv(tsv, fasta, config_from_mapping({}))
    assert set(df["protein_id"]) == {"P12345", "Q12345"}
    assert set(df["human_uniprot_accession"]) == {"Q02880", "P11388"}


def test_two_hundred_sp_tr_queries_do_not_collapse(tmp_path: Path) -> None:
    fasta = tmp_path / "queries_200.faa"
    lines = []
    for idx in range(200):
        prefix = "sp" if idx % 2 == 0 else "tr"
        accession = f"P{idx:05d}"
        lines.extend([f">{prefix}|{accession}|GENE{idx}_BACT GN=gene{idx}", "MAAA"])
    fasta.write_text("\n".join(lines) + "\n", encoding="utf-8")
    empty_tsv = tmp_path / "empty.tsv"
    empty_tsv.write_text("", encoding="utf-8")
    df = parse_diamond_tsv(empty_tsv, fasta, config_from_mapping({}))
    assert len(df) == 200
    assert df["protein_id"].nunique() == 200
    assert "sp" not in set(df["protein_id"])
    assert "tr" not in set(df["protein_id"])
    assert len(df) == 200
    assert df["homology_lookup_status"].eq("diamond_no_hit").all()
    assert df["homology_evidence_tier"].eq("no_detectable_human_similarity").all()
    assert df["source_database"].eq("computed_diamond_human_homology_v1").all()
    assert not df["source_database"].eq("provider_not_found").any()


def test_resolver_prefers_user_data_over_diamond_cache() -> None:
    workspace = _make_workspace("diamond_user_priority")
    try:
        shutil.copytree(SYNTHETIC_FIXTURE_DIR, workspace / "data_external" / "human_homology_synthetic")
        _write_minimal_core_layers(workspace)
        (workspace / "data_user").mkdir(exist_ok=True)
        (workspace / "data_user" / "human_homologs.csv").write_text(
            "protein_id,gene,human_homolog,evalue,human_gene,database\nP80200,cagA,0,,none,user_curated\n",
            encoding="utf-8",
        )
        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["human_homology_diamond"]["enabled"] = True
        config["online_sources"]["human_homology_diamond"]["candidate_fasta_path"] = (
            "data_external/human_homology_synthetic/synthetic_hpylori_candidates.faa"
        )
        config["online_sources"]["human_homology_diamond"]["cached_tsv_path"] = (
            "data_external/human_homology_synthetic/synthetic_diamond_results.tsv"
        )
        manifest = resolve_layer_inputs(workspace, config)
        assert manifest["human_homologs"]["resolved_from"] == "user"
        raw = pd.read_csv(workspace / "data_raw" / "human_homologs.csv")
        assert raw.loc[0, "protein_id"] == "P80200"
        assert int(raw.loc[0, "human_homolog"]) == 0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_name_match_unverified_does_not_set_human_homolog() -> None:
    workspace = _make_workspace("name_match_unverified")
    try:
        _write_minimal_core_layers(workspace)
        config = load_config(workspace / "config" / "params.yaml")
        with patch("src.nodos_funcionales.online_sources._query_uniprot_human_gene") as query_mock:
            def fake_query(gene: str, _cfg: dict) -> tuple[dict | None, list[str]]:
                if gene == "cagA":
                    return {
                        "primaryAccession": "P05109",
                        "uniProtkbId": "S100A8_HUMAN",
                        "genes": [{"geneName": {"value": "S100A8"}}],
                    }, []
                return None, []

            query_mock.side_effect = fake_query
            result = fetch_layer_external_source(
                layer_key="human_homologs",
                workspace=workspace,
                filename="human_homologs.csv",
                config=config,
                provider_name="uniprot_human_gene_lookup",
            )
        df = pd.read_csv(result["path"])
        caga = df.loc[df["gene"] == "cagA"].iloc[0]
        assert pd.isna(caga["human_homolog"])
        assert caga["homology_evidence_tier"] != "strong_human_sequence_homology"
        assert caga["homology_evidence_tier"] != "partial_human_sequence_similarity"
        assert caga["human_uniprot_accession"] != "P05109"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_diamond_output_survives_normalization_integration_and_scoring() -> None:
    workspace = _make_workspace("diamond_pipeline_compat")
    try:
        shutil.copytree(SYNTHETIC_FIXTURE_DIR, workspace / "data_external" / "human_homology_synthetic")
        _write_minimal_core_layers(workspace)
        config = load_config(workspace / "config" / "params.yaml")
        config["online_sources"]["human_homology_diamond"]["enabled"] = True
        config["online_sources"]["human_homology_diamond"]["candidate_fasta_path"] = (
            "data_external/human_homology_synthetic/synthetic_hpylori_candidates.faa"
        )
        config["online_sources"]["human_homology_diamond"]["cached_tsv_path"] = (
            "data_external/human_homology_synthetic/synthetic_diamond_results.tsv"
        )
        load_and_validate_all(workspace, config)
        normalize_all(workspace, config)
        integrate_tables(workspace)
        features, scored = build_features_and_scores(workspace, config)
        export_results(workspace, config, mode="compare")
        assert (workspace / "data_processed" / "validated_human_homologs.csv").exists()
        assert (workspace / "data_processed" / "normalized_human_homologs.csv").exists()
        assert (workspace / "results" / "ranking_nodos_by_gene.csv").exists()
        normalized_homologs = pd.read_csv(workspace / "data_processed" / "normalized_human_homologs.csv")
        for coverage_column in [
            "query_coverage",
            "subject_coverage",
            "orthology_query_coverage",
            "orthology_subject_coverage",
        ]:
            values = pd.to_numeric(normalized_homologs[coverage_column], errors="coerce").dropna()
            assert values.between(0.0, 1.0).all()
        assert "percent_identity" in features.columns
        assert "orthology_query_coverage" in features.columns
        assert "human_homology_audit_summary" in scored.columns
        ranking_by_gene = pd.read_csv(workspace / "results" / "ranking_nodos_by_gene.csv")
        assert "percent_identity" in ranking_by_gene.columns
        assert "orthology_query_coverage" in ranking_by_gene.columns
        assert "homology_evidence_tier" in ranking_by_gene.columns
        assert features["source_database"].astype(str).str.contains("computed_diamond_human_homology_v1", regex=False).all()
        assert not features["source_database"].astype(str).str.contains("provider_not_found", regex=False).any()
        assert {
            "strong_human_sequence_homology",
            "partial_human_sequence_similarity",
            "no_detectable_human_similarity",
        }.issubset(set(features["homology_evidence_tier"]))
        assert not ranking_by_gene["homology_lookup_status"].eq("unresolved_online_provider_not_available").any()
        assert {
            "strong_human_sequence_homology",
            "partial_human_sequence_similarity",
            "no_detectable_human_similarity",
        }.issubset(set(ranking_by_gene["homology_evidence_tier"]))
        caga = features.loc[features["gene"] == "cagA"].iloc[0]
        assert caga["homology_evidence_tier"] == "no_detectable_human_similarity"
        assert "S100A8" not in str(caga.to_dict())
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
