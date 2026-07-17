from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .online_http import get_ssl_context

import pandas as pd

from .provider_response_audit import request_provider_payload
from .string_api import fetch_string_functional_network


BOUNDARY_WARNING = (
    "Estos datos corresponden a informacion online general del organismo consultado. "
    "No representan datos de ningun proyecto independiente, coleccion particular de aislados "
    "ni analisis genomico local, salvo que el usuario cargue explicitamente esos archivos."
)

CANDIDATE_UNIVERSE_COLUMNS = [
    "gene_id",
    "gene_name",
    "protein_id",
    "protein_name",
    "organism",
    "taxon_id",
    "source",
    "evidence_level",
    "provenance_status",
    "retrieval_mode",
    "cache_status",
    "generated_at_utc",
]

LOCALIZATION_COLUMNS = [
    "protein_id",
    "gene",
    "localization",
    "database",
    "gene_id",
    "gene_name",
    "membrane_associated",
    "secreted",
    "surface_exposed",
    "evidence_source",
    "evidence_level",
    "provenance_status",
    "retrieval_mode",
    "cache_status",
    "generated_at_utc",
]

VIRULENCE_COLUMNS = [
    "protein_id",
    "gene",
    "virulence_score",
    "virulence_factor",
    "database",
    "gene_id",
    "gene_name",
    "product",
    "virulence_factor_name",
    "virulence_category",
    "evidence_source",
    "evidence_level",
    "provenance_status",
    "retrieval_mode",
    "cache_status",
    "generated_at_utc",
    "notes",
]

FUNCTIONAL_NETWORK_COLUMNS = [
    "protein_id",
    "gene",
    "network_centrality",
    "pathway_bottleneck_score",
    "redundancy_penalty",
    "functional_dependency_score",
    "database",
    "source_gene",
    "target_gene",
    "source_protein_id",
    "target_protein_id",
    "interaction_score",
    "interaction_type",
    "evidence_source",
    "provenance_status",
    "retrieval_mode",
    "cache_status",
    "source_version",
    "generated_at_utc",
]

EVOLUTIONARY_ESCAPE_RISK_COLUMNS = [
    "protein_id",
    "gene",
    "candidate_id",
    "organism",
    "strain",
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
    "evolutionary_escape_risk_score",
    "evidence_source",
    "source_type",
    "confidence",
    "notes",
    "gene_id",
    "gene_name",
    "paralog_count",
    "pathway_redundancy",
    "mutation_tolerance",
    "conservation_fraction",
    "mobile_context",
    "hgt_context",
    "recombination_context",
    "resistance_association",
    "network_centrality_proxy",
    "evolutionary_escape_risk",
    "evidence_level",
    "provenance_status",
    "database",
]

VIRULENCE_TERMS = {
    "pld",
    "dtxr",
    "faga",
    "fagb",
    "fagc",
    "fagd",
    "hmut",
    "hmuu",
    "hmuv",
    "ciua",
    "ciub",
    "ciuc",
    "ciud",
    "ciue",
    "sodc",
    "spaa",
    "spac",
    "spad",
    "srta",
    "srtb",
    "srtc",
    "sapa",
}


