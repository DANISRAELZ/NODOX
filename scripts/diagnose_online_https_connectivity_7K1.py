from __future__ import annotations

import csv
import json
import os
import platform
import socket
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.nodos_funcionales.provider_contracts import PROVIDER_CONTRACTS


OUTPUT_JSON = PROJECT_ROOT / "docs" / "audit_artifacts" / "online_https_connectivity_diagnostic_7K1.json"
OUTPUT_CSV = PROJECT_ROOT / "docs" / "audit_artifacts" / "online_https_connectivity_diagnostic_7K1.csv"
OUTPUT_MD = PROJECT_ROOT / "docs" / "online_https_connectivity_diagnostic_7K1.md"

USER_AGENT = "nodos-funcionales-7K1-diagnostic/1.0"
TIMEOUT_SECONDS = 12
ENDPOINTS = {
    "uniprot_taxon_287_minimal": "https://rest.uniprot.org/uniprotkb/search?query=organism_id:287&format=json&size=1&fields=accession,id,gene_names,protein_name",
    "interpro_minimal": "https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/uniprot/P0A7V0/?page_size=1",
    "europe_pmc_minimal": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:ribosome&format=json&pageSize=1",
    "ncbi_taxonomy_minimal": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=taxonomy&term=Pseudomonas%20aeruginosa&retmode=json&retmax=1",
}
SEED_ENDPOINTS = {
    "candidate_seed_taxon_287": ENDPOINTS["uniprot_taxon_287_minimal"],
    "candidate_seed_taxon_562": "https://rest.uniprot.org/uniprotkb/search?query=organism_id:562&format=json&size=1&fields=accession,id,gene_names,protein_name",
    "candidate_seed_taxon_1773": "https://rest.uniprot.org/uniprotkb/search?query=organism_id:1773&format=json&size=1&fields=accession,id,gene_names,protein_name",
}


def run_diagnostic(
    output_json: Path = OUTPUT_JSON,
    output_csv: Path = OUTPUT_CSV,
    output_md: Path = OUTPUT_MD,
) -> dict[str, Any]:
    started_at = _utc_now()
    rows: list[dict[str, Any]] = []
    rows.extend(_dns_rows())
    for endpoint_name, url in ENDPOINTS.items():
        rows.append(_probe_urllib_certifi(endpoint_name, url))
        rows.append(_probe_urllib_default(endpoint_name, url))
        rows.append(_probe_request_provider_payload(endpoint_name, url))
    for endpoint_name, url in SEED_ENDPOINTS.items():
        rows.append(_probe_candidate_seed(endpoint_name, url))

    payload = {
        "phase": "7K1_online_https_connectivity_diagnostic",
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "openssl_version": ssl.OPENSSL_VERSION,
        "certifi_path": _certifi_path(),
        "environment": _environment_snapshot(),
        "rows": rows,
        "probable_cause": classify_probable_cause(rows),
        "scoring_modified": False,
        "ranking_modified": False,
        "biological_evidence_generated": False,
    }
    _write_json(output_json, payload)
    _write_csv(output_csv, rows)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(_markdown_report(payload), encoding="utf-8")
    return payload


def classify_probable_cause(rows: list[dict[str, Any]]) -> str:
    https_rows = [row for row in rows if row.get("probe") != "dns"]
    statuses = [str(row.get("cause_classification", "")) for row in https_rows]
    if any(status == "success" for status in statuses):
        return "partial_success"
    priority = [
        "openssl_applink_error",
        "local_runtime_ssl_incompatibility",
        "certificate_verify_failed",
        "proxy_or_firewall_error",
        "dns_error",
        "timeout",
        "http_error",
        "provider_unavailable",
        "invalid_payload",
    ]
    for status in priority:
        if status in statuses:
            return status
    return "provider_unavailable"


