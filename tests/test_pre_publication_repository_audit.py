from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "pre_publication_repository_audit.md"


def test_pre_publication_repository_audit_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "license",
        "dependencies",
        "dependency license compatibility",
        "security and vulnerability considerations",
        "third-party code",
        "prompts",
        "logs",
        "sensitive data",
        "credentials",
        "api keys",
        "tokens",
        "passwords",
        "results/",
        "data_sessions",
        "data_processed",
        "ai-use transparency",
        "no clinical validation",
        "no experimental validation",
        "no therapeutic-target validation",
        "scoring is prioritization only",
        "team of collaborators",
        "final human approval is given",
        "final public tag `v0.1.0` remains blocked until",
        "do not create the final public release tag before those checks are complete",
    ]
    for term in required_terms:
        assert term in text
