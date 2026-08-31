from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_EVOLUTIONARY_ESCAPE_PARAMS: dict[str, object] = {
    "defaults": {
        "essentiality_score": 0.50,
        "contextual_essentiality_score": 0.50,
        "conservation_score": 0.50,
        "pleiotropy_score": 0.50,
        "redundancy_penalty": 0.50,
        "variant_burden": 0.50,
        "known_escape_mutation_score": 0.0,
        "inferred_functional_tolerance_score": 0.50,
        "module_participation_score": 0.50,
        "paralog_count_score": 0.50,
        "alternative_pathway_score": 0.50,
        "network_centrality": 0.50,
        "biofilm_escape_penalty": 0.0,
        "horizontal_transfer_penalty": 0.0,
        "collateral_sensitivity_score": 0.0,
    },
    "weights": {
        "mutational_tolerance_score": {
            "variant_burden": 0.30,
            "low_conservation_score": 0.25,
            "known_escape_mutation_score": 0.20,
            "low_essentiality_score": 0.15,
            "inferred_functional_tolerance_score": 0.10,
        },
        "fitness_cost_score": {
            "essentiality_score": 0.25,
            "conservation_score": 0.25,
            "pleiotropy_score": 0.20,
            "low_redundancy_score": 0.20,
            "module_participation_score": 0.10,
        },
        "compensation_difficulty_score": {
            "low_redundancy_score": 0.30,
            "low_paralog_score": 0.20,
            "low_alternative_pathway_score": 0.20,
            "network_centrality": 0.15,
            "contextual_essentiality_score": 0.15,
        },
        "evolutionary_escape_risk_score": {
            "mutational_tolerance_score": 0.25,
            "redundancy_penalty": 0.20,
            "biofilm_escape_penalty": 0.15,
            "horizontal_transfer_penalty": 0.15,
            "low_fitness_cost_score": 0.15,
            "low_compensation_difficulty_score": 0.10,
        },
        "evolutionary_space_constraint_score": {
            "conservation_score": 0.15,
            "max_essentiality_score": 0.15,
            "pleiotropy_score": 0.12,
            "fitness_cost_score": 0.14,
            "compensation_difficulty_score": 0.14,
            "collateral_sensitivity_score": 0.10,
            "low_redundancy_score": 0.08,
            "low_mutational_tolerance_score": 0.06,
            "low_biofilm_escape_penalty": 0.03,
            "low_horizontal_transfer_penalty": 0.03,
        },
    },
}


