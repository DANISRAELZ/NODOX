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
                "score_confidence_interpretation": explain_score_confidence_interpretation(row),
                "conservative_interpretation": explain_conservative_interpretation(row),
                "final_interpretation_matrix": explain_final_interpretation_matrix(row),
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
                f"- Lectura prioridad/confianza: {row.get('score_confidence_interpretation', 'not_reported')}",
                f"- Lectura conservadora: {row.get('conservative_interpretation', 'not_reported')}",
                f"- Matriz final de interpretacion: {row.get('final_interpretation_matrix', 'not_reported')}",
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
        "trazable segun su alcance; user_curated/externa_trazable pueden sostener evidencia trazable si estan "
        "documentadas; controlled_reference es referencia controlada, no evidencia de usuario; cache conserva "
        "reproducibilidad; proxy/demo/controlado solo orientan; missing/insufficient indican ausencia o "
        "insuficiencia, no evidencia negativa ni bajo riesgo."
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


def explain_score_confidence_interpretation(row: pd.Series) -> str:
    priority_value = _numeric(row.get("therapeutic_priority_score"))
    confidence_value = _numeric(row.get("evidence_confidence_score"))
    priority = _score(row.get("therapeutic_priority_score"))
    confidence = _score(row.get("evidence_confidence_score"))
    provenance = _clean(
        row.get(
            "provenance_status",
            row.get("confidence_source_class", row.get("evidence_source_type", "not_reported")),
        )
    )
    base = (
        "`therapeutic_priority_score` y `evidence_confidence_score` son dimensiones distintas: "
        "prioridad terapeutica dentro del modelo y soporte trazable de evidencia. "
        "Un score terapeutico alto no equivale automaticamente a confianza alta; "
        "confianza alta no equivale automaticamente a prioridad terapeutica alta. "
    )
    provenance_note = (
        f"Procedencia={provenance}; las capas user_curated deben interpretarse segun su procedencia; "
        "demo/proxy/cache no deben presentarse como evidencia real equivalente y controlled_reference "
        "es referencia controlada, no evidencia de usuario. "
    )
    non_clinical = (
        "Nodos Funcionales es una plataforma multiorganismo de priorizacion terapeutica, "
        "no una herramienta clinica ni predictor definitivo; los candidatos priorizados requieren "
        "validacion experimental."
    )
    if confidence_value is None:
        return (
            f"{base}Prioridad={priority}; confianza=not_evaluated. La ausencia de "
            "`evidence_confidence_score` no debe interpretarse como confianza alta ni baja; "
            "evidencia insuficiente no equivale a bajo riesgo. "
            f"{provenance_note}{non_clinical}"
        )
    if priority_value is None:
        return (
            f"{base}Prioridad=not_evaluated; confianza={confidence}. No hay prioridad terapeutica "
            "interpretable en esta ruta; no convertir evidencia disponible en recomendacion terapeutica. "
            f"{provenance_note}{non_clinical}"
        )

    high_priority = priority_value >= 0.65
    high_confidence = confidence_value >= 0.65
    if high_priority and high_confidence:
        reading = (
            "Prioridad alta/confianza alta: candidato priorizado con respaldo relativamente fuerte, "
            "pero sigue siendo hipotesis computacional y requiere validacion experimental. "
        )
    elif high_priority and not high_confidence:
        reading = (
            "Prioridad alta/confianza baja: hipotesis potencialmente interesante pero fragil por "
            "evidencia limitada; no debe presentarse como candidato confirmado. "
        )
    elif not high_priority and high_confidence:
        reading = (
            "Prioridad baja/confianza alta: hay evidencia relativamente trazable, pero no respalda "
            "automaticamente una prioridad terapeutica alta bajo las reglas actuales. "
        )
    else:
        reading = (
            "Prioridad baja/confianza baja: prioridad e informacion insuficientes; no debe "
            "sobreinterpretarse ni usarse como evidencia negativa. "
        )
    return f"{base}Prioridad={priority}; confianza={confidence}. {reading}{provenance_note}{non_clinical}"


