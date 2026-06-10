from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class FunctionalNodeModelConfig:
    """Explicit weights and thresholds for publication-oriented scoring.

    Evidence confidence is kept as an interpretation and confidence signal. It
    does not automatically turn a prioritized hypothesis into a confirmed target.
    """

    antibiotic_target_weight: float = 0.22
    antivirulence_target_weight: float = 0.16
    functional_node_weight: float = 0.24
    selectivity_weight: float = 0.14
    clinical_context_weight: float = 0.12
    evolutionary_penalty_weight: float = 0.12
    evidence_quality_weight: float = 0.0
    confidence_ceiling_weight: float = 0.0
    missing_evidence_penalty_weight: float = 0.10
    high_evolutionary_risk_threshold: float = 0.65
    low_evidence_confidence_threshold: float = 0.35

    def with_overrides(self, **overrides: float) -> "FunctionalNodeModelConfig":
        return replace(self, **overrides)


CONSERVATIVE_INTERPRETATION_WARNING = (
    "candidate functional node; prioritized hypothesis from a computational "
    "demonstration; requires independent validation; not experimental validation; "
    "not clinical recommendation; score high does not mean confirmed therapeutic evidence."
)
