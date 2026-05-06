from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_VIRULENCE_LAYER_PARAMS = {
    "missing_signal_default": 0.0,
    "direct_host_damage_weight": 0.20,
    "colonization_weight": 0.15,
    "immune_evasion_weight": 0.15,
    "biofilm_persistence_weight": 0.15,
    "toxin_activity_weight": 0.15,
    "nutritional_immunity_escape_weight": 0.10,
    "quorum_sensing_weight": 0.10,
}

DIRECT_DAMAGE_KEYWORDS = {
    "elastase",
    "protease",
    "hemolysin",
    "haemolysin",
    "phospholipase",
    "tissue damage",
    "cytotoxic",
    "exotoxin",
}
TOXIN_KEYWORDS = {"toxin", "exotoxin", "endotoxin", "hemolysin", "haemolysin", "cytotoxin", "type iii"}
COLONIZATION_KEYWORDS = {
    "adhesin",
    "adhesion",
    "colonization",
    "colonisation",
    "pilus",
    "fimbria",
    "surface protein",
    "outer membrane",
}
IMMUNE_EVASION_KEYWORDS = {
    "immune evasion",
    "complement",
    "capsule",
    "antigenic",
    "serum resistance",
    "phagocytosis",
}
BIOFILM_KEYWORDS = {"biofilm", "matrix", "alginate", "pellicle", "persist", "persistence", "adhesion"}
NUTRITIONAL_IMMUNITY_KEYWORDS = {
    "iron",
    "siderophore",
    "pyoverdine",
    "pyochelin",
    "heme",
    "haem",
    "ferric",
    "ferrous",
}
QUORUM_KEYWORDS = {"quorum", "agr", "lux", "lasr", "lasi", "rhlr", "rhli", "pqs", "autoinducer"}


