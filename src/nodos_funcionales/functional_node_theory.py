from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_FUNCTIONAL_NODE_THEORY_PARAMS = {
    "weights": {
        "w_functional_node": 0.25,
        "w_contextual_essentiality": 0.18,
        "w_pleiotropy": 0.12,
        "w_conservation": 0.12,
        "w_evolutionary_constraint": 0.20,
        "w_evidence_quality": 0.13,
    },
    "penalties": {
        "p_redundancy": 0.18,
        "p_escape": 0.22,
        "p_biofilm": 0.10,
        "p_hgt": 0.10,
        "p_host_similarity": 0.12,
    },
    "defaults": {
        "functional_node_score": 0.0,
        "contextual_essentiality_score": 0.0,
        "pleiotropy_score": 0.0,
        "conservation_score": 0.0,
        "evolutionary_space_constraint_score": 0.0,
        "evidence_quality_score": 0.0,
        "redundancy_penalty": 0.0,
        "evolutionary_escape_risk_score": 0.0,
        "biofilm_escape_penalty": 0.0,
        "horizontal_transfer_penalty": 0.0,
        "host_similarity_penalty": 0.0,
        "confidence_ceiling": 1.0,
    },
    "label_thresholds": {
        "high_score": 0.75,
        "promising_score": 0.55,
        "minimum_evidence": 0.35,
        "high_escape_risk": 0.65,
        "high_redundancy": 0.65,
        "antivirulence_signal": 0.65,
    },
}

FUNCTIONAL_NODE_THEORY_AUDIT_COLUMNS = [
    "protein_id",
    "gene",
    "organism",
    "taxon_id",
    "strain",
    "functional_node_theory_score",
    "functional_node_theory_confidence",
    "functional_node_theory_label",
    "functional_node_therapeutic_exploitability_score",
    "meets_minimum_functional_node_evidence",
    "functional_impact_component",
    "dependency_component",
    "redundancy_constraint_component",
    "context_component",
    "host_safety_component",
    "evidence_quality_component",
    "curated_evidence_layers",
    "curated_evidence_references",
    "curated_evidence_notes",
    "curated_evidence_missing_layers",
    "curated_evidence_conflict_flags",
    "curated_evidence_summary",
    "audit_flags",
    "missing_evidence_flags",
    "interpretation",
]


