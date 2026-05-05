from __future__ import annotations

import pandas as pd


def build_simple_candidate_explanations(ranking: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Build non-technical explanations without adding scientific claims."""
    rows: list[dict[str, object]] = []
    for rank, (_, row) in enumerate(ranking.head(top_n).iterrows(), start=1):
        rows.append(
            {
                "rank": rank,
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "therapeutic_role": row.get("therapeutic_role", "not_reported"),
                "why_prioritized": explain_prioritization(row),
                "supporting_evidence": explain_supporting_evidence(row),
                "missing_evidence": explain_missing_evidence(row),
                "sources_used": explain_sources_used(row),
                "confidence_level": explain_confidence(row),
            }
        )
    return pd.DataFrame(rows)


def build_simple_candidate_explanations_markdown(explanations: pd.DataFrame) -> str:
    lines = [
        "# Explicacion Simple de Candidatos",
        "",
        "Este reporte usa lenguaje no tecnico. Resume por que el pipeline priorizo cada nodo, que evidencia existe y que falta. No afirma validacion experimental.",
        "",
    ]
    if explanations.empty:
        lines.append("_No hay candidatos para explicar._")
        return "\n".join(lines)
    for _, row in explanations.iterrows():
        lines.extend(
            [
                f"## {int(row.get('rank', 0))}. {row.get('gene', '')} ({row.get('protein_id', '')})",
                "",
                f"- Rol sugerido: `{row.get('therapeutic_role', 'not_reported')}`",
                f"- Por que fue priorizado: {row.get('why_prioritized', 'not_reported')}",
                f"- Evidencia que lo sostiene: {row.get('supporting_evidence', 'not_reported')}",
                f"- Evidencia que falta: {row.get('missing_evidence', 'not_reported')}",
                f"- Fuentes usadas: {row.get('sources_used', 'not_reported')}",
                f"- Confianza: {row.get('confidence_level', 'not_reported')}",
                "",
            ]
        )
    return "\n".join(lines)


def explain_prioritization(row: pd.Series) -> str:
    role = str(row.get("therapeutic_role", "not_reported"))
    priority = _score(row.get("therapeutic_priority_score"))
    drivers = _clean(row.get("top_positive_drivers", "not_reported"))
    if role == "low_priority_candidate":
        return f"El nodo quedo con prioridad baja en las reglas actuales (score {priority}); revisar riesgos, acceso y evidencia faltante."
    return f"El nodo combina senales compatibles con `{role}` (score {priority}); principales aportes internos: {drivers}."


def explain_supporting_evidence(row: pd.Series) -> str:
    parts = []
    for label, column in [
        ("esencialidad", "essentiality_evidence_state"),
        ("virulencia", "virulence_evidence_state"),
        ("homologia humana", "homology_evidence_state"),
        ("localizacion", "localization_evidence_state"),
    ]:
        value = _clean(row.get(column, "not_reported"))
        parts.append(f"{label}={value}")
    literature = _clean(row.get("phase3_evidence_confidence_label", row.get("confidence_evidence_tier", "not_reported")))
    return "; ".join(parts + [f"confianza_evidencia={literature}"])


def explain_missing_evidence(row: pd.Series) -> str:
    missing = _clean(row.get("phase3_evidence_gap_summary", row.get("missing_evidence_flags", "not_reported")))
    therapeutic_missing = _clean(row.get("therapeutic_context_missingness", "not_reported"))
    negative = _clean(row.get("phase3_negative_evidence_summary", "none"))
    if missing in {"none", "not_reported"} and therapeutic_missing in {"none", "not_reported"}:
        return f"Sin faltantes dominantes reportados; evidencia negativa real: {negative}."
    return f"Faltantes: {missing}; contexto terapeutico incompleto: {therapeutic_missing}; evidencia negativa real: {negative}."


def explain_sources_used(row: pd.Series) -> str:
    source_summary = _clean(row.get("optional_data_source_summary", "none"))
    source_class = _clean(row.get("confidence_source_class", "unknown"))
    realism = _clean(row.get("data_realism_flag", "unknown"))
    warning = " Los datos demo/proxy/cache no equivalen a evidencia externa real." if any(
        token in f"{source_summary} {source_class} {realism}".lower()
        for token in ["demo", "proxy", "controlled", "cache"]
    ) else ""
    return f"clase={source_class}; realismo={realism}; resumen={source_summary}.{warning}"


def explain_confidence(row: pd.Series) -> str:
    confidence = _score(row.get("evidence_confidence_score"))
    coverage = _score(row.get("evidence_coverage_score"))
    ceiling = _score(row.get("confidence_ceiling", row.get("optional_data_quality_score", 0.0)))
    source_class = _clean(row.get("confidence_source_class", "unknown"))
    return f"confianza={confidence}; cobertura={coverage}; techo={ceiling}; fuente_dominante={source_class}"


def _score(value: object) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "not_reported"


def _clean(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return "not_reported"
    return text
