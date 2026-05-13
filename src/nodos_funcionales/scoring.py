from __future__ import annotations

import math
import warnings
from pathlib import Path

import pandas as pd

from .collateral_sensitivity import compute_collateral_sensitivity_features
from .contextual_essentiality import compute_contextual_essentiality_features
from .evidence_quality import compute_evidence_quality_features
from .evolutionary_escape import compute_evolutionary_escape_features
from .evolutionary_escape_risk import compute_evolutionary_escape_risk_features
from .functional_node_theory import compute_functional_node_theory_score
from .layer_registry import TARGET_LAYER_KEYS
from .phase3_evidence import apply_phase3_evidence_audit
from .redundancy_analysis import compute_redundancy_features
from .scoring_components import (
    assign_preferred_strategy,
    calculate_legacy_score,
    calculate_meta_priority_score,
    calculate_strategy_scores,
    human_similarity_score,
    validate_scoring_inputs,
)
from .therapeutic_role_stability import build_therapeutic_role_stability_audit, build_therapeutic_role_stability_report
from .virulence_layers import compute_virulence_layer_features


DEFAULT_META_PRIORITY_V3_CONFIG = {
    "weights": {
        "w_antibiotic": 0.20,
        "w_antivirulence": 0.15,
        "w_theory": 0.35,
        "w_evidence": 0.10,
        "w_combination": 0.10,
    },
    "penalties": {
        "p_escape": 0.18,
        "p_redundancy": 0.16,
        "p_biofilm": 0.08,
        "p_hgt": 0.08,
    },
    "role_thresholds": {
        "high_antibiotic": 0.70,
        "high_antivirulence": 0.70,
        "high_theory": 0.70,
        "high_combination": 0.65,
        "high_escape_risk": 0.65,
        "high_host_similarity_risk": 0.70,
        "minimum_evidence": 0.35,
        "dual_margin": 0.10,
    },
}

DEFAULT_PHASE3_RANKING_INCLUSION_CONFIG = {
    "min_real_layers_for_exploratory_inclusion": 1,
    "min_real_layers_for_real_candidate": 3,
    "max_demo_fraction_for_real_candidate": 0.50,
    "allow_mixed_evidence_candidates": True,
    "exclude_explicit_template_records": True,
    "exclude_demo_only_records": True,
}


PRIMARY_EVIDENCE_COLUMNS = [
    "essential",
    "virulence_score",
    "human_homolog",
    "localization",
]

OPTIONAL_SOURCE_COLUMNS = {
    "conservation_database": "conservation",
    "network_database": "network",
    "host_annotation_database": "host_annotation",
    "clinical_impact_database": "clinical_impact",
    "disease_context_database": "disease_context",
    "therapy_site_context_database": "therapy_site_context",
}

STRATEGY_SCORE_COLUMNS = [
    "antibiotic_target_score",
    "antivirulence_target_score",
    "functional_node_score",
]

THERAPEUTIC_PRIORITY_INPUT_COLUMNS = [
    "meta_priority_score",
    "host_safety_score",
    "host_damage_score",
    "infection_site_access_score",
    "infection_context_score",
]

INTERPRETATION_WARNING = (
    "Ranking = hipotesis terapeutica priorizada, no validacion experimental ni recomendacion clinica; "
    "score alto no implica farmaco disponible; esencialidad, virulencia, conectividad o bajo riesgo evolutivo "
    "no bastan por si solos; ausencia de evidencia no equivale a evidencia negativa."
)

HOST_RISK_AUDIT_COLUMNS = [
    "domain_overlap_score",
    "host_criticality_penalty",
    "host_safety_score",
    "host_annotation_database",
    "host_annotation_source_name",
    "host_annotation_retrieval_status",
    "interpro_rule",
    "interpro_missing_flags",
    "interpro_shared_entries",
    "interpro_bacterial_accession",
    "interpro_human_accession",
    "human_essentiality_score",
    "human_essentiality_status",
    "human_essentiality_lookup_status",
    "host_annotation_rule",
    "host_annotation_missing_flags",
]

HUMAN_HOMOLOGY_AUDIT_COLUMNS = [
    "homology_lookup_status",
    "homology_query_strategy",
    "homology_evidence_tier",
    "homology_confidence_score",
    "homology_missing_flags",
    "human_uniprot_accession",
    "human_uniprot_id",
    "human_homology_audit_summary",
]

THERAPY_SITE_CONTEXT_AUDIT_COLUMNS = [
    "infection_site",
    "access_evidence_type",
    "access_evidence_reference",
    "access_evidence_note",
    "disease_context",
    "syndrome",
    "disease_site_context_source",
    "therapy_site_context_audit_summary",
]

THERAPEUTIC_SEPARATION_COLUMNS = [
    "host_direct_damage_score",
    "virulence_associated_severity_score",
    "host_direct_damage_score_is_proxy",
    "virulence_associated_severity_score_is_proxy",
    "clinical_impact_catalog_source",
    "clinical_impact_evidence_type",
    "clinical_impact_evidence_reference",
    "clinical_impact_evidence_note",
]

THERAPEUTIC_CONTEXT_INPUT_COLUMNS = {
    "clinical_impact": [
        "host_damage_reduction_potential",
        "disease_severity_association",
        "clinical_impact_score",
        "host_damage_score",
    ],
    "curated_disease_context": ["infection_context_score"],
    "therapy_site_context": ["infection_site_access"],
}

THERAPEUTIC_CONTEXT_DATABASE_COLUMNS = {
    "clinical_impact": "clinical_impact_database",
    "curated_disease_context": "disease_context_database",
    "therapy_site_context": "therapy_site_context_database",
}

PHASE3_NUMERIC_DEFAULTS = {
    "contextual_essentiality_score": math.nan,
    "pleiotropy_score": math.nan,
    "functional_node_theory_score": math.nan,
    "mutational_tolerance_score": math.nan,
    "fitness_cost_score": math.nan,
    "compensation_difficulty_score": math.nan,
    "collateral_sensitivity_score": math.nan,
    "biofilm_escape_penalty": 0.0,
    "horizontal_transfer_penalty": 0.0,
    "evolutionary_escape_risk_score": math.nan,
    "evolutionary_space_constraint_score": math.nan,
    "evidence_quality_score": 0.0,
    "confidence_ceiling": 0.0,
}

PHASE3_TEXT_DEFAULTS = {
    "evidence_source_type": "not_assessed",
    "evidence_notes": "not_reported",
    "therapeutic_role_v3": "not_assessed",
    "recommended_combination_class": "not_assessed",
    "combination_rationale": "not_reported",
    "audit_flags": "phase3_not_enabled",
    "phase3_notes": "not_reported",
}


def _safe_series(df: pd.DataFrame, column: str, default: float = 0.5) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _status_from_binary(series: pd.Series, positive_value: int) -> pd.Series:
    return series.map(
        lambda value: "unknown"
        if pd.isna(value)
        else ("positive" if int(value) == positive_value else "negative")
    )


