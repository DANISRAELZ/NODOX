from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROFILE_FIELDS = [
    "organism",
    "strain",
    "taxonomy_id",
    "genome_accession",
    "proteome_source",
    "annotation_source",
    "essentiality_available",
    "virulence_available",
    "conservation_available",
    "functional_network_available",
    "localization_available",
    "human_homologs_available",
    "evolutionary_escape_available",
    "literature_support_available",
    "clinical_context_available",
    "disease_context_available",
    "host_context",
    "curator",
    "date",
    "notes",
]

CORE_LAYERS = ["essentiality", "virulence", "localization", "human_homologs"]
SUPPORT_LAYERS = [
    "strain_conservation",
    "functional_network",
    "evolutionary_escape",
    "evolutionary_escape_risk",
    "literature_support",
    "clinical_impact",
    "curated_disease_context",
    "therapy_site_context",
]


def validate_organism_profile(base_dir: Path, features: pd.DataFrame | None = None) -> tuple[pd.DataFrame, str]:
    """Classify whether an organism workspace is ready for interpretation."""
    profile = _load_profile(base_dir)
    layer_rows = _layer_rows(base_dir, features)
    real_layers = [row for row in layer_rows if row["evidence_group"] in {"user_curated", "external_real", "literature_curated", "computed_from_real_data"}]
    demo_proxy_layers = [row for row in layer_rows if row["uses_demo_default_or_proxy"]]
    missing_layers = [row for row in layer_rows if row["evidence_group"] == "missing"]
    real_count = len(real_layers)
    curated_literature = any(row["layer"] == "literature_support" and row["evidence_group"] == "literature_curated" for row in layer_rows)
    host_and_escape = any(row["layer"] == "human_homologs" and row["evidence_group"] != "missing" for row in layer_rows) and any(
        row["layer"] in {"evolutionary_escape", "evolutionary_escape_risk"} and row["evidence_group"] != "missing"
        for row in layer_rows
    )
    if real_count >= 8 and curated_literature and host_and_escape and not demo_proxy_layers:
        readiness = "publication_candidate_run"
    elif real_count >= 5 and host_and_escape:
        readiness = "evidence_supported_run"
    elif real_count >= 2:
        readiness = "exploratory_run"
    else:
        readiness = "demo_run"

    rows = []
    for row in layer_rows:
        rows.append(
            {
                **row,
                "organism": profile.get("organism") or profile.get("organism_canonical_name") or "not_reported",
                "strain": profile.get("strain") or profile.get("strain_canonical") or "not_reported",
                "readiness_level": readiness,
                "recommended_file_to_fill": _recommended_file(row["layer"]),
            }
        )
    summary = pd.DataFrame(rows)
    markdown = build_organism_profile_markdown(summary, profile, readiness, missing_layers, demo_proxy_layers)
    return summary, markdown


def build_organism_profile_markdown(
    summary: pd.DataFrame,
    profile: dict[str, Any],
    readiness: str,
    missing_layers: list[dict[str, Any]],
    demo_proxy_layers: list[dict[str, Any]],
) -> str:
    lines = [
        "# Validacion del Perfil del Organismo",
        "",
        f"- Organismo: `{profile.get('organism') or profile.get('organism_canonical_name', 'not_reported')}`",
        f"- Cepa: `{profile.get('strain') or profile.get('strain_canonical', 'not_reported')}`",
        f"- Nivel actual: `{readiness}`",
        "",
        _readiness_text(readiness),
        "",
        "## Capas",
        "",
        _markdown_table(summary[["layer", "evidence_group", "quality_hint", "status", "recommended_file_to_fill"]]),
        "",
        "## Que falta",
        "",
    ]
    if missing_layers:
        lines.extend(f"- `{row['layer']}`: llenar `{_recommended_file(row['layer'])}`." for row in missing_layers)
    else:
        lines.append("- No hay capas completamente ausentes segun la procedencia disponible.")
    lines.extend(["", "## Demo, Default o Proxy", ""])
    if demo_proxy_layers:
        lines.extend(
            f"- `{row['layer']}` usa demo/default/proxy. Sirve para probar el pipeline, pero no valida biologicamente el ranking."
            for row in demo_proxy_layers
        )
    else:
        lines.append("- No se detecto uso dominante de demo/default/proxy por capa.")
    return "\n".join(lines)


def write_organism_profile_validation(base_dir: Path, features: pd.DataFrame | None = None) -> tuple[Path, Path, pd.DataFrame]:
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    summary, markdown = validate_organism_profile(base_dir, features)
    csv_path = results_dir / "organism_profile_validation.csv"
    md_path = results_dir / "organism_profile_validation.md"
    summary.to_csv(csv_path, index=False)
    md_path.write_text(markdown, encoding="utf-8")
    return csv_path, md_path, summary