def compute_functional_node_theory_score(
    df: pd.DataFrame,
    params: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Return a copy of df with functional node theory score, confidence, and labels.

    The biological score is normalized to 0-1. If confidence_ceiling is present,
    only the reported confidence is capped; the biological score remains an
    interpretable estimate of node strength.
    """
    result = df.copy()
    cfg = _theory_config(params)
    defaults = _defaults(cfg)
    missing_columns = _missing_columns(result, defaults)

    positive = _positive_score(result, cfg, defaults)
    penalty = _penalty_score(result, cfg, defaults)
    result["functional_node_theory_score"] = (positive - penalty).clip(lower=0.0, upper=1.0)
    result["functional_impact_component"] = _functional_impact_component(result, defaults)
    result["dependency_component"] = _dependency_component(result, defaults)
    result["redundancy_constraint_component"] = _redundancy_constraint_component(result, defaults)
    result["context_component"] = _context_component(result, defaults)
    result["host_safety_component"] = _host_safety_component(result, defaults)
    result["evidence_quality_component"] = _evidence_quality_component(result, defaults)
    result["functional_node_theory_confidence"] = _confidence(result, defaults)
    result["meets_minimum_functional_node_evidence"] = result.apply(meets_minimum_functional_node_evidence, axis=1)
    result["functional_node_therapeutic_exploitability_score"] = _functional_node_therapeutic_exploitability_score(result)
    result["functional_node_theory_label"] = result.apply(lambda row: _label(row, cfg), axis=1)
    result["audit_flags"] = _append_theory_audit_flags(result, missing_columns)
    result["missing_evidence_flags"] = _append_missing_evidence_flags(result)
    result["interpretation"] = result.apply(_interpretation, axis=1)
    return result


def meets_minimum_functional_node_evidence(row: pd.Series) -> bool:
    """Return True only when several independent dimensions support the node.

    This is deliberately conservative: unresolved, demo, placeholder, or
    provider-failure evidence can keep a numeric hypothesis score, but it cannot
    satisfy the operational definition of a supported Functional Node.
    """
    if _has_low_realism_or_unresolved_evidence(row):
        return False
    return (
        float(row.get("functional_impact_component", 0.0) or 0.0) >= 0.45
        and float(row.get("dependency_component", 0.0) or 0.0) >= 0.35
        and float(row.get("redundancy_constraint_component", 0.0) or 0.0) >= 0.35
        and float(row.get("evidence_quality_component", 0.0) or 0.0) >= 0.45
    )


def build_functional_node_theory_audit(df: pd.DataFrame) -> pd.DataFrame:
    """Build the candidate-level audit table required by theory reporting."""
    audit = df.copy()
    if "functional_node_theory_score" not in audit.columns:
        audit = compute_functional_node_theory_score(audit)
    columns = [column for column in FUNCTIONAL_NODE_THEORY_AUDIT_COLUMNS if column in audit.columns]
    return audit[columns].copy()


def _theory_config(params: Mapping[str, object] | None) -> dict[str, object]:
    phase3 = _mapping_get(params or {}, "phase3")
    theory = _mapping_get(phase3, "functional_node_theory")
    merged = _deep_merge(DEFAULT_FUNCTIONAL_NODE_THEORY_PARAMS, theory)
    legacy_scoring = _mapping_get(phase3, "scoring")
    legacy_weights = _mapping_get(legacy_scoring, "weights")
    legacy_penalties = _mapping_get(legacy_scoring, "penalties")
    if legacy_weights:
        mapped_weights = {
            "w_contextual_essentiality": legacy_weights.get("contextual_essentiality_score"),
            "w_pleiotropy": legacy_weights.get("pleiotropy_score"),
            "w_conservation": legacy_weights.get("conservation_score"),
            "w_evolutionary_constraint": legacy_weights.get("evolutionary_space_constraint_score"),
            "w_evidence_quality": legacy_weights.get("evidence_quality_score"),
        }
        merged["weights"].update({key: float(value) for key, value in mapped_weights.items() if value is not None})
    if legacy_penalties:
        mapped_penalties = {
            "p_redundancy": legacy_penalties.get("redundancy_penalty"),
            "p_escape": legacy_penalties.get("evolutionary_escape_risk_score"),
            "p_biofilm": legacy_penalties.get("biofilm_escape_penalty"),
            "p_hgt": legacy_penalties.get("horizontal_transfer_penalty"),
            "p_host_similarity": legacy_penalties.get("host_similarity_penalty"),
        }
        merged["penalties"].update({key: float(value) for key, value in mapped_penalties.items() if value is not None})
    return merged


def _mapping_get(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key, {}) if isinstance(mapping, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _deep_merge(base: Mapping[str, object], override: Mapping[str, object]) -> dict[str, object]:
    merged = {key: value.copy() if isinstance(value, dict) else value for key, value in base.items()}
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _defaults(cfg: Mapping[str, object]) -> dict[str, float]:
    return {str(key): float(value) for key, value in _mapping_get(cfg, "defaults").items()}


def _positive_score(df: pd.DataFrame, cfg: Mapping[str, object], defaults: Mapping[str, float]) -> pd.Series:
    weights = {str(key): float(value) for key, value in _mapping_get(cfg, "weights").items()}
    terms = {
        "w_functional_node": _signal(df, "functional_node_score", defaults),
        "w_contextual_essentiality": _signal(df, "contextual_essentiality_score", defaults),
        "w_pleiotropy": _signal(df, "pleiotropy_score", defaults),
        "w_conservation": _signal(df, "conservation_score", defaults),
        "w_evolutionary_constraint": _signal(df, "evolutionary_space_constraint_score", defaults),
        "w_evidence_quality": _signal(df, "evidence_quality_score", defaults),
    }
    total_weight = sum(max(weights.get(key, 0.0), 0.0) for key in terms)
    if total_weight <= 0:
        return pd.Series([0.0] * len(df), index=df.index, dtype=float)
    return sum(terms[key] * max(weights.get(key, 0.0), 0.0) for key in terms) / total_weight


def _penalty_score(df: pd.DataFrame, cfg: Mapping[str, object], defaults: Mapping[str, float]) -> pd.Series:
    penalties = {str(key): float(value) for key, value in _mapping_get(cfg, "penalties").items()}
    terms = {
        "p_redundancy": _signal(df, "redundancy_penalty", defaults),
        "p_escape": _signal(df, "evolutionary_escape_risk_score", defaults),
        "p_biofilm": _signal(df, "biofilm_escape_penalty", defaults),
        "p_hgt": _signal(df, "horizontal_transfer_penalty", defaults),
        "p_host_similarity": _signal(df, "host_similarity_penalty", defaults),
    }
    total_penalty_weight = sum(max(penalties.get(key, 0.0), 0.0) for key in terms)
    if total_penalty_weight <= 0:
        return pd.Series([0.0] * len(df), index=df.index, dtype=float)
    weighted_penalty = sum(terms[key] * max(penalties.get(key, 0.0), 0.0) for key in terms) / total_penalty_weight
    return weighted_penalty * min(total_penalty_weight, 1.0)


def _confidence(df: pd.DataFrame, defaults: Mapping[str, float]) -> pd.Series:
    evidence_quality = _evidence_quality_component(df, defaults)
    ceiling = _signal(df, "confidence_ceiling", defaults)
    source_ceiling = df.apply(_source_confidence_ceiling, axis=1)
    return evidence_quality.clip(upper=ceiling).clip(upper=source_ceiling).clip(lower=0.0, upper=1.0)


def _label(row: pd.Series, cfg: Mapping[str, object]) -> str:
    thresholds = {str(key): float(value) for key, value in _mapping_get(cfg, "label_thresholds").items()}
    score = float(row.get("functional_node_theory_score", 0.0))
    confidence = float(row.get("functional_node_theory_confidence", 0.0))

    if _has_unresolved_evidence(row):
        return "unresolved_evidence_candidate"
    if _has_low_realism_or_unresolved_evidence(row):
        return "hypothesis_only_insufficient_evidence"
    if not bool(row.get("meets_minimum_functional_node_evidence", False)):
        if score >= thresholds["promising_score"]:
            return "low_confidence_functional_node_candidate"
        return "not_supported_as_functional_node"
    if confidence < thresholds["minimum_evidence"]:
        return "hypothesis_only_insufficient_evidence"
    if score >= thresholds["high_score"] and confidence >= 0.70:
        return "high_confidence_functional_node"
    if score >= thresholds["promising_score"]:
        return "moderate_confidence_functional_node"
    return "low_confidence_functional_node_candidate"


def _functional_impact_component(df: pd.DataFrame, defaults: Mapping[str, float]) -> pd.Series:
    return _max_signal(
        df,
        defaults,
        ["functional_node_score", "network_centrality", "pathway_bottleneck_score", "functional_dependency_score"],
    )


def _dependency_component(df: pd.DataFrame, defaults: Mapping[str, float]) -> pd.Series:
    return _max_signal(
        df,
        defaults,
        [
            "essentiality_score",
            "essentiality",
            "contextual_essentiality_score",
            "virulence_score",
            "virulence_severity_score",
            "host_damage_score",
            "clinical_impact_score",
        ],
    )


def _redundancy_constraint_component(df: pd.DataFrame, defaults: Mapping[str, float]) -> pd.Series:
    redundancy_constraint = 1.0 - _signal(df, "redundancy_penalty", defaults)
    escape_constraint = 1.0 - _signal(df, "evolutionary_escape_risk_score", defaults)
    return pd.concat(
        [
            redundancy_constraint,
            escape_constraint,
            _signal(df, "strain_coverage_score", defaults),
            _signal(df, "conservation_score", defaults),
            _signal(df, "evolutionary_constraint_score", defaults),
            _signal(df, "evolutionary_space_constraint_score", defaults),
        ],
        axis=1,
    ).max(axis=1)


def _context_component(df: pd.DataFrame, defaults: Mapping[str, float]) -> pd.Series:
    return _max_signal(df, defaults, ["infection_context_score", "infection_site_access_score", "contextual_essentiality_score"])


def _host_safety_component(df: pd.DataFrame, defaults: Mapping[str, float]) -> pd.Series:
    host_similarity_risk = _signal(df, "host_similarity_risk", defaults)
    host_similarity_penalty = _signal(df, "host_similarity_penalty", defaults)
    return pd.concat(
        [
            _signal(df, "host_safety_score", defaults),
            1.0 - host_similarity_risk,
            1.0 - host_similarity_penalty,
        ],
        axis=1,
    ).max(axis=1)


def _evidence_quality_component(df: pd.DataFrame, defaults: Mapping[str, float]) -> pd.Series:
    base = _max_signal(df, defaults, ["evidence_quality_score", "evidence_confidence_score", "evidence_coverage_score"])
    layer_count = _signal(df, "real_evidence_layer_count", defaults).clip(upper=1.0)
    phase3_layer_count = _signal(df, "phase3_real_evidence_layer_count", defaults).clip(upper=1.0)
    return pd.concat([base, layer_count, phase3_layer_count], axis=1).max(axis=1)


def _functional_node_therapeutic_exploitability_score(df: pd.DataFrame) -> pd.Series:
    access = _signal(df, "infection_site_access_score", {"infection_site_access_score": 0.0})
    selectivity = _signal(df, "selectivity_score", {"selectivity_score": 0.0})
    host_safety = _signal(df, "host_safety_component", {"host_safety_component": 0.0})
    theory = _signal(df, "functional_node_theory_score", {"functional_node_theory_score": 0.0})
    confidence = _signal(df, "functional_node_theory_confidence", {"functional_node_theory_confidence": 0.0})
    exploitability_context = (access + selectivity + host_safety) / 3.0
    return (theory * confidence * exploitability_context).clip(lower=0.0, upper=1.0)


def _max_signal(df: pd.DataFrame, defaults: Mapping[str, float], columns: list[str]) -> pd.Series:
    signals = [_signal(df, column, defaults) for column in columns]
    return pd.concat(signals, axis=1).max(axis=1)


def _source_confidence_ceiling(row: pd.Series) -> float:
    if _has_demo_or_placeholder_evidence(row):
        return 0.25
    if "curated_fixture" in _row_text(row):
        return 0.65
    if _has_unresolved_evidence(row):
        return 0.30
    if _has_missing_provider_evidence(row):
        return 0.40
    if _has_controlled_context_evidence(row):
        return 0.55
    return 1.0


def _has_low_realism_or_unresolved_evidence(row: pd.Series) -> bool:
    return (
        _has_demo_or_placeholder_evidence(row)
        or _has_unresolved_evidence(row)
        or _has_missing_provider_evidence(row)
        or _has_controlled_context_evidence(row)
    )


def _has_demo_or_placeholder_evidence(row: pd.Series) -> bool:
    text = _row_text(row)
    return any(token in text for token in ["demo_only", "placeholder", "placeholder_only", "template_or_demo"])


def _has_unresolved_evidence(row: pd.Series) -> bool:
    if _has_curated_multilayer_support(row):
        return False
    text = _row_text(row)
    return "unresolved" in text


def _has_missing_provider_evidence(row: pd.Series) -> bool:
    if _has_curated_multilayer_support(row):
        return False
    text = _row_text(row)
    return any(token in text for token in ["provider_not_implemented", "provider_not_found", "missing_optional_layer"])


def _has_controlled_context_evidence(row: pd.Series) -> bool:
    if _has_curated_multilayer_support(row):
        return False
    return "controlled_context" in _row_text(row)


def _has_curated_multilayer_support(row: pd.Series) -> bool:
    layer_count = float(row.get("curated_real_evidence_layer_count", 0.0) or 0.0)
    confidence = float(row.get("curated_evidence_confidence", 0.0) or 0.0)
    return layer_count >= 3 and confidence >= 0.5


def _row_text(row: pd.Series) -> str:
    fields = [
        "data_realism_flag",
        "evidence_level",
        "source_used",
        "retrieval_status",
        "provenance_status",
        "evidence_source",
        "audit_flags",
        "missing_evidence_flags",
        "ranking_inclusion_status",
        "ranking_inclusion_reason",
        "template_or_demo_reason",
        "phase3_evidence_gap_summary",
        "phase3_evidence_explanation",
        "clinical_impact_input_status",
        "curated_disease_context_input_status",
        "therapy_site_context_input_status",
    ]
    return " ".join(str(row.get(field, "") or "").casefold() for field in fields)


def _append_missing_evidence_flags(df: pd.DataFrame) -> pd.Series:
    generated = []
    for _, row in df.iterrows():
        flags = []
        if not bool(row.get("meets_minimum_functional_node_evidence", False)):
            flags.append("functional_node_minimum_evidence_not_met")
        if _has_demo_or_placeholder_evidence(row):
            flags.append("demo_or_placeholder_evidence")
        if _has_unresolved_evidence(row):
            flags.append("unresolved_evidence")
        if _has_missing_provider_evidence(row):
            flags.append("provider_or_optional_layer_missing")
        if _has_controlled_context_evidence(row):
            flags.append("controlled_context_evidence")
        if not flags:
            flags.append("functional_node_minimum_evidence_met")
        generated.append(";".join(flags))
    new_flags = pd.Series(generated, index=df.index, dtype=object)
    if "missing_evidence_flags" not in df.columns:
        return new_flags
    existing = df["missing_evidence_flags"].fillna("").astype(str).str.strip()
    return pd.Series(
        [flag if current == "" else f"{current};{flag}" for current, flag in zip(existing, new_flags, strict=False)],
        index=df.index,
        dtype=object,
    )


def _interpretation(row: pd.Series) -> str:
    label = str(row.get("functional_node_theory_label", "not_supported_as_functional_node"))
    if label == "high_confidence_functional_node":
        return "Evidence supports a functional node interpretation across impact, dependency, constraint, and provenance dimensions."
    if label == "moderate_confidence_functional_node":
        return "The candidate has multi-layer support, but confidence remains moderate and requires targeted validation."
    if label in {"hypothesis_only_insufficient_evidence", "unresolved_evidence_candidate"}:
        return "Computational hypothesis only: unresolved, demo, placeholder, controlled, or provider-limited evidence prevents a robust node claim."
    if label == "low_confidence_functional_node_candidate":
        return "Possible functional node candidate, but minimum evidence is incomplete or confidence is low."
    return "Current evidence does not support declaring this candidate a Functional Node."


def _missing_columns(df: pd.DataFrame, defaults: Mapping[str, float]) -> list[str]:
    expected = [
        "functional_node_score",
        "contextual_essentiality_score",
        "pleiotropy_score",
        "conservation_score",
        "evolutionary_space_constraint_score",
        "evidence_quality_score",
        "redundancy_penalty",
        "evolutionary_escape_risk_score",
        "biofilm_escape_penalty",
        "horizontal_transfer_penalty",
        "host_similarity_penalty",
    ]
    return [column for column in expected if column in defaults and column not in df.columns]


def _append_theory_audit_flags(df: pd.DataFrame, missing_columns: list[str]) -> pd.Series:
    flags_by_row = []
    confidence_limited = _signal(df, "evidence_quality_score", {"evidence_quality_score": 0.0}).gt(
        _signal(df, "confidence_ceiling", {"confidence_ceiling": 1.0})
    )
    for idx in df.index:
        flags = []
        applied_penalties = [
            name
            for name in [
                "redundancy_penalty",
                "evolutionary_escape_risk_score",
                "biofilm_escape_penalty",
                "horizontal_transfer_penalty",
                "host_similarity_penalty",
            ]
            if float(df.loc[idx].get(name, 0.0) or 0.0) > 0
        ]
        if applied_penalties:
            flags.append("functional_node_theory_penalties=" + "|".join(applied_penalties))
        if missing_columns:
            flags.append("functional_node_theory_missing=" + "|".join(missing_columns))
        if bool(confidence_limited.loc[idx]):
            flags.append("functional_node_theory_confidence_limited")
        if float(df.loc[idx].get("evolutionary_escape_risk_score", 0.0) or 0.0) >= 0.65:
            flags.append("functional_node_theory_high_evolutionary_risk")
        if float(df.loc[idx].get("redundancy_penalty", 0.0) or 0.0) >= 0.65:
            flags.append("functional_node_theory_high_redundancy")
        if not flags:
            flags.append("functional_node_theory_no_major_penalty")
        flags_by_row.append(";".join(flags))

    new_flags = pd.Series(flags_by_row, index=df.index, dtype=object)
    if "audit_flags" not in df.columns:
        return new_flags
    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return pd.Series(
        [
            flag if current == "" else f"{current};{flag}"
            for current, flag in zip(existing, new_flags, strict=False)
        ],
        index=df.index,
        dtype=object,
    )


def _signal(df: pd.DataFrame, column: str, defaults: Mapping[str, float]) -> pd.Series:
    default = float(defaults.get(column, 0.0))
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float).clip(lower=0.0, upper=1.0)
