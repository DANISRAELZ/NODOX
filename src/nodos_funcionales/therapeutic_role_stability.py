from __future__ import annotations

import pandas as pd


def build_therapeutic_role_stability_audit(features: pd.DataFrame) -> pd.DataFrame:
    """Build a per-node audit comparing Phase 2 and Phase 3 therapeutic roles."""
    audit = pd.DataFrame(
        {
            "node_id": features["protein_id"],
            "gene_name": features.get("gene", pd.Series([""] * len(features), index=features.index)),
            "protein_id": features["protein_id"],
            "therapeutic_role_v2": _text(features, "therapeutic_role", "not_reported"),
            "therapeutic_role_v3": _text(features, "therapeutic_role_v3", "not_reported"),
            "meta_priority_score_v2": _score(features, "meta_priority_score_v2", 0.0),
            "meta_priority_score_v3": _score(features, "meta_priority_score_v3", 0.0),
            "controlled_provider_used": _controlled_provider_used(features),
            "evidence_quality_score": _score(features, "evidence_quality_score", 0.0),
            "confidence_ceiling": _score(features, "confidence_ceiling", 1.0),
            "audit_flags": _text(features, "audit_flags", ""),
        }
    )
    audit["gene_name/protein_id"] = audit.apply(_gene_or_protein_label, axis=1)
    audit["role_changed"] = audit["therapeutic_role_v2"] != audit["therapeutic_role_v3"]
    audit["score_delta"] = (audit["meta_priority_score_v3"] - audit["meta_priority_score_v2"]).round(4)
    audit["role_change_type"] = audit.apply(_role_change_type, axis=1)
    audit["stability_label"] = features.apply(lambda row: _stability_label(row, audit.loc[row.name]), axis=1)
    return audit[
        [
            "node_id",
            "gene_name/protein_id",
            "gene_name",
            "protein_id",
            "therapeutic_role_v2",
            "therapeutic_role_v3",
            "role_changed",
            "role_change_type",
            "meta_priority_score_v2",
            "meta_priority_score_v3",
            "score_delta",
            "controlled_provider_used",
            "evidence_quality_score",
            "confidence_ceiling",
            "stability_label",
            "audit_flags",
        ]
    ]


def _gene_or_protein_label(row: pd.Series) -> str:
    gene = str(row.get("gene_name", "") or "").strip()
    protein = str(row.get("protein_id", "") or "").strip()
    if gene and gene.lower() not in {"nan", "none", "unknown"}:
        return gene
    return protein


def build_therapeutic_role_stability_report(audit: pd.DataFrame) -> str:
    """Render a short Markdown report from therapeutic role stability audit rows."""
    changed = int(audit["role_changed"].sum()) if "role_changed" in audit.columns else 0
    controlled = int(audit["controlled_provider_used"].sum()) if "controlled_provider_used" in audit.columns else 0
    low_conf = int(audit["stability_label"].eq("stable_low_confidence").sum()) if "stability_label" in audit.columns else 0
    lines = [
        "# Therapeutic Role Stability Audit",
        "",
        "Este reporte compara el rol terapeutico de Fase 2 contra Fase 3 y resume si los cambios parecen depender de penalizaciones evolutivas, esencialidad contextual, calidad de evidencia o proveedor controlado.",
        "",
        "## Resumen",
        "",
        f"- Nodos evaluados: {len(audit)}",
        f"- Roles cambiados: {changed}",
        f"- Nodos con proveedor controlado usado: {controlled}",
        f"- Nodos estables con baja confianza: {low_conf}",
        "",
        "## Distribucion de stability_label",
        "",
        _markdown_table(audit["stability_label"].value_counts().rename_axis("stability_label").reset_index(name="count")),
        "",
        "## Cambios principales",
        "",
        _markdown_table(audit.sort_values("score_delta", ascending=True).head(10)),
    ]
    return "\n".join(lines)


def _stability_label(feature_row: pd.Series, audit_row: pd.Series) -> str:
    if _missing_core_values(audit_row):
        return "insufficient_data"
    if bool(audit_row["role_changed"]):
        if float(feature_row.get("evolutionary_escape_risk_score", 0.0) or 0.0) >= 0.65 or float(audit_row["score_delta"]) < -0.10:
            return "changed_due_to_evolutionary_penalty"
        if float(feature_row.get("contextual_essentiality_score", 0.0) or 0.0) >= 0.70 or float(audit_row["score_delta"]) > 0.10:
            return "changed_due_to_contextual_essentiality"
        if float(audit_row["evidence_quality_score"]) < 0.35 or float(audit_row["confidence_ceiling"]) <= 0.50:
            return "changed_due_to_evidence_quality"
        if bool(audit_row["controlled_provider_used"]):
            return "changed_due_to_controlled_provider"
        return "changed_due_to_evidence_quality"
    if bool(audit_row["controlled_provider_used"]) and float(audit_row["confidence_ceiling"]) <= 0.50:
        return "changed_due_to_controlled_provider"
    if float(audit_row["evidence_quality_score"]) >= 0.70 and float(audit_row["confidence_ceiling"]) >= 0.70:
        return "stable_high_confidence"
    return "stable_low_confidence"


def _role_change_type(row: pd.Series) -> str:
    if not bool(row["role_changed"]):
        return "unchanged"
    if float(row["score_delta"]) > 0:
        return "role_changed_score_increased"
    if float(row["score_delta"]) < 0:
        return "role_changed_score_decreased"
    return "role_changed_without_score_delta"


def _controlled_provider_used(features: pd.DataFrame) -> pd.Series:
    flags = []
    for column in [
        "controlled_dependency_flags",
        "clinical_impact_database",
        "disease_context_database",
        "therapy_site_context_database",
        "evidence_source_type",
        "audit_flags",
    ]:
        if column in features.columns:
            flags.append(features[column].fillna("").astype(str).str.lower().str.contains("controlled"))
    for column in [
        "clinical_impact_controlled_dependency",
        "curated_disease_context_controlled_dependency",
        "therapy_site_context_controlled_dependency",
    ]:
        if column in features.columns:
            flags.append(features[column].fillna(False).astype(bool))
    if not flags:
        return pd.Series([False] * len(features), index=features.index)
    return pd.concat(flags, axis=1).any(axis=1)


def _missing_core_values(row: pd.Series) -> bool:
    return (
        str(row.get("therapeutic_role_v2", "not_reported")) == "not_reported"
        or str(row.get("therapeutic_role_v3", "not_reported")) == "not_reported"
    )


def _score(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float).clip(lower=0.0, upper=1.0)


def _text(df: pd.DataFrame, column: str, default: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=object)
    return df[column].fillna(default).astype(str)


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas para reportar._"
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].round(3)
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in display.iterrows():
        values = [str(row.get(column, "")).replace("\n", " ") for column in display.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)
