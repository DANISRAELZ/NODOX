from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8").lower()


def test_final_public_release_gate_files_and_dependency_boundary() -> None:
    required_files = [
        "LICENSE",
        "README.md",
        "CITATION.cff",
        "CHANGELOG.md",
        "docs/release_notes_v0_1_0_publication.md",
        "docs/final_public_release_audit.md",
        "docs/sensitive_data_and_secret_scan.md",
        "docs/core_dependency_review_summary.md",
        "docs/public_release_file_inclusion_review.md",
    ]
    for path in required_files:
        assert (PROJECT_ROOT / path).exists()

    assert "snakemake" not in _read("requirements.txt")
    assert "snakemake>=7.32.0" in _read("requirements-workflow.txt")


def test_final_public_release_gate_keeps_human_approval_and_no_validation_overclaim() -> None:
    combined = "\n".join(
        [
            _read("README.md"),
            _read("docs/final_publication_release_check.md"),
            _read("docs/v0_1_0_publication_release_decision.md"),
            _read("docs/final_public_release_audit.md"),
        ]
    )
    assert "human approval" in combined
    assert "do not create" in combined
    assert "no clinical validation" in combined
    assert "no experimental validation" in combined
    assert "clinically validated" not in combined
    assert "experimentally validated" not in combined
    assert "validated therapeutic target" not in combined
