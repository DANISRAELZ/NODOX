from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .online.provider_modes import normalize_provider_mode
from .online.provenance import provider_provenance


STRING_SOURCE_MODES = {"offline_only", "cache_first", "online_optional", "local", "auto", "api_stub"}


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


def _request_json(url: str, timeout: float, user_agent: str) -> Any:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        return _safe_json_loads(response.read())


def _api_get_json(url: str, cfg: dict[str, Any]) -> tuple[Any | None, list[str]]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []

    for attempt in range(retries + 1):
        try:
            return _request_json(url, timeout=timeout, user_agent=user_agent), errors
        except HTTPError as exc:
            errors.append(f"HTTP {exc.code} en STRING")
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff)
                continue
            break
        except URLError as exc:
            errors.append(f"Error de red en STRING: {exc.reason}")
            break
        except TimeoutError:
            errors.append("Timeout en STRING")
            break
        except ValueError as exc:
            errors.append(str(exc))
            break
    return None, errors


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
            candidates.setdefault(protein_id.upper(), {"protein_id": protein_id.upper(), "gene": gene})
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
                "string_id": str(item.get("stringId") or "").strip(),
                "preferred_name": str(item.get("preferredName") or query_term).strip(),
                "annotation": str(item.get("annotation") or "").strip(),
            }
        )
    return pd.DataFrame(rows)


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
) -> pd.DataFrame:
    merged = proteins.merge(mappings, on="protein_id", how="left")
    merged["mapping_matches_input_gene"] = (
        merged["gene"].fillna("").astype(str).str.casefold()
        == merged["preferred_name"].fillna("").astype(str).str.casefold()
    )
    string_to_protein = {
        str(row["string_id"]): str(row["protein_id"])
        for _, row in merged.dropna(subset=["string_id"]).iterrows()
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
                "mapping_matches_input_gene": bool(protein.get("mapping_matches_input_gene", False)),
            }
        )
    return pd.DataFrame(rows)


def _write_manifest_and_report(workspace: Path, manifest: dict[str, Any]) -> tuple[Path, Path]:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = results_dir / "online_source_manifest.json"
    report_path = results_dir / "online_source_report.md"
    _json_dump(manifest_path, manifest)

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
    served.setdefault("edge_count", int(cached_manifest.get("edge_count", 0)))
    notes = list(served.get("notes", []))
    if "served_from_cache" not in notes:
        notes.append("served_from_cache")
    served["notes"] = notes
    return served


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
            cached_df = pd.DataFrame(cached_entry.get("functional_network_rows", []))
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
    mapping_payload, mapping_errors = _api_get_json(id_url, cfg)
    mappings = _extract_string_mappings(mapping_payload)
    notes = mapping_errors[:]
    api_success = mapping_payload is not None and not mappings.empty
    fallback_reason = None

    if mappings.empty:
        if normalized_mode == "online_optional" and cache["entries"].get(cache_key):
            cached_entry = cache["entries"][cache_key]
            cached_df = pd.DataFrame(cached_entry.get("functional_network_rows", []))
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
            manifest_path, report_path = _write_manifest_and_report(workspace, manifest)
            return {
                "functional_network": cached_df,
                "manifest": manifest,
                "manifest_path": manifest_path,
                "report_path": report_path,
            }
        raise ValueError("STRING no devolvió mappings utilizables para las proteínas del workspace.")

    network_url = _build_network_url(mappings["string_id"].dropna().astype(str).tolist(), taxon_id, cfg)
    edge_payload, edge_errors = _api_get_json(network_url, cfg)
    notes.extend(edge_errors)
    if edge_payload is None and normalized_mode == "online_optional" and cache["entries"].get(cache_key):
        cached_entry = cache["entries"][cache_key]
        cached_df = pd.DataFrame(cached_entry.get("functional_network_rows", []))
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
    )
    mapped_gene_matches = int(derived["mapping_matches_input_gene"].sum()) if "mapping_matches_input_gene" in derived.columns else 0
    mapped_gene_mismatches = int(len(derived) - mapped_gene_matches)
    if mapped_gene_mismatches:
        notes.append(
            f"Se detectaron {mapped_gene_mismatches} discrepancias entre `gene` local y `string_preferred_name`; usar este enriquecimiento con cautela."
        )
    manifest = {
        "source": "string",
        "provider": str(cfg["provider_name"]),
        "provider_docs_url": str(cfg["provider_docs_url"]),
        "requested_mode": requested_mode,
        "mode": normalized_mode,
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "query_cache_key": cache_key,
        "protein_count_requested": int(len(proteins)),
        "protein_count_mapped": int(mappings["string_id"].astype(str).str.strip().ne("").sum()),
        "mapping_gene_matches": mapped_gene_matches,
        "mapping_gene_mismatches": mapped_gene_mismatches,
        "edge_count": int(len(edges)),
        "source_used": "api_real",
        "cache_hit": False,
        "api_attempted": True,
        "api_success": bool(edge_payload is not None),
        "fallback_reason": fallback_reason,
        "notes": notes,
        "generated_at_utc": _utc_now(),
        "data_realism_flag": "computed_online",
        "confidence": 0.88 if edge_payload is not None else 0.78,
        "provenance_summary": (
            f"provider={cfg['provider_name']}; source_used=api_real; cache_hit=False; api_success={edge_payload is not None}"
        ),
    }
    manifest.update(
        provider_provenance(
            str(cfg["provider_name"]),
            str(manifest["source_used"]),
            float(manifest["confidence"]),
            retrieval_mode=normalized_mode,
            cache_status="cache_miss",
            source_version=str(manifest["generated_at_utc"])[:10],
            incomplete=edge_payload is None or mappings.empty,
        )
    )

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

    output_path = _write_functional_network_output(workspace, derived, config, replace_existing=replace_existing)
    manifest["output_written"] = bool(output_path)
    manifest["output_path"] = str(output_path) if output_path else None
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
