from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FILES = [
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "CITATION.cff",
    PROJECT_ROOT / "CHANGELOG.md",
    PROJECT_ROOT / "docs" / "release_notes_v0_1_0_publication.md",
    PROJECT_ROOT / "docs" / "final_publication_release_check.md",
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_publication_release_metadata_is_consistent() -> None:
    texts = {path.name: _text(path) for path in FILES}
    combined = "\n".join(texts.values())

    assert "nodox" in texts["README.md"]
    assert "0.1.0-publication" in texts["CITATION.cff"]
    assert "v0.1.0-publication" in texts["CHANGELOG.md"]
    assert "v0.1.0-publication" in texts["release_notes_v0_1_0_publication.md"]
    assert "v0.1.0-publication" in texts["final_publication_release_check.md"]
    assert "2026-06-11" in texts["CITATION.cff"]
    assert "2026-06-11" in texts["CHANGELOG.md"]
    assert "2026-06-11" in texts["release_notes_v0_1_0_publication.md"]
    assert "doi:" not in combined
    assert "10.xxxx" not in combined
    assert "clinically validated" not in combined
    assert "experimentally validated" not in combined
    assert "validated therapeutic target" not in combined
    assert "confirmed therapeutic target" not in combined


def test_license_status_is_explicit() -> None:
    license_path = PROJECT_ROOT / "LICENSE"
    readme = _text(PROJECT_ROOT / "README.md")
    final_check = _text(PROJECT_ROOT / "docs" / "final_publication_release_check.md")
    third_party = _text(PROJECT_ROOT / "docs" / "third_party_data_terms_review.md")
    assert license_path.exists()
    assert "apache license" in _text(license_path)
    assert "apache license 2.0" in readme
    assert "project code is licensed under apache license 2.0" in final_check
    assert "provider terms can change" in third_party
