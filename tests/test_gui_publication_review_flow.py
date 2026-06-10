from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "apps" / "user_curated_onboarding_app.py"
GUIDE_PATH = PROJECT_ROOT / "docs" / "gui_publication_review_guide.md"
FORBIDDEN_PHRASES = [
    "clinically" + " validated",
    "experimentally" + " validated",
    "safe" + " target",
    "confirmed" + " therapeutic target",
    "validated" + " therapeutic target",
]


def _app_text() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_gui_publication_review_text_contract() -> None:
    text = _app_text()
    required_terms = [
        "8. Revisar resultados publicables",
        "Publication package overview",
        "Tables",
        "Figures",
        "Candidate explorer",
        "Conservative interpretation",
        "publication_results_manifest.json",
        "README_publication_package.md",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "evolutionary_escape_risk_score",
        "computationally prioritized hypotheses",
        "requiring independent validation",
        "demo_only, preliminary, proxy, missing, not_assessed or insufficient_evidence",
        "figure_1_top_candidates_meta_priority.png",
        "figure_2_priority_vs_confidence.png",
        "figure_3_score_decomposition.png",
        "figure_4_evolutionary_risk_vs_priority.png",
        "figure_5_ranking_stability.png",
        "figure_6_therapeutic_role_distribution.png",
    ]
    for term in required_terms:
        assert term in text


def test_gui_publication_review_has_no_streamlit_global_calls() -> None:
    tree = ast.parse(_app_text())
    function_depth = 0
    global_calls: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            nonlocal function_depth
            function_depth += 1
            self.generic_visit(node)
            function_depth -= 1

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            if function_depth == 0 and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "st":
                    global_calls.append(node.func.attr)
            self.generic_visit(node)

    Visitor().visit(tree)
    assert global_calls == []


def test_gui_publication_review_is_read_only_contract() -> None:
    text = _app_text()
    assert "run_pipeline.py" not in text
    assert "subprocess" not in text
    assert "import snakemake" not in text.lower()
    assert "no ejecuta scoring" in text
    assert "no ejecuta pipeline" in text
    assert "no modifica `results/`, `data_processed/` ni `data_sessions/`" in text
    assert ".to_csv(" not in text
    assert ".write_text(" not in text
    assert "create_staging" in text  # Existing onboarding behavior remains available.


def test_gui_publication_review_guide_exists_and_is_conservative() -> None:
    assert GUIDE_PATH.exists()
    text = GUIDE_PATH.read_text(encoding="utf-8").lower()
    assert "streamlit is optional" in text
    assert "candidate explorer" in text
    assert "publication_package" in text
    assert "therapeutic_priority_score" in text
    assert "evidence_confidence_score" in text
    assert "evolutionary_escape_risk_score" in text
    assert "computationally prioritized hypotheses requiring independent validation" in text
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in text
