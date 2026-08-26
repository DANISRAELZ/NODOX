from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

import pandas as pd

from .online.provider_modes import normalize_provider_mode
from .provider_response_audit import ProviderResponse, request_provider_payload, response_audit_fields

CONSERVATION_COLUMNS = [
    "protein_id",
    "gene",
    "core_genome_presence",
    "strain_coverage_score",
    "allelic_conservation",
    "variant_burden",
    "database",
]


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
        return {"schema_version": 2, "updated_at_utc": None, "entries": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("schema_version", 2)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_bvbrc_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["schema_version"] = max(int(payload.get("schema_version", 1)), 2)
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def _api_get_json(url: str, cfg: dict[str, Any]) -> tuple[Any | None, list[str], ProviderResponse | None]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        response = request_provider_payload(
            url,
            timeout=timeout,
            user_agent=user_agent,
            accept="application/json",
            opener=urlopen,
        )
        if response.error_status == "":
            return response.payload, errors, response
        errors.append(response.rejection_reason or response.error_status)
        if response.http_status == 429 and attempt < retries:
            time.sleep(backoff * (2**attempt))
            continue
        return None, errors, response
    return None, errors, None


def _get_candidate_proteins(workspace: Path) -> pd.DataFrame:
    for filename in ["strain_conservation.csv", "essentiality.csv"]:
        path = workspace / "data_raw" / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "protein_id" not in df.columns:
            continue
        rows: list[dict[str, str]] = []
        for _, row in df.iterrows():
            protein_id = str(row.get("protein_id", "")).strip().upper()
            if not protein_id:
                continue
            gene = str(row.get("gene", "")).strip() or protein_id
            rows.append({"protein_id": protein_id, "gene": gene})
        if rows:
            return (
                pd.DataFrame(rows)
                .drop_duplicates(subset=["protein_id"])
                .sort_values("protein_id")
                .reset_index(drop=True)
            )
    return pd.DataFrame(columns=["protein_id", "gene"])


def _cache_key(taxon_id: str | None, proteins: pd.DataFrame) -> str:
    ids = "|".join(sorted(proteins["protein_id"].astype(str).str.upper().tolist()))
    digest = hashlib.sha256(ids.encode("utf-8")).hexdigest()[:16]
    return f"bvbrc::{taxon_id or 'unknown'}::{digest}"


def _candidate_genes(proteins: pd.DataFrame, cfg: dict[str, Any] | None = None) -> list[str]:
    """Return every safe, unique candidate gene.

    Historically this function stopped after ``max_candidate_genes`` (50),
    silently limiting whole-proteome runs. The configuration value is now a
    *batch size* and no longer a biological coverage limit.
    """
    genes: list[str] = []
    seen: set[str] = set()
    for value in proteins.get("gene", pd.Series(dtype=str)).fillna("").astype(str):
        gene = value.strip()
        if not gene or not re.fullmatch(r"[A-Za-z0-9_.:-]+", gene):
            continue
        folded = gene.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        genes.append(gene)
    return genes


def _candidate_gene_batches(proteins: pd.DataFrame, cfg: dict[str, Any]) -> list[list[str]]:
    genes = _candidate_genes(proteins, cfg)
    batch_size = int(cfg.get("candidate_gene_batch_size", cfg.get("max_candidate_genes", 50)))
    if batch_size <= 0:
        raise ValueError("BV-BRC candidate_gene_batch_size must be greater than zero")
    return [genes[index : index + batch_size] for index in range(0, len(genes), batch_size)]


def _build_query_url(
    taxon_id: str,
    cfg: dict[str, Any],
    proteins: pd.DataFrame,
    *,
    genes: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> str:
    selected_genes = list(genes) if genes is not None else _candidate_genes(proteins, cfg)
    gene_filter = f"&in(gene,({','.join(selected_genes)}))" if selected_genes else ""
    page_size = int(limit or cfg.get("feature_page_size", 25000))
    limit_clause = f"limit({page_size},{int(offset)})" if offset else f"limit({page_size})"
    query = (
        f"eq(taxon_id,{taxon_id})&eq(feature_type,CDS){gene_filter}"
        "&select(feature_id,patric_id,protein_id,refseq_locus_tag,gene,product,pgfam_id,figfam_id,genome_id)"
        f"&{limit_clause}&http_accept=application/json"
    )
    return f"{str(cfg['provider_base_url']).rstrip('/')}/genome_feature/?{quote(query, safe='(),=&')}"


def _build_genome_query_url(taxon_id: str, cfg: dict[str, Any]) -> str:
    limit = int(cfg.get("genome_query_limit", 10000))
    query = f"eq(taxon_id,{taxon_id})&select(genome_id)&limit({limit})&http_accept=application/json"
    return f"{str(cfg['provider_base_url']).rstrip('/')}/genome/?{quote(query, safe='(),=&')}"


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


def _is_structured_bvbrc_payload(payload: Any, response: ProviderResponse | None) -> bool:
    return bool(response is not None and response.payload_type == "json" and isinstance(payload, (dict, list)))


def _conservative_status(response: ProviderResponse | None, records: list[dict[str, Any]] | None = None) -> str:
    if response is None:
        return "unresolved"
    if response.error_status:
        return response.error_status
    if response.payload_type == "empty":
        return "verified_empty_payload"
    if response.payload_type == "html":
        return "html_instead_of_structured_payload"
    if response.payload_type != "json":
        return "unresolved"
    if records is not None and not records:
        return "verified_empty_payload"
    return "api_real"


def _response_total(response: ProviderResponse | None, observed_count: int) -> int:
    if response is None:
        return observed_count
    content_range = str(response.headers.get("content-range", ""))
    match = re.search(r"/(\d+)\s*$", content_range)
    return int(match.group(1)) if match else observed_count


def _derive_rows(
    proteins: pd.DataFrame,
    payload: Any,
    genome_ids: set[str],
    config: dict[str, Any],
) -> tuple[pd.DataFrame, int, list[str]]:
    records = _as_records(payload)
    by_gene: dict[str, set[str]] = defaultdict(set)
    family_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in records:
        genome_id = str(record.get("genome_id") or "").strip()
        gene = str(record.get("gene") or "").strip().casefold()
        if gene and genome_id:
            by_gene[gene].add(genome_id)
        family = str(record.get("pgfam_id") or record.get("figfam_id") or "").strip()
        if family and gene:
            family_counts[gene][family] += 1

    total_genomes = len(genome_ids)
    rows: list[dict[str, Any]] = []
    matched = 0
    for _, protein in proteins.iterrows():
        protein_id = str(protein["protein_id"]).strip().upper()
        gene = str(protein["gene"]).strip()
        present = by_gene.get(gene.casefold(), set()) | by_gene.get(protein_id.casefold(), set())
        if not present:
            continue
        matched += 1
        presence = len(present) / total_genomes if total_genomes else float("nan")
        counts = family_counts.get(gene.casefold()) or family_counts.get(protein_id.casefold()) or {}
        observed_families = sum(counts.values())
        allelic = max(counts.values()) / observed_families if observed_families else float("nan")
        variant_burden = 1.0 - allelic if observed_families else float("nan")
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
    notes = [
        "coverage_denominator_is_complete_taxon_id_genome_query",
        "candidates_without_matched_features_are_omitted_not_encoded_as_zero",
        "allelic_conservation_is_dominant_observed_family_fraction; missing family annotations remain empty",
    ]
    return pd.DataFrame(rows, columns=CONSERVATION_COLUMNS), matched, notes


def _write_manifest(workspace: Path, manifest: dict[str, Any]) -> Path:
    path = workspace / "results" / "bvbrc_conservation_manifest.json"
    _json_dump(path, manifest)
    return path


def _cache_manifest(cached_manifest: dict[str, Any], mode: str) -> dict[str, Any]:
    manifest = {**cached_manifest}
    manifest.update(
        {
            "mode": mode,
            "source_used": "cache",
            "cache_hit": True,
            "api_attempted": False,
            # Cached provider evidence remains technically successful even though
            # no live API call was made in this invocation.
            "api_success": False,
        }
    )
    notes = list(manifest.get("notes", []))
    if "served_from_cache" not in notes:
        notes.append("served_from_cache")
    manifest["notes"] = notes
    return manifest


def _effective_conservation_updates(df: pd.DataFrame) -> tuple[int, int]:
    scoring_columns = [
        "core_genome_presence",
        "strain_coverage_score",
        "allelic_conservation",
        "variant_burden",
    ]
    if df.empty:
        return 0, 0
    numeric = df.reindex(columns=scoring_columns).apply(pd.to_numeric, errors="coerce")
    present = numeric.notna()
    return int(present.any(axis=1).sum()), int(present.sum().sum())


def _empty_result(workspace: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.setdefault("affects_score", False)
    manifest.setdefault("generated_at_utc", _utc_now())
    return {
        "strain_conservation_data": pd.DataFrame(columns=CONSERVATION_COLUMNS),
        "manifest": manifest,
        "manifest_path": _write_manifest(workspace, manifest),
    }


def _fetch_feature_batch(
    taxon_id: str,
    cfg: dict[str, Any],
    proteins: pd.DataFrame,
    genes: list[str],
) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    first_url = _build_query_url(taxon_id, cfg, proteins, genes=genes)
    payload, errors, response = _api_get_json(first_url, cfg)
    if payload is None or not _is_structured_bvbrc_payload(payload, response):
        return None, {
            "url": first_url,
            "errors": errors,
            "response": response,
            "status": _conservative_status(response),
            "pages": 0,
            "total": 0,
        }

    records = _as_records(payload)
    feature_total = _response_total(response, len(records))
    feature_limit = int(cfg.get("feature_query_limit", 50000))
    page_size = int(cfg.get("feature_page_size", 25000))
    if feature_total > feature_limit:
        return None, {
            "url": first_url,
            "errors": errors + ["feature_query_exceeds_configured_limit"],
            "response": response,
            "status": "response_truncated_no_evidence",
            "pages": 1,
            "total": feature_total,
        }

    pages = 1
    while len(records) < feature_total:
        page_url = _build_query_url(
            taxon_id,
            cfg,
            proteins,
            genes=genes,
            limit=min(page_size, feature_total - len(records)),
            offset=len(records),
        )
        page_payload, page_errors, page_response = _api_get_json(page_url, cfg)
        errors.extend(page_errors)
        if page_payload is None or not _is_structured_bvbrc_payload(page_payload, page_response):
            return None, {
                "url": page_url,
                "errors": errors,
                "response": page_response,
                "status": "paginated_response_incomplete",
                "pages": pages,
                "total": feature_total,
            }
        page_records = _as_records(page_payload)
        if not page_records:
            return None, {
                "url": page_url,
                "errors": errors + ["empty_bvbrc_feature_page"],
                "response": page_response,
                "status": "paginated_response_incomplete",
                "pages": pages,
                "total": feature_total,
            }
        records.extend(page_records)
        pages += 1

    if len(records) != feature_total:
        return None, {
            "url": first_url,
            "errors": errors + ["bvbrc_feature_count_mismatch"],
            "response": response,
            "status": "paginated_response_incomplete",
            "pages": pages,
            "total": feature_total,
        }
    return records, {
        "url": first_url,
        "errors": errors,
        "response": response,
        "status": "api_real" if records else "verified_empty_payload",
        "pages": pages,
        "total": feature_total,
    }


def fetch_bvbrc_strain_conservation(
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
    proteins = _get_candidate_proteins(workspace)
    cache = load_bvbrc_cache(workspace, config)
    cache_key = _cache_key(taxon_id, proteins)
    cfg = config["online_sources"]["bvbrc"]
    common = {
        "source": "bvbrc",
        "provider": str(cfg["provider_name"]),
        "provider_name": str(cfg["provider_name"]),
        "provider_mode": "online",
        "mode": mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "query_cache_key": cache_key,
        "proteins_queried": int(len(proteins)),
    }

    if not bool(cfg.get("enabled", True)):
        return _empty_result(
            workspace,
            {
                **common,
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
                "notes": ["provider_disabled_before_cache_or_network_lookup"],
            },
        )

    cached_entry = cache["entries"].get(cache_key)
    cached_manifest = cached_entry.get("manifest", {}) if isinstance(cached_entry, dict) else {}
    if not refresh_cache and cached_entry and bool(cached_manifest.get("query_complete", False)):
        df = pd.DataFrame(cached_entry.get("strain_conservation_rows", []), columns=CONSERVATION_COLUMNS)
        manifest = _cache_manifest(cached_manifest, mode)
        affected_candidate_count, updated_cell_count = _effective_conservation_updates(df)
        manifest.update(
            {
                "affected_candidate_count": affected_candidate_count,
                "updated_cell_count": updated_cell_count,
                "affects_score": bool(updated_cell_count),
            }
        )
        return {
            "strain_conservation_data": df,
            "manifest": manifest,
            "manifest_path": _write_manifest(workspace, manifest),
        }

    if mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache BV-BRC utilizable para este conjunto de proteinas.")
    if proteins.empty or not taxon_id:
        reason = "no_candidate_proteins" if proteins.empty else "missing_taxon_id"
        return _empty_result(
            workspace,
            {
                **common,
                "protein_count_mapped": 0,
                "source_used": "empty_candidates",
                "retrieval_status": reason,
                "cache_hit": False,
                "provider_attempted": False,
                "provider_success": False,
                "api_attempted": False,
                "api_success": False,
                "fallback_reason": reason,
                "evidence_level": "unresolved",
                "notes": [reason],
            },
        )

    batches = _candidate_gene_batches(proteins, cfg)
    all_genes = [gene for batch in batches for gene in batch]
    if not all_genes:
        return _empty_result(
            workspace,
            {
                **common,
                "protein_count_mapped": 0,
                "candidate_gene_count": 0,
                "source_used": "invalid_candidate_identifiers",
                "retrieval_status": "invalid_candidate_identifiers",
                "cache_hit": False,
                "provider_attempted": False,
                "provider_success": False,
                "api_attempted": False,
                "api_success": False,
                "fallback_reason": "no_safe_candidate_gene_symbols",
                "evidence_level": "unresolved",
                "notes": ["No BV-BRC query was sent because candidate gene symbols did not pass the conservative identifier filter."],
            },
        )

    genome_url = _build_genome_query_url(taxon_id, cfg)
    genome_payload, genome_errors, genome_response = _api_get_json(genome_url, cfg)
    if genome_payload is None or not _is_structured_bvbrc_payload(genome_payload, genome_response):
        if mode == "online_optional" and cached_entry and bool(cached_manifest.get("query_complete", False)):
            df = pd.DataFrame(cached_entry.get("strain_conservation_rows", []), columns=CONSERVATION_COLUMNS)
            manifest = _cache_manifest(cached_manifest, mode)
            manifest.update({"api_attempted": True, "fallback_reason": "api_failed_fallback_cache"})
            return {"strain_conservation_data": df, "manifest": manifest, "manifest_path": _write_manifest(workspace, manifest)}
        audit = response_audit_fields(genome_response, affects_score=False) if genome_response else {"provider_url": genome_url}
        return _empty_result(
            workspace,
            {
                **common,
                "protein_count_mapped": 0,
                "source_used": "api_failed",
                "retrieval_status": _conservative_status(genome_response),
                "cache_hit": False,
                "provider_attempted": True,
                "provider_success": False,
                "api_attempted": True,
                "api_success": False,
                "fallback_reason": "genome_query_failed_no_cache",
                "evidence_level": "unresolved",
                "notes": genome_errors,
                **audit,
            },
        )

    genome_records = _as_records(genome_payload)
    genome_ids = {
        str(record.get("genome_id") or "").strip()
        for record in genome_records
        if str(record.get("genome_id") or "").strip()
    }
    genome_total = _response_total(genome_response, len(genome_records))
    genome_limit = int(cfg.get("genome_query_limit", 10000))
    if not genome_ids:
        audit = response_audit_fields(genome_response, affects_score=False) if genome_response else {"provider_url": genome_url}
        return _empty_result(
            workspace,
            {
                **common,
                "protein_count_mapped": 0,
                "genomes_retrieved": 0,
                "source_used": _conservative_status(genome_response, genome_records),
                "retrieval_status": _conservative_status(genome_response, genome_records),
                "cache_hit": False,
                "provider_attempted": True,
                "provider_success": False,
                "api_attempted": True,
                "api_success": True,
                "fallback_reason": "verified_empty_payload_no_bvbrc_genomes",
                "evidence_level": "unresolved",
                "notes": genome_errors + ["Empty structured BV-BRC genome payload; no conservation evidence inferred."],
                **audit,
            },
        )
    if genome_total > len(genome_records) or genome_total > genome_limit:
        return _empty_result(
            workspace,
            {
                **common,
                "protein_count_mapped": 0,
                "genomes_retrieved": len(genome_ids),
                "genome_records_available": genome_total,
                "source_used": "response_truncated",
                "retrieval_status": "response_truncated_no_evidence",
                "cache_hit": False,
                "provider_attempted": True,
                "provider_success": False,
                "api_attempted": True,
                "api_success": True,
                "fallback_reason": "genome_query_incomplete_or_exceeds_configured_limit",
                "evidence_level": "unresolved",
                "notes": ["The genome denominator is incomplete or exceeds the configured maximum, so no conservation values were inferred."],
                "genome_provider_url": genome_url,
            },
        )

    all_records: list[dict[str, Any]] = []
    all_errors = list(genome_errors)
    total_pages = 0
    batch_summaries: list[dict[str, Any]] = []
    first_response: ProviderResponse | None = None
    first_provider_url = ""
    for batch_index, batch_genes in enumerate(batches, start=1):
        batch_records, batch_info = _fetch_feature_batch(taxon_id, cfg, proteins, batch_genes)
        all_errors.extend(batch_info["errors"])
        total_pages += int(batch_info["pages"])
        if first_response is None and batch_info.get("response") is not None:
            first_response = batch_info["response"]
            first_provider_url = str(batch_info["url"])
        batch_summaries.append(
            {
                "batch": batch_index,
                "gene_count": len(batch_genes),
                "record_count": len(batch_records or []),
                "pages": int(batch_info["pages"]),
                "status": str(batch_info["status"]),
            }
        )
        if batch_records is None:
            audit = response_audit_fields(batch_info.get("response"), affects_score=False) if batch_info.get("response") else {"provider_url": batch_info["url"]}
            return _empty_result(
                workspace,
                {
                    **common,
                    "protein_count_mapped": 0,
                    "candidate_gene_count": len(all_genes),
                    "candidate_gene_batch_size": int(cfg.get("candidate_gene_batch_size", cfg.get("max_candidate_genes", 50))),
                    "feature_batches_total": len(batches),
                    "feature_batches_completed": batch_index - 1,
                    "batch_summaries": batch_summaries,
                    "genomes_retrieved": len(genome_ids),
                    "source_used": str(batch_info["status"]),
                    "retrieval_status": "batched_response_incomplete",
                    "cache_hit": False,
                    "provider_attempted": True,
                    "provider_success": False,
                    "api_attempted": True,
                    "api_success": False,
                    "fallback_reason": "bvbrc_feature_batch_failed",
                    "evidence_level": "unresolved",
                    "query_complete": False,
                    "notes": all_errors + ["No BV-BRC conservation values were inferred because complete candidate-gene coverage is required."],
                    "genome_provider_url": genome_url,
                    **audit,
                },
            )
        all_records.extend(batch_records)

    df, matched, derive_notes = _derive_rows(proteins, all_records, genome_ids, config)
    affected_candidate_count, updated_cell_count = _effective_conservation_updates(df)
    audit = response_audit_fields(first_response, affects_score=bool(updated_cell_count)) if first_response else {"provider_url": first_provider_url, "affects_score": bool(updated_cell_count)}
    manifest = {
        **common,
        "candidate_genes_queried": all_genes,
        "candidate_gene_count": len(all_genes),
        "candidate_gene_batch_size": int(cfg.get("candidate_gene_batch_size", cfg.get("max_candidate_genes", 50))),
        "candidate_gene_coverage_fraction": round(len(all_genes) / max(len(proteins), 1), 6),
        "feature_batches_total": len(batches),
        "feature_batches_completed": len(batches),
        "batch_summaries": batch_summaries,
        "protein_count_mapped": int(matched),
        "genomes_retrieved": int(len(genome_ids)),
        "genome_records_available": int(genome_total),
        "feature_records_retrieved": int(len(all_records)),
        "feature_records_available": int(len(all_records)),
        "feature_pages_retrieved": int(total_pages),
        "query_complete": True,
        "source_used": "api_real" if matched else "bvbrc_filtered_no_matches",
        "retrieval_status": "api_real" if matched else "not_found",
        "cache_hit": False,
        "provider_attempted": True,
        "provider_success": True,
        "api_attempted": True,
        "api_success": True,
        "fallback_reason": None if matched else "no_bvbrc_matches_for_workspace_candidates",
        "evidence_level": "computational_online_evidence" if matched else "unresolved",
        "data_realism_flag": "computed_online" if matched else "unresolved",
        "notes": all_errors + derive_notes + ["All safe candidate genes were queried in bounded batches; max_candidate_genes is retained only as a backward-compatible batch-size fallback."],
        "generated_at_utc": _utc_now(),
        "genome_provider_url": genome_url,
        **audit,
        "affected_candidate_count": int(affected_candidate_count),
        "updated_cell_count": int(updated_cell_count),
        "affects_score": bool(updated_cell_count),
    }
    if not no_write_cache:
        cache["entries"][cache_key] = {
            "saved_at_utc": _utc_now(),
            "strain_conservation_rows": df.to_dict(orient="records"),
            "manifest": manifest,
        }
        save_bvbrc_cache(workspace, config, cache)
    return {
        "strain_conservation_data": df,
        "manifest": manifest,
        "manifest_path": _write_manifest(workspace, manifest),
    }