def _load_profile(base_dir: Path) -> dict[str, Any]:
    path = base_dir / "results" / "organism_profile.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _layer_rows(base_dir: Path, features: pd.DataFrame | None) -> list[dict[str, Any]]:
    layer_summary_path = base_dir / "results" / "layer_evidence_summary.csv"
    rows: list[dict[str, Any]] = []
    if layer_summary_path.exists():
        layer_evidence = pd.read_csv(layer_summary_path)
    else:
        layer_evidence = pd.DataFrame()
    all_layers = list(dict.fromkeys(CORE_LAYERS + SUPPORT_LAYERS))
    for layer in all_layers:
        source_type = _feature_source_type(features, layer)
        evidence_group = _evidence_group(source_type)
        if not layer_evidence.empty and "phase3_real_evidence_layer_count" in layer_evidence.columns and evidence_group == "missing":
            evidence_group = "computed_from_real_data" if _feature_has_layer_signal(features, layer) else evidence_group
        rows.append(
            {
                "layer": layer,
                "source_type": source_type or "missing",
                "evidence_group": evidence_group,
                "quality_hint": _quality_hint(evidence_group),
                "status": _status_text(evidence_group),
                "uses_demo_default_or_proxy": evidence_group in {"demo_data", "default_value", "proxy_inference", "controlled_provider"},
            }
        )
    return rows


def _feature_source_type(features: pd.DataFrame | None, layer: str) -> str:
    if features is None or features.empty:
        return "missing"
    for column in [f"{layer}_source_type", f"{layer}_retrieval_status", f"{layer}_database"]:
        if column in features.columns:
            values = features[column].dropna().astype(str).str.lower()
            if values.empty:
                continue
            joined = " ".join(values.head(5).tolist())
            if any(token in joined for token in ["demo", "example"]):
                return "demo_data"
            if "proxy" in joined:
                return "proxy_inference"
            if "default" in joined:
                return "default_value"
            if "stub" in joined or "controlled" in joined:
                return "controlled_provider"
            if any(token in joined for token in ["raw", "user"]):
                return "user_curated"
            if any(token in joined for token in ["uniprot", "string", "vfdb", "deg", "bvbrc", "interpro", "external"]):
                return "external_real"
            if any(token in joined for token in ["literature", "pubmed", "doi", "curated"]):
                return "literature_curated"
            if "computed" in joined or "cache" in joined:
                return "computed_from_real_data"
    return "missing"


def _feature_has_layer_signal(features: pd.DataFrame | None, layer: str) -> bool:
    if features is None or features.empty:
        return False
    return any(column.startswith(layer) or column.endswith(f"{layer}_database") for column in features.columns)


def _evidence_group(source_type: str) -> str:
    text = str(source_type or "").lower()
    if any(token in text for token in ["demo", "example"]):
        return "demo_data"
    if "proxy" in text:
        return "proxy_inference"
    if "default" in text:
        return "default_value"
    if "controlled" in text or "stub" in text:
        return "controlled_provider"
    if "raw" in text or "user" in text:
        return "user_curated"
    if any(token in text for token in ["literature", "pubmed", "doi"]):
        return "literature_curated"
    if any(token in text for token in ["external", "uniprot", "string", "vfdb", "deg", "bvbrc", "interpro"]):
        return "external_real"
    if "computed" in text or "cache" in text:
        return "computed_from_real_data"
    return "missing"


def _quality_hint(group: str) -> str:
    return {
        "user_curated": "alta si la curacion es correcta",
        "external_real": "moderada/alta segun proveedor",
        "literature_curated": "alta si la referencia es verificable",
        "computed_from_real_data": "moderada",
        "controlled_provider": "moderada-baja",
        "proxy_inference": "baja",
        "default_value": "muy baja",
        "demo_data": "solo demostracion",
        "missing": "ausente",
    }.get(group, "desconocida")


def _status_text(group: str) -> str:
    if group == "missing":
        return "falta evidencia; reduce confianza pero no es evidencia negativa"
    if group in {"demo_data", "default_value", "proxy_inference"}:
        return "sirve para ejecutar el pipeline, no para validar biologia"
    if group == "controlled_provider":
        return "inferencia controlada; revisar antes de publicar"
    return "aporta evidencia trazable"


def _recommended_file(layer: str) -> str:
    return {
        "strain_conservation": "data_user/strain_conservation.csv",
        "functional_network": "data_user/functional_network.csv",
        "curated_disease_context": "data_user/curated_disease_context.csv",
        "therapy_site_context": "data_user/therapy_site_context.csv",
    }.get(layer, f"data_user/{layer}.csv")


def _readiness_text(readiness: str) -> str:
    return {
        "demo_run": "Este workspace sirve para probar el flujo, pero no debe interpretarse como ranking terapeutico real.",
        "exploratory_run": "El ranking puede usarse para exploracion inicial, con cautela por capas incompletas.",
        "evidence_supported_run": "El ranking tiene varias capas reales y puede guiar priorizacion interna.",
        "publication_candidate_run": "El perfil es suficientemente completo para una revision cientifica robusta, aun sujeta a auditoria humana.",
    }.get(readiness, "Nivel no reconocido.")


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas para reportar._"
    headers = [str(column) for column in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")).replace("\n", " ") for column in df.columns) + " |")
    return "\n".join(lines)
