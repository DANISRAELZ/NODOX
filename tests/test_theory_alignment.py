from __future__ import annotations

import re

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.integration import integrate_tables
from src.nodos_funcionales.normalization import normalize_all
from src.nodos_funcionales.reporting import export_results
from src.nodos_funcionales.scoring import build_features_and_scores, compute_sensitivity
from src.nodos_funcionales.validation import load_and_validate_all
from tests.helpers import PROJECT_ROOT, make_temp_project


def _run_offline_phase2_workspace():
    project_dir = make_temp_project()
    config = load_config(project_dir / "config" / "params.yaml")
    load_and_validate_all(project_dir, config)
    normalize_all(project_dir, config)
    integrate_tables(project_dir)
    features, scored = build_features_and_scores(project_dir, config)
    sensitivity = compute_sensitivity(features, config)
    sensitivity.to_csv(project_dir / "results" / "sensitivity_analysis.csv", index=False)
    export_results(project_dir, config)
    return project_dir, features, scored


def test_theory_scores_and_aliases_are_exported_offline() -> None:
    _, features, scored = _run_offline_phase2_workspace()

    required_columns = {
        "candidate_id",
        "functional_node_score",
        "antibiotic_target_score",
        "antivirulence_target_score",
        "selectivity_score",
        "evolutionary_robustness_score",
        "clinical_context_score",
        "confidence_modifier",
        "meta_priority_score",
        "therapeutic_priority_score",
        "therapeutic_priority_contribution_summary",
        "therapeutic_priority_meta_priority_score_contribution",
        "therapeutic_priority_host_safety_score_contribution",
        "therapeutic_priority_host_damage_score_contribution",
        "therapeutic_priority_infection_site_access_score_contribution",
        "therapeutic_priority_infection_context_score_contribution",
        "functional_node_types",
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "mutation_tolerance",
        "pathway_redundancy",
        "paralog_count",
        "mobile_context",
        "hgt_context",
        "recombination_context",
        "resistance_association",
        "evidence_level",
        "evidence_source",
        "provenance_status",
        "retrieval_mode",
        "cache_status",
        "interpretation_warning",
    }
    assert required_columns.issubset(features.columns)
    assert required_columns.issubset(scored.columns)
    for column in [
        "selectivity_score",
        "evolutionary_robustness_score",
        "clinical_context_score",
        "confidence_modifier",
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "mutation_tolerance",
        "pathway_redundancy",
    ]:
        assert scored[column].between(0, 1).all(), column


def test_functional_node_typology_detects_integrative_candidates() -> None:
    _, features, _ = _run_offline_phase2_workspace()

    assert features["functional_node_types"].fillna("").str.len().gt(0).all()
    flattened = ";".join(features["functional_node_types"].astype(str))
    assert "essential_node" in flattened
    assert "functional_connectivity_node" in flattened
    assert "integrative_multilevel_node" in flattened


def test_reports_include_interpretation_limits_and_provenance() -> None:
    project_dir, _, _ = _run_offline_phase2_workspace()

    ranking = pd.read_csv(project_dir / "results" / "ranking_nodos.csv")
    explanations = pd.read_csv(project_dir / "results" / "candidate_explanations_simple.csv")
    report_text = (project_dir / "results" / "report_phase2.md").read_text(encoding="utf-8")
    explanation_text = (project_dir / "results" / "candidate_explanations_simple.md").read_text(encoding="utf-8")

    for column in [
        "functional_node_types",
        "therapeutic_priority_contribution_summary",
        "therapeutic_priority_components",
        "confidence_modifier",
        "provenance_status",
        "retrieval_mode",
        "cache_status",
        "interpretation_warning",
    ]:
        assert column in ranking.columns
    for column in [
        "functional_node_types",
        "therapeutic_priority_components",
        "theory_context",
        "provenance_context",
        "evolutionary_risk",
        "interpretation_warning",
    ]:
        assert column in explanations.columns

    warning_patterns = [
        "score alto no equivale a validacion experimental",
        "ausencia de evidencia no equivale a evidencia negativa",
        "Bajo riesgo evolutivo no significa ausencia de resistencia",
        "hipotesis terapeuticas priorizadas",
        "therapeutic_priority_components",
        "interpretacion computacional",
    ]
    combined = f"{report_text}\n{explanation_text}"
    for pattern in warning_patterns:
        assert re.search(pattern, combined, flags=re.IGNORECASE), pattern


def test_theory_documentation_is_not_organism_locked() -> None:
    docs = [
        PROJECT_ROOT / "docs" / "multi_organism_design.md",
        PROJECT_ROOT / "docs" / "README_theory_first.md",
        PROJECT_ROOT / "docs" / "theory_to_software_mapping.md",
    ]
    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "multi" in text.lower() or "cualquier organismo" in text.lower()
        assert "Pseudomonas aeruginosa PAO1" not in text or "demo" in text.lower()
