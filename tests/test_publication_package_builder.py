from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.publication_package_builder import build_publication_package


def _write_minimal_results(results_dir: Path) -> None:
    results_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "protein_id": "P1",
                "gene": "a",
                "antibiotic_target_score": 0.8,
                "antivirulence_target_score": 0.3,
                "functional_node_score": 0.7,
                "selectivity_score": 0.9,
                "clinical_context_score": 0.5,
                "therapeutic_priority_score": 0.62,
                "evidence_confidence_score": 0.8,
                "evolutionary_escape_risk_score": 0.1,
                "therapeutic_role": "bactericidal_candidate",
                "provenance_status": "demo_only",
            },
            {
                "protein_id": "P2",
                "gene": "b",
                "antibiotic_target_score": 0.3,
                "antivirulence_target_score": 0.8,
                "functional_node_score": 0.6,
                "selectivity_score": 0.8,
                "clinical_context_score": 0.4,
                "therapeutic_priority_score": 0.52,
                "evidence_confidence_score": 0.2,
                "evolutionary_escape_risk_score": 0.7,
                "therapeutic_role": "antivirulence_candidate",
                "provenance_status": "missing",
            },
        ]
    ).to_csv(results_dir / "ranking_nodos.csv", index=False)
    pd.DataFrame(
        [{"score_name": "meta_priority", "scenario": "baseline", "protein_id": "P1", "rank": 1, "rank_delta_vs_base": 0}]
    ).to_csv(results_dir / "sensitivity_analysis.csv", index=False)


def test_publication_package_builder_preserves_phase1_and_adds_baseline(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    output_dir = results_dir / "publication_package"
    _write_minimal_results(results_dir)

    manifest = build_publication_package(results_dir, output_dir)

    assert (output_dir / "publication_table_1_top_candidates.csv").exists()
    assert (output_dir / "publication_table_6_baseline_comparison.csv").exists()
    assert (output_dir / "publication_baseline_comparison.md").exists()
    assert (output_dir / "figures").exists()
    assert (output_dir / "figures" / "figure_1_top_candidates_meta_priority.png").exists()
    assert (output_dir / "figures" / "figure_2_priority_vs_confidence.png").exists()
    assert (output_dir / "figures" / "figure_3_score_decomposition.png").exists()
    assert (output_dir / "figures" / "figure_4_evolutionary_risk_vs_priority.png").exists()
    assert (output_dir / "figures" / "figure_5_ranking_stability.png").exists()
    assert (output_dir / "figures" / "figure_6_therapeutic_role_distribution.png").exists()
    assert (output_dir / "figures" / "publication_figures_interpretation.md").exists()
    assert (output_dir / "publication_results_manifest.json").exists()
    readme = (output_dir / "README_publication_package.md").read_text(encoding="utf-8")
    assert "figures/" in readme
    saved_manifest = json.loads((output_dir / "publication_results_manifest.json").read_text(encoding="utf-8"))
    assert saved_manifest["baseline_rows"] == 6
    assert saved_manifest["figures"]["generated_count"] == 6
    assert "publication_internal_validation.md" in manifest["files"] or (output_dir / "publication_internal_validation.md").exists()


def test_publication_figures_use_conservative_interpretation(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    output_dir = results_dir / "publication_package"
    _write_minimal_results(results_dir)
    build_publication_package(results_dir, output_dir)

    interpretation = (output_dir / "figures" / "publication_figures_interpretation.md").read_text(encoding="utf-8").lower()
    assert "computational demonstration" in interpretation
    assert "therapeutic_priority_score" in interpretation
    assert "evidence_confidence_score" in interpretation
    for phrase in [
        "clinically validated",
        "experimentally validated",
        "safe target",
        "confirmed therapeutic target",
        "validated therapeutic target",
    ]:
        assert phrase not in interpretation
