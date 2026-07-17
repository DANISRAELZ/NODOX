from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from .provider_contracts import PROVIDER_CONTRACTS
from .provider_response_audit import ProviderResponse, request_provider_payload


PHASE_7L_VERSION = "7L-2026-07-05"
NON_BLOCKING_NOTE = (
    "External provider evidence is non-blocking and does not directly alter "
    "therapeutic_priority_score."
)
PROVIDER_STATUSES = {
    "connected_structured",
    "connected_empty",
    "unavailable",
    "unsupported_payload",
    "deprecated_or_changed",
    "local_dataset_available",
    "local_dataset_missing",
    "skipped_not_applicable",
}
ONLINE_PROVIDERS: dict[str, dict[str, Any]] = {
    "uniprot": {
        "provider_name": "UniProt",
        "endpoint": "https://rest.uniprot.org/uniprotkb/search?query=taxonomy_id:562&format=json&size=1",
        "accept": "application/json",
        "expected_payload_types": {"json"},
    },
    "string": {
        "provider_name": "STRING",
        "endpoint": "https://string-db.org/api/json/get_string_ids?identifiers=PA0001&species=287&limit=1",
        "accept": "application/json",
        "expected_payload_types": {"json"},
    },
    "interpro": {
        "provider_name": "InterPro",
        "endpoint": "https://www.ebi.ac.uk/interpro/api/protein/UniProt/?taxon_id=562&page_size=1",
        "accept": "application/json",
        "expected_payload_types": {"json"},
    },
    "bvbrc": {
        "provider_name": "BV-BRC",
        "endpoint": "https://www.bv-brc.org/api/genome/?eq(taxon_id,562)&limit(1)",
        "accept": "application/json",
        "expected_payload_types": {"json"},
    },
    "europe_pmc": {
        "provider_name": "Europe PMC",
        "endpoint": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=Pseudomonas%20aeruginosa&format=json&pageSize=1",
        "accept": "application/json",
        "expected_payload_types": {"json"},
    },
    "taxonomy": {
        "provider_name": "Taxonomy",
        "endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=taxonomy&term=562%5BTaxId%5D&retmode=json&retmax=1",
        "accept": "application/json",
        "expected_payload_types": {"json"},
    },
}
LOCAL_DATASET_PROVIDERS: dict[str, dict[str, Any]] = {
    "vfdb": {
        "provider_name": "VFDB",
        "expected_path": "data_external/vfdb.csv",
        "version_path": "data_external/vfdb.version.txt",
    },
    "deg": {
        "provider_name": "DEG",
        "expected_path": "data_external/deg.csv",
        "version_path": "data_external/deg.version.txt",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_error(message: object) -> str:
    text = " ".join(str(message or "").replace("\r", " ").replace("\n", " ").split())
    for marker in ("token=", "api_key=", "apikey=", "authorization="):
        lowered = text.lower()
        start = lowered.find(marker)
        if start >= 0:
            end = text.find(" ", start)
            end = len(text) if end < 0 else end
            text = text[: start + len(marker)] + "[REDACTED]" + text[end:]
    return text[:300]


def _record_count(payload: Any) -> int:
    if payload is None:
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("results", "data", "records", "entries", "genomes"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict) and isinstance(value.get("result"), list):
                return len(value["result"])
        response = payload.get("response")
        if isinstance(response, dict) and isinstance(response.get("docs"), list):
            return len(response["docs"])
        esearch = payload.get("esearchresult")
        if isinstance(esearch, dict):
            try:
                return int(esearch.get("count", 0) or 0)
            except (TypeError, ValueError):
                return 0
        if payload:
            return 1
    if isinstance(payload, str):
        return max(0, len([line for line in payload.splitlines() if line.strip()]) - 1)
    return 0


def _base_record(
    *,
    provider_key: str,
    provider_name: str,
    provider_mode: str,
    endpoint_or_path: str,
    provider_status: str,
    payload_type: str = "",
    structured: bool = False,
    evidence_items_count: int = 0,
    error_category: str = "",
    error_message_sanitized: str = "",
    retrieved_at: str | None = None,
    provenance: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if provider_status not in PROVIDER_STATUSES:
        raise ValueError(f"unsupported Phase 7L provider_status: {provider_status}")
    record = {
        "provider_key": provider_key,
        "provider_name": provider_name,
        "provider_mode": provider_mode,
        "provider_status": provider_status,
        "endpoint_or_path": endpoint_or_path,
        "payload_type": payload_type,
        "structured": bool(structured),
        "evidence_items_count": int(evidence_items_count),
        "affects_score": False,
        "error_category": error_category,
        "error_message_sanitized": _sanitize_error(error_message_sanitized),
        "retrieved_at": retrieved_at or _now(),
        "provenance": provenance,
        "phase": PHASE_7L_VERSION,
    }
    if extra:
        record.update(extra)
    return record


def normalize_online_provider_response(
    provider_key: str,
    response: ProviderResponse,
    *,
    expected_payload_types: set[str] | None = None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Map a transport response into the common Phase 7L provider status model."""
    spec = ONLINE_PROVIDERS.get(provider_key, {})
    provider_name = str(spec.get("provider_name") or PROVIDER_CONTRACTS[provider_key].provider_name)
    accepted = expected_payload_types or set(spec.get("expected_payload_types", {"json"}))
    count = _record_count(response.payload)
    if response.error_status:
        status = "unavailable"
        if response.error_status == "not_found":
            status = "deprecated_or_changed"
        return _base_record(
            provider_key=provider_key,
            provider_name=provider_name,
            provider_mode="online",
            endpoint_or_path=response.url,
            provider_status=status,
            payload_type=response.payload_type,
            error_category=response.error_status,
            error_message_sanitized=response.rejection_reason,
            retrieved_at=retrieved_at,
            provenance="phase_7l_online_provider_transport",
        )
    if response.payload_type in {"html", "zip", "unexpected_text", "undecodable"}:
        return _base_record(
            provider_key=provider_key,
            provider_name=provider_name,
            provider_mode="online",
            endpoint_or_path=response.url,
            provider_status="unsupported_payload",
            payload_type=response.payload_type,
            error_category=response.rejection_reason or "unsupported_payload",
            error_message_sanitized=response.rejection_reason,
            retrieved_at=retrieved_at,
            provenance="phase_7l_online_provider_contract",
        )
    if response.payload_type == "empty" or count == 0:
        return _base_record(
            provider_key=provider_key,
            provider_name=provider_name,
            provider_mode="online",
            endpoint_or_path=response.url,
            provider_status="connected_empty",
            payload_type=response.payload_type,
            structured=response.payload_type in accepted,
            evidence_items_count=0,
            retrieved_at=retrieved_at,
            provenance="phase_7l_online_provider_contract",
        )
    if response.payload_type in accepted:
        return _base_record(
            provider_key=provider_key,
            provider_name=provider_name,
            provider_mode="online",
            endpoint_or_path=response.url,
            provider_status="connected_structured",
            payload_type=response.payload_type,
            structured=True,
            evidence_items_count=count,
            retrieved_at=retrieved_at,
            provenance="phase_7l_online_provider_contract",
        )
    return _base_record(
        provider_key=provider_key,
        provider_name=provider_name,
        provider_mode="online",
        endpoint_or_path=response.url,
        provider_status="unsupported_payload",
        payload_type=response.payload_type,
        error_category="payload_type_not_accepted",
        error_message_sanitized=response.rejection_reason or response.payload_type,
        retrieved_at=retrieved_at,
        provenance="phase_7l_online_provider_contract",
    )


def resolve_online_provider(
    provider_key: str,
    *,
    endpoint: str | None = None,
    opener: Any = urlopen,
    timeout: float = 20,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    if provider_key not in ONLINE_PROVIDERS:
        raise ValueError(f"unknown Phase 7L online provider: {provider_key}")
    spec = ONLINE_PROVIDERS[provider_key]
    url = endpoint or str(spec["endpoint"])
    try:
        response = request_provider_payload(
            url,
            timeout=timeout,
            user_agent="nodos-funcionales-provider-integration-7L/1.0",
            accept=str(spec["accept"]),
            opener=opener,
        )
    except Exception as exc:  # noqa: BLE001 - provider audit must remain non-blocking.
        response = ProviderResponse(None, url, "", "", "network_error", _sanitize_error(exc), "unresolved")
    return normalize_online_provider_response(
        provider_key,
        response,
        expected_payload_types=set(spec["expected_payload_types"]),
        retrieved_at=retrieved_at,
    )


def resolve_local_dataset_provider(
    provider_key: str,
    workspace: Path,
    *,
    expected_path: str | Path | None = None,
    version_path: str | Path | None = None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    if provider_key not in LOCAL_DATASET_PROVIDERS:
        raise ValueError(f"unknown Phase 7L local dataset provider: {provider_key}")
    spec = LOCAL_DATASET_PROVIDERS[provider_key]
    workspace = Path(workspace)
    path = Path(expected_path or spec["expected_path"])
    if not path.is_absolute():
        path = workspace / path
    version_file = Path(version_path or spec["version_path"])
    if not version_file.is_absolute():
        version_file = workspace / version_file
    exists = path.exists() and path.is_file()
    checksum = hashlib.sha256(path.read_bytes()).hexdigest() if exists else ""
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else ""
    return _base_record(
        provider_key=provider_key,
        provider_name=str(spec["provider_name"]),
        provider_mode="local_dataset",
        endpoint_or_path=str(path),
        provider_status="local_dataset_available" if exists else "local_dataset_missing",
        payload_type=path.suffix.lstrip(".").lower() if exists else "",
        structured=exists,
        evidence_items_count=_line_count(path) if exists else 0,
        retrieved_at=retrieved_at,
        provenance="phase_7l_local_versioned_dataset",
        extra={
            "expected_local_path": str(path),
            "dataset_version": version,
            "checksum_sha256": checksum,
        },
    )


def resolve_human_essentiality_provider(
    *,
    organism_domain: str = "bacteria",
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    domain = str(organism_domain or "").strip().casefold()
    if domain in {"bacteria", "bacterial", "prokaryote", "prokaryotic"}:
        return _base_record(
            provider_key="human_essentiality",
            provider_name="Human essentiality",
            provider_mode="optional",
            endpoint_or_path="optional_host_context_layer",
            provider_status="skipped_not_applicable",
            retrieved_at=retrieved_at,
            provenance="phase_7l_optional_provider_applicability",
            extra={"organism_domain": organism_domain},
        )
    return _base_record(
        provider_key="human_essentiality",
        provider_name="Human essentiality",
        provider_mode="optional",
        endpoint_or_path="optional_host_context_layer",
        provider_status="local_dataset_missing",
        retrieved_at=retrieved_at,
        provenance="phase_7l_optional_provider_applicability",
        extra={"organism_domain": organism_domain},
    )


def run_full_provider_integration_audit(
    workspace: Path,
    output_dir: Path,
    *,
    opener: Any = urlopen,
    organism_domain: str = "bacteria",
    timeout: float = 20,
) -> dict[str, Any]:
    """Write a Phase 7L non-scoring provider integration report."""
    rows = [
        resolve_online_provider(provider_key, opener=opener, timeout=timeout)
        for provider_key in ONLINE_PROVIDERS
    ]
    rows.extend(
        resolve_local_dataset_provider(provider_key, workspace)
        for provider_key in LOCAL_DATASET_PROVIDERS
    )
    rows.append(resolve_human_essentiality_provider(organism_domain=organism_domain))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "full_provider_integration_status.csv", rows)
    (output_dir / "full_provider_integration_status.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    manifest = {
        "phase": PHASE_7L_VERSION,
        "generated_at": _now(),
        "provider_count": len(rows),
        "statuses": sorted({str(row["provider_status"]) for row in rows}),
        "affects_score": False,
        "scores_modified": False,
        "blocking_failures": 0,
        "note": NON_BLOCKING_NOTE,
        "generated_artifacts": [
            "full_provider_integration_status.csv",
            "full_provider_integration_status.json",
            "full_provider_integration_manifest.json",
            "FULL_PROVIDER_INTEGRATION_REVIEW.md",
        ],
    }
    (output_dir / "full_provider_integration_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (output_dir / "FULL_PROVIDER_INTEGRATION_REVIEW.md").write_text(_review_markdown(rows), encoding="utf-8")
    return {"output_dir": str(output_dir), "rows": rows, "manifest": manifest}


def _line_count(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as handle:
        lines = [line for line in handle if line.strip()]
    return max(0, len(lines) - 1)


def _review_markdown(rows: list[dict[str, Any]]) -> str:
    table = [
        "| Provider | Mode | Status | Structured | Items | Affects score | Endpoint or path |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        table.append(
            "| "
            + " | ".join(
                str(value).replace("|", "\\|").replace("\n", " ")
                for value in (
                    row["provider_name"],
                    row["provider_mode"],
                    row["provider_status"],
                    str(row["structured"]).lower(),
                    row["evidence_items_count"],
                    str(row["affects_score"]).lower(),
                    row["endpoint_or_path"],
                )
            )
            + " |"
        )
    return "\n".join(
        [
            "# Full Provider Integration Review",
            "",
            "Phase 7L records provider availability and payload structure only. It does not make biological absence claims.",
            "",
            NON_BLOCKING_NOTE,
            "",
            *table,
            "",
        ]
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
