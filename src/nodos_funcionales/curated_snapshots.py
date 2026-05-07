from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_METADATA_FIELDS = {
    "schema_version",
    "organism",
    "strain",
    "canonical_organism_name",
    "taxon_id",
    "snapshot_id",
    "snapshot_label",
    "created_at_utc",
    "acquisition_mode",
    "network_policy",
    "allowed_sources",
    "source_versions",
    "cache_policy",
    "evidence_status",
    "confidence_policy",
    "provenance_policy",
    "limitations",
    "generated_by",
    "reproducibility_notes",
}

REQUIRED_SOURCE_FIELDS = {
    "source_name",
    "source_type",
    "source_status",
    "retrieval_status",
    "acquisition_mode",
    "cache_status",
    "confidence",
    "evidence_kind",
    "is_stub",
    "is_controlled",
    "is_real_external",
    "date_accessed_utc",
    "source_url",
    "source_reference",
    "notes",
}

REAL_FORBIDDEN_RETRIEVAL_MARKERS = ("stub", "fallback", "controlled_fixture")
FRESH_RETRIEVAL_STATUSES = {"fresh_api_run", "api_real", "api_real_success"}


def load_curated_snapshot(snapshot_dir: str | Path) -> dict[str, Any]:
    """Load the two contract files required by every curated snapshot."""
    root = Path(snapshot_dir)
    metadata = _read_json(root / "snapshot_metadata.json")
    sources_manifest = _read_json(root / "sources_manifest.json")
    return {"metadata": metadata, "sources_manifest": sources_manifest}


def validate_curated_snapshot(snapshot_dir: str | Path) -> list[str]:
    """Return user-readable validation errors for a curated snapshot directory."""
    root = Path(snapshot_dir)
    errors: list[str] = []
    try:
        snapshot = load_curated_snapshot(root)
    except FileNotFoundError as exc:
        return [f"Falta el archivo requerido `{Path(exc.filename).name}` en el snapshot."]
    except json.JSONDecodeError as exc:
        return [f"Un archivo JSON del snapshot no se puede leer: {exc.msg}."]

    metadata = snapshot["metadata"]
    sources_manifest = snapshot["sources_manifest"]
    errors.extend(_validate_metadata(metadata))
    errors.extend(_validate_sources_manifest(metadata, sources_manifest))
    return errors


def assert_curated_snapshot_valid(snapshot_dir: str | Path) -> None:
    """Raise a clear ValueError if a curated snapshot is invalid."""
    errors = validate_curated_snapshot(snapshot_dir)
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"El snapshot curado no es valido:\n{joined}")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"`{path.name}` debe contener un objeto JSON.")
    return data


def _validate_metadata(metadata: dict[str, Any]) -> list[str]:
    errors = _missing_field_errors(metadata, REQUIRED_METADATA_FIELDS, "metadata")
    allowed_sources = metadata.get("allowed_sources", [])
    if "allowed_sources" in metadata and not isinstance(allowed_sources, list):
        errors.append("`allowed_sources` debe ser una lista de tipos de fuente permitidos.")
    limitations = metadata.get("limitations", [])
    if "limitations" in metadata and not limitations:
        errors.append("`limitations` debe explicar las limitaciones del snapshot.")
    return errors


def _validate_sources_manifest(metadata: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["`sources_manifest.json` debe incluir una lista no vacia `sources`."]
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            errors.append(f"La fuente #{index} debe ser un objeto JSON.")
            continue
        errors.extend(_validate_source(metadata, source, index))
    return errors


def _validate_source(metadata: dict[str, Any], source: dict[str, Any], index: int) -> list[str]:
    label = str(source.get("source_name") or f"fuente #{index}")
    errors = _missing_field_errors(source, REQUIRED_SOURCE_FIELDS, label)
    if errors:
        return errors

    bool_flags = {
        "is_stub": source["is_stub"],
        "is_controlled": source["is_controlled"],
        "is_real_external": source["is_real_external"],
    }
    for field, value in bool_flags.items():
        if not isinstance(value, bool):
            errors.append(f"`{label}` tiene `{field}` no booleano; use true o false.")

    true_flags = [field for field, value in bool_flags.items() if value is True]
    if len(true_flags) > 1:
        errors.append(f"`{label}` mezcla categorias incompatibles: {', '.join(true_flags)}.")

    retrieval_status = str(source["retrieval_status"])
    source_status = str(source["source_status"])
    evidence_kind = str(source["evidence_kind"])
    acquisition_mode = str(source["acquisition_mode"])
    notes = str(source.get("notes") or "").strip()

    if source["is_real_external"] and any(marker in retrieval_status for marker in REAL_FORBIDDEN_RETRIEVAL_MARKERS):
        errors.append(f"`{label}` declara evidencia externa real, pero su retrieval_status es `{retrieval_status}`.")
    if source["is_controlled"] and retrieval_status in FRESH_RETRIEVAL_STATUSES:
        errors.append(f"`{label}` es controlada y no puede usar retrieval_status fresco `{retrieval_status}`.")
    if source["is_stub"] and evidence_kind not in {"stub", "stub_contract"}:
        errors.append(f"`{label}` esta marcada como stub, pero evidence_kind es `{evidence_kind}`.")
    if ("fallback" in retrieval_status or "fallback" in source_status) and not notes:
        errors.append(f"`{label}` usa fallback y debe incluir notas de procedencia.")
    if retrieval_status == "cache_reuse_run" and evidence_kind == "controlled_fixture":
        errors.append(f"`{label}` mezcla cache_reuse_run con controlled_fixture.")
    if metadata.get("network_policy") == "no_fresh_network_calls" and retrieval_status in FRESH_RETRIEVAL_STATUSES:
        errors.append(f"`{label}` declara `{retrieval_status}`, pero el snapshot prohibe llamadas frescas de red.")
    if acquisition_mode == "curated_snapshot_offline" and retrieval_status in FRESH_RETRIEVAL_STATUSES:
        errors.append(f"`{label}` usa adquisicion offline pero declara recuperacion fresca de API.")

    confidence = source["confidence"]
    if not isinstance(confidence, int | float) or not 0.0 <= float(confidence) <= 1.0:
        errors.append(f"`{label}` debe tener confidence numerica entre 0 y 1.")
    return errors


def _missing_field_errors(data: dict[str, Any], required_fields: set[str], label: str) -> list[str]:
    missing = sorted(field for field in required_fields if field not in data)
    return [f"`{label}` no tiene el campo obligatorio `{field}`." for field in missing]
