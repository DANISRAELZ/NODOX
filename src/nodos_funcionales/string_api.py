from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from .online.provider_modes import normalize_provider_mode, provider_mode_choices
from .online.provenance import provider_provenance
from .provider_response_audit import ProviderResponse, request_provider_payload, response_audit_fields


STRING_SOURCE_MODES = set(provider_mode_choices())

USABLE_STRING_MAPPING_STATUSES = {
    "exact_match",
    "locus_tag_match",
    "synonym_match",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_mode(mode: str, config: dict[str, Any]) -> str:
    return normalize_provider_mode(mode, config)


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(config["online_sources"]["string"]["cache_filename"])


def load_string_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload = _json_load(path)
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_string_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def invalidate_string_cache_entry(workspace: Path, config: dict[str, Any], cache_key: str) -> bool:
    cache = load_string_cache(workspace, config)
    removed = cache.get("entries", {}).pop(cache_key, None)
    save_string_cache(workspace, config, cache)
    return removed is not None


def invalidate_string_cache_entries_for_protein(workspace: Path, config: dict[str, Any], protein_id: str) -> int:
    protein_id = str(protein_id).strip().upper()
    cache = load_string_cache(workspace, config)
    keys = [key for key in cache.get("entries", {}) if protein_id and protein_id in key.upper()]
    for key in keys:
        cache["entries"].pop(key, None)
    save_string_cache(workspace, config, cache)
    return len(keys)


def _cache_key(taxon_id: str | None, proteins: pd.DataFrame, config: dict[str, Any]) -> str:
    required_score = int(config["online_sources"]["string"]["required_score"])
    protein_ids = sorted(str(item).strip().upper() for item in proteins["protein_id"].dropna().tolist() if str(item).strip())
    return f"string::{taxon_id or 'unknown'}::{required_score}::{'|'.join(protein_ids)}"


def _safe_json_loads(raw_bytes: bytes) -> Any:
    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Respuesta JSON invalida de STRING: {exc}") from exc


def _request_json(url: str, timeout: float, user_agent: str) -> ProviderResponse:
    return request_provider_payload(url, timeout=timeout, user_agent=user_agent, accept="application/json", opener=urlopen)


def _api_get_json(url: str, cfg: dict[str, Any]) -> tuple[Any | None, list[str], ProviderResponse | None]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []

    for attempt in range(retries + 1):
        response = _request_json(url, timeout=timeout, user_agent=user_agent)
        if response.error_status == "" and response.payload_type == "json":
            return response.payload, errors, response
        reason = response.rejection_reason or response.error_status or f"unexpected_payload_type:{response.payload_type}"
        errors.append(reason)
        if response.http_status == 429 and attempt < retries:
            time.sleep(backoff)
            continue
        return None, errors, response
    return None, errors, None


def _string_retrieval_status(response: ProviderResponse | None, payload: Any) -> str:
    if response is None:
        return "unresolved"
    if response.error_status == "ssl_error":
        return "ssl_error"
    if response.error_status == "not_found":
        return "not_found"
    if response.error_status:
        return "network_error" if response.payload_type == "network_error" else response.error_status
    if response.payload_type != "json":
        return "invalid_payload"
    if isinstance(payload, list):
        return "connected_structured_payload"
    return "invalid_payload"


def _string_audit(response: ProviderResponse | None, url: str) -> dict[str, Any]:
    if response is None:
        return {
            "provider_url": url,
            "http_status": "",
            "content_type": "",
            "payload_type": "unresolved",
            "rejection_reason": "no_response",
            "affects_score": False,
        }
    return response_audit_fields(response, affects_score=False)


def _get_candidate_proteins(workspace: Path) -> pd.DataFrame:
    raw_dir = workspace / "data_raw"
    candidates: dict[str, dict[str, str]] = {}
    for filename in ["essentiality.csv", "virulence.csv", "human_homologs.csv", "localization.csv"]:
        path = raw_dir / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "protein_id" not in df.columns:
            continue
        for _, row in df.iterrows():
            protein_id = str(row.get("protein_id", "")).strip()
            if not protein_id:
                continue
            gene = str(row.get("gene", "")).strip() or protein_id
            locus_tag = str(row.get("locus_tag", "") or row.get("locusTag", "") or "").strip()
            candidates.setdefault(
                protein_id.upper(),
                {"protein_id": protein_id.upper(), "gene": gene, "locus_tag": locus_tag},
            )
    if not candidates:
        raise ValueError("No hay proteínas base en el workspace para consultar STRING.")
    proteins = pd.DataFrame(candidates.values()).sort_values("protein_id").reset_index(drop=True)
    if len(proteins) < 2:
        raise ValueError("Se requieren al menos dos proteínas base para construir una red funcional desde STRING.")
    return proteins


def _build_string_id_url(proteins: pd.DataFrame, taxon_id: str, cfg: dict[str, Any]) -> str:
    identifiers = "\r".join(proteins["protein_id"].astype(str).tolist())
    params = {
        "identifiers": identifiers,
        "species": taxon_id,
        "caller_identity": "nodos_funcionales",
        "echo_query": 1,
    }
    return f"{str(cfg['provider_base_url']).rstrip('/')}/json/get_string_ids?{urlencode(params)}"


def _build_network_url(string_ids: list[str], taxon_id: str, cfg: dict[str, Any]) -> str:
    identifiers = "\r".join(string_ids)
    params = {
        "identifiers": identifiers,
        "species": taxon_id,
        "required_score": int(cfg["required_score"]),
        "network_type": str(cfg["network_type"]),
        "network_flavor": str(cfg["network_flavor"]),
        "caller_identity": "nodos_funcionales",
    }
    return f"{str(cfg['provider_base_url']).rstrip('/')}/json/network?{urlencode(params)}"


def _extract_string_mappings(payload: Any) -> pd.DataFrame:
    rows = []
    if not isinstance(payload, list):
        return pd.DataFrame(rows)
    for item in payload:
        if not isinstance(item, dict):
            continue
        query_term = str(item.get("queryItem") or item.get("queryIndex") or "").strip()
        if not query_term:
            continue
        rows.append(
            {
                "protein_id": query_term.upper(),
                "query_sent_to_string": query_term,
                "string_id": str(item.get("stringId") or "").strip(),
                "preferred_name": str(item.get("preferredName") or query_term).strip(),
                "ncbi_taxon_id": str(item.get("ncbiTaxonId") or item.get("taxonId") or "").strip(),
                "annotation": str(item.get("annotation") or "").strip(),
            }
        )
    return pd.DataFrame(rows)


def _normalize_identifier(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value or "").strip().casefold()


def _string_id_suffix(string_id: object) -> str:
    if pd.isna(string_id):
        return ""
    value = str(string_id or "").strip()
    if "." in value:
        return value.rsplit(".", 1)[-1]
    return value


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value or "").strip()


