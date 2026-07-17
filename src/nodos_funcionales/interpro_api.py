from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

import pandas as pd

from .human_essentiality_api import fetch_human_essentiality_annotations
from .online_http import get_ssl_context
from .provider_response_audit import request_provider_payload


SOURCE_MODES = {"offline_only", "cache_first", "online_optional"}
HOST_ANNOTATION_COLUMNS = [
    "protein_id",
    "gene",
    "domain_overlap_score",
    "host_criticality_penalty",
    "database",
    "interpro_bacterial_accession",
    "interpro_human_accession",
    "interpro_bacterial_entries",
    "interpro_human_entries",
    "interpro_shared_entries",
    "human_essentiality_score",
    "human_essentiality_status",
    "interpro_rule",
    "interpro_missing_flags",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(config["online_sources"]["interpro"]["cache_filename"])


def load_interpro_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_interpro_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def _api_get_json(url: str, cfg: dict[str, Any]) -> tuple[Any | None, list[str]]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        response = request_provider_payload(url, timeout=timeout, user_agent=user_agent, accept="application/json", opener=urlopen)
        if response.error_status == "" and response.payload_type == "json":
            return response.payload, errors
        errors.append(response.rejection_reason or response.error_status or f"unexpected_payload_type:{response.payload_type}")
        if response.http_status == 429 and attempt < retries:
            time.sleep(backoff)
            continue
        break
    return None, errors


def _interpro_status_from_notes(api_success: bool, accessions: list[str], notes: list[str]) -> str:
    if api_success and accessions:
        return "connected_structured_payload"
    joined = " ".join(str(note) for note in notes).lower()
    if "ssl_error" in joined or "openssl" in joined:
        return "ssl_error"
    if "network_error" in joined or "error de red" in joined:
        return "network_error"
    if "html_instead_of_structured_payload" in joined or "unexpected_payload_type" in joined:
        return "invalid_payload"
    return "unresolved"


def _normalise_id(value: object) -> str:
    return str(value or "").strip().upper()


def _clean_accession(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value or "").strip()
    return "" if text.lower() in {"", "nan", "none", "unknown"} else text


def _load_candidate_context(workspace: Path) -> pd.DataFrame:
    homologs_path = workspace / "data_raw" / "human_homologs.csv"
    if not homologs_path.exists():
        return pd.DataFrame(columns=["protein_id", "gene"])
    homologs = pd.read_csv(homologs_path)
    if "protein_id" not in homologs.columns:
        return pd.DataFrame(columns=["protein_id", "gene"])
    homologs = homologs.copy()
    homologs["protein_id"] = homologs["protein_id"].map(_normalise_id)
    if "gene" not in homologs.columns:
        homologs["gene"] = homologs["protein_id"]

    annotations_path = workspace / "data_raw" / "uniprot_annotations.csv"
    if annotations_path.exists():
        annotations = pd.read_csv(annotations_path)
        if {"protein_id", "uniprot_accession"}.issubset(annotations.columns):
            annotations = annotations.copy()
            annotations["protein_id"] = annotations["protein_id"].map(_normalise_id)
            annotations = annotations[["protein_id", "uniprot_accession"]].drop_duplicates("protein_id")
            homologs = homologs.merge(annotations, on="protein_id", how="left")
    if "uniprot_accession" not in homologs.columns:
        homologs["uniprot_accession"] = ""
    if "human_uniprot_accession" not in homologs.columns:
        homologs["human_uniprot_accession"] = ""
    return homologs.drop_duplicates("protein_id").sort_values("protein_id").reset_index(drop=True)


def _cache_key(candidates: pd.DataFrame) -> str:
    payload = "|".join(
        f"{row.get('protein_id')}:{row.get('uniprot_accession', '')}:{row.get('human_uniprot_accession', '')}"
        for _, row in candidates.iterrows()
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"interpro_host_annotation::{digest}"


def _build_query_url(accession: str, cfg: dict[str, Any]) -> str:
    base = str(cfg["provider_base_url"]).rstrip("/")
    page_size = int(cfg.get("page_size", 200))
    return f"{base}/entry/interpro/protein/uniprot/{quote(accession)}/?page_size={page_size}"


def _extract_entries(payload: Any) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    results = payload.get("results", []) or []
    entries: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata", {}) or {}
        accession = str(metadata.get("accession") or item.get("accession") or "").strip().upper()
        if accession:
            entries.add(accession)
    return entries


def _query_entries(accession: str, cfg: dict[str, Any]) -> tuple[set[str], list[str], bool]:
    clean = str(accession or "").strip()
    if not clean:
        return set(), ["missing_uniprot_accession"], False
    payload, errors = _api_get_json(_build_query_url(clean, cfg), cfg)
    if payload is None:
        return set(), errors, False
    return _extract_entries(payload), errors, True


def _format_entries(entries: set[str]) -> str:
    return ";".join(sorted(entries)) if entries else ""


def _human_essentiality_lookup(workspace: Path, config: dict[str, Any]) -> tuple[dict[str, float], dict[str, str], list[str]]:
    cfg = config["online_sources"].get("human_essentiality", {})
    if not bool(cfg.get("enabled", True)):
        return {}, {}, ["human_essentiality_disabled"]
    try:
        result = fetch_human_essentiality_annotations(workspace, config, mode="cache_first")
    except (FileNotFoundError, ValueError) as exc:
        return {}, {}, [str(exc)]
    df = result["human_essentiality"]
    if df.empty or "human_gene" not in df.columns:
        return {}, {}, list(result.get("manifest", {}).get("notes", []))
    score_lookup = {
        str(row.get("human_gene") or "").strip().upper(): float(row.get("human_essentiality_score", 0.0) or 0.0)
        for _, row in df.iterrows()
        if str(row.get("human_gene") or "").strip()
    }
    status_lookup = {
        str(row.get("human_gene") or "").strip().upper(): str(row.get("human_essentiality_lookup_status") or "unknown")
        for _, row in df.iterrows()
        if str(row.get("human_gene") or "").strip()
    }
    return score_lookup, status_lookup, list(result.get("manifest", {}).get("notes", []))


def _derive_host_annotation(candidates: pd.DataFrame, domain_lookup: dict[str, set[str]], config: dict[str, Any], workspace: Path) -> tuple[pd.DataFrame, int, list[str]]:
    cfg = config["online_sources"]["interpro"]
    essentiality_scores, essentiality_status, essentiality_notes = _human_essentiality_lookup(workspace, config)
    criticality_weight = float(config["online_sources"].get("human_essentiality", {}).get("criticality_weight", 0.20))
    neutral = float(config["imputation"]["neutral_unknown_score"])
    rows = []
    paired_domain_rows = 0
    for _, row in candidates.iterrows():
        protein_id = _normalise_id(row.get("protein_id"))
        if not protein_id:
            continue
        gene = str(row.get("gene") or protein_id).strip()
        bacterial_accession = _clean_accession(row.get("uniprot_accession"))
        human_accession = _clean_accession(row.get("human_uniprot_accession"))
        human_homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
        human_signal = neutral if pd.isna(human_homolog) else float(human_homolog)
        human_gene = str(row.get("human_gene") or "").strip().upper()
        human_essentiality = float(essentiality_scores.get(human_gene, 0.0))
        human_essentiality_lookup_status = essentiality_status.get(human_gene, "not_queried")
        bacterial_entries = domain_lookup.get(bacterial_accession, set())
        human_entries = domain_lookup.get(human_accession, set())
        shared_entries = bacterial_entries & human_entries
        flags = []
        if not bacterial_accession:
            flags.append("missing_bacterial_uniprot_accession")
        if not human_accession and human_signal > 0:
            flags.append("missing_human_uniprot_accession")
        if bacterial_accession and not bacterial_entries:
            flags.append("no_bacterial_interpro_entries")
        if human_accession and not human_entries:
            flags.append("no_human_interpro_entries")
        if human_signal > 0 and human_essentiality_lookup_status in {"not_found", "not_queried"}:
            flags.append("missing_human_essentiality")

        if bacterial_entries and human_entries:
            paired_domain_rows += 1
            denominator = max(len(bacterial_entries | human_entries), 1)
            domain_overlap = len(shared_entries) / denominator
            base_criticality = 0.75 * domain_overlap + 0.25 * human_signal
            host_criticality = min(1.0, max(0.0, (1.0 - criticality_weight) * base_criticality + criticality_weight * human_essentiality))
            rule = "interpro_shared_domain_overlap_v1"
        elif human_signal == 0:
            domain_overlap = 0.0
            host_criticality = 0.0
            rule = "interpro_no_human_homolog_low_overlap_v1"
        else:
            domain_overlap = neutral
            base_criticality = 0.60 * neutral + 0.40 * human_signal
            host_criticality = min(1.0, max(0.0, (1.0 - criticality_weight) * base_criticality + criticality_weight * human_essentiality))
            rule = "interpro_incomplete_domain_context_default_v1"

        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "domain_overlap_score": round(float(domain_overlap), 4),
                "host_criticality_penalty": round(float(host_criticality), 4),
                "database": str(cfg["database_label"]),
                "interpro_bacterial_accession": bacterial_accession,
                "interpro_human_accession": human_accession,
                "interpro_bacterial_entries": _format_entries(bacterial_entries),
                "interpro_human_entries": _format_entries(human_entries),
                "interpro_shared_entries": _format_entries(shared_entries),
                "human_essentiality_score": round(human_essentiality, 4),
                "human_essentiality_status": human_essentiality_lookup_status,
                "interpro_rule": rule,
                "interpro_missing_flags": "; ".join(flags) if flags else "none",
            }
        )
    return pd.DataFrame(rows, columns=HOST_ANNOTATION_COLUMNS), paired_domain_rows, essentiality_notes


