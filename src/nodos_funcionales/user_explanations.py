from __future__ import annotations

import pandas as pd


THEORY_V3_NOT_ASSESSED_NOTE = (
    "La capa theory-first/v3 existe, pero en esta corrida no hubo evidencia suficiente para evaluarla. "
    "Esto no indica error del sistema, no equivale a evidencia negativa, no valida experimentalmente el candidato "
    "y tampoco lo descarta biologicamente. La teoria guia la priorizacion, pero sus salidas siguen siendo "
    "hipotesis computacionales hasta validacion externa."
)

_UNASSESSED_VALUES = {"", "nan", "none", "not_reported", "not_assessed", "unknown"}


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
                "functional_node_types": row.get("functional_node_types", "not_reported"),
                "therapeutic_priority_components": explain_therapeutic_priority_components(row),
                "why_prioritized": explain_prioritization(row),
                "supporting_evidence": explain_supporting_evidence(row),
                "missing_evidence": explain_missing_evidence(row),
                "sources_used": explain_sources_used(row),
                "confidence_level": explain_confidence(row),
                "theory_context": explain_theory_context(row),
                "provenance_context": explain_provenance_context(row),
                "evolutionary_risk": explain_evolutionary_risk(row),
                "theory_v3_assessment_note": explain_theory_v3_assessment_note(row),
                "interpretation_warning": explain_interpretation_warning(row),
            }
        )
    return pd.DataFrame(rows)


def build_simple_candidate_explanations_markdown(explanations: pd.DataFrame) -> str:
    lines = [
        "# Explicacion Simple de Candidatos",
        "",
        "Este reporte usa lenguaje no tecnico. Resume por que el pipeline priorizo cada nodo, que evidencia existe y que falta. Nodos Funcionales es una plataforma de priorizacion terapeutica basada en evidencia, no un predictor clinico definitivo.",
        "",
        "`therapeutic_priority_score` ordena hipotesis dentro del modelo y `evidence_confidence_score` describe el soporte disponible para interpretarlas. Un score alto no equivale a confianza alta.",
        "",
        "Advertencia: un score alto no equivale a validacion experimental ni validacion clinica, no implica que exista un farmaco disponible y no constituye recomendacion terapeutica. No sustituye evaluacion medica, microbiologica ni farmacologica. La ausencia de evidencia no equivale a evidencia negativa; bajo riesgo evolutivo no significa ausencia de resistencia.",
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
                f"- Tipo(s) de nodo funcional: `{row.get('functional_node_types', 'not_reported')}`",
                f"- Componentes de prioridad terapeutica: {row.get('therapeutic_priority_components', 'not_reported')}",
                f"- Por que fue priorizado: {row.get('why_prioritized', 'not_reported')}",
                f"- Evidencia que lo sostiene: {row.get('supporting_evidence', 'not_reported')}",
                f"- Evidencia que falta: {row.get('missing_evidence', 'not_reported')}",
                f"- Fuentes usadas: {row.get('sources_used', 'not_reported')}",
                f"- Confianza: {row.get('confidence_level', 'not_reported')}",
                f"- Contexto teorico: {row.get('theory_context', 'not_reported')}",
                f"- Procedencia resumida: {row.get('provenance_context', 'not_reported')}",
                f"- Riesgo evolutivo: {row.get('evolutionary_risk', 'not_reported')}",
                *(
                    [f"- Nota theory-first/v3: {row.get('theory_v3_assessment_note')}"]
                    if _clean(row.get("theory_v3_assessment_note", "not_reported")) != "not_reported"
                    else []
                ),
                f"- Limite de interpretacion: {row.get('interpretation_warning', 'not_reported')}",
                "",
            ]
        )
    return "\n".join(lines)


def explain_prioritization(row: pd.Series) -> str:
    role = str(row.get("therapeutic_role", "not_reported"))
    priority = _score(row.get("therapeutic_priority_score"))
    drivers = _clean(row.get("top_positive_drivers", "not_reported"))
    node_types = _clean(row.get("functional_node_types", "not_reported"))
    if role == "low_priority_candidate":
        return f"El nodo quedo con prioridad baja en las reglas actuales (score {priority}); tipos={node_types}; revisar riesgos, acceso y evidencia faltante."
    return f"El nodo combina senales compatibles con `{role}` (score {priority}); tipos={node_types}; principales aportes internos: {drivers}."


def explain_therapeutic_priority_components(row: pd.Series) -> str:
    summary = _clean(row.get("therapeutic_priority_contribution_summary", "not_reported"))
    if summary != "not_reported":
        return summary
    parts = []
    for label, column in [
        ("meta_priority_score", "therapeutic_priority_meta_priority_score_contribution"),
        ("host_safety_score", "therapeutic_priority_host_safety_score_contribution"),
        ("host_damage_score", "therapeutic_priority_host_damage_score_contribution"),
        ("infection_site_access_score", "therapeutic_priority_infection_site_access_score_contribution"),
        ("infection_context_score", "therapeutic_priority_infection_context_score_contribution"),
    ]:
        value = _score(row.get(column))
        if value != "not_reported":
            parts.append(f"{label}={value}")
    return "; ".join(parts) if parts else "not_reported"


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
    limitation = "Ausencia o insuficiencia no equivale a evidencia negativa ni a bajo riesgo."
    if missing in {"none", "not_reported"} and therapeutic_missing in {"none", "not_reported"}:
        return f"Sin faltantes dominantes reportados; evidencia negativa real: {negative}. {limitation}"
    return f"Faltantes: {missing}; contexto terapeutico incompleto: {therapeutic_missing}; evidencia negativa real: {negative}. {limitation}"


