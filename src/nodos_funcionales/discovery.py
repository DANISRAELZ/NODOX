from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_config
from .taxonomy_api import query_ncbi_taxonomy
from .validation import DATASET_SPECS, SCHEMAS


FUTURE_DATASETS: list[dict[str, str]] = [
    {"filename": "clinical_impact.csv", "table_key": "clinical_impact", "category": "future"},
    {"filename": "curated_disease_context.csv", "table_key": "curated_disease_context", "category": "future"},
    {"filename": "therapy_site_context.csv", "table_key": "therapy_site_context", "category": "future"},
]

STRATEGY_CHOICES = {"antibiotic", "antivirulence", "functional", "meta"}
ACQUISITION_MODES = {"manual", "semi_auto", "auto"}
TAXON_RESOLUTION_MODES = {"offline_only", "cache_first", "online_optional", "api_stub", "auto", "local"}


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _slugify(value: str) -> str:
    normalized = _normalize_text(value).lower()
    slug_chars = [char if char.isalnum() else "_" for char in normalized]
    slug = "".join(slug_chars)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_catalog(project_root: Path, filename: str) -> dict[str, Any]:
    return _json_load(project_root / "config" / filename)


def _cache_path(project_root: Path, config: dict[str, Any]) -> Path:
    return project_root / "config" / str(config["taxonomy"]["cache_filename"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_resolution_mode(resolution_mode: str, config: dict[str, Any]) -> str:
    mode = str(resolution_mode)
    aliases = {str(key): str(value) for key, value in config["taxonomy"].get("legacy_mode_aliases", {}).items()}
    normalized = aliases.get(mode, mode)
    accepted = {str(key) for key, enabled in config["taxonomy"].get("accepted_resolution_modes", {}).items() if enabled}
    if normalized not in accepted:
        raise ValueError(f"taxon resolution mode no soportado: {resolution_mode}")
    return normalized


def _load_taxon_cache(project_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(project_root, config)
    if not path.exists():
        return {"schema_version": 2, "updated_at_utc": None, "entries": {}}
    payload = _json_load(path)
    if "schema_version" in payload:
        payload.setdefault("entries", {})
        return payload

    migrated_entries = {}
    for key, value in payload.get("entries", {}).items():
        migrated_entries[key] = {
            "cache_key": key,
            "saved_at_utc": value.get("timestamp_utc") or _utc_now(),
            "refresh_count": 1,
            "result": value,
        }
    return {
        "schema_version": 2,
        "updated_at_utc": _utc_now(),
        "entries": migrated_entries,
    }


def _save_taxon_cache(project_root: Path, config: dict[str, Any], cache_payload: dict[str, Any]) -> None:
    cache_payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(project_root, config), cache_payload)


def _cache_key(organism_name: str, strain: str | None) -> str:
    return f"{_normalize_text(organism_name).casefold()}::{_normalize_text(strain or '').casefold()}"


def _resolve_taxon_local(project_root: Path, organism_name: str, strain: str | None = None) -> dict[str, Any]:
    organism_input_name = _normalize_text(organism_name)
    if not organism_input_name:
        raise ValueError("organism_name no puede estar vacio")

    catalog = _load_catalog(project_root, "taxon_aliases.json")
    normalized_input = organism_input_name.casefold()
    matched_entry = None
    resolution_status = "unresolved_local"
    resolution_notes = "No hubo coincidencia exacta en el catalogo local; no se consultaron APIs externas."

    for entry in catalog["entries"]:
        canonical_name = _normalize_text(entry["canonical_name"])
        aliases = {_normalize_text(alias).casefold() for alias in entry.get("aliases", [])}
        aliases.add(canonical_name.casefold())
        if normalized_input == canonical_name.casefold():
            matched_entry = entry
            resolution_status = "exact_local_match"
            resolution_notes = "Coincidencia exacta en catalogo local."
            break
        if normalized_input in aliases:
            matched_entry = entry
            resolution_status = "alias_local_match"
            resolution_notes = "Coincidencia por alias en catalogo local."
            break

    if matched_entry is None:
        canonical_name = organism_input_name
        known_strains: list[str] = []
        taxon_id = None
        rank = None
    else:
        canonical_name = matched_entry["canonical_name"]
        known_strains = matched_entry.get("known_strains", [])
        taxon_id = matched_entry.get("taxon_id")
        rank = matched_entry.get("rank")

    strain_input = _normalize_text(strain) if strain else ""
    strain_canonical = strain_input
    if strain_input and known_strains:
        known_by_casefold = {item.casefold(): item for item in known_strains}
        if strain_input.casefold() in known_by_casefold:
            strain_canonical = known_by_casefold[strain_input.casefold()]
            resolution_notes += " Cepa reconocida en catalogo local."
        else:
            resolution_notes += " Cepa no encontrada en catalogo local; se conserva como fue ingresada."
    elif strain_input:
        resolution_notes += " No hay cepas registradas para este taxon en el catalogo local."

    organism_slug = _slugify(canonical_name + (f" {strain_canonical}" if strain_canonical else ""))
    return {
        "organism_input_name": organism_input_name,
        "organism_canonical_name": canonical_name,
        "strain_input": strain_input or None,
        "strain_canonical": strain_canonical or None,
        "taxon_id": taxon_id,
        "rank": rank,
        "matched_name": canonical_name,
        "source_used": "local_catalog",
        "taxon_provider": "local_catalog",
        "resolution_mode_used": "offline_only",
        "cache_hit": False,
        "api_attempted": False,
        "api_success": False,
        "fallback_reason": None,
        "taxon_resolution_status": resolution_status,
        "taxon_resolution_notes": resolution_notes,
        "resolution_confidence": 0.90 if matched_entry is not None else 0.30,
        "timestamp_utc": _utc_now(),
        "organism_slug": organism_slug,
    }


def _resolve_taxon_api_stub(project_root: Path, organism_name: str, strain: str | None, config: dict[str, Any]) -> dict[str, Any]:
    resolved = _resolve_taxon_local(project_root, organism_name, strain)
    resolved["source_used"] = "api_stub"
    resolved["taxon_provider"] = "stub"
    resolved["taxon_resolution_status"] = "api_stub_fallback"
    resolved["taxon_resolution_notes"] = (
        f"{config['taxonomy']['external_api_notes']} "
        f"Se devolvio la mejor resolucion local disponible para `{resolved['organism_input_name']}`."
    )
    resolved["resolution_mode_used"] = "api_stub"
    resolved["api_attempted"] = True
    resolved["api_success"] = False
    resolved["fallback_reason"] = "stub_mode_requested"
    resolved["resolution_confidence"] = min(float(resolved["resolution_confidence"]), 0.40)
    resolved["timestamp_utc"] = _utc_now()
    return resolved


def _backfill_taxon_result_fields(result: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(result)
    status = str(normalized.get("taxon_resolution_status", "unresolved_local"))
    inferred_source = "local_catalog"
    if status == "api_stub_fallback":
        inferred_source = "api_stub"
    elif status.startswith("online_"):
        inferred_source = "api_real"

    normalized.setdefault("taxon_id", None)
    normalized.setdefault("rank", None)
    normalized.setdefault("matched_name", normalized.get("organism_canonical_name"))
    normalized.setdefault("source_used", inferred_source)
    normalized.setdefault("taxon_provider", "ncbi_eutils" if inferred_source == "api_real" else inferred_source)
    normalized.setdefault("resolution_mode_used", "offline_only" if inferred_source == "local_catalog" else inferred_source)
    normalized.setdefault("cache_hit", False)
    normalized.setdefault("api_attempted", inferred_source in {"api_real", "api_stub"})
    normalized.setdefault("api_success", inferred_source == "api_real" and status != "online_fallback_local_no_match")
    normalized.setdefault("fallback_reason", "stub_mode_requested" if inferred_source == "api_stub" else None)
    normalized.setdefault(
        "resolution_confidence",
        0.95 if inferred_source == "api_real" else (0.40 if inferred_source == "api_stub" else 0.90),
    )
    normalized.setdefault("timestamp_utc", _utc_now())
    return normalized


def _cache_result(cache_payload: dict[str, Any], cache_key: str, resolved: dict[str, Any]) -> None:
    existing = cache_payload.get("entries", {}).get(cache_key, {})
    refresh_count = int(existing.get("refresh_count", 0)) + 1
    normalized_result = _backfill_taxon_result_fields(resolved)
    cache_payload.setdefault("entries", {})[cache_key] = {
        "cache_key": cache_key,
        "saved_at_utc": _utc_now(),
        "refresh_count": refresh_count,
        "result": normalized_result,
    }


def _resolve_taxon_online(
    project_root: Path,
    organism_name: str,
    strain: str | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    local_resolved = _resolve_taxon_local(project_root, organism_name, strain)
    api_result = query_ncbi_taxonomy(local_resolved["organism_canonical_name"], local_resolved.get("strain_canonical"), config)
    notes = [str(api_result["notes"]).strip()]
    notes.extend([str(item).strip() for item in api_result.get("api_error_notes", []) if str(item).strip()])

    if api_result["status"] == "online_no_match":
        local_resolved["api_attempted"] = True
        local_resolved["api_success"] = False
        local_resolved["fallback_reason"] = "api_no_match"
        local_resolved["taxon_resolution_status"] = "online_fallback_local_no_match"
        local_resolved["taxon_resolution_notes"] = " ".join([local_resolved["taxon_resolution_notes"], *notes]).strip()
        local_resolved["resolution_mode_used"] = "online_optional"
        local_resolved["timestamp_utc"] = api_result["timestamp_utc"]
        return local_resolved

    resolved = dict(local_resolved)
    matched_name = api_result.get("matched_name") or resolved["organism_canonical_name"]
    resolved["organism_canonical_name"] = matched_name
    resolved["matched_name"] = matched_name
    resolved["taxon_id"] = api_result.get("taxon_id")
    resolved["rank"] = api_result.get("rank")
    resolved["source_used"] = "api_real"
    resolved["taxon_provider"] = api_result.get("provider_name")
    resolved["resolution_mode_used"] = "online_optional"
    resolved["cache_hit"] = False
    resolved["api_attempted"] = True
    resolved["api_success"] = True
    resolved["fallback_reason"] = None
    resolved["taxon_resolution_status"] = api_result["status"]
    resolved["taxon_resolution_notes"] = " ".join(notes).strip()
    resolved["resolution_confidence"] = api_result["resolution_confidence"]
    resolved["timestamp_utc"] = api_result["timestamp_utc"]
    resolved["organism_slug"] = _slugify(
        matched_name + (f" {resolved['strain_canonical']}" if resolved.get("strain_canonical") else "")
    )
    return resolved


def resolve_taxon(
    project_root: Path,
    organism_name: str,
    strain: str | None = None,
    resolution_mode: str = "offline_only",
    config: dict[str, Any] | None = None,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
) -> dict[str, Any]:
    config = config or load_config(project_root / "config" / "params.yaml")
    normalized_mode = _normalize_resolution_mode(resolution_mode, config)
    cache = _load_taxon_cache(project_root, config)
    cache_key = _cache_key(organism_name, strain)

    if not refresh_cache and normalized_mode in {"offline_only", "cache_first", "online_optional", "auto"}:
        cached_entry = cache.get("entries", {}).get(cache_key)
        if cached_entry:
            cached = _backfill_taxon_result_fields(dict(cached_entry.get("result", cached_entry)))
            cached["cached_source_used"] = cached.get("source_used")
            cached["source_used"] = "cache"
            cached["cache_hit"] = True
            cached["resolution_mode_used"] = normalized_mode
            cached["taxon_resolution_status"] = "cache_hit"
            cached["taxon_resolution_notes"] = (
                "Resolucion recuperada desde cache local reproducible. "
                + str(cached.get("taxon_resolution_notes", ""))
            ).strip()
            cached["timestamp_utc"] = _utc_now()
            return cached

    if normalized_mode == "api_stub":
        resolved = _resolve_taxon_api_stub(project_root, organism_name, strain, config)
    elif normalized_mode == "online_optional":
        if bool(config["taxonomy"]["external_api_enabled"]):
            resolved = _resolve_taxon_online(project_root, organism_name, strain, config)
        else:
            resolved = _resolve_taxon_local(project_root, organism_name, strain)
            resolved["resolution_mode_used"] = "online_optional"
            resolved["fallback_reason"] = "external_api_disabled"
            resolved["taxon_resolution_status"] = "online_disabled_fallback_local"
            resolved["taxon_resolution_notes"] += " API real deshabilitada por configuracion; se uso catalogo local."
    elif normalized_mode == "auto":
        if bool(config["taxonomy"]["external_api_enabled"]):
            resolved = _resolve_taxon_online(project_root, organism_name, strain, config)
            resolved["resolution_mode_used"] = "auto"
        else:
            resolved = _resolve_taxon_local(project_root, organism_name, strain)
            resolved["resolution_mode_used"] = "auto"
            resolved["fallback_reason"] = "external_api_disabled"
            resolved["taxon_resolution_notes"] += " Modo auto en offline: se uso solo catalogo local."
    else:
        resolved = _resolve_taxon_local(project_root, organism_name, strain)
        resolved["resolution_mode_used"] = normalized_mode

    if normalized_mode == "offline_only":
        resolved["api_attempted"] = False
        resolved["api_success"] = False

    if not no_write_cache:
        _cache_result(cache, cache_key, resolved)
        _save_taxon_cache(project_root, config, cache)
    return resolved


def expected_datasets() -> list[dict[str, Any]]:
    dataset_rows: list[dict[str, Any]] = []
    for spec in DATASET_SPECS:
        if spec.required:
            category = "required"
        else:
            category = "optional_enriching"
        dataset_rows.append(
            {
                "filename": spec.filename,
                "table_key": spec.table_key,
                "category": category,
                "required": spec.required,
                "schema_required_columns": SCHEMAS[spec.table_key].required,
                "schema_optional_columns": SCHEMAS[spec.table_key].optional,
            }
        )
    dataset_rows.extend(FUTURE_DATASETS)
    return dataset_rows


def default_workspace(project_root: Path, organism_slug: str) -> Path:
    return project_root / "data_sessions" / organism_slug


def ensure_workspace_layout(workspace: Path) -> None:
    for relative in ["config", "data_raw", "data_processed", "results"]:
        (workspace / relative).mkdir(parents=True, exist_ok=True)


def initialize_workspace_config(project_root: Path, workspace: Path) -> Path:
    source = project_root / "config" / "params.yaml"
    target = workspace / "config" / "params.yaml"
    if not target.exists():
        shutil.copy2(source, target)
    return target


def _template_name(filename: str) -> str:
    stem = Path(filename).stem
    return f"{stem}_template.csv"


def _copy_template_if_missing(project_root: Path, workspace: Path, filename: str) -> None:
    raw_target = workspace / "data_raw" / filename
    if raw_target.exists():
        return
    template = project_root / "data_templates" / _template_name(filename)
    if template.exists():
        shutil.copy2(template, raw_target)


def _demo_match(project_root: Path, taxon_profile: dict[str, Any]) -> dict[str, Any] | None:
    demo_catalog = _load_catalog(project_root, "demo_organisms.json")
    canonical_name = taxon_profile["organism_canonical_name"]
    strain = taxon_profile.get("strain_canonical")
    for entry in demo_catalog["entries"]:
        entry_strain = entry.get("strain")
        if entry["canonical_name"] != canonical_name:
            continue
        if entry_strain and strain and entry_strain != strain:
            continue
        if entry_strain and not strain:
            continue
        return entry
    return None


def _copy_packaged_demo_data(project_root: Path, workspace: Path, demo_entry: dict[str, Any]) -> list[str]:
    copied = []
    for filename in demo_entry["files"]:
        demo_source = project_root / "data_demo" / filename
        legacy_source = project_root / "data_raw" / filename
        source = demo_source if demo_source.exists() else legacy_source
        target = workspace / "data_raw" / filename
        target_is_empty_template = False
        if target.exists():
            try:
                target_is_empty_template = len(target.read_text(encoding="utf-8").splitlines()) <= 1
            except UnicodeDecodeError:
                target_is_empty_template = False
        if source.exists() and (not target.exists() or target_is_empty_template):
            shutil.copy2(source, target)
            copied.append(filename)
    return copied


def _detect_dataset_state(raw_path: Path, table_key: str, config: dict[str, Any]) -> dict[str, Any]:
    state = {
        "present": raw_path.exists(),
        "usable": False,
        "row_count": 0,
        "declared_database": [],
        "source_type": "missing",
        "status": "missing",
        "notes": "",
    }
    if not raw_path.exists():
        return state

    try:
        df = pd.read_csv(raw_path)
    except Exception as exc:
        state["status"] = "invalid_csv"
        state["notes"] = str(exc)
        return state

    state["row_count"] = len(df)
    if df.empty:
        state["status"] = "template_or_empty"
        state["notes"] = "Archivo presente sin filas de datos."
        return state

    schema = SCHEMAS.get(table_key)
    if schema:
        missing_columns = [column for column in schema.required if column not in df.columns]
        if missing_columns:
            state["status"] = "schema_incomplete"
            state["notes"] = f"Faltan columnas requeridas: {missing_columns}"
            return state

    databases = []
    if "database" in df.columns:
        databases = sorted({str(item).strip() for item in df["database"].dropna().tolist() if str(item).strip()})
    state["declared_database"] = databases

    provenance_cfg = config["provenance"]
    if databases:
        source_type = "unknown"
        database_type_overrides = {str(k).lower(): str(v) for k, v in provenance_cfg["database_type_overrides"].items()}
        prefix_types = {str(k).lower(): str(v) for k, v in provenance_cfg["database_prefix_types"].items()}
        for database in databases:
            lowered = database.lower()
            if lowered in database_type_overrides:
                source_type = database_type_overrides[lowered]
                break
            for prefix, value in prefix_types.items():
                if lowered.startswith(prefix):
                    source_type = value
                    break
            if source_type != "unknown":
                break
    else:
        source_type = "undeclared"

    state["source_type"] = source_type
    state["usable"] = True
    state["status"] = "ready"
    state["notes"] = "Archivo listo para validacion."
    return state


def build_acquisition_manifest(
    project_root: Path,
    workspace: Path,
    taxon_profile: dict[str, Any],
    acquisition_mode: str,
    preferred_strategy: str | None,
    allow_demo_data: bool,
) -> dict[str, Any]:
    config = load_config(workspace / "config" / "params.yaml")
    existing_manifest_path = workspace / "results" / "acquisition_manifest.json"
    existing_entries: dict[str, Any] = {}
    if existing_manifest_path.exists():
        existing_manifest = _json_load(existing_manifest_path)
        existing_entries = {entry["filename"]: entry for entry in existing_manifest.get("datasets", [])}

    datasets = []
    missing_required = []
    warnings = []
    present_files = []

    for entry in expected_datasets():
        filename = entry["filename"]
        raw_path = workspace / "data_raw" / filename
        state = _detect_dataset_state(raw_path, entry["table_key"], config) if entry["table_key"] in SCHEMAS else {
            "present": raw_path.exists(),
            "usable": raw_path.exists(),
            "row_count": 0,
            "declared_database": [],
            "source_type": "missing" if not raw_path.exists() else "undeclared",
            "status": "missing" if not raw_path.exists() else "future_placeholder",
            "notes": "Dataset futuro no consumido por el motor actual.",
        }

        generated_by = existing_entries.get(filename, {}).get("generated_by", "user_provided" if state["present"] else "not_generated")
        dataset_entry = {
            "filename": filename,
            "table_key": entry["table_key"],
            "category": entry["category"],
            "required": bool(entry.get("required", False)),
            "path": str(raw_path),
            "present": state["present"],
            "usable": state["usable"],
            "row_count": state["row_count"],
            "status": state["status"],
            "source_type": state["source_type"],
            "declared_database": state["declared_database"],
            "generated_by": generated_by,
            "notes": state["notes"],
        }
        datasets.append(dataset_entry)
        if state["present"]:
            present_files.append(filename)
        if dataset_entry["required"] and not state["usable"]:
            missing_required.append(filename)
        if not allow_demo_data and state["source_type"] == "demo":
            warnings.append(f"{filename}: dataset demo detectado pero allow_demo_data=false")

    can_run_pipeline = not missing_required and not warnings
    completeness_status = "ready" if can_run_pipeline else ("partial" if present_files else "empty")

    manifest = {
        "organism_canonical_name": taxon_profile["organism_canonical_name"],
        "strain_canonical": taxon_profile.get("strain_canonical"),
        "taxon_id": taxon_profile.get("taxon_id"),
        "taxon_provider": taxon_profile.get("taxon_provider"),
        "source_used": taxon_profile.get("source_used"),
        "cache_hit": taxon_profile.get("cache_hit"),
        "api_attempted": taxon_profile.get("api_attempted"),
        "api_success": taxon_profile.get("api_success"),
        "taxon_resolution_status": taxon_profile.get("taxon_resolution_status"),
        "resolution_confidence": taxon_profile.get("resolution_confidence"),
        "fallback_reason": taxon_profile.get("fallback_reason"),
        "acquisition_mode": acquisition_mode,
        "preferred_strategy": preferred_strategy,
        "allow_demo_data": allow_demo_data,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "expected_dataset_count": len(datasets),
        "present_dataset_count": len(present_files),
        "missing_required_datasets": missing_required,
        "completeness_status": completeness_status,
        "can_run_pipeline": can_run_pipeline,
        "datasets": datasets,
        "warnings": warnings,
    }
    return manifest


def build_organism_profile(
    workspace: Path,
    taxon_profile: dict[str, Any],
    acquisition_mode: str,
    preferred_strategy: str | None,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        **taxon_profile,
        "workspace": str(workspace),
        "acquisition_mode": acquisition_mode,
        "preferred_strategy": preferred_strategy,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources_expected": [entry["filename"] for entry in manifest["datasets"]],
        "sources_present": [entry["filename"] for entry in manifest["datasets"] if entry["present"]],
        "completeness_status": manifest["completeness_status"],
        "warnings": manifest["warnings"],
        "associated_paths": {
            "raw_dir": str(workspace / "data_raw"),
            "processed_dir": str(workspace / "data_processed"),
            "results_dir": str(workspace / "results"),
            "manifest_path": str(workspace / "results" / "acquisition_manifest.json"),
        },
    }


def write_discovery_report(workspace: Path, profile: dict[str, Any], manifest: dict[str, Any]) -> Path:
    report_path = workspace / "results" / "discovery_report.md"
    lines = [
        "# Discovery Report",
        "",
        "## Organism Resolution",
        f"- Input organism: `{profile['organism_input_name']}`",
        f"- Canonical organism: `{profile['organism_canonical_name']}`",
        f"- Input strain: `{profile.get('strain_input') or 'none'}`",
        f"- Canonical strain: `{profile.get('strain_canonical') or 'none'}`",
        f"- Taxon id: `{profile.get('taxon_id') or 'none'}`",
        f"- Rank: `{profile.get('rank') or 'unknown'}`",
        f"- Provider: `{profile.get('taxon_provider') or 'unknown'}`",
        f"- Source used: `{profile.get('source_used') or 'unknown'}`",
        f"- Cache hit: `{profile.get('cache_hit')}`",
        f"- API attempted: `{profile.get('api_attempted')}`",
        f"- API success: `{profile.get('api_success')}`",
        f"- Fallback reason: `{profile.get('fallback_reason') or 'none'}`",
        f"- Resolution confidence: `{profile.get('resolution_confidence')}`",
        f"- Resolution status: `{profile['taxon_resolution_status']}`",
        f"- Resolution notes: {profile['taxon_resolution_notes']}",
        "",
        "## Workspace",
        f"- Workspace: `{workspace}`",
        f"- Acquisition mode: `{profile['acquisition_mode']}`",
        f"- Preferred strategy: `{profile.get('preferred_strategy') or 'not specified'}`",
        f"- Completeness: `{manifest['completeness_status']}`",
        f"- Can run pipeline: `{manifest['can_run_pipeline']}`",
        "",
        "## Datasets",
        "",
        "| filename | category | required | status | source_type | generated_by | row_count |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for dataset in manifest["datasets"]:
        lines.append(
            f"| {dataset['filename']} | {dataset['category']} | {dataset['required']} | {dataset['status']} | {dataset['source_type']} | {dataset['generated_by']} | {dataset['row_count']} |"
        )
    lines.extend(
        [
            "",
            "## Warnings",
        ]
    )
    if manifest["warnings"]:
        lines.extend([f"- {warning}" for warning in manifest["warnings"]])
    else:
        lines.append("- none")
    if manifest["missing_required_datasets"]:
        lines.extend(
            [
                "",
                "## Missing Required Datasets",
                *[f"- {item}" for item in manifest["missing_required_datasets"]],
            ]
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def prepare_discovery_workspace(
    project_root: Path,
    organism_name: str,
    strain: str | None = None,
    strategy: str | None = None,
    acquisition_mode: str = "semi_auto",
    workspace: str | Path | None = None,
    allow_demo_data: bool = False,
    dry_run: bool = False,
    taxon_resolution_mode: str | None = None,
    refresh_taxon_cache: bool = False,
    no_write_taxon_cache: bool = False,
) -> dict[str, Any]:
    if acquisition_mode not in ACQUISITION_MODES:
        raise ValueError(f"acquisition_mode no soportado: {acquisition_mode}")
    if strategy and strategy not in STRATEGY_CHOICES:
        raise ValueError(f"strategy no soportada: {strategy}")
    config = load_config(project_root / "config" / "params.yaml")
    resolution_mode = _normalize_resolution_mode(
        taxon_resolution_mode or str(config["taxonomy"]["resolution_mode_default"]),
        config,
    )

    taxon_profile = resolve_taxon(
        project_root,
        organism_name,
        strain,
        resolution_mode=resolution_mode,
        config=config,
        refresh_cache=refresh_taxon_cache,
        no_write_cache=no_write_taxon_cache,
    )
    workspace_path = Path(workspace) if workspace else default_workspace(project_root, taxon_profile["organism_slug"])
    ensure_workspace_layout(workspace_path)
    initialize_workspace_config(project_root, workspace_path)

    template_files = []
    if acquisition_mode in {"semi_auto", "auto"}:
        for spec in DATASET_SPECS:
            _copy_template_if_missing(project_root, workspace_path, spec.filename)
            template_files.append(spec.filename)

    demo_files = []
    warnings = []
    if acquisition_mode == "auto":
        warnings.append("Modo auto sin conectores reales: se comporta como semi_auto salvo que exista un demo empaquetado compatible.")
    demo_entry = _demo_match(project_root, taxon_profile)
    if allow_demo_data and demo_entry is not None:
        demo_files = _copy_packaged_demo_data(project_root, workspace_path, demo_entry)
        warnings.append(demo_entry["notes"])
    elif allow_demo_data and demo_entry is None:
        warnings.append("allow_demo_data=true, pero no hay demo empaquetado para este microorganismo/cepa.")

    manifest = build_acquisition_manifest(
        project_root=project_root,
        workspace=workspace_path,
        taxon_profile=taxon_profile,
        acquisition_mode=acquisition_mode,
        preferred_strategy=strategy,
        allow_demo_data=allow_demo_data,
    )

    demo_files_set = set(demo_files)
    for dataset in manifest["datasets"]:
        if dataset["filename"] in demo_files_set:
            dataset["generated_by"] = "packaged_demo"
            dataset["source_type"] = "demo"
            if dataset["status"] == "ready":
                dataset["notes"] = "Dataset copiado desde el demo empaquetado del repositorio."

    for warning in warnings:
        if warning not in manifest["warnings"]:
            manifest["warnings"].append(warning)
    manifest["taxon_resolution_mode"] = resolution_mode
    manifest["refresh_taxon_cache"] = refresh_taxon_cache
    manifest["no_write_taxon_cache"] = no_write_taxon_cache
    manifest["template_files"] = template_files
    manifest["demo_files_copied"] = demo_files
    if warnings and not manifest["can_run_pipeline"] and "warnings" in manifest:
        pass
    _json_dump(workspace_path / "results" / "acquisition_manifest.json", manifest)

    profile = build_organism_profile(
        workspace=workspace_path,
        taxon_profile=taxon_profile,
        acquisition_mode=acquisition_mode,
        preferred_strategy=strategy,
        manifest=manifest,
    )
    _json_dump(workspace_path / "results" / "organism_profile.json", profile)
    report_path = write_discovery_report(workspace_path, profile, manifest)

    return {
        "workspace": workspace_path,
        "profile_path": workspace_path / "results" / "organism_profile.json",
        "manifest_path": workspace_path / "results" / "acquisition_manifest.json",
        "report_path": report_path,
        "profile": profile,
        "manifest": manifest,
        "dry_run": dry_run,
    }