def explain_conservative_interpretation(row: pd.Series) -> str:
    priority = _numeric(row.get("therapeutic_priority_score"))
    confidence = _numeric(row.get("evidence_confidence_score"))
    escape_risk = _numeric(row.get("evolutionary_escape_risk_score", row.get("evolutionary_escape_risk")))
    evolutionary_constraint = _numeric(row.get("evolutionary_constraint_score", row.get("evolutionary_constraint")))
    mutation_tolerance = _numeric(row.get("mutation_tolerance_score", row.get("mutation_tolerance")))
    pathway_redundancy = _first_present(
        row,
        [
            "pathway_redundancy",
            "pathway_redundancy_score",
            "functional_redundancy_escape_score",
            "redundancy_penalty",
            "pathway_redundancy_evidence",
        ],
    )
    paralog_count = _numeric(row.get("paralog_count"))
    status = _clean(row.get("evolutionary_escape_risk_status", "not_reported")).lower()
    provenance_text = " ".join(
        _clean(row.get(column, "not_reported")).lower()
        for column in [
            "provenance_status",
            "confidence_source_class",
            "optional_data_source_summary",
            "evidence_source",
            "evidence_source_type",
            "evidence_kind",
            "retrieval_mode",
            "cache_status",
            "data_realism_flag",
        ]
    )

    cautions: list[str] = []
    if confidence is None:
        cautions.append("evidence_confidence_score no evaluado")
    elif confidence < 0.50:
        cautions.append("evidence_confidence_score bajo")
    if priority is not None and priority >= 0.65 and (confidence is None or confidence < 0.50):
        cautions.append("score alto con confianza baja o no evaluada")
    if any(token in provenance_text for token in ["demo", "proxy", "cache"]):
        cautions.append("procedencia demo/proxy/cache limitada")
    if "controlled_reference" in provenance_text or "controlled" in provenance_text:
        cautions.append("controlled_reference es referencia controlada, no evidencia de usuario")
    if "user_curated" in provenance_text and not any(token in provenance_text for token in ["provenance", "reference", "reviewed", "trace", "trazable"]):
        cautions.append("user_curated requiere procedencia trazable")
    if escape_risk is None:
        cautions.append("evolutionary_escape_risk no evaluado")
    elif escape_risk >= 0.65:
        cautions.append("evolutionary_escape_risk alto")
    if status in {"not_reported", "missing", "insufficient", "insufficient_evidence", "unknown", "not_assessed"}:
        cautions.append("riesgo evolutivo ausente, insuficiente o incierto")
    if evolutionary_constraint is None:
        cautions.append("evolutionary_constraint no evaluado")
    elif evolutionary_constraint < 0.35:
        cautions.append("evolutionary_constraint bajo")
    if mutation_tolerance is None:
        cautions.append("mutation_tolerance incierta")
    elif mutation_tolerance >= 0.65:
        cautions.append("mutation_tolerance alta")
    if _is_high_or_present(pathway_redundancy):
        cautions.append("pathway_redundancy alta")
    if paralog_count is not None and paralog_count >= 2:
        cautions.append("paralog_count alto")
    for label, column in [
        ("mobile_context", "mobile_context"),
        ("hgt_context", "hgt_context"),
        ("recombination_context", "recombination_context"),
        ("resistance_association", "resistance_association"),
    ]:
        if _is_present_or_uncertain(row.get(column)):
            cautions.append(f"{label} presente o incierto")
    if _clean(row.get("evolutionary_escape_risk_missing_variables", "not_reported")) != "not_reported":
        cautions.append("evidencia evolutiva insuficiente")

    unique_cautions = list(dict.fromkeys(cautions))
    caution_text = "; ".join(unique_cautions) if unique_cautions else "sin factores de cautela dominantes reportados"
    action = (
        "recomienda validacion experimental y revision experta antes de elevar conclusiones"
        if unique_cautions
        else "mantiene lectura prudente y requiere validacion experimental para cualquier aplicacion"
    )
    return (
        "Modo conservador interpretativo: no modifica therapeutic_priority_score, evidence_confidence_score, "
        "pesos ni ranking; no reordena candidatos. Factores de cautela detectados: "
        f"{caution_text}. Ausencia o insuficiencia de evidencia no equivale a bajo riesgo; riesgo evolutivo "
        "incierto no equivale a bajo riesgo evolutivo. Demo/proxy/cache no son evidencia real equivalente; "
        "controlled_reference no es evidencia de usuario; user_curated debe leerse segun procedencia trazable. "
        "La subcapa evolutiva modula la interpretacion, pero no sustituye funcionalidad, selectividad, "
        f"accesibilidad, evidencia, confianza ni validacion experimental. Plataforma multiorganismo; {action}."
    )


