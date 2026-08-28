from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

import pandas as pd

from .online_http import urlopen_json


HUMAN_TAXON_ID = "9606"
DEFAULT_PAGE_SIZE = 200
COMPARISON_RULE = "bacterial_interpro_entries_vs_human_taxon_catalog"


def build_human_interpro_catalog_url(
    provider_base_url: str,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> str:
    """Return the InterPro API endpoint for entries observed in human proteins."""
    base = str(provider_base_url).rstrip("/")
    return (
        f"{base}/entry/interpro/protein/uniprot/taxonomy/uniprot/"
        f"{HUMAN_TAXON_ID}/?page_size={int(page_size)}"
    )


def extract_interpro_entry_accessions(payload: Any) -> set[str]:
    entries: set[str] = set()
    if not isinstance(payload, dict):
        return entries
    for item in payload.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata", {}) or {}
        accession = str(
            metadata.get("accession") or item.get("accession") or ""
        ).strip().upper()
        if accession.startswith("IPR"):
            entries.add(accession)
    return entries


def fetch_human_interpro_catalog(
    provider_base_url: str,
    *,
    timeout_seconds: float = 30.0,
    user_agent: str = "nodox-interpro-human-domain/1.0",
    page_size: int = DEFAULT_PAGE_SIZE,
    opener: Callable[..., Any] = urlopen_json,
) -> tuple[set[str], dict[str, Any]]:
    """Fetch the complete human InterPro-entry catalog with pagination.

    This is a taxonomy-level comparison catalog, not a statement that a bacterial
    protein is homologous to any particular human protein.
    """
    first_url = build_human_interpro_catalog_url(
        provider_base_url,
        page_size=page_size,
    )
    expected_host = urlparse(first_url).netloc
    url: str | None = first_url
    entries: set[str] = set()
    pages = 0
    reported_count: int | None = None

    while url:
        if urlparse(url).netloc not in {"", expected_host}:
            raise ValueError("InterPro pagination escaped the configured provider host")
        payload = opener(
            url,
            timeout=float(timeout_seconds),
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )
        if not isinstance(payload, dict):
            raise ValueError("InterPro human catalog response is not a JSON object")
        pages += 1
        if reported_count is None and payload.get("count") is not None:
            reported_count = int(payload["count"])
        entries.update(extract_interpro_entry_accessions(payload))
        next_url = payload.get("next")
        url = urljoin(url, str(next_url)) if next_url else None

    manifest = {
        "provider": "interpro_api",
        "provider_base_url": str(provider_base_url),
        "human_taxon_id": HUMAN_TAXON_ID,
        "catalog_rule": "InterPro entries observed in UniProt proteins under human taxonomy 9606",
        "first_request_url": first_url,
        "page_size": int(page_size),
        "pages_retrieved": pages,
        "provider_reported_count": reported_count,
        "unique_interpro_entry_count": len(entries),
        "comparison_scope": "domain_presence_by_taxon_not_pairwise_homology",
    }
    return entries, manifest


def parse_interpro_entries(value: object) -> set[str]:
    if value is None or pd.isna(value):
        return set()
    return {
        token.strip().upper()
        for token in str(value).split(";")
        if token.strip().upper().startswith("IPR")
    }


def compare_bacterial_entries_to_human_catalog(
    bacterial_entries: object,
    human_catalog: set[str],
) -> dict[str, Any]:
    """Compare one bacterial InterPro annotation against the human catalog."""
    bacterial = parse_interpro_entries(bacterial_entries)
    if not bacterial:
        return {
            "human_comparable_interpro_entries": pd.NA,
            "shared_interpro_entries": pd.NA,
            "shared_domain_count": pd.NA,
            "domain_overlap_score_empirical": pd.NA,
            "interpro_human_comparison_status": "bacterial_interpro_annotation_missing",
            "interpro_human_comparison_rule": COMPARISON_RULE,
        }

    shared = sorted(bacterial & human_catalog)
    # This score is deliberately directional: it is the fraction of bacterial
    # InterPro entries also observed in the human taxon catalog. It is not a
    # calibrated toxicity probability and is not promoted into Phase 3 here.
    score = len(shared) / len(bacterial)
    return {
        "human_comparable_interpro_entries": ";".join(sorted(human_catalog)),
        "shared_interpro_entries": ";".join(shared),
        "shared_domain_count": int(len(shared)),
        "domain_overlap_score_empirical": float(score),
        "interpro_human_comparison_status": "complete_taxon_catalog_comparison",
        "interpro_human_comparison_rule": COMPARISON_RULE,
    }


def build_comparison_table(
    host_annotation: pd.DataFrame,
    human_catalog: set[str],
) -> pd.DataFrame:
    required = {"protein_id", "interpro_bacterial_entries"}
    missing = sorted(required - set(host_annotation.columns))
    if missing:
        raise ValueError(
            "host_annotation is missing required columns: " + ", ".join(missing)
        )

    rows: list[dict[str, Any]] = []
    for _, row in host_annotation.iterrows():
        comparison = compare_bacterial_entries_to_human_catalog(
            row.get("interpro_bacterial_entries"),
            human_catalog,
        )
        rows.append(
            {
                "protein_id": row.get("protein_id"),
                "gene": row.get("gene", ""),
                "interpro_bacterial_accession": row.get(
                    "interpro_bacterial_accession", ""
                ),
                "interpro_bacterial_entries": row.get(
                    "interpro_bacterial_entries", pd.NA
                ),
                **comparison,
                "domain_overlap_score_promoted_to_phase3": False,
                "scoring_effect": "none_pending_calibration",
            }
        )
    return pd.DataFrame(rows)


def write_catalog_snapshot(
    path: Path,
    entries: set[str],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        **manifest,
        "entries": sorted(entries),
    }
    serialized = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    payload["sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return payload
