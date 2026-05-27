from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.pipeline import run_pipeline


USER_LAYERS = ["essentiality", "virulence", "human_homologs", "localization", "evidence_quality"]
FORBIDDEN_SOURCE_TOKENS = ["demo", "proxy", "online", "controlled_reference"]
FORBIDDEN_INTERPRETIVE_TOKENS = [
    "accepted_for_test",
    "safe_target",
    "clinically_valid",
    "validated_experimentally",
]


def _write_workspace_config(workspace: Path) -> None:
    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "params.yaml").write_text("", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> pd.DataFrame:
    assert path.exists(), path
    return pd.read_csv(path)


def _read_text(path: Path) -> str:
    assert path.exists(), path
    return path.read_text(encoding="utf-8").lower()


def _combined_text(frame: pd.DataFrame) -> str:
    return " ".join(str(value).lower() for value in frame.fillna("").to_numpy().ravel())


def _assert_no_forbidden_source_tokens(text: str) -> None:
    for token in FORBIDDEN_SOURCE_TOKENS:
        assert token not in text
    assert "source_type=cache" not in text
    assert "resolved_from_cache" not in text


def _assert_no_false_validation_tokens(text: str) -> None:
    for token in FORBIDDEN_INTERPRETIVE_TOKENS:
        assert token not in text


def _write_user_curated_layers(data_user: Path) -> None:
    candidates = [
        ("REPORTUSER_0001", "reportA"),
        ("REPORTUSER_0002", "reportB"),
    ]
    provenance = "source_type=user_curated; provenance=user_curated_final_reporting_validation"
    unresolved = "insufficient_evidence; missing_evidence=unresolved_risk"

    _write_csv(
        data_user / "essentiality.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "essential": "1",
                "evidence": "reviewed_user_curated_local_export",
                "database": provenance,
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "essential": "0",
                "evidence": unresolved,
                "database": provenance,
            },
        ],
    )
    _write_csv(
        data_user / "virulence.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "virulence_score": "0.68",
                "virulence_factor": "1",
                "database": provenance,
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "virulence_score": "0.05",
                "virulence_factor": "0",
                "database": provenance,
            },
        ],
    )
    _write_csv(
        data_user / "human_homologs.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "human_homolog": "0",
                "evalue": "1.0",
                "human_gene": "none",
                "source_database": provenance,
                "evidence_source_type": "user_curated_manual_review",
                "curator_notes": "local_note is curation context only",
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "human_homolog": "0",
                "evalue": "1.0",
                "human_gene": "none",
                "source_database": provenance,
                "evidence_source_type": "user_curated_manual_review",
                "curator_notes": "missing_evidence=unresolved_risk; favorable safety cannot be inferred",
            },
        ],
    )
    _write_csv(
        data_user / "localization.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "localization": "outer_membrane",
                "database": provenance,
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "localization": "unknown",
                "database": provenance,
            },
        ],
    )
    _write_csv(
        data_user / "evidence_quality.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "evidence_quality_score": "0.40",
                "confidence_ceiling": "0.40",
                "evidence_source_type": "user_curated_manual_curation",
                "evidence_notes": (
                    "pending_review; curation_decision=include_for_structure_check; "
                    "reference_or_note=local_note_no_external_verification; "
                    "curator_notes=preserved_local_context"
                ),
                "audit_flags": "user_curated;interpretive_only;not_experimental_validation",
                "phase3_notes": "curator_notes preserve context and do not verify externally",
                "database": provenance,
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "evidence_quality_score": "0.10",
                "confidence_ceiling": "0.10",
                "evidence_source_type": "user_curated_manual_curation",
                "evidence_notes": unresolved,
                "audit_flags": "user_curated;insufficient_evidence;unresolved_risk",
                "phase3_notes": "insufficient evidence remains unresolved risk",
                "database": provenance,
            },
        ],
    )