def _accepted_descendant_taxa(
    config: dict[str, Any],
    expected_taxon_id: str | None,
) -> set[str]:
    """Return explicitly accepted descendant taxa for one requested taxon.

    A different taxon is not assumed to be biologically compatible merely
    because STRING returned it. Compatibility must be declared explicitly.
    """
    expected_taxon = str(expected_taxon_id or "").strip()
    if not expected_taxon:
        return set()

    string_cfg = config.get("online_sources", {}).get("string", {})
    configured = string_cfg.get("accepted_descendant_taxa", {})
    if not isinstance(configured, dict):
        return set()

    values = configured.get(expected_taxon, {})

    if isinstance(values, dict):
        return {
            str(value).strip()
            for value, enabled in values.items()
            if bool(enabled) and str(value).strip()
        }

    if isinstance(values, (str, int)):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return set()

    return {
        str(value).strip()
        for value in values
        if str(value).strip()
    }


def _taxon_relation(
    expected_taxon_id: str | None,
    returned_taxon_id: str | None,
    config: dict[str, Any],
) -> str:
    expected = str(expected_taxon_id or "").strip()
    returned = str(returned_taxon_id or "").strip()

    if not expected or not returned:
        return "taxon_unresolved"
    if expected == returned:
        return "exact_taxon_match"
    if returned in _accepted_descendant_taxa(config, expected):
        return "descendant_strain_match"
    return "unrelated_taxon"


def _select_network_taxon_id(
    mappings: pd.DataFrame,
    expected_taxon_id: str,
    config: dict[str, Any],
) -> str:
    """Use a unique compatible returned strain taxon for the network query."""
    if mappings.empty or "ncbi_taxon_id" not in mappings.columns:
        return expected_taxon_id

    returned_taxa = {
        str(value).strip()
        for value in mappings["ncbi_taxon_id"].dropna().tolist()
        if str(value).strip()
    }
    compatible = {
        taxon
        for taxon in returned_taxa
        if _taxon_relation(expected_taxon_id, taxon, config)
        in {"exact_taxon_match", "descendant_strain_match"}
    }

    if len(compatible) == 1:
        return next(iter(compatible))
    return expected_taxon_id


def _classify_mapping(
    row: pd.Series,
    expected_taxon_id: str | None,
    config: dict[str, Any],
) -> tuple[str, float, str, str]:
    protein_id = _normalize_identifier(row.get("protein_id"))
    gene = _normalize_identifier(row.get("gene"))
    locus_tag = _normalize_identifier(row.get("locus_tag"))
    preferred_name = _normalize_identifier(row.get("preferred_name"))
    string_id = _clean_text(row.get("string_id"))
    string_suffix = _normalize_identifier(_string_id_suffix(string_id))
    ncbi_taxon_id = _clean_text(row.get("ncbi_taxon_id"))
    annotation = _normalize_identifier(row.get("annotation"))
    mapping_count = int(row.get("mapping_candidate_count") or 0)
    expected_taxon = str(expected_taxon_id or "").strip()
    taxon_relation = _taxon_relation(
        expected_taxon,
        ncbi_taxon_id,
        config,
    )

    if not string_id:
        return (
            "missing_mapping",
            0.0,
            "STRING returned no stringId for this local protein_id.",
            taxon_relation,
        )

    if taxon_relation == "unrelated_taxon":
        return (
            "taxon_mismatch",
            0.0,
            (
                f"STRING taxon {ncbi_taxon_id} is not configured as "
                f"compatible with expected taxon {expected_taxon}."
            ),
            taxon_relation,
        )

    if mapping_count > 1:
        return (
            "ambiguous_mapping",
            0.40,
            "STRING returned multiple candidate mappings for the same query.",
            taxon_relation,
        )

    if gene and (preferred_name == gene or string_suffix == gene):
        return "exact_match", 0.90, "", taxon_relation

    if locus_tag and (
        preferred_name == locus_tag
        or string_suffix == locus_tag
    ):
        return "locus_tag_match", 0.82, "", taxon_relation

    if gene and gene in annotation:
        return (
            "synonym_match",
            0.65,
            (
                "Local gene appears in STRING annotation but not as "
                "preferredName."
            ),
            taxon_relation,
        )

    if protein_id and (
        preferred_name == protein_id
        or string_suffix == protein_id
    ):
        if gene and preferred_name and preferred_name != gene:
            return (
                "preferred_name_mismatch",
                0.55,
                (
                    "STRING id matches local protein_id but preferredName "
                    "differs from local gene."
                ),
                taxon_relation,
            )
        return "exact_match", 0.90, "", taxon_relation

    return (
        "ambiguous_mapping",
        0.40,
        (
            "STRING mapping could not be reconciled with local protein_id, "
            "gene, or locus_tag."
        ),
        taxon_relation,
    )


