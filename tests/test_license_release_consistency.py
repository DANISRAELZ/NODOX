from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8").lower()


def test_license_release_consistency_keeps_dependency_review_pending() -> None:
    readme = _read("README.md")
    final_check = _read("docs/final_publication_release_check.md")
    audit = _read("docs/license_and_dependency_audit.md")
    third_party = _read("docs/third_party_data_terms_review.md")
    citation = _read("CITATION.cff")

    assert "apache license 2.0" in readme
    assert "distributed under" in readme
    assert "project code license is apache license 2.0" in final_check
    assert "dependency review is complete" in final_check
    assert "does not complete the legal review" in audit
    assert "provider terms can change" in third_party
    assert 'license: "apache-2.0"' in citation
    assert "do not create the final tag until manually approved" in final_check
