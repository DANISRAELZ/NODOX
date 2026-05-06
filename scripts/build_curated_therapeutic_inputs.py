"""Construye CSV terapeuticos curados desde las colas de curacion revisadas.

La herramienta no inventa evidencia ni rellena scores: solo copia filas donde
los campos `curated_*` minimos ya fueron completados por curacion manual.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


LAYER_OUTPUT_COLUMNS = {
    "clinical_impact": [
        "protein_id",
        "gene",
        "host_damage_reduction_potential",
        "disease_severity_association",
        "clinical_impact_score",
        "host_damage_score",
        "host_direct_damage_score",
        "virulence_associated_severity_score",
        "clinical_impact_catalog_source",
        "clinical_impact_evidence_type",
        "clinical_impact_evidence_reference",
        "clinical_impact_evidence_note",
        "database",
    ],
    "curated_disease_context": [
        "protein_id",
        "gene",
        "infection_context_score",
        "disease_context",
        "infection_stage",
        "context_evidence_type",
        "context_evidence_reference",
        "context_evidence_note",
        "database",
    ],
    "therapy_site_context": [
        "protein_id",
        "gene",
        "infection_site_access",
        "infection_site",
        "access_evidence_type",
        "access_evidence_reference",
        "access_evidence_note",
        "disease_context",
        "syndrome",
        "disease_site_context_source",
        "database",
    ],
}


QUEUE_FILENAMES = {
    "clinical_impact": "clinical_impact_curation_queue.csv",
    "curated_disease_context": "disease_context_curation_queue.csv",
    "therapy_site_context": "therapy_site_context_curation_queue.csv",
}


CATALOG_DIR_NAMES = {
    "clinical_impact": "clinical_impact",
    "curated_disease_context": "curated_disease_context",
    "therapy_site_context": "therapy_site_context",
}


def _is_filled(value: object) -> bool:
    text = str(value or "").strip()
    return text.lower() not in {"", "nan", "none", "not_reported", "not_experimental"}


def _to_numeric(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    numeric = float(numeric)
    if numeric < 0.0 or numeric > 1.0:
        return None
    return numeric


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower())
    return text.strip("_") or "manual_curated"


def _read_queue(results_dir: Path, layer: str) -> pd.DataFrame:
    path = results_dir / QUEUE_FILENAMES[layer]
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _build_clinical_impact(queue: pd.DataFrame, source_label: str) -> pd.DataFrame:
    rows = []
    for _, row in queue.iterrows():
        direct_damage = _to_numeric(row.get("curated_host_direct_damage_score"))
        severity = _to_numeric(row.get("curated_virulence_associated_severity_score"))
        clinical_impact = _to_numeric(row.get("curated_clinical_impact_score"))
        reference = row.get("curated_clinical_impact_evidence_reference")
        evidence_type = row.get("curated_clinical_impact_evidence_type")
        if direct_damage is None or severity is None or clinical_impact is None:
            continue
        if not _is_filled(reference) or not _is_filled(evidence_type):
            continue
        rows.append(
            {
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "host_damage_reduction_potential": direct_damage,
                "disease_severity_association": severity,
                "clinical_impact_score": clinical_impact,
                "host_damage_score": direct_damage,
                "host_direct_damage_score": direct_damage,
                "virulence_associated_severity_score": severity,
                "clinical_impact_catalog_source": source_label,
                "clinical_impact_evidence_type": evidence_type,
                "clinical_impact_evidence_reference": reference,
                "clinical_impact_evidence_note": row.get("curated_clinical_impact_evidence_note", ""),
                "database": row.get("curated_database", "") or source_label,
            }
        )
    return pd.DataFrame(rows, columns=LAYER_OUTPUT_COLUMNS["clinical_impact"])


def _build_disease_context(queue: pd.DataFrame, source_label: str) -> pd.DataFrame:
    rows = []
    for _, row in queue.iterrows():
        context_score = _to_numeric(row.get("curated_infection_context_score"))
        disease_context = row.get("curated_disease_context")
        infection_stage = row.get("curated_infection_stage")
        evidence_type = row.get("curated_context_evidence_type")
        reference = row.get("curated_context_evidence_reference")
        if context_score is None:
            continue
        if not all(_is_filled(value) for value in [disease_context, infection_stage, evidence_type, reference]):
            continue
        rows.append(
            {
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "infection_context_score": context_score,
                "disease_context": disease_context,
                "infection_stage": infection_stage,
                "context_evidence_type": evidence_type,
                "context_evidence_reference": reference,
                "context_evidence_note": row.get("curated_context_evidence_note", ""),
                "database": row.get("curated_database", "") or source_label,
            }
        )
    return pd.DataFrame(rows, columns=LAYER_OUTPUT_COLUMNS["curated_disease_context"])


def _build_therapy_site_context(queue: pd.DataFrame, source_label: str) -> pd.DataFrame:
    rows = []
    for _, row in queue.iterrows():
        access = _to_numeric(row.get("curated_infection_site_access"))
        infection_site = row.get("curated_infection_site")
        evidence_type = row.get("curated_access_evidence_type")
        reference = row.get("curated_access_evidence_reference")
        if access is None:
            continue
        if not all(_is_filled(value) for value in [infection_site, evidence_type, reference]):
            continue
        rows.append(
            {
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "infection_site_access": access,
                "infection_site": infection_site,
                "access_evidence_type": evidence_type,
                "access_evidence_reference": reference,
                "access_evidence_note": row.get("curated_access_evidence_note", ""),
                "disease_context": row.get("current_disease_context", ""),
                "syndrome": row.get("current_disease_context", ""),
                "disease_site_context_source": source_label,
                "database": row.get("curated_database", "") or source_label,
            }
        )
    return pd.DataFrame(rows, columns=LAYER_OUTPUT_COLUMNS["therapy_site_context"])


def _build_layer(queue: pd.DataFrame, layer: str, source_label: str) -> pd.DataFrame:
    if layer == "clinical_impact":
        return _build_clinical_impact(queue, source_label)
    if layer == "curated_disease_context":
        return _build_disease_context(queue, source_label)
    if layer == "therapy_site_context":
        return _build_therapy_site_context(queue, source_label)
    raise ValueError(f"Capa no soportada: {layer}")


def _output_path(workspace: Path, layer: str, target: str, catalog_key: str) -> Path:
    if target == "data_user":
        return workspace / "data_user" / f"{layer}.csv"
    return workspace / "data_external" / "curated_catalogs" / CATALOG_DIR_NAMES[layer] / f"{catalog_key}.csv"


def build_curated_inputs(
    workspace: Path,
    target: str,
    catalog_key: str,
    overwrite: bool,
) -> list[tuple[str, Path, int]]:
    results_dir = workspace / "results"
    catalog_key = _slug(catalog_key)
    source_label = f"curated_from_queue_{catalog_key}"
    written: list[tuple[str, Path, int]] = []
    for layer in ["clinical_impact", "curated_disease_context", "therapy_site_context"]:
        queue = _read_queue(results_dir, layer)
        if queue.empty:
            continue
        curated = _build_layer(queue, layer, source_label)
        if curated.empty:
            continue
        path = _output_path(workspace, layer, target, catalog_key)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Ya existe {path}. Usa --overwrite para reemplazarlo.")
        path.parent.mkdir(parents=True, exist_ok=True)
        curated.to_csv(path, index=False)
        written.append((layer, path, len(curated)))
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construir CSV terapeuticos curados desde filas revisadas en results/*_curation_queue.csv."
    )
    parser.add_argument("--workspace", type=Path, default=BASE_DIR, help="Workspace que contiene results/ y data_user/.")
    parser.add_argument(
        "--target",
        choices=["data_user", "external_catalog"],
        default="data_user",
        help="Destino de los CSV curados.",
    )
    parser.add_argument(
        "--catalog-key",
        default="manual_curated",
        help="Nombre del archivo cuando --target external_catalog. Ejemplo: taxon_287.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Reemplazar archivos existentes.")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    catalog_key = _slug(args.catalog_key)
    written = build_curated_inputs(
        workspace=workspace,
        target=args.target,
        catalog_key=catalog_key,
        overwrite=bool(args.overwrite),
    )
    if not written:
        print("[INFO] No se escribieron archivos: no hay filas curated_* completas en las colas.")
        return
    for layer, path, row_count in written:
        print(f"[OK] {layer}: {path} ({row_count} filas)")


if __name__ == "__main__":
    main()
