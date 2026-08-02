from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .online.provider_modes import normalize_provider_mode

VIRULENCE_COLUMNS = ["protein_id", "gene", "virulence_score", "virulence_factor", "database"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(config["online_sources"]["vfdb"]["cache_filename"])


def load_vfdb_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_vfdb_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def _get_candidate_proteins(workspace: Path) -> pd.DataFrame:
    for filename in ["virulence.csv", "essentiality.csv"]:
        path = workspace / "data_raw" / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "protein_id" not in df.columns:
            continue
        rows = []
        for _, row in df.iterrows():
            protein_id = str(row.get("protein_id", "")).strip().upper()
            if not protein_id:
                continue
            gene = str(row.get("gene", "")).strip() or protein_id
            rows.append({"protein_id": protein_id, "gene": gene})
        if rows:
            return pd.DataFrame(rows).drop_duplicates(subset=["protein_id"]).sort_values("protein_id").reset_index(drop=True)
    return pd.DataFrame(columns=["protein_id", "gene"])


def _resolve_local_dataset_path(workspace: Path, cfg: dict[str, Any], key: str) -> Path:
    configured = Path(str(cfg[key]))
    return configured if configured.is_absolute() else workspace / configured


def _read_local_dataset(path: Path) -> pd.DataFrame:
    if not path.exists() or not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, sep=None, engine="python")


def _dataset_version(workspace: Path, cfg: dict[str, Any]) -> str:
    path = _resolve_local_dataset_path(workspace, cfg, "local_dataset_version_path")
    if not path.exists():
        return "not_recorded"
    value = path.read_text(encoding="utf-8", errors="replace").strip()
    return value[:300] or "not_recorded"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _filter_records_for_context(
    records: pd.DataFrame,
    organism_name: str,
    taxon_id: str | None,
) -> pd.DataFrame:
    if records.empty:
        return records
    for column in ["taxon_id", "taxonomy_id", "ncbi_taxon_id"]:
        if column in records.columns and taxon_id:
            return records[records[column].fillna("").astype(str).str.strip().eq(str(taxon_id))].copy()
    for column in ["organism", "organism_name", "species", "strain"]:
        if column in records.columns and organism_name:
            expected = organism_name.strip().casefold()
            values = records[column].fillna("").astype(str).str.strip().str.casefold()
            return records[values.map(lambda value: bool(value) and (expected in value or value in expected))].copy()
    return records


def _cache_key(taxon_id: str | None, proteins: pd.DataFrame) -> str:
    ids = "|".join(sorted(proteins["protein_id"].astype(str).str.upper().tolist()))
    digest = hashlib.sha256(ids.encode("utf-8")).hexdigest()[:16]
    return f"vfdb::{taxon_id or 'unknown'}::{digest}"


def _as_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ["results", "data", "records", "entries"]:
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, str):
        rows = []
        lines = [line for line in payload.splitlines() if line.strip()]
        if len(lines) < 2:
            return rows
        header = [item.strip().lower() for item in lines[0].split("\t")]
        for line in lines[1:]:
            values = line.split("\t")
            rows.append({header[idx]: values[idx] for idx in range(min(len(header), len(values)))})
        return rows
    return []


def _record_tokens(record: dict[str, Any]) -> set[str]:
    keys = ["protein_id", "protein", "locus_tag", "gene", "gene_name", "vf_id"]
    return {str(record.get(key, "")).strip().casefold() for key in keys if str(record.get(key, "")).strip()}


def _category_score(record: dict[str, Any]) -> float:
    raw = str(record.get("category") or record.get("vfcategory") or record.get("function") or "").casefold()
    if any(token in raw for token in ["toxin", "secretion", "adhesin", "invasion"]):
        return 1.0
    if any(token in raw for token in ["regulation", "biofilm", "motility"]):
        return 0.8
    value = pd.to_numeric(pd.Series([record.get("virulence_score") or record.get("score")]), errors="coerce").iloc[0]
    if pd.notna(value):
        return max(0.0, min(1.0, float(value)))
    return 0.7


def _derive_rows(proteins: pd.DataFrame, payload: Any, config: dict[str, Any]) -> tuple[pd.DataFrame, int]:
    records = _as_records(payload)
    record_tokens = [(record, _record_tokens(record)) for record in records]
    rows = []
    matched = 0
    for _, protein in proteins.iterrows():
        protein_id = str(protein["protein_id"]).strip().upper()
        gene = str(protein["gene"]).strip()
        tokens = {protein_id.casefold(), gene.casefold()}
        match = next((record for record, record_ids in record_tokens if tokens & record_ids), None)
        if match:
            matched += 1
            score = _category_score(match)
            rows.append({"protein_id": protein_id, "gene": gene, "virulence_score": score, "virulence_factor": 1, "database": str(config["online_sources"]["vfdb"]["database_label"])})
    return pd.DataFrame(rows, columns=VIRULENCE_COLUMNS), matched


def _write_manifest(workspace: Path, manifest: dict[str, Any]) -> Path:
    path = workspace / "results" / "vfdb_virulence_manifest.json"
    _json_dump(path, manifest)
    return path


def _cache_manifest(cached_manifest: dict[str, Any], mode: str) -> dict[str, Any]:
    manifest = {**cached_manifest}
    manifest.update({"mode": mode, "source_used": "cache", "cache_hit": True, "api_attempted": False, "api_success": False})
    notes = list(manifest.get("notes", []))
    if "served_from_cache" not in notes:
        notes.append("served_from_cache")
    manifest["notes"] = notes
    return manifest


