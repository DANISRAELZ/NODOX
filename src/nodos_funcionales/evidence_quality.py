from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


DEFAULT_EVIDENCE_QUALITY_PARAMS = {
    "default_quality": 0.0,
    "demo_only_ceiling": 0.40,
    "controlled_provider_only_ceiling": 0.50,
    "external_database_ceiling": 0.70,
    "curated_literature_ceiling": 0.80,
    "user_external_curated_ceiling": 0.95,
    "experimental_ceiling": 1.0,
    "user_data_weight": 0.25,
    "curated_literature_weight": 0.25,
    "external_database_weight": 0.20,
    "experimental_weight": 0.25,
    "multi_source_weight": 0.05,
    "demo_penalty_weight": 0.25,
    "controlled_only_penalty_weight": 0.20,
    "conflict_penalty_weight": 0.25,
}

SOURCE_COLUMNS = [
    "source_database",
    "essentiality_database",
    "virulence_database",
    "homology_database",
    "localization_database",
    "clinical_impact_database",
    "disease_context_database",
    "therapy_site_context_database",
    "host_annotation_database",
    "functional_network_database",
    "conservation_database",
    "database",
]

SOURCE_TYPE_COLUMNS = [
    "evidence_source_type",
    "confidence_source_class",
    "essentiality_source_type",
    "virulence_source_type",
    "human_homologs_source_type",
    "localization_source_type",
    "clinical_impact_source_type",
    "curated_disease_context_source_type",
    "therapy_site_context_source_type",
    "host_annotation_source_type",
    "functional_network_source_type",
    "strain_conservation_source_type",
]

EVIDENCE_TEXT_COLUMNS = [
    "evidence",
    "evidence_type",
    "clinical_impact_evidence_type",
    "context_evidence_type",
    "access_evidence_type",
    "evidence_notes",
    "clinical_impact_evidence_note",
    "context_evidence_note",
    "access_evidence_note",
    "audit_flags",
]


def compute_evidence_quality_features(df: pd.DataFrame, params: Mapping[str, object] | None = None) -> pd.DataFrame:
    """Return a copy of df with Phase 3 evidence quality and confidence ceiling fields.

    This module does not remove or replace existing confidence logic. It adds a
    stricter, traceable ceiling so weak, demo, or controlled-only evidence cannot
    inflate confidence beyond an explicit methodological cap.
    """
    result = df.copy()
    cfg = _evidence_config(params)
    source_text = _combined_text(result, SOURCE_COLUMNS + SOURCE_TYPE_COLUMNS + EVIDENCE_TEXT_COLUMNS)

    result["user_data_support"] = _boolean_support(result, "user_data_support", _user_support(result, source_text))
    result["curated_literature_support"] = _boolean_support(
        result,
        "curated_literature_support",
        _curated_support(source_text),
    )
    result["external_database_support"] = _boolean_support(
        result,
        "external_database_support",
        _external_support(result, source_text),
    )
    result["experimental_support"] = _boolean_support(result, "experimental_support", _experimental_support(source_text))
    if "demo_data_penalty" in result.columns:
        result["demo_data_penalty"] = _score(result, "demo_data_penalty", 0.0)
    else:
        result["demo_data_penalty"] = _demo_penalty(result, source_text)
    controlled_present = _controlled_present(source_text)
    high_quality_support_count = (
        result["user_data_support"].astype(int)
        + result["curated_literature_support"].astype(int)
        + result["external_database_support"].astype(int)
        + result["experimental_support"].astype(int)
    )
    controlled_only = controlled_present & high_quality_support_count.eq(0)
    result["controlled_provider_cap"] = controlled_only.astype(float) * float(cfg["controlled_provider_only_ceiling"])

    conflict = _conflicting_evidence(result, source_text)
    raw_quality = _raw_evidence_quality(result, controlled_only, conflict, cfg)
    result["confidence_ceiling"] = _confidence_ceiling(result, controlled_only, cfg)
    result["evidence_quality_score"] = raw_quality.clip(upper=result["confidence_ceiling"]).clip(lower=0.0, upper=1.0)
    result["evidence_source_type"] = _evidence_source_type(result, controlled_only)
    result["evidence_notes"] = _evidence_notes(result, controlled_only, conflict)
    result["audit_flags"] = _append_evidence_audit_flags(result, controlled_only, conflict, raw_quality)
    return result


