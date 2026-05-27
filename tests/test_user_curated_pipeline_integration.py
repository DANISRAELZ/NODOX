from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.pipeline import run_pipeline


def _write_workspace_config(workspace: Path) -> None:
    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "params.yaml").write_text("", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> pd.DataFrame:
    assert path.exists(), path
    return pd.read_csv(path)


def _assert_no_forbidden_source_tokens(values: pd.Series) -> None:
    combined = " ".join(values.fillna("").astype(str).str.lower())
    for token in ["demo", "proxy", "online", "controlled_reference"]:
        assert token not in combined
    assert "source_type=cache" not in combined
    assert "resolved_from_cache" not in combined


def test_user_curated_data_user_runs_through_pipeline_preserving_provenance(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    data_user = workspace / "data_user"
    _write_workspace_config(workspace)

    candidates = [
        ("PIPEUSER_0001", "pipeA"),
        ("PIPEUSER_0002", "pipeB"),
    ]
    provenance = "source_type=user_curated; provenance=user_curated_pipeline_validation"
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
                "virulence_score": "0.72",
                "virulence_factor": "1",
                "database": provenance,
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "virulence_score": "0.10",
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
                    "reference_or_note=local_note_no_external_verification"
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

    result = run_pipeline(
        base_dir=workspace,
        config_path=workspace / "config" / "params.yaml",
        mode="compare",
        online_source_mode="offline_only",
    )

    assert result["integrated_rows"] == 2
    assert result["feature_rows"] == 2

    integrated = _read_csv(workspace / "data_processed" / "integrated_nodes.csv")
    features = _read_csv(workspace / "data_processed" / "phase2_features.csv")
    scored = _read_csv(workspace / "data_processed" / "scored_nodes.csv")
    ranking = _read_csv(workspace / "results" / "ranking_nodos.csv")
    report_text = (workspace / "results" / "report_phase2.md").read_text(encoding="utf-8").lower()

    expected_ids = {candidate[0] for candidate in candidates}
    assert set(integrated["protein_id"]) == expected_ids
    assert set(features["protein_id"]) == expected_ids
    assert set(scored["protein_id"]) == expected_ids
    assert expected_ids <= set(ranking["protein_id"])

    for layer in ["essentiality", "virulence", "human_homologs", "localization", "evidence_quality"]:
        assert f"{layer}_source_type" in integrated.columns
        assert f"{layer}_is_user_supplied" in integrated.columns
        assert f"{layer}_is_cached" in integrated.columns
        assert f"{layer}_is_proxy" in integrated.columns
        assert integrated[f"{layer}_source_type"].eq("user").all()
        assert integrated[f"{layer}_is_user_supplied"].astype(bool).all()
        assert not integrated[f"{layer}_is_cached"].astype(bool).any()
        assert not integrated[f"{layer}_is_proxy"].astype(bool).any()
        _assert_no_forbidden_source_tokens(integrated[f"{layer}_source_name"])

    _assert_no_forbidden_source_tokens(integrated["source_database"])
    assert integrated["source_database"].str.contains("source_type=user_curated").all()
    assert integrated["phase3_evidence_quality_database"].str.contains("user_curated_pipeline_validation").all()

    unresolved_row = features.set_index("protein_id").loc["PIPEUSER_0002"]
    unresolved_text = " ".join(str(value).lower() for value in unresolved_row.fillna("").to_dict().values())
    assert "insufficient_evidence" in unresolved_text
    assert "missing_evidence=unresolved_risk" in unresolved_text
    assert "safe_target" not in unresolved_text
    assert "low_risk" not in unresolved_text
    assert "accepted_for_test" not in unresolved_text
    assert "clinically_valid" not in unresolved_text
    assert "validated_experimentally" not in unresolved_text

    feature_text = " ".join(str(value).lower() for value in features.fillna("").to_numpy().ravel())
    assert "pending_review" in feature_text
    assert "include_for_structure_check" in feature_text
    assert "local_note_no_external_verification" in feature_text
    assert "not_experimental_validation" in feature_text
    assert "source_type=user_curated" in feature_text

    for forbidden_phrase in [
        "clinically_valid",
        "validated_experimentally",
        "safe_target",
        "accepted_for_test",
    ]:
        assert forbidden_phrase not in report_text
    assert "ausencia o insuficiencia de evidencia no equivale a bajo riesgo" in report_text
