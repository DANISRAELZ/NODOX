from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "manuscript_figure_table_specifications.md"


def test_manuscript_figure_table_specifications_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "figure 1: functional nodes conceptual framework",
        "theory-first prioritization",
        "evidence layers",
        "functional constraints",
        "conservative interpretation",
        "figure 2: user_curated workflow",
        "curator-provided inputs",
        "quality gate",
        "expert review",
        "scoring readiness",
        "figure 3: gui-assisted execution and run-review workflow",
        "controlled execution",
        "isolated run directory",
        "logs",
        "outputs",
        "publication package",
        "review comparison",
        "figure 4 or supplementary figure: isolated publication package structure",
        "results/gui_runs/<run_id>/",
        "publication_package/",
        "review/",
        "table 1: model variables and interpretation boundaries",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "table 2: evidence/provenance classes",
        "user_curated",
        "demo evidence",
        "proxy evidence",
        "cache-derived evidence",
        "online evidence",
        "table 3: validation and testing boundaries",
        "workflow validation",
        "software validation",
        "biological validation",
        "clinical validation",
        "experimental validation",
        "table 4: demo output artifacts and interpretation",
        "ranking_nodos.csv",
        "report_phase2.md",
        "candidate_audit.csv",
        "publication_package/",
        "not themselves biological validation or experimental validation",
    ]
    for term in required_terms:
        assert term in text
