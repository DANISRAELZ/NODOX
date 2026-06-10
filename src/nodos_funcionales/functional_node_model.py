from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from .model_config import CONSERVATIVE_INTERPRETATION_WARNING, FunctionalNodeModelConfig


class FunctionalNodeModel:
    """Small, auditable model wrapper for publication package generation."""

    def __init__(self, config: FunctionalNodeModelConfig | None = None) -> None:
        self.config = config or FunctionalNodeModelConfig()

    def score_candidates(self, candidates: pd.DataFrame) -> pd.DataFrame:
        scored = candidates.copy()
        for column, default in self._required_defaults().items():
            if column not in scored.columns:
                scored[column] = default

        scored["therapeutic_priority_score"] = scored.apply(self.compute_therapeutic_priority, axis=1)
        scored["functional_node_score"] = scored.apply(self.compute_functional_node_score, axis=1)
        scored["functional_node_theory_score"] = scored.apply(self.compute_functional_node_theory_score, axis=1)
        scored["evidence_confidence_score"] = scored.apply(self.compute_evidence_confidence, axis=1)
        scored["evolutionary_escape_penalty_applied"] = scored.apply(
            self.compute_evolutionary_escape_penalty,
            axis=1,
        )
        scored["meta_priority_score"] = scored.apply(self.compute_meta_priority, axis=1)
        scored["evolutionary_adjusted_meta_priority_score"] = (
            scored["meta_priority_score"] - scored["evolutionary_escape_penalty_applied"]
        ).clip(lower=0.0, upper=1.0)
        scored["interpretation_warning"] = scored.apply(self._interpretation_warning, axis=1)
        scored["therapeutic_role"] = scored.apply(self._classify_role, axis=1)
        return self.rank_candidates(scored)

    def compute_therapeutic_priority(self, row: pd.Series) -> float:
        existing = self._num(row, "therapeutic_priority_score", None)
        if existing is not None:
            return self._clip(existing)
        values = {
            "meta_priority_score": self._num(row, "meta_priority_score", 0.0),
            "host_safety_score": self._num(row, "host_safety_score", self._num(row, "selectivity_score", 0.5)),
            "host_damage_score": self._num(row, "host_damage_score", 0.0),
            "infection_site_access_score": self._num(row, "infection_site_access_score", 0.0),
            "infection_context_score": self._num(row, "infection_context_score", 0.0),
        }
        score = (
            values["meta_priority_score"] * 0.35
            + values["host_safety_score"] * 0.20
            + values["host_damage_score"] * 0.15
            + values["infection_site_access_score"] * 0.15
            + values["infection_context_score"] * 0.15
        )
        return self._clip(score)

    def compute_functional_node_score(self, row: pd.Series) -> float:
        existing = self._num(row, "functional_node_score", None)
        if existing is not None:
            return self._clip(existing)
        score = (
            self._num(row, "network_centrality", 0.0) * 0.35
            + self._num(row, "pathway_bottleneck_score", 0.0) * 0.30
            + self._num(row, "essentiality_support", self._num(row, "essential", 0.0)) * 0.20
            + self._num(row, "virulence_support", self._num(row, "virulence_score", 0.0)) * 0.15
        )
        return self._clip(score)

    def compute_functional_node_theory_score(self, row: pd.Series) -> float:
        existing = self._num(row, "functional_node_theory_score", None)
        if existing is not None:
            return self._clip(existing)
        base = self.compute_functional_node_score(row)
        constraint = self._num(row, "evolutionary_space_constraint_score", 0.0)
        redundancy = self._num(row, "redundancy_penalty", 0.0)
        escape = self._num(row, "evolutionary_escape_risk_score", 0.0)
        return self._clip(base * 0.65 + constraint * 0.25 - redundancy * 0.05 - escape * 0.05)

    def compute_evidence_confidence(self, row: pd.Series) -> float:
        existing = self._num(row, "evidence_confidence_score", None)
        if existing is not None:
            return self._clip(existing)
        evidence_quality = self._num(row, "evidence_quality_score", 0.0)
        confidence_ceiling = self._num(row, "confidence_ceiling", 1.0)
        coverage = self._num(row, "evidence_coverage_score", 0.0)
        return self._clip(min(evidence_quality, confidence_ceiling) * 0.70 + coverage * 0.30)

    def compute_evolutionary_escape_penalty(self, row: pd.Series) -> float:
        existing = self._num(row, "evolutionary_escape_penalty_applied", None)
        if existing is not None:
            return self._clip(existing)
        risk = self._num(row, "evolutionary_escape_risk_score", 0.0)
        return self._clip(risk * self.config.evolutionary_penalty_weight)

    def compute_meta_priority(self, row: pd.Series) -> float:
        weights = {
            "antibiotic_target_score": self.config.antibiotic_target_weight,
            "antivirulence_target_score": self.config.antivirulence_target_weight,
            "functional_node_score": self.config.functional_node_weight,
            "selectivity_score": self.config.selectivity_weight,
            "clinical_context_score": self.config.clinical_context_weight,
        }
        total = sum(weights.values()) or 1.0
        weighted = sum(self._num(row, column, 0.0) * weight for column, weight in weights.items()) / total
        missing_penalty = 0.0
        if self.compute_evidence_confidence(row) < self.config.low_evidence_confidence_threshold:
            missing_penalty = self.config.missing_evidence_penalty_weight
        return self._clip(weighted - missing_penalty)

    def rank_candidates(self, scored_candidates: pd.DataFrame) -> pd.DataFrame:
        ranked = scored_candidates.sort_values(
            ["evolutionary_adjusted_meta_priority_score", "therapeutic_priority_score", "protein_id"],
            ascending=[False, False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        ranked["final_priority_rank"] = range(1, len(ranked) + 1)
        return ranked

    def explain_candidate(self, row: pd.Series) -> str:
        return (
            f"rank={row.get('final_priority_rank', 'not_ranked')}; "
            f"therapeutic_priority={self._num(row, 'therapeutic_priority_score', 0.0):.3f}; "
            f"functional_node={self._num(row, 'functional_node_score', 0.0):.3f}; "
            f"evidence_confidence={self._num(row, 'evidence_confidence_score', 0.0):.3f}; "
            f"evolutionary_risk={self._num(row, 'evolutionary_escape_risk_score', 0.0):.3f}; "
            f"role={row.get('therapeutic_role', 'not_assessed')}; "
            "interpretation=prioritized hypothesis requiring independent validation"
        )

    def config_as_dict(self) -> dict[str, float]:
        return asdict(self.config)

    def _classify_role(self, row: pd.Series) -> str:
        existing = str(row.get("therapeutic_role", "") or "").strip()
        allowed = {
            "bactericidal_candidate",
            "antivirulence_candidate",
            "sensitizer_candidate",
            "mixed_strategy_candidate",
            "low_priority_candidate",
        }
        if existing in allowed:
            return existing
        antibiotic = self._num(row, "antibiotic_target_score", 0.0)
        antivirulence = self._num(row, "antivirulence_target_score", 0.0)
        functional = self._num(row, "functional_node_score", 0.0)
        access = self._num(row, "infection_site_access_score", 0.0)
        host_risk = 1.0 - self._num(row, "selectivity_score", self._num(row, "host_safety_score", 0.5))
        evidence = self.compute_evidence_confidence(row)
        if evidence < self.config.low_evidence_confidence_threshold or host_risk >= 0.65:
            return "low_priority_candidate"
        if antibiotic >= 0.70 and functional >= 0.60 and access >= 0.40:
            return "bactericidal_candidate"
        if antivirulence >= 0.65 and host_risk < 0.40:
            return "antivirulence_candidate"
        if antibiotic >= 0.55 and antivirulence >= 0.55 and functional >= 0.55:
            return "mixed_strategy_candidate"
        if functional >= 0.45:
            return "sensitizer_candidate"
        return "low_priority_candidate"

    def _interpretation_warning(self, row: pd.Series) -> str:
        warnings = [CONSERVATIVE_INTERPRETATION_WARNING]
        if self.compute_evidence_confidence(row) < self.config.low_evidence_confidence_threshold:
            warnings.append("low evidence confidence limits interpretation without changing it into low risk")
        if self._num(row, "evolutionary_escape_risk_score", 0.0) >= self.config.high_evolutionary_risk_threshold:
            warnings.append("high evolutionary escape risk requires review before prioritization")
        provenance_text = " ".join(str(row.get(column, "") or "") for column in row.index).lower()
        for tag in ["demo_only", "proxy", "missing", "not_assessed", "not_reported", "pending_review"]:
            if tag in provenance_text:
                warnings.append(f"provenance_or_limitation_tag_preserved={tag}")
        return "; ".join(dict.fromkeys(warnings))

    @staticmethod
    def _num(row: pd.Series, column: str, default: float | None) -> float | None:
        value = row.get(column, default)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        if pd.isna(numeric):
            return default
        return numeric

    @staticmethod
    def _clip(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _required_defaults() -> dict[str, object]:
        return {
            "gene": "not_reported",
            "protein_id": "not_reported",
            "antibiotic_target_score": 0.0,
            "antivirulence_target_score": 0.0,
            "functional_node_score": 0.0,
            "selectivity_score": 0.5,
            "clinical_context_score": 0.0,
            "evolutionary_escape_risk_score": 0.0,
            "evidence_quality_score": 0.0,
            "confidence_ceiling": 1.0,
            "evidence_coverage_score": 0.0,
        }