def compute_mutational_tolerance_score(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.Series:
    """Estimate how easily a node can tolerate mutations without losing viable function."""
    cfg = _evolutionary_config(params)
    essentiality = _essentiality_signal(df, cfg).where(_essentiality_known_mask(df))
    signals = pd.DataFrame(
        {
            "variant_burden": _signal(df, "variant_burden", cfg),
            "low_conservation_score": 1.0 - _signal(df, "conservation_score", cfg),
            "known_escape_mutation_score": _signal(df, "known_escape_mutation_score", cfg),
            "low_essentiality_score": 1.0 - essentiality,
            "inferred_functional_tolerance_score": _signal(df, "inferred_functional_tolerance_score", cfg),
        },
        index=df.index,
    )
    return _weighted_score(signals, _weights(cfg, "mutational_tolerance_score"))


def compute_fitness_cost_score(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.Series:
    """Estimate how costly successful escape would be for the pathogen."""
    cfg = _evolutionary_config(params)
    essentiality = _essentiality_signal(df, cfg).where(_essentiality_known_mask(df))
    signals = pd.DataFrame(
        {
            "essentiality_score": essentiality,
            "conservation_score": _signal(df, "conservation_score", cfg),
            "pleiotropy_score": _signal(df, "pleiotropy_score", cfg),
            "low_redundancy_score": 1.0 - _signal(df, "redundancy_penalty", cfg),
            "module_participation_score": _signal(df, "module_participation_score", cfg),
        },
        index=df.index,
    )
    return _weighted_score(signals, _weights(cfg, "fitness_cost_score"))


def compute_compensation_difficulty_score(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.Series:
    """Estimate how hard it is to bypass, replace, or compensate the node."""
    cfg = _evolutionary_config(params)
    signals = pd.DataFrame(
        {
            "low_redundancy_score": 1.0 - _signal(df, "redundancy_penalty", cfg),
            "low_paralog_score": 1.0 - _signal(df, "paralog_count_score", cfg),
            "low_alternative_pathway_score": 1.0 - _signal(df, "alternative_pathway_score", cfg),
            "network_centrality": _signal(df, "network_centrality", cfg),
            "contextual_essentiality_score": _signal(df, "contextual_essentiality_score", cfg),
        },
        index=df.index,
    )
    return _weighted_score(signals, _weights(cfg, "compensation_difficulty_score"))


def compute_evolutionary_escape_risk_score(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.Series:
    """Estimate the risk that viable resistance routes remain available."""
    cfg = _evolutionary_config(params)
    mutational_tolerance = _existing_or_computed(df, "mutational_tolerance_score", compute_mutational_tolerance_score, cfg)
    fitness_cost = _existing_or_computed(df, "fitness_cost_score", compute_fitness_cost_score, cfg)
    compensation_difficulty = _existing_or_computed(
        df,
        "compensation_difficulty_score",
        compute_compensation_difficulty_score,
        cfg,
    )
    signals = pd.DataFrame(
        {
            "mutational_tolerance_score": mutational_tolerance,
            "redundancy_penalty": _signal(df, "redundancy_penalty", cfg),
            "biofilm_escape_penalty": _signal(df, "biofilm_escape_penalty", cfg),
            "horizontal_transfer_penalty": _signal(df, "horizontal_transfer_penalty", cfg),
            "low_fitness_cost_score": 1.0 - fitness_cost,
            "low_compensation_difficulty_score": 1.0 - compensation_difficulty,
        },
        index=df.index,
    )
    return _weighted_score(signals, _weights(cfg, "evolutionary_escape_risk_score"))


def compute_evolutionary_space_constraint_score(
    df: pd.DataFrame,
    params: Mapping[str, object] | None = None,
) -> pd.Series:
    """Estimate how strongly the node restricts viable evolutionary escape routes."""
    cfg = _evolutionary_config(params)
    mutational_tolerance = _existing_or_computed(df, "mutational_tolerance_score", compute_mutational_tolerance_score, cfg)
    fitness_cost = _existing_or_computed(df, "fitness_cost_score", compute_fitness_cost_score, cfg)
    compensation_difficulty = _existing_or_computed(
        df,
        "compensation_difficulty_score",
        compute_compensation_difficulty_score,
        cfg,
    )
    contextual_essentiality = _signal(df, "contextual_essentiality_score", cfg)
    max_essentiality = pd.concat(
        [
            _essentiality_signal(df, cfg),
            contextual_essentiality,
        ],
        axis=1,
    ).max(axis=1)
    max_essentiality = max_essentiality.where(
        _essentiality_known_mask(df),
        contextual_essentiality,
    )
    signals = pd.DataFrame(
        {
            "conservation_score": _signal(df, "conservation_score", cfg),
            "max_essentiality_score": max_essentiality,
            "pleiotropy_score": _signal(df, "pleiotropy_score", cfg),
            "fitness_cost_score": fitness_cost,
            "compensation_difficulty_score": compensation_difficulty,
            "collateral_sensitivity_score": _signal(df, "collateral_sensitivity_score", cfg),
            "low_redundancy_score": 1.0 - _signal(df, "redundancy_penalty", cfg),
            "low_mutational_tolerance_score": 1.0 - mutational_tolerance,
            "low_biofilm_escape_penalty": 1.0 - _signal(df, "biofilm_escape_penalty", cfg),
            "low_horizontal_transfer_penalty": 1.0 - _signal(df, "horizontal_transfer_penalty", cfg),
        },
        index=df.index,
    )
    return _weighted_score(signals, _weights(cfg, "evolutionary_space_constraint_score"))


def compute_evolutionary_escape_features(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.DataFrame:
    """Return a copy of df with Phase 3 evolutionary escape features added.

    Missing optional inputs are imputed from explicit configuration defaults and
    recorded in audit_flags. Unknown experimental essentiality is instead omitted
    from formulas that explicitly consume it, with remaining weights renormalized.
    Existing user-supplied feature columns are kept.
    """
    result = df.copy()
    cfg = _evolutionary_config(params)
    result = _derive_template_escape_scores(result)
    missing_defaults = _missing_default_columns(result, cfg)

    result["mutational_tolerance_score"] = _existing_or_computed(
        result,
        "mutational_tolerance_score",
        compute_mutational_tolerance_score,
        cfg,
    )
    result["fitness_cost_score"] = _existing_or_computed(result, "fitness_cost_score", compute_fitness_cost_score, cfg)
    result["compensation_difficulty_score"] = _existing_or_computed(
        result,
        "compensation_difficulty_score",
        compute_compensation_difficulty_score,
        cfg,
    )
    result["evolutionary_escape_risk_score"] = compute_evolutionary_escape_risk_score(result, cfg)
    result["evolutionary_space_constraint_score"] = compute_evolutionary_space_constraint_score(result, cfg)

    for column in [
        "mutational_tolerance_score",
        "fitness_cost_score",
        "compensation_difficulty_score",
        "evolutionary_escape_risk_score",
        "evolutionary_space_constraint_score",
    ]:
        result[column] = _clamp01(pd.to_numeric(result[column], errors="coerce").fillna(0.0))

    result["audit_flags"] = _append_audit_flags(result, missing_defaults)
    return result


def _derive_template_escape_scores(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "paralog_count" in result.columns and "paralog_count_score" not in result.columns:
        result["paralog_count_score"] = (pd.to_numeric(result["paralog_count"], errors="coerce").fillna(0.0) / 5.0).clip(0.0, 1.0)
    if "alternative_pathways" in result.columns and "alternative_pathway_score" not in result.columns:
        result["alternative_pathway_score"] = (
            pd.to_numeric(result["alternative_pathways"], errors="coerce").fillna(0.0) / 5.0
        ).clip(0.0, 1.0)
    if "known_escape_mutations" in result.columns and "known_escape_mutation_score" not in result.columns:
        result["known_escape_mutation_score"] = (
            pd.to_numeric(result["known_escape_mutations"], errors="coerce").fillna(0.0) / 5.0
        ).clip(0.0, 1.0)
    if "module_participation_count" in result.columns and "module_participation_score" not in result.columns:
        result["module_participation_score"] = (
            pd.to_numeric(result["module_participation_count"], errors="coerce").fillna(0.0) / 5.0
        ).clip(0.0, 1.0)
    return result


def _evolutionary_config(params: Mapping[str, object] | None) -> dict[str, object]:
    phase3_cfg = _mapping_get(params or {}, "phase3")
    module_cfg = _mapping_get(phase3_cfg, "evolutionary_escape")
    return _deep_merge(DEFAULT_EVOLUTIONARY_ESCAPE_PARAMS, module_cfg)


def _mapping_get(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key, {}) if isinstance(mapping, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _deep_merge(base: Mapping[str, object], override: Mapping[str, object]) -> dict[str, object]:
    merged: dict[str, object] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _weights(cfg: Mapping[str, object], score_name: str) -> dict[str, float]:
    weights_cfg = _mapping_get(_mapping_get(cfg, "weights"), score_name)
    return {str(key): float(value) for key, value in weights_cfg.items()}


def _defaults(cfg: Mapping[str, object]) -> dict[str, float]:
    defaults_cfg = _mapping_get(cfg, "defaults")
    return {str(key): float(value) for key, value in defaults_cfg.items()}


def _signal(df: pd.DataFrame, column: str, cfg: Mapping[str, object]) -> pd.Series:
    default = _defaults(cfg).get(column, 0.0)
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return _clamp01(pd.to_numeric(df[column], errors="coerce").fillna(default))


def _essentiality_signal(df: pd.DataFrame, cfg: Mapping[str, object]) -> pd.Series:
    if "essentiality_score" in df.columns:
        return _signal(df, "essentiality_score", cfg)
    if "essential" in df.columns:
        essential = pd.to_numeric(df["essential"], errors="coerce").fillna(_defaults(cfg).get("essentiality_score", 0.5))
        return _clamp01(essential)
    return _signal(df, "essentiality_score", cfg)


def _essentiality_known_mask(df: pd.DataFrame) -> pd.Series:
    """Identify rows with an observed essentiality signal rather than an imputed midpoint."""
    if "essential" in df.columns:
        return pd.to_numeric(df["essential"], errors="coerce").notna()
    if "essentiality_score" in df.columns:
        return pd.to_numeric(df["essentiality_score"], errors="coerce").notna()
    return pd.Series([False] * len(df), index=df.index, dtype=bool)


def _weighted_score(signals: pd.DataFrame, weights: Mapping[str, float]) -> pd.Series:
    active = [column for column in weights if column in signals.columns]
    if not active:
        return pd.Series([0.0] * len(signals), index=signals.index, dtype=float)

    numerator = pd.Series([0.0] * len(signals), index=signals.index, dtype=float)
    denominator = pd.Series([0.0] * len(signals), index=signals.index, dtype=float)
    for column in active:
        weight = float(weights[column])
        numeric = pd.to_numeric(signals[column], errors="coerce")
        present = numeric.notna()
        numerator = numerator + numeric.fillna(0.0) * weight
        denominator = denominator + present.astype(float) * weight

    weighted = numerator / denominator.replace(0.0, pd.NA)
    return _clamp01(weighted.fillna(0.0))


def _existing_or_computed(
    df: pd.DataFrame,
    column: str,
    compute_fn,
    cfg: Mapping[str, object],
) -> pd.Series:
    if column in df.columns:
        return _clamp01(pd.to_numeric(df[column], errors="coerce").fillna(compute_fn(df, cfg)))
    return compute_fn(df, cfg)


def _missing_default_columns(df: pd.DataFrame, cfg: Mapping[str, object]) -> list[str]:
    score_inputs = {
        "essentiality_score",
        "contextual_essentiality_score",
        "conservation_score",
        "pleiotropy_score",
        "redundancy_penalty",
        "variant_burden",
        "known_escape_mutation_score",
        "inferred_functional_tolerance_score",
        "module_participation_score",
        "paralog_count_score",
        "alternative_pathway_score",
        "network_centrality",
        "biofilm_escape_penalty",
        "horizontal_transfer_penalty",
        "collateral_sensitivity_score",
    }
    if "essential" in df.columns:
        score_inputs.remove("essentiality_score")
    configured_defaults = set(_defaults(cfg))
    return sorted(column for column in score_inputs if column in configured_defaults and column not in df.columns)


def _append_audit_flags(df: pd.DataFrame, missing_default_columns: list[str]) -> pd.Series:
    default_flag = (
        "evolutionary_escape_defaults_used=" + "|".join(missing_default_columns)
        if missing_default_columns
        else "evolutionary_escape_all_inputs_present"
    )
    if "audit_flags" not in df.columns:
        return pd.Series([default_flag] * len(df), index=df.index, dtype=object)

    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return existing.map(lambda value: default_flag if value == "" else f"{value};{default_flag}")


def _clamp01(series: pd.Series) -> pd.Series:
    return series.astype(float).clip(lower=0.0, upper=1.0)