def _known_fraction(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    present = pd.DataFrame({column: df[column].notna() if column in df.columns else False for column in columns})
    return present.mean(axis=1).astype(float)


def _unique_source_count(source_database: str) -> int:
    if not isinstance(source_database, str) or not source_database.strip():
        return 0
    return len({item.strip() for item in source_database.split(";") if item.strip()})


def _clamp(series: pd.Series, lower: float = 0.0, upper: float = 1.0) -> pd.Series:
    return series.clip(lower=lower, upper=upper).fillna(lower)


def _infer_source_type(database_value: object, provenance_cfg: dict) -> str:
    if not isinstance(database_value, str) or not database_value.strip():
        return "unknown"
    database = database_value.strip().lower()
    exact_map = {str(key).lower(): str(value) for key, value in provenance_cfg["database_type_overrides"].items()}
    if database in exact_map:
        return exact_map[database]
    prefix_map = {str(key).lower(): str(value) for key, value in provenance_cfg["database_prefix_types"].items()}
    for prefix, source_type in prefix_map.items():
        if database.startswith(prefix):
            return source_type
    return "unknown"


def _source_quality(source_type: str, provenance_cfg: dict) -> float:
    quality_map = provenance_cfg["default_quality_by_type"]
    return float(quality_map.get(source_type, quality_map["unknown"]))


def _confidence_source_class(row: pd.Series) -> str:
    optional_types = {
        str(row.get(f"{label}_source_type", "unknown") or "unknown").strip().lower()
        for label in OPTIONAL_SOURCE_COLUMNS.values()
    }
    layer_source_names = " ".join(
        str(row.get(f"{layer}_source_name", "") or "").strip().lower()
        for layer in TARGET_LAYER_KEYS
    )
    layer_statuses = " ".join(
        str(row.get(f"{layer}_retrieval_status", "") or "").strip().lower()
        for layer in TARGET_LAYER_KEYS
    )
    if any(bool(row.get(f"{layer}_is_user_supplied", False)) for layer in TARGET_LAYER_KEYS):
        return "user"
    if optional_types & {"curated", "literature"} or "curated_" in layer_source_names or "curated_" in layer_statuses:
        return "curated"
    if optional_types & {"experimental"}:
        return "experimental"
    if any(name in layer_source_names for name in ["uniprot", "string_db", "deg_real", "vfdb_real", "bvbrc", "interpro_api"]):
        return "experimental"
    if "controlled" in layer_source_names or "controlled" in layer_statuses or "controlled" in optional_types:
        return "controlled"
    if any(bool(row.get(f"{layer}_is_proxy", False)) for layer in TARGET_LAYER_KEYS) or "proxy" in optional_types:
        return "proxy"
    if "computed" in optional_types:
        return "computed"
    return "unknown"


def _confidence_evidence_tier(source_class: str, provenance_cfg: dict) -> str:
    class_cfg = provenance_cfg.get("confidence_source_classes", {})
    return str(class_cfg.get(source_class, class_cfg.get("unknown", {})).get("tier", source_class))


def _confidence_class_quality(source_class: str, provenance_cfg: dict) -> float:
    class_cfg = provenance_cfg.get("confidence_source_classes", {})
    unknown = class_cfg.get("unknown", {"quality": provenance_cfg["default_quality_by_type"]["unknown"]})
    return float(class_cfg.get(source_class, unknown).get("quality", unknown["quality"]))


def _row_mean(df: pd.DataFrame, columns: list[str], default: float) -> pd.Series:
    if not columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    return values.mean(axis=1).fillna(default).astype(float)


def _defragment_frame(df: pd.DataFrame) -> pd.DataFrame:
    # Pandas can fragment a DataFrame after many column insertions. A copy keeps
    # the exact values but consolidates internal blocks before the next phase.
    return df.copy()


def _weighted_score(df: pd.DataFrame, weights: dict[str, float]) -> tuple[pd.Series, dict[str, pd.Series]]:
    contributions: dict[str, pd.Series] = {}
    total_weight = sum(abs(value) for value in weights.values()) or 1.0

    for feature_name, weight in weights.items():
        feature = pd.to_numeric(df.get(feature_name, 0.5), errors="coerce").fillna(0.5)
        contributions[feature_name] = feature * weight

    raw = sum(contributions.values()) / total_weight
    return _clamp(raw), contributions


def _driver_strings(df: pd.DataFrame, weights: dict[str, float]) -> tuple[pd.Series, pd.Series]:
    positive_parts = []
    negative_parts = []
    weight_norm = sum(abs(value) for value in weights.values()) or 1.0
    for row_index in df.index:
        weighted_values = []
        weighted_deficits = []
        for feature_name, weight in weights.items():
            feature_value = float(pd.to_numeric(pd.Series([df.at[row_index, feature_name]]), errors="coerce").fillna(0.5).iloc[0])
            positive_contribution = (feature_value * weight) / weight_norm
            deficit_contribution = ((1.0 - feature_value) * abs(weight)) / weight_norm
            weighted_values.append((feature_name, positive_contribution))
            weighted_deficits.append((feature_name, deficit_contribution))
        positive = sorted(weighted_values, key=lambda item: item[1], reverse=True)[:3]
        negative = sorted(weighted_deficits, key=lambda item: item[1], reverse=True)[:3]
        positive_parts.append("; ".join(f"{key}={value:.3f}" for key, value in positive) if positive else "none")
        negative_parts.append("; ".join(f"{key}={value:.3f}" for key, value in negative) if negative else "none")
    return pd.Series(positive_parts), pd.Series(negative_parts)


def _contribution_summary(row: pd.Series, contribution_columns: list[str]) -> str:
    parts = []
    for column in contribution_columns:
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").fillna(0.0).iloc[0]
        feature_name = column.removeprefix("therapeutic_priority_").removesuffix("_contribution")
        parts.append((feature_name, float(value)))
    parts = sorted(parts, key=lambda item: item[1], reverse=True)
    return "; ".join(f"{feature_name}={value:.3f}" for feature_name, value in parts) if parts else "none"


def _truthy_signal(value: object, threshold: float = 0.60) -> bool:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.notna(numeric):
        return float(numeric) >= threshold
    text = str(value or "").strip().lower()
    return text in {"true", "yes", "detected", "positive", "present", "high"}


def _derive_functional_node_types(row: pd.Series) -> str:
    node_types: list[str] = []
    essentiality = float(row.get("essentiality_support", 0.0) or 0.0)
    virulence = float(row.get("virulence_support", 0.0) or 0.0)
    functional = float(row.get("functional_node_score", 0.0) or 0.0)
    access = float(row.get("infection_site_access_score", 0.0) or 0.0)
    context = float(row.get("infection_context_score", 0.0) or 0.0)
    robustness = float(row.get("evolutionary_robustness_score", 0.0) or 0.0)
    selectivity = float(row.get("selectivity_score", row.get("host_safety_score", 0.0)) or 0.0)
    clinical = float(row.get("clinical_context_score", 0.0) or 0.0)

    localization = str(row.get("localization", "") or "").lower()
    gene_text = " ".join(
        str(row.get(column, "") or "").lower()
        for column in ["gene", "uniprot_protein_name", "virulence_factor", "functional_module"]
    )

    essential_flag = pd.to_numeric(pd.Series([row.get("essential")]), errors="coerce").fillna(0).iloc[0]
    if essentiality >= 0.70 or int(essential_flag) == 1:
        node_types.append("essential_node")
    if virulence >= 0.65 or _truthy_signal(row.get("virulence_factor"), threshold=0.50):
        node_types.append("virulence_node")
    if context >= 0.60 or any(token in gene_text for token in ["stress", "biofilm", "persistence", "hypoxia", "iron", "quorum"]):
        node_types.append("adaptation_persistence_node")
    if any(token in gene_text for token in ["regulator", "sigma", "response regulator", "sensor kinase", "transcriptional", "quorum"]):
        node_types.append("regulatory_node")
    if functional >= 0.60 or float(row.get("network_centrality", 0.0) or 0.0) >= 0.65 or float(row.get("pathway_bottleneck_score", 0.0) or 0.0) >= 0.65:
        node_types.append("functional_connectivity_node")
    if access >= 0.60 or localization in {"extracellular", "cell_wall", "outer_membrane"}:
        node_types.append("therapeutic_accessibility_node")
    if (
        float(row.get("collateral_sensitivity_score", 0.0) or 0.0) >= 0.60
        or _truthy_signal(row.get("resistance_association"), threshold=0.60)
        or float(row.get("resistance_emergence_risk", 0.0) or 0.0) >= 0.60
    ):
        node_types.append("resistance_or_susceptibility_node")
    if robustness >= 0.65 or float(row.get("reduced_evolutionary_space_score", 0.0) or 0.0) >= 0.65:
        node_types.append("evolutionarily_constrained_node")
    if context >= 0.60 or clinical >= 0.60:
        node_types.append("contextual_node")

    favorable_axes = sum(
        [
            functional >= 0.60,
            max(essentiality, virulence) >= 0.65,
            selectivity >= 0.65,
            access >= 0.55,
            robustness >= 0.60,
            clinical >= 0.55,
            float(row.get("evidence_confidence_score", 0.0) or 0.0) >= 0.55,
        ]
    )
    if favorable_axes >= 4:
        node_types.append("integrative_multilevel_node")

    return "; ".join(dict.fromkeys(node_types)) if node_types else "unclassified_functional_node"


def _dominant_provenance_status(row: pd.Series) -> str:
    source_class = str(row.get("confidence_source_class", "unknown") or "unknown").strip().lower()
    data_realism = str(row.get("data_realism_flag", "") or "").strip().lower()
    missing_flags = str(row.get("missing_evidence_flags", "") or "").strip().lower()
    if source_class == "user":
        return "user_supplied"
    if source_class in {"curated", "literature"}:
        return "curated_snapshot"
    if source_class in {"experimental", "computed"}:
        return "real_external_online"
    if source_class == "controlled":
        return "controlled_provider"
    if source_class == "proxy":
        return "inferred_proxy"
    if "demo" in data_realism:
        return "demo"
    if "missing" in missing_flags:
        return "missing_input"
    return "insufficient_evidence"


def _aggregate_cache_status(row: pd.Series) -> str:
    cached = [bool(row.get(f"{layer}_is_cached", False)) for layer in TARGET_LAYER_KEYS]
    if any(cached):
        return "cache_hit"
    if any(bool(row.get(f"{layer}_is_external", False)) for layer in TARGET_LAYER_KEYS):
        return "not_cached_or_not_reported"
    return "not_cached"


def _aggregate_retrieval_mode(row: pd.Series) -> str:
    statuses = {
        str(row.get(f"{layer}_retrieval_status", "") or "").strip().lower()
        for layer in TARGET_LAYER_KEYS
    }
    source_names = {
        str(row.get(f"{layer}_source_name", "") or "").strip().lower()
        for layer in TARGET_LAYER_KEYS
    }
    if any("user" in status or "user" in name for status in statuses for name in source_names):
        return "user_or_local_file"
    if any("cache" in status or "cache" in name for status in statuses for name in source_names):
        return "cache_first_or_cache_hit"
    if any("external" in status or "api" in status or "real" in name for status in statuses for name in source_names):
        return "online_optional_or_external"
    if any("proxy" in status or "controlled" in status or "controlled" in name for status in statuses for name in source_names):
        return "controlled_or_proxy"
    return "not_reported"


def _build_missing_flags(df: pd.DataFrame) -> pd.Series:
    flags = []
    for _, row in df.iterrows():
        row_flags = []
        for column in PRIMARY_EVIDENCE_COLUMNS:
            value = row.get(column)
            if pd.isna(value) or str(value).strip().lower() in {"", "unknown", "nan"}:
                row_flags.append(f"missing_{column}")
        for placeholder in [
            "network_centrality",
            "pathway_bottleneck_score",
            "redundancy_penalty",
            "functional_dependency_score",
            "core_genome_presence",
            "strain_coverage_score",
            "allelic_conservation",
            "variant_burden",
        ]:
            if bool(row.get(f"{placeholder}_is_placeholder", False)):
                row_flags.append(f"placeholder_{placeholder}")
        flags.append("; ".join(row_flags) if row_flags else "none")
    return pd.Series(flags)


def _row_source_summary(row: pd.Series) -> str:
    parts = []
    for database_column, label in OPTIONAL_SOURCE_COLUMNS.items():
        source_type = row.get(f"{label}_source_type", "unknown")
        source_quality = row.get(f"{label}_source_quality", 0.5)
        database_value = row.get(database_column, "")
        if isinstance(database_value, str) and database_value.strip():
            parts.append(f"{label}={source_type}({float(source_quality):.2f})")
    return "; ".join(parts) if parts else "none"


def _host_risk_audit_summary(row: pd.Series) -> str:
    source_name = str(row.get("host_annotation_source_name", "missing") or "missing")
    retrieval_status = str(row.get("host_annotation_retrieval_status", "missing") or "missing")
    rule = row.get("interpro_rule")
    if pd.isna(rule) or not str(rule).strip():
        rule = row.get("host_annotation_rule", "no_host_annotation_rule")
    missing_flags = row.get("interpro_missing_flags")
    if pd.isna(missing_flags) or not str(missing_flags).strip():
        missing_flags = row.get("host_annotation_missing_flags", "not_reported")
    essentiality_status = row.get("human_essentiality_status", "not_reported")
    shared_entries = row.get("interpro_shared_entries", "")

    return (
        f"host_source={source_name}; "
        f"status={retrieval_status}; "
        f"rule={rule}; "
        f"domain_overlap={float(row.get('domain_overlap_score', 0.0)):.3f}; "
        f"host_criticality={float(row.get('host_criticality_penalty', 0.0)):.3f}; "
        f"human_essentiality={essentiality_status}; "
        f"shared_interpro={shared_entries if str(shared_entries).strip() else 'none'}; "
        f"missing={missing_flags}"
    )


def _human_homology_audit_summary(row: pd.Series) -> str:
    return (
        f"status={row.get('homology_lookup_status', 'not_reported')}; "
        f"strategy={row.get('homology_query_strategy', 'not_reported')}; "
        f"tier={row.get('homology_evidence_tier', 'not_reported')}; "
        f"confidence={float(row.get('homology_confidence_score', 0.0)):.2f}; "
        f"human_uniprot={row.get('human_uniprot_accession', '') or 'none'}; "
        f"missing={row.get('homology_missing_flags', 'not_reported')}"
    )


def _infer_legacy_homology_audit(row: pd.Series) -> tuple[str, float, str]:
    human_homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
    human_gene = str(row.get("human_gene", "") or "").strip()
    evalue = pd.to_numeric(pd.Series([row.get("evalue")]), errors="coerce").iloc[0]
    missing_flags = []
    if pd.isna(human_homolog):
        missing_flags.append("missing_human_homolog")
    if not human_gene or human_gene.lower() in {"none", "nan", "unknown"}:
        missing_flags.append("missing_human_gene")
    if pd.isna(evalue):
        missing_flags.append("missing_alignment_evalue")
    if pd.notna(human_homolog):
        return "legacy_or_user_supplied_unclassified", 0.50, "; ".join(missing_flags) if missing_flags else "none"
    return "unclassified_missing_homology", 0.20, "; ".join(missing_flags) if missing_flags else "none"


def _therapy_site_context_audit_summary(row: pd.Series) -> str:
    return (
        f"site={row.get('infection_site', 'not_reported')}; "
        f"evidence_type={row.get('access_evidence_type', 'not_reported')}; "
        f"reference={row.get('access_evidence_reference', 'not_reported')}; "
        f"source={row.get('therapy_site_context_source_name', 'not_reported')}; "
        f"status={row.get('therapy_site_context_retrieval_status', 'not_reported')}"
    )


def _use_empirical_or_proxy(
    df: pd.DataFrame,
    column: str,
    proxy_values: pd.Series,
    proxy_flag_column: str,
) -> None:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        empirical_mask = df[column].notna()
        df[column] = df[column].fillna(proxy_values)
        df[proxy_flag_column] = ~empirical_mask
    else:
        df[column] = proxy_values
        df[proxy_flag_column] = True


def _therapeutic_missingness(row: pd.Series, thresholds: dict[str, float]) -> str:
    flags: list[str] = []
    if bool(row.get("host_damage_score_is_proxy", False)):
        flags.append("proxy_host_damage_score")
    if bool(row.get("infection_site_access_score_is_proxy", False)):
        flags.append("proxy_infection_site_access_score")
    if bool(row.get("infection_context_score_is_proxy", False)):
        flags.append("proxy_infection_context_score")
    if float(row.get("evidence_confidence_score", 0.0)) < float(thresholds["minimum_confidence"]):
        flags.append("low_evidence_confidence")
    if float(row.get("evidence_coverage_score", 0.0)) < float(thresholds["minimum_coverage"]):
        flags.append("low_evidence_coverage")
    return "; ".join(flags) if flags else "none"


def _classify_therapeutic_role(row: pd.Series, thresholds: dict[str, float]) -> tuple[str, str]:
    host_safety = float(row.get("host_safety_score", 0.0))
    priority = float(row.get("therapeutic_priority_score", 0.0))
    evidence_confidence = float(row.get("evidence_confidence_score", 0.0))
    evidence_coverage = float(row.get("evidence_coverage_score", 0.0))
    essentiality = float(row.get("essentiality_support", 0.0))
    virulence = float(row.get("virulence_support", 0.0))
    access = float(row.get("infection_site_access_score", 0.0))
    context = float(row.get("infection_context_score", 0.0))
    damage = float(row.get("host_damage_score", 0.0))
    antibiotic = float(row.get("antibiotic_target_score", 0.0))
    antivirulence = float(row.get("antivirulence_target_score", 0.0))
    functional = float(row.get("functional_node_score", 0.0))
    margin = float(row.get("strategy_margin_score", 1.0))

    if evidence_confidence < float(thresholds["minimum_confidence"]):
        return "low_priority_candidate", "insufficient_evidence_confidence"
    if evidence_coverage < float(thresholds["minimum_coverage"]):
        return "low_priority_candidate", "insufficient_evidence_coverage"
    if host_safety < float(thresholds["host_safety_floor"]):
        return "low_priority_candidate", "host_risk_too_high"

    antibiotic_flag = (
        essentiality >= float(thresholds["high_essentiality"])
        and access >= float(thresholds["good_access"])
        and host_safety >= float(thresholds["low_host_risk"])
        and antibiotic >= float(thresholds["mixed_strategy_min_score"])
    )
    antivirulence_flag = (
        virulence >= float(thresholds["high_virulence"])
        and access >= float(thresholds["acceptable_access"])
        and damage >= float(thresholds["high_damage"])
        and host_safety >= float(thresholds["low_host_risk"])
        and antivirulence >= float(thresholds["mixed_strategy_min_score"])
    )
    sensitizer_flag = (
        functional >= float(thresholds["strong_functional"])
        and context >= float(thresholds["high_context"])
        and essentiality < float(thresholds["high_essentiality"])
        and host_safety >= float(thresholds["host_safety_floor"])
    )
    active_roles = [flag for flag in [antibiotic_flag, antivirulence_flag, sensitizer_flag] if flag]
    if len(active_roles) >= 2:
        return "mixed_strategy_candidate", "multiple_strategies_supported"
    if antibiotic_flag:
        return "bactericidal_candidate", "essentiality_access_and_host_safety_supported"
    if antivirulence_flag:
        return "antivirulence_candidate", "virulence_damage_and_access_supported"
    if sensitizer_flag:
        return "sensitizer_candidate", "functional_context_supported_without_strong_lethality"
    if (
        essentiality >= float(thresholds["high_essentiality"])
        and antibiotic >= float(thresholds["mixed_strategy_min_score"])
        and host_safety >= float(thresholds["low_host_risk"])
        and priority >= float(thresholds["strong_bactericidal_priority"])
        and access >= float(thresholds["critical_access_floor"])
    ):
        return "bactericidal_candidate", "strong_bactericidal_signal_with_limited_access"
    if (
        margin <= float(thresholds["mixed_margin_max"])
        and access >= float(thresholds["acceptable_access"])
        and context >= float(thresholds["high_context"])
        and sum(
            score >= float(thresholds["mixed_strategy_min_score"])
            for score in [antibiotic, antivirulence, functional]
        ) >= 2
    ):
        return "mixed_strategy_candidate", "multiple_strategies_supported"
    if access < float(thresholds["acceptable_access"]):
        return "low_priority_candidate", "poor_infection_site_access"
    if context < float(thresholds["high_context"]):
        return "low_priority_candidate", "weak_infection_context"
    if priority < float(thresholds["minimum_priority"]):
        return "low_priority_candidate", "therapeutic_priority_below_threshold"
    return "low_priority_candidate", "no_therapeutic_rule_reached"


def _controlled_layer_mask(features: pd.DataFrame, layer_key: str) -> pd.Series:
    source_name = features.get(f"{layer_key}_source_name", pd.Series([""] * len(features), index=features.index)).fillna("").astype(str).str.lower()
    status = features.get(f"{layer_key}_retrieval_status", pd.Series([""] * len(features), index=features.index)).fillna("").astype(str).str.lower()
    database_column = {
        "clinical_impact": "clinical_impact_database",
        "curated_disease_context": "disease_context_database",
        "therapy_site_context": "therapy_site_context_database",
    }.get(layer_key, "")
    if database_column and database_column in features.columns:
        database = features[database_column].fillna("").astype(str).str.lower()
    else:
        database = pd.Series([""] * len(features), index=features.index)
    return source_name.str.contains("controlled") | status.str.contains("controlled") | database.str.contains("controlled")


def _therapeutic_layer_input_status(features: pd.DataFrame, layer_key: str) -> pd.Series:
    input_columns = THERAPEUTIC_CONTEXT_INPUT_COLUMNS[layer_key]
    present_columns = [column for column in input_columns if column in features.columns]
    database_column = THERAPEUTIC_CONTEXT_DATABASE_COLUMNS[layer_key]
    source_type = features.get(
        f"{layer_key}_source_type",
        pd.Series(["missing"] * len(features), index=features.index),
    ).fillna("missing").astype(str)
    retrieval_status = features.get(
        f"{layer_key}_retrieval_status",
        pd.Series(["missing"] * len(features), index=features.index),
    ).fillna("missing").astype(str)
    is_proxy = features.get(
        f"{layer_key}_is_proxy",
        pd.Series([False] * len(features), index=features.index),
    ).fillna(False).astype(bool)

    if present_columns:
        has_values = pd.DataFrame(
            {
                column: pd.to_numeric(features[column], errors="coerce").notna()
                for column in present_columns
            }
        ).any(axis=1)
    else:
        has_values = pd.Series([False] * len(features), index=features.index)

    if database_column in features.columns:
        has_database = features[database_column].fillna("").astype(str).str.strip().ne("")
    else:
        has_database = pd.Series([False] * len(features), index=features.index)

    statuses = []
    for idx in features.index:
        if bool(has_values.loc[idx]):
            statuses.append("active_input")
        elif bool(is_proxy.loc[idx]):
            statuses.append("proxy_default_no_input_table")
        elif bool(has_database.loc[idx]):
            statuses.append("metadata_without_score_values")
        elif retrieval_status.loc[idx].startswith("resolved_from_") and source_type.loc[idx] not in {"missing", "proxy"}:
            statuses.append("resolved_empty_or_not_normalized")
        else:
            statuses.append("missing_or_inactive")
    return pd.Series(statuses, index=features.index)


def _controlled_dependency_flags(row: pd.Series) -> str:
    flags = []
    for layer_key in ["clinical_impact", "curated_disease_context", "therapy_site_context"]:
        if bool(row.get(f"{layer_key}_controlled_dependency", False)):
            flags.append(layer_key)
    return "; ".join(flags) if flags else "none"


def _therapeutic_boundary_margin(row: pd.Series, thresholds: dict[str, float]) -> float:
    checked_pairs = [
        ("evidence_confidence_score", "minimum_confidence"),
        ("evidence_coverage_score", "minimum_coverage"),
        ("host_safety_score", "host_safety_floor"),
        ("host_safety_score", "low_host_risk"),
        ("essentiality_support", "high_essentiality"),
        ("virulence_support", "high_virulence"),
        ("infection_site_access_score", "critical_access_floor"),
        ("infection_site_access_score", "acceptable_access"),
        ("infection_site_access_score", "good_access"),
        ("infection_context_score", "high_context"),
        ("host_damage_score", "high_damage"),
        ("functional_node_score", "strong_functional"),
        ("antibiotic_target_score", "mixed_strategy_min_score"),
        ("antivirulence_target_score", "mixed_strategy_min_score"),
        ("therapeutic_priority_score", "minimum_priority"),
        ("therapeutic_priority_score", "strong_bactericidal_priority"),
    ]
    margins = []
    for feature_name, threshold_name in checked_pairs:
        feature = pd.to_numeric(pd.Series([row.get(feature_name)]), errors="coerce").iloc[0]
        if pd.isna(feature):
            continue
        margins.append(abs(float(feature) - float(thresholds[threshold_name])))
    return round(min(margins), 4) if margins else 0.0


def _therapeutic_boundary_label(margin: float) -> str:
    if margin <= 0.05:
        return "near_rule_boundary"
    if margin <= 0.15:
        return "moderate_rule_margin"
    return "far_from_rule_boundary"


def _therapeutic_stability_explanation(row: pd.Series) -> str:
    if row.get("therapeutic_role_stability") == "changed":
        return "role_changed_after_removing_controlled_context"
    if str(row.get("controlled_dependency_flags", "none")) == "none":
        inactive_statuses = {
            str(row.get("clinical_impact_input_status", "missing_or_inactive")),
            str(row.get("curated_disease_context_input_status", "missing_or_inactive")),
            str(row.get("therapy_site_context_input_status", "missing_or_inactive")),
        }
        if inactive_statuses & {"resolved_empty_or_not_normalized", "missing_or_inactive", "proxy_default_no_input_table"}:
            return "stable_without_active_controlled_context"

    max_feature_delta = float(row.get("controlled_context_max_feature_delta", 0.0))
    priority_delta = abs(float(row.get("therapeutic_priority_controlled_delta", 0.0)))
    boundary_label = str(row.get("therapeutic_rule_boundary_proximity", "unknown"))

    if max_feature_delta <= 0.02 and priority_delta <= 0.02:
        return "stable_because_controlled_values_match_local_proxies"
    if boundary_label == "far_from_rule_boundary":
        return "stable_because_role_rule_far_from_thresholds"
    if max_feature_delta >= 0.10 or priority_delta >= 0.05:
        return "stable_but_scores_sensitive_review"
    return "stable_with_moderate_score_shift"


def _initialize_phase3_columns(features: pd.DataFrame) -> None:
    for column, default in PHASE3_NUMERIC_DEFAULTS.items():
        if column in features.columns:
            features[column] = pd.to_numeric(features[column], errors="coerce")
            if not pd.isna(default):
                features[column] = features[column].fillna(float(default))
            features[column] = features[column].clip(lower=0.0, upper=1.0)
        else:
            if pd.isna(default):
                features[column] = pd.Series([math.nan] * len(features), index=features.index, dtype=float)
            else:
                features[column] = float(default)

    if "conservation_score" not in features.columns:
        features["conservation_score"] = pd.Series([math.nan] * len(features), index=features.index, dtype=float)
    if "redundancy_penalty" not in features.columns:
        features["redundancy_penalty"] = 0.0

    for column, default in PHASE3_TEXT_DEFAULTS.items():
        if column not in features.columns:
            features[column] = default
        else:
            features[column] = features[column].fillna(default)


def build_features_and_scores(base_dir: Path, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    processed_dir = base_dir / "data_processed"
    integrated = pd.read_csv(processed_dir / "integrated_nodes.csv")
    features = integrated.copy()
    validate_scoring_inputs(features)

    threshold = float(config["thresholds"]["evalue_significance"])
    neutral = float(config["imputation"]["neutral_unknown_score"])
    localization_cfg = config["localization"]
    placeholder_defaults = config["imputation"]["placeholder_defaults"]
    provenance_cfg = config["provenance"]
    therapeutic_cfg = config["therapeutic_phase1"]

    features["essentiality_evidence_state"] = _status_from_binary(_safe_series(features, "essential"), 1)
    features["virulence_evidence_state"] = features.get("virulence_factor", pd.Series([pd.NA] * len(features))).map(
        lambda value: "unknown" if pd.isna(value) else ("positive" if int(value) == 1 else "negative")
    )
    features["homology_evidence_state"] = _status_from_binary(_safe_series(features, "human_homolog"), 0)
    features["localization_evidence_state"] = features.get("localization", pd.Series(["unknown"] * len(features))).map(
        lambda value: "unknown" if pd.isna(value) or str(value).strip().lower() in {"", "unknown", "nan"} else "positive"
    )

    features["essentiality_confidence"] = (
        0.5 * features["essential"].notna().astype(float)
        + 0.25 * features.get("evidence", pd.Series([""] * len(features))).fillna("").astype(str).ne("").astype(float)
        + 0.25 * features.get("essentiality_database", pd.Series([""] * len(features))).fillna("").astype(str).ne("").astype(float)
    )
    features["virulence_confidence"] = (
        0.55 * features["virulence_score"].notna().astype(float)
        + 0.20 * features.get("virulence_factor", pd.Series([pd.NA] * len(features))).notna().astype(float)
        + 0.25 * features.get("virulence_database", pd.Series([""] * len(features))).fillna("").astype(str).ne("").astype(float)
    )
    features["homology_confidence"] = (
        0.45 * features["human_homolog"].notna().astype(float)
        + 0.35 * features["evalue"].notna().astype(float)
        + 0.20 * features.get("homology_database", pd.Series([""] * len(features))).fillna("").astype(str).ne("").astype(float)
    )
    if "homology_confidence_score" in features.columns:
        features["homology_confidence_score"] = pd.to_numeric(features["homology_confidence_score"], errors="coerce").fillna(0.0)
    else:
        inferred_homology_audit = features.apply(_infer_legacy_homology_audit, axis=1)
        features["homology_evidence_tier"] = inferred_homology_audit.map(lambda item: item[0])
        features["homology_confidence_score"] = inferred_homology_audit.map(lambda item: item[1])
        features["homology_missing_flags"] = inferred_homology_audit.map(lambda item: item[2])
    for column, default in [
        ("homology_lookup_status", "not_reported"),
        ("homology_query_strategy", "not_reported"),
        ("homology_evidence_tier", "legacy_or_user_supplied_unclassified"),
        ("homology_missing_flags", "not_reported"),
        ("human_uniprot_accession", "none"),
        ("human_uniprot_id", "none"),
    ]:
        if column not in features.columns:
            features[column] = default
        else:
            features[column] = features[column].fillna(default)
    features["human_homology_audit_summary"] = features.apply(_human_homology_audit_summary, axis=1)
    features["localization_confidence"] = (
        0.70 * features["localization"].notna().astype(float)
        + 0.30 * features.get("localization_database", pd.Series([""] * len(features))).fillna("").astype(str).ne("").astype(float)
    )
    features["multi_source_support"] = features.get("source_database", pd.Series([""] * len(features))).map(_unique_source_count).astype(float)
    features["multi_source_support"] = _clamp(features["multi_source_support"] / 4.0)
    features["evidence_coverage_score"] = _known_fraction(features, PRIMARY_EVIDENCE_COLUMNS)
    base_confidence_score = _clamp(
        0.25 * features["essentiality_confidence"]
        + 0.25 * features["virulence_confidence"]
        + 0.25 * features["homology_confidence"]
        + 0.15 * features["localization_confidence"]
        + 0.10 * features["multi_source_support"]
    )
    optional_quality_columns: list[str] = []
    optional_presence_columns: list[str] = []
    for database_column, label in OPTIONAL_SOURCE_COLUMNS.items():
        if database_column in features.columns:
            features[f"{label}_source_type"] = features[database_column].map(lambda value: _infer_source_type(value, provenance_cfg))
            features[f"{label}_source_quality"] = features[f"{label}_source_type"].map(
                lambda source_type: _source_quality(source_type, provenance_cfg)
            )
            optional_quality_columns.append(f"{label}_source_quality")
            optional_presence_columns.append(database_column)
        else:
            features[f"{label}_source_type"] = "unknown"
            features[f"{label}_source_quality"] = float(provenance_cfg["default_quality_by_type"]["unknown"])
    if optional_presence_columns:
        features["optional_data_source_count"] = pd.DataFrame(
            {
                column: features[column].fillna("").astype(str).str.strip().ne("")
                for column in optional_presence_columns
            }
        ).sum(axis=1).astype(int)
    else:
        features["optional_data_source_count"] = pd.Series([0] * len(features), index=features.index, dtype=int)
    features["optional_data_quality_score"] = _row_mean(features, optional_quality_columns, neutral)
    confidence_influence = float(provenance_cfg["confidence_influence"])
    features["confidence_source_class"] = features.apply(_confidence_source_class, axis=1)
    features["confidence_evidence_tier"] = features["confidence_source_class"].map(
        lambda source_class: _confidence_evidence_tier(source_class, provenance_cfg)
    )
    features["confidence_source_quality_score"] = features["confidence_source_class"].map(
        lambda source_class: _confidence_class_quality(source_class, provenance_cfg)
    )
    controlled_or_proxy_mask = features["confidence_source_class"].isin(["controlled", "proxy"])
    if controlled_or_proxy_mask.any():
        features.loc[controlled_or_proxy_mask, "optional_data_quality_score"] = features.loc[
            controlled_or_proxy_mask,
            "optional_data_quality_score",
        ].clip(upper=features.loc[controlled_or_proxy_mask, "confidence_source_quality_score"])
    features["evidence_confidence_score"] = _clamp(
        (1.0 - confidence_influence) * base_confidence_score
        + confidence_influence * features["optional_data_quality_score"]
    )
    features["optional_data_source_summary"] = features.apply(_row_source_summary, axis=1)
    features["data_realism_flag"] = features["optional_data_quality_score"].map(
        lambda value: "demo_only" if value < 0.60 else ("mixed_or_computed" if value < 0.85 else "curated_or_experimental")
    )
    for layer_key in THERAPEUTIC_CONTEXT_INPUT_COLUMNS:
        features[f"{layer_key}_input_status"] = _therapeutic_layer_input_status(features, layer_key)
    features["therapeutic_context_input_summary"] = features.apply(
        lambda row: (
            f"clinical_impact={row['clinical_impact_input_status']}; "
            f"curated_disease_context={row['curated_disease_context_input_status']}; "
            f"therapy_site_context={row['therapy_site_context_input_status']}"
        ),
        axis=1,
    )
    features = _defragment_frame(features)

    features["human_similarity_score"] = features.apply(lambda row: human_similarity_score(row, neutral), axis=1)
    if "domain_overlap_score" in features.columns:
        features["domain_overlap_score"] = pd.to_numeric(features["domain_overlap_score"], errors="coerce")
        features["domain_overlap_score_is_empirical"] = features["domain_overlap_score"].notna()
        features["domain_overlap_score"] = features["domain_overlap_score"].fillna(
            _clamp(0.7 * features["human_similarity_score"] + 0.3 * features["human_homolog"].fillna(neutral).astype(float))
        )
    else:
        features["domain_overlap_score"] = _clamp(
            0.7 * features["human_similarity_score"] + 0.3 * features["human_homolog"].fillna(neutral).astype(float)
        )
        features["domain_overlap_score_is_empirical"] = False

    features["off_target_risk_score"] = _clamp(
        0.65 * features["human_similarity_score"] + 0.35 * features["domain_overlap_score"]
    )
    if "host_criticality_penalty" in features.columns:
        features["host_criticality_penalty"] = pd.to_numeric(features["host_criticality_penalty"], errors="coerce")
        features["host_criticality_penalty_is_empirical"] = features["host_criticality_penalty"].notna()
        features["host_criticality_penalty"] = features["host_criticality_penalty"].fillna(
            _clamp(0.75 * features["human_similarity_score"] + 0.25 * features["human_homolog"].fillna(neutral).astype(float))
        )
    else:
        features["host_criticality_penalty"] = _clamp(
            0.75 * features["human_similarity_score"] + 0.25 * features["human_homolog"].fillna(neutral).astype(float)
        )
        features["host_criticality_penalty_is_empirical"] = False

    features["host_safety_score"] = _clamp(
        1.0 - (0.55 * features["off_target_risk_score"] + 0.45 * features["host_criticality_penalty"])
    )
    features["host_risk_audit_summary"] = features.apply(_host_risk_audit_summary, axis=1)

    localization = features.get("localization", pd.Series(["unknown"] * len(features))).fillna("unknown").astype(str).str.lower()
    for new_column, mapping_name in [
        ("physical_accessibility", "physical_accessibility"),
        ("small_molecule_feasibility", "small_molecule_feasibility"),
        ("antibody_feasibility", "antibody_feasibility"),
        ("membrane_crossing_penalty", "membrane_crossing_penalty"),
    ]:
        mapping = localization_cfg[mapping_name]
        features[new_column] = localization.map(lambda value: float(mapping.get(value, mapping.get("unknown", neutral))))
    infection_site_access_proxy = localization.map(
        lambda value: float(localization_cfg["infection_site_access"].get(value, localization_cfg["infection_site_access"].get("unknown", neutral)))
    )
    _use_empirical_or_proxy(features, "infection_site_access", infection_site_access_proxy, "infection_site_access_is_proxy")

    placeholder_columns = [
        "network_centrality",
        "pathway_bottleneck_score",
        "redundancy_penalty",
        "functional_dependency_score",
        "core_genome_presence",
        "strain_coverage_score",
        "allelic_conservation",
        "variant_burden",
    ]
    for column in placeholder_columns:
        if column in features.columns:
            features[column] = pd.to_numeric(features[column], errors="coerce")
            empirical_mask = features[column].notna()
            features[column] = features[column].fillna(float(placeholder_defaults[column]))
            features[f"{column}_is_placeholder"] = ~empirical_mask
        else:
            features[column] = float(placeholder_defaults[column])
            features[f"{column}_is_placeholder"] = True

    features["essentiality_support"] = features["essential"].map(lambda value: neutral if pd.isna(value) else float(value))
    features["virulence_support"] = features["virulence_score"].map(lambda value: neutral if pd.isna(value) else float(value))
    virulence_factor_numeric = pd.to_numeric(features.get("virulence_factor", 0), errors="coerce").fillna(0.0)
    host_damage_reduction_proxy = _clamp(
        0.55 * features["virulence_support"]
        + 0.25 * virulence_factor_numeric
        + 0.20 * features["physical_accessibility"]
    )
    _use_empirical_or_proxy(
        features,
        "host_damage_reduction_potential",
        host_damage_reduction_proxy,
        "host_damage_reduction_potential_is_proxy",
    )
    disease_severity_proxy = _clamp(
        0.70 * features["virulence_support"]
        + 0.30 * virulence_factor_numeric
    )
    _use_empirical_or_proxy(
        features,
        "disease_severity_association",
        disease_severity_proxy,
        "disease_severity_association_is_proxy",
    )
    clinical_impact_proxy = _clamp(
        0.50 * features["disease_severity_association"]
        + 0.30 * features["host_damage_reduction_potential"]
        + 0.20 * features["infection_site_access"]
    )
    _use_empirical_or_proxy(features, "clinical_impact_score", clinical_impact_proxy, "clinical_impact_score_is_proxy")
    host_damage_proxy = _clamp(
        0.50 * features["host_damage_reduction_potential"]
        + 0.30 * features["disease_severity_association"]
        + 0.20 * features["virulence_support"]
    )
    _use_empirical_or_proxy(features, "host_damage_score", host_damage_proxy, "host_damage_score_is_proxy")
    _use_empirical_or_proxy(
        features,
        "host_direct_damage_score",
        _clamp(features["host_damage_score"]),
        "host_direct_damage_score_is_proxy",
    )
    _use_empirical_or_proxy(
        features,
        "virulence_associated_severity_score",
        _clamp(features["disease_severity_association"]),
        "virulence_associated_severity_score_is_proxy",
    )
    for column in [
        "clinical_impact_catalog_source",
        "clinical_impact_evidence_type",
        "clinical_impact_evidence_reference",
        "clinical_impact_evidence_note",
    ]:
        if column not in features.columns:
            features[column] = "not_reported"
        else:
            features[column] = features[column].fillna("not_reported")
    infection_access_proxy = _clamp(features["infection_site_access"])
    _use_empirical_or_proxy(
        features,
        "infection_site_access_score",
        infection_access_proxy,
        "infection_site_access_score_is_proxy",
    )
    if "infection_site_access_is_proxy" in features.columns:
        features["infection_site_access_score_is_proxy"] = features["infection_site_access_is_proxy"]
    for column in [
        "infection_site",
        "access_evidence_type",
        "access_evidence_reference",
        "access_evidence_note",
        "disease_context",
        "syndrome",
        "disease_site_context_source",
    ]:
        if column not in features.columns:
            features[column] = "not_reported"
        else:
            features[column] = features[column].fillna("not_reported")
    features["therapy_site_context_audit_summary"] = features.apply(_therapy_site_context_audit_summary, axis=1)
    features = _defragment_frame(features)

    features["conservation_score"] = _clamp(
        0.40 * features["core_genome_presence"]
        + 0.40 * features["strain_coverage_score"]
        + 0.20 * features["allelic_conservation"]
        - 0.15 * features["variant_burden"]
    )
    features["low_redundancy_score"] = _clamp(1.0 - features["redundancy_penalty"])
    features["functional_impact_score"] = _clamp(
        0.35 * features["network_centrality"]
        + 0.35 * features["pathway_bottleneck_score"]
        + 0.30 * features["functional_dependency_score"]
    )
    infection_context_proxy = _clamp(
        0.35 * features["host_damage_score"]
        + 0.25 * features["infection_site_access_score"]
        + 0.20 * features["functional_impact_score"]
        + 0.20 * features["conservation_score"]
    )
    _use_empirical_or_proxy(features, "infection_context_score", infection_context_proxy, "infection_context_score_is_proxy")

    features["legacy_score_final"] = calculate_legacy_score(
        features,
        config["weights"]["legacy"],
        neutral_unknown_score=neutral,
        evalue_significance_threshold=threshold,
    )

    strategy_score_columns, strategy_contributions = calculate_strategy_scores(features, config["weights"])
    for column, values in strategy_score_columns.items():
        features[column] = values
    antibiotic_contributions = strategy_contributions["antibiotic_target_score"]
    antivirulence_contributions = strategy_contributions["antivirulence_target_score"]
    functional_contributions = strategy_contributions["functional_node_score"]
    features = _defragment_frame(features)

    meta_score, meta_contributions = calculate_meta_priority_score(features, config["weights"]["meta_priority"])
    meta_input = features[list(config["weights"]["meta_priority"].keys())].copy()
    features["meta_priority_score"] = meta_score
    features = compute_evolutionary_escape_risk_features(features, config)
    features["candidate_id"] = features["protein_id"]
    features["product"] = features.get(
        "uniprot_protein_name",
        pd.Series(["not_reported"] * len(features), index=features.index),
    ).fillna("not_reported")
    if "organism" not in features.columns:
        features["organism"] = "not_reported"
    if "strain" not in features.columns:
        features["strain"] = "not_reported"
    features["selectivity_score"] = _clamp(features["host_safety_score"])
    features["clinical_context_score"] = _clamp(
        0.40 * features["infection_context_score"]
        + 0.30 * features["host_damage_score"]
        + 0.30 * features["infection_site_access_score"]
    )
    features["confidence_modifier"] = _clamp(
        0.60 * features["evidence_confidence_score"]
        + 0.25 * features["evidence_coverage_score"]
        + 0.15 * features["optional_data_quality_score"]
    )
    features["evolutionary_escape_risk"] = features["evolutionary_escape_risk_score"]
    features["evolutionary_constraint"] = features["evolutionary_constraint_score"]
    features["mutation_tolerance"] = features["mutation_tolerance_score"]
    features["pathway_redundancy"] = _clamp(
        pd.to_numeric(
            features.get("functional_redundancy_escape_score", features.get("redundancy_penalty", 0.5)),
            errors="coerce",
        ).fillna(0.5)
    )
    for column in ["paralog_count", "mobile_context", "hgt_context", "recombination_context", "resistance_association"]:
        if column not in features.columns:
            features[column] = "unknown"
        else:
            features[column] = features[column].fillna("unknown")
    features["evidence_level"] = features["confidence_evidence_tier"]
    features["evidence_source"] = features["optional_data_source_summary"]
    features["provenance_status"] = features.apply(_dominant_provenance_status, axis=1)
    features["retrieval_mode"] = features.apply(_aggregate_retrieval_mode, axis=1)
    features["cache_status"] = features.apply(_aggregate_cache_status, axis=1)
    for column in ["source_version", "updated_at"]:
        if column not in features.columns:
            features[column] = "not_reported"
        else:
            features[column] = features[column].fillna("not_reported")
    features["interpretation_warning"] = INTERPRETATION_WARNING

    preferred_strategy_columns = assign_preferred_strategy(features)
    for column in preferred_strategy_columns.columns:
        features[column] = preferred_strategy_columns[column]
    therapeutic_priority, therapeutic_priority_contributions = _weighted_score(features, therapeutic_cfg["priority_weights"])
    features["therapeutic_priority_score"] = therapeutic_priority
    therapeutic_priority_contribution_columns = []
    therapeutic_priority_weight_norm = sum(abs(value) for value in therapeutic_cfg["priority_weights"].values()) or 1.0
    for feature_name in THERAPEUTIC_PRIORITY_INPUT_COLUMNS:
        if feature_name not in therapeutic_cfg["priority_weights"]:
            continue
        column = f"therapeutic_priority_{feature_name}_contribution"
        features[column] = _clamp(therapeutic_priority_contributions[feature_name] / therapeutic_priority_weight_norm)
        therapeutic_priority_contribution_columns.append(column)
    features["therapeutic_priority_contribution_summary"] = features.apply(
        lambda row: _contribution_summary(row, therapeutic_priority_contribution_columns),
        axis=1,
    )
    features["therapeutic_priority_components"] = features["therapeutic_priority_contribution_summary"]
    thresholds = therapeutic_cfg["classification_thresholds"]
    therapeutic_role_rows = features.apply(lambda row: _classify_therapeutic_role(row, thresholds), axis=1)
    features["therapeutic_role"] = therapeutic_role_rows.map(lambda item: item[0])
    features["therapeutic_role_rule"] = therapeutic_role_rows.map(lambda item: item[1])
    features["functional_node_types"] = features.apply(_derive_functional_node_types, axis=1)
    features["therapeutic_role_with_controlled_provider"] = features["therapeutic_role"]
    scenario_without_controlled = features.copy()
    clinical_controlled = _controlled_layer_mask(features, "clinical_impact")
    disease_controlled = _controlled_layer_mask(features, "curated_disease_context")
    site_controlled = _controlled_layer_mask(features, "therapy_site_context")
    scenario_without_controlled.loc[clinical_controlled, "host_damage_score"] = host_damage_proxy.loc[clinical_controlled]
    scenario_without_controlled.loc[clinical_controlled, "host_direct_damage_score"] = host_damage_proxy.loc[clinical_controlled]
    scenario_without_controlled.loc[clinical_controlled, "virulence_associated_severity_score"] = disease_severity_proxy.loc[clinical_controlled]
    scenario_without_controlled.loc[site_controlled, "infection_site_access_score"] = infection_access_proxy.loc[site_controlled]
    scenario_without_controlled.loc[disease_controlled, "infection_context_score"] = infection_context_proxy.loc[disease_controlled]
    priority_without_controlled, _ = _weighted_score(scenario_without_controlled, therapeutic_cfg["priority_weights"])
    scenario_without_controlled["therapeutic_priority_score"] = priority_without_controlled
    role_without_controlled = scenario_without_controlled.apply(lambda row: _classify_therapeutic_role(row, thresholds), axis=1)
    features["host_damage_score_without_controlled_provider"] = scenario_without_controlled["host_damage_score"]
    features["infection_site_access_score_without_controlled_provider"] = scenario_without_controlled["infection_site_access_score"]
    features["infection_context_score_without_controlled_provider"] = scenario_without_controlled["infection_context_score"]
    features["host_damage_score_controlled_delta"] = (
        features["host_damage_score"] - features["host_damage_score_without_controlled_provider"]
    ).round(4)
    features["infection_site_access_score_controlled_delta"] = (
        features["infection_site_access_score"] - features["infection_site_access_score_without_controlled_provider"]
    ).round(4)
    features["infection_context_score_controlled_delta"] = (
        features["infection_context_score"] - features["infection_context_score_without_controlled_provider"]
    ).round(4)
    features["therapeutic_role_without_controlled_provider"] = role_without_controlled.map(lambda item: item[0])
    features["therapeutic_role_rule_without_controlled_provider"] = role_without_controlled.map(lambda item: item[1])
    features["therapeutic_priority_score_without_controlled_provider"] = priority_without_controlled
    features["therapeutic_priority_controlled_delta"] = (
        features["therapeutic_priority_score"] - features["therapeutic_priority_score_without_controlled_provider"]
    ).round(4)
    features["controlled_context_max_feature_delta"] = pd.DataFrame(
        {
            "host_damage": features["host_damage_score_controlled_delta"].abs(),
            "infection_site_access": features["infection_site_access_score_controlled_delta"].abs(),
            "infection_context": features["infection_context_score_controlled_delta"].abs(),
        }
    ).max(axis=1).round(4)
    features["clinical_impact_controlled_dependency"] = clinical_controlled
    features["curated_disease_context_controlled_dependency"] = disease_controlled
    features["therapy_site_context_controlled_dependency"] = site_controlled
    features["controlled_dependency_flags"] = features.apply(_controlled_dependency_flags, axis=1)
    features["therapeutic_role_stability"] = features.apply(
        lambda row: "stable"
        if row["therapeutic_role_with_controlled_provider"] == row["therapeutic_role_without_controlled_provider"]
        else "changed",
        axis=1,
    )
    features["therapeutic_rule_boundary_margin"] = features.apply(
        lambda row: _therapeutic_boundary_margin(row, thresholds),
        axis=1,
    )
    features["therapeutic_rule_boundary_proximity"] = features["therapeutic_rule_boundary_margin"].map(
        _therapeutic_boundary_label
    )
    features["therapeutic_role_stability_explanation"] = features.apply(
        _therapeutic_stability_explanation,
        axis=1,
    )
    features["therapeutic_context_missingness"] = features.apply(
        lambda row: _therapeutic_missingness(row, thresholds),
        axis=1,
    )
    proxy_columns = [
        "host_damage_reduction_potential_is_proxy",
        "disease_severity_association_is_proxy",
        "clinical_impact_score_is_proxy",
        "host_damage_score_is_proxy",
        "infection_site_access_score_is_proxy",
        "infection_context_score_is_proxy",
    ]
    features["proxy_feature_count"] = (
        pd.DataFrame({column: features[column].fillna(False).astype(bool) for column in proxy_columns}).sum(axis=1).astype(int)
    )

    _initialize_phase3_columns(features)

    features["confidence_summary"] = (
        "coverage="
        + features["evidence_coverage_score"].round(2).astype(str)
        + "; evidence_confidence="
        + features["evidence_confidence_score"].round(2).astype(str)
        + "; mapping_confidence="
        + features["mapping_confidence"].round(2).astype(str)
        + "; source_quality="
        + features["optional_data_quality_score"].round(2).astype(str)
        + "; source_class="
        + features["confidence_source_class"].astype(str)
    )
    top_positive, top_negative = _driver_strings(meta_input, config["weights"]["meta_priority"])
    features["top_positive_drivers"] = top_positive
    features["top_negative_drivers"] = top_negative
    features["missing_evidence_flags"] = _build_missing_flags(features)
    features["candidate_audit_summary"] = features.apply(
        lambda row: (
            f"preferred_strategy={row['preferred_strategy']}; "
            f"therapeutic_role={row['therapeutic_role']}; "
            f"role_stability={row['therapeutic_role_stability']}; "
            f"therapeutic_priority={row['therapeutic_priority_score']:.3f}; "
            f"therapeutic_priority_components={row['therapeutic_priority_components']}; "
            f"evolutionary_escape_risk={row.get('evolutionary_escape_risk_score', 0.0):.3f}; "
            f"evolutionary_penalty={row.get('evolutionary_escape_penalty_applied', 0.0):.3f}; "
            f"margin={row['strategy_margin_score']:.3f}; "
            f"source_quality={row['optional_data_quality_score']:.2f}; "
            f"realism={row['data_realism_flag']}; "
            f"host_risk={row['host_risk_audit_summary']}; "
            f"site_access={row['therapy_site_context_audit_summary']}; "
            f"main_risk={str(row['top_negative_drivers']).split(';')[0]}"
        ),
        axis=1,
    )
    features = _defragment_frame(features)

    features.to_csv(processed_dir / "phase2_features.csv", index=False)

    scored_columns = [
        "candidate_id",
        "protein_id",
        "gene",
        "product",
        "organism",
        "strain",
        "gene_symbol_normalized",
        "legacy_score_final",
        "antibiotic_target_score",
        "antivirulence_target_score",
        "functional_node_score",
        "selectivity_score",
        "evolutionary_robustness_score",
        "clinical_context_score",
        "confidence_modifier",
        "meta_priority_score",
        "evolutionary_adjusted_meta_priority_score",
        "evolutionary_escape_penalty_applied",
        "functional_node_types",
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "mutation_tolerance",
        "pathway_redundancy",
        "paralog_count",
        "mobile_context",
        "hgt_context",
        "recombination_context",
        "resistance_association",
        "evidence_level",
        "evidence_source",
        "provenance_status",
        "retrieval_mode",
        "cache_status",
        "source_version",
        "updated_at",
        "interpretation_warning",
        "evidence_confidence_score",
        "evidence_coverage_score",
        "confidence_source_class",
        "confidence_evidence_tier",
        "confidence_source_quality_score",
        "top_positive_drivers",
        "top_negative_drivers",
        "missing_evidence_flags",
        "confidence_summary",
        "preferred_strategy",
        "strategy_margin_score",
        "host_damage_score",
        "infection_site_access_score",
        "infection_context_score",
        "therapeutic_role",
        "therapeutic_role_with_controlled_provider",
        "therapeutic_role_without_controlled_provider",
        "therapeutic_role_rule_without_controlled_provider",
        "therapeutic_role_stability",
        "therapeutic_role_stability_explanation",
        "therapeutic_rule_boundary_margin",
        "therapeutic_rule_boundary_proximity",
        "host_damage_score_without_controlled_provider",
        "infection_site_access_score_without_controlled_provider",
        "infection_context_score_without_controlled_provider",
        "host_damage_score_controlled_delta",
        "infection_site_access_score_controlled_delta",
        "infection_context_score_controlled_delta",
        "therapeutic_priority_score_without_controlled_provider",
        "therapeutic_priority_controlled_delta",
        "controlled_context_max_feature_delta",
        "controlled_dependency_flags",
        "clinical_impact_input_status",
        "curated_disease_context_input_status",
        "therapy_site_context_input_status",
        "therapeutic_context_input_summary",
        "contextual_essentiality_score",
        "pleiotropy_score",
        "conservation_score",
        "functional_node_theory_score",
        "mutation_tolerance_score",
        "functional_redundancy_escape_score",
        "compensatory_pathway_score",
        "fitness_cost_of_escape",
        "evolutionary_constraint_score",
        "resistance_emergence_risk",
        "multi_node_dependency_score",
        "mutational_tolerance_score",
        "redundancy_penalty",
        "fitness_cost_score",
        "compensation_difficulty_score",
        "collateral_sensitivity_score",
        "biofilm_escape_penalty",
        "horizontal_transfer_penalty",
        "evolutionary_escape_risk_score",
        "evolutionary_robustness_score",
        "reduced_evolutionary_space_score",
        "evolutionary_escape_risk_confidence",
        "evolutionary_escape_risk_status",
        "evolutionary_escape_risk_source_type",
        "evolutionary_escape_risk_interpretation",
        "evolutionary_escape_risk_audit_summary",
        "evolutionary_space_constraint_score",
        "evidence_quality_score",
        "confidence_ceiling",
        "evidence_source_type",
        "evidence_notes",
        "therapeutic_role_v3",
        "recommended_combination_class",
        "combination_rationale",
        "audit_flags",
        "phase3_notes",
        "therapeutic_priority_score",
        "therapeutic_priority_contribution_summary",
        "therapeutic_priority_components",
        *[
            f"therapeutic_priority_{column}_contribution"
            for column in THERAPEUTIC_PRIORITY_INPUT_COLUMNS
        ],
        "therapeutic_role_rule",
        "therapeutic_context_missingness",
        "optional_data_quality_score",
        "optional_data_source_summary",
        "data_realism_flag",
        "candidate_audit_summary",
        "host_risk_audit_summary",
    ]
    scored_columns.extend(THERAPEUTIC_SEPARATION_COLUMNS)
    scored_columns.extend(HOST_RISK_AUDIT_COLUMNS)
    scored_columns.extend(HUMAN_HOMOLOGY_AUDIT_COLUMNS)
    scored_columns.extend(THERAPY_SITE_CONTEXT_AUDIT_COLUMNS)
    scored_columns = list(dict.fromkeys(scored_columns))
    scored = features[[column for column in scored_columns if column in features.columns]].copy()
    scored.to_csv(processed_dir / "scored_nodes.csv", index=False)

    return features, scored


def build_phase3_scores(base_dir: Path, config: dict, phase2_features: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    processed_dir = base_dir / "data_processed"
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    features = phase2_features.copy() if phase2_features is not None else pd.read_csv(processed_dir / "phase2_features.csv")
    explicit_phase3_inputs = features.copy()

    features["meta_priority_score_v2"] = features["meta_priority_score"]
    features = _sanitize_literature_support_features(features)
    features = compute_contextual_essentiality_features(features, config)
    features = compute_virulence_layer_features(features, config)
    features = compute_redundancy_features(features, config)
    features = compute_evolutionary_escape_features(features, config)
    features = compute_collateral_sensitivity_features(features, config)
    features = compute_evidence_quality_features(features, config)
    features["host_similarity_risk"] = _compute_host_similarity_risk(features)
    features["literature_negative_score"] = _compute_literature_negative_score(features)
    features["literature_positive_score"] = _compute_literature_positive_score(features)
    _restore_explicit_phase3_values(
        explicit_phase3_inputs,
        features,
        [
            "contextual_essentiality_score",
            "pleiotropy_score",
            "conservation_score",
            "redundancy_penalty",
            "evolutionary_escape_risk_score",
            "evolutionary_robustness_score",
            "reduced_evolutionary_space_score",
            "evolutionary_escape_penalty_applied",
            "evolutionary_adjusted_meta_priority_score",
            "evolutionary_space_constraint_score",
            "collateral_sensitivity_score",
            "combination_opportunity_score",
            "evidence_quality_score",
            "confidence_ceiling",
        ],
    )
    features, layer_evidence_audit, layer_evidence_summary = apply_phase3_evidence_audit(features, config)
    features = compute_functional_node_theory_score(features, config)
    features["meta_priority_score_v3"] = _compute_meta_priority_score_v3(features, config)
    features = _apply_template_or_demo_flags(features, config)
    features = _limit_template_or_demo_confidence(features)
    phase3_roles = features.apply(lambda row: _classify_therapeutic_role_v3(row, config), axis=1)
    features["therapeutic_role_v3"] = phase3_roles.map(lambda item: item[0])
    features["therapeutic_role_v3_reason"] = phase3_roles.map(lambda item: item[1])
    features["phase3_recommendation"] = features.apply(_phase3_recommendation, axis=1)
    features = _finalize_phase3_output_values(features)
    features = _assign_phase3_ranks(features)
    features["phase3_audit_summary"] = features.apply(_phase3_audit_summary, axis=1)
    features = _defragment_frame(features)
    _validate_phase3_scores_before_export(features)
    features.to_csv(processed_dir / "phase3_features.csv", index=False)
    layer_evidence_audit.to_csv(results_dir / "layer_evidence_audit.csv", index=False)
    layer_evidence_summary.to_csv(results_dir / "layer_evidence_summary.csv", index=False)

    scored_columns = [
        "protein_id",
        "gene",
        "gene_symbol_normalized",
        "legacy_score_final",
        "antibiotic_target_score",
        "antivirulence_target_score",
        "functional_node_score",
        "meta_priority_score_v2",
        "meta_priority_score_v3",
        "therapeutic_role",
        "therapeutic_role_v3",
        "candidate_record_type",
        "is_template_or_demo_record",
        "template_or_demo_reason",
        "included_in_therapeutic_ranking",
        "ranking_inclusion_status",
        "ranking_inclusion_reason",
        "evidence_mixture_label",
        "real_evidence_layer_count",
        "demo_or_default_layer_count",
        "proxy_layer_count",
        "missing_layer_count",
        "negative_evidence_layer_count",
        "rank_phase3_real_candidates",
        "rank_phase3_all_records",
        "functional_node_theory_score",
        "functional_node_theory_confidence",
        "functional_node_theory_label",
        "phase3_evidence_confidence_label",
        "therapeutic_role_v3_reason",
        "phase3_recommendation",
        "contextual_essentiality_score",
        "pleiotropy_score",
        "conservation_score",
        "evolutionary_space_constraint_score",
        "evolutionary_escape_risk_score",
        "evolutionary_robustness_score",
        "reduced_evolutionary_space_score",
        "evolutionary_escape_penalty_applied",
        "evolutionary_adjusted_meta_priority_score",
        "evolutionary_escape_risk_confidence",
        "evolutionary_escape_risk_status",
        "evolutionary_escape_risk_interpretation",
        "redundancy_penalty",
        "host_similarity_risk",
        "biofilm_escape_penalty",
        "horizontal_transfer_penalty",
        "collateral_sensitivity_score",
        "combination_opportunity_score",
        "recommended_combination_class",
        "escape_creates_vulnerability",
        "combination_rationale",
        "evidence_quality_score",
        "confidence_ceiling",
        "evidence_source_type",
        "evidence_notes",
        "phase3_layer_evidence_quality",
        "phase3_confidence_ceiling_from_layers",
        "phase3_real_evidence_layer_count",
        "phase3_proxy_layer_count",
        "phase3_demo_default_layer_count",
        "phase3_missing_layer_count",
        "phase3_negative_evidence_count",
        "phase3_evidence_category_summary",
        "phase3_evidence_gap_summary",
        "phase3_negative_evidence_summary",
        "phase3_evidence_explanation",
        "literature_positive_score",
        "literature_negative_score",
        "literature_support_score",
        "literature_support_status",
        "literature_source_quality",
        "literature_has_curated_evidence",
        "literature_evidence_type",
        "citation",
        "doi",
        "pubmed_id",
        "audit_flags",
        "phase3_audit_summary",
    ]
    scored = features[[column for column in scored_columns if column in features.columns]].copy()
    scored.to_csv(processed_dir / "scored_nodes_phase3.csv", index=False)
    _write_phase3_rankings(features, results_dir)
    return features, scored


def _finalize_phase3_output_values(features: pd.DataFrame) -> pd.DataFrame:
    """Fill Phase 3 output gaps with explicit defaults before writing reports.

    Earlier stages intentionally preserve missing source evidence. Phase 3
    reports are easier to audit when derived score columns and identifiers do
    not serialize as blank CSV cells, so this finalization only fills derived
    Phase 3 fields and human-readable identifiers. Missing evidence remains
    visible through audit flags and source/provenance columns.
    """
    result = features.copy()
    if "protein_id" in result.columns:
        protein_ids = result["protein_id"].fillna("unknown_protein").astype(str)
        if "gene" not in result.columns:
            result["gene"] = protein_ids
        else:
            missing_gene = result["gene"].fillna("").astype(str).str.strip().eq("")
            result.loc[missing_gene, "gene"] = protein_ids.loc[missing_gene]
        if "gene_symbol_normalized" not in result.columns:
            result["gene_symbol_normalized"] = result["gene"].fillna(protein_ids).astype(str).str.upper()
        else:
            missing_normalized = result["gene_symbol_normalized"].fillna("").astype(str).str.strip().eq("")
            result.loc[missing_normalized, "gene_symbol_normalized"] = (
                result.loc[missing_normalized, "gene"].fillna(protein_ids.loc[missing_normalized]).astype(str).str.upper()
            )

    phase3_numeric_defaults = {
        **{column: (0.0 if pd.isna(default) else float(default)) for column, default in PHASE3_NUMERIC_DEFAULTS.items()},
        "meta_priority_score_v2": 0.0,
        "meta_priority_score_v3": 0.0,
        "functional_node_theory_confidence": 0.0,
        "conservation_score": 0.0,
        "redundancy_penalty": 0.0,
        "host_similarity_penalty": 0.0,
        "combination_opportunity_score": 0.0,
        "phase3_evidence_confidence_score": 0.0,
    }
    for column, default in phase3_numeric_defaults.items():
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").fillna(default).clip(lower=0.0, upper=1.0)

    for column, default in PHASE3_TEXT_DEFAULTS.items():
        if column in result.columns:
            result[column] = result[column].fillna(default).astype(str)
    return result


def _sanitize_literature_support_features(features: pd.DataFrame) -> pd.DataFrame:
    """Keep literature neutral unless a real curated reference is present.

    Template rows and pending demo curation are useful for packaging and tests,
    but they must not increase Phase 3 confidence or priority. This function
    preserves the columns and marks why the literature layer is neutral.
    """
    result = features.copy()
    if result.empty:
        return result

    reference_columns = [
        column
        for column in ["doi", "doi_or_url", "pubmed_id", "pmid", "citation", "reference"]
        if column in result.columns
    ]
    text_columns = [
        column
        for column in [
            "literature_evidence_type",
            "evidence_type",
            "literature_evidence_source_type",
            "database",
            "literature_support_database",
            "curator_notes",
        ]
        if column in result.columns
    ]
    if reference_columns:
        references = result[reference_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    else:
        references = pd.Series([""] * len(result), index=result.index, dtype=object)
    if text_columns:
        evidence_text = result[text_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    else:
        evidence_text = pd.Series([""] * len(result), index=result.index, dtype=object)

    placeholder_reference = references.str.fullmatch(r"\s*").fillna(True) | references.str.contains(
        "to_be_curated|pending_manual_curation|template|example|demo|placeholder|not_available|none|nan",
        regex=True,
    )
    has_reference = references.str.contains(r"10\.\d{4,9}/|pubmed|pmid|\bdoi\b|\d{7,}", regex=True) & ~placeholder_reference
    curated_text = evidence_text.str.contains("curated|literature|experimental|pubmed|doi|manual_catalog", regex=True)
    demo_or_template_text = evidence_text.str.contains(
        "demo|template|example|pending_manual_curation|to_be_curated|placeholder",
        regex=True,
    )
    curated = (has_reference | (curated_text & ~placeholder_reference)) & ~demo_or_template_text

    if "literature_support_score" in result.columns:
        result["literature_support_score"] = pd.to_numeric(result["literature_support_score"], errors="coerce").fillna(0.0)
        result.loc[~curated, "literature_support_score"] = 0.0
        result["literature_support_score"] = result["literature_support_score"].clip(0.0, 1.0)
    for column in [
        "therapeutic_relevance",
        "virulence_relevance",
        "essentiality_relevance",
        "resistance_relevance",
        "host_safety_relevance",
        "evolutionary_escape_relevance",
    ]:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)
            result.loc[~curated, column] = 0.0
            result[column] = result[column].clip(0.0, 1.0)
    if "evidence_strength" in result.columns:
        result["evidence_strength"] = pd.to_numeric(result["evidence_strength"], errors="coerce").fillna(0.0)
        result.loc[~curated, "evidence_strength"] = 0.0
        result["evidence_strength"] = result["evidence_strength"].clip(0.0, 1.0)
    else:
        result["evidence_strength"] = curated.astype(float)
    if "literature_source_quality" in result.columns:
        result["literature_source_quality"] = pd.to_numeric(result["literature_source_quality"], errors="coerce").fillna(0.0)
        result.loc[~curated, "literature_source_quality"] = 0.0
    else:
        result["literature_source_quality"] = curated.astype(float)

    result["literature_has_curated_evidence"] = curated.astype(bool)
    result["literature_support_status"] = "curated_evidence_present"
    result.loc[~curated, "literature_support_status"] = "missing_or_template_only"
    if "literature_evidence_type" not in result.columns:
        result["literature_evidence_type"] = "not_reported"
    result.loc[~curated, "literature_evidence_type"] = "missing_or_template_only"
    return result


def _apply_template_or_demo_flags(features: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    result = features.copy()
    if result.empty:
        result["candidate_record_type"] = pd.Series(dtype=object)
        result["is_template_or_demo_record"] = pd.Series(dtype=bool)
        result["template_or_demo_reason"] = pd.Series(dtype=object)
        result["included_in_therapeutic_ranking"] = pd.Series(dtype=bool)
        result["ranking_inclusion_status"] = pd.Series(dtype=object)
        result["ranking_inclusion_reason"] = pd.Series(dtype=object)
        result["evidence_mixture_label"] = pd.Series(dtype=object)
        return result

    cfg = _phase3_ranking_inclusion_config(config or {})
    protein = result.get("protein_id", pd.Series([""] * len(result), index=result.index)).fillna("").astype(str).str.upper()
    gene = result.get("gene", pd.Series([""] * len(result), index=result.index)).fillna("").astype(str).str.upper()
    text_columns = [
        column
        for column in result.columns
        if column.endswith("_database")
        or column.endswith("_source_name")
        or column.endswith("_source_type")
        or column in {"source_database", "data_realism_flag", "evidence_source_type", "audit_flags", "literature_support_status"}
    ]
    combined = result[text_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower() if text_columns else pd.Series([""] * len(result), index=result.index)
    explicit_template = protein.eq("EXAMPLE_PROTEIN") | gene.eq("EXAMPLE_GENE")
    explicit_demo_text = combined.str.contains("template_record|demo_only_record|example_protein|example_gene", regex=True)
    demo_counts = result[[column for column in result.columns if column.endswith("_source_type")]].fillna("").astype(str).apply(
        lambda col: col.str.lower().isin(["demo", "demo_data", "template"]).astype(int)
    ).sum(axis=1) if any(column.endswith("_source_type") for column in result.columns) else pd.Series([0] * len(result), index=result.index)
    real_layer_count = pd.to_numeric(result.get("phase3_real_evidence_layer_count", pd.Series([0] * len(result), index=result.index)), errors="coerce").fillna(0).astype(int)
    demo_default_count = pd.to_numeric(result.get("phase3_demo_default_layer_count", pd.Series([0] * len(result), index=result.index)), errors="coerce").fillna(0).astype(int)
    proxy_count = pd.to_numeric(result.get("phase3_proxy_layer_count", pd.Series([0] * len(result), index=result.index)), errors="coerce").fillna(0).astype(int)
    missing_count = pd.to_numeric(result.get("phase3_missing_layer_count", pd.Series([0] * len(result), index=result.index)), errors="coerce").fillna(0).astype(int)
    negative_count = pd.to_numeric(result.get("phase3_negative_evidence_count", pd.Series([0] * len(result), index=result.index)), errors="coerce").fillna(0).astype(int)
    demo_or_default_layer_count = pd.concat([demo_default_count, demo_counts.astype(int)], axis=1).max(axis=1).astype(int)
    data_realism = result.get("data_realism_flag", pd.Series([""] * len(result), index=result.index)).fillna("").astype(str).str.lower()
    total_observed = (real_layer_count + demo_or_default_layer_count + proxy_count).clip(lower=1)
    demo_fraction = (demo_or_default_layer_count / total_observed).clip(0.0, 1.0)

    record_types: list[str] = []
    included_values: list[bool] = []
    inclusion_statuses: list[str] = []
    inclusion_reasons: list[str] = []
    template_flags: list[bool] = []
    template_reasons: list[str] = []
    mixture_labels: list[str] = []
    for idx in result.index:
        row_reasons: list[str] = []
        if bool(explicit_template.loc[idx]):
            row_reasons.append("explicit_example_identifier")
        if bool(explicit_demo_text.loc[idx]):
            row_reasons.append("source_or_literature_marked_demo_template")
        real = int(real_layer_count.loc[idx])
        demo_default = int(demo_or_default_layer_count.loc[idx])
        proxy = int(proxy_count.loc[idx])
        missing = int(missing_count.loc[idx])
        negative = int(negative_count.loc[idx])
        fraction = float(demo_fraction.loc[idx])
        explicit = bool(explicit_template.loc[idx])
        demo_only = real == 0 and (demo_default > 0 or data_realism.loc[idx] == "demo_only")
        mixed = real >= int(cfg["min_real_layers_for_exploratory_inclusion"]) and (demo_default > 0 or proxy > 0 or missing > 0)

        if explicit and bool(cfg["exclude_explicit_template_records"]):
            record_type = "template_record"
            included = False
            status = "excluded_template_record"
            reason = "EXAMPLE_PROTEIN/EXAMPLE_GENE o plantilla explicita; se conserva solo para pruebas."
            template_flag = True
        elif demo_only and bool(cfg["exclude_demo_only_records"]):
            record_type = "demo_record"
            included = False
            status = "excluded_demo_only_record"
            reason = "registro sin capas reales; demo/default/proxy no habilitan ranking terapeutico real."
            template_flag = True
            row_reasons.append("demo_or_default_without_real_evidence")
        elif real <= 0:
            record_type = "insufficiently_supported_candidate"
            included = False
            status = "excluded_no_real_evidence"
            reason = "sin evidencia real; missing no es evidencia negativa, pero no alcanza para ranking real."
            template_flag = False
        elif real >= int(cfg["min_real_layers_for_real_candidate"]) and fraction <= float(cfg["max_demo_fraction_for_real_candidate"]):
            record_type = "real_candidate"
            included = True
            status = "included_real_candidate"
            reason = f"{real} capas reales y fraccion demo/default {fraction:.2f}; candidato real interpretable con cautela."
            template_flag = False
        elif mixed and bool(cfg["allow_mixed_evidence_candidates"]):
            record_type = "mixed_evidence_candidate"
            included = True
            status = "included_exploratory_with_demo_support"
            reason = f"{real} capas reales con soporte demo/proxy/default parcial; entra como exploratorio, no validado."
            template_flag = False
        else:
            record_type = "insufficiently_supported_candidate"
            included = False
            status = "excluded_no_real_evidence"
            reason = "no alcanza umbrales configurados de inclusion."
            template_flag = False

        record_types.append(record_type)
        included_values.append(included)
        inclusion_statuses.append(status)
        inclusion_reasons.append(reason)
        template_flags.append(template_flag)
        template_reasons.append(";".join(dict.fromkeys(row_reasons)) if row_reasons else "not_template_record")
        mixture_labels.append(_evidence_mixture_label(real, demo_default, proxy, missing, negative))

    additions = pd.DataFrame(
        {
            "candidate_record_type": record_types,
            "is_template_or_demo_record": template_flags,
            "template_or_demo_reason": template_reasons,
            "included_in_therapeutic_ranking": included_values,
            "ranking_inclusion_status": inclusion_statuses,
            "ranking_inclusion_reason": inclusion_reasons,
            "real_evidence_layer_count": real_layer_count,
            "demo_or_default_layer_count": demo_or_default_layer_count,
            "proxy_layer_count": proxy_count,
            "missing_layer_count": missing_count,
            "negative_evidence_layer_count": negative_count,
            "evidence_mixture_label": mixture_labels,
        },
        index=result.index,
    )
    return pd.concat([result.drop(columns=[column for column in additions.columns if column in result.columns], errors="ignore"), additions], axis=1).copy()


def _phase3_ranking_inclusion_config(config: dict) -> dict[str, object]:
    cfg = dict(DEFAULT_PHASE3_RANKING_INCLUSION_CONFIG)
    configured = config.get("phase3", {}).get("ranking_inclusion", {}) if isinstance(config, dict) else {}
    if isinstance(configured, dict):
        cfg.update(configured)
    return cfg


def _evidence_mixture_label(real: int, demo_default: int, proxy: int, missing: int, negative: int) -> str:
    if negative > 0 and real > 0:
        return "real_evidence_with_negative_signal"
    if real > 0 and (demo_default > 0 or proxy > 0):
        return "mixed_real_demo_proxy"
    if real > 0 and missing > 0:
        return "partial_real_with_missing_layers"
    if real > 0:
        return "mostly_real_evidence"
    if demo_default > 0 or proxy > 0:
        return "demo_proxy_only"
    return "missing_only"


def _limit_template_or_demo_confidence(features: pd.DataFrame) -> pd.DataFrame:
    result = features.copy()
    if "is_template_or_demo_record" not in result.columns:
        return result
    demo = result["is_template_or_demo_record"].fillna(False).astype(bool)
    for column in ["evidence_quality_score", "confidence_ceiling", "functional_node_theory_confidence"]:
        if column in result.columns:
            values = pd.to_numeric(result[column], errors="coerce").fillna(0.0).clip(0.0, 1.0)
            values.loc[demo] = values.loc[demo].clip(upper=0.10)
            result[column] = values
    return result


def _validate_phase3_scores_before_export(features: pd.DataFrame) -> None:
    if features.empty or "meta_priority_score_v3" not in features.columns:
        return
    included = features.get("included_in_therapeutic_ranking", pd.Series([True] * len(features), index=features.index)).fillna(True).astype(bool)
    real_scores = pd.to_numeric(features.loc[included, "meta_priority_score_v3"], errors="coerce").fillna(0.0)
    if real_scores.empty:
        warnings.warn(
            "Phase 3 ranking contains only demo/template or missing candidates; no real therapeutic ranking was produced.",
            RuntimeWarning,
            stacklevel=2,
        )
    elif real_scores.eq(0.0).all():
        warnings.warn(
            "All non-demo Phase 3 candidates have meta_priority_score_v3=0.0. Check missing evidence, demo/default/proxy provenance, and score persistence before interpreting the ranking.",
            RuntimeWarning,
            stacklevel=2,
        )


def _phase3_sort_columns(df: pd.DataFrame) -> list[str]:
    columns = [
        "included_in_therapeutic_ranking",
        "meta_priority_score_v3",
        "evidence_quality_score",
        "functional_node_theory_score",
        "confidence_ceiling",
        "meta_priority_score_v2",
    ]
    return [column for column in columns if column in df.columns]


def _sort_phase3_records(features: pd.DataFrame) -> pd.DataFrame:
    result = features.copy()
    if "included_in_therapeutic_ranking" not in result.columns:
        result["included_in_therapeutic_ranking"] = True
    for column in ["meta_priority_score_v3", "evidence_quality_score", "functional_node_theory_score", "confidence_ceiling", "meta_priority_score_v2"]:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    result["included_in_therapeutic_ranking"] = result["included_in_therapeutic_ranking"].fillna(False).astype(bool)
    sort_columns = _phase3_sort_columns(result)
    return result.sort_values(
        sort_columns,
        ascending=[False] * len(sort_columns),
        kind="mergesort",
    ).reset_index(drop=True)


def _assign_phase3_ranks(features: pd.DataFrame) -> pd.DataFrame:
    ranked = _sort_phase3_records(features)
    ranked["rank_phase3_all_records"] = range(1, len(ranked) + 1)
    ranked["rank_phase3"] = ranked["rank_phase3_all_records"]
    ranked["rank_phase3_real_candidates"] = pd.NA
    included = ranked["included_in_therapeutic_ranking"].fillna(False).astype(bool)
    real_order = ranked.loc[included].sort_values(
        ["meta_priority_score_v3", "evidence_quality_score", "functional_node_theory_score", "confidence_ceiling", "meta_priority_score_v2"],
        ascending=[False, False, False, False, False],
        kind="mergesort",
    )
    ranked.loc[real_order.index, "rank_phase3_real_candidates"] = range(1, len(real_order) + 1)
    ranked = ranked.sort_values(
        ["included_in_therapeutic_ranking", "rank_phase3_real_candidates", "rank_phase3_all_records"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    return ranked


def _restore_explicit_phase3_values(source: pd.DataFrame, target: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column not in source.columns:
            continue
        explicit = pd.to_numeric(source[column], errors="coerce")
        if column not in target.columns:
            target[column] = explicit
            continue
        target[column] = pd.to_numeric(target[column], errors="coerce")
        target.loc[explicit.notna(), column] = explicit.loc[explicit.notna()]
        target[column] = target[column].clip(lower=0.0, upper=1.0)


def _compute_meta_priority_score_v3(features: pd.DataFrame, config: dict) -> pd.Series:
    cfg = {
        "weights": dict(DEFAULT_META_PRIORITY_V3_CONFIG["weights"]),
        "penalties": dict(DEFAULT_META_PRIORITY_V3_CONFIG["penalties"]),
        "role_thresholds": dict(DEFAULT_META_PRIORITY_V3_CONFIG["role_thresholds"]),
    }
    configured = config.get("phase3", {}).get("meta_priority_v3", {})
    if isinstance(configured, dict):
        cfg["weights"].update(configured.get("weights", {}) or {})
        cfg["penalties"].update(configured.get("penalties", {}) or {})
        cfg["role_thresholds"].update(configured.get("role_thresholds", {}) or {})
    weights = cfg.get("weights", {})
    penalties = cfg.get("penalties", {})
    positive_terms = {
        "w_antibiotic": _safe_series(features, "antibiotic_target_score", 0.0),
        "w_antivirulence": _safe_series(features, "antivirulence_target_score", 0.0),
        "w_theory": _safe_series(features, "functional_node_theory_score", 0.0),
        "w_evidence": _safe_series(features, "evidence_quality_score", 0.0),
        "w_combination": _safe_series(features, "combination_opportunity_score", 0.0),
    }
    penalty_terms = {
        "p_escape": _safe_series(features, "evolutionary_escape_risk_score", 0.0),
        "p_redundancy": _safe_series(features, "redundancy_penalty", 0.0),
        "p_biofilm": _safe_series(features, "biofilm_escape_penalty", 0.0),
        "p_hgt": _safe_series(features, "horizontal_transfer_penalty", 0.0),
    }
    total_weight = sum(max(float(weights.get(key, 0.0)), 0.0) for key in positive_terms)
    if total_weight <= 0:
        positive_score = pd.Series([0.0] * len(features), index=features.index, dtype=float)
    else:
        positive_score = sum(
            positive_terms[key].fillna(0.0).clip(0.0, 1.0) * max(float(weights.get(key, 0.0)), 0.0)
            for key in positive_terms
        ) / total_weight
    total_penalty = sum(max(float(penalties.get(key, 0.0)), 0.0) for key in penalty_terms)
    if total_penalty <= 0:
        penalty_score = pd.Series([0.0] * len(features), index=features.index, dtype=float)
    else:
        penalty_score = sum(
            penalty_terms[key].fillna(0.0).clip(0.0, 1.0) * max(float(penalties.get(key, 0.0)), 0.0)
            for key in penalty_terms
        ) / total_penalty
        penalty_score = penalty_score * min(total_penalty, 1.0)
    return (positive_score - penalty_score).clip(lower=0.0, upper=1.0)


def _compute_host_similarity_risk(features: pd.DataFrame) -> pd.Series:
    candidates = []
    for column, default in [
        ("human_homolog", 0.0),
        ("domain_overlap_score", 0.0),
        ("host_criticality_penalty", 0.0),
        ("orthology_confidence_score", 0.0),
    ]:
        candidates.append(_safe_series(features, column, default).fillna(default).clip(0.0, 1.0))
    if "orthology_percent_identity" in features.columns:
        candidates.append((_safe_series(features, "orthology_percent_identity", 0.0).fillna(0.0) / 100.0).clip(0.0, 1.0))
    return pd.concat(candidates, axis=1).max(axis=1).clip(0.0, 1.0)


def _compute_literature_negative_score(features: pd.DataFrame) -> pd.Series:
    negative_terms = []
    for column in ["host_safety_relevance", "resistance_relevance", "evolutionary_escape_relevance"]:
        if column in features.columns:
            values = pd.to_numeric(features[column], errors="coerce")
            negative_terms.append((-values).clip(lower=0.0, upper=1.0))
    if not negative_terms:
        return pd.Series([0.0] * len(features), index=features.index, dtype=float)
    strength = _safe_series(features, "evidence_strength", 1.0).fillna(1.0).clip(0.0, 1.0)
    return (pd.concat(negative_terms, axis=1).max(axis=1).fillna(0.0) * strength).clip(0.0, 1.0)


def _compute_literature_positive_score(features: pd.DataFrame) -> pd.Series:
    positive_terms = []
    for column in [
        "therapeutic_relevance",
        "virulence_relevance",
        "essentiality_relevance",
        "host_safety_relevance",
        "evolutionary_escape_relevance",
    ]:
        if column in features.columns:
            positive_terms.append(pd.to_numeric(features[column], errors="coerce").clip(lower=0.0, upper=1.0))
    base = _safe_series(features, "literature_support_score", 0.0).fillna(0.0).clip(0.0, 1.0)
    if positive_terms:
        base = pd.concat([base, *positive_terms], axis=1).max(axis=1)
    strength = _safe_series(features, "evidence_strength", 1.0).fillna(1.0).clip(0.0, 1.0)
    return (base * strength).clip(0.0, 1.0)


def _classify_therapeutic_role_v3(row: pd.Series, config: dict) -> tuple[str, str]:
    thresholds = dict(DEFAULT_META_PRIORITY_V3_CONFIG["role_thresholds"])
    thresholds.update(config.get("phase3", {}).get("meta_priority_v3", {}).get("role_thresholds", {}) or {})
    minimum_evidence = float(thresholds.get("minimum_evidence", 0.35))
    high_escape = float(thresholds.get("high_escape_risk", 0.65))
    high_host_similarity = float(thresholds.get("high_host_similarity_risk", 0.70))
    high_antibiotic = float(thresholds.get("high_antibiotic", 0.70))
    high_antivirulence = float(thresholds.get("high_antivirulence", 0.70))
    high_theory = float(thresholds.get("high_theory", 0.70))
    high_combination = float(thresholds.get("high_combination", 0.65))
    dual_margin = float(thresholds.get("dual_margin", 0.10))
    evidence = max(
        float(row.get("functional_node_theory_confidence", 0.0) or 0.0),
        float(row.get("evidence_quality_score", 0.0) or 0.0),
    )
    real_layers = int(row.get("phase3_real_evidence_layer_count", 0) or 0)
    negative_count = int(row.get("phase3_negative_evidence_count", 0) or 0)
    escape = float(row.get("evolutionary_escape_risk_score", 0.0) or 0.0)
    escape_status = str(row.get("evolutionary_escape_risk_status", "") or "")
    host_similarity = float(row.get("host_similarity_risk", 0.0) or 0.0)
    antibiotic = float(row.get("antibiotic_target_score", 0.0) or 0.0)
    antivirulence = float(row.get("antivirulence_target_score", 0.0) or 0.0)
    theory = float(row.get("functional_node_theory_score", 0.0) or 0.0)
    combination = float(row.get("combination_opportunity_score", 0.0) or 0.0)
    meta = float(row.get("meta_priority_score_v3", 0.0) or 0.0)

    if real_layers > 0 and host_similarity >= high_host_similarity:
        return "deprioritized_due_to_negative_evidence", "baja prioridad por riesgo real de similitud/homologia con hospedero"
    if real_layers > 0 and escape >= high_escape and escape_status not in {"insufficient_evidence", "unknown_missing_evidence"}:
        return "deprioritized_due_to_negative_evidence", "baja prioridad por riesgo evolutivo alto respaldado por evidencia"
    if negative_count > 0 and real_layers > 0:
        return "deprioritized_due_to_negative_evidence", "baja prioridad por evidencia biologica negativa real"
    if evidence < 0.15 and real_layers == 0:
        return "insufficient_evidence", "baja confianza por falta de datos reales; no equivale a evidencia negativa"
    if evidence < minimum_evidence:
        return "exploratory_candidate", "candidato exploratorio por senales parciales con confianza limitada"
    if abs(antibiotic - antivirulence) <= dual_margin and max(antibiotic, antivirulence) >= min(high_antibiotic, high_antivirulence):
        role = "mixed_strategy_candidate"
    elif theory >= high_theory:
        role = "strongly_supported_candidate" if evidence >= 0.75 and real_layers >= 4 else "moderately_supported_candidate"
    elif antibiotic >= high_antibiotic or antivirulence >= high_antivirulence or combination >= high_combination:
        role = "moderately_supported_candidate" if evidence >= 0.55 and real_layers >= 2 else "weakly_supported_candidate"
    elif evidence >= 0.75 and meta >= 0.60 and real_layers >= 4:
        role = "strongly_supported_candidate"
    elif evidence >= 0.55 and real_layers >= 2:
        role = "moderately_supported_candidate"
    elif evidence >= minimum_evidence or real_layers > 0:
        role = "weakly_supported_candidate"
    else:
        role = "exploratory_candidate"
    return role, _phase3_role_reason(role, evidence, real_layers, row)


def _phase3_role_reason(role: str, evidence: float, real_layers: int, row: pd.Series) -> str:
    if role == "strongly_supported_candidate":
        return "alta prioridad por evidencia real convergente y score funcional fuerte"
    if role == "moderately_supported_candidate":
        return "prioridad moderada por evidencia real parcial convergente"
    if role == "weakly_supported_candidate":
        return "senal util pero limitada por cobertura o confianza incompleta"
    if role == "mixed_strategy_candidate":
        return "senales antibiotica y antivirulencia cercanas; estrategia mixta plausible"
    if role == "exploratory_candidate":
        return "candidato exploratorio: requiere curacion adicional"
    return str(row.get("phase3_evidence_explanation", "")) or f"evidence={evidence:.3f}; real_layers={real_layers}"


def _phase3_recommendation(row: pd.Series) -> str:
    role = str(row.get("therapeutic_role_v3", "insufficient_evidence"))
    if role == "strongly_supported_candidate":
        return "Candidato prioritario con evidencia convergente suficiente"
    if role == "moderately_supported_candidate":
        return "Candidato prometedor, pero debe revisarse junto con seguridad y escape evolutivo"
    if role == "weakly_supported_candidate":
        return "Candidato exploratorio: requiere curacion adicional"
    if role == "deprioritized_due_to_negative_evidence":
        if float(row.get("host_similarity_risk", 0.0) or 0.0) >= 0.70:
            return "Candidato penalizado por posible similitud con hospedero"
        if float(row.get("evolutionary_escape_risk_score", 0.0) or 0.0) >= 0.65:
            return "Candidato penalizado por alto riesgo de escape evolutivo"
        return "Candidato penalizado por evidencia biologica negativa"
    if int(row.get("phase3_demo_default_layer_count", 0) or 0) > 0 and int(row.get("phase3_real_evidence_layer_count", 0) or 0) == 0:
        return "No interpretable como blanco terapeutico hasta reemplazar datos demo/default"
    return "Candidato exploratorio: requiere curacion adicional"


def _write_phase3_rankings(features: pd.DataFrame, results_dir: Path) -> None:
    phase3_ranking = _assign_phase3_ranks(features)
    ranking_columns = [
        "rank_phase3_all_records",
        "rank_phase3",
        "rank_phase3_real_candidates",
        "included_in_therapeutic_ranking",
        "candidate_record_type",
        "is_template_or_demo_record",
        "template_or_demo_reason",
        "ranking_inclusion_status",
        "ranking_inclusion_reason",
        "evidence_mixture_label",
        "real_evidence_layer_count",
        "demo_or_default_layer_count",
        "proxy_layer_count",
        "missing_layer_count",
        "negative_evidence_layer_count",
        "protein_id",
        "gene",
        "meta_priority_score_v2",
        "meta_priority_score_v3",
        "functional_node_theory_score",
        "functional_node_theory_confidence",
        "functional_node_theory_label",
        "therapeutic_role_v3",
        "therapeutic_role_v3_reason",
        "phase3_evidence_confidence_label",
        "phase3_recommendation",
        "evolutionary_escape_risk_score",
        "evolutionary_escape_risk_status",
        "host_similarity_risk",
        "evolutionary_robustness_score",
        "reduced_evolutionary_space_score",
        "evolutionary_escape_penalty_applied",
        "redundancy_penalty",
        "combination_opportunity_score",
        "evidence_quality_score",
        "confidence_ceiling",
        "phase3_real_evidence_layer_count",
        "phase3_proxy_layer_count",
        "phase3_demo_default_layer_count",
        "phase3_missing_layer_count",
        "phase3_negative_evidence_count",
        "phase3_evidence_gap_summary",
        "phase3_negative_evidence_summary",
        "phase3_evidence_explanation",
        "literature_support_score",
        "literature_support_status",
        "literature_source_quality",
        "literature_has_curated_evidence",
        "phase3_audit_summary",
    ]
    export_columns = [column for column in ranking_columns if column in phase3_ranking.columns]
    phase3_ranking[export_columns].to_csv(results_dir / "ranking_nodos_phase3.csv", index=False)
    real_candidates = phase3_ranking.loc[phase3_ranking["included_in_therapeutic_ranking"].fillna(False).astype(bool)].copy()
    real_candidates[export_columns].to_csv(results_dir / "ranking_nodos_phase3_real_candidates.csv", index=False)
    template_records = phase3_ranking.loc[phase3_ranking["is_template_or_demo_record"].fillna(False).astype(bool)].copy()
    template_records[export_columns].to_csv(results_dir / "template_or_demo_records.csv", index=False)
    comparison = _build_phase2_vs_phase3_comparison(features)
    comparison.to_csv(results_dir / "phase2_vs_phase3_comparison.csv", index=False)
    _build_evolutionary_escape_audit(features).to_csv(results_dir / "evolutionary_escape_audit.csv", index=False)
    role_stability_audit = build_therapeutic_role_stability_audit(features)
    role_stability_audit.to_csv(results_dir / "therapeutic_role_stability_audit.csv", index=False)
    (results_dir / "therapeutic_role_stability_report.md").write_text(
        build_therapeutic_role_stability_report(role_stability_audit),
        encoding="utf-8",
    )
    (results_dir / "theory_of_nodes_report.md").write_text(
        _build_theory_of_nodes_report(features, comparison),
        encoding="utf-8",
    )
    (results_dir / "top10_functional_node_theory_audit.md").write_text(
        _build_top10_functional_node_theory_audit(features),
        encoding="utf-8",
    )
    (results_dir / "report_phase3.md").write_text(
        _build_phase3_user_report(phase3_ranking),
        encoding="utf-8",
    )


def _build_evolutionary_escape_audit(features: pd.DataFrame) -> pd.DataFrame:
    audit = pd.DataFrame(
        {
            "node_id": features["protein_id"],
            "gene_name": features.get("gene", pd.Series([""] * len(features), index=features.index)),
            "protein_id": features["protein_id"],
            "mutational_tolerance_score": _safe_series(features, "mutational_tolerance_score", 0.0),
            "redundancy_penalty": _safe_series(features, "redundancy_penalty", 0.0),
            "fitness_cost_score": _safe_series(features, "fitness_cost_score", 0.0),
            "compensation_difficulty_score": _safe_series(features, "compensation_difficulty_score", 0.0),
            "collateral_sensitivity_score": _safe_series(features, "collateral_sensitivity_score", 0.0),
            "biofilm_escape_penalty": _safe_series(features, "biofilm_escape_penalty", 0.0),
            "horizontal_transfer_penalty": _safe_series(features, "horizontal_transfer_penalty", 0.0),
            "evolutionary_escape_risk_score": _safe_series(features, "evolutionary_escape_risk_score", 0.0),
            "evolutionary_space_constraint_score": _safe_series(features, "evolutionary_space_constraint_score", 0.0),
            "audit_flags": features.get("audit_flags", pd.Series([""] * len(features), index=features.index)).fillna(""),
        }
    )
    return audit.sort_values("evolutionary_escape_risk_score", ascending=False).reset_index(drop=True)


def _build_phase3_user_report(phase3_ranking: pd.DataFrame, top_n: int = 10) -> str:
    included = phase3_ranking.get("included_in_therapeutic_ranking", pd.Series([True] * len(phase3_ranking), index=phase3_ranking.index)).fillna(True).astype(bool)
    real_ranking = phase3_ranking.loc[included].copy()
    demo_ranking = phase3_ranking.loc[~included].copy()
    lines = [
        "# Reporte Fase 3",
        "",
        "Este reporte separa score biologico, confianza de evidencia y limitaciones de procedencia. Un score alto con baja confianza sigue siendo exploratorio.",
        "",
        f"- Candidatos reales incluidos en ranking terapeutico: {len(real_ranking)}",
        f"- Registros demo/template excluidos: {len(demo_ranking)}",
        "- Ranking real separado: `results/ranking_nodos_phase3_real_candidates.csv`",
        "- Registros excluidos: `results/template_or_demo_records.csv`",
        "",
        "## Top candidatos reales",
        "",
    ]
    if real_ranking.empty:
        lines.extend(
            [
                "No hay candidatos reales incluidos. Todos los registros fueron demo/template o carecen de evidencia suficiente para ranking terapeutico real.",
                "",
            ]
        )
    for rank, (_, row) in enumerate(real_ranking.head(top_n).iterrows(), start=1):
        lines.extend(
            [
                f"### {int(row.get('rank_phase3_real_candidates', rank) or rank)}. {_node_label(row)}",
                "",
                f"- Score final Fase 3: `{_fmt(row.get('meta_priority_score_v3'))}`",
                f"- Rank real Fase 3: `{row.get('rank_phase3_real_candidates', 'not_reported')}`",
                f"- Rol Fase 3: `{row.get('therapeutic_role_v3', 'not_reported')}`",
                f"- Etiqueta de confianza: `{row.get('phase3_evidence_confidence_label', 'not_reported')}`",
                f"- Recomendacion: {row.get('phase3_recommendation', 'not_reported')}",
                f"- Razones para priorizar: {_phase3_positive_reasons(row)}",
                f"- Razones para penalizar: {_phase3_negative_reasons(row)}",
                f"- Evidencia real disponible: `{int(row.get('phase3_real_evidence_layer_count', 0) or 0)}` capas",
                f"- Evidencia faltante: `{row.get('phase3_evidence_gap_summary', 'not_reported')}`",
                f"- Capas demo/proxy/default: demo/default=`{int(row.get('phase3_demo_default_layer_count', 0) or 0)}`, proxy=`{int(row.get('phase3_proxy_layer_count', 0) or 0)}`",
                f"- Riesgo de homologia humana: `{_fmt(row.get('host_similarity_risk'))}`",
                f"- Riesgo de escape evolutivo: `{_fmt(row.get('evolutionary_escape_risk_score'))}`; estado `{row.get('evolutionary_escape_risk_status', 'not_reported')}`",
                f"- Soporte bibliografico: score=`{_fmt(row.get('literature_support_score'))}`; estado=`{row.get('literature_support_status', 'not_reported')}`; calidad_fuente=`{_fmt(row.get('literature_source_quality'))}`",
                f"- Interpretacion: {row.get('therapeutic_role_v3_reason', 'not_reported')}",
                "",
            ]
        )
    if not demo_ranking.empty:
        lines.extend(["## Registros demo/template excluidos", ""])
        for _, row in demo_ranking.head(top_n).iterrows():
            lines.extend(
                [
                    f"- {_node_label(row)}: Candidato excluido del ranking terapeutico por tratarse de registro demo/template (`{row.get('template_or_demo_reason', 'not_reported')}`).",
                ]
            )
        lines.append("")
    return "\n".join(lines)


def _phase3_positive_reasons(row: pd.Series) -> str:
    reasons = []
    for column in ["antibiotic_target_score", "antivirulence_target_score", "functional_node_theory_score", "literature_positive_score"]:
        if float(row.get(column, 0.0) or 0.0) >= 0.60:
            reasons.append(f"{column}={float(row.get(column)):.3f}")
    if int(row.get("phase3_real_evidence_layer_count", 0) or 0) >= 2:
        reasons.append("evidencia real convergente")
    return "; ".join(reasons) if reasons else "sin razones fuertes; revisar como exploratorio"


def _phase3_negative_reasons(row: pd.Series) -> str:
    reasons = []
    if bool(row.get("is_template_or_demo_record", False)):
        reasons.append("Candidato excluido del ranking terapeutico por tratarse de registro demo/template")
    if int(row.get("phase3_real_evidence_layer_count", 0) or 0) == 0:
        reasons.append("Score bajo por falta de evidencia real suficiente")
    if int(row.get("phase3_demo_default_layer_count", 0) or 0) > 0:
        reasons.append("Score bajo por uso predominante de demo/default/proxy")
    if float(row.get("host_similarity_risk", 0.0) or 0.0) >= 0.70:
        reasons.append("Score bajo por riesgo alto de similitud con hospedero")
    if float(row.get("evolutionary_escape_risk_score", 0.0) or 0.0) >= 0.65:
        reasons.append("Score bajo por alto riesgo de escape evolutivo")
    if float(row.get("literature_negative_score", 0.0) or 0.0) > 0:
        reasons.append("Score bajo por evidencia negativa real")
    if int(row.get("phase3_missing_layer_count", 0) or 0) > 0:
        reasons.append("evidencia faltante")
    return "; ".join(reasons) if reasons else "sin penalizaciones fuertes reportadas"


def _build_theory_of_nodes_report(features: pd.DataFrame, comparison: pd.DataFrame) -> str:
    top_v3 = features.sort_values("meta_priority_score_v3", ascending=False).head(10)
    top_constraint = features.sort_values("evolutionary_space_constraint_score", ascending=False).head(10)
    top_escape = features.sort_values("evolutionary_escape_risk_score", ascending=False).head(10)
    risers = comparison.sort_values("rank_delta", ascending=False).head(10)
    fallers = comparison.sort_values("rank_delta", ascending=True).head(10)
    warnings = _phase3_warning_lines(features)
    lines = [
        "# Theory of Functional Nodes Report",
        "",
        "## Resumen",
        "",
        f"- Organismo analizado: {str(features.get('organism', pd.Series(['not_reported'])).iloc[0]) if 'organism' in features.columns else 'not_reported'}",
        f"- Cepa analizada: {str(features.get('strain', pd.Series(['not_reported'])).iloc[0]) if 'strain' in features.columns else 'not_reported'}",
        f"- Nodos evaluados: {len(features)}",
        "",
        "## Que agrega Fase 3",
        "",
        (
            "Fase 3 agrega una lectura opcional de teoria de nodos funcionales: combina "
            "importancia funcional, esencialidad contextual, restriccion evolutiva, riesgo "
            "de escape, redundancia, sensibilidad colateral y calidad de evidencia. Estos "
            "resultados son hipotesis priorizadas y no sustituyen validacion experimental."
        ),
        "",
        "## Advertencias metodologicas",
        "",
        *warnings,
        "",
        "## Top 10 por meta_priority_score_v3",
        "",
        _markdown_table(_phase3_report_table(top_v3)),
        "",
        "## Top 10 por evolutionary_space_constraint_score",
        "",
        _markdown_table(_phase3_report_table(top_constraint)),
        "",
        "## Top 10 por evolutionary_escape_risk_score",
        "",
        _markdown_table(_phase3_report_table(top_escape)),
        "",
        "## Nodos que mas subieron respecto a Fase 2",
        "",
        _markdown_table(risers),
        "",
        "## Nodos que mas bajaron respecto a Fase 2",
        "",
        _markdown_table(fallers),
        "",
        "## Explicacion cientifica de los principales nodos",
        "",
    ]
    for rank, (_, row) in enumerate(top_v3.iterrows(), start=1):
        lines.extend(_phase3_node_explanation(rank, row))
    return "\n".join(lines)


def _build_top10_functional_node_theory_audit(features: pd.DataFrame) -> str:
    top = features.sort_values("functional_node_theory_score", ascending=False).head(10)
    lines = [
        "# Top 10 Functional Node Theory Audit",
        "",
        "Este reporte explica por que los mejores candidatos de Fase 3 parecen fuertes o limitados. Las recomendaciones son interpretativas y dependen de la evidencia disponible.",
        "",
    ]
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        label = _node_label(row)
        lines.extend(
            [
                f"## {rank}. {label}",
                "",
                f"- Rol terapeutico: {row.get('therapeutic_role_v3', 'not_reported')}",
                f"- Evidencia: calidad={_fmt(row.get('evidence_quality_score'))}; techo_confianza={_fmt(row.get('confidence_ceiling'))}; fuente={row.get('evidence_source_type', 'not_reported')}",
                f"- Justificacion funcional: functional_node_score={_fmt(row.get('functional_node_score'))}; teoria={_fmt(row.get('functional_node_theory_score'))}; etiqueta={row.get('functional_node_theory_label', 'not_reported')}",
                f"- Justificacion evolutiva: restriccion={_fmt(row.get('evolutionary_space_constraint_score'))}; costo_fitness={_fmt(row.get('fitness_cost_score'))}; dificultad_compensacion={_fmt(row.get('compensation_difficulty_score'))}",
                f"- Riesgo de escape: escape={_fmt(row.get('evolutionary_escape_risk_score'))}; tolerancia_mutacional={_fmt(row.get('mutational_tolerance_score'))}",
                f"- Redundancia: redundancy_penalty={_fmt(row.get('redundancy_penalty'))}",
                f"- Sensibilidad colateral: score={_fmt(row.get('collateral_sensitivity_score'))}; oportunidad={_fmt(row.get('combination_opportunity_score'))}",
                f"- Combinacion sugerida: {row.get('recommended_combination_class', 'unknown')} - {row.get('combination_rationale', 'not_reported')}",
                f"- Limitaciones: {row.get('audit_flags', 'not_reported')}",
                f"- Interpretacion final: {_scientific_interpretation(row)}",
                "",
            ]
        )
    return "\n".join(lines)


def _phase3_report_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "gene",
        "protein_id",
        "therapeutic_role_v3",
        "meta_priority_score_v3",
        "functional_node_theory_score",
        "evolutionary_space_constraint_score",
        "evolutionary_escape_risk_score",
        "redundancy_penalty",
        "evidence_quality_score",
        "confidence_ceiling",
        "recommended_combination_class",
        "combination_rationale",
        "audit_flags",
    ]
    return df[[column for column in columns if column in df.columns]].copy()


def _phase3_node_explanation(rank: int, row: pd.Series) -> list[str]:
    return [
        f"### {rank}. {_node_label(row)}",
        "",
        f"- Rol v3: {row.get('therapeutic_role_v3', 'not_reported')}",
        f"- meta_priority_score_v3: {_fmt(row.get('meta_priority_score_v3'))}",
        f"- functional_node_theory_score: {_fmt(row.get('functional_node_theory_score'))}",
        f"- evolutionary_space_constraint_score: {_fmt(row.get('evolutionary_space_constraint_score'))}",
        f"- evolutionary_escape_risk_score: {_fmt(row.get('evolutionary_escape_risk_score'))}",
        f"- redundancy_penalty: {_fmt(row.get('redundancy_penalty'))}",
        f"- evidence_quality_score: {_fmt(row.get('evidence_quality_score'))}",
        f"- confidence_ceiling: {_fmt(row.get('confidence_ceiling'))}",
        f"- recommended_combination_class: {row.get('recommended_combination_class', 'unknown')}",
        f"- combination_rationale: {row.get('combination_rationale', 'not_reported')}",
        f"- audit_flags: {row.get('audit_flags', 'not_reported')}",
        f"- Explicacion: {_scientific_interpretation(row)}",
        "",
    ]


def _phase3_warning_lines(features: pd.DataFrame) -> list[str]:
    audit = features.get("audit_flags", pd.Series([""] * len(features), index=features.index)).fillna("").astype(str)
    warnings = []
    demo_count = audit.str.contains("demo_data_used|demo", case=False, regex=True).sum()
    capped_count = audit.str.contains("confidence_capped|confidence_limited", case=False, regex=True).sum()
    missing_count = audit.str.contains("missing|not_assessed|no_strong_source", case=False, regex=True).sum()
    if demo_count:
        warnings.append(f"- Datos demo detectados en {demo_count} nodos; no deben interpretarse como evidencia biologica final.")
    if capped_count:
        warnings.append(f"- Confidence ceiling o limite de confianza aplicado en {capped_count} nodos.")
    if missing_count:
        warnings.append(f"- Evidencia faltante, inferida o no evaluada en {missing_count} nodos.")
    if not warnings:
        warnings.append("- No se detectaron advertencias globales fuertes en audit_flags.")
    return warnings


def _scientific_interpretation(row: pd.Series) -> str:
    if float(row.get("evolutionary_escape_risk_score", 0.0) or 0.0) >= 0.65:
        return "Nodo con senal funcional, pero con riesgo evolutivo alto; conviene revisar escape y combinaciones antes de priorizar."
    if float(row.get("redundancy_penalty", 0.0) or 0.0) >= 0.65:
        return "Nodo biologicamente interesante, pero la redundancia sugiere posibles rutas compensatorias."
    if float(row.get("evolutionary_space_constraint_score", 0.0) or 0.0) >= 0.70:
        return "Nodo con buena capacidad inferida para restringir rutas evolutivas viables, sujeto a la calidad de evidencia disponible."
    if float(row.get("evidence_quality_score", 0.0) or 0.0) < 0.35:
        return "La interpretacion esta limitada por evidencia debil, demo, inferida o incompleta."
    return "Nodo con soporte moderado dentro de Fase 3; debe revisarse junto con procedencia, confianza y contexto biologico."


def _node_label(row: pd.Series) -> str:
    gene = str(row.get("gene", "") or "").strip()
    protein = str(row.get("protein_id", "") or "").strip()
    return f"{gene}/{protein}" if gene else protein


def _fmt(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "not_reported"


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas para reportar._"
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].round(3)
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in display.iterrows():
        values = [str(row.get(column, "")).replace("\n", " ") for column in display.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _build_phase2_vs_phase3_comparison(features: pd.DataFrame) -> pd.DataFrame:
    phase2 = features.sort_values("meta_priority_score_v2", ascending=False).reset_index(drop=True)
    phase2["rank_phase2"] = range(1, len(phase2) + 1)
    phase3 = features.sort_values("meta_priority_score_v3", ascending=False).reset_index(drop=True)
    phase3["rank_phase3"] = range(1, len(phase3) + 1)
    comparison = phase2[["protein_id", "gene", "meta_priority_score_v2", "rank_phase2"]].merge(
        phase3[
            [
                "protein_id",
                "meta_priority_score_v3",
                "rank_phase3",
                "functional_node_theory_score",
                "evolutionary_escape_risk_score",
                "redundancy_penalty",
                "evolutionary_space_constraint_score",
                "combination_opportunity_score",
                "evidence_quality_score",
            ]
        ],
        on="protein_id",
        how="left",
    )
    comparison["node_id"] = comparison["protein_id"]
    comparison["gene_name"] = comparison["gene"]
    comparison["rank_delta"] = comparison["rank_phase2"] - comparison["rank_phase3"]
    comparison["main_reason_for_change"] = comparison.apply(_phase3_rank_change_reason, axis=1)
    return comparison[
        [
            "node_id",
            "gene_name",
            "protein_id",
            "meta_priority_score_v2",
            "meta_priority_score_v3",
            "rank_phase2",
            "rank_phase3",
            "rank_delta",
            "main_reason_for_change",
        ]
    ]


def _phase3_rank_change_reason(row: pd.Series) -> str:
    if float(row.get("evolutionary_escape_risk_score", 0.0) or 0.0) >= 0.65:
        return "high_evolutionary_escape_risk_penalty"
    if float(row.get("redundancy_penalty", 0.0) or 0.0) >= 0.65:
        return "high_redundancy_penalty"
    if float(row.get("evolutionary_space_constraint_score", 0.0) or 0.0) >= 0.70:
        return "high_evolutionary_constraint_support"
    if float(row.get("functional_node_theory_score", 0.0) or 0.0) >= 0.70:
        return "functional_node_theory_support"
    if float(row.get("combination_opportunity_score", 0.0) or 0.0) >= 0.65:
        return "combination_opportunity_support"
    if float(row.get("evidence_quality_score", 0.0) or 0.0) < 0.35:
        return "limited_evidence_quality"
    return "minor_weighting_shift"


def _phase3_audit_summary(row: pd.Series) -> str:
    return (
        f"v2={float(row.get('meta_priority_score_v2', 0.0)):.3f}; "
        f"v3={float(row.get('meta_priority_score_v3', 0.0)):.3f}; "
        f"theory={float(row.get('functional_node_theory_score', 0.0)):.3f}; "
        f"confidence={float(row.get('functional_node_theory_confidence', 0.0)):.3f}; "
        f"escape={float(row.get('evolutionary_escape_risk_score', 0.0)):.3f}; "
        f"redundancy={float(row.get('redundancy_penalty', 0.0)):.3f}; "
        f"role_v3={row.get('therapeutic_role_v3', 'not_reported')}"
    )


def compute_sensitivity(features: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    if not config["sensitivity"]["enabled"]:
        return pd.DataFrame(columns=["score_name", "scenario", "protein_id", "score", "rank", "rank_delta_vs_base"])
    therapeutic_thresholds = config["therapeutic_phase1"]["classification_thresholds"]

    def build_scenario_rows(
        score_name: str,
        base_score_column: str,
        input_columns: list[str],
        scenario_weights: dict[str, dict[str, float]],
    ) -> None:
        base = features[["protein_id", base_score_column]].sort_values(base_score_column, ascending=False).reset_index(drop=True)
        base["base_rank"] = base.index + 1
        for scenario_name, weights in scenario_weights.items():
            scenario_scores, _ = _weighted_score(features[input_columns], weights)
            scenario_df = pd.DataFrame(
                {
                    "score_name": score_name,
                    "scenario": scenario_name,
                    "protein_id": features["protein_id"],
                    "gene": features["gene"],
                    "score": scenario_scores.round(4),
                }
            ).sort_values("score", ascending=False).reset_index(drop=True)
            scenario_df["rank"] = scenario_df.index + 1
            scenario_df = scenario_df.merge(base[["protein_id", "base_rank"]], on="protein_id", how="left")
            scenario_df["rank_delta_vs_base"] = scenario_df["rank"] - scenario_df["base_rank"]
            scenario_df["therapeutic_role"] = ""
            scenario_df["role_changed_vs_base"] = False
            rows.append(scenario_df)

    build_scenario_rows(
        "meta_priority",
        "meta_priority_score",
        STRATEGY_SCORE_COLUMNS,
        {name: cfg["meta_priority"] for name, cfg in config["sensitivity"]["scenarios"].items()},
    )
    for score_name, base_column, weight_key in [
        ("antibiotic_target", "antibiotic_target_score", "antibiotic_target"),
        ("antivirulence_target", "antivirulence_target_score", "antivirulence_target"),
        ("functional_node", "functional_node_score", "functional_node"),
    ]:
        build_scenario_rows(
            score_name,
            base_column,
            list(config["weights"][weight_key].keys()),
            config["sensitivity"]["strategy_scenarios"].get(score_name, {}),
        )

    therapeutic_base = features[["protein_id", "therapeutic_priority_score", "therapeutic_role"]].sort_values(
        "therapeutic_priority_score",
        ascending=False,
    ).reset_index(drop=True)
    therapeutic_base["base_rank"] = therapeutic_base.index + 1
    for scenario_name, weights in config["sensitivity"].get("therapeutic_priority_scenarios", {}).items():
        scenario_scores, _ = _weighted_score(features, weights)
        scenario_features = features.copy()
        scenario_features["therapeutic_priority_score"] = scenario_scores
        scenario_roles = scenario_features.apply(lambda row: _classify_therapeutic_role(row, therapeutic_thresholds)[0], axis=1)
        scenario_df = pd.DataFrame(
            {
                "score_name": "therapeutic_priority",
                "scenario": scenario_name,
                "protein_id": features["protein_id"],
                "gene": features["gene"],
                "score": scenario_scores.round(4),
                "therapeutic_role": scenario_roles,
            }
        ).sort_values("score", ascending=False).reset_index(drop=True)
        scenario_df["rank"] = scenario_df.index + 1
        scenario_df = scenario_df.merge(
            therapeutic_base[["protein_id", "base_rank", "therapeutic_role"]].rename(columns={"therapeutic_role": "base_therapeutic_role"}),
            on="protein_id",
            how="left",
        )
        scenario_df["rank_delta_vs_base"] = scenario_df["rank"] - scenario_df["base_rank"]
        scenario_df["role_changed_vs_base"] = scenario_df["therapeutic_role"] != scenario_df["base_therapeutic_role"]
        rows.append(scenario_df)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