def _extract_edges(payload: Any) -> pd.DataFrame:
    rows = []
    if not isinstance(payload, list):
        return pd.DataFrame(rows)
    for item in payload:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "string_id_a": str(item.get("stringId_A") or item.get("stringIdA") or "").strip(),
                "string_id_b": str(item.get("stringId_B") or item.get("stringIdB") or "").strip(),
                "preferred_name_a": str(item.get("preferredName_A") or item.get("preferredNameA") or "").strip(),
                "preferred_name_b": str(item.get("preferredName_B") or item.get("preferredNameB") or "").strip(),
                "score": float(item.get("score") or item.get("combined_score") or 0.0),
            }
        )
    edge_df = pd.DataFrame(rows)
    if not edge_df.empty:
        edge_df = edge_df.loc[edge_df["score"] > 0].reset_index(drop=True)
    return edge_df


def _betweenness_centrality(nodes: list[str], adjacency: dict[str, set[str]]) -> dict[str, float]:
    scores = {node: 0.0 for node in nodes}
    for source in nodes:
        stack: list[str] = []
        predecessors = {node: [] for node in nodes}
        sigma = dict.fromkeys(nodes, 0.0)
        sigma[source] = 1.0
        distance = dict.fromkeys(nodes, -1)
        distance[source] = 0
        queue = [source]
        while queue:
            current = queue.pop(0)
            stack.append(current)
            for neighbor in adjacency[current]:
                if distance[neighbor] < 0:
                    queue.append(neighbor)
                    distance[neighbor] = distance[current] + 1
                if distance[neighbor] == distance[current] + 1:
                    sigma[neighbor] += sigma[current]
                    predecessors[neighbor].append(current)
        dependency = dict.fromkeys(nodes, 0.0)
        while stack:
            current = stack.pop()
            for predecessor in predecessors[current]:
                if sigma[current]:
                    dependency[predecessor] += (sigma[predecessor] / sigma[current]) * (1.0 + dependency[current])
            if current != source:
                scores[current] += dependency[current]
    if len(nodes) <= 2:
        return {node: 0.0 for node in nodes}
    scale = 1.0 / ((len(nodes) - 1) * (len(nodes) - 2))
    return {node: min(1.0, value * scale) for node, value in scores.items()}


def _clustering_penalty(node: str, adjacency: dict[str, set[str]]) -> float:
    neighbors = list(adjacency[node])
    degree = len(neighbors)
    if degree < 2:
        return 0.0
    possible = degree * (degree - 1) / 2.0
    observed = 0
    for i, first in enumerate(neighbors):
        for second in neighbors[i + 1 :]:
            if second in adjacency[first]:
                observed += 1
    return min(1.0, observed / possible)


def _usable_edge_pairs(
    functional_network: pd.DataFrame,
    edges: pd.DataFrame,
) -> set[tuple[str, str]]:
    """Return unique edges whose two endpoints have usable local mappings."""
    if functional_network.empty or edges.empty:
        return set()

    required_network = {"protein_id", "string_id", "mapping_status"}
    required_edges = {"string_id_a", "string_id_b"}
    if not required_network.issubset(functional_network.columns):
        return set()
    if not required_edges.issubset(edges.columns):
        return set()

    usable = functional_network.loc[
        functional_network["mapping_status"]
        .fillna("")
        .astype(str)
        .isin(USABLE_STRING_MAPPING_STATUSES)
    ]
    string_to_protein = {
        str(row["string_id"]): str(row["protein_id"])
        for _, row in usable.iterrows()
        if str(row.get("string_id") or "").strip()
    }

    pairs: set[tuple[str, str]] = set()
    for _, edge in edges.iterrows():
        source = string_to_protein.get(str(edge.get("string_id_a") or ""))
        target = string_to_protein.get(str(edge.get("string_id_b") or ""))
        if not source or not target or source == target:
            continue
        pairs.add(tuple(sorted((source, target))))
    return pairs


