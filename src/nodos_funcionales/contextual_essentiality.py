from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_CONTEXTUAL_ESSENTIALITY_PARAMS = {
    "missing_context_default": 0.50,
    "infection_site_weight": 0.25,
    "host_stress_weight": 0.20,
    "iron_limitation_weight": 0.15,
    "oxidative_stress_weight": 0.15,
    "intracellular_survival_weight": 0.15,
    "biofilm_weight": 0.10,
}

IRON_KEYWORDS = {
    "iron",
    "siderophore",
    "ferric",
    "ferrous",
    "heme",
    "haem",
    "pyoverdine",
    "pyochelin",
}
OXIDATIVE_KEYWORDS = {"oxidative", "peroxide", "catalase", "superoxide", "sod", "oxy", "ros"}
BIOFILM_KEYWORDS = {"biofilm", "adhesion", "adhesin", "matrix", "alginate", "quorum", "persist"}
INTRACELLULAR_KEYWORDS = {"intracellular", "macrophage", "phagosome", "acid", "vacuole"}
COLONIZATION_KEYWORDS = {"adhesion", "colonization", "colonisation", "fimbria", "pilus", "motility"}

IRON_CONTEXT_KEYWORDS = {"iron", "nutritional immunity", "blood", "serum", "abscess", "lung", "chronic"}
OXIDATIVE_CONTEXT_KEYWORDS = {"oxidative", "inflammatory", "inflamed", "macrophage", "neutrophil", "intracellular"}
BIOFILM_CONTEXT_KEYWORDS = {"biofilm", "chronic", "device", "catheter", "abscess", "cystic fibrosis", "persistent"}
INTRACELLULAR_CONTEXT_KEYWORDS = {"intracellular", "macrophage", "phagosome", "cellular"}
COLONIZATION_CONTEXT_KEYWORDS = {"early", "colonization", "colonisation", "adhesion", "mucosal"}


