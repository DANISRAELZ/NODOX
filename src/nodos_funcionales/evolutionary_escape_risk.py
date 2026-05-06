from __future__ import annotations

import math
from typing import Any

import pandas as pd


RISK_INPUT_COLUMNS = [
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
]

RISK_FORMULA_COLUMNS = [
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "resistance_emergence_risk",
    "inverse_fitness_cost_of_escape",
    "inverse_evolutionary_constraint_score",
    "inverse_multi_node_dependency_score",
]

DEFAULT_EVOLUTIONARY_ESCAPE_RISK_CONFIG = {
    "enabled": True,
    "minimum_available_variables": 3,
    "penalty_weight": 0.15,
    "apply_to_meta_priority": False,
    "weights": {
        "mutation_tolerance_score": 0.20,
        "functional_redundancy_escape_score": 0.15,
        "compensatory_pathway_score": 0.15,
        "resistance_emergence_risk": 0.20,
        "inverse_fitness_cost_of_escape": 0.10,
        "inverse_evolutionary_constraint_score": 0.10,
        "inverse_multi_node_dependency_score": 0.10,
    },
    "reduced_space_weights": {
        "evolutionary_constraint_score": 0.25,
        "fitness_cost_of_escape": 0.25,
        "multi_node_dependency_score": 0.20,
        "inverse_functional_redundancy_escape_score": 0.15,
        "inverse_compensatory_pathway_score": 0.15,
    },
}