def compute_virulence_layer_features(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.DataFrame:
    """Return a copy of df with interpretable antivirulence sublayers.

    Existing explicit sublayer columns are preserved and clipped to 0-1. Missing
    sublayers are inferred from text annotations when possible. The legacy
    antivirulence_target_score is not removed or recalculated here.
    """
    result = df.copy()
    cfg = _virulence_config(params)
    text = _virulence_text(result)
    missing_layers = _missing_layer_columns(result)

    result["toxin_activity_score"] = _existing_or_keyword_score(
        result,
        "toxin_activity_score",
        text,
        TOXIN_KEYWORDS,
        cfg,
    )
    direct_damage_inferred = pd.concat(
        [
            _keyword_score(text, DIRECT_DAMAGE_KEYWORDS),
            result["toxin_activity_score"] * 0.85,
        ],
        axis=1,
    ).max(axis=1)
    result["direct_host_damage_score"] = _existing_or_inferred(
        result,
        "direct_host_damage_score",
        direct_damage_inferred,
        cfg,
    )
    result["colonization_score"] = _existing_or_keyword_score(result, "colonization_score", text, COLONIZATION_KEYWORDS, cfg)
    result["immune_evasion_score"] = _existing_or_keyword_score(result, "immune_evasion_score", text, IMMUNE_EVASION_KEYWORDS, cfg)
    result["biofilm_persistence_score"] = _existing_or_keyword_score(
        result,
        "biofilm_persistence_score",
        text,
        BIOFILM_KEYWORDS,
        cfg,
    )
    result["nutritional_immunity_escape_score"] = _existing_or_keyword_score(
        result,
        "nutritional_immunity_escape_score",
        text,
        NUTRITIONAL_IMMUNITY_KEYWORDS,
        cfg,
    )
    result["quorum_sensing_score"] = _existing_or_keyword_score(result, "quorum_sensing_score", text, QUORUM_KEYWORDS, cfg)
    result["virulence_severity_score"] = _virulence_severity_score(result, cfg)
    result["audit_flags"] = _append_virulence_audit_flags(result, missing_layers)
    return result


def _virulence_config(params: Mapping[str, object] | None) -> dict[str, float]:
    phase3 = _mapping_get(params or {}, "phase3")
    virulence_layers = _mapping_get(phase3, "virulence_layers")
    merged = dict(DEFAULT_VIRULENCE_LAYER_PARAMS)
    merged.update({str(key): float(value) for key, value in virulence_layers.items()})
    return merged


def _mapping_get(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key, {}) if isinstance(mapping, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _missing_layer_columns(df: pd.DataFrame) -> list[str]:
    expected = [
        "direct_host_damage_score",
        "colonization_score",
        "immune_evasion_score",
        "biofilm_persistence_score",
        "toxin_activity_score",
        "nutritional_immunity_escape_score",
        "quorum_sensing_score",
    ]
    return [column for column in expected if column not in df.columns]


def _existing_or_keyword_score(
    df: pd.DataFrame,
    column: str,
    text: pd.Series,
    keywords: set[str],
    cfg: Mapping[str, float],
) -> pd.Series:
    return _existing_or_inferred(df, column, _keyword_score(text, keywords), cfg)


def _existing_or_inferred(
    df: pd.DataFrame,
    column: str,
    inferred: pd.Series,
    cfg: Mapping[str, float],
) -> pd.Series:
    if column not in df.columns:
        return _clamp01(inferred.fillna(cfg["missing_signal_default"]))
    explicit = _score(df, column, cfg["missing_signal_default"])
    return _clamp01(pd.concat([explicit, inferred], axis=1).max(axis=1))


def _keyword_score(text: pd.Series, keywords: set[str]) -> pd.Series:
    return text.map(lambda value: 1.0 if any(keyword in value for keyword in keywords) else 0.0).astype(float)


def _virulence_severity_score(df: pd.DataFrame, cfg: Mapping[str, float]) -> pd.Series:
    weights = {
        "direct_host_damage_score": cfg["direct_host_damage_weight"],
        "colonization_score": cfg["colonization_weight"],
        "immune_evasion_score": cfg["immune_evasion_weight"],
        "biofilm_persistence_score": cfg["biofilm_persistence_weight"],
        "toxin_activity_score": cfg["toxin_activity_weight"],
        "nutritional_immunity_escape_score": cfg["nutritional_immunity_escape_weight"],
        "quorum_sensing_score": cfg["quorum_sensing_weight"],
    }
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return pd.Series([0.0] * len(df), index=df.index, dtype=float)
    weighted = sum(df[column] * weight for column, weight in weights.items()) / total_weight
    return _clamp01(weighted)


def _virulence_text(df: pd.DataFrame) -> pd.Series:
    columns = [
        "gene",
        "protein_name",
        "product",
        "function",
        "annotation",
        "pathway",
        "virulence_factor",
        "evidence",
        "evidence_notes",
        "phase3_notes",
    ]
    present = [column for column in columns if column in df.columns]
    if not present:
        return pd.Series([""] * len(df), index=df.index, dtype=object)
    values = df[present].fillna("").astype(str)
    return values.apply(lambda row: " ".join(row).lower(), axis=1)


def _score(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return _clamp01(pd.to_numeric(df[column], errors="coerce").fillna(default))


def _append_virulence_audit_flags(df: pd.DataFrame, missing_layers: list[str]) -> pd.Series:
    if missing_layers:
        flag = "virulence_layers_inferred_or_defaulted=" + "|".join(missing_layers)
    else:
        flag = "virulence_layers_explicit"
    if "antivirulence_target_score" in df.columns:
        flag = f"{flag};antivirulence_target_score_preserved"

    if "audit_flags" not in df.columns:
        return pd.Series([flag] * len(df), index=df.index, dtype=object)

    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return existing.map(lambda value: flag if value == "" else f"{value};{flag}")


def _clamp01(series: pd.Series) -> pd.Series:
    return series.astype(float).clip(lower=0.0, upper=1.0)