def explain_final_interpretation_matrix(row: pd.Series) -> str:
    priority = _numeric(row.get("therapeutic_priority_score"))
    confidence = _numeric(row.get("evidence_confidence_score"))
    escape_risk = _numeric(row.get("evolutionary_escape_risk_score", row.get("evolutionary_escape_risk")))
    status = _clean(row.get("evolutionary_escape_risk_status", "not_reported")).lower()
    provenance_text = _provenance_text(row)

    high_priority = priority is not None and priority >= 0.65
    low_or_missing_priority = priority is None or priority < 0.65
    high_confidence = confidence is not None and confidence >= 0.65
    low_or_missing_confidence = confidence is None or confidence < 0.50
    traceable_provenance = _has_traceable_provenance(provenance_text)
    provenance_limited = _has_limited_provenance(provenance_text)
    user_curated_untraced = "user_curated" in provenance_text and not traceable_provenance
    evolutionary_caution = _has_evolutionary_caution(row, escape_risk, status)

    secondary: list[str] = []
    if evolutionary_caution:
        secondary.append("evolutionary_caution")
    if provenance_limited:
        secondary.append("provenance_limited_interpretation")
    if user_curated_untraced:
        secondary.append("user_curated_requires_traceability")
    if confidence is None:
        secondary.append("confidence_not_evaluated")

    if high_priority and high_confidence and traceable_provenance and not evolutionary_caution and not provenance_limited:
        category = "strong_candidate_for_experimental_validation"
        interpretation = (
            "candidato fuerte para validacion experimental por prioridad alta, confianza alta, "
            "procedencia trazable y riesgo evolutivo bajo o evaluado sin senales criticas"
        )
    elif high_priority and (low_or_missing_confidence or provenance_limited or user_curated_untraced):
        category = "prioritized_hypothesis_limited_evidence"
        interpretation = "hipotesis priorizada, pero evidencia fragil o procedencia limitada; no es candidato confirmado"
    elif low_or_missing_priority and high_confidence:
        category = "evidence_supported_but_low_priority"
        interpretation = "evidencia relativamente trazable, pero baja prioridad terapeutica bajo el modelo actual"
    elif low_or_missing_priority and low_or_missing_confidence:
        category = "insufficient_information"
        interpretation = "informacion insuficiente; no sobreinterpretar y no tratar como bajo riesgo"
    else:
        category = "prioritized_hypothesis_limited_evidence" if high_priority else "insufficient_information"
        interpretation = "lectura mixta que requiere revisar evidencia, procedencia y cautelas conservadoras"

    secondary_text = ", ".join(dict.fromkeys(secondary)) if secondary else "none"
    priority_text = _score(row.get("therapeutic_priority_score"))
    confidence_text = _score(row.get("evidence_confidence_score"))
    risk_text = _score(row.get("evolutionary_escape_risk_score", row.get("evolutionary_escape_risk")))
    conservative = explain_conservative_interpretation(row)
    return (
        f"final_interpretation_category={category}; secondary_notes={secondary_text}; "
        f"priority={priority_text}; confidence={confidence_text}; evolutionary_escape_risk={risk_text}; "
        f"provenance_category={_summarize_provenance_category(provenance_text)}. "
        f"Interpretacion: {interpretation}. `therapeutic_priority_score`, `evidence_confidence_score`, "
        "procedencia y riesgo evolutivo son dimensiones separadas; score alto no equivale a confianza alta "
        "y confianza alta no equivale a prioridad terapeutica alta. Matriz final interpretativa: no modifica "
        "scores, pesos ni ranking, y no reordena candidatos. No es herramienta clinica ni predictor definitivo; "
        "cualquier candidato requiere validacion experimental. Evidencia insuficiente no equivale a bajo riesgo; "
        "riesgo evolutivo incierto no equivale a bajo riesgo evolutivo. user_curated requiere trazabilidad; "
        "demo/proxy/cache no equivalen a evidencia real; controlled_reference no es evidencia de usuario. "
        f"Plataforma multiorganismo. Lectura conservadora integrada: {conservative}"
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
    uncertain = (
        " Riesgo evolutivo incierto: ausencia o insuficiencia de evidencia evolutiva no equivale "
        "a bajo riesgo ni a bajo escape evolutivo; la subcapa evolutiva modula la interpretacion, "
        "pero no sustituye funcionalidad, selectividad, accesibilidad, confianza, evidencia ni "
        "validacion experimental."
        if risk == "not_reported" or status in {"not_reported", "missing", "insufficient", "unknown", "not_assessed"}
        else ""
    )
    return f"escape={risk}; robustez={robustness}; restriccion={constraint}; estado={status}; interpretacion={interpretation}.{uncertain}"


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


def _numeric(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _first_present(row: pd.Series, columns: list[str]) -> object:
    for column in columns:
        value = row.get(column)
        if _clean(value) != "not_reported":
            return value
    return None


def _is_high_or_present(value: object) -> bool:
    numeric = _numeric(value)
    if numeric is not None:
        return numeric >= 0.65
    text = _clean(value).lower()
    return any(token in text for token in ["high", "alta", "present", "presente", "yes", "true", "1"])


def _is_present_or_uncertain(value: object) -> bool:
    numeric = _numeric(value)
    if numeric is not None:
        return numeric > 0
    text = _clean(value).lower()
    return any(
        token in text
        for token in ["present", "presente", "positive", "positivo", "yes", "true", "uncertain", "incierto", "unknown"]
    )


def _provenance_text(row: pd.Series) -> str:
    return " ".join(
        _clean(row.get(column, "not_reported")).lower()
        for column in [
            "provenance_status",
            "confidence_source_class",
            "optional_data_source_summary",
            "evidence_source",
            "evidence_source_type",
            "evidence_kind",
            "retrieval_mode",
            "cache_status",
            "data_realism_flag",
            "source_name",
            "source_type",
        ]
    )


def _has_limited_provenance(provenance_text: str) -> bool:
    normalized = (
        provenance_text.replace("not_cached", "")
        .replace("not cached", "")
        .replace("cache=not_primary", "")
        .replace("cache not primary", "")
    )
    return any(token in normalized for token in ["demo", "proxy", "cache", "controlled_reference", "controlled"])


def _has_traceable_provenance(provenance_text: str) -> bool:
    return any(
        token in provenance_text
        for token in ["provenance", "reference", "reviewed", "trace", "trazable", "external_real", "literature_curated"]
    )


def _has_evolutionary_caution(row: pd.Series, escape_risk: float | None, status: str) -> bool:
    if escape_risk is None or escape_risk >= 0.65:
        return True
    if status in {"not_reported", "missing", "insufficient", "insufficient_evidence", "unknown", "not_assessed"}:
        return True
    for column in ["mobile_context", "hgt_context", "recombination_context", "resistance_association"]:
        if _is_present_or_uncertain(row.get(column)):
            return True
    return False


def _summarize_provenance_category(provenance_text: str) -> str:
    if "user_curated" in provenance_text:
        return "user_curated"
    if "controlled_reference" in provenance_text or "controlled" in provenance_text:
        return "controlled_reference"
    if "demo" in provenance_text:
        return "demo"
    if "proxy" in provenance_text:
        return "proxy"
    if "cache" in provenance_text:
        return "cache"
    if "external" in provenance_text:
        return "external_or_online"
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
