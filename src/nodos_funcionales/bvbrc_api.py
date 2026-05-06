from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd


SOURCE_MODES = {"offline_only", "cache_first", "online_optional"}
CONSERVATION_COLUMNS = ["protein_id", "gene", "core_genome_presence", "strain_coverage_score", "allelic_conservation", "variant_burden", "database"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(config["online_sources"]["bvbrc"]["cache_filename"])


def load_bvbrc_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_bvbrc_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def _request_json(url: str, timeout: float, user_agent: str) -> Any:
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


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
            errors.append(f"HTTP {exc.code} en BV-BRC")
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff)
                continue
            break
        except URLError as exc:
            errors.append(f"Error de red en BV-BRC: {exc.reason}")
            break
        except TimeoutError:
            errors.append("Timeout en BV-BRC")
            break
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"Respuesta JSON invalida de BV-BRC: {exc}")
            break
    return None, errors


def _get_candidate_proteins(workspace: Path) -> pd.DataFrame:
    for filename in ["strain_conservation.csv", "essentiality.csv"]:
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


def _cache_key(taxon_id: str | None, proteins: pd.DataFrame) -> str:
    ids = "|".join(sorted(proteins["protein_id"].astype(str).str.upper().tolist()))
    digest = hashlib.sha256(ids.encode("utf-8")).hexdigest()[:16]
    return f"bvbrc::{taxon_id or 'unknown'}::{digest}"


def _build_query_url(taxon_id: str, cfg: dict[str, Any]) -> str:
    query = f"in(taxon_lineage_ids,({taxon_id}))&eq(feature_type,CDS)&select(patric_id,gene,pgfam_id,figfam_id,genome_id)"
    return f"{str(cfg['provider_base_url']).rstrip('/')}/genome_feature/?{quote(query, safe='(),=&')}"


def _as_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ["results", "data", "response", "records"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict) and isinstance(value.get("docs"), list):
                return [item for item in value["docs"] if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _derive_rows(proteins: pd.DataFrame, payload: Any, config: dict[str, Any]) -> tuple[pd.DataFrame, int, list[str]]:
    records = _as_records(payload)
    by_gene: dict[str, set[str]] = defaultdict(set)
    by_family: dict[str, set[str]] = defaultdict(set)
    genomes = set()
    for record in records:
        genome_id = str(record.get("genome_id") or "").strip()
        if genome_id:
            genomes.add(genome_id)
        gene = str(record.get("gene") or record.get("patric_id") or "").strip().casefold()
        if gene and genome_id:
            by_gene[gene].add(genome_id)
        family = str(record.get("pgfam_id") or record.get("figfam_id") or "").strip()
        if family and genome_id:
            by_family[gene or family.casefold()].add(family)
    total_genomes = max(len(genomes), 1)
    rows = []
    matched = 0
    for _, protein in proteins.iterrows():
        protein_id = str(protein["protein_id"]).strip().upper()
        gene = str(protein["gene"]).strip()
        present = by_gene.get(gene.casefold(), set()) | by_gene.get(protein_id.casefold(), set())
        if present:
            matched += 1
        presence = len(present) / total_genomes if present else 0.0
        family_count = len(by_family.get(gene.casefold(), set()) or by_family.get(protein_id.casefold(), set()))
        allelic = 0.5 if family_count <= 1 else max(0.0, 1.0 - min(1.0, (family_count - 1) / max(total_genomes, 1)))
        variant_burden = 0.5 if family_count <= 1 else max(0.0, min(1.0, 1.0 - allelic))
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "core_genome_presence": round(float(presence), 4),
                "strain_coverage_score": round(float(presence), 4),
                "allelic_conservation": round(float(allelic), 4),
                "variant_burden": round(float(variant_burden), 4),
                "database": str(config["online_sources"]["bvbrc"]["database_label"]),
            }
        )
    notes = ["variant_data_unavailable_defaults_used_for_single_family_rows"]
    return pd.DataFrame(rows, columns=CONSERVATION_COLUMNS), matched, notes


def _write_manifest(workspace: Path, manifest: dict[str, Any]) -> Path:
    path = workspace / "results" / "bvbrc_conservation_manifest.json"
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


def fetch_bvbrc_strain_conservation(
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
    cache = load_bvbrc_cache(workspace, config)
    cache_key = _cache_key(taxon_id, proteins)
    cfg = config["online_sources"]["bvbrc"]

    if not refresh_cache and cache["entries"].get(cache_key):
        entry = cache["entries"][cache_key]
        df = pd.DataFrame(entry.get("strain_conservation_rows", []), columns=CONSERVATION_COLUMNS)
        manifest = _cache_manifest(entry.get("manifest", {}), mode)
        return {"strain_conservation_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
    if mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache BV-BRC utilizable para este conjunto de proteinas.")
    if proteins.empty or not taxon_id:
        reason = "no_candidate_proteins" if proteins.empty else "missing_taxon_id"
        manifest = {"source": "bvbrc", "provider": str(cfg["provider_name"]), "mode": mode, "organism_name": organism_name, "taxon_id": taxon_id, "query_cache_key": cache_key, "proteins_queried": int(len(proteins)), "protein_count_mapped": 0, "source_used": "empty_candidates", "cache_hit": False, "api_attempted": False, "api_success": False, "fallback_reason": reason, "notes": [reason], "generated_at_utc": _utc_now()}
        return {"strain_conservation_data": pd.DataFrame(columns=CONSERVATION_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    payload, errors = _api_get_json(_build_query_url(taxon_id, cfg), cfg)
    if payload is None:
        if mode == "online_optional" and cache["entries"].get(cache_key):
            entry = cache["entries"][cache_key]
            df = pd.DataFrame(entry.get("strain_conservation_rows", []), columns=CONSERVATION_COLUMNS)
            manifest = _cache_manifest(entry.get("manifest", {}), mode)
            manifest["api_attempted"] = True
            manifest["fallback_reason"] = "api_failed_fallback_cache"
            return {"strain_conservation_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
        manifest = {"source": "bvbrc", "provider": str(cfg["provider_name"]), "mode": mode, "organism_name": organism_name, "taxon_id": taxon_id, "query_cache_key": cache_key, "proteins_queried": int(len(proteins)), "protein_count_mapped": 0, "source_used": "api_failed", "cache_hit": False, "api_attempted": True, "api_success": False, "fallback_reason": "api_failed_no_cache", "notes": errors, "generated_at_utc": _utc_now()}
        return {"strain_conservation_data": pd.DataFrame(columns=CONSERVATION_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    df, matched, notes = _derive_rows(proteins, payload, config)
    manifest = {"source": "bvbrc", "provider": str(cfg["provider_name"]), "mode": mode, "organism_name": organism_name, "taxon_id": taxon_id, "query_cache_key": cache_key, "proteins_queried": int(len(proteins)), "protein_count_mapped": int(matched), "source_used": "api_real" if matched else "bvbrc_filtered_no_matches", "cache_hit": False, "api_attempted": True, "api_success": True, "fallback_reason": None if matched else "no_bvbrc_matches_for_workspace_candidates", "notes": errors + notes, "generated_at_utc": _utc_now()}
    if not no_write_cache:
        cache["entries"][cache_key] = {"saved_at_utc": _utc_now(), "strain_conservation_rows": df.to_dict(orient="records"), "manifest": manifest}
        save_bvbrc_cache(workspace, config, cache)
    return {"strain_conservation_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
