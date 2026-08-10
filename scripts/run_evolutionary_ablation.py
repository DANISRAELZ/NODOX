#!/usr/bin/env python3
"""Run a read-only evolutionary ablation against a selected NODOX run.

Stage 4B keeps historical proxy hypotheses separate from contract-supported
explicit evolutionary evidence. Missing evidence is never converted into low
risk or into a supported evolutionary contribution.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.nodos_funcionales.config import load_config, parse_simple_yaml
from src.nodos_funcionales.evolutionary_ablation_comparison import (
    write_evolutionary_ablation_comparison_outputs,
)

DEFAULT_THEORY = {
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
    },
}

DEFAULT_STAGE2_CONFIG = {
    "version": 2,
    "selected_run": {"expected_candidate_count": 25},
    "ablation": {
        "reported_score_column": "functional_node_theory_score",
        "baseline_name": "full_functional_node_theory",
        "baseline_tolerance": 1.0e-6,
        "scenarios": {
            "no_escape_penalty": {
                "remove_positive_weights": [],
                "remove_penalties": ["p_escape"],
            },
            "no_evolutionary_dimension": {
                "remove_positive_weights": ["w_evolutionary_constraint"],
                "remove_penalties": ["p_escape", "p_biofilm", "p_hgt"],
            },
        },
        "sensitivity_multipliers": [0.80, 0.90, 1.10, 1.20],
        "sensitivity_positive_weights": ["w_evolutionary_constraint"],
        "sensitivity_penalties": ["p_escape", "p_biofilm", "p_hgt"],
        "supported_evidence": {
            "minimum_explicit_variables": 3,
            "minimum_independent_evidence_groups": 2,
            "require_contract_supported": True,
            "unknown_statuses": [
                "unknown_missing_evidence",
                "unknown",
                "missing",
                "not_reported",
                "unresolved",
                "insufficient_evidence",
                "insufficient_independent_evidence",
                "derived_from_related_layers",
            ],
        },
    },
}

POSITIVE_TERMS = {
    "w_functional_node": "functional_node_score",
    "w_contextual_essentiality": "contextual_essentiality_score",
    "w_pleiotropy": "pleiotropy_score",
    "w_conservation": "conservation_score",
    "w_evolutionary_constraint": "evolutionary_space_constraint_score",
    "w_evidence_quality": "evidence_quality_score",
}
PENALTY_TERMS = {
    "p_redundancy": "redundancy_penalty",
    "p_escape": "evolutionary_escape_risk_score",
    "p_biofilm": "biofilm_escape_penalty",
    "p_hgt": "horizontal_transfer_penalty",
    "p_host_similarity": "host_similarity_penalty",
}
FEATURE_PRIORITY = ("phase3_features.csv",)
RANKING_PRIORITY = (
    "ranking_nodos_phase3_real_candidates.csv",
    "ranking_nodos_phase3.csv",
    "ranking_nodos.csv",
)
COVERAGE_PRIORITY = ("evolutionary_coverage_by_candidate.csv",)
IDENTITY_COLUMNS = ("protein_id", "accession", "entry", "gene", "locus_tag")
EVOLUTIONARY_EXPLICIT_VARIABLES = (
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
)
EVOLUTIONARY_PROXY_COLUMNS = (
    *EVOLUTIONARY_EXPLICIT_VARIABLES,
    "evolutionary_escape_risk_score",
)


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_stage2_config(path: Path) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_STAGE2_CONFIG)
    if not path.exists():
        return config
    try:
        raw = path.read_text(encoding="utf-8")
        loaded = (
            json.loads(raw)
            if path.suffix.lower() == ".json"
            else parse_simple_yaml(raw)
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return config
    return _deep_merge(config, loaded) if isinstance(loaded, Mapping) else config


def effective_theory_config(params: Mapping[str, Any]) -> dict[str, Any]:
    phase3 = (
        params.get("phase3", {})
        if isinstance(params.get("phase3"), Mapping)
        else {}
    )
    theory = (
        phase3.get("functional_node_theory", {})
        if isinstance(phase3.get("functional_node_theory"), Mapping)
        else {}
    )
    return _deep_merge(DEFAULT_THEORY, theory)


def _path_priority(path: Path, names: Sequence[str]) -> tuple[int, int, str]:
    name_rank = list(names).index(path.name) if path.name in names else len(names)
    lowered = path.as_posix().lower()
    if "workspace/data_processed" in lowered:
        location_rank = 0
    elif "workspace/results" in lowered:
        location_rank = 1
    elif "review_package" in lowered:
        location_rank = 2
    else:
        location_rank = 3
    return name_rank, location_rank, lowered


def find_artifact(run_dir: Path, names: Sequence[str]) -> Path | None:
    matches = [
        path
        for name in names
        for path in run_dir.rglob(name)
        if path.is_file()
    ]
    return (
        sorted(set(matches), key=lambda path: _path_priority(path, names))[0]
        if matches
        else None
    )


def find_params_path(run_dir: Path, repo_root: Path) -> Path:
    candidates = [
        run_dir / "workspace" / "config" / "params.yaml",
        run_dir / "config" / "params.yaml",
        repo_root / "config" / "params.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "No se encontró params.yaml de la corrida ni del repositorio"
    )


def candidate_ids(frame: pd.DataFrame) -> pd.Series:
    columns = [column for column in IDENTITY_COLUMNS if column in frame.columns]
    if not columns:
        return pd.Series(
            [f"candidate_{index + 1}" for index in range(len(frame))],
            index=frame.index,
            dtype="string",
        )
    values = frame[columns].astype("string").replace(
        {"<NA>": pd.NA, "nan": pd.NA, "": pd.NA}
    )
    fallback = pd.Series(
        [f"candidate_{index + 1}" for index in range(len(frame))],
        index=frame.index,
        dtype="string",
    )
    return values.bfill(axis=1).iloc[:, 0].fillna(fallback)


def _common_identity(left: pd.DataFrame, right: pd.DataFrame) -> str | None:
    return next(
        (
            column
            for column in IDENTITY_COLUMNS
            if column in left.columns and column in right.columns
        ),
        None,
    )


def select_analysis_frame(
    feature_frame: pd.DataFrame,
    ranking_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    if ranking_frame is None or ranking_frame.empty:
        return feature_frame.copy().reset_index(drop=True)
    key = _common_identity(feature_frame, ranking_frame)
    if key is None:
        if len(feature_frame) == len(ranking_frame):
            return feature_frame.copy().reset_index(drop=True)
        raise ValueError(
            "No se pudo alinear phase3_features con el ranking seleccionado"
        )
    ranked_ids = ranking_frame[key].astype(str)
    features = feature_frame.copy()
    features[key] = features[key].astype(str)
    features = features.drop_duplicates(subset=[key], keep="first").set_index(key)
    missing = [value for value in ranked_ids if value not in features.index]
    if missing:
        raise ValueError(
            f"Faltan {len(missing)} candidatos del ranking en phase3_features: "
            f"{missing[:5]}"
        )
    return features.loc[ranked_ids].reset_index()


def _series(frame: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([default] * len(frame), index=frame.index, dtype=float)
    return (
        pd.to_numeric(frame[column], errors="coerce")
        .fillna(default)
        .clip(lower=0.0, upper=1.0)
    )


def compute_theory_score(
    frame: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.Series:
    defaults = {
        key: float(value) for key, value in config.get("defaults", {}).items()
    }
    weights = {
        key: max(float(value), 0.0)
        for key, value in config.get("weights", {}).items()
    }
    penalties = {
        key: max(float(value), 0.0)
        for key, value in config.get("penalties", {}).items()
    }

    positive_weight = sum(weights.get(key, 0.0) for key in POSITIVE_TERMS)
    positive = pd.Series([0.0] * len(frame), index=frame.index, dtype=float)
    if positive_weight > 0:
        positive = sum(
            _series(frame, column, defaults.get(column, 0.0))
            * weights.get(weight_key, 0.0)
            for weight_key, column in POSITIVE_TERMS.items()
        ) / positive_weight

    penalty_weight = sum(penalties.get(key, 0.0) for key in PENALTY_TERMS)
    penalty = pd.Series([0.0] * len(frame), index=frame.index, dtype=float)
    if penalty_weight > 0:
        weighted = sum(
            _series(frame, column, defaults.get(column, 0.0))
            * penalties.get(penalty_key, 0.0)
            for penalty_key, column in PENALTY_TERMS.items()
        ) / penalty_weight
        penalty = weighted * min(penalty_weight, 1.0)
    return (positive - penalty).clip(lower=0.0, upper=1.0)


def apply_scenario(
    config: Mapping[str, Any],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(dict(config))
    for key in scenario.get("remove_positive_weights", []):
        result.setdefault("weights", {})[key] = 0.0
    for key in scenario.get("remove_penalties", []):
        result.setdefault("penalties", {})[key] = 0.0
    return result


def apply_sensitivity(
    config: Mapping[str, Any],
    multiplier: float,
    positive_keys: Sequence[str],
    penalty_keys: Sequence[str],
) -> dict[str, Any]:
    result = copy.deepcopy(dict(config))
    for key in positive_keys:
        result.setdefault("weights", {})[key] = (
            float(result.get("weights", {}).get(key, 0.0)) * multiplier
        )
    for key in penalty_keys:
        result.setdefault("penalties", {})[key] = (
            float(result.get("penalties", {}).get(key, 0.0)) * multiplier
        )
    return result


def deterministic_rank(score: pd.Series, ids: pd.Series) -> pd.Series:
    working = pd.DataFrame(
        {"score": score, "candidate_id": ids.astype(str)},
        index=score.index,
    )
    ordered = working.sort_values(
        ["score", "candidate_id"],
        ascending=[False, True],
        kind="mergesort",
    )
    ranks = pd.Series(index=score.index, dtype=int)
    ranks.loc[ordered.index] = range(1, len(ordered) + 1)
    return ranks.astype(int)


def _normalize_status(series: pd.Series) -> pd.Series:
    return (
        series.fillna("not_reported")
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({"": "not_reported", "nan": "not_reported"})
    )


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in frame.columns:
        return None
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return (
        values.fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y", "supported"})
    )


def explicit_variable_count(frame: pd.DataFrame) -> pd.Series:
    if "evolutionary_escape_risk_explicit_variable_count" in frame.columns:
        return (
            pd.to_numeric(
                frame["evolutionary_escape_risk_explicit_variable_count"],
                errors="coerce",
            )
            .fillna(0)
            .clip(lower=0)
            .astype(int)
        )

    # Legacy flags are retained only as a diagnostic count. They do not satisfy
    # the Stage 4B contract gate without an explicit contract-supported column.
    flags: dict[str, pd.Series] = {}
    for variable in EVOLUTIONARY_EXPLICIT_VARIABLES:
        values = _bool_series(frame, f"{variable}_contract_explicit")
        if values is not None:
            flags[variable] = values
    if not flags:
        return pd.Series([0] * len(frame), index=frame.index, dtype=int)
    return pd.DataFrame(flags, index=frame.index).sum(axis=1).astype(int)


def independent_evidence_group_count(frame: pd.DataFrame) -> pd.Series:
    column = "evolutionary_escape_risk_independent_evidence_group_count"
    if column not in frame.columns:
        return pd.Series([0] * len(frame), index=frame.index, dtype=int)
    return (
        pd.to_numeric(frame[column], errors="coerce")
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )


def evolutionary_supported_mask(
    frame: pd.DataFrame,
    cfg: Mapping[str, Any],
) -> pd.Series:
    support_cfg = (
        cfg.get("supported_evidence", {})
        if isinstance(cfg.get("supported_evidence"), Mapping)
        else {}
    )
    minimum_variables = int(support_cfg.get("minimum_explicit_variables", 3))
    minimum_groups = int(
        support_cfg.get("minimum_independent_evidence_groups", 2)
    )
    require_contract = bool(support_cfg.get("require_contract_supported", True))
    unknown_statuses = {
        str(value).strip().lower()
        for value in support_cfg.get(
            "unknown_statuses",
            DEFAULT_STAGE2_CONFIG["ablation"]["supported_evidence"][
                "unknown_statuses"
            ],
        )
    }

    counts = explicit_variable_count(frame)
    groups = independent_evidence_group_count(frame)
    if "evolutionary_escape_risk_status" in frame.columns:
        status = _normalize_status(frame["evolutionary_escape_risk_status"])
    else:
        status = pd.Series(
            ["not_reported"] * len(frame),
            index=frame.index,
            dtype="string",
        )

    contract = _bool_series(frame, "evolutionary_evidence_contract_supported")
    if contract is None:
        contract = pd.Series(False, index=frame.index, dtype=bool)

    threshold_mask = (
        (counts >= minimum_variables)
        & (groups >= minimum_groups)
        & ~status.isin(unknown_statuses)
    )
    if require_contract:
        return threshold_mask & contract
    return threshold_mask


def build_gene_summary(candidate_output: pd.DataFrame) -> pd.DataFrame:
    if candidate_output.empty:
        return candidate_output.copy()
    group_column = "gene" if "gene" in candidate_output.columns else "candidate_id"
    working = candidate_output.copy()
    working[group_column] = (
        working[group_column]
        .fillna("not_reported")
        .astype(str)
        .replace({"": "not_reported", "nan": "not_reported"})
    )
    aggregations: dict[str, tuple[str, str | Any]] = {
        "accession_count": ("candidate_id", "nunique"),
        "score_without_evolutionary_information": (
            "ranking_without_evolutionary_information_score",
            "mean",
        ),
        "score_with_proxy_evolutionary_dimension": (
            "ranking_with_proxy_evolutionary_score",
            "mean",
        ),
        "score_with_supported_evolutionary_dimension": (
            "ranking_with_supported_evolutionary_score",
            "mean",
        ),
        "proxy_evolutionary_score_contribution": (
            "proxy_evolutionary_score_contribution",
            "mean",
        ),
        "supported_evolutionary_score_contribution": (
            "supported_evolutionary_score_contribution",
            "mean",
        ),
        "maximum_explicit_variable_count": (
            "evolutionary_escape_risk_explicit_variable_count",
            "max",
        ),
        "maximum_independent_evidence_group_count": (
            "evolutionary_escape_risk_independent_evidence_group_count",
            "max",
        ),
        "supported_accession_count": (
            "supported_evolutionary_dimension_applied",
            "sum",
        ),
    }
    if "evolutionary_escape_proxy_score" in working.columns:
        aggregations["mean_evolutionary_escape_proxy_score"] = (
            "evolutionary_escape_proxy_score",
            "mean",
        )
    if "evolutionary_escape_supported_score" in working.columns:
        aggregations["mean_evolutionary_escape_supported_score"] = (
            "evolutionary_escape_supported_score",
            "mean",
        )

    grouped = (
        working.groupby(group_column, dropna=False)
        .agg(**aggregations)
        .reset_index()
    )
    ids = grouped[group_column].astype(str)
    grouped["rank_without_evolutionary_information"] = deterministic_rank(
        grouped["score_without_evolutionary_information"], ids
    )
    grouped["rank_with_proxy_evolutionary_dimension"] = deterministic_rank(
        grouped["score_with_proxy_evolutionary_dimension"], ids
    )
    grouped["rank_with_supported_evolutionary_dimension"] = deterministic_rank(
        grouped["score_with_supported_evolutionary_dimension"], ids
    )
    grouped["proxy_rank_shift_vs_without_evolutionary_information"] = (
        grouped["rank_with_proxy_evolutionary_dimension"]
        - grouped["rank_without_evolutionary_information"]
    )
    grouped["supported_rank_shift_vs_without_evolutionary_information"] = (
        grouped["rank_with_supported_evolutionary_dimension"]
        - grouped["rank_without_evolutionary_information"]
    )
    grouped["evolutionary_evidence_mode"] = grouped.apply(
        lambda row: (
            "supported_explicit"
            if int(row["supported_accession_count"]) == int(row["accession_count"])
            else "mixed_supported_and_proxy"
            if int(row["supported_accession_count"]) > 0
            else "proxy_hypothesis_only"
        ),
        axis=1,
    )
    return grouped


def build_proxy_decomposition(
    frame: pd.DataFrame,
    candidate_output: pd.DataFrame,
) -> pd.DataFrame:
    output = pd.DataFrame(index=frame.index)
    output["candidate_id"] = candidate_ids(frame)
    for column in IDENTITY_COLUMNS:
        if column in frame.columns:
            output[column] = frame[column]
    for column in EVOLUTIONARY_PROXY_COLUMNS:
        if column in frame.columns:
            output[column] = pd.to_numeric(frame[column], errors="coerce")
        for suffix in ("is_explicit", "contract_explicit", "source_type"):
            audit_column = f"{column}_{suffix}"
            if audit_column in frame.columns:
                output[audit_column] = frame[audit_column]
    for column in (
        "evolutionary_escape_risk_status",
        "evolutionary_escape_risk_input_source_type",
        "evolutionary_escape_risk_source_type",
        "evolutionary_escape_source_type",
        "redundancy_source_type",
        "evolutionary_escape_risk_layer_source_type",
        "evolutionary_evidence_contract_supported",
        "evolutionary_escape_risk_independent_evidence_group_count",
        "evolutionary_escape_risk_independence_groups",
        "evolutionary_evidence_contract_errors",
        "evolutionary_evidence_contract_warnings",
    ):
        if column in frame.columns:
            output[column] = frame[column]
    for column in (
        "evolutionary_escape_proxy_score",
        "evolutionary_escape_supported_score",
        "evolutionary_escape_risk_explicit_variable_count",
        "evolutionary_escape_risk_independent_evidence_group_count",
        "evolutionary_evidence_contract_supported",
        "evolutionary_evidence_mode",
        "supported_evolutionary_dimension_applied",
        "proxy_evolutionary_score_contribution",
        "supported_evolutionary_score_contribution",
        "ranking_with_matched_proxy_evolutionary_score",
        "ranking_with_matched_proxy_evolutionary_rank",
        "matched_proxy_evolutionary_score_contribution",
    ):
        if column in candidate_output.columns:
            output[column] = candidate_output[column].values
    return output


def _evidence_gated_theory_score(
    frame: pd.DataFrame,
    theory: Mapping[str, Any],
    no_evolution_config: Mapping[str, Any],
    supported_mask: pd.Series,
    *,
    escape_column: str,
    constraint_column: str,
) -> pd.Series:
    """Restore only evidence-gated evolutionary terms over the no-evolution model.

    Biofilm and HGT remain excluded because Stage 4A does not define them as
    explicit evolutionary variables. Callers choose either proxy or supported
    values while retaining the same terms and unchanged theory weights.
    """

    no_evolution_score = compute_theory_score(frame, no_evolution_config)
    if not bool(supported_mask.any()):
        return no_evolution_score

    supported_frame = frame.copy()
    if escape_column in supported_frame.columns:
        supported_escape = pd.to_numeric(
            supported_frame[escape_column],
            errors="coerce",
        )
    else:
        supported_escape = pd.Series(math.nan, index=frame.index)
    supported_frame["evolutionary_escape_risk_score"] = supported_escape

    escape_config = copy.deepcopy(dict(no_evolution_config))
    escape_config.setdefault("penalties", {})["p_escape"] = float(
        theory.get("penalties", {}).get("p_escape", 0.0)
    )
    escape_score = compute_theory_score(supported_frame, escape_config)

    constraint_mask = _bool_series(
        supported_frame,
        "evolutionary_constraint_score_contract_explicit",
    )
    if constraint_mask is None:
        constraint_mask = pd.Series(False, index=frame.index, dtype=bool)
    constraint_mask = constraint_mask & supported_mask

    constraint_config = copy.deepcopy(escape_config)
    constraint_config.setdefault("weights", {})["w_evolutionary_constraint"] = float(
        theory.get("weights", {}).get("w_evolutionary_constraint", 0.0)
    )
    if constraint_column in supported_frame.columns:
        supported_frame["evolutionary_space_constraint_score"] = pd.to_numeric(
            supported_frame[constraint_column],
            errors="coerce",
        )
    constraint_score = compute_theory_score(supported_frame, constraint_config)

    output = no_evolution_score.copy()
    escape_usable = supported_mask & supported_escape.notna()
    output.loc[escape_usable] = escape_score.loc[escape_usable]
    output.loc[constraint_mask & escape_usable] = constraint_score.loc[
        constraint_mask & escape_usable
    ]
    return output


def _supported_theory_score(
    frame: pd.DataFrame,
    theory: Mapping[str, Any],
    no_evolution_config: Mapping[str, Any],
    supported_mask: pd.Series,
) -> pd.Series:
    """Apply only contract-supported evolutionary terms."""

    return _evidence_gated_theory_score(
        frame,
        theory,
        no_evolution_config,
        supported_mask,
        escape_column="evolutionary_escape_supported_score",
        constraint_column="evolutionary_constraint_score",
    )


def _matched_proxy_theory_score(
    frame: pd.DataFrame,
    theory: Mapping[str, Any],
    no_evolution_config: Mapping[str, Any],
    supported_mask: pd.Series,
) -> pd.Series:
    """Apply proxies to the same candidates and terms as supported evidence."""

    return _evidence_gated_theory_score(
        frame,
        theory,
        no_evolution_config,
        supported_mask,
        escape_column="evolutionary_escape_risk_score",
        constraint_column="evolutionary_space_constraint_score",
    )


def build_ablation(
    frame: pd.DataFrame,
    theory: Mapping[str, Any],
    stage2: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    cfg = (
        stage2.get("ablation", {})
        if isinstance(stage2.get("ablation"), Mapping)
        else {}
    )
    scenarios = (
        cfg.get("scenarios", {})
        if isinstance(cfg.get("scenarios"), Mapping)
        else {}
    )
    ids = candidate_ids(frame)
    output = pd.DataFrame({"candidate_id": ids})
    for column in IDENTITY_COLUMNS:
        if column in frame.columns:
            output[column] = frame[column]

    baseline = compute_theory_score(frame, theory)
    output["recomputed_baseline_score"] = baseline
    output["baseline_rank"] = deterministic_rank(baseline, ids)
    reported_column = str(
        cfg.get("reported_score_column", "functional_node_theory_score")
    )
    reported = (
        pd.to_numeric(frame[reported_column], errors="coerce")
        if reported_column in frame.columns
        else pd.Series(math.nan, index=frame.index)
    )
    output["reported_functional_node_theory_score"] = reported
    output["baseline_reconstruction_delta"] = baseline - reported

    explicit_counts = explicit_variable_count(frame)
    group_counts = independent_evidence_group_count(frame)
    output["evolutionary_escape_risk_explicit_variable_count"] = explicit_counts
    output["evolutionary_escape_risk_independent_evidence_group_count"] = group_counts
    if "evolutionary_escape_risk_available_variable_count" in frame.columns:
        output["evolutionary_escape_risk_available_variable_count"] = (
            pd.to_numeric(
                frame["evolutionary_escape_risk_available_variable_count"],
                errors="coerce",
            )
            .fillna(0)
            .clip(lower=0)
            .astype(int)
        )
    if "evolutionary_escape_risk_status" in frame.columns:
        output["evolutionary_escape_risk_status"] = frame[
            "evolutionary_escape_risk_status"
        ].fillna("not_reported")
    else:
        output["evolutionary_escape_risk_status"] = "not_reported"

    contract = _bool_series(frame, "evolutionary_evidence_contract_supported")
    if contract is None:
        contract = pd.Series(False, index=frame.index, dtype=bool)
    output["evolutionary_evidence_contract_supported"] = contract

    proxy_risk = (
        pd.to_numeric(frame["evolutionary_escape_risk_score"], errors="coerce")
        if "evolutionary_escape_risk_score" in frame.columns
        else pd.Series(math.nan, index=frame.index)
    )
    contract_supported_mask = evolutionary_supported_mask(frame, cfg)
    if "evolutionary_escape_supported_score" in frame.columns:
        supported_risk = pd.to_numeric(
            frame["evolutionary_escape_supported_score"],
            errors="coerce",
        ).where(contract_supported_mask, math.nan)
    else:
        supported_risk = pd.Series(math.nan, index=frame.index, dtype=float)
    supported_mask = contract_supported_mask & supported_risk.notna()
    output["evolutionary_escape_proxy_score"] = proxy_risk
    output["evolutionary_escape_supported_score"] = supported_risk
    output["supported_evolutionary_dimension_applied"] = supported_mask
    output["evolutionary_evidence_mode"] = supported_mask.map(
        {True: "supported_explicit", False: "proxy_hypothesis_only"}
    )

    scenario_metadata: dict[str, Any] = {}
    scenario_scores: dict[str, pd.Series] = {}
    scenario_ranks: dict[str, pd.Series] = {}
    for name, raw in scenarios.items():
        scenario = raw if isinstance(raw, Mapping) else {}
        score = compute_theory_score(frame, apply_scenario(theory, scenario))
        rank = deterministic_rank(score, ids)
        scenario_scores[name] = score
        scenario_ranks[name] = rank
        output[f"{name}_score"] = score
        output[f"{name}_rank"] = rank
        output[f"rank_shift_full_vs_{name}"] = output["baseline_rank"] - rank
        output[f"score_delta_full_minus_{name}"] = baseline - score
        scenario_metadata[name] = {
            "remove_positive_weights": list(
                scenario.get("remove_positive_weights", [])
            ),
            "remove_penalties": list(scenario.get("remove_penalties", [])),
        }

    central = "no_evolutionary_dimension"
    if central not in scenario_scores:
        fallback_scenario = DEFAULT_STAGE2_CONFIG["ablation"]["scenarios"][central]
        scenario_scores[central] = compute_theory_score(
            frame,
            apply_scenario(theory, fallback_scenario),
        )
        scenario_ranks[central] = deterministic_rank(
            scenario_scores[central],
            ids,
        )
        output[f"{central}_score"] = scenario_scores[central]
        output[f"{central}_rank"] = scenario_ranks[central]
        output[f"rank_shift_full_vs_{central}"] = (
            output["baseline_rank"] - scenario_ranks[central]
        )
        output[f"score_delta_full_minus_{central}"] = (
            baseline - scenario_scores[central]
        )
        scenario_metadata[central] = copy.deepcopy(fallback_scenario)

    no_evolution_score = scenario_scores[central]
    no_evolution_rank = scenario_ranks[central]
    no_evolution_config = apply_scenario(
        theory,
        scenarios.get(
            central,
            DEFAULT_STAGE2_CONFIG["ablation"]["scenarios"][central],
        ),
    )
    supported_score = _supported_theory_score(
        frame,
        theory,
        no_evolution_config,
        supported_mask,
    )
    supported_rank = deterministic_rank(supported_score, ids)
    matched_proxy_score = _matched_proxy_theory_score(
        frame,
        theory,
        no_evolution_config,
        supported_mask,
    )
    matched_proxy_rank = deterministic_rank(matched_proxy_score, ids)

    output["ranking_without_evolutionary_information_score"] = no_evolution_score
    output["ranking_without_evolutionary_information_rank"] = no_evolution_rank
    output["ranking_with_proxy_evolutionary_score"] = baseline
    output["ranking_with_proxy_evolutionary_rank"] = output["baseline_rank"]
    output["ranking_with_supported_evolutionary_score"] = supported_score
    output["ranking_with_supported_evolutionary_rank"] = supported_rank
    output["ranking_with_matched_proxy_evolutionary_score"] = matched_proxy_score
    output["ranking_with_matched_proxy_evolutionary_rank"] = matched_proxy_rank
    output["proxy_rank_shift_vs_without_evolutionary_information"] = (
        output["ranking_with_proxy_evolutionary_rank"]
        - output["ranking_without_evolutionary_information_rank"]
    )
    output["supported_rank_shift_vs_without_evolutionary_information"] = (
        output["ranking_with_supported_evolutionary_rank"]
        - output["ranking_without_evolutionary_information_rank"]
    )
    output["proxy_evolutionary_score_contribution"] = baseline - no_evolution_score
    output["supported_evolutionary_score_contribution"] = (
        supported_score - no_evolution_score
    )
    output["matched_proxy_evolutionary_score_contribution"] = (
        matched_proxy_score - no_evolution_score
    )

    shift = output[f"rank_shift_full_vs_{central}"]
    output["evolutionary_rank_effect"] = shift.map(
        lambda value: (
            "demoted_by_evolution"
            if value > 0
            else "promoted_by_evolution"
            if value < 0
            else "unchanged"
        )
    )
    output["evolutionary_score_contribution"] = output[
        f"score_delta_full_minus_{central}"
    ]

    sensitivity_rows: list[dict[str, Any]] = []
    for multiplier in [
        float(value) for value in cfg.get("sensitivity_multipliers", [])
    ]:
        score = compute_theory_score(
            frame,
            apply_sensitivity(
                theory,
                multiplier,
                list(cfg.get("sensitivity_positive_weights", [])),
                list(cfg.get("sensitivity_penalties", [])),
            ),
        )
        rank = deterministic_rank(score, ids)
        for index in frame.index:
            sensitivity_rows.append(
                {
                    "candidate_id": str(ids.loc[index]),
                    "multiplier": multiplier,
                    "analysis_mode": "proxy_hypothesis_only",
                    "score": float(score.loc[index]),
                    "rank": int(rank.loc[index]),
                    "rank_change_vs_baseline": int(
                        rank.loc[index] - output.loc[index, "baseline_rank"]
                    ),
                }
            )
    sensitivity = pd.DataFrame(sensitivity_rows)

    tolerance = float(cfg.get("baseline_tolerance", 1.0e-6))
    deltas = pd.to_numeric(
        output["baseline_reconstruction_delta"], errors="coerce"
    ).abs()
    comparable = int(deltas.notna().sum())
    mismatches = int((deltas > tolerance).sum())
    supported_count = int(supported_mask.sum())
    proxy_only_count = int((~supported_mask).sum())
    support_cfg = (
        cfg.get("supported_evidence", {})
        if isinstance(cfg.get("supported_evidence"), Mapping)
        else {}
    )
    summary = {
        "schema_version": 4,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(output),
        "reported_baseline_comparable_count": comparable,
        "reported_baseline_mismatch_count": mismatches,
        "maximum_absolute_baseline_delta": (
            float(deltas.max()) if comparable else None
        ),
        "baseline_tolerance": tolerance,
        "baseline_reconstruction_valid": (
            comparable == len(output) and mismatches == 0
        ),
        "scenario_definitions": scenario_metadata,
        "sensitivity_row_count": len(sensitivity),
        "sensitivity_rows": sensitivity_rows,
        "supported_evidence_minimum_explicit_variables": int(
            support_cfg.get("minimum_explicit_variables", 3)
        ),
        "supported_evidence_minimum_independent_evidence_groups": int(
            support_cfg.get("minimum_independent_evidence_groups", 2)
        ),
        "supported_evidence_requires_contract": bool(
            support_cfg.get("require_contract_supported", True)
        ),
        "supported_evolutionary_candidate_count": supported_count,
        "proxy_only_candidate_count": proxy_only_count,
        "all_candidates_proxy_only": proxy_only_count == len(output),
        "scientific_interpretation": {
            "rank_shift_is_not_predictive_validation": True,
            "unknown_escape_is_not_low_escape": True,
            "analysis_does_not_change_defaults": True,
            "proxy_ranking_is_exploratory_only": True,
            "supported_ranking_requires_contract_evidence_gate": True,
            "supported_ranking_excludes_uncontracted_biofilm_hgt": True,
        },
    }
    return output, summary


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "not_available"
    return result.stdout.strip() or "not_available"


def write_summary_report(
    path: Path,
    output: pd.DataFrame,
    gene_output: pd.DataFrame,
    summary: Mapping[str, Any],
    feature_source: Path,
    ranking_source: Path | None,
    params_source: Path,
) -> None:
    valid = bool(summary["baseline_reconstruction_valid"])
    proxy_shift = "proxy_rank_shift_vs_without_evolutionary_information"
    supported_shift = "supported_rank_shift_vs_without_evolutionary_information"

    proxy_demoted = int((output[proxy_shift] > 0).sum()) if valid else 0
    proxy_promoted = int((output[proxy_shift] < 0).sum()) if valid else 0
    proxy_unchanged = int((output[proxy_shift] == 0).sum()) if valid else 0
    supported_demoted = int((output[supported_shift] > 0).sum()) if valid else 0
    supported_promoted = int((output[supported_shift] < 0).sum()) if valid else 0
    supported_unchanged = int((output[supported_shift] == 0).sum()) if valid else 0
    largest = (
        output.reindex(output[proxy_shift].abs().sort_values(ascending=False).index)
        .head(10)
        if valid
        else output.head(0)
    )
    gene_changed = (
        int(
            (
                gene_output[
                    "proxy_rank_shift_vs_without_evolutionary_information"
                ]
                != 0
            ).sum()
        )
        if not gene_output.empty
        else 0
    )

    lines = [
        "# Ablación exploratoria de la dimensión evolutiva",
        "",
        f"Generado: `{summary['generated_at_utc']}`",
        f"Tabla de características: `{feature_source.as_posix()}`",
        (
            "Ranking seleccionado: "
            f"`{ranking_source.as_posix() if ranking_source else 'not_available'}`"
        ),
        f"Configuración de la corrida: `{params_source.as_posix()}`",
        "",
        "## Verificación de reconstrucción",
        "",
        f"- Candidatos: **{summary['candidate_count']}**",
        (
            "- Puntajes reportados comparables: "
            f"**{summary['reported_baseline_comparable_count']}**"
        ),
        (
            "- Diferencias mayores a la tolerancia: "
            f"**{summary['reported_baseline_mismatch_count']}**"
        ),
        (
            "- Diferencia absoluta máxima: "
            f"**{summary['maximum_absolute_baseline_delta']}**"
        ),
        f"- Reconstrucción válida: **{summary['baseline_reconstruction_valid']}**",
        "",
        "## Separación de evidencia",
        "",
        (
            "- Candidatos con dimensión evolutiva respaldada por contrato: "
            f"**{summary['supported_evolutionary_candidate_count']}**"
        ),
        (
            "- Candidatos evaluados sólo como hipótesis proxy: "
            f"**{summary['proxy_only_candidate_count']}**"
        ),
        (
            "- Mínimo de variables explícitas exigido: "
            f"**{summary['supported_evidence_minimum_explicit_variables']}**"
        ),
        (
            "- Mínimo de grupos independientes exigido: "
            f"**{summary['supported_evidence_minimum_independent_evidence_groups']}**"
        ),
        "",
    ]
    if summary.get("all_candidates_proxy_only"):
        lines.extend(
            [
                "> **Advertencia científica:** todos los candidatos carecen "
                "de evidencia evolutiva explícita suficiente bajo el contrato. "
                "Los cambios del ranking proxy son exploratorios.",
                "",
            ]
        )
    if valid:
        lines.extend(
            [
                "## Efecto del ranking proxy derivado",
                "",
                f"- Promovidos al añadir proxies evolutivos: **{proxy_promoted}**",
                f"- Despriorizados al añadir proxies evolutivos: **{proxy_demoted}**",
                f"- Sin cambio de posición: **{proxy_unchanged}**",
                "",
                "## Efecto del ranking respaldado",
                "",
                (
                    "- Promovidos al añadir evidencia evolutiva respaldada: "
                    f"**{supported_promoted}**"
                ),
                (
                    "- Despriorizados al añadir evidencia evolutiva respaldada: "
                    f"**{supported_demoted}**"
                ),
                f"- Sin cambio de posición: **{supported_unchanged}**",
                f"- Genes con cambio de rango proxy: **{gene_changed}**",
                "",
                "## Mayores cambios del ranking proxy",
                "",
                (
                    "| Candidato | Rango sin información evolutiva | "
                    "Rango proxy | Cambio | Contribución proxy | Modo |"
                ),
                "|---|---:|---:|---:|---:|---|",
            ]
        )
        for row in largest.to_dict(orient="records"):
            lines.append(
                f"| {row['candidate_id']} | "
                f"{row['ranking_without_evolutionary_information_rank']} | "
                f"{row['ranking_with_proxy_evolutionary_rank']} | "
                f"{row[proxy_shift]} | "
                f"{row['proxy_evolutionary_score_contribution']:.6f} | "
                f"{row['evolutionary_evidence_mode']} |"
            )
    else:
        lines.extend(
            [
                "## Resultado bloqueado",
                "",
                (
                    "Los cambios de rango no deben interpretarse hasta que "
                    "la reconstrucción reproduzca exactamente el puntaje reportado."
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Límites científicos",
            "",
            (
                "- El ranking proxy demuestra operacionalización computacional, "
                "no predicción de resistencia."
            ),
            (
                "- `unknown`, `missing` y `not_reported` no se convierten en "
                "riesgo bajo ni en evidencia respaldada."
            ),
            (
                "- El ranking respaldado exige simultáneamente contrato válido, "
                "variables explícitas suficientes y grupos independientes suficientes."
            ),
            (
                "- Biofilm y HGT permanecen fuera del ranking respaldado hasta "
                "contar con un contrato explícito equivalente."
            ),
            "- Este análisis no modifica pesos ni resultados históricos.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *,
    repo_root: Path,
    run_dir: Path,
    output_dir: Path,
    stage2_config_path: Path,
) -> dict[str, Any]:
    feature_path = find_artifact(run_dir, FEATURE_PRIORITY)
    if feature_path is None:
        raise FileNotFoundError(
            "No se encontró workspace/data_processed/phase3_features.csv; "
            "el ranking exportado no contiene todas las variables requeridas"
        )
    ranking_path = find_artifact(run_dir, RANKING_PRIORITY)
    coverage_path = find_artifact(run_dir, COVERAGE_PRIORITY)
    feature_frame = pd.read_csv(feature_path, low_memory=False)
    ranking_frame = (
        pd.read_csv(ranking_path, low_memory=False) if ranking_path else None
    )
    coverage_frame = (
        pd.read_csv(coverage_path, low_memory=False) if coverage_path else None
    )
    frame = select_analysis_frame(feature_frame, ranking_frame)
    params_path = find_params_path(run_dir, repo_root)
    params = load_config(params_path)
    stage2 = load_stage2_config(stage2_config_path)
    theory = effective_theory_config(params)
    output, summary = build_ablation(frame, theory, stage2)
    sensitivity = pd.DataFrame(summary.pop("sensitivity_rows"))
    gene_output = build_gene_summary(output)
    proxy_decomposition = build_proxy_decomposition(frame, output)
    summary.update(
        {
            "repo_head": _git(repo_root, "rev-parse", "HEAD"),
            "repo_branch": _git(repo_root, "branch", "--show-current"),
            "source_feature_table": feature_path.resolve().as_posix(),
            "source_ranking_table": (
                ranking_path.resolve().as_posix() if ranking_path else None
            ),
            "source_params": params_path.resolve().as_posix(),
            "gene_count": int(len(gene_output)),
            "gene_proxy_rank_change_count": (
                int(
                    (
                        gene_output[
                            "proxy_rank_shift_vs_without_evolutionary_information"
                        ]
                        != 0
                    ).sum()
                )
                if not gene_output.empty
                else 0
            ),
            "gene_supported_rank_change_count": (
                int(
                    (
                        gene_output[
                            "supported_rank_shift_vs_without_evolutionary_information"
                        ]
                        != 0
                    ).sum()
                )
                if not gene_output.empty
                else 0
            ),
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_output_path = output_dir / "evolutionary_ablation_by_candidate.csv"
    output.to_csv(candidate_output_path, index=False)
    gene_output.to_csv(output_dir / "evolutionary_ablation_by_gene.csv", index=False)
    proxy_decomposition.to_csv(
        output_dir / "evolutionary_proxy_decomposition.csv", index=False
    )
    sensitivity.to_csv(
        output_dir / "evolutionary_weight_sensitivity.csv", index=False
    )
    (output_dir / "evolutionary_ablation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_summary_report(
        output_dir / "evolutionary_ablation_report.md",
        output,
        gene_output,
        summary,
        feature_path,
        ranking_path,
        params_path,
    )
    stage4h_manifest = write_evolutionary_ablation_comparison_outputs(
        output_dir,
        output,
        coverage_frame,
        summary,
        ablation_source=candidate_output_path,
        coverage_source=coverage_path,
    )
    summary["stage4h_analysis_status"] = stage4h_manifest["analysis_status"]
    summary["stage4h_supported_evaluable_candidate_count"] = stage4h_manifest[
        "supported_evaluable_candidate_count"
    ]
    (output_dir / "evolutionary_ablation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=Path, default=Path("."))
    value.add_argument("--run-dir", type=Path, required=True)
    value.add_argument("--output-dir", type=Path, required=True)
    value.add_argument(
        "--stage2-config",
        type=Path,
        default=Path("config/integrated_validation_stage2.json"),
    )
    return value


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    run_dir = (
        args.run_dir if args.run_dir.is_absolute() else repo_root / args.run_dir
    )
    output_dir = (
        args.output_dir
        if args.output_dir.is_absolute()
        else repo_root / args.output_dir
    )
    config = (
        args.stage2_config
        if args.stage2_config.is_absolute()
        else repo_root / args.stage2_config
    )
    summary = run(
        repo_root=repo_root,
        run_dir=run_dir,
        output_dir=output_dir,
        stage2_config_path=config,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