def classify_probe_result(returncode: int, stdout: str, stderr: str) -> str:
    text = f"{stdout}\n{stderr}".lower()
    if returncode == 0 and '"ok": true' in text:
        return "success"
    if "openssl_uplink" in text or "no openssl_applink" in text or "applink" in text:
        return "openssl_applink_error"
    if "certificate_verify_failed" in text:
        return "certificate_verify_failed"
    if "name or service not known" in text or "getaddrinfo failed" in text or "temporary failure in name resolution" in text:
        return "dns_error"
    if "proxy" in text or "tunnel" in text or "firewall" in text or "forbidden" in text:
        return "proxy_or_firewall_error"
    if "timed out" in text or "timeout" in text:
        return "timeout"
    if "http_error" in text or "http " in text or "httperror" in text:
        return "http_error"
    if "invalid_payload" in text or "jsondecodeerror" in text:
        return "invalid_payload"
    if "ssl" in text:
        return "ssl_error"
    if "network" in text or "network unreachable" in text:
        return "network_error"
    if "urlerror" in text or "connection" in text:
        return "provider_unavailable"
    return "provider_unavailable" if returncode else "success"


def _dns_rows() -> list[dict[str, Any]]:
    hosts = sorted({"rest.uniprot.org", "www.ebi.ac.uk", "eutils.ncbi.nlm.nih.gov"})
    rows = []
    for host in hosts:
        try:
            addresses = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
            rows.append(_base_row("dns", host, "", "success", "success", records=len(addresses)))
        except OSError as exc:
            rows.append(_base_row("dns", host, "", "dns_error", "dns_error", stderr=str(exc)))
    return rows


def _probe_urllib_certifi(endpoint_name: str, url: str) -> dict[str, Any]:
    code = r"""
import json, ssl, sys
from urllib.request import Request, urlopen
import certifi
url = sys.argv[1]
request = Request(url, headers={"User-Agent": "nodos-funcionales-7K1-diagnostic/1.0", "Accept": "application/json"})
context = ssl.create_default_context(cafile=certifi.where())
with urlopen(request, timeout=12, context=context) as response:
    raw = response.read()
    print(json.dumps({"ok": True, "http_status": getattr(response, "status", 200), "content_type": response.headers.get("Content-Type", ""), "bytes": len(raw)}))
"""
    return _row_from_subprocess("urllib_certifi", endpoint_name, url, code)


def _probe_urllib_default(endpoint_name: str, url: str) -> dict[str, Any]:
    code = r"""
import json, sys
from urllib.request import Request, urlopen
url = sys.argv[1]
request = Request(url, headers={"User-Agent": "nodos-funcionales-7K1-diagnostic/1.0", "Accept": "application/json"})
with urlopen(request, timeout=12) as response:
    raw = response.read()
    print(json.dumps({"ok": True, "http_status": getattr(response, "status", 200), "content_type": response.headers.get("Content-Type", ""), "bytes": len(raw)}))
"""
    return _row_from_subprocess("urllib_default", endpoint_name, url, code)


def _probe_request_provider_payload(endpoint_name: str, url: str) -> dict[str, Any]:
    code = r"""
import json, sys
from src.nodos_funcionales.provider_response_audit import request_provider_payload
url = sys.argv[1]
response = request_provider_payload(url, timeout=12, user_agent="nodos-funcionales-7K1-diagnostic/1.0", accept="application/json")
record_count = len(response.payload.get("results", [])) if isinstance(response.payload, dict) and isinstance(response.payload.get("results"), list) else 0
print(json.dumps({"ok": response.error_status == "", "http_status": response.http_status, "content_type": response.content_type, "payload_type": response.payload_type, "error_status": response.error_status, "rejection_reason": response.rejection_reason, "record_count": record_count}))
"""
    return _row_from_subprocess("request_provider_payload", endpoint_name, url, code)


def _probe_candidate_seed(endpoint_name: str, url: str) -> dict[str, Any]:
    row = _probe_request_provider_payload(endpoint_name, url)
    row["probe"] = "candidate_seed_contract"
    row["passes_contract"] = str(row.get("payload_type") == "json" and int(row.get("number_of_records", 0) or 0) >= 1).lower()
    row["contract_provider"] = "candidate_seed/uniprot"
    return row


