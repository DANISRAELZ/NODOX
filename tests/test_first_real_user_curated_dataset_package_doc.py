from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "first_real_user_curated_dataset_package.md"


def test_first_real_user_curated_dataset_package_doc_covers_contract() -> None:
    assert DOC_PATH.exists()
    raw_text = DOC_PATH.read_text(encoding="utf-8")
    text = raw_text.lower()

    for phrase in [
        "user_curated",
        "controlled_reference",
        "demo",
        "proxy",
        "cache",
        "online",
        "provenance_type",
        "provenance.yaml",
        "manifest.yaml",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "insufficient_evidence",
        "low_risk",
        "pending_review",
        "local_note",
        "curator_notes",
        "include_for_structure_check",
        "accepted_for_test",
        "needs_revision",
        "excluded_from_scoring",
        "ready_for_import",
        "conditionally_ready_for_controlled_test",
        "no predictor clinico",
        "plataforma de priorizacion terapeutica",
        "no validacion clinica",
        "no validacion experimental",
        "no uso clinico",
        "revision experta",
        "validacion experimental",
        "riesgo no resuelto",
        "gene_list.csv",
        "functional_annotations.csv",
        "essentiality.csv",
        "virulence.csv",
        "conservation.csv",
        "localization.csv",
        "human_homologs.csv",
        "manual_curation.csv",
        "evidence_quality.csv",
        "readme_dataset.md",
        "teoria de nodos funcionales",
        "multi-organismo",
        "score alto no equivale automaticamente a confianza alta",
        "evidencia local",
        "literatura externa",
        "procedencia",
        "primer dataset real",
        "importancia funcional",
        "selectividad",
        "accesibilidad",
        "conservacion",
        "riesgo de escape evolutivo",
        "redundancia",
        "tolerancia mutacional",
        "paralogia",
        "hgt",
        "recombinacion",
        "resistencia",
    ]:
        assert phrase in text

    for document_name in [
        "real_user_curated_dataset_validation.md",
        "real_user_operational_guide.md",
        "real_user_curated_dataset_checklist.md",
        "first_real_user_curated_dataset_readiness_index.md",
        "user_curated_portable_validation_phase_index.md",
        "internal_release_readiness_2026_05_27.md",
        "methodology.md",
        "data_model.md",
        "readme.md",
    ]:
        assert document_name in text

    assert "PowerShell" in raw_text
