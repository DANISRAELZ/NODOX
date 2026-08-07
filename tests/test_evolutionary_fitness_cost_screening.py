from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.evolutionary_fitness_cost_screening import (
    audit_screened_fitness_cost_literature,
)


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "results").mkdir(parents=True)
    (workspace / "results" / "organism_profile.json").write_text(
        json.dumps({"organism": "Helicobacter pylori", "taxon_id": 210}),
        encoding="utf-8",
    )
    return workspace


def _screening_dir(workspace: Path) -> Path:
    directory = workspace / "data_curated" / "organisms" / "helicobacter_pylori"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _config(mode: str = "hybrid_curated") -> dict:
    return {
        "online_sources": {"source_mode_effective": mode},
        "curated_real_evidence": {
            "enabled": True,
            "base_dir": "data_curated/organisms",
        },
    }


def _row(*, relative_fitness: str = "", declared_status: str = "screening_only_missing_numeric_relative_fitness") -> dict:
    return {
        "gene": "pbp1",
        "gene_aliases": "pbp1A",
        "taxon_id": "210",
        "mutation": "V374L",
        "candidate_scope": "protein_candidate",
        "antibiotic": "amoxicillin",
        "assay_type": "in_vitro_competition",
        "assay_context": "24-hour liquid competition against wild-type G27",
        "finding_direction": "fitness_defect",
        "reported_metric": "relative fitness",
        "relative_fitness": relative_fitness,
        "measurement_type": "competition_relative_fitness_ratio",
        "screening_status": declared_status,
        "screening_reason": "test fixture",
        "source_type": "literature_curated",
        "source_database": "Helicobacter",
        "source_record": "PMID:32677105",
        "source_version": "2020-10",
        "screened_at": "2026-08-07",
        "mapping_method": "exact gene+mutation+taxon literature curation",
        "mapping_status": "exact_gene_and_taxon",
        "evidence_status": "observed",
        "evidence_confidence": "high",
        "method_scope": "competition assay of isogenic resistance mutant versus wild type",
        "pmid": "32677105",
        "doi": "10.1111/hel.12724",
        "supporting_pmid": "35389254",
        "reference": "Windham and Merrell 2020",
        "notes": "test fixture",
    }


def _write_screening(workspace: Path, rows: list[dict]) -> Path:
    path = _screening_dir(workspace) / "evolutionary_fitness_cost_screened.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_qualitative_fitness_defect_is_not_promoted_to_numeric_evidence(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_screening(workspace, [_row(relative_fitness="")])

    summary = audit_screened_fitness_cost_literature(workspace, _config())

    assert len(summary) == 1
    assert summary.loc[0, "derived_screening_status"] == "screening_only_missing_numeric_relative_fitness"
    assert bool(summary.loc[0, "promotion_candidate"]) is False
    assert bool(summary.loc[0, "stage4e_catalog_match"]) is False

    manifest = json.loads(
        (workspace / "results" / "evolutionary_fitness_cost_literature_screening_manifest.json").read_text()
    )
    assert manifest["scoring_effect"] is False
    assert manifest["quantitative_candidate_count"] == 0
    assert manifest["promoted_record_count"] == 0


def test_quantitative_record_is_only_a_candidate_until_explicitly_added_to_stage4e_catalog(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_screening(
        workspace,
        [_row(relative_fitness="0.82", declared_status="quantitative_candidate_requires_stage4e_catalog")],
    )

    summary = audit_screened_fitness_cost_literature(workspace, _config())

    assert bool(summary.loc[0, "promotion_candidate"]) is True
    assert summary.loc[0, "derived_screening_status"] == "quantitative_candidate_not_promoted"
    assert bool(summary.loc[0, "stage4e_catalog_match"]) is False


def test_matching_production_catalog_is_reported_as_promoted_without_auto_writing_it(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    directory = _screening_dir(workspace)
    _write_screening(
        workspace,
        [_row(relative_fitness="0.82", declared_status="quantitative_candidate_requires_stage4e_catalog")],
    )
    pd.DataFrame(
        [
            {
                "gene": "pbp1",
                "mutation": "V374L",
                "source_record": "PMID:32677105",
                "pmid": "32677105",
                "relative_fitness": "0.82",
            }
        ]
    ).to_csv(directory / "evolutionary_fitness_cost.csv", index=False)

    summary = audit_screened_fitness_cost_literature(workspace, _config())

    assert bool(summary.loc[0, "promotion_candidate"]) is True
    assert bool(summary.loc[0, "stage4e_catalog_match"]) is True
    assert summary.loc[0, "derived_screening_status"] == "promoted_to_stage4e_catalog"


def test_online_strict_disables_local_screening_audit(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_screening(workspace, [_row(relative_fitness="0.82")])

    summary = audit_screened_fitness_cost_literature(workspace, _config("online_strict"))

    assert summary.empty
    manifest = json.loads(
        (workspace / "results" / "evolutionary_fitness_cost_literature_screening_manifest.json").read_text()
    )
    assert manifest["status"] == "disabled"
    assert manifest["reason"] == "disabled_by_online_strict_policy"
    assert manifest["scoring_effect"] is False


def test_declared_status_cannot_turn_missing_numeric_value_into_promotable_evidence(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    _write_screening(
        workspace,
        [_row(relative_fitness="", declared_status="promoted_to_stage4e_catalog")],
    )

    summary = audit_screened_fitness_cost_literature(workspace, _config())

    assert summary.loc[0, "derived_screening_status"] == "screening_only_missing_numeric_relative_fitness"
    assert bool(summary.loc[0, "promotion_candidate"]) is False
    assert bool(summary.loc[0, "declared_status_matches_derived"]) is False


def test_tracked_h_pylori_screening_registry_contains_no_fabricated_numeric_fitness() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path = repo_root / "data_curated" / "organisms" / "helicobacter_pylori" / "evolutionary_fitness_cost_screened.csv"
    table = pd.read_csv(path, dtype=str, keep_default_na=False)

    assert set(table["mutation"]) == {"V374L", "N562Y"}
    assert set(table["pmid"]) == {"32677105"}
    assert set(table["supporting_pmid"]) == {"35389254"}
    assert table["relative_fitness"].eq("").all()
    assert table["screening_status"].eq("screening_only_missing_numeric_relative_fitness").all()
