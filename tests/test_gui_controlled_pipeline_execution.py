from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "apps" / "user_curated_onboarding_app.py"
FORBIDDEN_PHRASES = [
    "clinically" + " validated",
    "experimentally" + " validated",
    "safe" + " target",
    "confirmed" + " therapeutic target",
    "validated" + " therapeutic target",
]


def _app_text() -> str:
    return APP_PATH.read_text(encoding="utf-8")


def test_controlled_pipeline_gui_text_contract() -> None:
    text = _app_text()
    required_terms = [
        "9. Ejecutar pipeline controlado",
        "Pipeline execution overview",
        "Input selection",
        "Preflight / dry-run",
        "Controlled execution",
        "Logs and run manifest",
        "Previous GUI runs",
        "Selected run summary",
        "Run outputs",
        "Run publication package",
        "Compare against base publication package",
        "Conservative interpretation",
        "results/gui_runs",
        "pipeline_runner",
        "I understand this will run a computational workflow and write outputs to a new isolated directory.",
        "computationally prioritized hypotheses requiring independent validation",
    ]
    for term in required_terms:
        assert term in text


def test_controlled_pipeline_gui_imports_runner_but_not_direct_entrypoints() -> None:
    text = _app_text()
    assert "run_pipeline_controlled" in text
    assert "run_pipeline_preflight" in text
    assert "gui_run_review" in text
    assert "compare_publication_packages" in text
    assert "run_pipeline.py" not in text
    assert "import snakemake" not in text.lower()
    assert "subprocess" not in text
    assert "shell command" in text


def test_controlled_pipeline_gui_has_no_streamlit_global_calls() -> None:
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


def test_controlled_pipeline_gui_language_is_conservative() -> None:
    text = _app_text().lower()
    assert "experimental validation" in text
    assert "clinical validation" in text
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in text