def _row_from_subprocess(probe: str, endpoint_name: str, url: str, code: str) -> dict[str, Any]:
    result = _run_python_probe(code, url)
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    classification = classify_probe_result(result.returncode, stdout, stderr)
    parsed = _parse_stdout_json(stdout)
    status = "success" if classification == "success" else classification
    payload_type = str(parsed.get("payload_type", "json" if classification == "success" else "unresolved"))
    return {
        "probe": probe,
        "endpoint": endpoint_name,
        "url": url,
        "final_status": status,
        "cause_classification": classification,
        "returncode": result.returncode,
        "http_status": parsed.get("http_status", ""),
        "content_type": parsed.get("content_type", ""),
        "payload_type": payload_type,
        "number_of_records": parsed.get("record_count", parsed.get("bytes", 0)),
        "passes_contract": str(classification == "success").lower(),
        "contract_provider": _contract_for_endpoint(endpoint_name),
        "stdout_excerpt": stdout[:300],
        "stderr_excerpt": stderr[:500],
        "evidence_inferred": "false",
        "affects_score": "false",
        "blocks_ranking": "false",
    }


def _run_python_probe(code: str, url: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NODOS_ALLOW_WINDOWS_REAL_HTTPS": "1"}
    return subprocess.run(
        [sys.executable, "-c", code, url],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS + 8,
        env=env,
    )


def _contract_for_endpoint(endpoint_name: str) -> str:
    if "uniprot" in endpoint_name or "candidate_seed" in endpoint_name:
        return "uniprot"
    if "interpro" in endpoint_name:
        return "interpro"
    if "europe_pmc" in endpoint_name:
        return "europe_pmc"
    if "ncbi" in endpoint_name or "taxonomy" in endpoint_name:
        return "taxonomy"
    return "not_mapped"


def _parse_stdout_json(stdout: str) -> dict[str, Any]:
    try:
        return json.loads(stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}


def _base_row(
    probe: str,
    endpoint: str,
    url: str,
    final_status: str,
    cause: str,
    records: int = 0,
    stderr: str = "",
) -> dict[str, Any]:
    return {
        "probe": probe,
        "endpoint": endpoint,
        "url": url,
        "final_status": final_status,
        "cause_classification": cause,
        "returncode": 0 if cause == "success" else 1,
        "http_status": "",
        "content_type": "",
        "payload_type": "dns" if cause == "success" else "unresolved",
        "number_of_records": records,
        "passes_contract": str(cause == "success").lower(),
        "contract_provider": "dns",
        "stdout_excerpt": "",
        "stderr_excerpt": stderr[:500],
        "evidence_inferred": "false",
        "affects_score": "false",
        "blocks_ranking": "false",
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_report(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    return "\n".join(
        [
            "# Online HTTPS connectivity diagnostic 7K.1",
            "",
            f"- Python executable: `{payload['python_executable']}`",
            f"- Python version: `{payload['python_version']}`",
            f"- Platform: `{payload['platform']}`",
            f"- OpenSSL: `{payload['openssl_version']}`",
            f"- certifi path: `{payload['certifi_path']}`",
            f"- Probable cause: `{payload['probable_cause']}`",
            "",
            "This diagnostic does not touch scoring, ranking, GUI, user-curated evidence or biological interpretation.",
            "",
            "| probe | endpoint | final_status | cause_classification | payload_type | records |",
            "|---|---|---|---|---|---|",
            *[
                f"| {row['probe']} | {row['endpoint']} | {row['final_status']} | {row['cause_classification']} | {row['payload_type']} | {row['number_of_records']} |"
                for row in rows
            ],
        ]
    )


def _environment_snapshot() -> dict[str, str]:
    keys = ["SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY"]
    return {key: os.environ.get(key, "") for key in keys}


def _certifi_path() -> str:
    try:
        import certifi

        return str(certifi.where())
    except Exception:  # noqa: BLE001 - optional runtime metadata.
        return "not_available"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    payload = run_diagnostic()
    print(json.dumps({"probable_cause": payload["probable_cause"], "json": str(OUTPUT_JSON), "csv": str(OUTPUT_CSV)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
