from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .online_http import get_ssl_context
from .provider_response_audit import request_provider_payload


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(raw_bytes: bytes) -> dict[str, Any]:
    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Respuesta JSON invalida desde proveedor taxonomico: {exc}") from exc


def _request_json(url: str, timeout: float, user_agent: str) -> dict[str, Any]:
    response = request_provider_payload(url, timeout=timeout, user_agent=user_agent, accept="application/json", opener=urlopen)
    if response.error_status == "" and response.payload_type == "json":
        return response.payload
    if response.payload_type == "network_error":
        raise URLError(response.rejection_reason)
    if response.payload_type == "timeout":
        raise TimeoutError(response.rejection_reason)
    raise ValueError(response.rejection_reason or response.error_status or f"unexpected_payload_type:{response.payload_type}")


def _candidate_name(summary: dict[str, Any]) -> str:
    for key in ("scientificname", "organism_name", "title", "commonname"):
        value = summary.get(key)
        if value:
            return str(value)
    return ""


def _rank_value(summary: dict[str, Any]) -> str | None:
    for key in ("rank", "current_rank"):
        value = summary.get(key)
        if value:
            return str(value)
    return None


def _taxon_id_value(summary: dict[str, Any], fallback_id: str) -> str | None:
    for key in ("taxid", "tax_id", "uid"):
        value = summary.get(key)
        if value is not None:
            return str(value)
    return fallback_id or None


def _build_search_terms(organism_name: str, strain: str | None) -> list[str]:
    terms = []
    organism = " ".join(organism_name.strip().split())
    if strain:
        strain_clean = " ".join(strain.strip().split())
        if strain_clean:
            terms.append(f"{organism} {strain_clean}")
    terms.append(organism)
    deduped: list[str] = []
    for term in terms:
        if term and term not in deduped:
            deduped.append(term)
    return deduped


def _pick_best_match(
    summaries: list[dict[str, Any]],
    organism_name: str,
    strain: str | None,
) -> tuple[dict[str, Any] | None, str, float]:
    organism_cf = organism_name.casefold()
    strain_cf = (strain or "").casefold()
    exact_with_strain = None
    exact_species = None
    partial = None

    for summary in summaries:
        name_cf = _candidate_name(summary).casefold()
        if strain_cf and name_cf == f"{organism_cf} {strain_cf}":
            exact_with_strain = summary
            break
        if name_cf == organism_cf and exact_species is None:
            exact_species = summary
        if organism_cf in name_cf and partial is None:
            partial = summary

    if exact_with_strain is not None:
        return exact_with_strain, "online_exact_strain_match", 0.98
    if exact_species is not None:
        return exact_species, "online_exact_name_match", 0.95
    if partial is not None:
        return partial, "online_partial_name_match", 0.70
    if summaries:
        return summaries[0], "online_ambiguous_first_match", 0.55
    return None, "online_no_match", 0.0


def query_ncbi_taxonomy(
    organism_name: str,
    strain: str | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    taxonomy_cfg = config["taxonomy"]
    base_url = str(taxonomy_cfg["provider_base_url"]).rstrip("/")
    timeout = float(taxonomy_cfg["provider_timeout_seconds"])
    max_retries = int(taxonomy_cfg["provider_max_retries"])
    backoff_seconds = float(taxonomy_cfg["provider_backoff_seconds"])
    user_agent = str(taxonomy_cfg["provider_user_agent"])

    search_terms = _build_search_terms(organism_name, strain)
    api_error_notes: list[str] = []

    for term in search_terms:
        params = {
            "db": "taxonomy",
            "term": term,
            "retmode": "json",
            "retmax": "5",
        }
        search_url = f"{base_url}/esearch.fcgi?{urlencode(params)}"
        search_payload: dict[str, Any] | None = None
        for attempt in range(max_retries + 1):
            try:
                search_payload = _request_json(search_url, timeout=timeout, user_agent=user_agent)
                break
            except HTTPError as exc:
                api_error_notes.append(f"HTTP {exc.code} during esearch for `{term}`")
                if exc.code == 429:
                    time.sleep(backoff_seconds)
                else:
                    break
            except URLError as exc:
                api_error_notes.append(f"Network error during esearch for `{term}`: {exc.reason}")
                break
            except TimeoutError:
                api_error_notes.append(f"Timeout during esearch for `{term}`")
                break
            except ValueError as exc:
                api_error_notes.append(str(exc))
                break
            if attempt < max_retries:
                time.sleep(backoff_seconds)

        if not search_payload:
            continue

        search_result = search_payload.get("esearchresult", {})
        id_list = [str(item) for item in search_result.get("idlist", []) if str(item).strip()]
        if not id_list:
            continue

        summary_params = {
            "db": "taxonomy",
            "id": ",".join(id_list),
            "retmode": "json",
        }
        summary_url = f"{base_url}/esummary.fcgi?{urlencode(summary_params)}"
        try:
            summary_payload = _request_json(summary_url, timeout=timeout, user_agent=user_agent)
        except HTTPError as exc:
            api_error_notes.append(f"HTTP {exc.code} during esummary for `{term}`")
            continue
        except URLError as exc:
            api_error_notes.append(f"Network error during esummary for `{term}`: {exc.reason}")
            continue
        except TimeoutError:
            api_error_notes.append(f"Timeout during esummary for `{term}`")
            continue
        except ValueError as exc:
            api_error_notes.append(str(exc))
            continue

        result = summary_payload.get("result", {})
        summaries = []
        for uid in result.get("uids", []):
            record = result.get(str(uid), {})
            if record:
                summaries.append(record)

        best_match, status, confidence = _pick_best_match(summaries, organism_name, strain)
        if best_match is None:
            continue

        matched_name = _candidate_name(best_match)
        return {
            "provider_name": str(taxonomy_cfg["provider_name"]),
            "provider_url": search_url,
            "provider_docs_url": str(taxonomy_cfg["provider_docs_url"]),
            "matched_name": matched_name or None,
            "taxon_id": _taxon_id_value(best_match, str(result.get("uids", [""])[0] if result.get("uids") else "")),
            "rank": _rank_value(best_match),
            "status": status,
            "resolution_confidence": confidence,
            "notes": (
                f"Resolucion por API publica NCBI E-utilities usando termino `{term}`."
                + (" Se selecciono la mejor coincidencia disponible." if status == "online_ambiguous_first_match" else "")
            ),
            "api_error_notes": api_error_notes,
            "timestamp_utc": _now_utc(),
        }

    return {
        "provider_name": str(taxonomy_cfg["provider_name"]),
        "provider_url": str(taxonomy_cfg["provider_base_url"]),
        "provider_docs_url": str(taxonomy_cfg["provider_docs_url"]),
        "matched_name": None,
        "taxon_id": None,
        "rank": None,
        "status": "online_no_match",
        "resolution_confidence": 0.0,
        "notes": "La API publica no devolvio una coincidencia taxonomica utilizable.",
        "api_error_notes": api_error_notes,
        "timestamp_utc": _now_utc(),
    }
