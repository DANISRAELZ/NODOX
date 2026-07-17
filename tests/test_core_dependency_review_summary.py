from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "core_dependency_review_summary.md"


def test_core_dependency_review_summary_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "core dependencies",
        "optional workflow dependencies",
        "local virtual environment inventory",
        "transitive dependencies",
        "dev/test dependencies",
        "requirements.txt",
        "pyproject.toml",
        "requirements-workflow.txt",
        "docs/dependency_license_inventory.md",
        "snakemake is an optional workflow dependency, not core",
        "snakemake-related unknown metadata does not block the core release by default",
        "optional workflow distribution remains blocked pending separate review",
        "core dependency review must still be completed or explicitly accepted by human approval",
        "core dependency security scan must be completed or explicitly accepted by human approval",
        "not scientific validation",
        "clinical validation",
        "experimental validation",
    ]
    for term in required_terms:
        assert term in text