def explain_sources_used(row: pd.Series) -> str:
    source_summary = _clean(row.get("optional_data_source_summary", "none"))
    source_class = _clean(row.get("confidence_source_class", "unknown"))
    realism = _clean(row.get("data_realism_flag", "unknown"))
    provenance = _clean(row.get("provenance_status", "not_reported"))
    retrieval = _clean(row.get("retrieval_mode", "not_reported"))
    cache = _clean(row.get("cache_status", "not_reported"))
    warning = " Los datos demo/proxy/cache no equivalen a evidencia externa real." if any(
        token in f"{source_summary} {source_class} {realism} {provenance}".lower()
        for token in ["demo", "proxy", "controlled", "cache"]
    ) else ""
    provenance_note = (
        " Interpretacion de procedencia: usuario/externa_trazable/snapshot_controlado pueden sostener evidencia "
        "trazable; cache conserva reproducibilidad; proxy/demo/controlado solo orientan; missing/insufficient "
        "indican ausencia o insuficiencia, no evidencia negativa ni bajo riesgo."
    )
    return f"clase={source_class}; procedencia={provenance}; retrieval={retrieval}; cache={cache}; realismo={realism}; resumen={source_summary}.{warning}{provenance_note}"


def explain_confidence(row: pd.Series) -> str:
    confidence = _score(row.get("evidence_confidence_score"))
    coverage = _score(row.get("evidence_coverage_score"))
    ceiling = _score(row.get("confidence_ceiling", row.get("optional_data_quality_score", 0.0)))
    modifier = _score(row.get("confidence_modifier"))
    source_class = _clean(row.get("confidence_source_class", "unknown"))
    return (
        f"confianza={confidence}; cobertura={coverage}; modificador={modifier}; techo={ceiling}; "
        f"fuente_dominante={source_class}; independiente_de_prioridad=si"
    )


def explain_theory_context(row: pd.Series) -> str:
    return (
        f"functional_node_score={_score(row.get('functional_node_score'))}; "
        f"selectividad={_score(row.get('selectivity_score'))}; "
        f"contexto_clinico={_score(row.get('clinical_context_score'))}; "
        f"robustez_evolutiva={_score(row.get('evolutionary_robustness_score'))}; "
        f"confidence_modifier={_score(row.get('confidence_modifier'))}"
    )


def explain_provenance_context(row: pd.Series) -> str:
    return (
        f"evidence_level={_clean(row.get('evidence_level', 'not_reported'))}; "
        f"provenance_status={_clean(row.get('provenance_status', 'not_reported'))}; "
        f"retrieval_mode={_clean(row.get('retrieval_mode', 'not_reported'))}; "
        f"cache_status={_clean(row.get('cache_status', 'not_reported'))}; "
        f"source_version={_clean(row.get('source_version', 'not_reported'))}; "
        f"updated_at={_clean(row.get('updated_at', 'not_reported'))}"
    )


def explain_evolutionary_risk(row: pd.Series) -> str:
    risk = _score(row.get("evolutionary_escape_risk_score", row.get("evolutionary_escape_risk")))
    robustness = _score(row.get("evolutionary_robustness_score"))
    constraint = _score(row.get("evolutionary_constraint_score", row.get("evolutionary_constraint")))
    status = _clean(row.get("evolutionary_escape_risk_status", "not_reported"))
    interpretation = _clean(row.get("evolutionary_escape_risk_interpretation", "not_reported"))
    return f"escape={risk}; robustez={robustness}; restriccion={constraint}; estado={status}; interpretacion={interpretation}"


def explain_theory_v3_assessment_note(row: pd.Series) -> str:
    if _is_unassessed(row.get("functional_node_theory_score")) or _is_unassessed(row.get("therapeutic_role_v3")):
        return THEORY_V3_NOT_ASSESSED_NOTE
    return "not_reported"


def explain_interpretation_warning(row: pd.Series) -> str:
    warning = _clean(row.get("interpretation_warning", "not_reported"))
    if warning != "not_reported":
        return warning
    return (
        "Ranking = hipotesis terapeutica priorizada, no validacion experimental ni validacion clinica y no recomendacion terapeutica; "
        "requiere validacion experimental y clinica antes de cualquier aplicacion; score alto no equivale a confianza alta; "
        "ausencia, proxy o evidencia incompleta no equivalen a evidencia negativa ni a bajo riesgo."
    )


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


def _is_unassessed(value: object) -> bool:
    if value is None:
        return True
    try:
        if bool(pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in _UNASSESSED_VALUES