def _evidence_config(params: Mapping[str, object] | None) -> dict[str, float]:
    phase3 = _mapping_get(params or {}, "phase3")
    evidence_quality = _mapping_get(phase3, "evidence_quality")
    merged = dict(DEFAULT_EVIDENCE_QUALITY_PARAMS)
    merged.update(
        {
            str(key): float(value)
            for key, value in evidence_quality.items()
            if not isinstance(value, Mapping)
        }
    )
    return merged


def _mapping_get(mapping: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = mapping.get(key, {}) if isinstance(mapping, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _raw_evidence_quality(
    df: pd.DataFrame,
    controlled_only: pd.Series,
    conflict: pd.Series,
    cfg: Mapping[str, float],
) -> pd.Series:
    multi_source = (
        df[
            [
                "user_data_support",
                "curated_literature_support",
                "external_database_support",
                "experimental_support",
            ]
        ]
        .astype(int)
        .sum(axis=1)
        .clip(upper=3)
        / 3.0
    )
    quality = (
        df["user_data_support"].astype(float) * cfg["user_data_weight"]
        + df["curated_literature_support"].astype(float) * cfg["curated_literature_weight"]
        + df["external_database_support"].astype(float) * cfg["external_database_weight"]
        + df["experimental_support"].astype(float) * cfg["experimental_weight"]
        + multi_source * cfg["multi_source_weight"]
    )
    quality = quality - df["demo_data_penalty"] * cfg["demo_penalty_weight"]
    quality = quality - controlled_only.astype(float) * cfg["controlled_only_penalty_weight"]
    quality = quality - conflict.astype(float) * cfg["conflict_penalty_weight"]
    return quality.fillna(float(cfg["default_quality"])).clip(lower=0.0, upper=1.0)


def _confidence_ceiling(df: pd.DataFrame, controlled_only: pd.Series, cfg: Mapping[str, float]) -> pd.Series:
    ceiling = pd.Series([0.50] * len(df), index=df.index, dtype=float)
    demo_only = df["demo_data_penalty"].gt(0) & ~(
        df["user_data_support"]
        | df["curated_literature_support"]
        | df["external_database_support"]
        | df["experimental_support"]
    )
    ceiling.loc[demo_only] = cfg["demo_only_ceiling"]
    ceiling.loc[controlled_only] = cfg["controlled_provider_only_ceiling"]
    ceiling.loc[df["external_database_support"]] = cfg["external_database_ceiling"]
    ceiling.loc[df["curated_literature_support"]] = cfg["curated_literature_ceiling"]
    strong_combo = df["user_data_support"] & df["external_database_support"] & df["curated_literature_support"]
    ceiling.loc[strong_combo] = cfg["user_external_curated_ceiling"]
    ceiling.loc[df["experimental_support"]] = cfg["experimental_ceiling"]
    return ceiling.clip(lower=0.0, upper=1.0)


def _evidence_source_type(df: pd.DataFrame, controlled_only: pd.Series) -> pd.Series:
    source_type = pd.Series(["not_assessed"] * len(df), index=df.index, dtype=object)
    source_type.loc[df["demo_data_penalty"].gt(0)] = "demo"
    source_type.loc[controlled_only] = "controlled_provider"
    source_type.loc[df["external_database_support"]] = "external_database"
    source_type.loc[df["curated_literature_support"]] = "curated_literature"
    source_type.loc[df["user_data_support"]] = "user_data"
    source_type.loc[
        df["user_data_support"] & df["external_database_support"] & df["curated_literature_support"]
    ] = "user_external_curated"
    source_type.loc[df["experimental_support"]] = "experimental"
    return source_type


def _evidence_notes(df: pd.DataFrame, controlled_only: pd.Series, conflict: pd.Series) -> pd.Series:
    notes = []
    for idx in df.index:
        row_notes = []
        if bool(df.loc[idx, "user_data_support"]):
            row_notes.append("user data present")
        if bool(df.loc[idx, "curated_literature_support"]):
            row_notes.append("curated literature present")
        if bool(df.loc[idx, "external_database_support"]):
            row_notes.append("external database present")
        if bool(df.loc[idx, "experimental_support"]):
            row_notes.append("experimental support present")
        if float(df.loc[idx, "demo_data_penalty"]) > 0:
            row_notes.append("demo data used")
        if bool(controlled_only.loc[idx]):
            row_notes.append("controlled provider only")
        if bool(conflict.loc[idx]):
            row_notes.append("conflicting evidence")
        notes.append("; ".join(row_notes) if row_notes else "no strong evidence source detected")
    return pd.Series(notes, index=df.index, dtype=object)


def _append_evidence_audit_flags(
    df: pd.DataFrame,
    controlled_only: pd.Series,
    conflict: pd.Series,
    raw_quality: pd.Series,
) -> pd.Series:
    flags_by_row = []
    capped = raw_quality.gt(df["confidence_ceiling"])
    for idx in df.index:
        flags = []
        if float(df.loc[idx, "demo_data_penalty"]) > 0:
            flags.append("demo_data_used")
        if bool(controlled_only.loc[idx]):
            flags.append("controlled_provider_only")
        if bool(df.loc[idx, "external_database_support"]):
            flags.append("external_evidence_present")
        if bool(df.loc[idx, "curated_literature_support"]):
            flags.append("curated_literature_present")
        if bool(df.loc[idx, "experimental_support"]):
            flags.append("experimental_support_present")
        if bool(conflict.loc[idx]):
            flags.append("conflicting_evidence")
        if bool(capped.loc[idx]):
            flags.append("confidence_capped")
        if not flags:
            flags.append("evidence_quality_no_strong_source")
        flags_by_row.append(";".join(flags))

    new_flags = pd.Series(flags_by_row, index=df.index, dtype=object)
    if "audit_flags" not in df.columns:
        return new_flags
    existing = df["audit_flags"].fillna("").astype(str).str.strip()
    return pd.Series(
        [
            flag if current == "" else f"{current};{flag}"
            for current, flag in zip(existing, new_flags, strict=False)
        ],
        index=df.index,
        dtype=object,
    )


def _user_support(df: pd.DataFrame, source_text: pd.Series) -> pd.Series:
    explicit_columns = [column for column in df.columns if column.endswith("_is_user_supplied")]
    explicit = (
        pd.DataFrame({column: df[column].fillna(False).astype(bool) for column in explicit_columns}).any(axis=1)
        if explicit_columns
        else pd.Series([False] * len(df), index=df.index)
    )
    text = source_text.str.contains("user|data_user|user_data", regex=True)
    return explicit | text


def _curated_support(source_text: pd.Series) -> pd.Series:
    curated = source_text.str.contains("curated_literature|literature|doi|pubmed|manual_catalog", regex=True)
    demo = source_text.str.contains("demo|example_", regex=True)
    return curated & ~demo


def _external_support(df: pd.DataFrame, source_text: pd.Series) -> pd.Series:
    explicit_columns = [column for column in df.columns if column.endswith("_is_external")]
    explicit = (
        pd.DataFrame({column: df[column].fillna(False).astype(bool) for column in explicit_columns}).any(axis=1)
        if explicit_columns
        else pd.Series([False] * len(df), index=df.index)
    )
    text = source_text.str.contains("external|uniprot|string|vfdb|deg|bvbrc|interpro|database", regex=True)
    return explicit | text


def _experimental_support(source_text: pd.Series) -> pd.Series:
    return source_text.str.contains("experimental|validated|tn-seq|tnseq|knockout|assay", regex=True)


def _demo_penalty(df: pd.DataFrame, source_text: pd.Series) -> pd.Series:
    demo = source_text.str.contains("demo|example_", regex=True)
    if "data_realism_flag" in df.columns:
        demo = demo | df["data_realism_flag"].fillna("").astype(str).str.lower().eq("demo_only")
    return demo.astype(float)


def _controlled_present(source_text: pd.Series) -> pd.Series:
    return source_text.str.contains("controlled|provider_controlled", regex=True)


def _conflicting_evidence(df: pd.DataFrame, source_text: pd.Series) -> pd.Series:
    conflict = source_text.str.contains("conflict|discordant|contradict", regex=True)
    for column in ["conflicting_evidence", "evidence_conflict", "has_conflicting_evidence"]:
        if column in df.columns:
            conflict = conflict | df[column].fillna(False).astype(bool)
    if "evidence_conflict_score" in df.columns:
        conflict = conflict | pd.to_numeric(df["evidence_conflict_score"], errors="coerce").fillna(0.0).gt(0)
    return conflict


def _boolean_support(df: pd.DataFrame, column: str, inferred: pd.Series) -> pd.Series:
    if column not in df.columns:
        return inferred.fillna(False).astype(bool)
    explicit = df[column].fillna(False).astype(bool)
    return explicit | inferred.fillna(False).astype(bool)


def _score(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float).clip(lower=0.0, upper=1.0)


def _combined_text(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    present = [column for column in columns if column in df.columns]
    if not present:
        return pd.Series([""] * len(df), index=df.index, dtype=object)
    values = df[present].fillna("").astype(str)
    return values.apply(lambda row: " ".join(row).lower(), axis=1)
