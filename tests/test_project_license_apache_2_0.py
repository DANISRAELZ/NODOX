from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_license_is_apache_2_0() -> None:
    license_path = PROJECT_ROOT / "LICENSE"
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    final_check = (PROJECT_ROOT / "docs" / "final_publication_release_check.md").read_text(encoding="utf-8").lower()
    third_party = (PROJECT_ROOT / "docs" / "third_party_data_terms_review.md").read_text(encoding="utf-8").lower()

    assert license_path.exists()
    license_text = license_path.read_text(encoding="utf-8").lower()
    assert "apache license" in license_text
    assert "version 2.0, january 2004" in license_text
    assert "copyright 2026 the nodos funcionales contributors" in license_text
    assert "apache license 2.0" in readme
    assert "distributed under" in readme
    assert "project code is licensed under apache license 2.0" in final_check
    assert "external biological database content is not automatically covered" in third_party


def test_no_pending_project_license_language_remains() -> None:
    pending_phrase = " ".join(["license", "pending", "review", "before", "public", "distribution"])
    paths = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "docs" / "final_publication_release_check.md",
        PROJECT_ROOT / "docs" / "software_release_readiness_checklist.md",
        PROJECT_ROOT / "docs" / "pre_publication_repository_audit.md",
        PROJECT_ROOT / "docs" / "repository_hygiene_checklist.md",
        PROJECT_ROOT / "docs" / "license_and_dependency_audit.md",
        PROJECT_ROOT / "docs" / "v0_1_0_publication_release_decision.md",
        PROJECT_ROOT / "docs" / "publication_readiness_master_index.md",
        PROJECT_ROOT / "docs" / "release_notes_v0_1_0_publication.md",
    ]
    for path in paths:
        assert pending_phrase not in path.read_text(encoding="utf-8").lower()
