from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "sensitive_data_and_secret_scan.md"


def test_sensitive_data_and_secret_scan_documentation() -> None:
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    required_terms = [
        "api keys",
        "tokens",
        "passwords",
        ".env",
        "private keys",
        "secrets",
        "personal emails",
        "phone numbers",
        "local machine paths",
        "patient data",
        "clinical confidential data",
        "institutional confidential data",
        "internal prompts",
        "raw chatgpt/codex transcripts",
        "unreviewed logs",
        "uncontrolled `results/`",
        "uncontrolled `data_sessions/`",
        "uncontrolled `data_processed/`",
        "caches and temporary outputs",
        "lightweight repository-level scan",
        "final human review remains required",
    ]
    for term in required_terms:
        assert term in text


def test_lightweight_static_secret_scan_gate() -> None:
    assert not (PROJECT_ROOT / ".env").exists()
    final_check = (PROJECT_ROOT / "docs" / "final_publication_release_check.md").read_text(encoding="utf-8").lower()
    assert "repository owner has authorized" in final_check
    assert "public release inventory" in final_check
    for risky_name in [".env", "id_rsa", "secret.key", "credentials.json"]:
        assert not (PROJECT_ROOT / risky_name).exists()
