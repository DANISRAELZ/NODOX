from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

NETWORK_COLUMNS = [
    "protein_id",
    "gene",
    "network_centrality",
    "pathway_bottleneck_score",
    "redundancy_penalty",
    "functional_dependency_score",
    "database",
    "provider",
    "source_used",
    "mapping_status",
    "mapping_confidence",
    "string_id",
    "interaction_partner_count",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_candidates(workspace: Path) -> pd.DataFrame:
    for directory in ("data_external", "data_raw"):
        path = workspace / directory / "essentiality.csv"
        if not path.is_file():
            continue
        df = pd.read_csv(path, low_memory=False)
        if "protein_id" not in df.columns:
            continue
        if "gene" not in df.columns:
            df["gene"] = df["protein_id"]
        if "locus_tag" not in df.columns:
            df["locus_tag"] = ""
        result = df[["protein_id", "gene", "locus_tag"]].copy()
        result["protein_id"] = result["protein_id"].fillna("").astype(str).str.strip().str.upper()
        result["gene"] = result["gene"].fillna("").astype(str).str.strip()
        result["locus_tag"] = result["locus_tag"].fillna("").astype(str).str.strip()
        return result.loc[result["protein_id"].ne("")].drop_duplicates("protein_id").reset_index(drop=True)
    raise FileNotFoundError("No candidate essentiality.csv was found in data_external or data_raw")


def _read_aliases(path: Path, taxon_id: str) -> pd.DataFrame:
    aliases = pd.read_csv(path, sep="\t", compression="infer", dtype=str, low_memory=False)
    aliases.columns = [str(column).strip().lstrip("#") for column in aliases.columns]
    protein_col = next((c for c in aliases.columns if c in {"string_protein_id", "protein_id"}), None)
    alias_col = next((c for c in aliases.columns if c == "alias"), None)
    if not protein_col or not alias_col:
        raise ValueError("STRING aliases file must contain string_protein_id/protein_id and alias columns")
    aliases = aliases.rename(columns={protein_col: "string_id", alias_col: "alias"})
    aliases["string_id"] = aliases["string_id"].fillna("").astype(str).str.strip()
    aliases["alias"] = aliases["alias"].fillna("").astype(str).str.strip()
    prefix = f"{taxon_id}."
    aliases = aliases.loc[aliases["string_id"].str.startswith(prefix) & aliases["alias"].ne("")].copy()
    aliases["alias_norm"] = aliases["alias"].str.casefold()
    return aliases[["string_id", "alias", "alias_norm"]].drop_duplicates()


def _candidate_tokens(row: pd.Series) -> set[str]:
    tokens: set[str] = set()
    for key in ("protein_id", "gene", "locus_tag"):
        value = str(row.get(key) or "").strip()
        if value:
            tokens.add(value.casefold())
    return tokens


def _map_candidates(candidates: pd.DataFrame, aliases: pd.DataFrame) -> pd.DataFrame:
    alias_lookup: dict[str, set[str]] = defaultdict(set)
    for _, row in aliases.iterrows():
        alias_lookup[str(row["alias_norm"])].add(str(row["string_id"]))

    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        matches: set[str] = set()
        for token in _candidate_tokens(candidate):
            matches.update(alias_lookup.get(token, set()))
        if len(matches) == 1:
            string_id = next(iter(matches))
            status = "exact_alias_match"
            confidence = 0.92
        elif len(matches) > 1:
            string_id = ""
            status = "ambiguous_alias_match"
            confidence = 0.0
        else:
            string_id = ""
            status = "unresolved"
            confidence = 0.0
        rows.append(
            {
                "protein_id": str(candidate["protein_id"]),
                "gene": str(candidate["gene"]),
                "string_id": string_id,
                "mapping_status": status,
                "mapping_confidence": confidence,
                "mapping_candidate_count": len(matches),
            }
        )
    return pd.DataFrame(rows)


def _read_links(path: Path, allowed_ids: set[str], required_score: int) -> pd.DataFrame:
    links = pd.read_csv(path, sep=r"\s+", compression="infer", dtype={"protein1": str, "protein2": str}, low_memory=False)
    required = {"protein1", "protein2", "combined_score"}
    if not required.issubset(links.columns):
        raise ValueError("STRING links file must contain protein1, protein2 and combined_score columns")
    links["combined_score"] = pd.to_numeric(links["combined_score"], errors="coerce")
    links = links.loc[
        links["protein1"].isin(allowed_ids)
        & links["protein2"].isin(allowed_ids)
        & links["combined_score"].ge(int(required_score))
    ].copy()
    if links.empty:
        return links
    links["pair_key"] = links.apply(lambda row: "|".join(sorted((str(row["protein1"]), str(row["protein2"])))), axis=1)
    links = links.sort_values("combined_score", ascending=False).drop_duplicates("pair_key")
    links["score"] = (links["combined_score"] / 1000.0).clip(lower=0.0, upper=1.0)
    return links[["protein1", "protein2", "combined_score", "score"]].reset_index(drop=True)


def _approximate_betweenness(nodes: list[str], adjacency: dict[str, set[str]], max_sources: int = 64) -> dict[str, float]:
    if len(nodes) <= 2:
        return {node: 0.0 for node in nodes}
    if len(nodes) <= max_sources:
        sources = nodes
    else:
        step = max(len(nodes) // max_sources, 1)
        sources = nodes[::step][:max_sources]

    centrality = dict.fromkeys(nodes, 0.0)
    for source in sources:
        stack: list[str] = []
        predecessors = {node: [] for node in nodes}
        sigma = dict.fromkeys(nodes, 0.0)
        sigma[source] = 1.0
        distance = dict.fromkeys(nodes, -1)
        distance[source] = 0
        queue: deque[str] = deque([source])
        while queue:
            current = queue.popleft()
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
                if sigma[current] > 0:
                    dependency[predecessor] += (sigma[predecessor] / sigma[current]) * (1.0 + dependency[current])
            if current != source:
                centrality[current] += dependency[current]

    maximum = max(centrality.values(), default=0.0) or 1.0
    return {node: min(1.0, value / maximum) for node, value in centrality.items()}


def _clustering(node: str, adjacency: dict[str, set[str]]) -> float:
    neighbors = adjacency[node]
    degree = len(neighbors)
    if degree < 2:
        return 0.0
    observed_twice = sum(len(adjacency[neighbor] & neighbors) for neighbor in neighbors)
    observed = observed_twice / 2.0
    possible = degree * (degree - 1) / 2.0
    return min(1.0, observed / possible) if possible else 0.0


def materialize_string_local_network(
    *,
    workspace: Path,
    links_path: Path,
    aliases_path: Path,
    taxon_id: str,
    required_score: int = 400,
    database_label: str = "computed_string_local_v12",
) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    links_path = Path(links_path).expanduser().resolve()
    aliases_path = Path(aliases_path).expanduser().resolve()
    if not links_path.is_file():
        raise FileNotFoundError(f"STRING links dataset not found: {links_path}")
    if not aliases_path.is_file():
        raise FileNotFoundError(f"STRING aliases dataset not found: {aliases_path}")

    candidates = _load_candidates(workspace)
    aliases = _read_aliases(aliases_path, str(taxon_id))
    mapping = _map_candidates(candidates, aliases)
    mapped = mapping.loc[mapping["string_id"].ne("")].copy()
    allowed_ids = set(mapped["string_id"].astype(str))
    links = _read_links(links_path, allowed_ids, int(required_score))

    string_to_protein = dict(zip(mapped["string_id"], mapped["protein_id"]))
    nodes = candidates["protein_id"].astype(str).tolist()
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    weighted_degree = defaultdict(float)
    support = defaultdict(list)
    for _, edge in links.iterrows():
        source = string_to_protein.get(str(edge["protein1"]))
        target = string_to_protein.get(str(edge["protein2"]))
        if not source or not target or source == target:
            continue
        score = float(edge["score"])
        adjacency[source].add(target)
        adjacency[target].add(source)
        weighted_degree[source] += score
        weighted_degree[target] += score
        support[source].append(score)
        support[target].append(score)

    max_degree = max(weighted_degree.values(), default=0.0) or 1.0
    bottleneck = _approximate_betweenness(nodes, adjacency)
    mapping_by_protein = mapping.set_index("protein_id").to_dict(orient="index")
    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        protein_id = str(candidate["protein_id"])
        degree_score = weighted_degree.get(protein_id, 0.0) / max_degree
        mean_support = sum(support.get(protein_id, [])) / max(len(support.get(protein_id, [])), 1)
        map_row = mapping_by_protein.get(protein_id, {})
        rows.append(
            {
                "protein_id": protein_id,
                "gene": str(candidate["gene"]),
                "network_centrality": round(float(degree_score), 6),
                "pathway_bottleneck_score": round(float(bottleneck.get(protein_id, 0.0)), 6),
                "redundancy_penalty": round(float(_clustering(protein_id, adjacency)), 6),
                "functional_dependency_score": round(float(min(1.0, 0.65 * degree_score + 0.35 * mean_support)), 6),
                "database": database_label,
                "provider": "string_db_local_dataset",
                "source_used": "versioned_local_dataset",
                "mapping_status": str(map_row.get("mapping_status", "unresolved")),
                "mapping_confidence": float(map_row.get("mapping_confidence", 0.0)),
                "string_id": str(map_row.get("string_id", "")),
                "interaction_partner_count": len(adjacency.get(protein_id, set())),
            }
        )

    output = pd.DataFrame(rows, columns=NETWORK_COLUMNS)
    external_dir = workspace / "data_external"
    results_dir = workspace / "results"
    external_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = external_dir / "functional_network.csv"
    mapping_path = results_dir / "string_local_mapping_audit.csv"
    manifest_path = results_dir / "string_local_network_manifest.json"
    output.to_csv(output_path, index=False)
    mapping.to_csv(mapping_path, index=False)

    usable = int(mapped["protein_id"].nunique())
    manifest = {
        "schema_version": "1.0",
        "provider": "string_db",
        "access_mode": "versioned_local_dataset",
        "taxon_id": str(taxon_id),
        "candidate_count": int(len(candidates)),
        "mapped_candidate_count": usable,
        "mapping_coverage_fraction": round(usable / max(len(candidates), 1), 6),
        "interaction_edge_count": int(len(links)),
        "required_score": int(required_score),
        "links_path": str(links_path),
        "links_sha256": _sha256(links_path),
        "aliases_path": str(aliases_path),
        "aliases_sha256": _sha256(aliases_path),
        "functional_network_path": str(output_path),
        "mapping_audit_path": str(mapping_path),
        "pathway_bottleneck_method": "deterministic_sampled_brandes_unweighted_max_64_sources",
        "negative_evidence_inferred_count": 0,
        "affects_score": bool(usable and len(links)),
        "generated_at_utc": _utc_now(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"functional_network": output, "manifest": manifest, "manifest_path": manifest_path}
