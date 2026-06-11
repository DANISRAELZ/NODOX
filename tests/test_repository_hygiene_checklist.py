from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "repository_hygiene_checklist.md"


def test_repository_hygiene_checklist_content() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "git status --short",
        "no unexpected modified tracked files",
        "no untracked private files",
        "no `.env`",
        "no credentials",
        "no secrets",
        "no private local paths",
        "no patient data",
        "no confidential institutional data",
        "no unreviewed prompts/logs",
        "no uncontrolled results",
        "no uncontrolled data_sessions",
        "no uncontrolled data_processed",
        "no cache metadata changes",
        "`license` present with apache license 2.0 for project code",
        "project code is licensed under apache license 2.0",
        "dependency license and security review remain release requirements",
        "dependency licenses reviewed",
        "dependency security reviewed",
        "readme limitations present",
        "citation metadata reviewed",
        "ai-use transparency statement present",
        "full offline suite passing",
        "final human approval before tag",
    ]
    for term in required_terms:
        assert term in text
