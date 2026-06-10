from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.nodos_funcionales.publication_gui_readers import (
    PUBLICATION_FIGURES,
    PUBLICATION_TABLES,
    build_candidate_index,
    check_publication_package_exists,
    get_candidate_details,
    get_conservative_gui_warning,
    list_publication_figures,
    list_publication_tables,
    load_publication_table,
    load_publication_manifest,
    summarize_publication_package,
)


def test_publication_gui_readers_summarize_existing_package(tmp_path: Path) -> None:
    package_dir = tmp_path / "publication_package"
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True)
    for table_name in PUBLICATION_TABLES:
        pd.DataFrame([{"gene": "a", "protein_id": "P1"}]).to_csv(package_dir / table_name, index=False)
    for figure_name in PUBLICATION_FIGURES:
        (figures_dir / figure_name).write_bytes(b"not-a-real-png-for-reader-test")

    summary = summarize_publication_package(package_dir)

    assert check_publication_package_exists(package_dir)
    assert summary["exists"] is True
    assert summary["tables_found"] == 6
    assert summary["figures_found"] == 6
    assert [item["table"] for item in summary["tables"]] == PUBLICATION_TABLES
    assert [item["figure"] for item in summary["figures"]] == PUBLICATION_FIGURES
    assert [item["table"] for item in list_publication_tables(package_dir)] == PUBLICATION_TABLES


def test_load_publication_table_reports_missing_without_exception(tmp_path: Path) -> None:
    table, error = load_publication_table(tmp_path / "missing.csv")

    assert table.empty
    assert error is not None
    assert "Missing publication table" in error


def test_list_publication_figures_marks_missing_files(tmp_path: Path) -> None:
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    (figures_dir / PUBLICATION_FIGURES[0]).write_bytes(b"placeholder")

    figures = list_publication_figures(figures_dir)

    assert figures[0]["exists"] is True
    assert all(item["exists"] is False for item in figures[1:])


def test_publication_manifest_missing_is_reported(tmp_path: Path) -> None:
    manifest, error = load_publication_manifest(tmp_path / "publication_package")

    assert manifest == {}
    assert error is not None
    assert "Missing publication manifest" in error


def test_candidate_index_and_details_work_with_minimal_tables(tmp_path: Path) -> None:
    package_dir = tmp_path / "publication_package"
    package_dir.mkdir()
    pd.DataFrame(
        [
            {
                "final_priority_rank": 1,
                "gene": "geneA",
                "protein_id": "P1",
                "product": "enzyme",
                "organism": "Example bacterium",
                "therapeutic_role": "bactericidal_candidate",
                "meta_priority_score": 0.8,
                "therapeutic_priority_score": 0.7,
                "evidence_confidence_score": 0.4,
                "functional_node_score": 0.6,
                "functional_node_theory_score": 0.5,
                "evolutionary_escape_risk_score": 0.2,
                "evolutionary_escape_penalty_applied": 0.03,
                "interpretation_warning": "prioritized hypothesis",
                "top_positive_drivers": "functional_node_score=0.6",
                "top_negative_drivers": "evidence_confidence_score=0.4",
                "missing_evidence_flags": "not_assessed",
                "provenance_status": "demo_only",
            }
        ]
    ).to_csv(package_dir / "publication_table_1_top_candidates.csv", index=False)
    pd.DataFrame([{"protein_id": "P1", "rank_delta_vs_base": -2}]).to_csv(
        package_dir / "publication_table_4_sensitivity_stability.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "protein_id": "P1",
                "baseline_name": "baseline_rank_by_functional_node_score",
                "baseline_rank": 3,
                "rank_delta": 2,
            }
        ]
    ).to_csv(package_dir / "publication_table_6_baseline_comparison.csv", index=False)

    index = build_candidate_index(package_dir)
    details = get_candidate_details(package_dir, "P1")

    assert index[0]["candidate_id"] == "P1"
    assert "geneA" in index[0]["label"]
    assert details["scores"]["therapeutic_priority_score"] == 0.7
    assert details["scores"]["evidence_confidence_score"] == 0.4
    assert details["scores"]["evolutionary_escape_risk_score"] == 0.2
    assert details["interpretation"]["ranking_stability_label"] == "moderate_shift_review"
    assert "baseline_rank_by_functional_node_score" in details["interpretation"]["baseline_comparison_summary"]
    assert get_conservative_gui_warning() in details["interpretation"]["fixed_warning"]
