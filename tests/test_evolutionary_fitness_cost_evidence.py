from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.curated_real_evidence import apply_curated_real_evidence
from src.nodos_funcionales.evolutionary_escape_risk import (
    compute_evolutionary_escape_risk_features,
)
from src.nodos_funcionales.evolutionary_fitness_cost_evidence import (
    AMRFINDER_SHARED_INDEPENDENCE_GROUP,
    apply_curated_fitness_cost_evidence,
)


def _write_profile(workspace: Path) -> None:
    results = workspace / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "organism_profile.json").write_text(
        json.dumps(
            {
                "organism_input_name": "Helicobacter pylori",
                "organism_canonical_name": "Helicobacter pylori",
                "organism": "Helicobacter pylori",
                "strain_canonical": None,
                "taxon_id": "210",
            }
        ),
        encoding="utf-8",
    )


def _config(workspace: Path, mode: str = "hybrid_curated") -> dict:
    return {
        "online_sources": {"source_mode_effective": mode},
        "curated_real_evidence": {
            "enabled": True,
            "base_dir": str(workspace / "data_curated" / "organisms"),
            "minimum_confidence": 0.5,
            "precedence": {
                "replace_unresolved": True,
                "preserve_online_real": True,
            },
        },
        "evolutionary_fitness_cost_curated": {
            "enabled": True,
            "base_dir": str(workspace / "data_curated" / "organisms"),
            "filename": "evolutionary_fitness_cost.csv",
        },
    }


def _candidate(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "protein_id": "HP_GYRA",
        "protein_id_canonical": "HP_GYRA",
        "candidate_id": "HP_GYRA",
        "gene": "gyrA",
        "taxon_id": "210",
        "meta_priority_score": 0.80,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def _valid_record(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "gene": "gyrA",
        "taxon_id": "210",
        "mutation": "N87K",
        "escape_association": "target_site_resistance_mutation",
        "relative_fitness": 0.82,
        "measurement_type": "relative_fitness_ratio",
        "assay_context": "in vitro competition against isogenic wild type",
        "source_type": "literature_curated",
        "source_database": "PubMed",
        "source_record": "PMID:12345678:gyrA_N87K_fitness",
        "source_version": "publication_snapshot_v1",
        "retrieved_at": "2026-08-07T18:00:00+00:00",
        "mapping_method": "manual_gene_taxon_curation",
        "mapping_status": "exact_gene_and_taxon",
        "evidence_status": "observed",
        "evidence_confidence": "high",
        "method_scope": "relative fitness of resistant mutant versus isogenic WT",
        "pmid": "12345678",
        "doi": "10.1000/example.fitness",
        "reference": "experimental fitness study",
    }
    row.update(overrides)
    return row


def _write_catalog(workspace: Path, rows: list[dict[str, object]]) -> Path:
    root = workspace / "data_curated" / "organisms" / "helicobacter_pylori"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "evolutionary_fitness_cost.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _add_explicit_record(
    frame: pd.DataFrame,
    variable: str,
    value: float,
    *,
    group: str,
    source_type: str = "literature_curated",
    source_record: str | None = None,
) -> None:
    frame[variable] = value
    frame[f"{variable}_is_explicit"] = True
    frame[f"{variable}_source_type"] = source_type
    frame[f"{variable}_source_database"] = "stage4e_test_source"
    frame[f"{variable}_source_record"] = source_record or f"record:{variable}"
    frame[f"{variable}_source_version"] = "v1"
    frame[f"{variable}_retrieved_at"] = "2026-08-07T18:00:00+00:00"
    frame[f"{variable}_mapping_method"] = "manual_gene_taxon_curation"
    frame[f"{variable}_mapping_status"] = "exact_gene_and_taxon"
    frame[f"{variable}_evidence_status"] = "observed"
    frame[f"{variable}_evidence_confidence"] = "high"
    frame[f"{variable}_independence_group"] = group
    frame[f"{variable}_method_scope"] = "Stage 4E regression evidence"
    frame[f"{variable}_taxon_id"] = "210"
    frame[f"{variable}_notes"] = "Stage 4E regression evidence"


