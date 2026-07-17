from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .online_provider_connectivity import CONSERVATIVE_WARNING


TECHNICAL_STATUS_MAP = {
    "timeout": "unresolved",
    "http_error": "provider_failed",
    "schema_error": "unresolved",
    "unresolved": "unresolved",
    "provider_failed": "provider_failed",
    "unavailable": "unresolved",
    "not_applicable": "not_applicable",
}
PROVIDER_WARNINGS = {
    "VFDB": "VFDB not_found or unresolved must not be interpreted as absence of virulence.",
    "DEG": "DEG not_found or unresolved must not be interpreted as absence of essentiality.",
    "BV-BRC": "BV-BRC not_found or unresolved must not be interpreted as absence of genomic or resistance evidence.",
}
CONTAINER_KEYS = {
    "VFDB": ("results", "data", "records", "entries"),
    "DEG": ("results", "data", "records", "entries"),
    "BV-BRC": ("results", "data", "records", "response"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _records(payload: Any, provider: str) -> tuple[list[dict[str, Any]], bool]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], all(isinstance(item, dict) for item in payload)
    if not isinstance(payload, dict):
        return [], False
    for key in CONTAINER_KEYS[provider]:
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)], all(isinstance(item, dict) for item in value)
        if provider == "BV-BRC" and isinstance(value, dict) and isinstance(value.get("docs"), list):
            docs = value["docs"]
            return [item for item in docs if isinstance(item, dict)], all(isinstance(item, dict) for item in docs)
        return [], False
    return [], False