def compute_contextual_essentiality_features(
    df: pd.DataFrame,
    params: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Return a copy of df with Phase 3 contextual essentiality features.

    The module uses explicit curated scores when available. Otherwise it derives
    conservative signals from existing clinical, disease-context, therapy-site,
    and annotation columns. Missing infection context is imputed with a neutral
    configurable default and recorded in audit_flags.
    """
    result = df.copy()
    cfg = _contextual_config(params)
    missing_context = _context_missing(result)

    result["therapy_site_context_score"] = _therapy_site_context_score(result, cfg)
    result["infection_site_relevance_score"] = _existing_or_inferred(
        result,
        "infection_site_relevance_score",
        _infection_site_relevance_score(result, cfg),
        cfg,
    )
    result["host_stress_relevance_score"] = _existing_or_inferred(
        result,
        "host_stress_relevance_score",
        _host_stress_relevance_score(result, cfg),
        cfg,
    )
    result["iron_limitation_relevance_score"] = _existing_or_inferred(
        result,
        "iron_limitation_relevance_score",
        _keyword_context_score(result, IRON_KEYWORDS, IRON_CONTEXT_KEYWORDS, cfg),
        cfg,
    )
    result["oxidative_stress_relevance_score"] = _existing_or_inferred(
        result,
        "oxidative_stress_relevance_score",
        _keyword_context_score(result, OXIDATIVE_KEYWORDS, OXIDATIVE_CONTEXT_KEYWORDS, cfg),
        cfg,
    )
    result["intracellular_survival_score"] = _existing_or_inferred(
        result,
        "intracellular_survival_score",
        _keyword_context_score(result, INTRACELLULAR_KEYWORDS, INTRACELLULAR_CONTEXT_KEYWORDS, cfg),
        cfg,
    )
    result["biofilm_relevance_score"] = _existing_or_inferred(
        result,
        "biofilm_relevance_score",
        _keyword_context_score(result, BIOFILM_KEYWORDS, BIOFILM_CONTEXT_KEYWORDS, cfg),
        cfg,
    )

    contextual_scores = pd.DataFrame(
        {
            "infection_site": result["infection_site_relevance_score"],
            "host_stress": result["host_stress_relevance_score"],
            "iron_limitation": result["iron_limitation_relevance_score"],
            "oxidative_stress": result["oxidative_stress_relevance_score"],
            "intracellular_survival": result["intracellular_survival_score"],
            "biofilm": result["biofilm_relevance_score"],
        },
        index=result.index,
    )
    result["contextual_essentiality_score"] = _weighted_contextual_score(contextual_scores, cfg)
    result["audit_flags"] = _append_contextual_audit_flags(result, missing_context)
    return result


def _contextual_config(params: Mapping[str, object] | None) -> dict[str, float]:
    phase3 = _mapping_get(params or {}, "phase3")
    contextual = _mapping_get(phase3, "contextual_essentiality")
    merged = dict(DEFAULT_CONTEXTUAL_ESSENTIALITY_PARAMS)
    merged.update({str(key): float(value) for key, value in contextual.items()})
    return merged


def _mapping_get(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key, {}) if isinstance(mapping, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _context_missing(df: pd.DataFrame) -> bool:
    context_columns = [
        "infection_site",
        "disease_context",
        "infection_stage",
        "syndrome",
        "infection_context_score",
        "infection_site_access_score",
        "infection_site_access",
    ]
    present = [column for column in context_columns if column in df.columns and df[column].notna().any()]
    return not present


def _therapy_site_context_score(df: pd.DataFrame, cfg: Mapping[str, float]) -> pd.Series:
    if "therapy_site_context_score" in df.columns:
        return _score(df, "therapy_site_context_score", cfg["missing_context_default"])
    for column in ["infection_site_access_score", "infection_site_access"]:
        if column in df.columns:
            return _score(df, column, cfg["missing_context_default"])
    return pd.Series([cfg["missing_context_default"]] * len(df), index=df.index, dtype=float)


def _infection_site_relevance_score(df: pd.DataFrame, cfg: Mapping[str, float]) -> pd.Series:
    base = result = pd.Series([cfg["missing_context_default"]] * len(df), index=df.index, dtype=float)
    if "infection_context_score" in df.columns:
        base = _score(df, "infection_context_score", cfg["missing_context_default"])
    site = _context_text(df).map(_site_relevance_from_text)
    result = pd.concat([base, site], axis=1).max(axis=1)
    return _clamp01(result)


def _host_stress_relevance_score(df: pd.DataFrame, cfg: Mapping[str, float]) -> pd.Series:
    base = pd.Series([cfg["missing_context_default"]] * len(df), index=df.index, dtype=float)
    for column in ["clinical_impact_score", "host_damage_score", "disease_severity_association"]:
        if column in df.columns:
            base = pd.concat([base, _score(df, column, cfg["missing_context_default"])], axis=1).max(axis=1)
    context = _context_text(df).map(lambda text: 0.85 if _contains_any(text, OXIDATIVE_CONTEXT_KEYWORDS) else 0.0)
    return _clamp01(pd.concat([base, context], axis=1).max(axis=1))


def _keyword_context_score(
    df: pd.DataFrame,
    node_keywords: set[str],
    context_keywords: set[str],
    cfg: Mapping[str, float],
) -> pd.Series:
    node_text = _node_text(df)
    context_text = _context_text(df)
    node_signal = node_text.map(lambda text: 1.0 if _contains_any(text, node_keywords) else 0.0)
    context_signal = context_text.map(lambda text: 1.0 if _contains_any(text, context_keywords) else 0.0)
    explicit_context = _score(df, "infection_context_score", cfg["missing_context_default"])
    matched = node_signal * pd.concat([context_signal, explicit_context], axis=1).max(axis=1)
    neutral = pd.Series([cfg["missing_context_default"]] * len(df), index=df.index, dtype=float)
    return _clamp01(pd.concat([matched, neutral * 0.5], axis=1).max(axis=1))


def _existing_or_inferred(
    df: pd.DataFrame,
    column: str,
    inferred: pd.Series,
    cfg: Mapping[str, float],
) -> pd.Series:
    if column not in df.columns:
        return _clamp01(inferred)
    explicit = _score(df, column, cfg["missing_context_default"])
    return _clamp01(pd.concat([explicit, inferred], axis=1).max(axis=1))


def _weighted_contextual_score(scores: pd.DataFrame, cfg: Mapping[str, float]) -> pd.Series:
    weights = {
        "infection_site": cfg["infection_site_weight"],
        "host_stress": cfg["host_stress_weight"],
        "iron_limitation": cfg["iron_limitation_weight"],
        "oxidative_stress": cfg["oxidative_stress_weight"],
        "intracellular_survival": cfg["intracellular_survival_weight"],
        "biofilm": cfg["biofilm_weight"],
    }
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return pd.Series([cfg["missing_context_default"]] * len(scores), index=scores.index, dtype=float)
    weighted = sum(scores[column] * weight for column, weight in weights.items()) / total_weight
    return _clamp01(weighted)


def _node_text(df: pd.DataFrame) -> pd.Series:
    columns = [
        "gene",
        "protein_name",
        "product",
        "function",
        "annotation",
        "pathway",
        "virulence_factor",
        "phase3_notes",
        "evidence_notes",
    ]
    return _combined_text(df, columns)


def _context_text(df: pd.DataFrame) -> pd.Series:
    columns = [
        "infection_site",
        "disease_context",
        "infection_stage",
        "syndrome",
        "clinical_impact_evidence_note",
        "context_evidence_note",
        "access_evidence_note",
        "therapy_site_context_database",
        "disease_context_database",
        "clinical_impact_database",
    ]
    return _combined_text(df, columns)


def _combined_text(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    present = [column for column in columns if column in df.columns]
    if not present:
        return pd.Series([""] * len(df), index=df.index, dtype=object)
    values = df[present].fillna("").astype(str)
    return values.apply(lambda row: " ".join(row).lower(), axis=1)


def _site_relevance_from_text(text: str) -> float:
    if _contains_any(text, IRON_CONTEXT_KEYWORDS | OXIDATIVE_CONTEXT_KEYWORDS | BIOFILM_CONTEXT_KEYWORDS):
        return 0.80
    if _contains_any(text, INTRACELLULAR_CONTEXT_KEYWORDS | COLONIZATION_CONTEXT_KEYWORDS):
        return 0.70
    return 0.0


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _score(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return _clamp01(pd.to_numeric(df[column], errors="coerce").fillna(default))


def _append_contextual_audit_flags(df: pd.DataFrame, missing_context: bool) -> pd.Series:
    controlled_used = _controlled_context_used(df)
    flags = []
    if missing_context:
        flags.append("contextual_essentiality_context_missing")
    else:
        flags.append("contextual_essentiality_context_present")
    if controlled_used:
        flags.append("contextual_essentiality_controlled_context_used_no_confidence_boost")
    flag = ";".join(flags)

    if "audit_flags" not in df.columns:
        return pd.Series([flag] * len(df), index=df.index, dtype=object)

    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return existing.map(lambda value: flag if value == "" else f"{value};{flag}")


def _controlled_context_used(df: pd.DataFrame) -> bool:
    controlled_columns = [
        "clinical_impact_database",
        "disease_context_database",
        "therapy_site_context_database",
        "clinical_impact_source_name",
        "curated_disease_context_source_name",
        "therapy_site_context_source_name",
    ]
    for column in controlled_columns:
        if column in df.columns and df[column].fillna("").astype(str).str.lower().str.contains("controlled").any():
            return True
    return False


def _clamp01(series: pd.Series) -> pd.Series:
    return series.astype(float).clip(lower=0.0, upper=1.0)