def test_valid_relative_fitness_materializes_explicit_fitness_cost(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record()])

    result = apply_curated_fitness_cost_evidence(tmp_path, _candidate(), _config(tmp_path))

    assert bool(result.loc[0, "fitness_cost_curated_evidence_eligible"])
    assert abs(float(result.loc[0, "fitness_cost_of_escape"]) - 0.18) < 1e-12
    assert bool(result.loc[0, "fitness_cost_of_escape_is_explicit"])
    assert result.loc[0, "fitness_cost_of_escape_mapping_status"] == "exact_gene_and_taxon"
    assert result.loc[0, "fitness_cost_of_escape_evidence_status"] == "observed"
    assert result.loc[0, "fitness_cost_of_escape_source_record"].startswith("PMID:12345678")
    assert result.loc[0, "fitness_cost_curated_selected_mutation"] == "N87K"


def test_curated_real_evidence_pipeline_loads_fitness_even_without_other_curated_layers(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record(relative_fitness=0.75)])

    result = apply_curated_real_evidence(tmp_path, _candidate(), _config(tmp_path))

    assert abs(float(result.loc[0, "fitness_cost_of_escape"]) - 0.25) < 1e-12
    assert bool(result.loc[0, "fitness_cost_of_escape_is_explicit"])
    assert (tmp_path / "results" / "evolutionary_fitness_cost_manifest.json").exists()
    assert (tmp_path / "results" / "curated_real_evidence_manifest.json").exists()


