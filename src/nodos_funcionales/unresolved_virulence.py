from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError


VIRULENCE_LAYER_COLUMNS = [
    "protein_id",
    "gene",
    "protein_id_original",
    "protein_id_canonical",
    "virulence_score",
    "virulence_factor",
    "evidence",
    "source_database",
    "database",
    "mapping_confidence",
    "retrieval_status",
    "evidence_source_type",
    "unresolved_evidence_note",
]

ID_SOURCE_FILES = [
    ("data_processed", "normalized_localization.csv"),
    ("data_processed", "validated_localization.csv"),
    ("data_processed", "normalized_essentiality.csv"),
    ("data_processed", "validated_essentiality.csv"),
    ("data_processed", "normalized_uniprot_annotations.csv"),
    ("data_raw", "uniprot_annotations.csv"),
    ("data_external", "localization.csv"),
    ("data_external", "essentiality.csv"),
]

ID_COLUMNS = [
    "protein_id",
    "protein_id_canonical",
    "protein_id_original",
    "uniprot_accession",
    "accession",
]


def materialize_unresolved_virulence_layer(workspace: Path) -> None:
    """Create processed unresolved virulence files without inferring evidence."""
    workspace = Path(workspace)
    processed_dir = workspace / "data_processed"
    normalized_path = processed_dir / "normalized_virulence.csv"
    validated_path = processed_dir / "validated_virulence.csv"
    if normalized_path.exists() and validated_path.exists():
        return

    identifiers = _collect_protein_identifiers(workspace)
    if not identifiers:
        raise ValueError("Cannot materialize unresolved virulence layer: no protein identifiers found in workspace.")

    processed_dir.mkdir(parents=True, exist_ok=True)
    virulence = _build_unresolved_virulence_frame(identifiers)
    if not normalized_path.exists():
        virulence.to_csv(normalized_path, index=False)
    if not validated_path.exists():
        virulence.to_csv(validated_path, index=False)
    _update_validation_summary(workspace, len(virulence))
    _update_layer_resolution_manifest(workspace, normalized_path, len(virulence))
    _update_online_only_virulence_manifest(workspace, normalized_path, len(virulence))


def _collect_protein_identifiers(workspace: Path) -> list[tuple[str, str]]:
    seen: set[str] = set()
    identifiers: list[tuple[str, str]] = []
    for directory_name, filename in ID_SOURCE_FILES:
        path = workspace / directory_name / filename
        if not path.exists():
            continue
        try:
            table = pd.read_csv(path)
        except EmptyDataError:
            continue
        for _, row in table.iterrows():
            protein_id = _first_non_empty(row, ID_COLUMNS)
            if not protein_id or protein_id in seen:
                continue
            seen.add(protein_id)
            gene = _first_non_empty(row, ["gene", "gene_symbol_normalized", "uniprot_gene_primary"]) or protein_id
            identifiers.append((protein_id, gene))
    return identifiers


def _build_unresolved_virulence_frame(identifiers: list[tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for protein_id, gene in identifiers:
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "protein_id_original": protein_id,
                "protein_id_canonical": protein_id,
                "virulence_score": pd.NA,
                "virulence_factor": "",
                "evidence": "unresolved",
                "source_database": "provider_not_implemented",
                "database": "provider_not_implemented",
                "mapping_confidence": 0.0,
                "retrieval_status": "unresolved",
                "evidence_source_type": "unresolved_online_required_fallback",
                "unresolved_evidence_note": (
                    "Virulence provider was unavailable, not implemented, failed, or returned no usable data; "
                    "no positive virulence evidence was inferred."
                ),
            }
        )
    return pd.DataFrame(rows, columns=VIRULENCE_LAYER_COLUMNS)


def _update_validation_summary(workspace: Path, row_count: int) -> None:
    path = workspace / "data_processed" / "validation_summary.csv"
    row = {
        "table": "virulence",
        "severity": "info",
        "issue_type": "unresolved_layer_materialized",
        "count": int(row_count),
        "details": "source_database=provider_not_implemented; evidence=unresolved; retrieval_status=unresolved",
    }
    if path.exists():
        try:
            summary = pd.read_csv(path)
        except EmptyDataError:
            summary = pd.DataFrame()
        summary = summary[
            ~(
                summary.get("table", pd.Series(dtype=str)).astype(str).eq("virulence")
                & summary.get("issue_type", pd.Series(dtype=str)).astype(str).eq("unresolved_layer_materialized")
            )
        ].copy()
        summary = pd.concat([summary, pd.DataFrame([row])], ignore_index=True)
    else:
        summary = pd.DataFrame([row])
    path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path, index=False)


def _update_layer_resolution_manifest(workspace: Path, normalized_path: Path, row_count: int) -> None:
    path = workspace / "results" / "layer_resolution_manifest.json"
    manifest = _read_json(path)
    if not isinstance(manifest, dict):
        manifest = {}
    manifest["virulence"] = {
        **manifest.get("virulence", {}),
        "layer_key": "virulence",
        "filename": "virulence.csv",
        "resolved_from": "processed_unresolved_fallback",
        "source_type": "unresolved",
        "source_name": "provider_not_implemented",
        "is_user_supplied": False,
        "is_external": False,
        "is_cached": False,
        "is_proxy": False,
        "confidence": 0.0,
        "retrieval_status": "unresolved",
        "output_path": str(normalized_path),
        "selected_inputs": ["processed:normalized_virulence.csv"],
        "generated_by": "materialize_unresolved_virulence_layer",
        "row_count": int(row_count),
    }
    _write_json(path, manifest)


def _update_online_only_virulence_manifest(workspace: Path, normalized_path: Path, row_count: int) -> None:
    path = workspace / "results" / "online_only_virulence_manifest.json"
    manifest = _read_json(path)
    if not isinstance(manifest, dict):
        manifest = {}
    manifest.update(
        {
            "layer_key": "virulence",
            "provider_name": manifest.get("provider_name", "vfdb"),
            "provider": manifest.get("provider", manifest.get("provider_name", "vfdb")),
            "api_attempted": bool(manifest.get("api_attempted", False)),
            "api_success": False,
            "retrieved_record_count": int(manifest.get("retrieved_record_count", 0) or 0),
            "matched_candidate_count": int(row_count),
            "fallback_used": True,
            "fallback_reason": "provider_not_implemented_or_no_usable_virulence_data",
            "retrieval_status": "unresolved",
            "source_used": "provider_not_implemented",
            "source_database": "provider_not_implemented",
            "evidence": "unresolved",
            "data_realism_flag": "unresolved",
            "evidence_level": "unresolved",
            "experimental_validation_supported": False,
            "output_path": str(normalized_path),
            "generated_by": "materialize_unresolved_virulence_layer",
            "generated_at_utc": manifest.get("generated_at_utc") or _utc_now(),
        }
    )
    _write_json(path, manifest)


def _first_non_empty(row: pd.Series, columns: list[str]) -> str:
    for column in columns:
        if column not in row.index:
            continue
        value = row.get(column)
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.casefold() not in {"nan", "none", "null"}:
            return text
    return ""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
