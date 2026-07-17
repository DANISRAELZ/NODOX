from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "final_public_release_audit.md"


def test_final_public_release_audit_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "apache license 2.0 present",
        "core release no longer requires snakemake",
        "optional workflow dependency",
        "separate review required before public workflow distribution",
        "core dependency license review status",
        "core dependency security review status",
        "sensitive data/secrets scan status",
        "internal prompts/logs scan status",
        "generated results/data directory review status",
        "ai-use transparency",
        "no clinical validation",
        "no experimental validation",
        "no claims that therapeutic targets are validated",
        "final tag remains blocked until human approval",
    ]
    for term in required_terms:
        assert term in text