def _mapping_get(mapping: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if isinstance(mapping, dict):
        return mapping.get(key, default)
    return default


def _config(params: dict[str, Any] | None) -> dict[str, Any]:
    raw = _mapping_get(params or {}, "evolutionary_escape_risk", {})
    merged = {
        **DEFAULT_EVOLUTIONARY_ESCAPE_RISK_CONFIG,
        **(raw if isinstance(raw, dict) else {}),
    }
    merged["weights"] = {
        **DEFAULT_EVOLUTIONARY_ESCAPE_RISK_CONFIG["weights"],
        **(_mapping_get(raw, "weights", {}) if isinstance(raw, dict) else {}),
    }
    merged["reduced_space_weights"] = {
        **DEFAULT_EVOLUTIONARY_ESCAPE_RISK_CONFIG["reduced_space_weights"],
        **(_mapping_get(raw, "reduced_space_weights", {}) if isinstance(raw, dict) else {}),
    }
    return merged


def _series(df: pd.DataFrame, column: str, default: float = math.nan) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _text_series(df: pd.DataFrame, column: str, default: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="string")
    return df[column].fillna(default).astype(str)


def _clamp(series: pd.Series, lower: float = 0.0, upper: float = 1.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").clip(lower=lower, upper=upper)


def _weighted_mean(values: dict[str, pd.Series], weights: dict[str, float], default: float = 0.5) -> pd.Series:
    numerator = pd.Series([0.0] * len(next(iter(values.values()))), index=next(iter(values.values())).index)
    denominator = pd.Series([0.0] * len(numerator), index=numerator.index)
    for column, series in values.items():
        weight = float(weights.get(column, 0.0))
        if weight <= 0:
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        present = numeric.notna()
        numerator = numerator + numeric.fillna(0.0) * weight
        denominator = denominator + present.astype(float) * weight
    return _clamp((numerator / denominator.replace(0.0, math.nan)).fillna(default))


def _first_available(df: pd.DataFrame, columns: list[str], default: float = math.nan) -> pd.Series:
    available = [pd.to_numeric(df[column], errors="coerce") for column in columns if column in df.columns]
    if not available:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.concat(available, axis=1).bfill(axis=1).iloc[:, 0]


def _source_label(row: pd.Series) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    derived = int(row.get("evolutionary_escape_risk_available_variable_count", 0)) - explicit
    source_type = str(row.get("evolutionary_escape_risk_input_source_type", "") or "").strip()
    if source_type and source_type.lower() not in {"nan", "not_reported"}:
        return source_type
    if explicit:
        return "user_or_curated"
    if derived > 0:
        return "derived"
    return "proxy"


def _confidence_label(row: pd.Series, minimum_available: int) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    available = int(row.get("evolutionary_escape_risk_available_variable_count", 0))
    input_confidence = str(row.get("evolutionary_escape_risk_input_confidence", "") or "").strip().lower()
    if explicit == 0:
        return "low"
    if input_confidence in {"high", "moderate", "medium", "low"} and explicit >= minimum_available:
        return "moderate" if input_confidence == "medium" else input_confidence
    if explicit >= 5:
        return "high"
    if explicit >= minimum_available or available >= 5:
        return "moderate"
    return "low"


def _status_label(row: pd.Series, minimum_available: int) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    available = int(row.get("evolutionary_escape_risk_available_variable_count", 0))
    if explicit == 0:
        return "unknown_missing_evidence"
    if explicit >= minimum_available:
        return "sufficient_evidence"
    if available >= minimum_available:
        return "derived_from_related_layers"
    return "insufficient_evidence"


def _interpretation(row: pd.Series) -> str:
    status = str(row.get("evolutionary_escape_risk_status", "") or "")
    if status == "unknown_missing_evidence":
        return "Riesgo desconocido: no hay evidencia explicita suficiente; no debe interpretarse como riesgo bajo."
    risk = float(row.get("evolutionary_escape_risk_score", 0.0))
    if risk < 0.35:
        return (
            "Riesgo bajo: alta restriccion evolutiva, baja redundancia funcional "
            "o alto costo adaptativo estimado reducen el espacio de escape."
        )
    if risk < 0.65:
        return (
            "Riesgo moderado: conserva valor terapeutico, pero hay senales parciales "
            "de tolerancia mutacional, redundancia o rutas compensatorias."
        )
    return (
        "Riesgo alto: el candidato podria escapar por tolerancia mutacional, "
        "redundancia funcional, rutas compensatorias o bajo costo adaptativo."
    )


def compute_evolutionary_escape_risk_features(df: pd.DataFrame, params: dict[str, Any] | None) -> pd.DataFrame:
    result = df.copy()
    if "evolutionary_escape_risk_source_type" in result.columns and "evolutionary_escape_risk_layer_source_type" not in result.columns:
        result["evolutionary_escape_risk_layer_source_type"] = result["evolutionary_escape_risk_source_type"]
    if "evolutionary_escape_risk_confidence" in result.columns and "evolutionary_escape_risk_layer_confidence" not in result.columns:
        result["evolutionary_escape_risk_layer_confidence"] = pd.to_numeric(
            result["evolutionary_escape_risk_confidence"],
            errors="coerce",
        )
    cfg = _config(params)
    enabled = bool(cfg.get("enabled", True))

    explicit_values = {
        column: _series(result, column)
        for column in RISK_INPUT_COLUMNS
    }
    explicit_values["mutation_tolerance_score"] = explicit_values["mutation_tolerance_score"].combine_first(
        _series(result, "mutational_tolerance_score")
    )

    derived = {
        "mutation_tolerance_score": _clamp(
            0.55 * _series(result, "variant_burden", 0.5).fillna(0.5)
            + 0.45 * (1.0 - _series(result, "conservation_score", 0.5).fillna(0.5))
        ),
        "functional_redundancy_escape_score": _clamp(
            _first_available(result, ["redundancy_penalty", "functional_backup_score"], 0.5).fillna(0.5)
        ),
        "compensatory_pathway_score": _clamp(
            pd.concat(
                [
                    _series(result, "alternative_pathway_score", 0.5),
                    _series(result, "metabolic_bypass_score", 0.5),
                    _series(result, "regulatory_bypass_score", 0.5),
                    (_series(result, "pathway_alternative_count", 0.0).fillna(0.0) / 5.0),
                ],
                axis=1,
            ).max(axis=1)
        ),
        "fitness_cost_of_escape": _clamp(
            0.40 * _series(result, "essentiality_support", 0.5).fillna(0.5)
            + 0.25 * _series(result, "conservation_score", 0.5).fillna(0.5)
            + 0.20 * _series(result, "low_redundancy_score", 0.5).fillna(0.5)
            + 0.15 * _series(result, "fitness_cost_score", 0.5).fillna(0.5)
        ),
        "evolutionary_constraint_score": _clamp(
            _first_available(result, ["evolutionary_space_constraint_score"], math.nan).combine_first(
                0.35 * _series(result, "conservation_score", 0.5).fillna(0.5)
                + 0.25 * _series(result, "essentiality_support", 0.5).fillna(0.5)
                + 0.20 * _series(result, "low_redundancy_score", 0.5).fillna(0.5)
                + 0.20 * _series(result, "functional_impact_score", 0.5).fillna(0.5)
            )
        ),
        "multi_node_dependency_score": _clamp(
            pd.concat(
                [
                    _series(result, "functional_dependency_score", 0.5),
                    _series(result, "functional_impact_score", 0.5),
                    _series(result, "network_centrality", 0.5),
                    _series(result, "pathway_bottleneck_score", 0.5),
                    _series(result, "module_participation_score", 0.5),
                ],
                axis=1,
            ).mean(axis=1)
        ),
    }
    derived["resistance_emergence_risk"] = _clamp(
        0.30 * explicit_values["mutation_tolerance_score"].combine_first(derived["mutation_tolerance_score"])
        + 0.25 * explicit_values["functional_redundancy_escape_score"].combine_first(derived["functional_redundancy_escape_score"])
        + 0.25 * explicit_values["compensatory_pathway_score"].combine_first(derived["compensatory_pathway_score"])
        + 0.20 * (1.0 - explicit_values["fitness_cost_of_escape"].combine_first(derived["fitness_cost_of_escape"]))
    )

    availability = {}
    for column in RISK_INPUT_COLUMNS:
        explicit = explicit_values[column].notna()
        value = explicit_values[column].combine_first(derived[column])
        result[column] = _clamp(value.fillna(0.5))
        result[f"{column}_is_explicit"] = explicit
        result[f"{column}_source_type"] = explicit.map(lambda flag: "user_or_curated" if flag else "derived")
        availability[column] = result[column].notna()

    explicit_count = pd.DataFrame({column: explicit_values[column].notna() for column in RISK_INPUT_COLUMNS}).sum(axis=1)
    available_count = pd.DataFrame(availability).sum(axis=1)
    result["evolutionary_escape_risk_explicit_variable_count"] = explicit_count.astype(int)
    result["evolutionary_escape_risk_available_variable_count"] = available_count.astype(int)
    result["evolutionary_escape_risk_missing_variables"] = pd.DataFrame(
        {
            column: explicit_values[column].notna()
            for column in RISK_INPUT_COLUMNS
        }
    ).apply(
        lambda row: "; ".join([column for column in RISK_INPUT_COLUMNS if not bool(row[column])]) or "none",
        axis=1,
    )
    result["evolutionary_escape_risk_available_variables"] = pd.DataFrame(
        {
            column: explicit_values[column].notna()
            for column in RISK_INPUT_COLUMNS
        }
    ).apply(
        lambda row: "; ".join([column for column in RISK_INPUT_COLUMNS if bool(row[column])]) or "none",
        axis=1,
    )
    result["evolutionary_escape_risk_input_source_type"] = _text_series(
        result,
        "evolutionary_escape_risk_input_source_type",
        "not_reported",
    )
    result["evolutionary_escape_risk_evidence_source"] = _text_series(
        result,
        "evolutionary_escape_risk_evidence_source",
        "not_reported",
    )
    result["evolutionary_escape_risk_input_confidence"] = _text_series(
        result,
        "evolutionary_escape_risk_input_confidence",
        "not_reported",
    )
    result["evolutionary_escape_risk_notes"] = _text_series(
        result,
        "evolutionary_escape_risk_notes",
        "not_reported",
    )

    if not enabled:
        result["evolutionary_escape_risk_score"] = 0.0
        result["evolutionary_robustness_score"] = 1.0
        result["reduced_evolutionary_space_score"] = 0.0
        result["evolutionary_escape_penalty_applied"] = 0.0
        result["evolutionary_adjusted_meta_priority_score"] = _series(result, "meta_priority_score", 0.0).fillna(0.0)
        result["evolutionary_escape_risk_confidence"] = "disabled"
        result["evolutionary_escape_risk_status"] = "disabled"
        result["evolutionary_escape_risk_source_type"] = "disabled"
        result["evolutionary_escape_risk_interpretation"] = "Subcapa desactivada por configuracion."
        return result

    formula_values = {
        "mutation_tolerance_score": result["mutation_tolerance_score"],
        "functional_redundancy_escape_score": result["functional_redundancy_escape_score"],
        "compensatory_pathway_score": result["compensatory_pathway_score"],
        "resistance_emergence_risk": result["resistance_emergence_risk"],
        "inverse_fitness_cost_of_escape": 1.0 - result["fitness_cost_of_escape"],
        "inverse_evolutionary_constraint_score": 1.0 - result["evolutionary_constraint_score"],
        "inverse_multi_node_dependency_score": 1.0 - result["multi_node_dependency_score"],
    }
    result["evolutionary_escape_risk_score"] = _weighted_mean(formula_values, cfg["weights"], default=0.5)
    result["evolutionary_robustness_score"] = _clamp(1.0 - result["evolutionary_escape_risk_score"])

    reduced_values = {
        "evolutionary_constraint_score": result["evolutionary_constraint_score"],
        "fitness_cost_of_escape": result["fitness_cost_of_escape"],
        "multi_node_dependency_score": result["multi_node_dependency_score"],
        "inverse_functional_redundancy_escape_score": 1.0 - result["functional_redundancy_escape_score"],
        "inverse_compensatory_pathway_score": 1.0 - result["compensatory_pathway_score"],
    }
    result["reduced_evolutionary_space_score"] = _weighted_mean(
        reduced_values,
        cfg["reduced_space_weights"],
        default=0.5,
    )

    penalty_weight = max(0.0, min(1.0, float(cfg.get("penalty_weight", 0.15))))
    result["evolutionary_escape_penalty_applied"] = _clamp(
        penalty_weight * result["evolutionary_escape_risk_score"],
        0.0,
        penalty_weight,
    )
    base_meta = _series(result, "meta_priority_score", 0.0).fillna(0.0)
    adjusted = _clamp(base_meta * (1.0 - result["evolutionary_escape_penalty_applied"]))
    result["evolutionary_adjusted_meta_priority_score"] = adjusted
    if bool(cfg.get("apply_to_meta_priority", False)):
        result["meta_priority_score"] = adjusted

    minimum_available = int(cfg.get("minimum_available_variables", 3))
    result["evolutionary_escape_risk_confidence"] = result.apply(
        lambda row: _confidence_label(row, minimum_available),
        axis=1,
    )
    result["evolutionary_escape_risk_status"] = result.apply(
        lambda row: _status_label(row, minimum_available),
        axis=1,
    )
    result["evolutionary_escape_risk_source_type"] = result.apply(_source_label, axis=1)
    result["evolutionary_escape_risk_interpretation"] = result.apply(_interpretation, axis=1)
    result["evolutionary_escape_risk_audit_summary"] = (
        "risk="
        + result["evolutionary_escape_risk_score"].round(3).astype(str)
        + "; confidence="
        + result["evolutionary_escape_risk_confidence"].astype(str)
        + "; status="
        + result["evolutionary_escape_risk_status"].astype(str)
        + "; penalty="
        + result["evolutionary_escape_penalty_applied"].round(3).astype(str)
    )
    return result
