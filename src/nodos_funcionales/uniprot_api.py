from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .online.provider_modes import accepted_provider_modes, normalize_provider_mode
from .online.provenance import provider_provenance

UNIPROT_SOURCE_MODES = {"offline_only", "cache_first", "online_optional", "local", "auto", "api_stub"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(config["online_sources"]["uniprot"]["cache_filename"])


def load_uniprot_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload = _json_load(path)
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_uniprot_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def invalidate_uniprot_cache_entry(workspace: Path, config: dict[str, Any], cache_key: str) -> bool:
    cache = load_uniprot_cache(workspace, config)
    removed = cache.get("entries", {}).pop(cache_key, None)
    save_uniprot_cache(workspace, config, cache)
    return removed is not None


def invalidate_uniprot_cache_entries_for_protein(workspace: Path, config: dict[str, Any], protein_id: str) -> int:
    protein_id = str(protein_id).strip().upper()
    cache = load_uniprot_cache(workspace, config)
    keys = [key for key in cache.get("entries", {}) if protein_id and protein_id in key.upper()]
    for key in keys:
        cache["entries"].pop(key, None)
    save_uniprot_cache(workspace, config, cache)
    return len(keys)


def _request_json(url: str, timeout: float, user_agent: str) -> Any:
    request = Request(url, headers={"User-Agent": user_agent})
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
            errors.append(f"HTTP {exc.code} en UniProt")
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff)
                continue
            break
        except URLError as exc:
            errors.append(f"Error de red en UniProt: {exc.reason}")
            break
        except TimeoutError:
            errors.append("Timeout en UniProt")
            break
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"Respuesta JSON invalida de UniProt: {exc}")
            break
    return None, errors


def _get_candidate_proteins(workspace: Path) -> pd.DataFrame:
    raw_dir = workspace / "data_raw"
    candidates: dict[str, dict[str, str]] = {}
    for filename in ["essentiality.csv", "virulence.csv", "human_homologs.csv", "localization.csv"]:
        path = raw_dir / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "protein_id" not in df.columns:
            continue
        for _, row in df.iterrows():
            protein_id = str(row.get("protein_id", "")).strip()
            if not protein_id:
                continue
            gene = str(row.get("gene", "")).strip() or protein_id
            candidates.setdefault(protein_id.upper(), {"protein_id": protein_id.upper(), "gene": gene})
    if not candidates:
        raise ValueError("No hay proteínas base en el workspace para consultar UniProt.")
    return pd.DataFrame(candidates.values()).sort_values("protein_id").reset_index(drop=True)


def _cache_key(taxon_id: str | None, proteins: pd.DataFrame) -> str:
    payload = "|".join(
        f"{str(row['protein_id']).strip().upper()}:{str(row['gene']).strip()}"
        for _, row in proteins.sort_values("protein_id").iterrows()
    )
    return f"uniprot::{taxon_id or 'unknown'}::{payload}"


def _extract_gene_names(entry: dict[str, Any]) -> list[str]:
    results = []
    for gene in entry.get("genes", []) or []:
        gene_name = gene.get("geneName", {})
        if gene_name.get("value"):
            results.append(str(gene_name["value"]))
        for field in ["synonyms", "orderedLocusNames", "orfNames"]:
            for item in gene.get(field, []) or []:
                if item.get("value"):
                    results.append(str(item["value"]))
    deduped = []
    for item in results:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _extract_protein_name(entry: dict[str, Any]) -> str:
    description = entry.get("proteinDescription", {}) or {}
    recommended = description.get("recommendedName", {}) or {}
    full = recommended.get("fullName", {}) or {}
    if full.get("value"):
        return str(full["value"])
    for submitted in description.get("submissionNames", []) or []:
        full_name = (submitted.get("fullName") or {}).get("value")
        if full_name:
            return str(full_name)
    return ""


def _extract_subcellular_location(entry: dict[str, Any]) -> str:
    locations: list[str] = []
    for comment in entry.get("comments", []) or []:
        if str(comment.get("commentType") or "").strip().lower() != "subcellular location":
            continue
        for location in comment.get("subcellularLocations", []) or []:
            value = (((location.get("location") or {}).get("value")) or "").strip()
            if value:
                locations.append(value)
    deduped: list[str] = []
    for item in locations:
        if item not in deduped:
            deduped.append(item)
    return ";".join(deduped)


