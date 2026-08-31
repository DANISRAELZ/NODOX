from __future__ import annotations

import math
from typing import Any

import pandas as pd


STRATEGY_SCORE_LABELS = {
    "antibiotic_target_score": "antibiotic_target",
    "antivirulence_target_score": "antivirulence_target",
    "functional_node_score": "functional_node",
}


# Host-similarity risk is an interpretable alignment-risk index, not a calibrated
# probability of human toxicity. DIAMOND reports local alignments, so statistical
# significance alone must not turn a short/partial match into maximal host risk.
HOST_SIMILARITY_IDENTITY_BASELINE_PERCENT = 20.0
HOST_SIMILARITY_IDENTITY_HIGH_PERCENT = 60.0
HOST_SIMILARITY_EVALUE_BASELINE_LOG10 = 5.0
HOST_SIMILARITY_EVALUE_HIGH_LOG10 = 50.0
HOST_SIMILARITY_WEIGHTS = {
    "identity": 0.45,
    "coverage": 0.40,
    "significance": 0.15,
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


def weighted_score_omitting_unknown(
    df: pd.DataFrame,
    weights: dict[str, float],
    omit_masks: dict[str, pd.Series],
    default: float = 0.5,
) -> tuple[pd.Series, dict[str, pd.Series]]:
    """Score rows after removing selected epistemically unknown terms.

    This is intentionally row-wise: a missing biological signal is omitted from
    both numerator and denominator rather than being converted into a synthetic
    midpoint observation. Other configured defaults remain unchanged.
    """
    contributions: dict[str, pd.Series] = {}
    denominator = pd.Series(
        [sum(abs(value) for value in weights.values())] * len(df),
        index=df.index,
        dtype=float,
    )
    for feature_name, weight in weights.items():
        feature = pd.to_numeric(df.get(feature_name, default), errors="coerce").fillna(default)
        contribution = feature * weight
        omit = omit_masks.get(feature_name)
        if omit is not None:
            omit = omit.reindex(df.index).fillna(False).astype(bool)
            contribution = contribution.where(~omit, 0.0)
            denominator = denominator - omit.astype(float) * abs(float(weight))
        contributions[feature_name] = contribution
    raw = sum(contributions.values()) / denominator.replace(0.0, math.nan)
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
        weights = weights_config[config_key]
        if config_key == "antibiotic_target" and "essential" in features and "essentiality_support" in weights:
            essential_unknown = pd.to_numeric(features["essential"], errors="coerce").isna()
            scores[output_column], contributions[output_column] = weighted_score_omitting_unknown(
                features,
                weights,
                {"essentiality_support": essential_unknown},
            )
        else:
            scores[output_column], contributions[output_column] = weighted_score(features, weights)
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


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _coverage_fraction(value: object) -> float | None:
    """Return a coverage value on 0-1, accepting legacy percent-form inputs."""
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    result = float(numeric)
    if result > 1.0:
        result /= 100.0
    return _bounded(result)


def _identity_strength(percent_identity: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([percent_identity]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    pident = float(numeric)
    span = HOST_SIMILARITY_IDENTITY_HIGH_PERCENT - HOST_SIMILARITY_IDENTITY_BASELINE_PERCENT
    return _bounded((pident - HOST_SIMILARITY_IDENTITY_BASELINE_PERCENT) / span)


def _alignment_extent(query_coverage: object, subject_coverage: object) -> float | None:
    """Use geometric mean so one-sided local coverage cannot look globally extensive."""
    qcov = _coverage_fraction(query_coverage)
    scov = _coverage_fraction(subject_coverage)
    if qcov is None or scov is None:
        return None
    return math.sqrt(qcov * scov)


def _significance_strength(evalue: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([evalue]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    value = max(float(numeric), 1e-300)
    log_strength = -math.log10(value)
    span = HOST_SIMILARITY_EVALUE_HIGH_LOG10 - HOST_SIMILARITY_EVALUE_BASELINE_LOG10
    return _bounded((log_strength - HOST_SIMILARITY_EVALUE_BASELINE_LOG10) / span)


def human_similarity_score(row: pd.Series, neutral_unknown_score: float) -> float:
    """Estimate continuous host-similarity risk from a DIAMOND local alignment.

    ``human_homolog`` remains a detection/classification flag, while risk is
    derived from the alignment itself whenever DIAMOND has materialized all
    required dimensions. This matters for weak/low-coverage hits that are kept
    unresolved in the binary field but still contain real identity, coverage,
    and E-value evidence.

    Because DIAMOND performs local alignment, a very small e-value can arise for
    a conserved domain that covers only part of one or both proteins. Such a hit
    is retained as real evidence but does not automatically imply maximal
    off-target risk. The neutral score is reserved for genuinely incomplete
    alignment evidence.

    This score is a prioritization heuristic, not a probability of toxicity and
    not proof of functional equivalence to the human hit.
    """
    human_homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
    tier_value = row.get("homology_evidence_tier", "")
    tier = "" if pd.isna(tier_value) else str(tier_value).strip().lower()

    if pd.notna(human_homolog) and int(float(human_homolog)) == 0:
        return 0.0

    no_hit_tiers = {
        "no_detectable_human_similarity",
        "no_detectable_human_sequence_homology",
        "no_human_sequence_hit",
    }
    if tier in no_hit_tiers:
        return 0.0

    identity = _identity_strength(row.get("percent_identity"))
    extent = _alignment_extent(row.get("query_coverage"), row.get("subject_coverage"))
    significance = _significance_strength(row.get("evalue"))

    if identity is None or extent is None or significance is None:
        return float(neutral_unknown_score)

    risk = (
        HOST_SIMILARITY_WEIGHTS["identity"] * identity
        + HOST_SIMILARITY_WEIGHTS["coverage"] * extent
        + HOST_SIMILARITY_WEIGHTS["significance"] * significance
    )
    return _bounded(risk)
