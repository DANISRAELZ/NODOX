from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_COLLATERAL_SENSITIVITY_PARAMS = {
    "enabled": True,
    "default_score": 0.0,
    "rule_based_mode": True,
}

OXIDATIVE_STRESS_KEYWORDS = {"oxidative", "peroxide", "catalase", "superoxide", "sod", "ros", "stress response"}
BIOFILM_KEYWORDS = {"biofilm", "matrix", "alginate", "pellicle", "persist", "persistence"}
ENERGY_METABOLISM_KEYWORDS = {
    "respiration",
    "electron transport",
    "atp",
    "energy",
    "dehydrogenase",
    "oxidase",
    "metabolism",
}
IRON_KEYWORDS = {"iron", "siderophore", "pyoverdine", "pyochelin", "heme", "haem", "ferric", "ferrous"}
VIRULENCE_KEYWORDS = {"toxin", "adhesin", "virulence", "secretion", "immune evasion", "colonization", "colonisation"}
DNA_REPAIR_KEYWORDS = {"dna repair", "reca", "uvr", "mut", "mismatch repair", "recombinase", "topoisomerase"}


def compute_collateral_sensitivity_features(
    df: pd.DataFrame,
    params: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Return a copy of df with rule-based collateral sensitivity opportunities.

    Recommendations are mechanistic hypotheses, not experimental evidence. The
    module marks inferred recommendations in audit_flags.
    """
    result = df.copy()
    cfg = _collateral_config(params)
    if not cfg["enabled"]:
        return _disabled_result(result, cfg)

    text = _node_text(result)
    rules = pd.DataFrame(
        {
            "oxidative_stress": _rule_signal(result, text, "oxidative_stress_relevance_score", OXIDATIVE_STRESS_KEYWORDS),
            "biofilm": _rule_signal(result, text, "biofilm_persistence_score", BIOFILM_KEYWORDS),
            "energy_metabolism": _rule_signal(result, text, "energy_metabolism_score", ENERGY_METABOLISM_KEYWORDS),
            "iron_acquisition": _rule_signal(
                result,
                text,
                "nutritional_immunity_escape_score",
                IRON_KEYWORDS,
            ),
            "virulence": _virulence_rule_signal(result, text),
            "dna_repair": _rule_signal(result, text, "dna_repair_score", DNA_REPAIR_KEYWORDS),
        },
        index=result.index,
    )
    selected_rule = rules.idxmax(axis=1)
    selected_score = rules.max(axis=1).clip(lower=0.0, upper=1.0)
    selected_rule = selected_rule.where(selected_score > 0.0, "unknown")

    result["collateral_sensitivity_score"] = _existing_or_selected(result, "collateral_sensitivity_score", selected_score, cfg)
    result["combination_opportunity_score"] = _existing_or_selected(
        result,
        "combination_opportunity_score",
        _combination_opportunity_score(result, selected_score),
        cfg,
    )
    result["recommended_combination_class"] = selected_rule.map(_combination_class)
    result["escape_creates_vulnerability"] = selected_rule.map(lambda rule: rule != "unknown")
    result["combination_rationale"] = selected_rule.map(_combination_rationale)
    result["audit_flags"] = _append_collateral_audit_flags(result)
    return result


def _collateral_config(params: Mapping[str, object] | None) -> dict[str, object]:
    phase3 = _mapping_get(params or {}, "phase3")
    collateral = _mapping_get(phase3, "collateral_sensitivity")
    merged = dict(DEFAULT_COLLATERAL_SENSITIVITY_PARAMS)
    merged.update(collateral)
    merged["enabled"] = bool(merged["enabled"])
    merged["default_score"] = float(merged["default_score"])
    merged["rule_based_mode"] = bool(merged["rule_based_mode"])
    return merged


def _mapping_get(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key, {}) if isinstance(mapping, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _disabled_result(df: pd.DataFrame, cfg: Mapping[str, object]) -> pd.DataFrame:
    result = df.copy()
    result["collateral_sensitivity_score"] = _score(result, "collateral_sensitivity_score", float(cfg["default_score"]))
    result["combination_opportunity_score"] = _score(result, "combination_opportunity_score", float(cfg["default_score"]))
    result["recommended_combination_class"] = "not_available"
    result["escape_creates_vulnerability"] = False
    result["combination_rationale"] = "Collateral sensitivity module disabled."
    result["audit_flags"] = _append_flag(result, "collateral_sensitivity_disabled")
    return result


def _rule_signal(df: pd.DataFrame, text: pd.Series, explicit_column: str, keywords: set[str]) -> pd.Series:
    explicit = _score(df, explicit_column, 0.0)
    keyword = text.map(lambda value: 1.0 if any(keyword in value for keyword in keywords) else 0.0).astype(float)
    return pd.concat([explicit, keyword], axis=1).max(axis=1).clip(lower=0.0, upper=1.0)


def _virulence_rule_signal(df: pd.DataFrame, text: pd.Series) -> pd.Series:
    candidates = [
        _rule_signal(df, text, "virulence_severity_score", VIRULENCE_KEYWORDS),
        _score(df, "direct_host_damage_score", 0.0),
        _score(df, "colonization_score", 0.0),
        _score(df, "immune_evasion_score", 0.0),
        _score(df, "toxin_activity_score", 0.0),
    ]
    return pd.concat(candidates, axis=1).max(axis=1).clip(lower=0.0, upper=1.0)


def _combination_opportunity_score(df: pd.DataFrame, selected_score: pd.Series) -> pd.Series:
    evidence_quality = _score(df, "evidence_quality_score", 0.5)
    context = _score(df, "contextual_essentiality_score", 0.5)
    return (0.60 * selected_score + 0.25 * context + 0.15 * evidence_quality).clip(lower=0.0, upper=1.0)


def _existing_or_selected(
    df: pd.DataFrame,
    column: str,
    selected: pd.Series,
    cfg: Mapping[str, object],
) -> pd.Series:
    if column not in df.columns:
        return selected.fillna(float(cfg["default_score"])).clip(lower=0.0, upper=1.0)
    explicit = _score(df, column, float(cfg["default_score"]))
    return pd.concat([explicit, selected], axis=1).max(axis=1).clip(lower=0.0, upper=1.0)


def _combination_class(rule: str) -> str:
    return {
        "oxidative_stress": "oxidative_damage_adjuvant",
        "biofilm": "antibiofilm_or_beta_lactam_combination",
        "energy_metabolism": "metabolism_dependent_bactericidal_combination",
        "iron_acquisition": "nutritional_immunity_or_siderophore_strategy",
        "virulence": "conventional_antibiotic_or_immune_therapy",
        "dna_repair": "quinolone_or_genomic_damage_combination",
        "unknown": "unknown",
    }.get(rule, "unknown")


def _combination_rationale(rule: str) -> str:
    return {
        "oxidative_stress": (
            "Rule-based hypothesis: disrupting an oxidative stress node may sensitize bacteria to "
            "quinolones, aminoglycosides, or treatments that increase oxidative damage."
        ),
        "biofilm": (
            "Rule-based hypothesis: disrupting a biofilm node may improve exposure to beta-lactams, "
            "penetration-improved antibiotics, or antibiofilm agents."
        ),
        "energy_metabolism": (
            "Rule-based hypothesis: disrupting energy metabolism may create vulnerability to "
            "bactericidal treatments that depend on active metabolism or cellular damage."
        ),
        "iron_acquisition": (
            "Rule-based hypothesis: disrupting iron acquisition may pair with prooxidant antibiotics, "
            "siderophore-linked strategies, or nutritional-immunity pressure."
        ),
        "virulence": (
            "Rule-based hypothesis: reducing virulence may combine with conventional antibiotics or "
            "immune-directed therapy without claiming direct bactericidal evidence."
        ),
        "dna_repair": (
            "Rule-based hypothesis: disrupting DNA repair may increase vulnerability to quinolones or "
            "other genome-damage-inducing treatments."
        ),
        "unknown": "No rule-based collateral sensitivity opportunity was identified from available fields.",
    }.get(rule, "No rule-based collateral sensitivity opportunity was identified from available fields.")


def _node_text(df: pd.DataFrame) -> pd.Series:
    columns = [
        "gene",
        "protein_name",
        "product",
        "function",
        "annotation",
        "pathway",
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
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float).clip(lower=0.0, upper=1.0)


def _append_collateral_audit_flags(df: pd.DataFrame) -> pd.Series:
    inferred = df["recommended_combination_class"].ne("unknown") & df["recommended_combination_class"].ne("not_available")
    flags = inferred.map(
        lambda value: "collateral_sensitivity_rule_based_inference"
        if bool(value)
        else "collateral_sensitivity_no_rule_available"
    )
    if "audit_flags" not in df.columns:
        return flags.astype(object)
    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return pd.Series(
        [
            flag if current == "" else f"{current};{flag}"
            for current, flag in zip(existing, flags, strict=False)
        ],
        index=df.index,
        dtype=object,
    )


def _append_flag(df: pd.DataFrame, flag: str) -> pd.Series:
    if "audit_flags" not in df.columns:
        return pd.Series([flag] * len(df), index=df.index, dtype=object)
    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return existing.map(lambda value: flag if value == "" else f"{value};{flag}")