@dataclass(frozen=True)
class OnlineLayerSummary:
    layer: str
    rows: int
    status: str
    path: Path
    notes: list[str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _request_json(url: str, timeout: float, user_agent: str) -> Any:
    response = request_provider_payload(url, timeout=timeout, user_agent=user_agent, accept="application/json", opener=urlopen)
    if response.error_status == "" and response.payload_type == "json":
        return response.payload
    raise ValueError(response.rejection_reason or response.error_status or f"unexpected_payload_type:{response.payload_type}")


def _extract_gene_names(entry: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for gene in entry.get("genes", []) or []:
        value = ((gene.get("geneName") or {}).get("value") or "").strip()
        if value:
            names.append(value)
        for field in ["synonyms", "orderedLocusNames", "orfNames"]:
            for item in gene.get(field, []) or []:
                value = str(item.get("value") or "").strip()
                if value:
                    names.append(value)
    deduped: list[str] = []
    for name in names:
        if name not in deduped:
            deduped.append(name)
    return deduped


def _extract_protein_name(entry: dict[str, Any]) -> str:
    description = entry.get("proteinDescription", {}) or {}
    recommended = description.get("recommendedName", {}) or {}
    full = recommended.get("fullName", {}) or {}
    if full.get("value"):
        return str(full["value"])
    for submitted in description.get("submissionNames", []) or []:
        value = ((submitted.get("fullName") or {}).get("value") or "").strip()
        if value:
            return value
    return ""


def _extract_location_text(entry: dict[str, Any]) -> str:
    locations: list[str] = []
    for comment in entry.get("comments", []) or []:
        if str(comment.get("commentType") or "").casefold() != "subcellular location":
            continue
        for item in comment.get("subcellularLocations", []) or []:
            value = (((item.get("location") or {}).get("value")) or "").strip()
            if value:
                locations.append(value)
    return ";".join(dict.fromkeys(locations))


def _normalize_localization(value: str) -> str:
    text = str(value or "").casefold()
    if "secret" in text or "extracellular" in text:
        return "extracellular"
    if "cell wall" in text:
        return "cell_wall"
    if "outer membrane" in text:
        return "outer_membrane"
    if "periplasm" in text:
        return "periplasm"
    if "membrane" in text:
        return "inner_membrane"
    if "cytoplasm" in text or "cytosol" in text:
        return "cytoplasm"
    return "unknown"


def _gene_key(value: object) -> str:
    return str(value or "").replace("_", "").replace("-", "").casefold()


def _empty(path: Path, columns: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(columns=columns)
    df.to_csv(path, index=False)
    return df


def fetch_uniprot_candidate_universe(
    workspace: Path,
    organism_name: str,
    taxon_id: str | None,
    config: dict[str, Any],
    mode: str,
    force_refresh: bool = False,
    max_records: int = 50,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw_dir = workspace / "data_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output = raw_dir / "candidate_universe.csv"
    cfg = config["online_sources"]["uniprot"]
    manifest = {
        "source": "uniprot",
        "organism_name": organism_name,
        "taxon_id": taxon_id,
        "mode": mode,
        "api_attempted": False,
        "api_success": False,
        "provenance_status": "missing_input",
        "notes": [],
        "generated_at_utc": _utc_now(),
    }
    if output.exists() and not force_refresh and mode in {"cache_first", "offline_only"}:
        df = pd.read_csv(output)
        manifest.update({"api_success": False, "cache_status": "cache_hit", "provenance_status": "real_external_online" if not df.empty else "missing_input"})
        return df, manifest
    if mode == "offline_only":
        df = _empty(output, CANDIDATE_UNIVERSE_COLUMNS)
        manifest["notes"].append("offline_only sin cache candidate_universe utilizable")
        return df, manifest
    if not taxon_id:
        df = _empty(output, CANDIDATE_UNIVERSE_COLUMNS)
        manifest["notes"].append("taxon_id ausente; no se consulta UniProt")
        return df, manifest

    fields = "accession,id,protein_name,gene_names,organism_name,cc_subcellular_location"
    params = {"query": f"organism_id:{taxon_id}", "format": "json", "size": max_records, "fields": fields}
    url = f"{str(cfg['provider_base_url'])}?{urlencode(params)}"
    manifest["api_attempted"] = True
    try:
        payload = _request_json(url, float(cfg["provider_timeout_seconds"]), str(cfg["provider_user_agent"]))
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        df = _empty(output, CANDIDATE_UNIVERSE_COLUMNS)
        manifest["notes"].append(f"UniProt unavailable: {exc}")
        return df, manifest

    rows = []
    for entry in payload.get("results", []) or []:
        gene_names = _extract_gene_names(entry)
        gene = gene_names[0] if gene_names else str(entry.get("uniProtkbId") or entry.get("primaryAccession") or "")
        protein_id = str(entry.get("primaryAccession") or entry.get("uniProtkbId") or gene).strip()
        rows.append(
            {
                "gene_id": gene,
                "gene_name": gene,
                "protein_id": protein_id,
                "protein_name": _extract_protein_name(entry),
                "organism": str((entry.get("organism") or {}).get("scientificName") or organism_name),
                "taxon_id": taxon_id,
                "source": "uniprot_rest",
                "evidence_level": "online_general_annotation",
                "provenance_status": "real_external_online",
                "retrieval_mode": mode,
                "cache_status": "cache_miss",
                "generated_at_utc": _utc_now(),
                "raw_location": _extract_location_text(entry),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=CANDIDATE_UNIVERSE_COLUMNS + ["raw_location"])
        manifest["provenance_status"] = "missing_input"
        manifest["notes"].append("UniProt returned no candidate proteins")
    else:
        manifest["api_success"] = True
        manifest["provenance_status"] = "real_external_online"
    df.to_csv(output, index=False)
    return df, manifest


def build_localization_from_uniprot_candidates(workspace: Path, candidates: pd.DataFrame, mode: str) -> pd.DataFrame:
    path = workspace / "data_raw" / "localization.csv"
    if candidates.empty:
        return _empty(path, LOCALIZATION_COLUMNS)
    rows = []
    for _, row in candidates.iterrows():
        loc = _normalize_localization(str(row.get("raw_location", "")))
        status = "real_external_online" if loc != "unknown" else "insufficient_evidence"
        rows.append(
            {
                "protein_id": row["protein_id"],
                "gene": row["gene_name"],
                "localization": loc,
                "database": "uniprot_rest_general_organism",
                "gene_id": row["gene_id"],
                "gene_name": row["gene_name"],
                "membrane_associated": "" if loc == "unknown" else int(loc in {"cell_wall", "outer_membrane", "inner_membrane", "periplasm"}),
                "secreted": "" if loc == "unknown" else int(loc == "extracellular"),
                "surface_exposed": "" if loc == "unknown" else int(loc in {"extracellular", "cell_wall", "outer_membrane"}),
                "evidence_source": "uniprot_rest",
                "evidence_level": "online_general_subcellular_location" if loc != "unknown" else "insufficient_location_annotation",
                "provenance_status": status,
                "retrieval_mode": mode,
                "cache_status": row.get("cache_status", "cache_miss"),
                "generated_at_utc": _utc_now(),
            }
        )
    df = pd.DataFrame(rows, columns=LOCALIZATION_COLUMNS)
    df.to_csv(path, index=False)
    return df


def build_virulence_proxy_from_candidates(workspace: Path, candidates: pd.DataFrame, mode: str) -> pd.DataFrame:
    path = workspace / "data_raw" / "virulence.csv"
    rows = []
    for _, row in candidates.iterrows():
        gene_key = _gene_key(row.get("gene_name"))
        product = str(row.get("protein_name", ""))
        product_key = product.casefold()
        if gene_key not in VIRULENCE_TERMS and not any(term in product_key for term in ["virulence", "toxin", "sortase", "adhesin", "heme", "iron"]):
            continue
        rows.append(
            {
                "protein_id": row["protein_id"],
                "gene": row["gene_name"],
                "virulence_score": 0.35,
                "virulence_factor": 1,
                "database": "uniprot_keyword_inferred_proxy",
                "gene_id": row["gene_id"],
                "gene_name": row["gene_name"],
                "product": product,
                "virulence_factor_name": product or row["gene_name"],
                "virulence_category": "annotation_keyword",
                "evidence_source": "uniprot_rest",
                "evidence_level": "inferred_from_general_annotation",
                "provenance_status": "inferred_proxy",
                "retrieval_mode": mode,
                "cache_status": row.get("cache_status", "cache_miss"),
                "generated_at_utc": _utc_now(),
                "notes": "Keyword proxy only; not VFDB/CARD evidence and not organism-specific experimental proof.",
            }
        )
    df = pd.DataFrame(rows, columns=VIRULENCE_COLUMNS)
    df.to_csv(path, index=False)
    return df


def build_conservative_escape_risk(workspace: Path, candidates: pd.DataFrame, network: pd.DataFrame | None = None) -> pd.DataFrame:
    path = workspace / "data_raw" / "evolutionary_escape_risk.csv"
    if candidates.empty:
        return _empty(path, EVOLUTIONARY_ESCAPE_RISK_COLUMNS)
    network = network if network is not None else pd.DataFrame()
    centrality = {}
    if not network.empty and "protein_id" in network.columns and "network_centrality" in network.columns:
        centrality = dict(zip(network["protein_id"].astype(str), pd.to_numeric(network["network_centrality"], errors="coerce").fillna(0.0)))
    rows = []
    for _, row in candidates.iterrows():
        protein_id = str(row["protein_id"])
        proxy = centrality.get(protein_id, "")
        rows.append(
            {
                "protein_id": protein_id,
                "gene": row["gene_name"],
                "candidate_id": protein_id,
                "organism": row.get("organism", ""),
                "strain": "",
                "mutation_tolerance_score": "",
                "functional_redundancy_escape_score": "",
                "compensatory_pathway_score": "",
                "fitness_cost_of_escape": "",
                "evolutionary_constraint_score": "",
                "resistance_emergence_risk": "",
                "multi_node_dependency_score": proxy,
                "evolutionary_escape_risk_score": "",
                "evidence_source": "online_general_uniprot_string",
                "source_type": "inferred_proxy",
                "confidence": 0.30 if proxy != "" else 0.0,
                "notes": "No local pangenome, SNP, HGT, mobile-element, or recombination evidence loaded; unknown fields are not negative evidence.",
                "gene_id": row["gene_id"],
                "gene_name": row["gene_name"],
                "paralog_count": "unknown",
                "pathway_redundancy": "unknown",
                "mutation_tolerance": "unknown",
                "conservation_fraction": "unknown",
                "mobile_context": "unknown",
                "hgt_context": "unknown",
                "recombination_context": "unknown",
                "resistance_association": "unknown",
                "network_centrality_proxy": proxy,
                "evolutionary_escape_risk": "unknown",
                "evidence_level": "insufficient_local_evolutionary_evidence",
                "provenance_status": "insufficient_evidence",
                "database": "conservative_online_escape_placeholder_v1",
            }
        )
    df = pd.DataFrame(rows, columns=EVOLUTIONARY_ESCAPE_RISK_COLUMNS)
    df.to_csv(path, index=False)
    return df


def _write_online_report(workspace: Path, manifest: dict[str, Any], summaries: list[OnlineLayerSummary]) -> tuple[Path, Path]:
    results = workspace / "results"
    results.mkdir(parents=True, exist_ok=True)
    audit_path = results / "online_enrichment_audit.csv"
    report_path = results / "online_enrichment_report.md"
    pd.DataFrame([summary.__dict__ for summary in summaries]).to_csv(audit_path, index=False)
    lines = [
        "# Online Organism Enrichment Report",
        "",
        f"- Organism: `{manifest.get('organism_name', '')}`",
        f"- Strain: `{manifest.get('strain') or 'not_specified'}`",
        f"- Taxon id: `{manifest.get('taxon_id') or 'unknown'}`",
        f"- Mode: `{manifest.get('mode')}`",
        f"- Sources requested: `{', '.join(manifest.get('sources_requested', []))}`",
        f"- Sources successful: `{', '.join(manifest.get('sources_successful', [])) or 'none'}`",
        f"- Sources failed: `{', '.join(manifest.get('sources_failed', [])) or 'none'}`",
        f"- Candidate proteins recovered: `{manifest.get('candidate_count', 0)}`",
        f"- STRING network rows: `{manifest.get('network_rows', 0)}`",
        "",
        "## Layers",
        "",
    ]
    for summary in summaries:
        lines.append(f"- `{summary.layer}`: {summary.rows} rows, status `{summary.status}`")
    lines.extend(["", "## Boundary Warning", "", BOUNDARY_WARNING])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    _json_dump(results / "online_enrichment_manifest.json", manifest)
    return audit_path, report_path


def run_organism_online_enrichment(
    workspace: Path,
    organism_name: str,
    strain: str | None,
    taxon_id: str | None,
    config: dict[str, Any],
    sources: list[str],
    mode: str,
    force_refresh: bool = False,
) -> dict[str, Any]:
    workspace = Path(workspace)
    (workspace / "config").mkdir(parents=True, exist_ok=True)
    (workspace / "data_raw").mkdir(parents=True, exist_ok=True)
    (workspace / "results").mkdir(parents=True, exist_ok=True)
    requested = [source.strip().lower() for source in sources if source.strip()]
    summaries: list[OnlineLayerSummary] = []
    successful: list[str] = []
    failed: list[str] = []

    candidates, uniprot_manifest = fetch_uniprot_candidate_universe(
        workspace, organism_name, taxon_id, config, mode, force_refresh=force_refresh
    )
    candidate_path = workspace / "data_raw" / "candidate_universe.csv"
    summaries.append(OnlineLayerSummary("candidate_universe", len(candidates), uniprot_manifest["provenance_status"], candidate_path, list(uniprot_manifest.get("notes", []))))
    if "uniprot" in requested and not candidates.empty:
        successful.append("uniprot")
    elif "uniprot" in requested:
        failed.append("uniprot")

    localization = build_localization_from_uniprot_candidates(workspace, candidates, mode)
    loc_status = "real_external_online" if not localization.empty and localization["provenance_status"].eq("real_external_online").any() else "insufficient_evidence"
    summaries.append(OnlineLayerSummary("localization", len(localization), loc_status, workspace / "data_raw" / "localization.csv", []))

    virulence = build_virulence_proxy_from_candidates(workspace, candidates, mode)
    summaries.append(OnlineLayerSummary("virulence", len(virulence), "inferred_proxy" if not virulence.empty else "insufficient_evidence", workspace / "data_raw" / "virulence.csv", []))

    network = pd.DataFrame()
    if "string" in requested:
        try:
            result = fetch_string_functional_network(
                workspace=workspace,
                organism_name=organism_name,
                taxon_id=taxon_id,
                config=config,
                mode=mode,
                refresh_cache=force_refresh,
                replace_existing=True,
            )
            network = result["functional_network"]
            successful.append("string")
            status = "real_external_online" if not network.empty else "insufficient_evidence"
            notes = list(result["manifest"].get("notes", []))
        except Exception as exc:
            failed.append("string")
            network = _empty(workspace / "data_raw" / "functional_network.csv", FUNCTIONAL_NETWORK_COLUMNS)
            status = "missing_input"
            notes = [str(exc)]
        summaries.append(OnlineLayerSummary("functional_network", len(network), status, workspace / "data_raw" / "functional_network.csv", notes))

    escape = build_conservative_escape_risk(workspace, candidates, network)
    summaries.append(OnlineLayerSummary("evolutionary_escape_risk", len(escape), "insufficient_evidence", workspace / "data_raw" / "evolutionary_escape_risk.csv", []))

    manifest = {
        "organism_name": organism_name,
        "strain": strain,
        "taxon_id": taxon_id,
        "mode": mode,
        "sources_requested": requested,
        "sources_successful": successful,
        "sources_failed": failed,
        "candidate_count": int(len(candidates)),
        "network_rows": int(len(network)),
        "generated_at_utc": _utc_now(),
        "boundary_warning": BOUNDARY_WARNING,
    }
    audit_path, report_path = _write_online_report(workspace, manifest, summaries)
    return {"manifest": manifest, "summaries": summaries, "audit_path": audit_path, "report_path": report_path}

