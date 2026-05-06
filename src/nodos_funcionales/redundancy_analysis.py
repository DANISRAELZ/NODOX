from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_REDUNDANCY_PARAMS = {
    "missing_data_default": 0.30,
    "paralog_weight": 0.35,
    "pathway_alternative_weight": 0.35,
    "functional_backup_weight": 0.30,
    "max_paralog_count": 5.0,
    "max_pathway_alternative_count": 5.0,
    "metabolic_bypass_weight": 0.50,
    "regulatory_bypass_weight": 0.50,
    "protective_adjustment_weight": 0.25,
}


def compute_redundancy_features(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.DataFrame:
    """Return a copy of df with interpretable Phase 3 redundancy features.

    The calculation is conservative: explicit evidence of paralogs, alternative
    pathways, metabolic bypass, regulatory bypass, or functional backup raises
    redundancy_penalty. Missing evidence uses a configurable default and is
    recorded in audit_flags instead of being treated as proof of no redundancy.
    """
    result = df.copy()
    cfg = _redundancy_config(params)
    missing_columns = _missing_columns(result)

    result["paralog_count"] = _nonnegative_number(result, "paralog_count", 0.0)
    result["pathway_alternative_count"] = _nonnegative_number(result, "pathway_alternative_count", 0.0)
    result["metabolic_bypass_score"] = _score(result, "metabolic_bypass_score", cfg["missing_data_default"])
    result["regulatory_bypass_score"] = _score(result, "regulatory_bypass_score", cfg["missing_data_default"])
    result["functional_backup_score"] = _functional_backup_score(result, cfg)
    result["redundancy_penalty"] = _redundancy_penalty(result, cfg)
    result["audit_flags"] = _append_redundancy_audit_flags(result, missing_columns)
    return result


def _redundancy_config(params: Mapping[str, object] | None) -> dict[str, float]:
    phase3 = _mapping_get(params or {}, "phase3")
    redundancy = _mapping_get(phase3, "redundancy")
    merged = dict(DEFAULT_REDUNDANCY_PARAMS)
    merged.update({str(key): float(value) for key, value in redundancy.items()})
    return merged


def _mapping_get(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key, {}) if isinstance(mapping, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _missing_columns(df: pd.DataFrame) -> list[str]:
    expected = [
        "paralog_count",
        "pathway_alternative_count",
        "functional_backup_score",
        "metabolic_bypass_score",
        "regulatory_bypass_score",
    ]
    return [column for column in expected if column not in df.columns]


def _nonnegative_number(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).clip(lower=0.0)


def _score(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return _clamp01(pd.to_numeric(df[column], errors="coerce").fillna(default))


def _functional_backup_score(df: pd.DataFrame, cfg: Mapping[str, float]) -> pd.Series:
    if "functional_backup_score" in df.columns:
        return _score(df, "functional_backup_score", cfg["missing_data_default"])
    metabolic = _score(df, "metabolic_bypass_score", cfg["missing_data_default"])
    regulatory = _score(df, "regulatory_bypass_score", cfg["missing_data_default"])
    total_weight = cfg["metabolic_bypass_weight"] + cfg["regulatory_bypass_weight"]
    if total_weight <= 0:
        return pd.Series([cfg["missing_data_default"]] * len(df), index=df.index, dtype=float)
    return _clamp01(
        (
            metabolic * cfg["metabolic_bypass_weight"]
            + regulatory * cfg["regulatory_bypass_weight"]
        )
        / total_weight
    )


def _redundancy_penalty(df: pd.DataFrame, cfg: Mapping[str, float]) -> pd.Series:
    paralog_score = _clamp01(df["paralog_count"] / cfg["max_paralog_count"])
    pathway_score = _clamp01(df["pathway_alternative_count"] / cfg["max_pathway_alternative_count"])
    total_weight = cfg["paralog_weight"] + cfg["pathway_alternative_weight"] + cfg["functional_backup_weight"]
    if total_weight <= 0:
        base_penalty = pd.Series([cfg["missing_data_default"]] * len(df), index=df.index, dtype=float)
    else:
        base_penalty = (
            paralog_score * cfg["paralog_weight"]
            + pathway_score * cfg["pathway_alternative_weight"]
            + df["functional_backup_score"] * cfg["functional_backup_weight"]
        ) / total_weight

    protective_signal = _protective_uniqueness_signal(df)
    adjusted_penalty = base_penalty * (1.0 - cfg["protective_adjustment_weight"] * protective_signal)
    return _clamp01(adjusted_penalty)


def _protective_uniqueness_signal(df: pd.DataFrame) -> pd.Series:
    low_paralog = 1.0 - _clamp01(df["paralog_count"] / 1.0)
    low_pathway = 1.0 - _clamp01(df["pathway_alternative_count"] / 1.0)
    low_backup = 1.0 - df["functional_backup_score"]
    conserved = _optional_score(df, "conservation_score", 0.50)
    essential = _essentiality_score(df)
    signals = pd.concat([low_paralog, low_pathway, low_backup, conserved, essential], axis=1)
    return _clamp01(signals.mean(axis=1))


def _essentiality_score(df: pd.DataFrame) -> pd.Series:
    if "essentiality_score" in df.columns:
        return _optional_score(df, "essentiality_score", 0.50)
    if "essential" in df.columns:
        return _clamp01(pd.to_numeric(df["essential"], errors="coerce").fillna(0.50))
    return pd.Series([0.50] * len(df), index=df.index, dtype=float)


def _optional_score(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return _clamp01(pd.to_numeric(df[column], errors="coerce").fillna(default))


def _append_redundancy_audit_flags(df: pd.DataFrame, missing_columns: list[str]) -> pd.Series:
    if missing_columns:
        flag = "redundancy_data_missing=" + "|".join(missing_columns)
    else:
        flag = "redundancy_data_complete"

    if "audit_flags" not in df.columns:
        return pd.Series([flag] * len(df), index=df.index, dtype=object)

    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return existing.map(lambda value: flag if value == "" else f"{value};{flag}")


def _clamp01(series: pd.Series) -> pd.Series:
    return series.astype(float).clip(lower=0.0, upper=1.0)
