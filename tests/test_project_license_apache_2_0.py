from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_license_is_not_invented_when_missing() -> None:
    license_path = PROJECT_ROOT / "LICENSE"
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    final_check = (PROJECT_ROOT / "docs" / "final_publication_release_check.md").read_text(encoding="utf-8").lower()

    if license_path.exists():
        license_text = license_path.read_text(encoding="utf-8").lower()
        assert "apache license" in license_text or "mit license" in license_text or "bsd" in license_text
    else:
        assert "license pending review before public distribution" in readme
        assert "license decision is complete" in final_check
