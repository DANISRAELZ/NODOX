from __future__ import annotations

import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


SOURCE_MODES = {"offline_only", "cache_first", "online_optional"}
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


def _request_json(url: str, timeout: float, user_agent: str) -> Any:
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json,text/tab-separated-values,*/*"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass
    text = raw.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _api_get_json(url: str, cfg: dict[str, Any]) -> tuple[Any | None, list[str]]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            return _request_json(url, timeout=timeout, user_agent=user_agent), errors
        except HTTPError as exc:
            errors.append(f"HTTP {exc.code} en VFDB")
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff)
                continue
            break
        except URLError as exc:
            errors.append(f"Error de red en VFDB: {exc.reason}")
            break
        except TimeoutError:
            errors.append("Timeout en VFDB")
            break
        except UnicodeDecodeError as exc:
            errors.append(f"Respuesta no decodificable de VFDB: {exc}")
            break
    return None, errors


def _get_candidate_proteins(workspace: Path) -> pd.DataFrame:
    path = workspace / "data_raw" / "virulence.csv"
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
        else:
            rows.append({"protein_id": protein_id, "gene": gene, "virulence_score": 0.0, "virulence_factor": 0, "database": str(config["online_sources"]["vfdb"]["database_label"])})
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
    if mode not in SOURCE_MODES:
        raise ValueError(f"online source mode no soportado: {mode}")
    workspace = Path(workspace)
    proteins = _get_candidate_proteins(workspace)
    cache = load_vfdb_cache(workspace, config)
    cache_key = _cache_key(taxon_id, proteins)
    cfg = config["online_sources"]["vfdb"]

    if not refresh_cache and cache["entries"].get(cache_key):
        entry = cache["entries"][cache_key]
        df = pd.DataFrame(entry.get("virulence_rows", []), columns=VIRULENCE_COLUMNS)
        manifest = _cache_manifest(entry.get("manifest", {}), mode)
        return {"virulence_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
    if mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache VFDB utilizable para este conjunto de proteinas.")
    if proteins.empty:
        manifest = {"source": "vfdb", "provider": str(cfg["provider_name"]), "mode": mode, "organism_name": organism_name, "taxon_id": taxon_id, "query_cache_key": cache_key, "proteins_queried": 0, "protein_count_mapped": 0, "source_used": "empty_candidates", "cache_hit": False, "api_attempted": False, "api_success": False, "fallback_reason": "no_candidate_proteins", "notes": ["no_candidate_proteins"], "generated_at_utc": _utc_now()}
        return {"virulence_data": pd.DataFrame(columns=VIRULENCE_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    payload, errors = _api_get_json(str(cfg["provider_base_url"]).rstrip("/") + "/VFs.tsv.gz", cfg)
    if payload is None:
        if mode == "online_optional" and cache["entries"].get(cache_key):
            entry = cache["entries"][cache_key]
            df = pd.DataFrame(entry.get("virulence_rows", []), columns=VIRULENCE_COLUMNS)
            manifest = _cache_manifest(entry.get("manifest", {}), mode)
            manifest["api_attempted"] = True
            manifest["fallback_reason"] = "api_failed_fallback_cache"
            return {"virulence_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
        manifest = {"source": "vfdb", "provider": str(cfg["provider_name"]), "mode": mode, "organism_name": organism_name, "taxon_id": taxon_id, "query_cache_key": cache_key, "proteins_queried": int(len(proteins)), "protein_count_mapped": 0, "source_used": "api_failed", "cache_hit": False, "api_attempted": True, "api_success": False, "fallback_reason": "api_failed_no_cache", "notes": errors, "generated_at_utc": _utc_now()}
        return {"virulence_data": pd.DataFrame(columns=VIRULENCE_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    df, matched = _derive_rows(proteins, payload, config)
    manifest = {"source": "vfdb", "provider": str(cfg["provider_name"]), "mode": mode, "organism_name": organism_name, "taxon_id": taxon_id, "query_cache_key": cache_key, "proteins_queried": int(len(proteins)), "protein_count_mapped": int(matched), "source_used": "api_real" if matched else "vfdb_filtered_no_matches", "cache_hit": False, "api_attempted": True, "api_success": True, "fallback_reason": None if matched else "no_vfdb_matches_for_workspace_candidates", "notes": errors, "generated_at_utc": _utc_now()}
    if not no_write_cache:
        cache["entries"][cache_key] = {"saved_at_utc": _utc_now(), "virulence_rows": df.to_dict(orient="records"), "manifest": manifest}
        save_vfdb_cache(workspace, config, cache)
    return {"virulence_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
