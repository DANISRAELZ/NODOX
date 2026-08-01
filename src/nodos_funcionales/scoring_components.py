from __future__ import annotations

import math
from typing import Any

import pandas as pd


STRATEGY_SCORE_LABELS = {
    "antibiotic_target_score": "antibiotic_target",
    "antivirulence_target_score": "antivirulence_target",
    "functional_node_score": "functional_node",
}


HOMOLOGY_TIER_RISK_FLOORS = {
    "partial_human_sequence_similarity": 0.60,
    "strong_human_sequence_homology": 0.70,
}


def clamp_score(series: pd.Series, lower: float = 0.0, upper: float = 1.0) -> pd.Series:
    """Clamp numeric scores while keeping missing values conservative."""
    return pd.to_numeric(series, errors="coerce").clip(lower=lower, upper=upper).fillna(lower)


def validate_scoring_inputs(features: pd.DataFrame, required_columns: list[str] | None = None) -> None:
    required = required_columns or ["protein_id", "essential", "virulence_score", "human_homolog", "localization"]
    missing = [column for column in required if column not in features.columns]
    if missing:
        raise ValueError(
            "No se puede calcular scoring: faltan columnas requeridas "
            + ", ".join(f"`{column}`" for column in missing)
            + ". Ejecuta validacion, normalizacion e integracion antes de scoring."
        )


def weighted_score(df: pd.DataFrame, weights: dict[str, float], default: float = 0.5) -> tuple[pd.Series, dict[str, pd.Series]]:
    contributions: dict[str, pd.Series] = {}
    total_weight = sum(abs(value) for value in weights.values()) or 1.0
    for feature_name, weight in weights.items():
        feature = pd.to_numeric(df.get(feature_name, default), errors="coerce").fillna(default)
        contributions[feature_name] = feature * weight
    raw = sum(contributions.values()) / total_weight
    return clamp_score(raw), contributions


def calculate_legacy_score(
    features: pd.DataFrame,
    weights: dict[str, float],
    neutral_unknown_score: float,
    evalue_significance_threshold: float,
) -> pd.Series:
    legacy_no_human = features["human_homolog"].map(
        lambda value: 1.0 if pd.isna(value) else 1.0 - float(value)
    )
    legacy_host_risk = features.apply(
        lambda row: _legacy_host_risk(row, neutral_unknown_score, evalue_significance_threshold),
        axis=1,
    )
    return clamp_score(
        weights["essentiality"] * features["essentiality_support"]
        + weights["virulence"] * features["virulence_support"]
        + weights["no_human_homolog"] * legacy_no_human
        + weights["accessibility"] * features["physical_accessibility"]
        - weights["host_risk"] * legacy_host_risk
    )


def calculate_strategy_scores(
    features: pd.DataFrame,
    weights_config: dict[str, dict[str, float]],
) -> tuple[dict[str, pd.Series], dict[str, dict[str, pd.Series]]]:
    score_columns = {
        "antibiotic_target_score": "antibiotic_target",
        "antivirulence_target_score": "antivirulence_target",
        "functional_node_score": "functional_node",
    }
    scores: dict[str, pd.Series] = {}
    contributions: dict[str, dict[str, pd.Series]] = {}
    for output_column, config_key in score_columns.items():
        scores[output_column], contributions[output_column] = weighted_score(features, weights_config[config_key])
    return scores, contributions


def calculate_meta_priority_score(
    features: pd.DataFrame,
    weights: dict[str, float],
) -> tuple[pd.Series, dict[str, pd.Series]]:
    return weighted_score(features[list(weights.keys())].copy(), weights)


def assign_preferred_strategy(features: pd.DataFrame) -> pd.DataFrame:
    strategy_scores = features[list(STRATEGY_SCORE_LABELS)].copy()
    runner_up = strategy_scores.apply(lambda row: row.nlargest(2).iloc[-1], axis=1)
    return pd.DataFrame(
        {
            "preferred_strategy": strategy_scores.idxmax(axis=1).map(STRATEGY_SCORE_LABELS),
            "preferred_strategy_score": strategy_scores.max(axis=1),
            "runner_up_strategy_score": runner_up,
            "strategy_margin_score": (strategy_scores.max(axis=1) - runner_up).round(4),
        },
        index=features.index,
    )


def _legacy_host_risk(row: pd.Series, neutral_unknown_score: float, threshold: float) -> float:
    human_homolog = row.get("human_homolog")
    if pd.isna(human_homolog):
        return 0.0 if neutral_unknown_score < 1 else neutral_unknown_score
    if int(human_homolog) == 0:
        return 0.0
    evalue = row.get("evalue")
    if not pd.isna(evalue) and float(evalue) <= threshold:
        return 1.0
    return 0.5


def human_similarity_score(row: pd.Series, neutral_unknown_score: float) -> float:
    """Estimate host-similarity risk while respecting resolved DIAMOND tiers.

    The e-value supplies continuous information, but a resolved partial or
    strong human-homology classification must not appear safer than an
    unresolved, neutral host-risk state.
    """
    human_homolog = row.get("human_homolog")
    evalue = row.get("evalue")
    tier_value = row.get("homology_evidence_tier", "")
    tier = (
        ""
        if pd.isna(tier_value)
        else str(tier_value).strip().lower()
    )

    if pd.isna(human_homolog):
        return float(neutral_unknown_score)

    if int(human_homolog) == 0:
        return 0.0

    if pd.isna(evalue):
        raw_score = 0.60
    else:
        value = max(float(evalue), 1e-300)
        raw_score = -math.log10(value) / 50.0

    tier_floor = HOMOLOGY_TIER_RISK_FLOORS.get(tier)

    if tier_floor is not None:
        raw_score = max(
            raw_score,
            float(neutral_unknown_score),
            tier_floor,
        )

    return min(1.0, max(0.0, raw_score))