def test_multiple_escape_routes_use_minimum_observed_cost(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(
        tmp_path,
        [
            _valid_record(mutation="N87K", relative_fitness=0.70, source_record="PMID:11111111:N87K", pmid="11111111"),
            _valid_record(mutation="D91N", relative_fitness=0.95, source_record="PMID:22222222:D91N", pmid="22222222"),
        ],
    )

    result = apply_curated_fitness_cost_evidence(tmp_path, _candidate(), _config(tmp_path))

    assert abs(float(result.loc[0, "fitness_cost_of_escape"]) - 0.05) < 1e-12
    assert result.loc[0, "fitness_cost_curated_selected_mutation"] == "D91N"
    assert int(result.loc[0, "fitness_cost_curated_valid_record_count"]) == 2


def test_measured_no_cost_can_be_explicit_zero_but_missing_evidence_never_becomes_zero(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record(relative_fitness=1.05)])

    measured = apply_curated_fitness_cost_evidence(tmp_path, _candidate(), _config(tmp_path))
    assert float(measured.loc[0, "fitness_cost_of_escape"]) == 0.0
    assert bool(measured.loc[0, "fitness_cost_of_escape_is_explicit"])

    other_workspace = tmp_path / "missing"
    _write_profile(other_workspace)
    original = _candidate()
    missing = apply_curated_fitness_cost_evidence(
        other_workspace,
        original,
        _config(other_workspace),
    )
    pd.testing.assert_frame_equal(missing, original)
    manifest = json.loads(
        (other_workspace / "results" / "evolutionary_fitness_cost_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["reason"] == "catalog_not_found"


def test_wrong_taxon_unsupported_measurement_and_missing_reference_fail_closed(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(
        tmp_path,
        [
            _valid_record(taxon_id="287", source_record="PMID:11111111:wrong_taxon", pmid="11111111"),
            _valid_record(measurement_type="growth_rate_difference", source_record="PMID:22222222:wrong_measure", pmid="22222222"),
            _valid_record(source_record="record_without_reference", pmid="", doi="", reference=""),
        ],
    )

    result = apply_curated_fitness_cost_evidence(tmp_path, _candidate(), _config(tmp_path))

    assert not bool(result.loc[0, "fitness_cost_curated_evidence_eligible"])
    assert "fitness_cost_of_escape" not in result.columns
    assert int(result.loc[0, "fitness_cost_curated_rejected_record_count"]) == 3
    reason = str(result.loc[0, "fitness_cost_curated_evidence_reason"])
    assert "taxon_mismatch" in reason
    assert "unsupported_measurement_type" in reason
    assert "missing_literature_identifier" in reason


def test_online_strict_never_loads_local_fitness_cost(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record()])
    original = _candidate()

    result = apply_curated_fitness_cost_evidence(
        tmp_path,
        original,
        _config(tmp_path, mode="online_strict"),
    )

    pd.testing.assert_frame_equal(result, original)
    manifest = json.loads(
        (tmp_path / "results" / "evolutionary_fitness_cost_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["enabled"] is False
    assert manifest["reason"] == "disabled_by_online_strict_policy"


def test_existing_canonical_fitness_cost_evidence_is_preserved(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record(relative_fitness=0.90)])
    candidate = _candidate()
    _add_explicit_record(
        candidate,
        "fitness_cost_of_escape",
        0.40,
        group="existing_experimental_study",
        source_type="experimental",
    )

    result = apply_curated_fitness_cost_evidence(tmp_path, candidate, _config(tmp_path))

    assert abs(float(result.loc[0, "fitness_cost_of_escape"]) - 0.40) < 1e-12
    assert result.loc[0, "fitness_cost_of_escape_independence_group"] == "existing_experimental_study"
    assert result.loc[0, "fitness_cost_curated_evidence_reason"] == (
        "eligible_but_existing_canonical_fitness_cost_evidence_preserved"
    )


def test_shared_amrfinder_pubmed_uses_same_independence_group(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record(pmid="12345678")])
    candidate = _candidate(amrfinder_pubmed_references="99999999;12345678")

    result = apply_curated_fitness_cost_evidence(tmp_path, candidate, _config(tmp_path))

    assert result.loc[0, "fitness_cost_of_escape_independence_group"] == AMRFINDER_SHARED_INDEPENDENCE_GROUP
    assert result.loc[0, "fitness_cost_curated_independence_reason"] == (
        "shared_pubmed_with_amrfinderplus_same_independence_group"
    )


def test_bvbrc_amrfinder_and_fitness_cost_reach_contract_with_two_independent_groups(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record(pmid="12345678", relative_fitness=0.80)])
    candidate = _candidate(amrfinder_pubmed_references="12345678")

    _add_explicit_record(
        candidate,
        "evolutionary_constraint_score",
        0.85,
        group="bvbrc_strain_conservation_taxon_210",
        source_type="computed_from_real_data",
    )
    _add_explicit_record(
        candidate,
        "resistance_emergence_risk",
        1.0,
        group=AMRFINDER_SHARED_INDEPENDENCE_GROUP,
        source_type="literature_curated",
        source_record="AMRFinderPlus:PMID:12345678",
    )

    enriched = apply_curated_fitness_cost_evidence(tmp_path, candidate, _config(tmp_path))
    scored = compute_evolutionary_escape_risk_features(enriched, {})

    assert int(scored.loc[0, "evolutionary_escape_risk_explicit_variable_count"]) == 3
    assert int(scored.loc[0, "evolutionary_escape_risk_independent_evidence_group_count"]) == 2
    assert bool(scored.loc[0, "evolutionary_evidence_contract_supported"])
    assert pd.notna(scored.loc[0, "evolutionary_escape_supported_score"])
    assert "fitness_cost_of_escape" in str(scored.loc[0, "evolutionary_escape_risk_explicit_variables"])


def test_pandas_na_explicit_flag_does_not_crash_or_block_curated_fitness(tmp_path: Path) -> None:
    _write_profile(tmp_path)
    _write_catalog(tmp_path, [_valid_record()])
    candidate = _candidate(fitness_cost_of_escape_is_explicit=pd.NA)

    result = apply_curated_fitness_cost_evidence(tmp_path, candidate, _config(tmp_path))

    assert bool(result.loc[0, "fitness_cost_of_escape_is_explicit"])
    assert abs(float(result.loc[0, "fitness_cost_of_escape"]) - 0.18) < 1e-12
