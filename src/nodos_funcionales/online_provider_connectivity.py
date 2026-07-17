from __future__ import annotations

import csv
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from .online_http import urlopen_json


ALLOWED_STATUSES = {
    "success", "no_results", "unresolved", "provider_failed", "timeout",
    "http_error", "schema_error", "unavailable", "skipped", "not_configured",
}
CONSERVATIVE_WARNING = (
    "Provider failure, unresolved status, timeout, schema error, or no_results must not be interpreted as "
    "biological absence of essentiality, virulence, resistance, interaction, or literature evidence."
)
PROVIDERS: dict[str, dict[str, str]] = {
    "UniProt": {"category": "protein_annotation", "scope": "seed_candidate", "base": "https://rest.uniprot.org/uniprotkb/search"},
    "STRING": {"category": "functional_interaction", "scope": "functional_interaction", "base": "https://string-db.org/api/json/get_string_ids"},
    "InterPro": {"category": "domain_annotation", "scope": "domain_annotation", "base": "https://www.ebi.ac.uk/interpro/api/protein/UniProt/"},
    "Europe PMC": {"category": "literature", "scope": "literature_support", "base": "https://www.ebi.ac.uk/europepmc/webservices/rest/search"},
    "VFDB": {"category": "virulence", "scope": "virulence_association", "base": "http://www.mgc.ac.cn/VFs/Down/VFDB_setB_pro.fas.gz"},
    "DEG": {"category": "essentiality", "scope": "essentiality_association", "base": "http://origin.tubic.org/deg/public/index.php"},
    "BV-BRC": {"category": "genomics", "scope": "resistance_association", "base": "https://www.bv-brc.org/api/genome/"},
    "NCBI Taxonomy": {"category": "taxonomy", "scope": "taxonomy_resolution", "base": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_error(exc: BaseException) -> str:
    return " ".join(str(exc).split())[:300]


def _query(provider: str, organism_label: str, taxon_id: str | int | None) -> tuple[str, str]:
    taxon = str(taxon_id or "").strip()
    if provider == "UniProt":
        query = f"taxonomy_id:{taxon}" if taxon else f'organism_name:"{organism_label}"'
        return query, PROVIDERS[provider]["base"] + "?" + urlencode({"query": query, "format": "json", "size": 1})
    if provider == "STRING":
        query = taxon or organism_label
        return query, PROVIDERS[provider]["base"] + "?" + urlencode({"identifiers": organism_label, "species": taxon, "limit": 1})
    if provider == "InterPro":
        query = f"taxon_id={taxon}" if taxon else organism_label
        return query, PROVIDERS[provider]["base"] + "?" + urlencode({"taxon_id": taxon, "page_size": 1})
    if provider == "Europe PMC":
        query = f'TITLE_ABS:"{organism_label}"'
        return query, PROVIDERS[provider]["base"] + "?" + urlencode({"query": query, "format": "json", "pageSize": 1})
    if provider == "BV-BRC":
        query = f"taxon_id:{taxon}" if taxon else organism_label
        return query, PROVIDERS[provider]["base"] + "?" + urlencode({"eq(taxon_id)": taxon, "limit(1)": ""})
    if provider == "NCBI Taxonomy":
        query = f"{taxon}[TaxId]" if taxon else f"{organism_label}[Scientific Name]"
        return query, PROVIDERS[provider]["base"] + "?" + urlencode({"db": "taxonomy", "term": query, "retmode": "json", "retmax": 1})
    query = taxon or organism_label
    return query, PROVIDERS[provider]["base"]


def _record_count(payload: Any) -> int:
    if not isinstance(payload, (dict, list)):
        raise ValueError("provider response is not a JSON object or list")
    if isinstance(payload, list):
        return len(payload)
    for key in ("results", "resultList", "data", "records", "genomes"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict) and isinstance(value.get("result"), list):
            return len(value["result"])
    for key in ("count", "hitCount", "numFound"):
        if key in payload:
            return int(payload[key] or 0)
    esearch = payload.get("esearchresult")
    if isinstance(esearch, dict):
        return int(esearch.get("count", 0))
    if not payload:
        return 0
    raise ValueError("provider JSON did not contain a recognized result collection")


def check_provider_connectivity(
    provider_name: str,
    organism_label: str,
    taxon_id: str | int | None,
    *,
    requester: Callable[..., Any] = urlopen_json,
    timeout: float = 20,
    enabled: bool = True,
) -> dict[str, Any]:
    """Check one provider and return provenance without biological interpretation."""
    if provider_name not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider_name}")
    config = PROVIDERS[provider_name]
    query, url = _query(provider_name, organism_label, taxon_id)
    record: dict[str, Any] = {
        "provider_name": provider_name, "provider_url": url, "provider_category": config["category"],
        "organism_query": query, "query_used": query, "taxon_id": taxon_id or "", "organism_label": organism_label,
        "status": "skipped" if not enabled else "unresolved", "http_status": "", "records_found": 0,
        "error_type": "", "error_message": "", "blocking": False, "checked_at": _now(),
        "provenance_level": "external_connectivity_audit", "evidence_scope": config["scope"],
        "interpretation_warning": CONSERVATIVE_WARNING,
    }
    if not enabled:
        return record
    try:
        payload = requester(url, timeout=timeout, headers={"User-Agent": "nodos-funcionales-connectivity/1.0"})
        record["records_found"] = _record_count(payload)
        record["status"] = "success" if record["records_found"] else "no_results"
        record["http_status"] = 200
    except TimeoutError as exc:
        record.update(status="timeout", error_type="timeout", error_message=_safe_error(exc))
    except (socket.timeout,) as exc:
        record.update(status="timeout", error_type="timeout", error_message=_safe_error(exc))
    except HTTPError as exc:
        record.update(status="http_error", http_status=exc.code, error_type="http_error", error_message=_safe_error(exc))
    except (URLError, ConnectionError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        status = "timeout" if isinstance(reason, (TimeoutError, socket.timeout)) else "unavailable"
        record.update(status=status, error_type=status, error_message=_safe_error(exc))
    except (ValueError, TypeError, KeyError) as exc:
        record.update(status="schema_error", error_type="schema_error", error_message=_safe_error(exc))
    except Exception as exc:  # noqa: BLE001 - secondary providers must remain non-blocking.
        record.update(status="provider_failed", error_type=type(exc).__name__, error_message=_safe_error(exc))
    return record


def _provider_checker(name: str) -> Callable[..., dict[str, Any]]:
    def check(organism_label: str, taxon_id: str | int | None, **kwargs: Any) -> dict[str, Any]:
        return check_provider_connectivity(name, organism_label, taxon_id, **kwargs)
    return check


check_uniprot_connectivity = _provider_checker("UniProt")
check_string_connectivity = _provider_checker("STRING")
check_interpro_connectivity = _provider_checker("InterPro")
check_europe_pmc_connectivity = _provider_checker("Europe PMC")
check_vfdb_connectivity = _provider_checker("VFDB")
check_deg_connectivity = _provider_checker("DEG")
check_bvbrc_connectivity = _provider_checker("BV-BRC")
check_ncbi_taxonomy_connectivity = _provider_checker("NCBI Taxonomy")


def run_provider_connectivity_audit(
    organisms: list[dict[str, Any]], output_dir: Path, *, requester: Callable[..., Any] = urlopen_json,
    provider_names: list[str] | None = None, disabled_providers: set[str] | None = None,
) -> dict[str, Any]:
    names = provider_names or list(PROVIDERS)
    disabled = disabled_providers or set()
    rows = [
        check_provider_connectivity(name, str(org["organism_label"]), org.get("taxon_id"), requester=requester, enabled=name not in disabled)
        for org in organisms for name in names
    ]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "provider_connectivity_matrix.csv", rows)
    (output_dir / "provider_connectivity_matrix.json").write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
    manifest = {
        "phase": "7C_online_only_provider_connectivity", "generated_at": _now(), "record_count": len(rows),
        "organism_count": len(organisms), "providers": names, "blocking_failures": 0,
        "conservative_interpretation": True, "generated_artifacts": [
            "provider_connectivity_matrix.csv", "provider_connectivity_matrix.json",
            "provider_connectivity_manifest.json", "ONLINE_ONLY_PROVIDER_CONNECTIVITY_REVIEW.md",
        ],
    }
    (output_dir / "provider_connectivity_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    counts = {status: sum(row["status"] == status for row in rows) for status in sorted(ALLOWED_STATUSES)}
    review = "\n".join([
        "# Online-Only Provider Connectivity Review", "", "## Scope", "",
        "This phase audits technical connectivity and provenance. It does not validate biological claims or modify scores.", "",
        "## Status counts", "", *[f"- `{key}`: {value}" for key, value in counts.items() if value], "",
        "## Conservative interpretation", "", CONSERVATIVE_WARNING, "",
        "All providers are secondary and `blocking=false`; local artifact failures remain the only critical failures.",
    ])
    (output_dir / "ONLINE_ONLY_PROVIDER_CONNECTIVITY_REVIEW.md").write_text(review, encoding="utf-8")
    return {"output_dir": str(output_dir), "rows": rows, "manifest": manifest}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
