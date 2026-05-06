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
    result["functional_node_theory_confidence"] = _confidence(result, defaults)
    result["functional_node_theory_label"] = result.apply(lambda row: _label(row, cfg), axis=1)
    result["audit_flags"] = _append_theory_audit_flags(result, missing_columns)
    return result


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
    evidence_quality = _signal(df, "evidence_quality_score", defaults)
    ceiling = _signal(df, "confidence_ceiling", defaults)
    return evidence_quality.clip(upper=ceiling).clip(lower=0.0, upper=1.0)


def _label(row: pd.Series, cfg: Mapping[str, object]) -> str:
    thresholds = {str(key): float(value) for key, value in _mapping_get(cfg, "label_thresholds").items()}
    score = float(row.get("functional_node_theory_score", 0.0))
    confidence = float(row.get("functional_node_theory_confidence", 0.0))
    escape = float(row.get("evolutionary_escape_risk_score", 0.0))
    redundancy = float(row.get("redundancy_penalty", 0.0))
    antivirulence = max(
        float(row.get("antivirulence_target_score", 0.0) or 0.0),
        float(row.get("virulence_severity_score", 0.0) or 0.0),
    )

    if confidence < thresholds["minimum_evidence"]:
        return "insufficient_evidence"
    if redundancy >= thresholds["high_redundancy"]:
        return "central_but_redundant"
    if escape >= thresholds["high_escape_risk"]:
        return "promising_but_evolutionary_risk"
    if antivirulence >= thresholds["antivirulence_signal"] and score >= thresholds["promising_score"]:
        return "antivirulence_candidate"
    if score >= thresholds["high_score"]:
        return "high_confidence_functional_node"
    if score >= thresholds["promising_score"]:
        return "promising_but_evolutionary_risk"
    return "weak_candidate"


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