def _derive_functional_network(
    proteins: pd.DataFrame,
    mappings: pd.DataFrame,
    edges: pd.DataFrame,
    config: dict[str, Any],
    source_used: str,
    cache_hit: bool,
    api_attempted: bool,
    api_success: bool,
    fallback_reason: str | None,
    taxon_id: str | None = None,
) -> pd.DataFrame:
    mapping_counts = (
        mappings.groupby("protein_id").size().rename("mapping_candidate_count")
        if not mappings.empty and "protein_id" in mappings.columns
        else pd.Series(dtype="int64", name="mapping_candidate_count")
    )
    mapping_single = mappings.drop_duplicates(subset=["protein_id"], keep="first") if not mappings.empty else mappings
    merged = proteins.merge(mapping_single, on="protein_id", how="left")
    if not mapping_counts.empty:
        merged = merged.merge(mapping_counts.reset_index(), on="protein_id", how="left")
    else:
        merged["mapping_candidate_count"] = 0
    for column in ["query_sent_to_string", "string_id", "preferred_name", "ncbi_taxon_id", "annotation", "locus_tag"]:
        if column not in merged.columns:
            merged[column] = ""
    merged["mapping_candidate_count"] = merged["mapping_candidate_count"].fillna(0).astype(int)
    merged["mapping_matches_input_gene"] = (
        merged["gene"].fillna("").astype(str).str.casefold()
        == merged["preferred_name"].fillna("").astype(str).str.casefold()
    )
    mapping_audit = merged.apply(
        lambda row: _classify_mapping(row, taxon_id, config),
        axis=1,
    )
    merged["mapping_status"] = mapping_audit.map(lambda item: item[0])
    merged["mapping_confidence"] = mapping_audit.map(lambda item: item[1])
    merged["mapping_warning"] = mapping_audit.map(lambda item: item[2])
    merged["taxon_relation"] = mapping_audit.map(lambda item: item[3])
    merged["usable_for_network"] = merged["mapping_status"].isin(
        USABLE_STRING_MAPPING_STATUSES
    )
    usable_mappings = merged.loc[merged["usable_for_network"]]
    string_to_protein = {
        str(row["string_id"]): str(row["protein_id"])
        for _, row in usable_mappings.dropna(subset=["string_id"]).iterrows()
        if str(row["string_id"]).strip()
    }
    nodes = merged["protein_id"].astype(str).tolist()
    weighted_degree = defaultdict(float)
    weighted_mean_support = defaultdict(list)
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}

    for _, edge in edges.iterrows():
        source = string_to_protein.get(str(edge["string_id_a"]))
        target = string_to_protein.get(str(edge["string_id_b"]))
        if not source or not target or source == target:
            continue
        score = min(1.0, float(edge["score"]))
        weighted_degree[source] += score
        weighted_degree[target] += score
        weighted_mean_support[source].append(score)
        weighted_mean_support[target].append(score)
        adjacency[source].add(target)
        adjacency[target].add(source)

    max_degree = max(weighted_degree.values(), default=0.0) or 1.0
    betweenness = _betweenness_centrality(nodes, adjacency)
    rows = []
    for _, protein in merged.iterrows():
        protein_id = str(protein["protein_id"])
        degree_score = weighted_degree.get(protein_id, 0.0) / max_degree
        support_score = sum(weighted_mean_support.get(protein_id, [])) / max(len(weighted_mean_support.get(protein_id, [])), 1)
        bottleneck = betweenness.get(protein_id, 0.0)
        redundancy = _clustering_penalty(protein_id, adjacency)
        dependency = min(1.0, (0.65 * degree_score) + (0.35 * support_score))
        rows.append(
            {
                "protein_id": protein_id,
                "gene": protein["gene"],
                "network_centrality": round(float(degree_score), 6),
                "pathway_bottleneck_score": round(float(bottleneck), 6),
                "redundancy_penalty": round(float(redundancy), 6),
                "functional_dependency_score": round(float(dependency), 6),
                "database": str(config["online_sources"]["string"]["database_label"]),
                "provider": str(config["online_sources"]["string"]["provider_name"]),
                "source_used": source_used,
                "cache_hit": cache_hit,
                "api_attempted": api_attempted,
                "api_success": api_success,
                "fallback_reason": fallback_reason or "",
                "data_realism_flag": "computed_online" if api_success else "computed_cached",
                "provenance_summary": (
                    f"provider={config['online_sources']['string']['provider_name']}; "
                    f"source_used={source_used}; cache_hit={cache_hit}; api_success={api_success}"
                ),
                "network_centrality_origin": "derived_from_string_network",
                "pathway_bottleneck_origin": "derived_betweenness_proxy_from_string_network",
                "redundancy_penalty_origin": "derived_clustering_proxy_from_string_network",
                "functional_dependency_origin": "derived_connectivity_support_proxy_from_string_network",
                "string_id": protein.get("string_id", ""),
                "string_preferred_name": protein.get("preferred_name", ""),
                "input_gene": protein.get("gene", ""),
                "input_locus_tag": protein.get("locus_tag", ""),
                "query_sent_to_string": protein.get("query_sent_to_string", protein_id),
                "string_id_returned": protein.get("string_id", ""),
                "preferred_name_returned": protein.get("preferred_name", ""),
                "ncbi_taxon_id": protein.get("ncbi_taxon_id", ""),
                "taxon_relation": protein.get(
                    "taxon_relation",
                    "taxon_unresolved",
                ),
                "mapping_status": protein.get("mapping_status", "unresolved"),
                "usable_for_network": bool(protein.get("usable_for_network", False)),
                "mapping_confidence": round(float(protein.get("mapping_confidence", 0.0)), 3),
                "mapping_warning": protein.get("mapping_warning", ""),
                "mapping_candidate_count": int(protein.get("mapping_candidate_count", 0)),
                "mapping_matches_input_gene": bool(protein.get("mapping_matches_input_gene", False)),
                "used_as_final_protein_id": protein_id,
                "used_as_final_gene": protein.get("gene", ""),
                "evidence_source": source_used,
                "cache_status": "cache_hit" if cache_hit else "cache_miss",
                "run_kind": "cache_reuse_run" if cache_hit and not api_attempted else ("fresh_api_run" if api_attempted and api_success else "fallback_mapping"),
                "interaction_partner_count": len(adjacency.get(protein_id, set())),
            }
        )
    return pd.DataFrame(rows)