def test_user_curated_final_reports_preserve_conservative_interpretation(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    data_user = workspace / "data_user"
    _write_workspace_config(workspace)
    _write_user_curated_layers(data_user)

    result = run_pipeline(
        base_dir=workspace,
        config_path=workspace / "config" / "params.yaml",
        mode="compare",
        online_source_mode="offline_only",
    )

    assert result["integrated_rows"] == 2
    assert result["feature_rows"] == 2

    results_dir = workspace / "results"
    expected_artifacts = [
        results_dir / "ranking_nodos.csv",
        results_dir / "report_phase2.md",
        results_dir / "candidate_explanations_simple.csv",
        results_dir / "candidate_explanations_simple.md",
        results_dir / "candidate_audit.csv",
        results_dir / "candidate_audit.md",
        results_dir / "evidence_strength_audit.csv",
        results_dir / "evidence_strength_audit.md",
        results_dir / "layer_resolution_summary.csv",
        results_dir / "layer_resolution_summary.md",
    ]
    for artifact in expected_artifacts:
        assert artifact.exists(), artifact

    expected_ids = {"REPORTUSER_0001", "REPORTUSER_0002"}
    ranking = _read_csv(results_dir / "ranking_nodos.csv")
    assert expected_ids <= set(ranking["protein_id"])
    for column in ["therapeutic_priority_score", "evidence_confidence_score"]:
        assert column in ranking.columns
    ranking_candidates = ranking[ranking["protein_id"].isin(expected_ids)]
    ranking_provenance_columns = [
        column
        for column in ranking_candidates.columns
        if any(token in column for token in ["source", "provenance", "retrieval", "cache", "proxy"])
    ]
    if ranking_provenance_columns:
        _assert_no_forbidden_source_tokens(_combined_text(ranking_candidates[ranking_provenance_columns]))

    layer_summary = _read_csv(results_dir / "layer_resolution_summary.csv")
    layer_summary_md = _read_text(results_dir / "layer_resolution_summary.md")
    user_layer_summary = layer_summary[layer_summary["layer"].isin(USER_LAYERS)]
    assert set(USER_LAYERS) <= set(user_layer_summary["layer"])
    assert user_layer_summary["source_type"].eq("user").all()
    assert user_layer_summary["is_user_supplied"].astype(bool).all()
    assert not user_layer_summary["is_cached"].astype(bool).any()
    assert not user_layer_summary["is_proxy"].astype(bool).any()
    assert "user" in layer_summary_md
    _assert_no_forbidden_source_tokens(_combined_text(user_layer_summary))

    explanations = _read_csv(results_dir / "candidate_explanations_simple.csv")
    explanations_md = _read_text(results_dir / "candidate_explanations_simple.md")
    candidate_explanations = explanations[explanations["protein_id"].isin(expected_ids)]
    explanation_text = _combined_text(candidate_explanations) + " " + explanations_md
    assert expected_ids <= set(explanations["protein_id"])
    assert "user_curated" in explanation_text
    assert "no evidencia externa verificada automaticamente" in explanation_text
    assert "therapeutic_priority_score" in explanation_text
    assert "evidence_confidence_score" in explanation_text
    assert "score alto no equivale a confianza alta" in explanation_text
    assert "no equivale a validacion experimental" in explanation_text
    assert "validacion clinica" in explanation_text
    assert "include_for_structure_check no es validacion experimental" in explanation_text
    assert "curator_notes preserva contexto" in explanation_text
    _assert_no_false_validation_tokens(explanation_text)

    candidate_audit = _read_csv(results_dir / "candidate_audit.csv")
    candidate_audit_md = _read_text(results_dir / "candidate_audit.md")
    unresolved_audit = candidate_audit[candidate_audit["protein_id"].eq("REPORTUSER_0002")]
    assert len(unresolved_audit) == 1
    unresolved_audit_text = _combined_text(unresolved_audit) + " " + candidate_audit_md
    assert "low_risk" not in unresolved_audit_text
    _assert_no_false_validation_tokens(unresolved_audit_text)

    evidence_strength = _read_csv(results_dir / "evidence_strength_audit.csv")
    evidence_strength_md = _read_text(results_dir / "evidence_strength_audit.md")
    evidence_strength_text = _combined_text(evidence_strength) + " " + evidence_strength_md
    assert {"evidence_strength", "evidence_strength_scope_note"}.issubset(evidence_strength.columns)
    assert "no modifica therapeutic_priority_score" in evidence_strength_text
    assert "no modifica therapeutic_priority_score ni evidence_confidence_score" in evidence_strength_text
    assert "user_curated significa evidencia aportada" in evidence_strength_text
    assert "no evidencia externa verificada automaticamente" in evidence_strength_text
    assert "evidencia insuficiente no equivale a bajo riesgo" in evidence_strength_text
    assert "no equivale a validacion experimental" in evidence_strength_text
    assert set(evidence_strength["evidence_strength"]).issubset({"strong", "moderate", "weak", "insufficient"})
    final_interpretation_text = explanation_text + " " + evidence_strength_text
    assert "evidencia insuficiente" in final_interpretation_text
    assert "no equivale a bajo riesgo" in final_interpretation_text

    report_text = _read_text(results_dir / "report_phase2.md")
    for required_phrase in [
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "score alto no equivale a confianza alta",
        "un score alto no equivale a validacion experimental",
        "no recomendaciones clinicas",
        "ausencia o insuficiencia de evidencia no equivale a bajo riesgo",
        "user_curated",
        "no equivale automaticamente a evidencia externa verificada",
    ]:
        assert required_phrase in report_text
    _assert_no_false_validation_tokens(report_text)
