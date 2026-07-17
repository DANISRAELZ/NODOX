from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .external_provider_adapters import normalize_provider_payloads, write_provider_adapter_artifacts
from .online_provider_connectivity import CONSERVATIVE_WARNING


EVIDENCE_TYPES = {
    "seed_candidate", "protein_annotation", "functional_interaction", "domain_annotation",
    "literature_support", "virulence_association", "essentiality_association",
    "resistance_association", "taxonomy_resolution", "unresolved_provider",
}
STATUS_MAP = {
    "success": "supported", "no_results": "not_found", "unresolved": "unresolved",
    "timeout": "unresolved", "http_error": "provider_failed", "schema_error": "unresolved",
    "provider_failed": "provider_failed", "unavailable": "unresolved", "skipped": "not_applicable",
    "not_configured": "not_applicable",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_external_evidence(
    connectivity_rows: list[dict[str, Any]], candidates: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Normalize external audit records descriptively; no record can affect scoring."""
    candidates = candidates or []
    by_organism: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        key = (str(candidate.get("organism_label", "")), str(candidate.get("taxon_id", "")))
        by_organism.setdefault(key, []).append(candidate)
    normalized: list[dict[str, Any]] = []
    normalized_at = _now()
    for source in connectivity_rows:
        key = (str(source.get("organism_label", "")), str(source.get("taxon_id", "")))
        targets = by_organism.get(key) or [{}]
        provider_status = str(source.get("status", "unresolved"))
        status = STATUS_MAP.get(provider_status, "unresolved")
        evidence_type = str(source.get("evidence_scope", "unresolved_provider"))
        if status in {"unresolved", "provider_failed"}:
            evidence_type = "unresolved_provider"
        if evidence_type not in EVIDENCE_TYPES:
            evidence_type = "unresolved_provider"
        warning = CONSERVATIVE_WARNING
        if provider_status == "no_results":
            warning = "not_found reflects only this limited query; it is not proof of total biological or literature absence."
        if source.get("provider_name") == "UniProt":
            warning += " UniProt seed or annotation evidence is computational metadata, not experimental validation."
        for candidate in targets:
            normalized.append({
                "organism_label": source.get("organism_label", ""), "taxon_id": source.get("taxon_id", ""),
                "candidate_gene": candidate.get("candidate_gene", candidate.get("gene", "")),
                "protein_id": candidate.get("protein_id", ""), "provider_name": source.get("provider_name", ""),
                "evidence_type": evidence_type, "evidence_status": status,
                "evidence_value": source.get("records_found", 0),
                "evidence_confidence_label": "external_query_supported" if status == "supported" else "limited_or_unresolved",
                "evidence_scope": source.get("evidence_scope", ""), "source_record_id": candidate.get("source_record_id", ""),
                "source_url": source.get("provider_url", ""), "query_used": source.get("query_used", source.get("organism_query", "")),
                "checked_at": source.get("checked_at", ""), "normalized_at": normalized_at,
                "interpretation_warning": warning, "affects_score": False,
                "external_evidence_normalized": True, "experimental_validation_supported": False,
            })
    return normalized


def write_external_evidence_package(
    connectivity_rows: list[dict[str, Any]], candidates: list[dict[str, Any]], output_dir: Path,
    provider_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = normalize_external_evidence(connectivity_rows, candidates)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_rows = normalize_provider_payloads(provider_payloads) if provider_payloads is not None else []
    rows.extend(provider_rows)
    adapter_artifacts = write_provider_adapter_artifacts(provider_rows, output_dir) if provider_payloads is not None else []
    _write_csv(output_dir / "external_evidence_normalized.csv", rows)
    (output_dir / "external_evidence_normalized.json").write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
    by_org = _summary(rows, "organism_label")
    by_provider = _summary(rows, "provider_name")
    unresolved = [row for row in rows if row["evidence_status"] in {"unresolved", "provider_failed", "not_found"}]
    _write_csv(output_dir / "external_evidence_by_organism.csv", by_org)
    _write_csv(output_dir / "external_evidence_by_provider.csv", by_provider)
    _write_csv(output_dir / "unresolved_external_evidence.csv", unresolved)
    manifest = {
        "phase": "7D_external_evidence_normalization", "generated_at": _now(), "record_count": len(rows),
        "candidate_count": len({(r["organism_label"], r["protein_id"], r["candidate_gene"]) for r in rows if r["protein_id"] or r["candidate_gene"]}),
        "external_evidence_normalized": True, "affects_score": False, "scores_modified": False,
        "generated_artifacts": ["external_evidence_normalized.csv", "external_evidence_normalized.json",
            "external_evidence_by_organism.csv", "external_evidence_by_provider.csv",
            "unresolved_external_evidence.csv", "EXTERNAL_EVIDENCE_NORMALIZATION_REVIEW.md", "external_evidence_manifest.json",
            *adapter_artifacts],
        "phase_7e_provider_adapters_enabled": provider_payloads is not None,
        "provider_record_count": len(provider_rows),
    }
    (output_dir / "external_evidence_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    status_counts = Counter(row["evidence_status"] for row in rows)
    review = "\n".join([
        "# External Evidence Normalization Review", "", "## Coverage", "",
        f"- Organisms analyzed: {', '.join(sorted({str(r['organism_label']) for r in rows})) or 'none'}",
        f"- Providers consulted: {', '.join(sorted({str(r['provider_name']) for r in rows})) or 'none'}",
        f"- Candidates with normalized evidence: {manifest['candidate_count']}",
        *[f"- Provider `{item['provider_name']}` records: {item['record_count']}" for item in by_provider],
        f"- unresolved/provider_failed/no_results-derived records: {sum(status_counts[s] for s in ('unresolved', 'provider_failed', 'not_found'))}", "",
        "## Conservative interpretation", "", CONSERVATIVE_WARNING,
        "`no_results` is normalized as `not_found` only for the limited query. `unresolved` is not negative evidence.",
        "Every record has `affects_score=false`; no scoring or ranking rule was modified.",
        "This package is computational evidence normalization, not experimental validation.",
    ])
    (output_dir / "EXTERNAL_EVIDENCE_NORMALIZATION_REVIEW.md").write_text(review, encoding="utf-8")
    return {"output_dir": str(output_dir), "rows": rows, "manifest": manifest}


def _summary(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(field, "")) for row in rows)
    return [{field: key, "record_count": value} for key, value in sorted(counts.items())]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