def _write_string_mapping_audit(workspace: Path, functional_network: pd.DataFrame, manifest: dict[str, Any]) -> tuple[Path, Path]:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    audit_path = results_dir / "string_mapping_audit.csv"
    report_path = results_dir / "string_mapping_audit.md"
    columns = [
        "input_protein_id",
        "input_gene",
        "input_locus_tag",
        "query_sent_to_string",
        "string_id_returned",
        "preferred_name_returned",
        "ncbi_taxon_id",
        "taxon_relation",
        "mapping_status",
        "usable_for_network",
        "mapping_confidence",
        "mapping_warning",
        "used_as_final_protein_id",
        "used_as_final_gene",
        "evidence_source",
        "run_kind",
        "cache_status",
        "interaction_partner_count",
    ]
    audit = pd.DataFrame()
    if not functional_network.empty:
        audit = functional_network.copy()
        audit["input_protein_id"] = audit.get("protein_id", pd.Series(dtype=str))
        for column in columns:
            if column not in audit.columns:
                audit[column] = ""
        audit = audit[columns]
    audit.to_csv(audit_path, index=False)

    status_counts = audit["mapping_status"].value_counts().to_dict() if "mapping_status" in audit.columns else {}
    ambiguous_count = int(
        audit.get("mapping_status", pd.Series(dtype=str)).astype(str).isin(
            ["preferred_name_mismatch", "taxon_mismatch", "ambiguous_mapping", "missing_mapping", "fallback_mapping", "unresolved"]
        ).sum()
    ) if not audit.empty else 0
    lines = [
        "# STRING Mapping Audit",
        "",
        f"- Source used: `{manifest.get('source_used', '')}`",
        f"- Run kind: `{manifest.get('run_kind', '')}`",
        f"- Cache status: `{'cache_hit' if manifest.get('cache_hit') else 'cache_miss'}`",
        f"- Queries sent: `{manifest.get('protein_count_requested', 0)}`",
        f"- Exact matches: `{status_counts.get('exact_match', 0)}`",
        f"- Synonym matches: `{status_counts.get('synonym_match', 0)}`",
        f"- Locus-tag matches: `{status_counts.get('locus_tag_match', 0)}`",
        f"- Preferred-name mismatches: `{status_counts.get('preferred_name_mismatch', 0)}`",
        f"- Ambiguous mappings: `{status_counts.get('ambiguous_mapping', 0)}`",
        f"- Missing mappings: `{status_counts.get('missing_mapping', 0)}`",
        f"- Taxon mismatches: `{status_counts.get('taxon_mismatch', 0)}`",
        f"- Ambiguous or degraded records: `{ambiguous_count}`",
        "",
        "## Interpretation",
        "",
        "Mappings with degraded status remain traceable and should not be promoted to curated evidence without review.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return audit_path, report_path


def _write_manifest_and_report(workspace: Path, manifest: dict[str, Any]) -> tuple[Path, Path]:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = results_dir / "online_source_manifest.json"
    report_path = results_dir / "online_source_report.md"
    _json_dump(manifest_path, manifest)
    _json_dump(results_dir / "string_functional_network_manifest.json", manifest)

    lines = [
        "# Online Source Report",
        "",
        f"- Source: `{manifest['source']}`",
        f"- Provider: `{manifest['provider']}`",
        f"- Mode: `{manifest['mode']}`",
        f"- Source used: `{manifest['source_used']}`",
        f"- Cache hit: `{manifest['cache_hit']}`",
        f"- API attempted: `{manifest['api_attempted']}`",
        f"- API success: `{manifest['api_success']}`",
        f"- Fallback reason: `{manifest.get('fallback_reason') or 'none'}`",
        f"- Taxon id: `{manifest.get('taxon_id') or 'unknown'}`",
        f"- Candidate proteins requested: `{manifest['protein_count_requested']}`",
        f"- Candidate proteins mapped: `{manifest['protein_count_mapped']}`",
        f"- Mapping gene matches: `{manifest.get('mapping_gene_matches', 0)}`",
        f"- Mapping gene mismatches: `{manifest.get('mapping_gene_mismatches', 0)}`",
        f"- Network edges recovered: `{manifest['edge_count']}`",
        f"- Usable network edges: `{manifest.get('usable_edge_count', 0)}`",
        f"- Excluded network edges: `{manifest.get('excluded_edge_count', 0)}`",
        f"- Output written: `{manifest.get('output_written')}`",
        "",
        "## Notes",
    ]
    if manifest.get("notes"):
        lines.extend([f"- {note}" for note in manifest["notes"]])
    else:
        lines.append("- none")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return manifest_path, report_path


def _build_cache_served_manifest(cached_manifest: dict[str, Any], mode: str) -> dict[str, Any]:
    provider = str(cached_manifest.get("provider", "string"))
    served = {
        **cached_manifest,
        "source": cached_manifest.get("source", "string"),
        "provider": provider,
        "mode": mode,
        "source_used": "cache",
        "cache_hit": True,
        "api_attempted": False,
        "api_success": False,
        "fallback_reason": None,
        "data_realism_flag": "computed_cached",
        "provenance_summary": f"provider={provider}; source_used=cache; cache_hit=True; api_success=False",
    }
    served.update(
        provider_provenance(
            provider,
            "cache",
            float(cached_manifest.get("confidence", 0.78)),
            retrieval_mode=mode,
            cache_status="cache_hit",
            source_version=str(cached_manifest.get("generated_at_utc", ""))[:10] or None,
        )
    )
    served.setdefault("taxon_id", cached_manifest.get("taxon_id"))
    served.setdefault("protein_count_requested", int(cached_manifest.get("protein_count_requested", 0)))
    served.setdefault("protein_count_mapped", int(cached_manifest.get("protein_count_mapped", 0)))
    served.setdefault("mapping_gene_matches", int(cached_manifest.get("mapping_gene_matches", 0)))
    served.setdefault("mapping_gene_mismatches", int(cached_manifest.get("mapping_gene_mismatches", 0)))
    served.setdefault("mapping_status_counts", cached_manifest.get("mapping_status_counts", {}))
    served.setdefault("degraded_mapping_count", int(cached_manifest.get("degraded_mapping_count", 0)))
    served.setdefault("edge_count", int(cached_manifest.get("edge_count", 0)))
    served.setdefault(
        "usable_edge_count",
        int(cached_manifest.get("usable_edge_count", 0) or 0),
    )
    served.setdefault(
        "excluded_edge_count",
        int(
            cached_manifest.get(
                "excluded_edge_count",
                max(
                    int(served["edge_count"])
                    - int(served["usable_edge_count"]),
                    0,
                ),
            )
            or 0
        ),
    )
    served["run_kind"] = "cache_reuse_run"
    notes = list(served.get("notes", []))
    if "served_from_cache" not in notes:
        notes.append("served_from_cache")
    served["notes"] = notes
    return served


def _mark_cached_functional_network(functional_network: pd.DataFrame, fallback_reason: str | None = None) -> pd.DataFrame:
    cached = functional_network.copy()
    if cached.empty:
        return cached
    cached["source_used"] = "cache"
    cached["cache_hit"] = True
    cached["api_attempted"] = bool(fallback_reason)
    cached["api_success"] = False
    cached["fallback_reason"] = fallback_reason or ""
    cached["data_realism_flag"] = "computed_cached"
    cached["evidence_source"] = "cache"
    cached["cache_status"] = "cache_fallback" if fallback_reason else "cache_hit"
    cached["run_kind"] = "fallback_after_api_failure" if fallback_reason else "cache_reuse_run"
    return cached


def fetch_string_functional_network(
    workspace: Path,
    organism_name: str,
    taxon_id: str | None,
    config: dict[str, Any],
    mode: str,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
    replace_existing: bool = False,
) -> dict[str, Any]:
    workspace = Path(workspace)
    if not workspace.exists():
        raise FileNotFoundError(f"Workspace no encontrado: {workspace}")

    requested_mode = mode
    normalized_mode = _normalize_mode(mode, config)
    proteins = _get_candidate_proteins(workspace)
    cache = load_string_cache(workspace, config)
    cache_key = _cache_key(taxon_id, proteins, config)
    cfg = config["online_sources"]["string"]

    if not refresh_cache and normalized_mode in {"offline_only", "cache_first", "online_optional"}:
        cached_entry = cache["entries"].get(cache_key)
        if cached_entry:
            cached_df = _mark_cached_functional_network(pd.DataFrame(cached_entry.get("functional_network_rows", [])))
            manifest = _build_cache_served_manifest(cached_entry.get("manifest", {}), normalized_mode)
            manifest["requested_mode"] = requested_mode
            manifest["output_written"] = False
            output_path = _write_functional_network_output(
                workspace,
                cached_df,
                config,
                replace_existing=replace_existing,
            )
            manifest["output_written"] = bool(output_path)
            manifest["output_path"] = str(output_path) if output_path else None
            manifest["run_kind"] = "cache_reuse_run"
            audit_path, audit_report_path = _write_string_mapping_audit(workspace, cached_df, manifest)
            manifest["mapping_audit_path"] = str(audit_path)
            manifest["mapping_audit_report_path"] = str(audit_report_path)
            manifest_path, report_path = _write_manifest_and_report(workspace, manifest)
            return {
                "functional_network": cached_df,
                "manifest": manifest,
                "manifest_path": manifest_path,
                "report_path": report_path,
            }

    if normalized_mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache STRING utilizable para este conjunto de proteínas.")

    if not taxon_id:
        raise ValueError("Se requiere taxon_id para consultar STRING de forma reproducible.")

    id_url = _build_string_id_url(proteins, taxon_id, cfg)
    mapping_payload, mapping_errors, mapping_response = _api_get_json(id_url, cfg)
    mappings = _extract_string_mappings(mapping_payload)
    notes = mapping_errors[:]
    api_success = mapping_payload is not None and not mappings.empty
    fallback_reason = None

    if mappings.empty:
        if normalized_mode == "online_optional" and cache["entries"].get(cache_key):
            cached_entry = cache["entries"][cache_key]
            cached_df = _mark_cached_functional_network(
                pd.DataFrame(cached_entry.get("functional_network_rows", [])),
                fallback_reason="mapping_failed_fallback_cache",
            )
            manifest = {
                **cached_entry.get("manifest", {}),
                "source_used": "cache",
                "cache_hit": True,
                "api_attempted": True,
                "api_success": False,
                "fallback_reason": "mapping_failed_fallback_cache",
                "requested_mode": requested_mode,
                "mode": normalized_mode,
            }
            manifest.update(
                provider_provenance(
                    str(manifest.get("provider", cfg["provider_name"])),
                    "mapping_failed_fallback_cache",
                    float(manifest.get("confidence", 0.78)),
                    retrieval_mode=normalized_mode,
                    cache_status="cache_fallback",
                    source_version=str(manifest.get("generated_at_utc", ""))[:10] or None,
                )
            )
            output_path = _write_functional_network_output(workspace, cached_df, config, replace_existing=replace_existing)
            manifest["output_written"] = bool(output_path)
            manifest["output_path"] = str(output_path) if output_path else None
            manifest["run_kind"] = "fallback_after_api_failure"
            audit_path, audit_report_path = _write_string_mapping_audit(workspace, cached_df, manifest)
            manifest["mapping_audit_path"] = str(audit_path)
            manifest["mapping_audit_report_path"] = str(audit_report_path)
            manifest_path, report_path = _write_manifest_and_report(workspace, manifest)
            return {
                "functional_network": cached_df,
                "manifest": manifest,
                "manifest_path": manifest_path,
                "report_path": report_path,
            }
        status = _string_retrieval_status(mapping_response, mapping_payload)
        reason = "; ".join(notes) or "STRING no devolvio mappings utilizables para las proteinas del workspace."
        raise ValueError(f"{status}: {reason}")

    network_taxon_id = _select_network_taxon_id(
        mappings,
        taxon_id,
        config,
    )
    network_url = _build_network_url(
        mappings["string_id"].dropna().astype(str).tolist(),
        network_taxon_id,
        cfg,
    )
    edge_payload, edge_errors, edge_response = _api_get_json(network_url, cfg)
    notes.extend(edge_errors)
    if edge_payload is None and normalized_mode == "online_optional" and cache["entries"].get(cache_key):
        cached_entry = cache["entries"][cache_key]
        cached_df = _mark_cached_functional_network(
            pd.DataFrame(cached_entry.get("functional_network_rows", [])),
            fallback_reason="network_fetch_failed_fallback_cache",
        )
        manifest = {
            **cached_entry.get("manifest", {}),
            "source_used": "cache",
            "cache_hit": True,
            "api_attempted": True,
            "api_success": False,
            "fallback_reason": "network_fetch_failed_fallback_cache",
            "requested_mode": requested_mode,
            "mode": normalized_mode,
        }
        manifest.update(
            provider_provenance(
                str(manifest.get("provider", cfg["provider_name"])),
                "network_fetch_failed_fallback_cache",
                float(manifest.get("confidence", 0.78)),
                retrieval_mode=normalized_mode,
                cache_status="cache_fallback",
                source_version=str(manifest.get("generated_at_utc", ""))[:10] or None,
            )
        )
        output_path = _write_functional_network_output(workspace, cached_df, config, replace_existing=replace_existing)
        manifest["output_written"] = bool(output_path)
        manifest["output_path"] = str(output_path) if output_path else None
        manifest["run_kind"] = "fallback_after_api_failure"
        audit_path, audit_report_path = _write_string_mapping_audit(workspace, cached_df, manifest)
        manifest["mapping_audit_path"] = str(audit_path)
        manifest["mapping_audit_report_path"] = str(audit_report_path)
        manifest_path, report_path = _write_manifest_and_report(workspace, manifest)
        return {
            "functional_network": cached_df,
            "manifest": manifest,
            "manifest_path": manifest_path,
            "report_path": report_path,
        }
    edges = _extract_edges(edge_payload)
    if edges.empty:
        notes.append("STRING no devolvió aristas para el conjunto consultado; se generará una red vacía pero compatible.")
    retrieval_status = _string_retrieval_status(edge_response, edge_payload)
    audit = _string_audit(edge_response, network_url)
    derived = _derive_functional_network(
        proteins=proteins,
        mappings=mappings,
        edges=edges,
        config=config,
        source_used="api_real",
        cache_hit=False,
        api_attempted=True,
        api_success=api_success and edge_payload is not None,
        fallback_reason=fallback_reason,
        taxon_id=taxon_id,
    )
    mapped_mask = derived.get(
        "string_id_returned",
        pd.Series("", index=derived.index, dtype=object),
    ).fillna("").astype(str).str.strip().ne("")
    gene_match_mask = derived.get(
        "mapping_matches_input_gene",
        pd.Series(False, index=derived.index, dtype=bool),
    ).fillna(False).astype(bool)
    mapped_gene_matches = int((mapped_mask & gene_match_mask).sum())
    mapped_gene_mismatches = int(mapped_mask.sum() - mapped_gene_matches)
    mapping_status_counts = (
        derived["mapping_status"].fillna("unresolved").astype(str).value_counts().to_dict()
        if "mapping_status" in derived.columns
        else {}
    )
    mapping_status = derived.get(
        "mapping_status",
        pd.Series("unresolved", index=derived.index, dtype=object),
    ).fillna("unresolved").astype(str)
    usable_mapping_count = int(
        mapping_status.isin(USABLE_STRING_MAPPING_STATUSES).sum()
    )
    degraded_mapping_count = int(len(derived) - usable_mapping_count)
    usable_edge_count = len(_usable_edge_pairs(derived, edges))
    excluded_edge_count = max(
        int(len(edges)) - int(usable_edge_count),
        0,
    )
    if mapped_gene_mismatches:
        notes.append(
            f"Se detectaron {mapped_gene_mismatches} discrepancias entre `gene` local y `string_preferred_name`; usar este enriquecimiento con cautela."
        )
    if degraded_mapping_count:
        notes.append(
            f"STRING mapping audit registro {degraded_mapping_count} mappings degradados o ambiguos; revisar string_mapping_audit.csv antes de curar snapshots."
        )

    connectivity_success = bool(
        mapping_response is not None
        and mapping_response.http_status is not None
    )
    retrieval_success = bool(edge_payload is not None and len(edges) > 0)
    mapping_success = bool(usable_mapping_count > 0)
    usable_evidence = bool(retrieval_success and usable_edge_count > 0)

    if not mapping_success:
        final_retrieval_status = "degraded_no_usable_mapping"
        final_fallback_reason = (
            fallback_reason or "api_response_no_usable_mapping"
        )
    elif retrieval_success and not usable_evidence:
        final_retrieval_status = "degraded_no_usable_edge"
        final_fallback_reason = (
            fallback_reason or "api_response_no_usable_edge"
        )
        notes.append(
            "STRING returned interactions, but no edge had usable mappings "
            "at both endpoints; network metrics were excluded from scoring."
        )
    elif not retrieval_success:
        final_retrieval_status = "api_success_no_interactions"
        final_fallback_reason = (
            fallback_reason or "api_success_no_interactions"
        )
    else:
        final_retrieval_status = retrieval_status
        final_fallback_reason = fallback_reason

    manifest = {
        "source": "string",
        "provider": str(cfg["provider_name"]),
        "provider_docs_url": str(cfg["provider_docs_url"]),
        "requested_mode": requested_mode,
        "mode": normalized_mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "network_taxon_id": network_taxon_id,
        "query_cache_key": cache_key,
        "protein_count_requested": int(len(proteins)),
        "protein_count_mapped": int(mappings["string_id"].astype(str).str.strip().ne("").sum()),
        "mapping_gene_matches": mapped_gene_matches,
        "mapping_gene_mismatches": mapped_gene_mismatches,
        "mapping_status_counts": mapping_status_counts,
        "degraded_mapping_count": degraded_mapping_count,
        "usable_mapping_count": usable_mapping_count,
        "edge_count": int(len(edges)),
        "usable_edge_count": int(usable_edge_count),
        "excluded_edge_count": int(excluded_edge_count),
        "usable_mapping_statuses": sorted(USABLE_STRING_MAPPING_STATUSES),
        "source_used": "api_real",
        "retrieval_status": final_retrieval_status,
        "cache_hit": False,
        "api_attempted": True,
        "api_success": bool(edge_payload is not None),
        "connectivity_success": connectivity_success,
        "retrieval_success": retrieval_success,
        "mapping_success": mapping_success,
        "usable_evidence": usable_evidence,
        "fallback_used": not usable_evidence,
        "fallback_reason": final_fallback_reason,
        "notes": notes,
        "generated_at_utc": _utc_now(),
        "data_realism_flag": "computed_online",
        "confidence": 0.88 if usable_evidence else (0.72 if retrieval_success else 0.0),
        "run_kind": "fresh_api_run" if usable_evidence else "degraded_api_run",
        "provenance_summary": (
            f"provider={cfg['provider_name']}; source_used=api_real; cache_hit=False; api_success={edge_payload is not None}"
        ),
        "id_query_url": id_url,
        "network_query_url": network_url,
        "parser_used": "string_json_list_parser",
        "blocks_ranking": False,
        "evidence_inferred": usable_evidence,
        **audit,
    }
    manifest.update(
        provider_provenance(
            str(cfg["provider_name"]),
            str(manifest["source_used"]),
            float(manifest["confidence"]),
            retrieval_mode=normalized_mode,
            cache_status="cache_miss",
            source_version=str(manifest["generated_at_utc"])[:10],
            incomplete=edge_payload is None or mappings.empty or not usable_evidence,
        )
    )
    manifest["retrieval_status"] = final_retrieval_status
    manifest["usable_evidence"] = usable_evidence
    manifest["affects_score"] = usable_evidence
    manifest["fallback_used"] = not usable_evidence
    manifest["fallback_reason"] = final_fallback_reason

    if not no_write_cache:
        cache["entries"][cache_key] = {
            "saved_at_utc": _utc_now(),
            "source": "string",
            "organism_name": organism_name,
            "taxon_id": taxon_id,
            "functional_network_rows": derived.to_dict(orient="records"),
            "manifest": manifest,
        }
        save_string_cache(workspace, config, cache)

    diagnostic_path = workspace / "results" / "string_functional_network_diagnostic.csv"
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    derived.to_csv(diagnostic_path, index=False)
    manifest["diagnostic_output_path"] = str(diagnostic_path)

    if usable_evidence:
        output_path = _write_functional_network_output(
            workspace,
            derived,
            config,
            replace_existing=replace_existing,
        )
    else:
        output_path = None
        stale_output = workspace / "data_raw" / "functional_network.csv"
        if replace_existing and stale_output.exists():
            stale_output.unlink()

    manifest["output_written"] = bool(output_path)
    manifest["output_path"] = str(output_path) if output_path else None
    audit_path, audit_report_path = _write_string_mapping_audit(workspace, derived, manifest)
    manifest["mapping_audit_path"] = str(audit_path)
    manifest["mapping_audit_report_path"] = str(audit_report_path)
    manifest_path, report_path = _write_manifest_and_report(workspace, manifest)
    return {
        "functional_network": derived,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "report_path": report_path,
    }


def _write_functional_network_output(
    workspace: Path,
    functional_network: pd.DataFrame,
    config: dict[str, Any],
    replace_existing: bool = False,
) -> Path | None:
    raw_dir = workspace / "data_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "functional_network.csv"
    if output_path.exists() and not replace_existing:
        existing = pd.read_csv(output_path)
        if not existing.empty and "database" in existing.columns:
            databases = existing["database"].fillna("").astype(str).tolist()
            allow_replace_demo = bool(config["online_sources"]["string"]["allow_replace_demo_dataset"])
            all_demo = all(item.startswith(("demo_", "example_")) or item == "example_curated_demo" for item in databases if item)
            if not (allow_replace_demo and all_demo):
                return None
    functional_network.to_csv(output_path, index=False)
    return output_path
