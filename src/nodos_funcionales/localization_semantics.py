from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PERIPHERAL_TOPOLOGY = "peripheral membrane protein"
INNER_PERIPHERAL_CLASS = "inner_membrane_peripheral"
OUTER_PERIPHERAL_CLASS = "outer_membrane_peripheral"


def _extract_topologies(entry: dict[str, Any]) -> list[str]:
    topologies: list[str] = []
    for comment in entry.get("comments", []) or []:
        if str(comment.get("commentType") or "").strip().lower() != "subcellular location":
            continue
        for item in comment.get("subcellularLocations", []) or []:
            value = str(((item.get("topology") or {}).get("value")) or "").strip()
            if value and value not in topologies:
                topologies.append(value)
    return topologies


def _load_frozen_seed_records(base_dir: Path) -> list[dict[str, Any]]:
    path = Path(base_dir) / "results" / "online_only_uniprot_seed_records.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    records = payload.get("results", []) if isinstance(payload, dict) else []
    return [record for record in records if isinstance(record, dict)]


def _topology_by_accession(base_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in _load_frozen_seed_records(base_dir):
        accession = str(entry.get("primaryAccession") or entry.get("uniProtkbId") or "").strip().upper()
        if not accession:
            continue
        topologies = _extract_topologies(entry)
        if topologies:
            result[accession] = ";".join(topologies)
    return result


def install_peripheral_membrane_profiles(config: dict[str, Any]) -> None:
    """Add conservative scoring profiles for explicit peripheral membrane topology.

    No new numeric calibration is introduced. Inner-membrane peripheral proteins
    reuse the existing cytoplasmic profile because membrane association alone
    does not establish membrane spanning or extracellular exposure. Outer-
    membrane peripheral proteins reuse the existing periplasmic profile for the
    same reason. The original compartment is retained separately for audit.
    """
    localization = config.get("localization", {})
    for mapping in localization.values():
        if not isinstance(mapping, dict):
            continue
        if "cytoplasm" in mapping:
            mapping[INNER_PERIPHERAL_CLASS] = float(mapping["cytoplasm"])
        if "periplasm" in mapping:
            mapping[OUTER_PERIPHERAL_CLASS] = float(mapping["periplasm"])


def apply_frozen_uniprot_topology_semantics(
    base_dir: Path,
    integrated: pd.DataFrame,
) -> pd.DataFrame:
    """Preserve UniProt topology and derive a conservative localization scoring class.

    The raw UniProt compartment remains in ``localization_reported``. Only rows
    explicitly annotated as ``Peripheral membrane protein`` are changed, and
    only when their normalized compartment is inner or outer membrane. Integral
    membrane proteins and rows without topology evidence are untouched.
    """
    result = integrated.copy()
    if result.empty or "protein_id" not in result.columns or "localization" not in result.columns:
        return result

    topology_lookup = _topology_by_accession(base_dir)
    protein_ids = result["protein_id"].fillna("").astype(str).str.strip().str.upper()
    result["uniprot_membrane_topology"] = protein_ids.map(topology_lookup).fillna("")
    result["localization_reported"] = result["localization"]
    result["localization_scoring_rule"] = "reported_compartment"

    topology = result["uniprot_membrane_topology"].fillna("").astype(str).str.lower()
    peripheral = topology.str.contains(PERIPHERAL_TOPOLOGY, regex=False)
    normalized = result["localization"].fillna("unknown").astype(str).str.strip().str.lower()

    inner_mask = peripheral & normalized.eq("inner_membrane")
    outer_mask = peripheral & normalized.eq("outer_membrane")

    result.loc[inner_mask, "localization"] = INNER_PERIPHERAL_CLASS
    result.loc[inner_mask, "localization_scoring_rule"] = (
        "uniprot_peripheral_membrane;conservative_access_profile=cytoplasm"
    )
    result.loc[outer_mask, "localization"] = OUTER_PERIPHERAL_CLASS
    result.loc[outer_mask, "localization_scoring_rule"] = (
        "uniprot_peripheral_membrane;conservative_access_profile=periplasm"
    )
    return result


def materialize_frozen_uniprot_topology_semantics(
    base_dir: Path,
    integrated: pd.DataFrame,
) -> pd.DataFrame:
    """Apply topology semantics and persist the integrated table consumed by scoring."""
    result = apply_frozen_uniprot_topology_semantics(base_dir, integrated)
    output = Path(base_dir) / "data_processed" / "integrated_nodes.csv"
    if output.parent.is_dir() or output.parent.mkdir(parents=True, exist_ok=True) is None:
        result.to_csv(output, index=False)
    return result