def fetch_vfdb_virulence(
    workspace: Path,
    organism_name: str,
    taxon_id: str | None,
    config: dict[str, Any],
    mode: str,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
) -> dict[str, Any]:
    mode = normalize_provider_mode(mode, config)
    workspace = Path(workspace)
    cfg = config["online_sources"]["vfdb"]
    proteins = _get_candidate_proteins(workspace)
    dataset_path = _resolve_local_dataset_path(workspace, cfg, "local_dataset_path")
    dataset_checksum = _sha256(dataset_path) if dataset_path.exists() and dataset_path.is_file() else ""
    cache = load_vfdb_cache(workspace, config)
    cache_key = f"{_cache_key(taxon_id, proteins)}::{dataset_checksum[:16] or 'missing'}"

    if not bool(cfg.get("enabled", True)):
        manifest = {
            "source": "vfdb",
            "provider": str(cfg["provider_name"]),
            "provider_name": str(cfg["provider_name"]),
            "provider_mode": "local_dataset",
            "mode": mode,
            "organism_name": organism_name,
            "taxon_id": taxon_id,
            "query_cache_key": cache_key,
            "proteins_queried": int(len(proteins)),
            "protein_count_mapped": 0,
            "source_used": "provider_disabled",
            "retrieval_status": "provider_disabled",
            "cache_hit": False,
            "provider_attempted": False,
            "provider_success": False,
            "api_attempted": False,
            "api_success": False,
            "fallback_reason": "provider_disabled_by_run_configuration",
            "evidence_level": "unresolved",
            "affects_score": False,
            "notes": ["provider_disabled_before_local_dataset_lookup"],
            "generated_at_utc": _utc_now(),
        }
        return {
            "virulence_data": pd.DataFrame(columns=VIRULENCE_COLUMNS),
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    if not refresh_cache and cache["entries"].get(cache_key):
        entry = cache["entries"][cache_key]
        df = pd.DataFrame(entry.get("virulence_rows", []), columns=VIRULENCE_COLUMNS)
        manifest = _cache_manifest(entry.get("manifest", {}), mode)
        return {"virulence_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
    if proteins.empty:
        status = "empty_candidates"
        fallback_reason = "no_candidate_proteins"
        records = pd.DataFrame()
    elif not dataset_path.exists():
        status = "local_dataset_missing"
        fallback_reason = "vfdb_requires_versioned_local_dataset"
        records = pd.DataFrame()
    else:
        try:
            records = _filter_records_for_context(
                _read_local_dataset(dataset_path),
                organism_name,
                taxon_id,
            )
        except Exception as exc:  # noqa: BLE001 - invalid local data remains non-blocking.
            status = "local_dataset_invalid"
            fallback_reason = f"local_dataset_parse_error:{type(exc).__name__}"
            records = pd.DataFrame()
        else:
            has_identifiers = any(_record_tokens(row) for row in records.to_dict(orient="records"))
            if records.empty:
                status = "local_dataset_empty_for_organism"
                fallback_reason = "no_vfdb_records_for_requested_organism"
            elif not has_identifiers:
                status = "local_dataset_invalid"
                fallback_reason = "vfdb_dataset_missing_supported_identifier_columns"
            else:
                status = "local_dataset_available"
                fallback_reason = ""

    df, matched = (
        _derive_rows(proteins, records.to_dict(orient="records"), config)
        if status == "local_dataset_available"
        else (pd.DataFrame(columns=VIRULENCE_COLUMNS), 0)
    )
    retrieval_status = "local_dataset_available" if matched else (
        "local_dataset_no_candidate_matches" if status == "local_dataset_available" else status
    )
    manifest = {
        "source": "vfdb",
        "provider": str(cfg["provider_name"]),
        "provider_name": str(cfg["provider_name"]),
        "provider_mode": "local_dataset",
        "mode": mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "query_cache_key": cache_key,
        "proteins_queried": int(len(proteins)),
        "records_retrieved": int(len(records)),
        "protein_count_mapped": int(matched),
        "source_used": "local_dataset" if status == "local_dataset_available" else status,
        "retrieval_status": retrieval_status,
        "cache_hit": False,
        "provider_attempted": bool(proteins.empty is False),
        "provider_success": status == "local_dataset_available",
        "api_attempted": False,
        "api_success": False,
        "fallback_reason": fallback_reason or (None if matched else "no_vfdb_matches_for_workspace_candidates"),
        "evidence_level": "curated_external_dataset" if matched else "unresolved",
        "data_realism_flag": "external_real" if matched else "unresolved",
        "local_dataset_path": str(dataset_path),
        "dataset_version": _dataset_version(workspace, cfg) if dataset_path.exists() else "not_available",
        "checksum_sha256": dataset_checksum,
        "affects_score": False,
        "notes": [
            "VFDB is read only from a user-supplied, versioned local dataset; no portal scraping is attempted.",
            "Candidates absent from the dataset remain unresolved and are not emitted as virulence_factor=0.",
        ],
        "generated_at_utc": _utc_now(),
    }
    if not no_write_cache:
        cache["entries"][cache_key] = {"saved_at_utc": _utc_now(), "virulence_rows": df.to_dict(orient="records"), "manifest": manifest}
        save_vfdb_cache(workspace, config, cache)
    return {"virulence_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