def _first(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _base(
    provider: str,
    organism_label: str,
    taxon_id: str | int | None,
    query_used: str,
    source_url: str,
    checked_at: str,
) -> dict[str, Any]:
    return {
        "organism_label": organism_label,
        "taxon_id": taxon_id or "",
        "provider_name": provider,
        "source_url": source_url,
        "query_used": query_used,
        "checked_at": checked_at or _now(),
        "normalized_at": _now(),
        "affects_score": False,
        "external_evidence_normalized": True,
        "experimental_validation_supported": False,
    }


def _status_record(
    provider: str,
    status: str,
    organism_label: str,
    taxon_id: str | int | None,
    query_used: str,
    source_url: str,
    checked_at: str,
) -> dict[str, Any]:
    evidence_status = "not_found" if status == "no_results" else TECHNICAL_STATUS_MAP.get(status, "unresolved")
    warning = PROVIDER_WARNINGS[provider] + " " + CONSERVATIVE_WARNING
    return {
        **_base(provider, organism_label, taxon_id, query_used, source_url, checked_at),
        "candidate_gene": "",
        "protein_id": "",
        "evidence_type": "unresolved_provider" if evidence_status in {"unresolved", "provider_failed"} else _default_type(provider),
        "evidence_status": evidence_status,
        "evidence_value": "",
        "evidence_confidence_label": "limited_query_no_record" if evidence_status == "not_found" else "provider_unresolved",
        "evidence_scope": _default_type(provider),
        "source_record_id": "",
        "interpretation_warning": warning,
    }


def _default_type(provider: str) -> str:
    return {"VFDB": "virulence_association", "DEG": "essentiality_association", "BV-BRC": "protein_annotation"}[provider]


def _normalize(
    payload: Any,
    provider: str,
    mapper: Callable[[dict[str, Any]], list[tuple[str, str]]],
    *,
    organism_label: str,
    taxon_id: str | int | None,
    query_used: str = "",
    source_url: str = "",
    checked_at: str = "",
    provider_status: str = "success",
) -> list[dict[str, Any]]:
    if provider_status != "success":
        return [_status_record(provider, provider_status, organism_label, taxon_id, query_used, source_url, checked_at)]
    records, schema_valid = _records(payload, provider)
    if not schema_valid:
        return [_status_record(provider, "schema_error", organism_label, taxon_id, query_used, source_url, checked_at)]
    if not records:
        return [_status_record(provider, "no_results", organism_label, taxon_id, query_used, source_url, checked_at)]
    normalized: list[dict[str, Any]] = []
    for raw in records:
        gene = _first(raw, "gene", "gene_name", "locus_tag", "symbol")
        protein_id = _first(raw, "protein_id", "protein", "accession", "patric_id", "locus_tag")
        source_record_id = _first(raw, "vfdb_id", "deg_id", "feature_id", "patric_id", "id", "accession")
        for evidence_type, evidence_value in mapper(raw):
            normalized.append({
                **_base(provider, organism_label, taxon_id, query_used, source_url, checked_at),
                "candidate_gene": gene,
                "protein_id": protein_id,
                "evidence_type": evidence_type,
                "evidence_status": "supported",
                "evidence_value": evidence_value,
                "evidence_confidence_label": "explicit_external_record",
                "evidence_scope": evidence_type,
                "source_record_id": source_record_id,
                "interpretation_warning": PROVIDER_WARNINGS[provider] + " Supported denotes an explicit external record, not experimental validation by this pipeline.",
            })
    if not normalized:
        return [_status_record(provider, "schema_error", organism_label, taxon_id, query_used, source_url, checked_at)]
    return normalized


def _vfdb_mapping(record: dict[str, Any]) -> list[tuple[str, str]]:
    value = _first(record, "virulence_factor", "factor", "product", "description", "vf_name")
    return [("virulence_association", value)] if value or _first(record, "vfdb_id", "id") else []


def _deg_mapping(record: dict[str, Any]) -> list[tuple[str, str]]:
    value = _first(record, "evidence", "experiment", "method", "essentiality", "description")
    return [("essentiality_association", value)] if value or _first(record, "deg_id", "id") else []


def _bvbrc_mapping(record: dict[str, Any]) -> list[tuple[str, str]]:
    mapped: list[tuple[str, str]] = []
    annotation = _first(record, "product", "function", "annotation", "pgfam_id", "figfam_id", "feature_type")
    if annotation or _first(record, "patric_id", "feature_id"):
        mapped.append(("protein_annotation", annotation))
    resistance = _first(record, "antibiotic", "resistance", "resistance_gene", "amr", "amr_evidence")
    if resistance:
        mapped.append(("resistance_association", resistance))
    taxonomy = _first(record, "taxonomy_resolution", "resolved_taxon_id")
    if taxonomy:
        mapped.append(("taxonomy_resolution", taxonomy))
    return mapped


def normalize_vfdb_records(payload: Any, **context: Any) -> list[dict[str, Any]]:
    return _normalize(payload, "VFDB", _vfdb_mapping, **context)


def normalize_deg_records(payload: Any, **context: Any) -> list[dict[str, Any]]:
    return _normalize(payload, "DEG", _deg_mapping, **context)


def normalize_bvbrc_records(payload: Any, **context: Any) -> list[dict[str, Any]]:
    return _normalize(payload, "BV-BRC", _bvbrc_mapping, **context)


def normalize_provider_payloads(provider_payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    adapters = {"VFDB": normalize_vfdb_records, "DEG": normalize_deg_records, "BV-BRC": normalize_bvbrc_records}
    rows: list[dict[str, Any]] = []
    for provider, item in provider_payloads.items():
        if provider not in adapters:
            raise ValueError(f"unsupported provider adapter: {provider}")
        context = {key: value for key, value in item.items() if key != "payload"}
        rows.extend(adapters[provider](item.get("payload"), **context))
    return rows


def write_provider_adapter_artifacts(rows: list[dict[str, Any]], output_dir: Path) -> list[str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames = ["external_provider_records_normalized.csv", "external_provider_records_normalized.json"]
    _write_csv(output_dir / filenames[0], rows)
    (output_dir / filenames[1]).write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
    for provider, filename in (("VFDB", "vfdb_normalized_records.csv"), ("DEG", "deg_normalized_records.csv"), ("BV-BRC", "bvbrc_normalized_records.csv")):
        _write_csv(output_dir / filename, [row for row in rows if row["provider_name"] == provider])
        filenames.append(filename)
    review_name = "EXTERNAL_PROVIDER_ADAPTERS_REVIEW.md"
    review = "\n".join([
        "# External Provider Adapters Review", "", "Phase 7E normalizes already obtained records and performs no network requests.", "",
        *[f"- {provider}: {sum(row['provider_name'] == provider for row in rows)} normalized records" for provider in ("VFDB", "DEG", "BV-BRC")], "",
        CONSERVATIVE_WARNING,
        "All records have `affects_score=false`. Supported means an explicit external record, not experimental validation.",
    ])
    (output_dir / review_name).write_text(review, encoding="utf-8")
    filenames.append(review_name)
    return filenames


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
