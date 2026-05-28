from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.acquisition import import_user_dataset
from src.nodos_funcionales.pipeline import run_pipeline
from src.nodos_funcionales.user_curated_validation import (
    USER_CURATED_MANIFEST_COLUMNS,
    validate_user_curated_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPORTABLE_LAYER_FILES = {
    "essentiality": "essentiality.csv",
    "virulence": "virulence.csv",
    "human_homologs": "human_homologs.csv",
    "localization": "localization.csv",
    "evidence_quality": "evidence_quality.csv",
}
USER_LAYERS = set(IMPORTABLE_LAYER_FILES)
FORBIDDEN_SOURCE_TOKENS = ["demo", "proxy", "controlled_reference"]
FORBIDDEN_DIRECT_USER_EVIDENCE_TOKENS = ["source_type=cache", "resolved_from_cache", "source_type=online"]
FORBIDDEN_VALIDATION_TOKENS = [
    "safe_target",
    "clinically_valid",
    "validated_experimentally",
    "validated_clinically",
]


def _write_workspace_config(workspace: Path) -> None:
    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "params.yaml").write_text("", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]))
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


def _assert_no_forbidden_validation_tokens(text: str) -> None:
    for token in FORBIDDEN_VALIDATION_TOKENS:
        assert token not in text


def _assert_no_forbidden_direct_user_evidence_tokens(text: str) -> None:
    for token in FORBIDDEN_SOURCE_TOKENS + FORBIDDEN_DIRECT_USER_EVIDENCE_TOKENS:
        assert token not in text


def _write_portable_user_curated_source(source_dir: Path) -> None:
    organism = "Klebsiella pneumoniae portable user validation isolate"
    strain = "KPV-01"
    dataset_id = "portable_user_curated_functional_validation_01"
    candidates = [
        ("FUNCUSER_0001", "fuvA"),
        ("FUNCUSER_0002", "fuvB"),
    ]
    provenance = "source_type=user_curated;source_name=local_review;provenance=portable_functional_validation"
    unresolved = "insufficient_evidence;missing_evidence=unresolved_risk;curator_notes=needs_follow_up"

    manifest_rows = [
        {
            "organism": organism,
            "strain": strain,
            "dataset_id": dataset_id,
            "dataset_version": "v1",
            "curator_name": "local functional validation curator",
            "curation_date": "2026-05-27",
            "source_type": "user_curated",
            "evidence_status": "reviewed" if filename != "evidence_quality.csv" else "pending_review",
            "evidence_kind": "local_review",
            "provenance": "user_curated_local_review_portable_fixture",
            "input_file": filename,
            "input_schema": f"data_templates/{filename.replace('.csv', '_template.csv')}",
            "required_for_scoring": "true",
            "notes": "portable tmp_path fixture; not clinical or experimental validation",
        }
        for filename in IMPORTABLE_LAYER_FILES.values()
    ]
    _write_csv(source_dir / "manifest.csv", manifest_rows, fieldnames=USER_CURATED_MANIFEST_COLUMNS)

    _write_csv(
        source_dir / "essentiality.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "essential": "1",
                "evidence": "reviewed_user_curated_local_review",
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
        source_dir / "virulence.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "virulence_score": "0.66",
                "virulence_factor": "1",
                "database": provenance,
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "virulence_score": "0.04",
                "virulence_factor": "0",
                "database": provenance,
            },
        ],
    )
    _write_csv(
        source_dir / "human_homologs.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "human_homolog": "0",
                "evalue": "1.0",
                "human_gene": "none",
                "source_database": provenance,
                "evidence_source_type": "user_curated_manual_review",
                "curator_notes": "local_note is preserved context only",
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "human_homolog": "0",
                "evalue": "1.0",
                "human_gene": "none",
                "source_database": provenance,
                "evidence_source_type": "user_curated_manual_review",
                "curator_notes": unresolved,
            },
        ],
    )
    _write_csv(
        source_dir / "localization.csv",
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
        source_dir / "evidence_quality.csv",
        [
            {
                "protein_id": candidates[0][0],
                "gene": candidates[0][1],
                "evidence_quality_score": "0.45",
                "confidence_ceiling": "0.45",
                "evidence_source_type": "user_curated_manual_curation",
                "evidence_notes": "pending_review; local_note=structure_check_requested",
                "audit_flags": "user_curated;interpretive_only;not_experimental_validation",
                "phase3_notes": "curator_notes do not verify evidence externally",
                "database": provenance,
            },
            {
                "protein_id": candidates[1][0],
                "gene": candidates[1][1],
                "evidence_quality_score": "0.08",
                "confidence_ceiling": "0.08",
                "evidence_source_type": "user_curated_manual_curation",
                "evidence_notes": unresolved,
                "audit_flags": "user_curated;insufficient_evidence;unresolved_risk",
                "phase3_notes": "insufficient evidence remains unresolved risk",
                "database": provenance,
            },
        ],
    )


