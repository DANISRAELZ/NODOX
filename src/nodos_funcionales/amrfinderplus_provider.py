from __future__ import annotations

import hashlib
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import pandas as pd

from .provider_response_audit import ProviderResponse, request_provider_payload, response_audit_fields


AMRFINDER_EVIDENCE_COLUMNS = [
    "protein_id",
    "gene",
    "resistance_emergence_risk",
    "evidence_source",
    "source_type",
    "confidence",
    "notes",
    "database",
    "amrfinder_source_record",
    "amrfinder_source_version",
    "amrfinder_retrieved_at",
    "amrfinder_catalog_sha256",
    "amrfinder_mapping_method",
    "amrfinder_mapping_status",
    "amrfinder_evidence_status",
    "amrfinder_evidence_confidence",
    "amrfinder_independence_group",
    "amrfinder_method_scope",
    "amrfinder_taxon_id",
    "amrfinder_organism_group",
    "amrfinder_pubmed_references",
    "amrfinder_mutation_symbols",
    "amrfinder_drug_classes",
    "amrfinder_drug_subclasses",
    "amrfinder_mutation_count",
    "amrfinder_provider_retrieval_status",
    "amrfinder_provider_source_used",
    "amrfinder_provider_url",
]

DEFAULT_AMRFINDER_CONFIG: dict[str, Any] = {
    "enabled": True,
    "provider_name": "amrfinderplus_point_mutations",
    "provider_base_url": "https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/AMRFinderPlus/database/latest",
    "catalog_filename": "ReferenceGeneCatalog.txt",
    "version_filename": "version.txt",
    "provider_timeout_seconds": 45,
    "provider_max_retries": 1,
    "provider_backoff_seconds": 1.0,
    "provider_user_agent": "nodox-amrfinderplus/1.0 (offline-safe; contact=local-workspace)",
    "cache_filename": "amrfinderplus_point_mutation_cache.json",
    "database_label": "ncbi_amrfinderplus_reference_gene_catalog",
    "confidence_real": 0.95,
    "scope": "core",
    "type": "AMR",
    "subtype": "POINT",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _cfg(config: dict[str, Any]) -> dict[str, Any]:
    supplied = config.get("online_sources", {}).get("amrfinderplus", {})
    return {**DEFAULT_AMRFINDER_CONFIG, **(supplied if isinstance(supplied, dict) else {})}


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(_cfg(config)["cache_filename"])


def _read_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def _write_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    path = _cache_path(workspace, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at_utc"] = _utc_now()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_manifest(workspace: Path, manifest: dict[str, Any]) -> Path:
    path = workspace / "results" / "amrfinderplus_point_mutation_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return path


def _candidate_proteins(workspace: Path) -> pd.DataFrame:
    rows: dict[str, dict[str, str]] = {}
    for filename in ["essentiality.csv", "virulence.csv", "human_homologs.csv", "localization.csv"]:
        path = workspace / "data_raw" / filename
        if not path.exists():
            continue
        try:
            table = pd.read_csv(path)
        except Exception:  # noqa: BLE001 - candidate discovery is best-effort.
            continue
        if "protein_id" not in table.columns:
            continue
        for _, row in table.iterrows():
            protein_id = str(row.get("protein_id") or "").strip().upper()
            if not protein_id:
                continue
            gene = str(row.get("gene") or "").strip()
            if not gene or gene.lower() in {"nan", "none", "unknown"}:
                continue
            rows.setdefault(protein_id, {"protein_id": protein_id, "gene": gene})
    if not rows:
        return pd.DataFrame(columns=["protein_id", "gene"])
    return pd.DataFrame(rows.values()).sort_values("protein_id").reset_index(drop=True)


def _normalize_token(value: object) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _organism_tokens(organism_name: str, cfg: dict[str, Any]) -> set[str]:
    tokens = {_normalize_token(organism_name)}
    words = [item for item in re.split(r"\s+", str(organism_name or "").strip()) if item]
    if len(words) >= 2:
        tokens.add(_normalize_token(" ".join(words[:2])))
    for alias in cfg.get("organism_aliases", []) or []:
        normalized = _normalize_token(alias)
        if normalized:
            tokens.add(normalized)
    return {token for token in tokens if token}


def _split_taxa(value: object) -> set[str]:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none"}:
        return set()
    values = re.split(r"[;,|]+", text)
    return {_normalize_token(item) for item in values if _normalize_token(item)}


def _cache_key(taxon_id: str | None, organism_name: str, candidates: pd.DataFrame) -> str:
    genes = sorted({str(value).strip().casefold() for value in candidates.get("gene", pd.Series(dtype=str)) if str(value).strip()})
    raw = f"{taxon_id or 'unknown'}|{_normalize_token(organism_name)}|{'|'.join(genes)}"
    return "amrfinderplus::" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _request_text(url: str, cfg: dict[str, Any]) -> tuple[str | None, ProviderResponse | None, list[str]]:
    retries = int(cfg["provider_max_retries"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        response = request_provider_payload(
            url,
            timeout=float(cfg["provider_timeout_seconds"]),
            user_agent=str(cfg["provider_user_agent"]),
            accept="text/plain,text/tab-separated-values,*/*",
            opener=urlopen,
        )
        if response.error_status == "" and isinstance(response.payload, str) and response.payload.strip():
            return response.payload, response, errors
        errors.append(response.rejection_reason or response.error_status or response.payload_type)
        if response.http_status == 429 and attempt < retries:
            time.sleep(float(cfg["provider_backoff_seconds"]))
            continue
        return None, response, errors
    return None, None, errors


def _normalize_catalog_columns(table: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for column in table.columns:
        normalized = re.sub(r"[^a-z0-9]+", "_", str(column).strip().casefold()).strip("_")
        renamed[column] = normalized
    return table.rename(columns=renamed)


def _parse_catalog(text: str) -> pd.DataFrame:
    table = pd.read_csv(io.StringIO(text), sep="\t", dtype=str, keep_default_na=False)
    table = _normalize_catalog_columns(table)
    required = {
        "allele",
        "gene_family",
        "whitelisted_taxa",
        "scope",
        "type",
        "subtype",
        "class",
        "subclass",
        "pubmed_reference",
        "db_version",
    }
    missing = sorted(required - set(table.columns))
    if missing:
        raise ValueError("AMRFinderPlus ReferenceGeneCatalog missing columns: " + ",".join(missing))
    return table


def _join_unique(values: list[object], *, limit: int = 80) -> str:
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text.lower() in {"nan", "none"}:
            continue
        if text not in unique:
            unique.append(text)
        if len(unique) >= limit:
            break
    return ";".join(unique)


def _build_rows(
    candidates: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    organism_name: str,
    taxon_id: str,
    release_version: str,
    catalog_sha256: str,
    retrieved_at: str,
    provider_url: str,
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    organism_tokens = _organism_tokens(organism_name, cfg)
    core = catalog[
        catalog["scope"].astype(str).str.casefold().eq(str(cfg["scope"]).casefold())
        & catalog["type"].astype(str).str.casefold().eq(str(cfg["type"]).casefold())
        & catalog["subtype"].astype(str).str.casefold().eq(str(cfg["subtype"]).casefold())
    ].copy()
    if core.empty:
        return pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS), {
            "point_mutation_catalog_rows": 0,
            "organism_scoped_rows": 0,
            "candidate_gene_matches": 0,
        }

    organism_mask = core["whitelisted_taxa"].map(lambda value: bool(_split_taxa(value) & organism_tokens))
    organism_rows = core.loc[organism_mask].copy()
    if organism_rows.empty:
        return pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS), {
            "point_mutation_catalog_rows": int(len(core)),
            "organism_scoped_rows": 0,
            "candidate_gene_matches": 0,
        }

    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        gene = str(candidate.get("gene") or "").strip()
        protein_id = str(candidate.get("protein_id") or "").strip().upper()
        if not gene or not protein_id:
            continue
        matches = organism_rows[
            organism_rows["gene_family"].astype(str).str.casefold().eq(gene.casefold())
        ].copy()
        if matches.empty:
            continue

        mutation_symbols = _join_unique(matches["allele"].tolist())
        pubmed = _join_unique(matches["pubmed_reference"].tolist())
        drug_classes = _join_unique(matches["class"].tolist())
        drug_subclasses = _join_unique(matches["subclass"].tolist())
        organism_groups = _join_unique(matches["whitelisted_taxa"].tolist())
        refseq_proteins = _join_unique(matches.get("refseq_protein_accession", pd.Series(dtype=str)).tolist())
        record = (
            f"AMRFinderPlus:{release_version};gene={gene};organism={organism_groups};"
            f"mutations={mutation_symbols};refseq={refseq_proteins}"
        )
        source_type = "literature_curated" if pubmed else "real_external"
        evidence_confidence = "high" if pubmed else "moderate"
        database = f"{cfg['database_label']}:{release_version}"
        method_scope = (
            "Target-level evidence that NCBI AMRFinderPlus contains at least one curated "
            "AMR point mutation for the exact candidate gene within an exact whitelisted "
            "organism group. This does not assert that the current candidate sequence "
            "already carries the mutation and does not encode absence of catalog matches as low risk."
        )
        notes = (
            "Positive-only Stage 4D evidence: resistance_emergence_risk=1.0 denotes a documented "
            "target-site escape route in the curated AMRFinderPlus catalog, not a prospective probability."
        )
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "resistance_emergence_risk": 1.0,
                "evidence_source": "NCBI AMRFinderPlus Reference Gene Catalog point mutations",
                "source_type": source_type,
                "confidence": evidence_confidence,
                "notes": notes,
                "database": database,
                "amrfinder_source_record": record,
                "amrfinder_source_version": release_version,
                "amrfinder_retrieved_at": retrieved_at,
                "amrfinder_catalog_sha256": catalog_sha256,
                "amrfinder_mapping_method": "exact_gene_family_and_whitelisted_organism",
                "amrfinder_mapping_status": "exact_gene_and_taxon",
                "amrfinder_evidence_status": "observed",
                "amrfinder_evidence_confidence": evidence_confidence,
                "amrfinder_independence_group": "ncbi_amrfinderplus_curated_point_mutations",
                "amrfinder_method_scope": method_scope,
                "amrfinder_taxon_id": str(taxon_id),
                "amrfinder_organism_group": organism_groups,
                "amrfinder_pubmed_references": pubmed,
                "amrfinder_mutation_symbols": mutation_symbols,
                "amrfinder_drug_classes": drug_classes,
                "amrfinder_drug_subclasses": drug_subclasses,
                "amrfinder_mutation_count": int(len(matches)),
                "amrfinder_provider_retrieval_status": "api_real",
                "amrfinder_provider_source_used": "api_real",
                "amrfinder_provider_url": provider_url,
            }
        )

    return pd.DataFrame(rows, columns=AMRFINDER_EVIDENCE_COLUMNS), {
        "point_mutation_catalog_rows": int(len(core)),
        "organism_scoped_rows": int(len(organism_rows)),
        "candidate_gene_matches": int(len(rows)),
    }


def _cached_result(
    workspace: Path,
    entry: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    rows = entry.get("rows", []) if isinstance(entry, dict) else []
    data = pd.DataFrame(rows, columns=AMRFINDER_EVIDENCE_COLUMNS)
    manifest = dict(entry.get("manifest", {}) if isinstance(entry, dict) else {})
    manifest.update(
        {
            "source_used": "cache",
            "retrieval_status": "cache_reused",
            "cache_hit": True,
            "api_attempted": False,
            "api_success": False,
            "mode": mode,
        }
    )
    return {
        "evolutionary_escape_risk_data": data,
        "manifest": manifest,
        "manifest_path": _write_manifest(workspace, manifest),
    }


def fetch_amrfinderplus_point_mutation_evidence(
    workspace: Path,
    organism_name: str | None,
    taxon_id: str | None,
    config: dict[str, Any],
    mode: str,
    *,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
) -> dict[str, Any]:
    workspace = Path(workspace)
    cfg = _cfg(config)
    candidates = _candidate_proteins(workspace)
    cache = _read_cache(workspace, config)
    cache_key = _cache_key(taxon_id, organism_name or "", candidates)

    if not bool(cfg.get("enabled", True)):
        manifest = {
            "source": "amrfinderplus",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "source_used": "provider_disabled",
            "retrieval_status": "provider_disabled",
            "cache_hit": False,
            "api_attempted": False,
            "api_success": False,
            "query_complete": False,
            "candidate_count": int(len(candidates)),
            "candidate_gene_matches": 0,
            "affects_score": False,
            "generated_at_utc": _utc_now(),
        }
        return {
            "evolutionary_escape_risk_data": pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS),
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    cached_entry = cache.get("entries", {}).get(cache_key)
    if (
        not refresh_cache
        and isinstance(cached_entry, dict)
        and bool(cached_entry.get("manifest", {}).get("query_complete", False))
    ):
        return _cached_result(workspace, cached_entry, mode=mode)

    if candidates.empty or not organism_name or not taxon_id:
        reason = "no_candidate_genes" if candidates.empty else "missing_organism_or_taxon"
        manifest = {
            "source": "amrfinderplus",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "source_used": reason,
            "retrieval_status": reason,
            "cache_hit": False,
            "api_attempted": False,
            "api_success": False,
            "query_complete": False,
            "candidate_count": int(len(candidates)),
            "candidate_gene_matches": 0,
            "affects_score": False,
            "generated_at_utc": _utc_now(),
        }
        return {
            "evolutionary_escape_risk_data": pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS),
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    base_url = str(cfg["provider_base_url"]).rstrip("/")
    version_url = f"{base_url}/{cfg['version_filename']}"
    catalog_url = f"{base_url}/{cfg['catalog_filename']}"
    retrieved_at = _utc_now()

    version_text, version_response, version_errors = _request_text(version_url, cfg)
    if version_text is None:
        if isinstance(cached_entry, dict) and bool(cached_entry.get("manifest", {}).get("query_complete", False)):
            fallback = _cached_result(workspace, cached_entry, mode=mode)
            fallback["manifest"]["api_attempted"] = True
            fallback["manifest"]["fallback_reason"] = "version_fetch_failed_fallback_cache"
            fallback["manifest"]["notes"] = version_errors
            _write_manifest(workspace, fallback["manifest"])
            return fallback
        audit = response_audit_fields(version_response, affects_score=False) if version_response else {}
        manifest = {
            "source": "amrfinderplus",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "source_used": "provider_failed",
            "retrieval_status": "version_fetch_failed",
            "cache_hit": False,
            "api_attempted": True,
            "api_success": False,
            "query_complete": False,
            "candidate_count": int(len(candidates)),
            "candidate_gene_matches": 0,
            "affects_score": False,
            "notes": version_errors,
            "generated_at_utc": retrieved_at,
            **audit,
        }
        return {
            "evolutionary_escape_risk_data": pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS),
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    release_version = version_text.strip().splitlines()[0].strip()
    if not release_version or len(release_version) > 100:
        manifest = {
            "source": "amrfinderplus",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "source_used": "provider_failed",
            "retrieval_status": "invalid_version_payload",
            "cache_hit": False,
            "api_attempted": True,
            "api_success": False,
            "query_complete": False,
            "candidate_count": int(len(candidates)),
            "candidate_gene_matches": 0,
            "affects_score": False,
            "generated_at_utc": retrieved_at,
        }
        return {
            "evolutionary_escape_risk_data": pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS),
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    catalog_text, catalog_response, catalog_errors = _request_text(catalog_url, cfg)
    if catalog_text is None:
        if isinstance(cached_entry, dict) and bool(cached_entry.get("manifest", {}).get("query_complete", False)):
            fallback = _cached_result(workspace, cached_entry, mode=mode)
            fallback["manifest"]["api_attempted"] = True
            fallback["manifest"]["fallback_reason"] = "catalog_fetch_failed_fallback_cache"
            fallback["manifest"]["notes"] = catalog_errors
            _write_manifest(workspace, fallback["manifest"])
            return fallback
        audit = response_audit_fields(catalog_response, affects_score=False) if catalog_response else {}
        manifest = {
            "source": "amrfinderplus",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "source_used": "provider_failed",
            "retrieval_status": "catalog_fetch_failed",
            "cache_hit": False,
            "api_attempted": True,
            "api_success": False,
            "query_complete": False,
            "candidate_count": int(len(candidates)),
            "candidate_gene_matches": 0,
            "affects_score": False,
            "notes": catalog_errors,
            "generated_at_utc": retrieved_at,
            **audit,
        }
        return {
            "evolutionary_escape_risk_data": pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS),
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    try:
        catalog = _parse_catalog(catalog_text)
    except (ValueError, pd.errors.ParserError) as exc:
        manifest = {
            "source": "amrfinderplus",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "source_used": "provider_failed",
            "retrieval_status": "catalog_schema_invalid",
            "cache_hit": False,
            "api_attempted": True,
            "api_success": False,
            "query_complete": False,
            "candidate_count": int(len(candidates)),
            "candidate_gene_matches": 0,
            "affects_score": False,
            "notes": [str(exc)],
            "generated_at_utc": retrieved_at,
        }
        return {
            "evolutionary_escape_risk_data": pd.DataFrame(columns=AMRFINDER_EVIDENCE_COLUMNS),
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    catalog_sha256 = hashlib.sha256(catalog_text.encode("utf-8")).hexdigest()
    provider_url = str(catalog_response.url if catalog_response else catalog_url)
    data, stats = _build_rows(
        candidates,
        catalog,
        organism_name=str(organism_name),
        taxon_id=str(taxon_id),
        release_version=release_version,
        catalog_sha256=catalog_sha256,
        retrieved_at=retrieved_at,
        provider_url=provider_url,
        cfg=cfg,
    )
    organism_covered = int(stats["organism_scoped_rows"]) > 0
    status = "api_real" if not data.empty else (
        "organism_not_covered" if not organism_covered else "no_candidate_gene_matches"
    )
    audit = response_audit_fields(catalog_response, affects_score=not data.empty) if catalog_response else {}
    manifest = {
        "source": "amrfinderplus",
        "provider": str(cfg["provider_name"]),
        "mode": mode,
        "organism_name": str(organism_name),
        "taxon_id": str(taxon_id),
        "query_cache_key": cache_key,
        "source_used": "api_real",
        "retrieval_status": status,
        "cache_hit": False,
        "api_attempted": True,
        "api_success": True,
        "query_complete": True,
        "candidate_count": int(len(candidates)),
        "candidate_gene_matches": int(stats["candidate_gene_matches"]),
        "point_mutation_catalog_rows": int(stats["point_mutation_catalog_rows"]),
        "organism_scoped_rows": int(stats["organism_scoped_rows"]),
        "release_version": release_version,
        "catalog_sha256": catalog_sha256,
        "version_url": version_url,
        "catalog_url": catalog_url,
        "affected_candidate_count": int(len(data)),
        "updated_cell_count": int(len(data)),
        "affects_score": bool(len(data)),
        "notes": [
            "positive_matches_only; absence is never encoded as resistance_emergence_risk=0",
            "catalog count is not used to scale the score because curation intensity is not a biological probability",
        ],
        "generated_at_utc": retrieved_at,
        **audit,
    }

    if not no_write_cache:
        cache.setdefault("entries", {})[cache_key] = {
            "saved_at_utc": _utc_now(),
            "rows": data.to_dict(orient="records"),
            "manifest": manifest,
        }
        _write_cache(workspace, config, cache)

    return {
        "evolutionary_escape_risk_data": data,
        "manifest": manifest,
        "manifest_path": _write_manifest(workspace, manifest),
    }
