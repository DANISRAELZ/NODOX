from __future__ import annotations

from typing import Callable

import pandas as pd

from .scoring_components import human_similarity_score


DEFAULT_NEUTRAL_HOST_RISK = 0.50


def continuous_host_similarity_risk(features: pd.DataFrame) -> pd.Series:
    """Return the DIAMOND-derived continuous sequence-similarity risk.

    Phase 2 already materializes ``human_similarity_score`` from the configured
    neutral score. Reuse it when present so Phase 3 does not reinterpret the
    binary ``human_homolog`` detection flag as maximal risk. The row-wise
    fallback exists for focused tests and legacy frames.

    This is a prioritization risk index, not a toxicity probability. Domain
    overlap and host criticality remain separate host-annotation signals and
    must not be collapsed into sequence-similarity risk.
    """
    if "human_similarity_score" in features.columns:
        return (
            pd.to_numeric(features["human_similarity_score"], errors="coerce")
            .fillna(DEFAULT_NEUTRAL_HOST_RISK)
            .clip(0.0, 1.0)
        )
    return features.apply(
        lambda row: human_similarity_score(row, DEFAULT_NEUTRAL_HOST_RISK),
        axis=1,
    ).astype(float).clip(0.0, 1.0)


def install_phase3_host_similarity_semantics() -> None:
    """Install the corrected semantics in the normal NODOX pipeline.

    ``scoring.build_phase3_scores`` historically calls a private helper that
    takes the maximum of ``human_homolog`` and several host signals. Because
    ``human_homolog`` is binary, every detected DIAMOND hit becomes risk=1.0.
    Rebind that helper to the continuous sequence-risk function while retaining
    ``human_homolog`` unchanged as an auditable detection flag.

    Phase 3 evidence auditing also historically marked both ``human_homolog``
    and ``host_similarity_risk`` as independent negative evidence. Change only
    the former's audit semantics so detection is reported but not double-counted
    as a second penalty. The continuous risk remains negative evidence when it
    crosses the configured high-risk threshold.

    The operation is idempotent and intentionally centralized here until the
    large scoring module is decomposed into public host-risk components.
    """
    from . import phase3_evidence
    from . import scoring

    scoring._compute_host_similarity_risk = continuous_host_similarity_risk

    corrected = []
    for item in phase3_evidence.LAYER_VARIABLES:
        if item.layer_name == "human_homologs" and item.variable_name == "human_homolog":
            corrected.append(
                phase3_evidence.LayerVariable(
                    item.layer_name,
                    item.variable_name,
                    negative_high=False,
                    negative_low=item.negative_low,
                )
            )
        else:
            corrected.append(item)
    phase3_evidence.LAYER_VARIABLES[:] = corrected


def installed_host_risk_callable() -> Callable[[pd.DataFrame], pd.Series]:
    """Expose the intended callable for regression/audit tests."""
    return continuous_host_similarity_risk
