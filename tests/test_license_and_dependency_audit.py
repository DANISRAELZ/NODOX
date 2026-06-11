from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "license_and_dependency_audit.md"


def test_license_and_dependency_audit_optional_workflow_boundary() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "core install does not require snakemake",
        "snakemake is separated as an optional workflow dependency",
        "requirements-workflow.txt",
        ".[workflow]",
        "optional workflow dependencies have separate transitive license/security review requirements",
        "unknown snakemake transitive dependency metadata does not block the core release",
        "public workflow distribution remains blocked until reviewed",
        "current local virtual environment",
        "may include optional workflow/transitive packages",
        "not treat the inventory as the minimal core dependency list",
        "not biological validation",
        "clinical validation",
        "experimental validation",
    ]
    for term in required_terms:
        assert term in text
