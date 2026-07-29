from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from .bvbrc_api import fetch_bvbrc_strain_conservation
from .deg_api import fetch_deg_essentiality
from .human_homology_diamond import build_human_homologs_with_diamond
from .interpro_api import fetch_interpro_host_annotation
from .online_http import classify_provider_failure, get_ssl_context
from .online.provider_modes import normalize_provider_mode
from .provider_response_audit import request_provider_payload
from .string_api import fetch_string_functional_network
from .uniprot_api import fetch_uniprot_annotations
from .vfdb_api import fetch_vfdb_virulence


SUPPORTED_ONLINE_SOURCES = {"string", "uniprot"}
THERAPEUTIC_CONTEXT_PROVIDER = "controlled_therapeutic_context_v1"
THERAPEUTIC_CONTEXT_PROVIDER_V2 = "controlled_therapeutic_context_v2"
THERAPEUTIC_CONTEXT_PROVIDERS = {THERAPEUTIC_CONTEXT_PROVIDER, THERAPEUTIC_CONTEXT_PROVIDER_V2}
NETWORK_BLOCKED_MODES = {"offline_only"}
NETWORK_PROVIDERS = {
    "uniprot_real",
    "string_real",
    "uniprot_human_gene_lookup",
    "human_homology_diamond",
    "interpro_domain_overlap",
    "deg_real",
    "vfdb_real",
    "bvbrc_real",
}
PROVIDER_CONFIG_SECTIONS = {
    "uniprot_real": "uniprot",
    "string_real": "string",
    "uniprot_human_gene_lookup": "human_homologs_lookup",
    "interpro_domain_overlap": "interpro",
    "deg_real": "deg",
    "vfdb_real": "vfdb",
    "bvbrc_real": "bvbrc",
}


def effective_online_source_mode(config: dict[str, Any]) -> str:
    """Return the effective online-source mode used by external layer providers."""
    online_cfg = config.get("online_sources", {})
    requested = str(
        online_cfg.get("source_mode_effective")
        or online_cfg.get("source_mode")
        or online_cfg.get("source_mode_default")
        or "cache_first"
    )
    return normalize_provider_mode(requested, config)


def _network_is_blocked(config: dict[str, Any]) -> bool:
    return effective_online_source_mode(config) in NETWORK_BLOCKED_MODES


def _provider_is_enabled(config: dict[str, Any], provider_name: str) -> bool:
    """Honor the provider switch before consulting cache, files, or the network."""
    section = PROVIDER_CONFIG_SECTIONS.get(provider_name)
    if section is None:
        return True
    provider_cfg = config.get("online_sources", {}).get(section, {})
    return bool(provider_cfg.get("enabled", True))


def _workspace_context(workspace: Path) -> dict[str, str | None]:
    profile_path = workspace / "results" / "organism_profile.json"
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        return {
            "organism_name": str(profile.get("organism_canonical_name") or profile.get("organism_input_name") or "").strip() or None,
            "strain": str(profile.get("strain_canonical") or profile.get("strain_input") or "").strip() or None,
            "taxon_id": str(profile.get("taxon_id") or "").strip() or None,
        }
    return {"organism_name": None, "strain": None, "taxon_id": None}


