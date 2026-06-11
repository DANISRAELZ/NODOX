from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "public_release_exclusion_policy.md"


def test_public_release_exclusion_policy_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        ".env",
        "credentials",
        "api keys",
        "tokens",
        "passwords",
        "private config files",
        "local machine paths",
        "personal emails",
        "patient or clinical data",
        "real institutional data",
        "internal prompts",
        "raw chatgpt/codex transcripts",
        "unreviewed logs",
        "caches",
        "temporary outputs",
        "uncontrolled `results/`",
        "uncontrolled `data_sessions/`",
        "uncontrolled `data_processed/`",
        "large generated artifacts",
        "unpublished real datasets",
        "non-consented datasets",
        "fixtures",
        "toy/demo datasets",
        "publication demo inputs",
        "expected outputs generated from safe demo data",
        "documentation examples",
        "tests",
        "publication-safety policy",
        "does not imply that excluded files are scientifically invalid",
        "prevents accidental disclosure",
    ]
    for term in required_terms:
        assert term in text