def test_minimal_user_curated_functional_validation_flow_reaches_final_reports(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source_dir = tmp_path / "portable_user_curated_source"
    _write_workspace_config(workspace)
    _write_portable_user_curated_source(source_dir)

    manifest_path = source_dir / "manifest.csv"
    assert validate_user_curated_manifest(manifest_path) == []
    manifest_text = manifest_path.read_text(encoding="utf-8").lower()
    assert "pao1" not in manifest_text
    assert "h37rv" not in manifest_text
    assert "source_type,user_curated" not in manifest_text

    for dataset_key, filename in IMPORTABLE_LAYER_FILES.items():
        imported = import_user_dataset(
            workspace=workspace,
            dataset_key=dataset_key,
            input_path=source_dir / filename,
            project_root=PROJECT_ROOT,
            as_user_layer=True,
        )
        assert imported["as_user_layer"] is True
        assert Path(imported["target_path"]).is_relative_to(workspace / "data_user")
        assert Path(imported["target_path"]).exists()

    result = run_pipeline(
        base_dir=workspace,
        config_path=workspace / "config" / "params.yaml",
        mode="compare",
        online_source_mode="offline_only",
    )

    assert result["integrated_rows"] == 2
    assert result["feature_rows"] == 2

    results_dir = workspace / "results"
    expected_outputs = [
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
    for output_path in expected_outputs:
        assert output_path.exists(), output_path

    expected_ids = {"FUNCUSER_0001", "FUNCUSER_0002"}
    integrated = _read_csv(workspace / "data_processed" / "integrated_nodes.csv")
    features = _read_csv(workspace / "data_processed" / "phase2_features.csv")
    ranking = _read_csv(results_dir / "ranking_nodos.csv")
    layer_summary = _read_csv(results_dir / "layer_resolution_summary.csv")
    explanations = _read_csv(results_dir / "candidate_explanations_simple.csv")
    candidate_audit = _read_csv(results_dir / "candidate_audit.csv")
    evidence_strength = _read_csv(results_dir / "evidence_strength_audit.csv")

    assert set(integrated["protein_id"]) == expected_ids
    assert set(features["protein_id"]) == expected_ids
    assert expected_ids <= set(ranking["protein_id"])
    assert {"therapeutic_priority_score", "evidence_confidence_score"}.issubset(ranking.columns)
    assert ranking["therapeutic_priority_score"].notna().all()
    assert ranking["evidence_confidence_score"].notna().all()

    user_layer_summary = layer_summary[layer_summary["layer"].isin(USER_LAYERS)]
    assert set(user_layer_summary["layer"]) == USER_LAYERS
    assert user_layer_summary["source_type"].eq("user").all()
    assert user_layer_summary["is_user_supplied"].astype(bool).all()
    assert not user_layer_summary["is_cached"].astype(bool).any()
    assert not user_layer_summary["is_proxy"].astype(bool).any()
    _assert_no_forbidden_direct_user_evidence_tokens(_combined_text(user_layer_summary))

    for layer in USER_LAYERS:
        assert integrated[f"{layer}_source_type"].eq("user").all()
        assert integrated[f"{layer}_is_user_supplied"].astype(bool).all()
        assert not integrated[f"{layer}_is_cached"].astype(bool).any()
        assert not integrated[f"{layer}_is_proxy"].astype(bool).any()
        _assert_no_forbidden_direct_user_evidence_tokens(
            _combined_text(integrated[[f"{layer}_source_name", f"{layer}_retrieval_status"]])
        )

    unresolved_feature = features[features["protein_id"].eq("FUNCUSER_0002")]
    assert len(unresolved_feature) == 1
    unresolved_text = _combined_text(unresolved_feature)
    assert "insufficient_evidence" in unresolved_text
    assert "missing_evidence=unresolved_risk" in unresolved_text
    assert "low_risk" not in unresolved_text
    _assert_no_forbidden_validation_tokens(unresolved_text)

    feature_text = _combined_text(features)
    assert "pending_review" in feature_text
    assert "local_note" in feature_text
    assert "curator_notes" in feature_text
    assert "not_experimental_validation" in feature_text
    _assert_no_forbidden_validation_tokens(feature_text)

    final_report_text = " ".join(
        [
            _read_text(results_dir / "report_phase2.md"),
            _read_text(results_dir / "candidate_explanations_simple.md"),
            _read_text(results_dir / "candidate_audit.md"),
            _read_text(results_dir / "evidence_strength_audit.md"),
            _read_text(results_dir / "layer_resolution_summary.md"),
            _combined_text(explanations),
            _combined_text(candidate_audit),
            _combined_text(evidence_strength),
        ]
    )
    assert "therapeutic_priority_score" in final_report_text
    assert "evidence_confidence_score" in final_report_text
    assert "score alto no equivale a confianza alta" in final_report_text
    assert "evidencia insuficiente no equivale a bajo riesgo" in final_report_text
    assert "user_curated significa evidencia aportada" in final_report_text
    assert "no evidencia externa verificada automaticamente" in final_report_text
    assert "no equivale a validacion experimental" in final_report_text
    assert "validacion clinica" in final_report_text
    assert "source_type=cache" not in final_report_text
    assert "resolved_from_cache" not in final_report_text
    _assert_no_forbidden_validation_tokens(final_report_text)