def _external_dir(workspace: Path, config: dict[str, Any]) -> Path:
    path = workspace / config["layer_resolution"]["external_data_dir"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_external_layer(path: Path, df: pd.DataFrame) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return str(path)


def _unresolved_external_result(
    layer_key: str,
    provider_name: str,
    reason: object,
) -> dict[str, Any]:
    status = classify_provider_failure(reason)
    source_name = "provider_not_found" if status == "not_found" else provider_name
    return {
        "layer_key": layer_key,
        "provider_name": provider_name,
        "source_name": source_name,
        "path": None,
        "status": status,
        "confidence": 0.0,
        "retrieval_status": "unresolved",
        "source_database": source_name,
        "evidence": "unresolved",
        "notes": [str(reason), "Provider retrieval failed; no biological absence was inferred."],
    }


def _catalog_slug(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _catalog_key_candidates(context: dict[str, str | None], extra_keys: list[object] | None = None) -> list[str]:
    keys: list[str] = []
    taxon_id = str(context.get("taxon_id") or "").strip()
    organism_name = str(context.get("organism_name") or "").strip()
    strain = str(context.get("strain") or "").strip()
    if taxon_id:
        keys.extend([f"taxon_{taxon_id}", taxon_id])
    organism_slug = _catalog_slug(organism_name)
    strain_slug = _catalog_slug(strain)
    if organism_slug and strain_slug:
        keys.append(f"{organism_slug}_{strain_slug}")
    if organism_slug:
        keys.append(organism_slug)
    for key in extra_keys or []:
        slug = _catalog_slug(key)
        if slug:
            keys.append(slug)
    deduped: list[str] = []
    for key in keys:
        if key and key not in deduped:
            deduped.append(key)
    return deduped


def _read_curated_therapeutic_catalog(
    workspace: Path,
    config: dict[str, Any],
    catalog_key: str,
    candidates: list[str],
) -> tuple[Path | None, pd.DataFrame]:
    cfg = config["online_sources"].get("curated_therapeutic_catalogs", {})
    if not bool(cfg.get("enabled", True)):
        return None, pd.DataFrame()
    configured_base = str(cfg.get("base_dir", "data_external/curated_catalogs"))
    repo_root = Path(__file__).resolve().parents[2]
    base_dirs = [workspace / configured_base, repo_root / configured_base]
    for base_dir in base_dirs:
        catalog_dir = base_dir / str(cfg.get(catalog_key, catalog_key))
        for candidate in candidates:
            for filename in [f"{candidate}.csv", f"{candidate.lower()}.csv"]:
                path = catalog_dir / filename
                if path.exists():
                    df = pd.read_csv(path)
                    if not df.empty:
                        return path, df
    return None, pd.DataFrame()


def _build_curated_literature_support_from_catalog(
    workspace: Path,
    catalog_df: pd.DataFrame,
    catalog_path: Path,
) -> pd.DataFrame:
    candidates = _get_candidate_proteins(workspace)
    if candidates.empty or catalog_df.empty:
        return pd.DataFrame()
    by_protein = {
        _normalise_protein_id(row["protein_id"]): row
        for _, row in candidates.iterrows()
        if str(row.get("protein_id", "")).strip()
    }
    by_gene = {
        str(row.get("gene", "")).strip().lower(): row
        for _, row in candidates.iterrows()
        if str(row.get("gene", "")).strip()
    }

    rows: list[dict[str, Any]] = []
    for _, catalog_row in catalog_df.iterrows():
        catalog_protein_id = str(catalog_row.get("protein_id", "")).strip()
        catalog_gene = str(catalog_row.get("gene", "")).strip()
        match = by_protein.get(_normalise_protein_id(catalog_protein_id))
        match_status = "protein_id"
        if match is None and catalog_gene:
            match = by_gene.get(catalog_gene.lower())
            match_status = "gene_symbol"
        if match is None:
            continue
        materialized = catalog_row.to_dict()
        materialized["catalog_protein_id"] = catalog_protein_id
        materialized["catalog_gene"] = catalog_gene
        materialized["protein_id"] = match["protein_id"]
        materialized["gene"] = match.get("gene", catalog_gene or match["protein_id"])
        materialized["curated_online_catalog_source"] = _display_catalog_path(catalog_path, workspace)
        materialized["curated_online_match_status"] = match_status
        if not str(materialized.get("evidence_source_type", "")).strip():
            materialized["evidence_source_type"] = "literature_curated"
        if not str(materialized.get("database", "")).strip():
            materialized["database"] = "curated_online_pubmed_ncbi_v1"
        rows.append(materialized)
    return pd.DataFrame(rows)


def _build_curated_layer_from_catalog(
    workspace: Path,
    catalog_df: pd.DataFrame,
    catalog_path: Path,
) -> pd.DataFrame:
    candidates = _get_candidate_proteins(workspace)
    if candidates.empty or catalog_df.empty:
        return pd.DataFrame()
    by_protein = {
        _normalise_protein_id(row["protein_id"]): row
        for _, row in candidates.iterrows()
        if str(row.get("protein_id", "")).strip()
    }
    by_gene = {
        str(row.get("gene", "")).strip().lower(): row
        for _, row in candidates.iterrows()
        if str(row.get("gene", "")).strip()
    }
    rows: list[dict[str, Any]] = []
    for _, catalog_row in catalog_df.iterrows():
        catalog_protein_id = str(catalog_row.get("protein_id", "")).strip()
        catalog_gene = str(catalog_row.get("gene", "")).strip()
        match = by_protein.get(_normalise_protein_id(catalog_protein_id))
        match_status = "protein_id"
        if match is None and catalog_gene:
            match = by_gene.get(catalog_gene.lower())
            match_status = "gene_symbol"
        if match is None:
            continue
        materialized = catalog_row.to_dict()
        materialized["catalog_protein_id"] = catalog_protein_id
        materialized["catalog_gene"] = catalog_gene
        materialized["protein_id"] = match["protein_id"]
        materialized["gene"] = match.get("gene", catalog_gene or match["protein_id"])
        materialized["curated_online_catalog_source"] = _display_catalog_path(catalog_path, workspace)
        materialized["curated_online_match_status"] = match_status
        if not str(materialized.get("database", "")).strip():
            materialized["database"] = "curated_online_examples_v1"
        rows.append(materialized)
    return pd.DataFrame(rows)


def _raw_file_marked_demo(workspace: Path, filename: str) -> bool:
    manifest_path = workspace / "results" / "acquisition_manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if filename in set(manifest.get("demo_files_copied", []) or []):
        return True
    for dataset in manifest.get("datasets", []) or []:
        if dataset.get("filename") == filename and dataset.get("source_type") == "demo":
            return True
    return False


def _clamp_value(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(upper, max(lower, float(value)))


def _read_raw_layer(workspace: Path, filename: str) -> pd.DataFrame:
    path = workspace / "data_raw" / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _display_catalog_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _normalise_protein_id(value: object) -> str:
    return str(value).strip().upper().replace(" ", "_")


def _numeric_row_value(row: pd.Series, column: str, default: float) -> float:
    value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
    if pd.isna(value):
        return default
    return float(value)


def _numeric_row_value_with_flag(row: pd.Series, column: str, default: float) -> tuple[float, str | None]:
    value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
    if pd.isna(value):
        return default, f"default_{column}"
    return float(value), None


def _localization_access(localization: object, config: dict[str, Any]) -> float:
    neutral = float(config["imputation"]["neutral_unknown_score"])
    mapping = config["localization"]["infection_site_access"]
    value = str(localization or "unknown").strip().lower()
    return float(mapping.get(value, mapping.get("unknown", neutral)))


def _localization_access_with_flag(localization: object, config: dict[str, Any]) -> tuple[float, str | None]:
    neutral = float(config["imputation"]["neutral_unknown_score"])
    mapping = config["localization"]["infection_site_access"]
    value = str(localization or "unknown").strip().lower()
    if value in mapping:
        return float(mapping[value]), None
    return float(mapping.get("unknown", neutral)), "default_localization_access"


def _format_controlled_inputs(values: dict[str, float]) -> str:
    return "; ".join(f"{key}={value:.4f}" for key, value in values.items())


def _format_missing_flags(flags: list[str | None]) -> str:
    clean = [flag for flag in flags if flag]
    return "; ".join(clean) if clean else "none"


def _controlled_confidence_reason(config: dict[str, Any]) -> str:
    confidence = float(config["online_sources"]["therapeutic_context"]["confidence_controlled"])
    return f"controlled_semicurated_workspace_derivation; confidence={confidence:.2f}; not_experimental"


def _controlled_confidence_reason_v2(config: dict[str, Any]) -> str:
    confidence = float(config["online_sources"]["therapeutic_context_v2"]["confidence_controlled"])
    return f"controlled_semantic_v2_workspace_derivation; confidence={confidence:.2f}; not_experimental"


def _controlled_context_base(workspace: Path) -> pd.DataFrame:
    candidates = _get_candidate_proteins(workspace)
    if candidates.empty:
        return pd.DataFrame()
    candidates["protein_id"] = candidates["protein_id"].map(_normalise_protein_id)

    for filename, prefix in [
        ("essentiality.csv", "essentiality"),
        ("virulence.csv", "virulence"),
        ("localization.csv", "localization"),
        ("strain_conservation.csv", "conservation"),
        ("functional_network.csv", "network"),
    ]:
        layer = _read_raw_layer(workspace, filename)
        if layer.empty or "protein_id" not in layer.columns:
            continue
        layer = layer.copy()
        layer["protein_id"] = layer["protein_id"].map(_normalise_protein_id)
        layer = layer.drop_duplicates(subset=["protein_id"], keep="first")
        rename_columns = {
            column: f"{prefix}_{column}"
            for column in layer.columns
            if column not in {"protein_id", "gene"}
        }
        candidates = candidates.merge(
            layer.rename(columns=rename_columns),
            on="protein_id",
            how="left",
            suffixes=("", f"_{prefix}"),
        )
        if f"gene_{prefix}" in candidates.columns:
            missing_gene = candidates["gene"].fillna("").astype(str).str.strip().eq("")
            candidates.loc[missing_gene, "gene"] = candidates.loc[missing_gene, f"gene_{prefix}"]
    return candidates


def _build_controlled_clinical_impact(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    base = _controlled_context_base(workspace)
    if base.empty:
        return pd.DataFrame(
            columns=[
                "protein_id",
                "gene",
                "host_damage_reduction_potential",
                "disease_severity_association",
                "clinical_impact_score",
                "host_damage_score",
                "database",
                "controlled_context_rule",
                "controlled_context_inputs",
                "controlled_context_confidence_reason",
                "controlled_context_missing_flags",
            ]
        )

    rows = []
    for _, row in base.iterrows():
        virulence, virulence_flag = _numeric_row_value_with_flag(row, "virulence_virulence_score", 0.5)
        virulence_factor, virulence_factor_flag = _numeric_row_value_with_flag(row, "virulence_virulence_factor", 0.0)
        access, access_flag = _localization_access_with_flag(row.get("localization_localization", "unknown"), config)
        damage_reduction = _clamp_value(0.60 * virulence + 0.25 * virulence_factor + 0.15 * access)
        disease_severity = _clamp_value(0.75 * virulence + 0.25 * virulence_factor)
        clinical_impact = _clamp_value(0.45 * disease_severity + 0.35 * damage_reduction + 0.20 * access)
        host_damage = _clamp_value(0.45 * damage_reduction + 0.35 * disease_severity + 0.20 * virulence)
        inputs = {
            "virulence_score": virulence,
            "virulence_factor": virulence_factor,
            "localization_access": access,
        }
        rows.append(
            {
                "protein_id": row["protein_id"],
                "gene": row.get("gene", row["protein_id"]),
                "host_damage_reduction_potential": round(damage_reduction, 4),
                "disease_severity_association": round(disease_severity, 4),
                "clinical_impact_score": round(clinical_impact, 4),
                "host_damage_score": round(host_damage, 4),
                "database": str(config["online_sources"]["therapeutic_context"]["database_label"]),
                "controlled_context_rule": "clinical_impact_weighted_virulence_access_v1",
                "controlled_context_inputs": _format_controlled_inputs(inputs),
                "controlled_context_confidence_reason": _controlled_confidence_reason(config),
                "controlled_context_missing_flags": _format_missing_flags([virulence_flag, virulence_factor_flag, access_flag]),
            }
        )
    return pd.DataFrame(rows)


def _build_controlled_therapy_site_context(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    base = _controlled_context_base(workspace)
    if base.empty:
        return pd.DataFrame(
            columns=[
                "protein_id",
                "gene",
                "infection_site_access",
                "database",
                "controlled_context_rule",
                "controlled_context_inputs",
                "controlled_context_confidence_reason",
                "controlled_context_missing_flags",
            ]
        )

    rows = []
    for _, row in base.iterrows():
        localization_access, access_flag = _localization_access_with_flag(row.get("localization_localization", "unknown"), config)
        virulence, virulence_flag = _numeric_row_value_with_flag(row, "virulence_virulence_score", 0.5)
        infection_site_access = _clamp_value(0.85 * localization_access + 0.15 * virulence)
        inputs = {
            "localization_access": localization_access,
            "virulence_score": virulence,
        }
        rows.append(
            {
                "protein_id": row["protein_id"],
                "gene": row.get("gene", row["protein_id"]),
                "infection_site_access": round(infection_site_access, 4),
                "database": str(config["online_sources"]["therapeutic_context"]["database_label"]),
                "controlled_context_rule": "therapy_site_access_localization_weighted_v1",
                "controlled_context_inputs": _format_controlled_inputs(inputs),
                "controlled_context_confidence_reason": _controlled_confidence_reason(config),
                "controlled_context_missing_flags": _format_missing_flags([access_flag, virulence_flag]),
            }
        )
    return pd.DataFrame(rows)


def _build_controlled_curated_disease_context(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    base = _controlled_context_base(workspace)
    if base.empty:
        return pd.DataFrame(
            columns=[
                "protein_id",
                "gene",
                "infection_context_score",
                "database",
                "controlled_context_rule",
                "controlled_context_inputs",
                "controlled_context_confidence_reason",
                "controlled_context_missing_flags",
            ]
        )

    clinical = _build_controlled_clinical_impact(workspace, config).set_index("protein_id")
    site = _build_controlled_therapy_site_context(workspace, config).set_index("protein_id")
    rows = []
    for _, row in base.iterrows():
        protein_id = row["protein_id"]
        host_damage = float(clinical.at[protein_id, "host_damage_score"]) if protein_id in clinical.index else 0.5
        access = float(site.at[protein_id, "infection_site_access"]) if protein_id in site.index else 0.5
        clinical_flag = None if protein_id in clinical.index else "default_host_damage_score"
        site_flag = None if protein_id in site.index else "default_infection_site_access"
        network_centrality, network_centrality_flag = _numeric_row_value_with_flag(row, "network_network_centrality", 0.5)
        pathway_bottleneck, pathway_bottleneck_flag = _numeric_row_value_with_flag(row, "network_pathway_bottleneck_score", 0.5)
        dependency, dependency_flag = _numeric_row_value_with_flag(row, "network_functional_dependency_score", 0.5)
        core_presence, core_presence_flag = _numeric_row_value_with_flag(row, "conservation_core_genome_presence", 0.5)
        strain_coverage, strain_coverage_flag = _numeric_row_value_with_flag(row, "conservation_strain_coverage_score", 0.5)
        allelic_conservation, allelic_conservation_flag = _numeric_row_value_with_flag(row, "conservation_allelic_conservation", 0.5)
        variant_burden, variant_burden_flag = _numeric_row_value_with_flag(row, "conservation_variant_burden", 0.5)
        functional_impact = _clamp_value(0.35 * network_centrality + 0.35 * pathway_bottleneck + 0.30 * dependency)
        conservation = _clamp_value(0.40 * core_presence + 0.40 * strain_coverage + 0.20 * allelic_conservation - 0.15 * variant_burden)
        infection_context = _clamp_value(0.35 * host_damage + 0.25 * access + 0.20 * functional_impact + 0.20 * conservation)
        inputs = {
            "host_damage_score": host_damage,
            "infection_site_access": access,
            "functional_impact": functional_impact,
            "conservation": conservation,
        }
        rows.append(
            {
                "protein_id": protein_id,
                "gene": row.get("gene", protein_id),
                "infection_context_score": round(infection_context, 4),
                "database": str(config["online_sources"]["therapeutic_context"]["database_label"]),
                "controlled_context_rule": "disease_context_damage_access_function_conservation_v1",
                "controlled_context_inputs": _format_controlled_inputs(inputs),
                "controlled_context_confidence_reason": _controlled_confidence_reason(config),
                "controlled_context_missing_flags": _format_missing_flags(
                    [
                        clinical_flag,
                        site_flag,
                        network_centrality_flag,
                        pathway_bottleneck_flag,
                        dependency_flag,
                        core_presence_flag,
                        strain_coverage_flag,
                        allelic_conservation_flag,
                        variant_burden_flag,
                    ]
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_controlled_therapeutic_layer(layer_key: str, workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    if layer_key == "clinical_impact":
        return _build_controlled_clinical_impact(workspace, config)
    if layer_key == "curated_disease_context":
        return _build_controlled_curated_disease_context(workspace, config)
    if layer_key == "therapy_site_context":
        return _build_controlled_therapy_site_context(workspace, config)
    return pd.DataFrame()


def _localization_map_value(localization: object, config: dict[str, Any], mapping_name: str) -> tuple[float, str | None]:
    neutral = float(config["imputation"]["neutral_unknown_score"])
    mapping = config["localization"][mapping_name]
    value = str(localization or "unknown").strip().lower()
    if value in mapping:
        return float(mapping[value]), None
    return float(mapping.get("unknown", neutral)), f"default_{mapping_name}"


def _build_controlled_clinical_impact_v2(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    base = _controlled_context_base(workspace)
    columns = [
        "protein_id",
        "gene",
        "host_damage_reduction_potential",
        "disease_severity_association",
        "clinical_impact_score",
        "host_damage_score",
        "host_direct_damage_score",
        "virulence_associated_severity_score",
        "clinical_impact_catalog_source",
        "clinical_impact_evidence_type",
        "clinical_impact_evidence_reference",
        "clinical_impact_evidence_note",
        "database",
        "controlled_context_rule",
        "controlled_context_inputs",
        "controlled_context_confidence_reason",
        "controlled_context_missing_flags",
    ]
    if base.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    database_label = str(config["online_sources"]["therapeutic_context_v2"]["database_label"])
    catalog_defaults = config["online_sources"].get("curated_therapeutic_catalogs", {})
    for _, row in base.iterrows():
        virulence, virulence_flag = _numeric_row_value_with_flag(row, "virulence_virulence_score", 0.5)
        virulence_factor, virulence_factor_flag = _numeric_row_value_with_flag(row, "virulence_virulence_factor", 0.0)
        essentiality, essentiality_flag = _numeric_row_value_with_flag(row, "essentiality_essential", 0.5)
        host_damage = _clamp_value(0.70 * virulence + 0.20 * virulence_factor + 0.10 * essentiality)
        damage_reduction = _clamp_value(0.65 * virulence + 0.25 * virulence_factor + 0.10 * essentiality)
        disease_severity = _clamp_value(0.80 * virulence + 0.20 * virulence_factor)
        clinical_impact = _clamp_value(0.55 * disease_severity + 0.35 * host_damage + 0.10 * essentiality)
        inputs = {
            "virulence_score": virulence,
            "virulence_factor": virulence_factor,
            "essentiality": essentiality,
        }
        rows.append(
            {
                "protein_id": row["protein_id"],
                "gene": row.get("gene", row["protein_id"]),
                "host_damage_reduction_potential": round(damage_reduction, 4),
                "disease_severity_association": round(disease_severity, 4),
                "clinical_impact_score": round(clinical_impact, 4),
                "host_damage_score": round(host_damage, 4),
                "host_direct_damage_score": round(host_damage, 4),
                "virulence_associated_severity_score": round(disease_severity, 4),
                "clinical_impact_catalog_source": "controlled_therapeutic_context_v2",
                "clinical_impact_evidence_type": "controlled_provider",
                "clinical_impact_evidence_reference": "not_experimental",
                "clinical_impact_evidence_note": "host_direct_damage_score and virulence_associated_severity_score are separated controlled derivations.",
                "database": database_label,
                "controlled_context_rule": "clinical_impact_host_damage_virulence_v2",
                "controlled_context_inputs": _format_controlled_inputs(inputs),
                "controlled_context_confidence_reason": _controlled_confidence_reason_v2(config),
                "controlled_context_missing_flags": _format_missing_flags([virulence_flag, virulence_factor_flag, essentiality_flag]),
            }
        )
    return pd.DataFrame(rows)


def _build_controlled_therapy_site_context_v2(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    base = _controlled_context_base(workspace)
    columns = [
        "protein_id",
        "gene",
        "infection_site_access",
        "infection_site",
        "access_evidence_type",
        "access_evidence_reference",
        "access_evidence_note",
        "disease_context",
        "syndrome",
        "disease_site_context_source",
        "database",
        "controlled_context_rule",
        "controlled_context_inputs",
        "controlled_context_confidence_reason",
        "controlled_context_missing_flags",
    ]
    if base.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    database_label = str(config["online_sources"]["therapeutic_context_v2"]["database_label"])
    catalog_defaults = config["online_sources"].get("curated_therapeutic_catalogs", {})
    for _, row in base.iterrows():
        localization = row.get("localization_localization", "unknown")
        infection_access, infection_flag = _localization_map_value(localization, config, "infection_site_access")
        physical_access, physical_flag = _localization_map_value(localization, config, "physical_accessibility")
        small_molecule, small_molecule_flag = _localization_map_value(localization, config, "small_molecule_feasibility")
        antibody, antibody_flag = _localization_map_value(localization, config, "antibody_feasibility")
        membrane_penalty, membrane_flag = _localization_map_value(localization, config, "membrane_crossing_penalty")
        membrane_feasibility = _clamp_value(1.0 - membrane_penalty)
        infection_site_access = _clamp_value(
            0.35 * infection_access
            + 0.25 * physical_access
            + 0.20 * small_molecule
            + 0.10 * antibody
            + 0.10 * membrane_feasibility
        )
        inputs = {
            "infection_access": infection_access,
            "physical_accessibility": physical_access,
            "small_molecule_feasibility": small_molecule,
            "antibody_feasibility": antibody,
            "membrane_feasibility": membrane_feasibility,
        }
        rows.append(
            {
                "protein_id": row["protein_id"],
                "gene": row.get("gene", row["protein_id"]),
                "infection_site_access": round(infection_site_access, 4),
                "infection_site": str(catalog_defaults.get("default_infection_site", "not_reported")),
                "access_evidence_type": "controlled_provider",
                "access_evidence_reference": "not_experimental",
                "access_evidence_note": "Controlled access estimate from localization and barrier feasibility.",
                "disease_context": str(catalog_defaults.get("default_disease_context", "not_reported")),
                "syndrome": str(catalog_defaults.get("default_disease_context", "not_reported")),
                "disease_site_context_source": "controlled_therapeutic_context_v2",
                "database": database_label,
                "controlled_context_rule": "therapy_site_access_localization_barrier_v2",
                "controlled_context_inputs": _format_controlled_inputs(inputs),
                "controlled_context_confidence_reason": _controlled_confidence_reason_v2(config),
                "controlled_context_missing_flags": _format_missing_flags(
                    [infection_flag, physical_flag, small_molecule_flag, antibody_flag, membrane_flag]
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_controlled_curated_disease_context_v2(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    base = _controlled_context_base(workspace)
    columns = [
        "protein_id",
        "gene",
        "infection_context_score",
        "database",
        "controlled_context_rule",
        "controlled_context_inputs",
        "controlled_context_confidence_reason",
        "controlled_context_missing_flags",
    ]
    if base.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    database_label = str(config["online_sources"]["therapeutic_context_v2"]["database_label"])
    for _, row in base.iterrows():
        virulence, virulence_flag = _numeric_row_value_with_flag(row, "virulence_virulence_score", 0.5)
        essentiality, essentiality_flag = _numeric_row_value_with_flag(row, "essentiality_essential", 0.5)
        network_centrality, network_centrality_flag = _numeric_row_value_with_flag(row, "network_network_centrality", 0.5)
        pathway_bottleneck, pathway_bottleneck_flag = _numeric_row_value_with_flag(row, "network_pathway_bottleneck_score", 0.5)
        dependency, dependency_flag = _numeric_row_value_with_flag(row, "network_functional_dependency_score", 0.5)
        redundancy, redundancy_flag = _numeric_row_value_with_flag(row, "network_redundancy_penalty", 0.5)
        core_presence, core_presence_flag = _numeric_row_value_with_flag(row, "conservation_core_genome_presence", 0.5)
        strain_coverage, strain_coverage_flag = _numeric_row_value_with_flag(row, "conservation_strain_coverage_score", 0.5)
        allelic_conservation, allelic_conservation_flag = _numeric_row_value_with_flag(row, "conservation_allelic_conservation", 0.5)
        variant_burden, variant_burden_flag = _numeric_row_value_with_flag(row, "conservation_variant_burden", 0.5)
        functional_impact = _clamp_value(0.30 * network_centrality + 0.30 * pathway_bottleneck + 0.25 * dependency + 0.15 * (1.0 - redundancy))
        conservation = _clamp_value(0.40 * core_presence + 0.35 * strain_coverage + 0.20 * allelic_conservation - 0.15 * variant_burden)
        infection_context = _clamp_value(0.35 * functional_impact + 0.30 * conservation + 0.20 * virulence + 0.15 * essentiality)
        inputs = {
            "functional_impact": functional_impact,
            "conservation": conservation,
            "virulence_score": virulence,
            "essentiality": essentiality,
        }
        rows.append(
            {
                "protein_id": row["protein_id"],
                "gene": row.get("gene", row["protein_id"]),
                "infection_context_score": round(infection_context, 4),
                "database": database_label,
                "controlled_context_rule": "disease_context_function_conservation_infection_v2",
                "controlled_context_inputs": _format_controlled_inputs(inputs),
                "controlled_context_confidence_reason": _controlled_confidence_reason_v2(config),
                "controlled_context_missing_flags": _format_missing_flags(
                    [
                        virulence_flag,
                        essentiality_flag,
                        network_centrality_flag,
                        pathway_bottleneck_flag,
                        dependency_flag,
                        redundancy_flag,
                        core_presence_flag,
                        strain_coverage_flag,
                        allelic_conservation_flag,
                        variant_burden_flag,
                    ]
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_controlled_therapeutic_layer_v2(layer_key: str, workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    if layer_key == "clinical_impact":
        return _build_controlled_clinical_impact_v2(workspace, config)
    if layer_key == "curated_disease_context":
        return _build_controlled_curated_disease_context_v2(workspace, config)
    if layer_key == "therapy_site_context":
        return _build_controlled_therapy_site_context_v2(workspace, config)
    return pd.DataFrame()


def _extract_uniprot_locations(annotation_value: object) -> str:
    text = str(annotation_value or "").strip().lower()
    if not text:
        return "unknown"
    if "outer membrane" in text:
        return "outer_membrane"
    if "inner membrane" in text or "cell membrane" in text or "membrane" in text:
        return "inner_membrane"
    if "periplasm" in text:
        return "periplasm"
    if "cell wall" in text or "surface" in text:
        return "cell_wall"
    if "secreted" in text or "extracellular" in text:
        return "extracellular"
    if "cytoplasm" in text or "cytosol" in text:
        return "cytoplasm"
    return "unknown"


def _build_localization_from_uniprot(annotations: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if annotations.empty:
        return pd.DataFrame(columns=["protein_id", "gene", "localization", "database"])
    return pd.DataFrame(
        {
            "protein_id": annotations["protein_id"],
            "gene": annotations["gene"],
            "localization": annotations.get("uniprot_subcellular_location", pd.Series(["unknown"] * len(annotations))).map(_extract_uniprot_locations),
            "database": str(config["online_sources"]["uniprot"]["database_label"]),
        }
    )


def _build_human_homologs_stub(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    raw_path = workspace / "data_raw" / "human_homologs.csv"
    if raw_path.exists() and not _raw_file_marked_demo(workspace, "human_homologs.csv"):
        existing = pd.read_csv(raw_path).copy()
        if "database" not in existing.columns:
            existing["database"] = "configurable_stub_human_homologs_v1"
        return _annotate_human_homologs_audit(existing)
    candidates = _get_candidate_proteins(workspace)
    if candidates.empty:
        return pd.DataFrame(
            columns=[
                "protein_id",
                "gene",
                "human_homolog",
                "evalue",
                "human_gene",
                "database",
                "homology_lookup_status",
                "homology_query_strategy",
                "homology_evidence_note",
                "human_uniprot_accession",
                "human_uniprot_id",
                "homology_evidence_tier",
                "homology_confidence_score",
                "homology_missing_flags",
            ]
        )
    rows = [
        _human_homolog_row(
            protein_id=str(row["protein_id"]),
            gene=str(row.get("gene", row["protein_id"])),
            human_homolog=pd.NA,
            evalue=pd.NA,
            human_gene="unknown",
            database="configurable_stub_human_homologs_unknown_v1",
            lookup_status="unknown_no_real_homology_evidence",
            query_strategy="demo_raw_ignored_or_no_curated_input",
            evidence_note="No hay evidencia real suficiente para afirmar presencia o ausencia de homologia humana.",
        )
        for _, row in candidates.iterrows()
    ]
    return _annotate_human_homologs_audit(pd.DataFrame(rows))


def _build_unresolved_human_homologs(
    workspace: Path,
    database: str,
    lookup_status: str,
    query_strategy: str,
    evidence_note: str,
) -> pd.DataFrame:
    candidates = _get_candidate_proteins(workspace)
    if candidates.empty:
        return pd.DataFrame(columns=["protein_id", "gene", "human_homolog", "evalue", "human_gene", "database"])
    rows = [
        _human_homolog_row(
            protein_id=str(row["protein_id"]),
            gene=str(row.get("gene", row["protein_id"])),
            human_homolog=pd.NA,
            evalue=pd.NA,
            human_gene="unknown",
            database=database,
            lookup_status=lookup_status,
            query_strategy=query_strategy,
            evidence_note=evidence_note,
        )
        for _, row in candidates.iterrows()
    ]
    return _annotate_human_homologs_audit(pd.DataFrame(rows))


def _api_get_json(url: str, cfg: dict[str, Any]) -> tuple[Any | None, list[str]]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        response = request_provider_payload(url, timeout=timeout, user_agent=user_agent, accept="application/json", opener=urlopen)
        if response.error_status == "" and response.payload_type == "json":
            return response.payload, errors
        errors.append(response.rejection_reason or response.error_status or f"unexpected_payload_type:{response.payload_type}")
        if response.http_status == 429 and attempt < retries:
            time.sleep(backoff)
            continue
        if response.payload_type == "undecodable":
            errors.append("Respuesta JSON invalida en human_homologs_lookup")
            break
        break
    return None, errors


def _load_uniprot_annotation_lookup(workspace: Path) -> pd.DataFrame:
    path = workspace / "data_raw" / "uniprot_annotations.csv"
    if not path.exists():
        return pd.DataFrame(columns=["protein_id", "uniprot_protein_name"])
    annotations = pd.read_csv(path)
    if "protein_id" not in annotations.columns:
        return pd.DataFrame(columns=["protein_id", "uniprot_protein_name"])
    annotations = annotations.copy()
    annotations["protein_id"] = annotations["protein_id"].astype("string").str.strip().str.upper()
    keep_columns = [column for column in ["protein_id", "uniprot_protein_name"] if column in annotations.columns]
    return annotations[keep_columns].drop_duplicates(subset=["protein_id"], keep="first")


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
        return pd.DataFrame(columns=["protein_id", "gene"])
    proteins = pd.DataFrame(candidates.values()).sort_values("protein_id").reset_index(drop=True)
    annotations = _load_uniprot_annotation_lookup(workspace)
    if not annotations.empty:
        proteins = proteins.merge(annotations, on="protein_id", how="left")
    if "uniprot_protein_name" not in proteins.columns:
        proteins["uniprot_protein_name"] = ""
    return proteins


def _extract_gene_names(entry: dict[str, Any]) -> list[str]:
    results = []
    for gene in entry.get("genes", []) or []:
        gene_name = gene.get("geneName", {})
        if gene_name.get("value"):
            results.append(str(gene_name["value"]))
        for field in ["synonyms", "orderedLocusNames", "orfNames"]:
            for item in gene.get(field, []) or []:
                if item.get("value"):
                    results.append(str(item["value"]))
    deduped = []
    for item in results:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _query_uniprot_human_gene(gene: str, cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    query = f"(organism_id:{cfg['human_taxon_id']}) AND (gene:{gene})"
    params = {
        "query": query,
        "format": "json",
        "size": int(cfg["max_results_per_query"]),
        "fields": str(cfg["fields"]),
    }
    url = f"{str(cfg['provider_base_url'])}?{urlencode(params)}"
    payload, errors = _api_get_json(url, cfg)
    if not payload:
        return None, errors
    results = payload.get("results", []) or []
    if not results:
        return None, errors
    return results[0], errors


def _query_uniprot_human_protein_name(protein_name: str, cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    clean_name = str(protein_name or "").strip()
    if not clean_name or clean_name.lower() in {"nan", "none", "unknown"}:
        return None, []
    query = f'(organism_id:{cfg["human_taxon_id"]}) AND (protein_name:"{clean_name}")'
    params = {
        "query": query,
        "format": "json",
        "size": int(cfg["max_results_per_query"]),
        "fields": str(cfg["fields"]),
    }
    url = f"{str(cfg['provider_base_url'])}?{urlencode(params)}"
    payload, errors = _api_get_json(url, cfg)
    if not payload:
        return None, errors
    results = payload.get("results", []) or []
    if not results:
        return None, errors
    return results[0], errors


def _load_curated_human_gene_lookup(workspace: Path) -> dict[str, str]:
    path = workspace / "data_raw" / "human_homologs.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    if "protein_id" not in df.columns or "human_gene" not in df.columns:
        return {}
    if _raw_file_marked_demo(workspace, "human_homologs.csv"):
        return {}
    curated_mask = pd.Series([True] * len(df), index=df.index)
    if "database" in df.columns:
        database_values = df["database"].fillna("").astype(str).str.lower()
        if database_values.str.contains("demo|example_").any():
            return {}
        curated_mask = database_values.str.contains("curated") & ~database_values.str.contains("computed|stub|configurable")
        if not curated_mask.any():
            return {}
    lookup: dict[str, str] = {}
    for _, row in df.loc[curated_mask].iterrows():
        human_homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
        if pd.isna(human_homolog) or int(human_homolog) != 1:
            continue
        human_gene = str(row.get("human_gene") or "").strip()
        if not human_gene or human_gene.lower() in {"none", "nan", "unknown"}:
            continue
        protein_id = str(row.get("protein_id") or "").strip().upper()
        if protein_id:
            lookup[protein_id] = human_gene
    return lookup


def _human_homolog_row(
    protein_id: str,
    gene: str,
    human_homolog: object,
    evalue: object,
    human_gene: str,
    database: str,
    lookup_status: str,
    query_strategy: str,
    evidence_note: str,
    human_uniprot_accession: str = "",
    human_uniprot_id: str = "",
) -> dict[str, object]:
    return {
        "protein_id": protein_id,
        "gene": gene,
        "human_homolog": human_homolog,
        "evalue": evalue,
        "human_gene": human_gene,
        "database": database,
        "homology_lookup_status": lookup_status,
        "homology_query_strategy": query_strategy,
        "homology_evidence_note": evidence_note,
        "human_uniprot_accession": human_uniprot_accession,
        "human_uniprot_id": human_uniprot_id,
    }


def _normalise_local_orthology_row(row: pd.Series, cfg: dict[str, Any]) -> dict[str, object] | None:
    protein_id = str(row.get("protein_id", "") or "").strip().upper()
    if not protein_id:
        return None
    gene = str(row.get("gene", "") or "").strip() or protein_id
    human_gene = str(row.get("human_gene", "") or "").strip()
    evalue = pd.to_numeric(pd.Series([row.get("evalue")]), errors="coerce").iloc[0]
    confidence = pd.to_numeric(pd.Series([row.get("orthology_confidence_score")]), errors="coerce").iloc[0]
    if pd.isna(confidence):
        confidence = pd.to_numeric(pd.Series([row.get("source_quality")]), errors="coerce").iloc[0]
    min_confidence = float(cfg.get("local_orthology_min_confidence", 0.60))
    human_homolog_raw = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]

    supported_by_flag = pd.notna(human_homolog_raw) and int(human_homolog_raw) == 1
    supported_by_confidence = pd.notna(confidence) and float(confidence) >= min_confidence
    supported_by_gene = bool(human_gene) and human_gene.lower() not in {"none", "nan", "unknown"}
    human_homolog = 1 if supported_by_flag or (supported_by_confidence and supported_by_gene) else 0
    if human_homolog == 0 and not human_gene:
        human_gene = "none"

    normalized = _human_homolog_row(
        protein_id=protein_id,
        gene=gene,
        human_homolog=human_homolog,
        evalue=evalue if pd.notna(evalue) else pd.NA,
        human_gene=human_gene,
        database=str(row.get("database", "") or cfg.get("local_orthology_database_label", "local_reproducible_orthology_v1")),
        lookup_status="local_orthology_match" if human_homolog == 1 else "local_orthology_no_match",
        query_strategy=str(row.get("orthology_method", "") or "local_orthology_file"),
        evidence_note=str(row.get("orthology_evidence_note", "") or "Local reproducible orthology file mapped to human_homologs contract."),
        human_uniprot_accession=str(row.get("human_uniprot_accession", "") or ""),
        human_uniprot_id=str(row.get("human_uniprot_id", "") or ""),
    )
    for column in [
        "orthology_method",
        "orthology_tool",
        "orthology_version",
        "orthology_reference",
        "orthology_query_coverage",
        "orthology_subject_coverage",
        "orthology_percent_identity",
        "orthology_bitscore",
        "orthology_confidence_score",
        "orthology_evidence_note",
    ]:
        normalized[column] = row.get(column, "")
    for source_column, target_column in [
        ("human_hit_id", "human_uniprot_accession"),
        ("human_hit_name", "human_gene"),
        ("percent_identity", "orthology_percent_identity"),
        ("query_coverage", "orthology_query_coverage"),
        ("subject_coverage", "orthology_subject_coverage"),
        ("bit_score", "orthology_bitscore"),
        ("source_database", "database"),
        ("curator_notes", "orthology_evidence_note"),
    ]:
        if source_column in row.index and (not normalized.get(target_column)):
            normalized[target_column] = row.get(source_column, "")
    return normalized


def _load_local_orthology_human_homologs(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    cfg = config["online_sources"]["human_homologs_lookup"]
    if not bool(cfg.get("local_orthology_enabled", True)):
        return pd.DataFrame()
    relative_path = str(cfg.get("local_orthology_filename", "data_external/human_homologs_orthology.csv"))
    path = workspace / relative_path
    if not path.exists():
        return pd.DataFrame()
    orthology = pd.read_csv(path)
    if orthology.empty or "protein_id" not in orthology.columns:
        return pd.DataFrame()
    rows = []
    for _, row in orthology.iterrows():
        normalized = _normalise_local_orthology_row(row, cfg)
        if normalized is not None:
            rows.append(normalized)
    if not rows:
        return pd.DataFrame()
    return _annotate_human_homologs_audit(pd.DataFrame(rows).drop_duplicates(subset=["protein_id"], keep="first"))


def _write_diamond_manifest(workspace: Path, manifest: dict[str, Any]) -> None:
    results_dir = workspace / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "human_homology_diamond_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _load_diamond_human_homologs(workspace: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    cfg = config.get("online_sources", {}).get("human_homology_diamond", {})
    try:
        df, manifest = build_human_homologs_with_diamond(workspace, cfg)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        manifest = {
            "provider_name": "human_homology_diamond",
            "status": "diamond_provider_unresolved",
            "retrieval_status": "diamond_provider_unresolved",
            "execution_status": "failed_before_execution",
            "fallback_reason": str(exc),
            "notes": [str(exc), "No se infirio presencia ni ausencia biologica por el fallo del proveedor."],
        }
        _write_diamond_manifest(workspace, manifest)
        return pd.DataFrame(), manifest
    _write_diamond_manifest(workspace, manifest)
    if df.empty:
        return df, manifest
    return _annotate_human_homologs_audit(df), manifest


def _homology_audit_from_row(row: pd.Series) -> tuple[str, float, str]:
    lookup_status = str(row.get("homology_lookup_status", "") or "").strip()
    query_strategy = str(row.get("homology_query_strategy", "") or "").strip()
    human_homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
    evalue = pd.to_numeric(pd.Series([row.get("evalue")]), errors="coerce").iloc[0]
    human_gene = str(row.get("human_gene", "") or "").strip()
    human_accession = str(row.get("human_uniprot_accession", "") or "").strip()
    database = str(row.get("database", "") or "").strip().lower()

    missing_flags: list[str] = []
    if pd.isna(human_homolog):
        missing_flags.append("missing_human_homolog")
    if not human_gene or human_gene.lower() in {"none", "nan", "unknown"}:
        missing_flags.append("missing_human_gene")
    if pd.isna(evalue):
        missing_flags.append("missing_alignment_evalue")
    if not human_accession:
        missing_flags.append("missing_human_uniprot_accession")

    if lookup_status == "name_match_unverified":
        return "name_match_unverified", 0.30, _format_missing_flags(missing_flags)
    if lookup_status == "diamond_unresolved":
        return "diamond_unresolved", 0.0, _format_missing_flags(missing_flags)
    if lookup_status == "real_match" and query_strategy in {"human_gene_exact", "human_curated_gene", "human_protein_name"}:
        return "name_match_unverified", 0.30, _format_missing_flags(missing_flags)
    if lookup_status in {"diamond_hit", "diamond_no_hit"}:
        tier = str(row.get("homology_evidence_tier", "") or "").strip()
        confidence = pd.to_numeric(pd.Series([row.get("homology_confidence_score")]), errors="coerce").fillna(0.60).iloc[0]
        return tier or "diamond_sequence_alignment", float(confidence), _format_missing_flags(missing_flags)
    if lookup_status == "local_orthology_match":
        confidence = pd.to_numeric(pd.Series([row.get("orthology_confidence_score")]), errors="coerce").fillna(0.75).iloc[0]
        return "local_reproducible_orthology", float(confidence), _format_missing_flags(missing_flags)
    if lookup_status == "local_orthology_no_match":
        return "local_orthology_no_match", 0.60, _format_missing_flags([flag for flag in missing_flags if flag != "missing_human_gene"])
    if lookup_status == "real_partial_non_exact":
        return "real_inconclusive_match", 0.45, _format_missing_flags(missing_flags)
    if lookup_status == "no_real_match":
        return "real_lookup_no_match", 0.55, _format_missing_flags([flag for flag in missing_flags if flag != "missing_human_gene"])
    if lookup_status == "stub_backfill_after_inconclusive_real_lookup":
        return "stub_backfill_after_real_lookup", 0.35, _format_missing_flags(missing_flags)
    if lookup_status == "stub_only" or "stub" in database:
        return "configurable_stub_only", 0.25, _format_missing_flags(missing_flags)
    if pd.notna(human_homolog):
        return "legacy_or_user_supplied_unclassified", 0.50, _format_missing_flags(missing_flags)
    return "unclassified_missing_homology", 0.20, _format_missing_flags(missing_flags)


def _annotate_human_homologs_audit(df: pd.DataFrame) -> pd.DataFrame:
    annotated = df.copy()
    for column, default in [
        ("homology_lookup_status", "stub_only"),
        ("homology_query_strategy", "configurable_stub"),
        ("homology_evidence_note", "No real lookup row was available; retained configurable stub value."),
        ("human_uniprot_accession", ""),
        ("human_uniprot_id", ""),
    ]:
        if column not in annotated.columns:
            annotated[column] = default
    audit_rows = annotated.apply(_homology_audit_from_row, axis=1)
    annotated["homology_evidence_tier"] = audit_rows.map(lambda item: item[0])
    annotated["homology_confidence_score"] = audit_rows.map(lambda item: item[1])
    annotated["homology_missing_flags"] = audit_rows.map(lambda item: item[2])
    return annotated


def _build_human_homologs_from_real_lookup(workspace: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, int, list[str], bool]:
    cfg = config["online_sources"]["human_homologs_lookup"]
    proteins = _get_candidate_proteins(workspace)
    if proteins.empty:
        return pd.DataFrame(
            columns=[
                "protein_id",
                "gene",
                "human_homolog",
                "evalue",
                "human_gene",
                "database",
                "human_uniprot_accession",
                "human_uniprot_id",
            ]
        ), 0, ["no_candidate_proteins"], False

    rows = []
    notes: list[str] = []
    exact_matches = 0
    api_success = True
    curated_human_genes = _load_curated_human_gene_lookup(workspace)
    for _, protein in proteins.iterrows():
        protein_id = str(protein["protein_id"]).strip()
        gene = str(protein["gene"]).strip()
        entry, errors = _query_uniprot_human_gene(gene, cfg)
        notes.extend(errors)
        if errors:
            api_success = False
        query_strategy = "human_gene_exact"
        if not entry:
            protein_name = str(protein.get("uniprot_protein_name", "") or "").strip()
            protein_entry, protein_errors = _query_uniprot_human_protein_name(protein_name, cfg)
            notes.extend(protein_errors)
            if protein_errors:
                api_success = False
            if protein_entry:
                entry = protein_entry
                query_strategy = "human_protein_name"
        if not entry:
            curated_human_gene = curated_human_genes.get(protein_id.upper(), "")
            if curated_human_gene:
                curated_entry, curated_errors = _query_uniprot_human_gene(curated_human_gene, cfg)
                notes.extend(curated_errors)
                if curated_errors:
                    api_success = False
                if curated_entry:
                    entry = curated_entry
                    query_strategy = "human_curated_gene"
        if not entry:
            rows.append(
                _human_homolog_row(
                    protein_id=protein_id,
                    gene=gene,
                    human_homolog=pd.NA,
                    evalue=pd.NA,
                    human_gene="",
                    database=str(cfg["database_label"]),
                    lookup_status="no_real_match",
                    query_strategy=query_strategy,
                    evidence_note="UniProt human lookup returned no usable match; keep fallback evidence if available.",
                )
            )
            continue
        gene_names = _extract_gene_names(entry)
        exact_match = any(item.casefold() == gene.casefold() for item in gene_names)
        curated_human_gene = curated_human_genes.get(protein_id.upper(), "")
        curated_gene_match = bool(curated_human_gene) and any(
            item.casefold() == curated_human_gene.casefold() for item in gene_names
        )
        if exact_match or query_strategy == "human_protein_name" or (
            query_strategy == "human_curated_gene" and curated_gene_match
        ):
            exact_matches += 1
            rows.append(
                _human_homolog_row(
                    protein_id=protein_id,
                    gene=gene,
                    human_homolog=pd.NA,
                    evalue=pd.NA,
                    human_gene=gene_names[0] if gene_names else gene,
                    database=str(cfg["database_label"]),
                    lookup_status="name_match_unverified",
                    query_strategy=query_strategy,
                    evidence_note=(
                        "UniProt human lookup found a name or gene-symbol match, but no sequence-alignment "
                        "metrics were available; this is auxiliary evidence and does not establish homology."
                    ),
                    human_uniprot_accession=str(entry.get("primaryAccession") or ""),
                    human_uniprot_id=str(entry.get("uniProtkbId") or ""),
                )
            )
        else:
            rows.append(
                _human_homolog_row(
                    protein_id=protein_id,
                    gene=gene,
                    human_homolog=pd.NA,
                    evalue=pd.NA,
                    human_gene="",
                    database=str(cfg["database_label"]),
                    lookup_status="name_match_unverified",
                    query_strategy=query_strategy,
                    evidence_note=(
                        "UniProt returned a human entry without sequence-alignment metrics or exact curated support; "
                        "the candidate hit was not associated as a homolog."
                    ),
                )
            )
    return _annotate_human_homologs_audit(pd.DataFrame(rows)), exact_matches, notes, api_success


def _merge_human_homologs_with_stub(real_df: pd.DataFrame, stub_df: pd.DataFrame) -> pd.DataFrame:
    if stub_df.empty:
        return real_df.copy()
    merged = stub_df.copy()
    if "protein_id" in merged.columns:
        merged["protein_id"] = merged["protein_id"].astype("string").str.strip().str.upper()
    real_lookup = real_df.copy()
    if "protein_id" in real_lookup.columns:
        real_lookup["protein_id"] = real_lookup["protein_id"].astype("string").str.strip().str.upper()
    real_lookup = real_lookup.set_index("protein_id")
    for idx, row in merged.iterrows():
        protein_id = str(row.get("protein_id", "")).strip().upper()
        if not protein_id or protein_id not in real_lookup.index:
            merged.at[idx, "homology_lookup_status"] = "stub_only"
            merged.at[idx, "homology_query_strategy"] = "configurable_stub"
            merged.at[idx, "homology_evidence_note"] = "No real lookup row was available; retained configurable stub value."
            continue
        real_row = real_lookup.loc[protein_id]
        if str(real_row.get("homology_lookup_status", "") or "") == "name_match_unverified":
            merged.at[idx, "human_homolog"] = pd.NA
            merged.at[idx, "evalue"] = pd.NA
            merged.at[idx, "human_gene"] = real_row.get("human_gene", "")
            merged.at[idx, "database"] = real_row.get("database")
            merged.at[idx, "homology_lookup_status"] = "name_match_unverified"
            merged.at[idx, "homology_query_strategy"] = real_row.get("homology_query_strategy", "human_gene_exact")
            merged.at[idx, "homology_evidence_note"] = real_row.get(
                "homology_evidence_note",
                "Name match without sequence-alignment metrics; retained as auxiliary evidence only.",
            )
            merged.at[idx, "human_uniprot_accession"] = real_row.get("human_uniprot_accession", "")
            merged.at[idx, "human_uniprot_id"] = real_row.get("human_uniprot_id", "")
        elif pd.notna(real_row.get("human_homolog")):
            merged.at[idx, "human_homolog"] = real_row.get("human_homolog")
            merged.at[idx, "evalue"] = real_row.get("evalue")
            merged.at[idx, "human_gene"] = real_row.get("human_gene")
            merged.at[idx, "database"] = real_row.get("database")
            merged.at[idx, "homology_lookup_status"] = real_row.get("homology_lookup_status", "real_match")
            merged.at[idx, "homology_query_strategy"] = real_row.get("homology_query_strategy", "human_gene_exact")
            merged.at[idx, "homology_evidence_note"] = real_row.get("homology_evidence_note", "Real lookup overrode stub value.")
            merged.at[idx, "human_uniprot_accession"] = real_row.get("human_uniprot_accession", "")
            merged.at[idx, "human_uniprot_id"] = real_row.get("human_uniprot_id", "")
        else:
            merged.at[idx, "homology_lookup_status"] = "stub_backfill_after_inconclusive_real_lookup"
            merged.at[idx, "homology_query_strategy"] = real_row.get("homology_query_strategy", "human_gene_exact")
            merged.at[idx, "homology_evidence_note"] = "Real lookup was inconclusive; retained configurable stub value."
            if "human_uniprot_accession" not in merged.columns:
                merged["human_uniprot_accession"] = ""
            if "human_uniprot_id" not in merged.columns:
                merged["human_uniprot_id"] = ""
    existing_ids = {str(item).strip().upper() for item in merged.get("protein_id", pd.Series(dtype="string")).tolist()}
    additional = real_df.loc[
        real_df["protein_id"].astype("string").str.strip().str.upper().map(lambda item: item not in existing_ids)
    ].copy()
    if not additional.empty:
        merged = pd.concat([merged, additional], ignore_index=True, sort=False)
    return _annotate_human_homologs_audit(merged)


def _human_similarity_from_row(row: pd.Series, neutral: float) -> tuple[float, str | None]:
    human_homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
    if pd.isna(human_homolog):
        return neutral, "default_human_homolog"
    if int(human_homolog) == 0:
        return 0.0, None

    evalue = pd.to_numeric(pd.Series([row.get("evalue")]), errors="coerce").iloc[0]
    if pd.isna(evalue):
        return 0.60, "default_evalue_missing"
    value = max(float(evalue), 1e-300)
    similarity = min(1.0, max(0.0, -math.log10(value) / 50.0))
    return similarity, None


def _build_controlled_host_annotation(workspace: Path, config: dict[str, Any]) -> pd.DataFrame:
    columns = [
        "protein_id",
        "gene",
        "domain_overlap_score",
        "host_criticality_penalty",
        "database",
        "host_annotation_rule",
        "host_annotation_inputs",
        "host_annotation_confidence_reason",
        "host_annotation_missing_flags",
    ]
    homologs_path = workspace / "data_raw" / "human_homologs.csv"
    if homologs_path.exists():
        homologs = pd.read_csv(homologs_path)
    else:
        homologs = _build_human_homologs_stub(workspace, config)
    if homologs.empty or "protein_id" not in homologs.columns:
        return pd.DataFrame(columns=columns)

    cfg = config["online_sources"]["host_annotation"]
    neutral = float(config["imputation"]["neutral_unknown_score"])
    rows = []
    for _, row in homologs.iterrows():
        protein_id = str(row.get("protein_id", "")).strip().upper()
        if not protein_id:
            continue
        gene = str(row.get("gene", "")).strip() or protein_id
        human_homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
        homolog_signal = neutral if pd.isna(human_homolog) else float(human_homolog)
        similarity, similarity_flag = _human_similarity_from_row(row, neutral)
        lookup_status = str(row.get("homology_lookup_status", "") or "").strip()
        real_match_signal = 1.0 if lookup_status == "real_match" else 0.0
        inconclusive_signal = 1.0 if lookup_status in {"real_partial_non_exact", "stub_backfill_after_inconclusive_real_lookup"} else 0.0
        domain_overlap = _clamp_value(0.70 * similarity + 0.20 * homolog_signal + 0.10 * real_match_signal)
        host_criticality = _clamp_value(0.60 * similarity + 0.25 * homolog_signal + 0.15 * inconclusive_signal)
        inputs = {
            "human_similarity": similarity,
            "human_homolog": homolog_signal,
            "real_match_signal": real_match_signal,
            "inconclusive_signal": inconclusive_signal,
        }
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "domain_overlap_score": round(domain_overlap, 4),
                "host_criticality_penalty": round(host_criticality, 4),
                "database": str(cfg["database_label"]),
                "host_annotation_rule": "host_annotation_homology_risk_v1",
                "host_annotation_inputs": _format_controlled_inputs(inputs),
                "host_annotation_confidence_reason": (
                    f"controlled_from_resolved_human_homologs; confidence={float(cfg['confidence_controlled']):.2f}; "
                    "not_experimental_domain_annotation"
                ),
                "host_annotation_missing_flags": _format_missing_flags([similarity_flag]),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def fetch_layer_external_source(
    layer_key: str,
    workspace: Path,
    filename: str,
    config: dict[str, Any],
    provider_name: str,
) -> dict[str, Any]:
    external_dir = workspace / config["layer_resolution"]["external_data_dir"]
    external_path = external_dir / filename
    context = _workspace_context(workspace)
    organism_name = context["organism_name"] or "unknown"
    taxon_id = context["taxon_id"]
    online_mode = effective_online_source_mode(config)

    if not _provider_is_enabled(config, provider_name):
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": provider_name,
            "path": None,
            "status": "provider_disabled_by_configuration",
            "confidence": 0.0,
            "notes": ["provider_disabled_before_file_cache_or_network_lookup"],
            "provenance": "provider switch from the isolated run configuration",
        }

    if provider_name in NETWORK_PROVIDERS and _network_is_blocked(config):
        if external_path.exists():
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": f"{provider_name}:data_external",
                "path": str(external_path),
                "status": "external_file_available_offline_mode",
                "confidence": float(config["layer_resolution"]["default_confidence_by_source"].get("external", 0.70)),
                "notes": ["api_not_requested_offline_mode", f"online_source_mode={online_mode}"],
                "provenance": "external provider skipped before network because offline-safe mode is active",
            }
        if provider_name in {"uniprot_human_gene_lookup", "human_homology_diamond"} and layer_key == "human_homologs":
            local_orthology = _load_local_orthology_human_homologs(workspace, config)
            if not local_orthology.empty:
                written_path = _write_external_layer(external_path, local_orthology)
                return {
                    "layer_key": layer_key,
                    "provider_name": provider_name,
                    "source_name": "local_reproducible_orthology",
                    "path": written_path,
                    "status": "local_orthology_file_materialized",
                    "confidence": float(config["online_sources"]["human_homologs_lookup"]["confidence_local_orthology"]),
                    "notes": ["api_not_requested_offline_mode", "local_orthology_file_used_before_uniprot_lookup"],
                    "provenance": "local orthology was materialized without UniProt lookup",
                }
            diamond_df, diamond_manifest = _load_diamond_human_homologs(workspace, config)
            if not diamond_df.empty:
                written_path = _write_external_layer(external_path, diamond_df)
                return {
                    "layer_key": layer_key,
                    "provider_name": provider_name,
                    "source_name": "diamond_human_sequence_alignment",
                    "path": written_path,
                    "status": str(diamond_manifest.get("status", "diamond_cached_tsv_materialized")),
                    "confidence": 0.86,
                    "notes": ["api_not_requested_offline_mode", *list(diamond_manifest.get("notes", []))],
                    "provenance": "DIAMOND sequence alignment materialized without UniProt name lookup",
                }
            if provider_name == "human_homology_diamond":
                unresolved = _build_unresolved_human_homologs(
                    workspace,
                    database="computed_diamond_human_homology_unresolved_v1",
                    lookup_status="diamond_unresolved",
                    query_strategy="diamond_blastp_sequence_alignment",
                    evidence_note="DIAMOND evidence unresolved; no human_homolog value was inferred.",
                )
                if not unresolved.empty:
                    written_path = _write_external_layer(external_path, unresolved)
                    return {
                        "layer_key": layer_key,
                        "provider_name": provider_name,
                        "source_name": "diamond_human_sequence_alignment",
                        "path": written_path,
                        "status": str(diamond_manifest.get("status", "diamond_unavailable")),
                        "confidence": 0.0,
                        "notes": list(diamond_manifest.get("notes", [])),
                    }
                return {
                    "layer_key": layer_key,
                    "provider_name": provider_name,
                    "source_name": "diamond_human_sequence_alignment",
                    "path": None,
                    "status": str(diamond_manifest.get("status", "diamond_unavailable")),
                    "confidence": 0.0,
                    "notes": list(diamond_manifest.get("notes", [])),
                }
            stub_df = _build_human_homologs_stub(workspace, config)
            written_path = _write_external_layer(external_path, stub_df)
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "configurable_stub_human_homologs_v1",
                "path": written_path,
                "status": "api_not_requested_offline_mode",
                "confidence": float(config["online_sources"]["human_homologs_lookup"]["confidence_stub_fallback"]),
                "notes": ["not_requested_offline_mode", f"online_source_mode={online_mode}"],
                "provenance": "stub fallback; no negative homology evidence inferred",
            }
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": provider_name,
            "path": None,
            "status": "api_not_requested_offline_mode",
            "confidence": 0.0,
            "notes": ["not_requested_offline_mode", f"online_source_mode={online_mode}"],
            "provenance": "external provider skipped before network because offline-safe mode is active",
        }

    if provider_name == "curated_online_examples" and layer_key == "literature_support":
        catalog_cfg = config["online_sources"].get("curated_therapeutic_catalogs", {})
        if external_path.exists():
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "curated_online_literature_catalog:data_external",
                "path": str(external_path),
                "status": "external_file_available",
                "confidence": float(catalog_cfg.get("confidence_literature_support_catalog", 0.92)),
            }
        catalog_path, catalog_df = _read_curated_therapeutic_catalog(
            workspace,
            config,
            "literature_support_catalog_dir",
            _catalog_key_candidates(context),
        )
        if catalog_path is None or catalog_df.empty:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "curated_literature_catalog_unavailable",
                "confidence": 0.0,
            }
        materialized = _build_curated_literature_support_from_catalog(workspace, catalog_df, catalog_path)
        if materialized.empty:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "curated_online_literature_catalog",
                "path": None,
                "status": "curated_literature_catalog_no_candidate_matches",
                "confidence": 0.0,
            }
        written_path = _write_external_layer(external_path, materialized)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "curated_online_literature_catalog",
            "path": written_path,
            "status": "curated_literature_catalog_materialized",
            "confidence": float(catalog_cfg.get("confidence_literature_support_catalog", 0.92)),
        }

    if provider_name == "curated_online_examples" and layer_key in {"essentiality", "virulence", "localization"}:
        catalog_cfg = config["online_sources"].get("curated_therapeutic_catalogs", {})
        if external_path.exists():
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": f"curated_online_{layer_key}_catalog:data_external",
                "path": str(external_path),
                "status": "external_file_available",
                "confidence": float(catalog_cfg.get("confidence_curated_layer_catalog", 0.90)),
            }
        catalog_path, catalog_df = _read_curated_therapeutic_catalog(
            workspace,
            config,
            f"{layer_key}_catalog_dir",
            _catalog_key_candidates(context),
        )
        if catalog_path is None or catalog_df.empty:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": f"curated_{layer_key}_catalog_unavailable",
                "confidence": 0.0,
            }
        materialized = _build_curated_layer_from_catalog(workspace, catalog_df, catalog_path)
        if materialized.empty:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": f"curated_online_{layer_key}_catalog",
                "path": None,
                "status": f"curated_{layer_key}_catalog_no_candidate_matches",
                "confidence": 0.0,
            }
        written_path = _write_external_layer(external_path, materialized)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": f"curated_online_{layer_key}_catalog",
            "path": written_path,
            "status": f"curated_{layer_key}_catalog_materialized",
            "confidence": float(catalog_cfg.get("confidence_curated_layer_catalog", 0.90)),
        }

    if provider_name == "uniprot_real" and layer_key == "localization":
        if not taxon_id:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "external_unavailable_missing_taxon_id",
                "confidence": 0.0,
            }
        try:
            result = fetch_uniprot_annotations(
                workspace=workspace,
                organism_name=organism_name,
                taxon_id=taxon_id,
                config=config,
                mode=online_mode,
            )
        except Exception as exc:  # noqa: BLE001 - provider failures degrade to unresolved evidence.
            return _unresolved_external_result(layer_key, provider_name, exc)
        localization = _build_localization_from_uniprot(result["annotations"], config)
        written_path = _write_external_layer(external_path, localization)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "uniprot_rest",
            "path": written_path,
            "status": str(result["manifest"].get("source_used", "uniprot_external")),
            "confidence": 0.90 if result["manifest"].get("api_success") else 0.80,
        }

    if provider_name == "string_real" and layer_key == "functional_network":
        if not taxon_id:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "external_unavailable_missing_taxon_id",
                "confidence": 0.0,
            }
        try:
            result = fetch_string_functional_network(
                workspace=workspace,
                organism_name=organism_name,
                taxon_id=taxon_id,
                config=config,
                mode=online_mode,
                replace_existing=True,
            )
        except Exception as exc:  # noqa: BLE001 - provider failures degrade to unresolved evidence.
            return _unresolved_external_result(layer_key, provider_name, exc)
        written_path = _write_external_layer(external_path, result["functional_network"])
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "string_db",
            "path": written_path,
            "status": str(result["manifest"].get("source_used", "string_external")),
            "confidence": 0.88 if result["manifest"].get("api_success") else 0.78,
        }

    if provider_name in {"uniprot_human_gene_lookup", "human_homology_diamond"} and layer_key == "human_homologs":
        local_orthology = _load_local_orthology_human_homologs(workspace, config)
        if not local_orthology.empty:
            written_path = _write_external_layer(external_path, local_orthology)
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "local_reproducible_orthology",
                "path": written_path,
                "status": "local_orthology_file_materialized",
                "confidence": float(config["online_sources"]["human_homologs_lookup"]["confidence_local_orthology"]),
                "notes": ["local_orthology_file_used_before_uniprot_lookup"],
            }
        diamond_df, diamond_manifest = _load_diamond_human_homologs(workspace, config)
        if not diamond_df.empty:
            written_path = _write_external_layer(external_path, diamond_df)
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "diamond_human_sequence_alignment",
                "path": written_path,
                "status": str(diamond_manifest.get("status", "diamond_cached_tsv_materialized")),
                "confidence": 0.86,
                "notes": list(diamond_manifest.get("notes", [])),
            }
        if provider_name == "human_homology_diamond":
            unresolved = _build_unresolved_human_homologs(
                workspace,
                database="computed_diamond_human_homology_unresolved_v1",
                lookup_status="diamond_unresolved",
                query_strategy="diamond_blastp_sequence_alignment",
                evidence_note="DIAMOND evidence unresolved; no human_homolog value was inferred.",
            )
            if not unresolved.empty:
                written_path = _write_external_layer(external_path, unresolved)
                return {
                    "layer_key": layer_key,
                    "provider_name": provider_name,
                    "source_name": "diamond_human_sequence_alignment",
                    "path": written_path,
                    "status": str(diamond_manifest.get("status", "diamond_unavailable")),
                    "confidence": 0.0,
                    "notes": list(diamond_manifest.get("notes", [])),
                }
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "diamond_human_sequence_alignment",
                "path": None,
                "status": str(diamond_manifest.get("status", "diamond_unavailable")),
                "confidence": 0.0,
                "notes": list(diamond_manifest.get("notes", [])),
            }
        stub_df = _build_human_homologs_stub(workspace, config)
        real_df, exact_matches, notes, api_success = _build_human_homologs_from_real_lookup(workspace, config)
        if not real_df.empty and (exact_matches > 0 or (api_success and not stub_df.empty)):
            merged = _merge_human_homologs_with_stub(real_df, stub_df)
            matched_rows = int(real_df.get("homology_lookup_status", pd.Series(dtype=str)).astype(str).eq("real_match").sum())
            written_path = _write_external_layer(external_path, merged)
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "uniprot_human_gene_lookup+configurable_stub",
                "path": written_path,
                "status": "api_real_partial_with_stub_backfill" if exact_matches > 0 or matched_rows > 0 else "api_real_inconclusive_with_stub_backfill",
                "confidence": float(config["online_sources"]["human_homologs_lookup"]["confidence_hybrid"]),
                "notes": notes,
            }
        if not real_df.empty and api_success:
            written_path = _write_external_layer(external_path, real_df)
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "uniprot_human_gene_lookup",
                "path": written_path,
                "status": "api_real_partial_gene_lookup",
                "confidence": float(config["online_sources"]["human_homologs_lookup"]["confidence_real_partial"]),
                "notes": notes,
            }
        stub_df = _build_human_homologs_stub(workspace, config)
        written_path = _write_external_layer(external_path, stub_df)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "configurable_stub_human_homologs_v1",
            "path": written_path,
            "status": "external_real_unavailable_fallback_stub",
            "confidence": float(config["online_sources"]["human_homologs_lookup"]["confidence_stub_fallback"]),
            "notes": notes,
        }

    if provider_name == "configurable_stub" and layer_key == "human_homologs":
        stub_df = _build_human_homologs_stub(workspace, config)
        written_path = _write_external_layer(external_path, stub_df)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "configurable_stub_human_homologs_v1",
            "path": written_path,
            "status": "external_configurable_stub",
            "confidence": 0.40,
        }

    if provider_name == "controlled_host_annotation_v1" and layer_key == "host_annotation":
        cfg = config["online_sources"]["host_annotation"]
        if not bool(cfg.get("enabled", True)):
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "controlled_provider_disabled",
                "confidence": 0.0,
            }
        layer = _build_controlled_host_annotation(workspace, config)
        if layer.empty:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "controlled_provider_no_homology_inputs",
                "confidence": 0.0,
            }
        written_path = _write_external_layer(external_path, layer)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": provider_name,
            "path": written_path,
            "status": "controlled_provider_materialized",
            "confidence": float(cfg["confidence_controlled"]),
        }

    if provider_name == "interpro_domain_overlap" and layer_key == "host_annotation":
        cfg = config["online_sources"]["interpro"]
        if not bool(cfg.get("enabled", True)):
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "interpro_provider_disabled",
                "confidence": 0.0,
            }
        try:
            result = fetch_interpro_host_annotation(
                workspace=workspace,
                organism_name=organism_name,
                taxon_id=taxon_id,
                config=config,
                mode=online_mode,
            )
            df = result["host_annotation_data"]
            manifest = result["manifest"]
        except (FileNotFoundError, ValueError) as exc:
            df = pd.DataFrame()
            manifest = {"source_used": "interpro_unavailable", "paired_domain_rows": 0, "notes": [str(exc)]}
        paired_rows = int(manifest.get("paired_domain_rows", 0) or 0)
        if not df.empty and paired_rows > 0:
            written_path = _write_external_layer(external_path, df)
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "interpro_api",
                "path": written_path,
                "status": str(manifest.get("source_used", "api_real")),
                "confidence": float(cfg["confidence_real"]),
            }
        fallback = _build_controlled_host_annotation(workspace, config)
        if fallback.empty:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "interpro_api",
                "path": None,
                "status": "interpro_unavailable_no_controlled_fallback",
                "confidence": 0.0,
                "notes": manifest.get("notes", []),
            }
        written_path = _write_external_layer(external_path, fallback)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "interpro_api+controlled_host_annotation_v1",
            "path": written_path,
            "status": "interpro_no_comparable_domains_fallback_controlled",
            "confidence": float(cfg["confidence_controlled_fallback"]),
            "notes": manifest.get("notes", []),
        }

    if provider_name in THERAPEUTIC_CONTEXT_PROVIDERS and layer_key in {
        "clinical_impact",
        "curated_disease_context",
        "therapy_site_context",
    }:
        catalog_cfg = config["online_sources"].get("curated_therapeutic_catalogs", {})
        if layer_key == "clinical_impact":
            catalog_path, catalog_df = _read_curated_therapeutic_catalog(
                workspace,
                config,
                "clinical_impact_catalog_dir",
                _catalog_key_candidates(context),
            )
            if catalog_path is not None and not catalog_df.empty:
                materialized = catalog_df.copy()
                materialized["clinical_impact_catalog_source"] = _display_catalog_path(catalog_path, workspace)
                if "database" not in materialized.columns:
                    materialized["database"] = "curated_clinical_impact_catalog_v1"
                written_path = _write_external_layer(external_path, materialized)
                return {
                    "layer_key": layer_key,
                    "provider_name": provider_name,
                    "source_name": "curated_clinical_impact_catalog",
                    "path": written_path,
                    "status": "curated_organism_catalog_materialized",
                    "confidence": float(catalog_cfg.get("confidence_clinical_impact_catalog", 0.86)),
                }
        if layer_key == "therapy_site_context":
            disease_keys = [
                catalog_cfg.get("default_disease_context", ""),
                catalog_cfg.get("default_infection_site", ""),
            ]
            catalog_path, catalog_df = _read_curated_therapeutic_catalog(
                workspace,
                config,
                "therapy_site_context_catalog_dir",
                _catalog_key_candidates(context, disease_keys),
            )
            if catalog_path is not None and not catalog_df.empty:
                materialized = catalog_df.copy()
                materialized["disease_site_context_source"] = _display_catalog_path(catalog_path, workspace)
                if "database" not in materialized.columns:
                    materialized["database"] = "curated_disease_site_context_v1"
                written_path = _write_external_layer(external_path, materialized)
                return {
                    "layer_key": layer_key,
                    "provider_name": provider_name,
                    "source_name": "curated_disease_site_context",
                    "path": written_path,
                    "status": "curated_disease_site_context_materialized",
                    "confidence": float(catalog_cfg.get("confidence_disease_site_context", 0.84)),
                }
        cfg_key = "therapeutic_context_v2" if provider_name == THERAPEUTIC_CONTEXT_PROVIDER_V2 else "therapeutic_context"
        cfg = config["online_sources"][cfg_key]
        if not bool(cfg.get("enabled", True)):
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "controlled_provider_disabled",
                "confidence": 0.0,
            }
        layer = (
            _build_controlled_therapeutic_layer_v2(layer_key, workspace, config)
            if provider_name == THERAPEUTIC_CONTEXT_PROVIDER_V2
            else _build_controlled_therapeutic_layer(layer_key, workspace, config)
        )
        if layer.empty:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "controlled_provider_no_candidate_inputs",
                "confidence": 0.0,
            }
        written_path = _write_external_layer(external_path, layer)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": provider_name,
            "path": written_path,
            "status": "controlled_provider_materialized",
            "confidence": float(cfg["confidence_controlled"]),
        }

    # === PROVEEDOR: deg_real -> essentiality ===
    if provider_name == "deg_real" and layer_key == "essentiality":
        if external_path.exists():
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "deg_database:data_external",
                "path": str(external_path),
                "status": "external_file_available",
                "confidence": float(config["layer_resolution"]["default_confidence_by_source"].get("external", 0.70)),
            }
        if not taxon_id:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "external_unavailable_missing_taxon_id",
                "confidence": 0.0,
            }
        try:
            result = fetch_deg_essentiality(
                workspace=workspace,
                organism_name=organism_name,
                taxon_id=taxon_id,
                config=config,
                mode=online_mode,
            )
        except Exception as exc:  # noqa: BLE001 - provider failures degrade to unresolved evidence.
            return _unresolved_external_result(layer_key, provider_name, exc)
        df = result["essentiality_data"]
        if df.empty:
            status = str(result.get("manifest", {}).get("retrieval_status") or result.get("manifest", {}).get("source_used") or "external_api_empty_response")
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "provider_not_found" if status == "not_found" else "deg_real",
                "path": None,
                "status": status,
                "confidence": 0.0,
            }
        written_path = _write_external_layer(external_path, df)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "deg_database",
            "path": written_path,
            "status": str(result["manifest"].get("source_used", "deg_external")),
            "confidence": 0.85 if result["manifest"].get("provider_success") else 0.0,
        }

    # === PROVEEDOR: vfdb_real -> virulence ===
    if provider_name == "vfdb_real" and layer_key == "virulence":
        if external_path.exists():
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "vfdb_database:data_external",
                "path": str(external_path),
                "status": "external_file_available",
                "confidence": float(config["layer_resolution"]["default_confidence_by_source"].get("external", 0.70)),
            }
        if not taxon_id:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "external_unavailable_missing_taxon_id",
                "confidence": 0.0,
            }
        try:
            result = fetch_vfdb_virulence(
                workspace=workspace,
                organism_name=organism_name,
                taxon_id=taxon_id,
                config=config,
                mode=online_mode,
            )
        except Exception as exc:  # noqa: BLE001 - provider failures degrade to unresolved evidence.
            return _unresolved_external_result(layer_key, provider_name, exc)
        df = result["virulence_data"]
        if df.empty:
            status = str(result.get("manifest", {}).get("retrieval_status") or result.get("manifest", {}).get("source_used") or "external_api_empty_response")
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "provider_not_found" if status == "not_found" else "vfdb_real",
                "path": None,
                "status": status,
                "confidence": 0.0,
            }
        written_path = _write_external_layer(external_path, df)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "vfdb_database",
            "path": written_path,
            "status": str(result["manifest"].get("source_used", "vfdb_external")),
            "confidence": 0.82 if result["manifest"].get("provider_success") else 0.0,
        }

    # === PROVEEDOR: bvbrc_real -> strain_conservation ===
    if provider_name == "bvbrc_real" and layer_key == "strain_conservation":
        if external_path.exists():
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "bvbrc_api:data_external",
                "path": str(external_path),
                "status": "external_file_available",
                "confidence": float(config["layer_resolution"]["default_confidence_by_source"].get("external", 0.70)),
            }
        if not taxon_id:
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": provider_name,
                "path": None,
                "status": "external_unavailable_missing_taxon_id",
                "confidence": 0.0,
            }
        try:
            result = fetch_bvbrc_strain_conservation(
                workspace=workspace,
                organism_name=organism_name,
                taxon_id=taxon_id,
                config=config,
                mode=online_mode,
            )
        except Exception as exc:  # noqa: BLE001 - provider failures degrade to unresolved evidence.
            return _unresolved_external_result(layer_key, provider_name, exc)
        df = result["strain_conservation_data"]
        if df.empty:
            status = str(result.get("manifest", {}).get("retrieval_status") or result.get("manifest", {}).get("source_used") or "external_api_empty_response")
            return {
                "layer_key": layer_key,
                "provider_name": provider_name,
                "source_name": "provider_not_found" if status == "not_found" else "bvbrc_real",
                "path": None,
                "status": status,
                "confidence": 0.0,
            }
        written_path = _write_external_layer(external_path, df)
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": "bvbrc_api",
            "path": written_path,
            "status": str(result["manifest"].get("source_used", "bvbrc_external")),
            "confidence": 0.80 if result["manifest"].get("provider_success") else 0.0,
        }

    if provider_name == "workspace_stub" and external_path.exists():
        return {
            "layer_key": layer_key,
            "provider_name": provider_name,
            "source_name": f"workspace_stub:{filename}",
            "path": str(external_path),
            "status": "external_stub_available",
        }
    return {
        "layer_key": layer_key,
        "provider_name": provider_name,
        "source_name": provider_name,
        "path": None,
        "status": "external_unavailable",
    }


def fetch_online_source(
    source: str,
    workspace: Path,
    organism_name: str,
    taxon_id: str | None,
    config: dict[str, Any],
    mode: str,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
    replace_existing: bool = False,
) -> dict[str, Any]:
    if source == "string":
        return fetch_string_functional_network(
            workspace=workspace,
            organism_name=organism_name,
            taxon_id=taxon_id,
            config=config,
            mode=mode,
            refresh_cache=refresh_cache,
            no_write_cache=no_write_cache,
            replace_existing=replace_existing,
        )
    if source == "uniprot":
        return fetch_uniprot_annotations(
            workspace=workspace,
            organism_name=organism_name,
            taxon_id=taxon_id,
            config=config,
            mode=mode,
            refresh_cache=refresh_cache,
            no_write_cache=no_write_cache,
        )
    raise ValueError(f"Fuente online no soportada: {source}")
