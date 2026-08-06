
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

EXPLICIT_SOURCE_TYPES = {
    "user",
    "user_supplied",
    "user_or_curated",
    "user_curated",
    "curated",
    "literature",
    "literature_curated",
    "experimental",
    "external_real",
    "real_external",
    "real_external_online",
    "versioned_snapshot",
    "computed_from_real_data",
}

NON_EXPLICIT_SOURCE_TYPES = {
    "",
    "nan",
    "none",
    "missing",
    "not_reported",
    "unknown",
    "unresolved",
    "derived",
    "proxy",
    "proxy_inference",
    "proxy_hypothesis_only",
    "controlled",
    "controlled_provider",
    "default",
    "default_value",
    "demo",
    "demo_data",
    "template",
    "placeholder",
}

DEFAULT_EVOLUTIONARY_ESCAPE_RISK_CONFIG = {
    "enabled": True,
    "minimum_available_variables": 3,
    "minimum_explicit_variables": 3,
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
    if "minimum_explicit_variables" not in merged:
        merged["minimum_explicit_variables"] = int(merged.get("minimum_available_variables", 3))
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


def _weighted_mean(
    values: dict[str, pd.Series],
    weights: dict[str, float],
    default: float = 0.5,
) -> pd.Series:
    first = next(iter(values.values()))
    numerator = pd.Series([0.0] * len(first), index=first.index, dtype=float)
    denominator = pd.Series([0.0] * len(first), index=first.index, dtype=float)
    for column, series in values.items():
        weight = float(weights.get(column, 0.0))
        if weight <= 0:
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        present = numeric.notna()
        numerator = numerator + numeric.fillna(0.0) * weight
        denominator = denominator + present.astype(float) * weight
    score = numerator / denominator.replace(0.0, math.nan)
    if not math.isnan(default):
        score = score.fillna(default)
    return _clamp(score)


def _first_available(
    df: pd.DataFrame,
    columns: list[str],
    default: float = math.nan,
) -> pd.Series:
    available = [
        pd.to_numeric(df[column], errors="coerce")
        for column in columns
        if column in df.columns
    ]
    if not available:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.concat(available, axis=1).bfill(axis=1).iloc[:, 0]


def _bool_series(df: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in df.columns:
        return None
    values = df[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    normalized = values.fillna("").astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y", "explicit", "supported"})


def _normalized_source_series(df: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in df.columns:
        return None
    return df[column].fillna("").astype(str).str.strip().str.lower()


def _source_explicit_mask(source: pd.Series, values: pd.Series) -> pd.Series:
    explicit = source.isin(EXPLICIT_SOURCE_TYPES)
    non_explicit = source.isin(NON_EXPLICIT_SOURCE_TYPES)
    fallback = values.notna() & ~(explicit | non_explicit)
    return values.notna() & (explicit | fallback)


def _explicit_input_mask(
    df: pd.DataFrame,
    column: str,
    values: pd.Series,
) -> pd.Series:
    explicit_flag = _bool_series(df, f"{column}_is_explicit")
    if explicit_flag is not None:
        return values.notna() & explicit_flag

    source = _normalized_source_series(df, f"{column}_source_type")
    if source is not None:
        return _source_explicit_mask(source, values)

    for source_column in [
        "evolutionary_escape_risk_input_source_type",
        "source_type",
        "evidence_source_type",
    ]:
        source = _normalized_source_series(df, source_column)
        if source is not None:
            return _source_explicit_mask(source, values)

    # Backward compatibility: a direct numeric input without provenance columns
    # is treated as user-provided. Upstream derived values should carry an
    # explicit false flag or a derived/proxy source type.
    return values.notna()


def _input_value_and_mask(
    df: pd.DataFrame,
    column: str,
    alias: str | None = None,
) -> tuple[pd.Series, pd.Series]:
    primary = _series(df, column)
    primary_mask = _explicit_input_mask(df, column, primary)
    if not alias:
        return primary, primary_mask

    alternate = _series(df, alias)
    alternate_mask = _explicit_input_mask(df, alias, alternate)
    combined = primary.combine_first(alternate)
    combined_mask = primary_mask | (primary.isna() & alternate_mask)
    return combined, combined_mask


def _source_label(row: pd.Series) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    derived = (
        int(row.get("evolutionary_escape_risk_available_variable_count", 0))
        - explicit
    )
    source_type = str(
        row.get("evolutionary_escape_risk_input_source_type", "") or ""
    ).strip()
    if source_type and source_type.lower() not in {"nan", "not_reported"}:
        return source_type
    if explicit:
        return "user_or_curated"
    if derived > 0:
        return "derived"
    return "proxy"


def _confidence_label(row: pd.Series, minimum_explicit: int) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    available = int(row.get("evolutionary_escape_risk_available_variable_count", 0))
    input_confidence = str(
        row.get("evolutionary_escape_risk_input_confidence", "") or ""
    ).strip().lower()
    if explicit == 0:
        return "low"
    if (
        input_confidence in {"high", "moderate", "medium", "low"}
        and explicit >= minimum_explicit
    ):
        return "moderate" if input_confidence == "medium" else input_confidence
    if explicit >= 5:
        return "high"
    if explicit >= minimum_explicit or available >= 5:
        return "moderate"
    return "low"


def _status_label(row: pd.Series, minimum_explicit: int) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    available = int(row.get("evolutionary_escape_risk_available_variable_count", 0))
    if explicit == 0:
        return "unknown_missing_evidence"
    if explicit >= minimum_explicit:
        return "sufficient_evidence"
    if available >= minimum_explicit:
        return "derived_from_related_layers"
    return "insufficient_evidence"


def _evidence_mode_label(row: pd.Series, minimum_explicit: int) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    available = int(row.get("evolutionary_escape_risk_available_variable_count", 0))
    if explicit >= minimum_explicit:
        return "supported"
    if explicit > 0:
        return "insufficient_explicit_evidence_proxy_only"
    if available > 0:
        return "proxy_hypothesis_only"
    return "unknown_missing_evidence"


def _supported_status_label(row: pd.Series, minimum_explicit: int) -> str:
    explicit = int(row.get("evolutionary_escape_risk_explicit_variable_count", 0))
    if explicit >= minimum_explicit:
        return "sufficient_explicit_evidence"
    if explicit > 0:
        return "insufficient_explicit_evidence"
    return "unknown_missing_evidence"


def _interpretation(row: pd.Series) -> str:
    status = str(row.get("evolutionary_escape_risk_status", "") or "")
    if status == "unknown_missing_evidence":
        return (
            "Riesgo desconocido: no hay evidencia explicita suficiente; "
            "no debe interpretarse como riesgo bajo."
        )
    if status in {"derived_from_related_layers", "insufficient_evidence"}:
        return (
            "Hipotesis proxy: el valor deriva de capas relacionadas y no "
            "constituye evidencia evolutiva explicita ni validacion predictiva."
        )
    risk = float(row.get("evolutionary_escape_risk_score", 0.0))
    if risk < 0.35:
        return (
            "Riesgo bajo bajo la evidencia explicita disponible: alta "
            "restriccion evolutiva, baja redundancia funcional o alto costo "
            "adaptativo estimado reducen el espacio de escape."
        )
    if risk < 0.65:
        return (
            "Riesgo moderado bajo la evidencia explicita disponible: hay "
            "senales parciales de tolerancia mutacional, redundancia o rutas "
            "compensatorias."
        )
    return (
        "Riesgo alto bajo la evidencia explicita disponible: el candidato "
        "podria conservar rutas de escape por tolerancia mutacional, "
        "redundancia funcional, compensacion o bajo costo adaptativo."
    )


def _supported_interpretation(row: pd.Series) -> str:
    mode = str(row.get("evolutionary_escape_evidence_mode", "") or "")
    if mode == "supported":
        score = pd.to_numeric(
            pd.Series([row.get("evolutionary_escape_supported_score")]),
            errors="coerce",
        ).iloc[0]
        if pd.isna(score):
            return "Evidencia explicita suficiente, pero el score respaldado no pudo calcularse."
        if float(score) < 0.35:
            return "Riesgo respaldado bajo dentro de la evidencia explicita disponible."
        if float(score) < 0.65:
            return "Riesgo respaldado moderado dentro de la evidencia explicita disponible."
        return "Riesgo respaldado alto dentro de la evidencia explicita disponible."
    if mode == "insufficient_explicit_evidence_proxy_only":
        return (
            "Existen variables explicitas, pero no alcanzan el umbral; "
            "el score respaldado permanece no evaluable."
        )
    if mode == "proxy_hypothesis_only":
        return (
            "Solo hay señales derivadas o proxy; el score respaldado permanece "
            "no evaluable y no aplica penalizacion respaldada."
        )
    return "Riesgo respaldado no evaluable por ausencia de evidencia explicita."


def compute_evolutionary_escape_risk_features(
    df: pd.DataFrame,
    params: dict[str, Any] | None,
) -> pd.DataFrame:
    result = df.copy()
    if (
        "evolutionary_escape_risk_source_type" in result.columns
        and "evolutionary_escape_risk_layer_source_type" not in result.columns
    ):
        result["evolutionary_escape_risk_layer_source_type"] = result[
            "evolutionary_escape_risk_source_type"
        ]
    if (
        "evolutionary_escape_risk_confidence" in result.columns
        and "evolutionary_escape_risk_layer_confidence" not in result.columns
    ):
        result["evolutionary_escape_risk_layer_confidence"] = pd.to_numeric(
            result["evolutionary_escape_risk_confidence"],
            errors="coerce",
        )
    cfg = _config(params)
    enabled = bool(cfg.get("enabled", True))

    input_values: dict[str, pd.Series] = {}
    explicit_masks: dict[str, pd.Series] = {}
    for column in RISK_INPUT_COLUMNS:
        alias = "mutational_tolerance_score" if column == "mutation_tolerance_score" else None
        value, mask = _input_value_and_mask(result, column, alias=alias)
        input_values[column] = value
        explicit_masks[column] = mask

    explicit_values = {
        column: input_values[column].where(explicit_masks[column])
        for column in RISK_INPUT_COLUMNS
    }

    derived = {
        "mutation_tolerance_score": _clamp(
            0.55 * _series(result, "variant_burden", 0.5).fillna(0.5)
            + 0.45
            * (1.0 - _series(result, "conservation_score", 0.5).fillna(0.5))
        ),
        "functional_redundancy_escape_score": _clamp(
            _first_available(
                result,
                ["redundancy_penalty", "functional_backup_score"],
                0.5,
            ).fillna(0.5)
        ),
        "compensatory_pathway_score": _clamp(
            pd.concat(
                [
                    _series(result, "alternative_pathway_score", 0.5),
                    _series(result, "metabolic_bypass_score", 0.5),
                    _series(result, "regulatory_bypass_score", 0.5),
                    (
                        _series(result, "pathway_alternative_count", 0.0)
                        .fillna(0.0)
                        / 5.0
                    ),
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
            _first_available(
                result,
                ["evolutionary_space_constraint_score"],
                math.nan,
            ).combine_first(
                0.35 * _series(result, "conservation_score", 0.5).fillna(0.5)
                + 0.25
                * _series(result, "essentiality_support", 0.5).fillna(0.5)
                + 0.20
                * _series(result, "low_redundancy_score", 0.5).fillna(0.5)
                + 0.20
                * _series(result, "functional_impact_score", 0.5).fillna(0.5)
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
        0.30
        * input_values["mutation_tolerance_score"].combine_first(
            derived["mutation_tolerance_score"]
        )
        + 0.25
        * input_values["functional_redundancy_escape_score"].combine_first(
            derived["functional_redundancy_escape_score"]
        )
        + 0.25
        * input_values["compensatory_pathway_score"].combine_first(
            derived["compensatory_pathway_score"]
        )
        + 0.20
        * (
            1.0
            - input_values["fitness_cost_of_escape"].combine_first(
                derived["fitness_cost_of_escape"]
            )
        )
    )

    proxy_values: dict[str, pd.Series] = {}
    for column in RISK_INPUT_COLUMNS:
        value = input_values[column].combine_first(derived[column])
        proxy_values[column] = _clamp(value.fillna(0.5))
        result[column] = proxy_values[column]
        result[f"{column}_is_explicit"] = explicit_masks[column]
        existing_source = _normalized_source_series(
            df,
            f"{column}_source_type",
        )
        if existing_source is None:
            result[f"{column}_source_type"] = explicit_masks[column].map(
                lambda flag: "user_or_curated" if flag else "derived"
            )
        else:
            result[f"{column}_source_type"] = existing_source.where(
                existing_source.ne(""),
                explicit_masks[column].map(
                    lambda flag: "user_or_curated" if flag else "derived"
                ),
            )

    explicit_frame = pd.DataFrame(explicit_masks)
    proxy_frame = pd.DataFrame(
        {column: proxy_values[column].notna() for column in RISK_INPUT_COLUMNS}
    )
    explicit_count = explicit_frame.sum(axis=1)
    available_count = proxy_frame.sum(axis=1)

    result["evolutionary_escape_risk_explicit_variable_count"] = (
        explicit_count.astype(int)
    )
    result["evolutionary_escape_risk_available_variable_count"] = (
        available_count.astype(int)
    )
    result["evolutionary_escape_risk_missing_variables"] = explicit_frame.apply(
        lambda row: "; ".join(
            [column for column in RISK_INPUT_COLUMNS if not bool(row[column])]
        )
        or "none",
        axis=1,
    )
    explicit_variable_text = explicit_frame.apply(
        lambda row: "; ".join(
            [column for column in RISK_INPUT_COLUMNS if bool(row[column])]
        )
        or "none",
        axis=1,
    )
    result["evolutionary_escape_risk_available_variables"] = explicit_variable_text
    result["evolutionary_escape_risk_explicit_variables"] = explicit_variable_text
    result["evolutionary_escape_risk_proxy_available_variables"] = proxy_frame.apply(
        lambda row: "; ".join(
            [column for column in RISK_INPUT_COLUMNS if bool(row[column])]
        )
        or "none",
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

    base_meta = _series(result, "meta_priority_score", 0.0).fillna(0.0)
    if not enabled:
        result["evolutionary_escape_risk_score"] = 0.0
        result["evolutionary_escape_proxy_score"] = 0.0
        result["evolutionary_escape_supported_score"] = math.nan
        result["evolutionary_robustness_score"] = 1.0
        result["reduced_evolutionary_space_score"] = 0.0
        result["evolutionary_escape_penalty_applied"] = 0.0
        result["evolutionary_escape_proxy_penalty_applied"] = 0.0
        result["evolutionary_escape_supported_penalty_applied"] = 0.0
        result["evolutionary_adjusted_meta_priority_score"] = base_meta
        result["evolutionary_proxy_adjusted_meta_priority_score"] = base_meta
        result["evolutionary_supported_adjusted_meta_priority_score"] = base_meta
        result["evolutionary_escape_risk_confidence"] = "disabled"
        result["evolutionary_escape_risk_status"] = "disabled"
        result["evolutionary_escape_risk_source_type"] = "disabled"
        result["evolutionary_escape_evidence_mode"] = "disabled"
        result["evolutionary_escape_supported_status"] = "disabled"
        result["evolutionary_escape_risk_interpretation"] = (
            "Subcapa desactivada por configuracion."
        )
        result["evolutionary_escape_supported_interpretation"] = (
            "Subcapa desactivada por configuracion."
        )
        result["evolutionary_escape_risk_audit_summary"] = (
            "risk=0.0; supported=nan; mode=disabled; penalty=0.0"
        )
        return result

    formula_values = {
        "mutation_tolerance_score": result["mutation_tolerance_score"],
        "functional_redundancy_escape_score": result[
            "functional_redundancy_escape_score"
        ],
        "compensatory_pathway_score": result["compensatory_pathway_score"],
        "resistance_emergence_risk": result["resistance_emergence_risk"],
        "inverse_fitness_cost_of_escape": 1.0
        - result["fitness_cost_of_escape"],
        "inverse_evolutionary_constraint_score": 1.0
        - result["evolutionary_constraint_score"],
        "inverse_multi_node_dependency_score": 1.0
        - result["multi_node_dependency_score"],
    }
    proxy_score = _weighted_mean(formula_values, cfg["weights"], default=0.5)
    result["evolutionary_escape_risk_score"] = proxy_score
    result["evolutionary_escape_proxy_score"] = proxy_score
    result["evolutionary_robustness_score"] = _clamp(1.0 - proxy_score)

    reduced_values = {
        "evolutionary_constraint_score": result["evolutionary_constraint_score"],
        "fitness_cost_of_escape": result["fitness_cost_of_escape"],
        "multi_node_dependency_score": result["multi_node_dependency_score"],
        "inverse_functional_redundancy_escape_score": 1.0
        - result["functional_redundancy_escape_score"],
        "inverse_compensatory_pathway_score": 1.0
        - result["compensatory_pathway_score"],
    }
    result["reduced_evolutionary_space_score"] = _weighted_mean(
        reduced_values,
        cfg["reduced_space_weights"],
        default=0.5,
    )

    minimum_explicit = int(
        cfg.get(
            "minimum_explicit_variables",
            cfg.get("minimum_available_variables", 3),
        )
    )
    supported_formula_values = {
        "mutation_tolerance_score": explicit_values["mutation_tolerance_score"],
        "functional_redundancy_escape_score": explicit_values[
            "functional_redundancy_escape_score"
        ],
        "compensatory_pathway_score": explicit_values[
            "compensatory_pathway_score"
        ],
        "resistance_emergence_risk": explicit_values[
            "resistance_emergence_risk"
        ],
        "inverse_fitness_cost_of_escape": 1.0
        - explicit_values["fitness_cost_of_escape"],
        "inverse_evolutionary_constraint_score": 1.0
        - explicit_values["evolutionary_constraint_score"],
        "inverse_multi_node_dependency_score": 1.0
        - explicit_values["multi_node_dependency_score"],
    }
    supported_raw = _weighted_mean(
        supported_formula_values,
        cfg["weights"],
        default=math.nan,
    )
    supported_mask = explicit_count >= minimum_explicit
    result["evolutionary_escape_supported_score"] = supported_raw.where(
        supported_mask,
        math.nan,
    )

    penalty_weight = max(
        0.0,
        min(1.0, float(cfg.get("penalty_weight", 0.15))),
    )
    proxy_penalty = _clamp(
        penalty_weight * proxy_score,
        0.0,
        penalty_weight,
    )
    supported_penalty = _clamp(
        penalty_weight
        * result["evolutionary_escape_supported_score"].fillna(0.0),
        0.0,
        penalty_weight,
    )
    result["evolutionary_escape_penalty_applied"] = proxy_penalty
    result["evolutionary_escape_proxy_penalty_applied"] = proxy_penalty
    result["evolutionary_escape_supported_penalty_applied"] = supported_penalty

    proxy_adjusted = _clamp(base_meta * (1.0 - proxy_penalty))
    supported_adjusted = _clamp(base_meta * (1.0 - supported_penalty))
    result["evolutionary_adjusted_meta_priority_score"] = proxy_adjusted
    result["evolutionary_proxy_adjusted_meta_priority_score"] = proxy_adjusted
    result["evolutionary_supported_adjusted_meta_priority_score"] = (
        supported_adjusted
    )
    if bool(cfg.get("apply_to_meta_priority", False)):
        result["meta_priority_score"] = proxy_adjusted

    result["evolutionary_escape_risk_confidence"] = result.apply(
        lambda row: _confidence_label(row, minimum_explicit),
        axis=1,
    )
    result["evolutionary_escape_risk_status"] = result.apply(
        lambda row: _status_label(row, minimum_explicit),
        axis=1,
    )
    result["evolutionary_escape_risk_source_type"] = result.apply(
        _source_label,
        axis=1,
    )
    result["evolutionary_escape_evidence_mode"] = result.apply(
        lambda row: _evidence_mode_label(row, minimum_explicit),
        axis=1,
    )
    result["evolutionary_escape_supported_status"] = result.apply(
        lambda row: _supported_status_label(row, minimum_explicit),
        axis=1,
    )
    result["evolutionary_escape_risk_interpretation"] = result.apply(
        _interpretation,
        axis=1,
    )
    result["evolutionary_escape_supported_interpretation"] = result.apply(
        _supported_interpretation,
        axis=1,
    )
    result["evolutionary_escape_risk_audit_summary"] = (
        "proxy_risk="
        + result["evolutionary_escape_proxy_score"].round(3).astype(str)
        + "; supported_risk="
        + result["evolutionary_escape_supported_score"].round(3).astype(str)
        + "; confidence="
        + result["evolutionary_escape_risk_confidence"].astype(str)
        + "; status="
        + result["evolutionary_escape_risk_status"].astype(str)
        + "; mode="
        + result["evolutionary_escape_evidence_mode"].astype(str)
        + "; proxy_penalty="
        + result["evolutionary_escape_proxy_penalty_applied"].round(3).astype(str)
        + "; supported_penalty="
        + result["evolutionary_escape_supported_penalty_applied"].round(3).astype(str)
    )
    return result