def _write_manifest(workspace: Path, manifest: dict[str, Any]) -> Path:
    path = workspace / "results" / "interpro_host_annotation_manifest.json"
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


def fetch_interpro_host_annotation(
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
    candidates = _load_candidate_context(workspace)
    cache = load_interpro_cache(workspace, config)
    cache_key = _cache_key(candidates)
    cfg = config["online_sources"]["interpro"]

    if not refresh_cache and cache["entries"].get(cache_key):
        entry = cache["entries"][cache_key]
        df = pd.DataFrame(entry.get("host_annotation_rows", []), columns=HOST_ANNOTATION_COLUMNS)
        manifest = _cache_manifest(entry.get("manifest", {}), mode)
        return {"host_annotation_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
    if mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache InterPro utilizable para esta capa.")
    if candidates.empty:
        manifest = {
            "source": "interpro",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "organism_name": organism_name,
            "taxon_id": taxon_id,
            "query_cache_key": cache_key,
            "proteins_queried": 0,
            "paired_domain_rows": 0,
            "source_used": "empty_candidates",
            "cache_hit": False,
            "api_attempted": False,
            "api_success": False,
            "fallback_reason": "no_candidate_proteins",
            "notes": ["no_candidate_proteins"],
            "generated_at_utc": _utc_now(),
        }
        return {"host_annotation_data": pd.DataFrame(columns=HOST_ANNOTATION_COLUMNS), "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}

    accessions = sorted(
        {
            _clean_accession(value)
            for column in ["uniprot_accession", "human_uniprot_accession"]
            for value in candidates.get(column, pd.Series(dtype="string")).fillna("").tolist()
            if _clean_accession(value)
        }
    )
    domain_lookup: dict[str, set[str]] = {}
    notes: list[str] = []
    api_success = True
    for accession in accessions:
        entries, errors, success = _query_entries(accession, cfg)
        notes.extend(errors)
        if not success:
            api_success = False
        domain_lookup[accession] = entries

    df, paired_domain_rows, essentiality_notes = _derive_host_annotation(candidates, domain_lookup, config, workspace)
    source_used = "api_real" if api_success and paired_domain_rows else ("api_real_partial" if api_success else "api_failed")
    all_notes = notes + essentiality_notes
    manifest = {
        "source": "interpro",
        "provider": str(cfg["provider_name"]),
        "provider_docs_url": str(cfg.get("provider_docs_url", "")),
        "mode": mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "query_cache_key": cache_key,
        "proteins_queried": int(len(candidates)),
        "accessions_queried": int(len(accessions)),
        "paired_domain_rows": int(paired_domain_rows),
        "source_used": source_used,
        "cache_hit": False,
        "api_attempted": bool(accessions),
        "api_success": bool(api_success and accessions),
        "retrieval_status": _interpro_status_from_notes(api_success, accessions, notes),
        "fallback_reason": None if paired_domain_rows else "no_comparable_interpro_domain_pairs",
        "notes": all_notes,
        "generated_at_utc": _utc_now(),
        "affects_score": False,
        "blocks_ranking": False,
        "evidence_inferred": bool(paired_domain_rows),
        "parser_used": "interpro_json_results_parser",
    }
    if not no_write_cache and not df.empty and api_success:
        cache["entries"][cache_key] = {"saved_at_utc": _utc_now(), "host_annotation_rows": df.to_dict(orient="records"), "manifest": manifest}
        save_interpro_cache(workspace, config, cache)
    return {"host_annotation_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
