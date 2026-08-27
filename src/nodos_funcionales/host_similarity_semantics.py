from __future__ import annotations

from typing import Callable

import pandas as pd

from .scoring_components import human_similarity_score


DEFAULT_NEUTRAL_HOST_RISK = 0.50
_REQUIRED_ALIGNMENT_COLUMNS = (
    "percent_identity",
    "query_coverage",
    "subject_coverage",
    "evalue",
)
_NO_HIT_TIERS = {
    "no_detectable_human_similarity",
    "no_detectable_human_sequence_homology",
    "no_human_sequence_hit",
}


def _has_complete_alignment(row: pd.Series) -> bool:
    return all(pd.notna(pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]) for column in _REQUIRED_ALIGNMENT_COLUMNS)


def _is_explicit_no_hit(row: pd.Series) -> bool:
    homolog = pd.to_numeric(pd.Series([row.get("human_homolog")]), errors="coerce").iloc[0]
    if pd.notna(homolog) and int(float(homolog)) == 0:
        return True
    tier_value = row.get("homology_evidence_tier", "")
    tier = "" if pd.isna(tier_value) else str(tier_value).strip().lower()
    return tier in _NO_HIT_TIERS


def continuous_host_similarity_risk(features: pd.DataFrame) -> pd.Series:
    """Return the current DIAMOND-derived continuous sequence-similarity risk.

    Prefer recomputation from raw alignment dimensions whenever they are present,
    even if ``human_similarity_score`` was materialized by an older scoring
    implementation. This prevents Phase 3-only recomputation from preserving a
    stale neutral value for weak/low-coverage DIAMOND hits after scoring-semantics
    fixes.

    Explicit no-hit records are always recomputed as risk 0.0. Rows without a
    complete alignment keep a previously materialized score when available;
    otherwise they fall back to the neutral unresolved risk.

    This is a prioritization risk index, not a toxicity probability. Domain
    overlap and host criticality remain separate host-annotation signals and
    must not be collapsed into sequence-similarity risk.
    """
    existing = None
    if "human_similarity_score" in features.columns:
        existing = pd.to_numeric(features["human_similarity_score"], errors="coerce")

    values: list[float] = []
    for idx, row in features.iterrows():
        if _is_explicit_no_hit(row) or _has_complete_alignment(row):
            value = human_similarity_score(row, DEFAULT_NEUTRAL_HOST_RISK)
        elif existing is not None and pd.notna(existing.loc[idx]):
            value = float(existing.loc[idx])
        else:
            value = DEFAULT_NEUTRAL_HOST_RISK
        values.append(min(1.0, max(0.0, float(value))))

    return pd.Series(values, index=features.index, dtype=float)


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
