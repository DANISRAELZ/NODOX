from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "pseudomonas_aeruginosa_publication_demo_phase3_manuscript_material.md"
FORBIDDEN_TERMS = [
    "clinically_valid",
    "validated_experimentally",
    "safe_target",
    "definitive_target",
    "confirmed_drug_target",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase3_manuscript_material_document_exists_and_has_required_terms() -> None:
    assert DOC_PATH.is_file()
    text = _read_text(DOC_PATH)
    lower_text = text.lower()

    for required in [
        "Pseudomonas aeruginosa",
        "publication demo",
        "manuscript material",
        "user_curated",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "evidence_strength",
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "resistance_association",
        "provenance",
        "examples/pseudomonas_aeruginosa_publication_demo/expected_outputs/publication_candidate_summary.csv",
    ]:
        assert required in text

    for required in [
        "interpretacion conservadora",
        "no es validacion clinica",
        "no es validacion experimental",
        "score alto no equivale a confianza alta",
        "evidencia insuficiente no equivale a bajo riesgo",
    ]:
        assert required in lower_text

    for section in [
        "## Methods",
        "## Results",
        "## Discussion",
        "## Limitations",
        "## Proposed manuscript figure",
        "## Proposed manuscript table",
        "## Checklist de publicacion",
    ]:
        assert section in text

    assert "user_curated no significa evidencia externa automaticamente verificada" in lower_text


def test_phase3_manuscript_material_avoids_disallowed_scope_and_claims() -> None:
    lower_text = _read_text(DOC_PATH).lower()

    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in lower_text

    assert "corynebacterium" not in lower_text
    assert "user_curated es evidencia externa verificada automaticamente" not in lower_text
    assert "user_curated significa evidencia externa automaticamente verificada" not in lower_text
