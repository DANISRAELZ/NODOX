from __future__ import annotations

from pathlib import Path

import pandas as pd


SOURCE_EXPLANATIONS = {
    "user_curated": "Datos curados por el usuario. Su contribucion es mas confiable si la curacion esta documentada.",
    "external_real": "Datos de una base externa real. Deben revisarse version, proveedor y fecha.",
    "literature_curated": "Literatura curada con referencia verificable. Puede aumentar confianza.",
    "computed_from_real_data": "Calculo interno derivado de datos reales. Aporta soporte trazable, pero depende del metodo.",
    "controlled_provider": "Proveedor controlado o stub reproducible. Util para exploracion, no como validacion final.",
    "proxy_inference": "Inferencia proxy. Puede orientar pruebas, pero no debe elevar confianza cientifica.",
    "default_value": "Valor por defecto. Mantiene el pipeline ejecutable, pero no es evidencia biologica.",
    "demo_data": "Dato demo o plantilla. Sirve para probar el pipeline; no valida el ranking.",
    "missing": "Dato ausente. Reduce confianza, pero no significa que el candidato sea malo.",
}


def build_provenance_user_summary(features: pd.DataFrame, layer_resolution_summary: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    if layer_resolution_summary.empty:
        layer_resolution_summary = _fallback_layer_summary(features)
    for _, row in layer_resolution_summary.iterrows():
        layer = str(row.get("layer", row.get("dataset", "unknown")))
        source_type = _main_source_type(row)
        group = _source_group(source_type)
        feature_group = _feature_source_group(features, layer)
        if group == "missing" and feature_group != "missing":
            group = feature_group
        missing = _missing_text(row, group)
        demo_proxy = "si" if group in {"demo_data", "default_value", "proxy_inference", "controlled_provider"} else "no"
        rows.append(
            {
                "Capa": layer,
                "Tipo principal de evidencia": group,
                "Calidad de evidencia": _quality_text(group),
                "Datos faltantes": missing,
                "Uso de demo/default/proxy": demo_proxy,
                "Impacto sobre el ranking": _impact_text(group),
                "Recomendacion para mejorar": _recommendation(layer, group),
            }
        )
    table = pd.DataFrame(rows)
    markdown = _build_markdown(table)
    return table, markdown


def write_provenance_user_summary(base_dir: Path, features: pd.DataFrame, layer_resolution_summary: pd.DataFrame) -> tuple[Path, pd.DataFrame]:
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    table, markdown = build_provenance_user_summary(features, layer_resolution_summary)
    path = results_dir / "provenance_user_summary.md"
    path.write_text(markdown, encoding="utf-8")
    return path, table


def _build_markdown(table: pd.DataFrame) -> str:
    return "\n".join(
        [
            "# Resumen de Procedencia para Usuarios",
            "",
            "Este reporte explica de donde vienen los datos y como afectan la confianza del ranking. "
            "La falta de datos reduce confianza, pero no es evidencia negativa. La evidencia negativa solo cuenta cuando proviene de una fuente real, curada o externa.",
            "",
            "## Como leerlo",
            "",
            "- `demo_data`, `default_value` y `proxy_inference` permiten ejecutar el pipeline, pero no validan biologicamente un candidato.",
            "- `missing` significa ausencia de evidencia; no significa que el blanco sea malo.",
            "- `literature_curated`, `user_curated` y `external_real` son las fuentes mas utiles para aumentar confianza.",
            "",
            "## Tabla por capa",
            "",
            _markdown_table(table),
        ]
    )


def _main_source_type(row: pd.Series) -> str:
    for column in ["source_type", "evidence_source_type", "status", "retrieval_status"]:
        if column in row.index and str(row.get(column, "")).strip():
            return str(row.get(column))
    return "missing"


def _source_group(source_type: str) -> str:
    text = str(source_type).lower()
    if "demo" in text or "example" in text:
        return "demo_data"
    if "default" in text:
        return "default_value"
    if "proxy" in text:
        return "proxy_inference"
    if "controlled" in text or "stub" in text:
        return "controlled_provider"
    if "user" in text or "raw" in text:
        return "user_curated"
    if "literature" in text or "pubmed" in text or "doi" in text:
        return "literature_curated"
    if any(token in text for token in ["external", "uniprot", "string", "vfdb", "deg", "bvbrc", "interpro"]):
        return "external_real"
    if "cache" in text or "computed" in text:
        return "computed_from_real_data"
    return "missing"


def _fallback_layer_summary(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in [col for col in features.columns if col.endswith("_source_type")]:
        rows.append({"layer": column.removesuffix("_source_type"), "source_type": features[column].dropna().astype(str).iloc[0] if features[column].notna().any() else "missing"})
    return pd.DataFrame(rows)


def _feature_source_group(features: pd.DataFrame, layer: str) -> str:
    if features.empty:
        return "missing"
    candidate_columns = [
        f"{layer}_source_type",
        f"{layer}_evidence_source_type",
    ]
    if layer == "functional_network":
        candidate_columns.append("network_source_type")
    if layer == "curated_disease_context":
        candidate_columns.append("disease_context_source_type")
    groups = []
    for column in candidate_columns:
        if column not in features.columns:
            continue
        values = features[column].dropna().astype(str).str.strip()
        for value in values[values != ""]:
            groups.append(_source_group(value))
    informative = [group for group in groups if group != "missing"]
    if not informative:
        return "missing"
    return pd.Series(informative).value_counts().idxmax()


def _missing_text(row: pd.Series, group: str) -> str:
    if group == "missing":
        return "si; la capa no aporta evidencia directa"
    retrieval = str(row.get("retrieval_status", "")).lower()
    return "posible" if "missing" in retrieval or "failed" in retrieval else "no dominante"


def _quality_text(group: str) -> str:
    return {
        "user_curated": "alta si esta documentada",
        "external_real": "moderada/alta",
        "literature_curated": "alta si la referencia es verificable",
        "computed_from_real_data": "moderada",
        "controlled_provider": "moderada-baja",
        "proxy_inference": "baja",
        "default_value": "muy baja",
        "demo_data": "solo demostracion",
        "missing": "sin evidencia",
    }.get(group, "desconocida")


def _impact_text(group: str) -> str:
    if group == "missing":
        return "reduce confianza; no penaliza como evidencia negativa"
    if group in {"demo_data", "default_value", "proxy_inference"}:
        return "no debe elevar confianza cientifica"
    if group == "controlled_provider":
        return "puede orientar exploracion, con techo de confianza"
    return "puede aumentar confianza si converge con otras capas"


def _recommendation(layer: str, group: str) -> str:
    if group in {"missing", "demo_data", "default_value", "proxy_inference", "controlled_provider"}:
        return f"Completar o reemplazar `{_recommended_file(layer)}` con evidencia real o curada."
    return "Conservar procedencia, version y referencias para auditoria."


def _recommended_file(layer: str) -> str:
    mapping = {
        "disease_context": "data_user/curated_disease_context.csv",
        "therapy_site_context": "data_user/therapy_site_context.csv",
        "conservation": "data_user/strain_conservation.csv",
        "network": "data_user/functional_network.csv",
    }
    return mapping.get(layer, f"data_user/{layer}.csv")


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin capas para reportar._"
    headers = [str(column) for column in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("\n", " ") for column in df.columns) + " |")
    return "\n".join(lines)