def _query_uniprot_for_gene(gene: str, taxon_id: str, cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    query = f"(organism_id:{taxon_id}) AND (gene:{gene})"
    params = {
        "query": query,
        "format": "json",
        "size": int(cfg["max_results_per_query"]),
        "fields": str(cfg["fields"]),
    }
    url = f"{str(cfg['provider_base_url'])}?{urlencode(params)}"
    payload, errors = _api_get_json(url, cfg)
    if not payload:
        return None, errors
    results = payload.get("results", []) or []
    if not results:
        return None, errors
    return results[0], errors


def _build_uniprot_row(
    protein_id: str,
    gene: str,
    entry: dict[str, Any] | None,
    config: dict[str, Any],
    source_used: str,
    cache_hit: bool,
    api_attempted: bool,
    api_success: bool,
    fallback_reason: str | None,
) -> dict[str, Any]:
    provider_name = str(config["online_sources"]["uniprot"]["provider_name"])
    if not entry:
        return {
            "protein_id": protein_id,
            "gene": gene,
            "uniprot_accession": "",
            "uniprot_id": "",
            "uniprot_reviewed": "",
            "uniprot_protein_name": "",
            "uniprot_gene_primary": "",
            "uniprot_gene_names": "",
            "uniprot_annotation_score": "",
            "uniprot_organism_name": "",
            "uniprot_subcellular_location": "",
            "uniprot_match_status": "no_match",
            "database": str(config["online_sources"]["uniprot"]["database_label"]),
            "provider": provider_name,
            "source_used": source_used,
            "cache_hit": cache_hit,
            "api_attempted": api_attempted,
            "api_success": api_success,
            "fallback_reason": fallback_reason or "",
            "data_realism_flag": "computed_online" if api_success else "computed_cached",
            "provenance_summary": f"provider={provider_name}; source_used={source_used}; cache_hit={cache_hit}; api_success={api_success}",
        }

    gene_names = _extract_gene_names(entry)
    primary_gene = gene_names[0] if gene_names else ""
    exact_gene_match = any(item.casefold() == gene.casefold() for item in gene_names)
    return {
        "protein_id": protein_id,
        "gene": gene,
        "uniprot_accession": str(entry.get("primaryAccession") or ""),
        "uniprot_id": str(entry.get("uniProtkbId") or ""),
        "uniprot_reviewed": "reviewed" if str(entry.get("entryType", "")).lower().find("reviewed") >= 0 else "unreviewed",
        "uniprot_protein_name": _extract_protein_name(entry),
        "uniprot_gene_primary": primary_gene,
        "uniprot_gene_names": ";".join(gene_names),
        "uniprot_annotation_score": entry.get("annotationScore", ""),
        "uniprot_organism_name": str((entry.get("organism") or {}).get("scientificName") or ""),
        "uniprot_subcellular_location": _extract_subcellular_location(entry),
        "uniprot_match_status": "exact_gene_match" if exact_gene_match else "partial_gene_match",
        "database": str(config["online_sources"]["uniprot"]["database_label"]),
        "provider": provider_name,
        "source_used": source_used,
        "cache_hit": cache_hit,
        "api_attempted": api_attempted,
        "api_success": api_success,
        "fallback_reason": fallback_reason or "",
        "data_realism_flag": "computed_online" if api_success else "computed_cached",
        "provenance_summary": f"provider={provider_name}; source_used={source_used}; cache_hit={cache_hit}; api_success={api_success}",
    }


def _write_outputs(workspace: Path, annotations: pd.DataFrame, manifest: dict[str, Any]) -> tuple[Path, Path]:
    raw_dir = workspace / "data_raw"
    results_dir = workspace / "results"
    raw_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    annotation_path = raw_dir / "uniprot_annotations.csv"
    manifest_path = results_dir / "online_source_manifest.json"
    report_path = results_dir / "online_source_report.md"
    annotations.to_csv(annotation_path, index=False)
    _json_dump(manifest_path, manifest)
    lines = [
        "# Online Source Report",
        "",
        f"- Source: `{manifest['source']}`",
        f"- Provider: `{manifest['provider']}`",
        f"- Mode: `{manifest['mode']}`",
        f"- Source used: `{manifest['source_used']}`",
        f"- Cache hit: `{manifest['cache_hit']}`",
        f"- API success: `{manifest['api_success']}`",
        f"- Taxon id: `{manifest.get('taxon_id') or 'unknown'}`",
        f"- Proteins requested: `{manifest['protein_count_requested']}`",
        f"- Exact gene matches: `{manifest['exact_gene_match_count']}`",
        f"- Partial gene matches: `{manifest['partial_gene_match_count']}`",
        f"- No matches: `{manifest['no_match_count']}`",
        f"- Output written: `{annotation_path}`",
        "",
        "## Notes",
    ]
    if manifest.get("notes"):
        lines.extend([f"- {note}" for note in manifest["notes"]])
    else:
        lines.append("- none")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return manifest_path, report_path


def _build_cache_served_manifest(cached_manifest: dict[str, Any], mode: str) -> dict[str, Any]:
    provider = str(cached_manifest.get("provider", "uniprot_rest"))
    served = {
        **cached_manifest,
        "mode": mode,
        "source_used": "cache",
        "cache_hit": True,
        "api_attempted": False,
        "api_success": False,
        "fallback_reason": None,
        "data_realism_flag": "computed_cached",
        "provenance_summary": f"provider={provider}; source_used=cache; cache_hit=True; api_success=False",
    }
    served.update(
        provider_provenance(
            provider,
            "cache",
            float(cached_manifest.get("confidence", 0.80)),
            retrieval_mode=mode,
            cache_status="cache_hit",
            source_version=str(cached_manifest.get("generated_at_utc", ""))[:10] or None,
        )
    )
    notes = list(served.get("notes", []))
    if "served_from_cache" not in notes:
        notes.append("served_from_cache")
    served["notes"] = notes
    return served


def fetch_uniprot_annotations(
    workspace: Path,
    organism_name: str,
    taxon_id: str | None,
    config: dict[str, Any],
    mode: str,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
) -> dict[str, Any]:
    workspace = Path(workspace)
    if not workspace.exists():
        raise FileNotFoundError(f"Workspace no encontrado: {workspace}")
    if mode not in accepted_provider_modes(config):
        raise ValueError(f"online source mode no soportado: {mode}")
    requested_mode = mode
    mode = normalize_provider_mode(mode, config)

    proteins = _get_candidate_proteins(workspace)
    cache = load_uniprot_cache(workspace, config)
    cache_key = _cache_key(taxon_id, proteins)
    cfg = config["online_sources"]["uniprot"]

    if not refresh_cache and mode in {"offline_only", "cache_first", "online_optional"}:
        cached_entry = cache["entries"].get(cache_key)
        if cached_entry:
            annotations = pd.DataFrame(cached_entry.get("annotations", []))
            manifest = _build_cache_served_manifest(cached_entry.get("manifest", {}), mode)
            manifest["requested_mode"] = requested_mode
            manifest_path, report_path = _write_outputs(workspace, annotations, manifest)
            return {"annotations": annotations, "manifest": manifest, "manifest_path": manifest_path, "report_path": report_path}

    if mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache UniProt utilizable para este conjunto de proteínas.")
    if not taxon_id:
        raise ValueError("Se requiere taxon_id para consultar UniProt de forma reproducible.")

    rows = []
    notes: list[str] = []
    exact = partial = no_match = 0
    for _, protein in proteins.iterrows():
        gene = str(protein["gene"]).strip()
        entry, errors = _query_uniprot_for_gene(gene, taxon_id, cfg)
        notes.extend(errors)
        row = _build_uniprot_row(
            protein_id=str(protein["protein_id"]),
            gene=gene,
            entry=entry,
            config=config,
            source_used="api_real",
            cache_hit=False,
            api_attempted=True,
            api_success=True,
            fallback_reason=None,
        )
        rows.append(row)
        status = row["uniprot_match_status"]
        if status == "exact_gene_match":
            exact += 1
        elif status == "partial_gene_match":
            partial += 1
        else:
            no_match += 1

    annotations = pd.DataFrame(rows)
    manifest = {
        "source": "uniprot",
        "provider": str(cfg["provider_name"]),
        "provider_docs_url": str(cfg["provider_docs_url"]),
        "requested_mode": requested_mode,
        "mode": mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "query_cache_key": cache_key,
        "protein_count_requested": int(len(proteins)),
        "exact_gene_match_count": exact,
        "partial_gene_match_count": partial,
        "no_match_count": no_match,
        "source_used": "api_real",
        "cache_hit": False,
        "api_attempted": True,
        "api_success": True,
        "fallback_reason": None,
        "notes": notes,
        "generated_at_utc": _utc_now(),
        "data_realism_flag": "computed_online",
        "confidence": 0.90,
        "provenance_summary": f"provider={cfg['provider_name']}; source_used=api_real; cache_hit=False; api_success=True",
    }
    manifest.update(
        provider_provenance(
            str(cfg["provider_name"]),
            str(manifest["source_used"]),
            float(manifest["confidence"]),
            retrieval_mode=mode,
            cache_status="cache_miss",
            source_version=str(manifest["generated_at_utc"])[:10],
            incomplete=exact == 0 and partial == 0,
        )
    )

    if not no_write_cache:
        cache["entries"][cache_key] = {
            "saved_at_utc": _utc_now(),
            "source": "uniprot",
            "organism_name": organism_name,
            "taxon_id": taxon_id,
            "annotations": annotations.to_dict(orient="records"),
            "manifest": manifest,
        }
        save_uniprot_cache(workspace, config, cache)

    manifest_path, report_path = _write_outputs(workspace, annotations, manifest)
    return {"annotations": annotations, "manifest": manifest, "manifest_path": manifest_path, "report_path": report_path}
