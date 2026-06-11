from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8").lower()


def test_requirements_keep_snakemake_out_of_core_and_in_workflow_file() -> None:
    requirements = _read("requirements.txt")
    workflow = _read("requirements-workflow.txt")

    assert "snakemake" not in requirements
    assert "snakemake>=7.32.0" in workflow
    assert "optional workflow dependencies" in workflow


def test_pyproject_declares_snakemake_only_as_optional_workflow_dependency() -> None:
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    core_dependencies = data["project"]["dependencies"]
    optional_workflow = data["project"]["optional-dependencies"]["workflow"]

    assert all("snakemake" not in dep.lower() for dep in core_dependencies)
    assert "snakemake>=7.32.0" in optional_workflow


def test_release_docs_describe_optional_workflow_dependency_boundary() -> None:
    readme = _read("README.md")
    license_audit = _read("docs/license_and_dependency_audit.md")
    security_review = _read("docs/dependency_security_review.md")
    final_check = _read("docs/final_publication_release_check.md")
    decision = _read("docs/v0_1_0_publication_release_decision.md")

    combined = "\n".join([readme, license_audit, security_review, final_check, decision])

    assert "snakemake is an optional workflow dependency" in combined
    assert "core install does not require snakemake" in combined
    assert "optional workflow dependencies have separate transitive license/security review requirements" in combined
    assert "unknown snakemake transitive dependency metadata does not block the core release" in combined
    assert "public workflow distribution remains blocked until optional workflow dependency review is completed" in combined
    assert "does not claim dependency review is complete" not in combined
    assert "clinical validation" in combined
    assert "experimental validation" in combined
