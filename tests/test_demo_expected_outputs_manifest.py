from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "demo_expected_outputs_manifest.md"


def test_demo_expected_outputs_manifest_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "ranking_nodos.csv",
        "report_phase2.md",
        "candidate_explanations_simple",
        "candidate_audit",
        "evidence_strength_audit",
        "layer_resolution_summary",
        "publication_package/",
        "run_manifest.json",
        "pipeline_stdout.log",
        "pipeline_stderr.log",
        "workflow validation and reproducibility",
        "not experimental validation",
        "do not establish clinical utility",
        "candidate ranking requires downstream validation",
    ]
    for term in required_terms:
        assert term in text
