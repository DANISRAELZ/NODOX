from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from .provider_response_audit import ProviderResponse, request_provider_payload, response_audit_fields


SOURCE_MODES = {"offline_only", "cache_first", "online_optional"}
ESSENTIALITY_COLUMNS = ["protein_id", "gene", "essential", "evidence", "database"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(config["online_sources"]["deg"]["cache_filename"])


def load_deg_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload = _json_load(path)
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_deg_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def _api_get_json(url: str, cfg: dict[str, Any]) -> tuple[Any | None, list[str], ProviderResponse | None]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        response = request_provider_payload(url, timeout=timeout, user_agent=user_agent, accept="application/json,text/plain,*/*", opener=urlopen)
        if response.error_status == "":
            return response.payload, errors, response
        errors.append(response.rejection_reason or response.error_status)
        if response.http_status == 429 and attempt < retries:
            time.sleep(backoff)
            continue
        return None, errors, response
    return None, errors, None


def _get_candidate_proteins(workspace: Path) -> pd.DataFrame:
    path = workspace / "data_raw" / "essentiality.csv"
    if not path.exists():
        return pd.DataFrame(columns=["protein_id", "gene"])
    df = pd.read_csv(path)
    if "protein_id" not in df.columns:
        return pd.DataFrame(columns=["protein_id", "gene"])
    rows = []
    for _, row in df.iterrows():
        protein_id = str(row.get("protein_id", "")).strip().upper()
        if not protein_id:
            continue
        gene = str(row.get("gene", "")).strip() or protein_id
        rows.append({"protein_id": protein_id, "gene": gene})
    return pd.DataFrame(rows).drop_duplicates(subset=["protein_id"]).sort_values("protein_id").reset_index(drop=True)


def _cache_key(taxon_id: str | None, proteins: pd.DataFrame) -> str:
    ids = "|".join(sorted(proteins["protein_id"].astype(str).str.upper().tolist()))
    digest = hashlib.sha256(ids.encode("utf-8")).hexdigest()[:16]
    return f"deg::{taxon_id or 'unknown'}::{digest}"


def _build_query_url(organism_name: str, taxon_id: str | None, cfg: dict[str, Any]) -> str:
    params = {"query": taxon_id or organism_name, "format": "json"}
    return f"{str(cfg['provider_base_url']).rstrip('/')}?{urlencode(params)}"


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


def _is_structured_deg_payload(payload: Any, response: ProviderResponse | None) -> bool:
    if response is None:
        return False
    if response.payload_type != "json":
        return False
    return bool(_as_records(payload))


def _conservative_status(response: ProviderResponse | None) -> str:
    if response is None:
        return "unresolved"
    if response.payload_type == "html":
        return "html_instead_of_structured_payload"
    if response.error_status == "not_found":
        return "not_found"
    if response.error_status:
        return response.error_status
    if response.payload_type == "zip":
        return "unsupported_structured_archive"
    if response.payload_type in {"empty", "unexpected_text", "tabular_text"}:
        return "unresolved"
    return "unresolved"


def _record_tokens(record: dict[str, Any]) -> set[str]:
    keys = ["protein_id", "protein", "locus_tag", "gene", "gene_name", "deg_id"]
    return {str(record.get(key, "")).strip().casefold() for key in keys if str(record.get(key, "")).strip()}


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
            evidence = str(match.get("evidence") or match.get("experiment") or match.get("method") or "deg_match").strip()
            rows.append(
                {
                    "protein_id": protein_id,
                    "gene": gene,
                    "essential": 1,
                    "evidence": evidence,
                    "database": str(config["online_sources"]["deg"]["database_label"]),
                }
            )
        else:
            rows.append(
                {
                    "protein_id": protein_id,
                    "gene": gene,
                    "essential": 0,
                    "evidence": "not_in_deg",
                    "database": str(config["online_sources"]["deg"]["database_label"]),
                }
            )
    return pd.DataFrame(rows, columns=ESSENTIALITY_COLUMNS), matched


def _write_manifest(workspace: Path, manifest: dict[str, Any]) -> Path:
    path = workspace / "results" / "deg_essentiality_manifest.json"
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


def fetch_deg_essentiality(
    workspace: Path,
    organism_name: str,
    taxon_id: str | None,
    config: dict[str, Any],
    mode: str,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
) -> dict[str, Any]:
    if mode not in SOURCE_MODES:
        raise ValueError(f"online source mode no soportado: {mode}")
    workspace = Path(workspace)
    proteins = _get_candidate_proteins(workspace)
    cache = load_deg_cache(workspace, config)
    cache_key = _cache_key(taxon_id, proteins)
    cfg = config["online_sources"]["deg"]

    if not refresh_cache and mode in SOURCE_MODES and cache["entries"].get(cache_key):
        entry = cache["entries"][cache_key]
        df = pd.DataFrame(entry.get("essentiality_rows", []), columns=ESSENTIALITY_COLUMNS)
        manifest = _cache_manifest(entry.get("manifest", {}), mode)
        return {"essentiality_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    if mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache DEG utilizable para este conjunto de proteinas.")

    if proteins.empty:
        manifest = {
            "source": "deg",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "organism_name": organism_name,
            "taxon_id": taxon_id,
            "query_cache_key": cache_key,
            "proteins_queried": 0,
            "protein_count_mapped": 0,
            "source_used": "empty_candidates",
            "cache_hit": False,
            "api_attempted": False,
            "api_success": False,
            "fallback_reason": "no_candidate_proteins",
            "notes": ["no_candidate_proteins"],
            "generated_at_utc": _utc_now(),
        }
        return {"essentiality_data": pd.DataFrame(columns=ESSENTIALITY_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    provider_url = _build_query_url(organism_name, taxon_id, cfg)
    payload, errors, response = _api_get_json(provider_url, cfg)
    if payload is None:
        if mode == "online_optional" and cache["entries"].get(cache_key):
            entry = cache["entries"][cache_key]
            df = pd.DataFrame(entry.get("essentiality_rows", []), columns=ESSENTIALITY_COLUMNS)
            manifest = _cache_manifest(entry.get("manifest", {}), mode)
            manifest["api_attempted"] = True
            manifest["fallback_reason"] = "api_failed_fallback_cache"
            return {"essentiality_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
        audit = response_audit_fields(response, affects_score=False) if response else {"provider_url": provider_url, "affects_score": False}
        manifest = {
            "source": "deg",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "organism_name": organism_name,
            "taxon_id": taxon_id,
            "query_cache_key": cache_key,
            "proteins_queried": int(len(proteins)),
            "protein_count_mapped": 0,
            "source_used": "api_failed",
            "retrieval_status": _conservative_status(response),
            "cache_hit": False,
            "api_attempted": True,
            "api_success": False,
            "fallback_reason": "api_failed_no_cache",
            "notes": errors,
            "generated_at_utc": _utc_now(),
            **audit,
        }
        return {"essentiality_data": pd.DataFrame(columns=ESSENTIALITY_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    if not _is_structured_deg_payload(payload, response):
        audit = response_audit_fields(response, affects_score=False) if response else {"provider_url": provider_url, "affects_score": False}
        status = _conservative_status(response)
        reason = audit.get("rejection_reason") or "structured_deg_payload_not_verified"
        manifest = {
            "source": "deg",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "organism_name": organism_name,
            "taxon_id": taxon_id,
            "query_cache_key": cache_key,
            "proteins_queried": int(len(proteins)),
            "protein_count_mapped": 0,
            "source_used": status,
            "retrieval_status": status,
            "cache_hit": False,
            "api_attempted": True,
            "api_success": False,
            "fallback_reason": reason,
            "notes": errors + [str(reason), "No essentiality evidence was inferred from this provider response."],
            "generated_at_utc": _utc_now(),
            **audit,
        }
        return {"essentiality_data": pd.DataFrame(columns=ESSENTIALITY_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    df, matched = _derive_rows(proteins, payload, config)
    audit = response_audit_fields(response, affects_score=False) if response else {"provider_url": provider_url, "affects_score": False}
    manifest = {
        "source": "deg",
        "provider": str(cfg["provider_name"]),
        "mode": mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "query_cache_key": cache_key,
        "proteins_queried": int(len(proteins)),
        "protein_count_mapped": int(matched),
        "source_used": "api_real" if matched else "deg_local_lookup_no_matches",
        "retrieval_status": "api_real" if matched else "not_found",
        "cache_hit": False,
        "api_attempted": True,
        "api_success": True,
        "fallback_reason": None if matched else "no_deg_matches_for_workspace_candidates",
        "notes": errors,
        "generated_at_utc": _utc_now(),
        **audit,
    }
    if not no_write_cache:
        cache["entries"][cache_key] = {"saved_at_utc": _utc_now(), "essentiality_rows": df.to_dict(orient="records"), "manifest": manifest}
        save_deg_cache(workspace, config, cache)
    return {"essentiality_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
