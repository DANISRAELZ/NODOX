from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_no_root_env_file_exists() -> None:
    assert not (PROJECT_ROOT / ".env").exists()


def test_release_docs_keep_public_tag_blocked_until_audit() -> None:
    audit = _read(PROJECT_ROOT / "docs" / "pre_publication_repository_audit.md")
    final_check = _read(PROJECT_ROOT / "docs" / "final_publication_release_check.md")
    assert "final public tag `v0.1.0-publication` remains blocked" in audit
    assert "final public release is blocked until" in final_check
    assert "do not create the final public release tag automatically" in audit


def test_no_raw_transcript_files_are_intentionally_documented_as_release_inputs() -> None:
    policy = _read(PROJECT_ROOT / "docs" / "public_release_exclusion_policy.md")
    assert "raw chatgpt/codex transcripts" in policy
    assert "always exclude or review before public release" in policy
