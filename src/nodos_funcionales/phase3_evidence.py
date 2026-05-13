from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .layer_registry import TARGET_LAYER_KEYS


DEFAULT_EVIDENCE_WEIGHTS = {
    "user_curated": 1.00,
    "literature_curated": 0.95,
    "external_real": 0.90,
    "computed_from_real_data": 0.80,
    "controlled_provider": 0.60,
    "proxy_inference": 0.40,
    "default_value": 0.20,
    "demo_data": 0.10,
    "missing": 0.00,
}


@dataclass(frozen=True)
class LayerVariable:
    layer_name: str
    variable_name: str
    negative_high: bool = False
    negative_low: bool = False


LAYER_VARIABLES = [
    LayerVariable("essentiality", "essential"),
    LayerVariable("virulence", "virulence_score"),
    LayerVariable("human_homologs", "human_homolog", negative_high=True),
    LayerVariable("human_homologs", "host_similarity_risk", negative_high=True),
    LayerVariable("localization", "localization"),
    LayerVariable("strain_conservation", "conservation_score"),
    LayerVariable("strain_conservation", "core_genome_presence"),
    LayerVariable("strain_conservation", "strain_coverage_score"),
    LayerVariable("functional_network", "network_centrality"),
    LayerVariable("functional_network", "pathway_bottleneck_score"),
    LayerVariable("host_annotation", "domain_overlap_score", negative_high=True),
    LayerVariable("host_annotation", "host_criticality_penalty", negative_high=True),
    LayerVariable("clinical_impact", "host_damage_score"),
    LayerVariable("curated_disease_context", "infection_context_score"),
    LayerVariable("therapy_site_context", "infection_site_access_score"),
    LayerVariable("therapy_site_context", "infection_site_access"),
    LayerVariable("redundancy", "redundancy_penalty", negative_high=True),
    LayerVariable("evolutionary_escape", "evolutionary_escape_risk_score", negative_high=True),
    LayerVariable("evolutionary_escape_risk", "evolutionary_escape_risk_score", negative_high=True),
    LayerVariable("collateral_sensitivity", "collateral_sensitivity_score"),
    LayerVariable("contextual_essentiality", "contextual_essentiality_score"),
    LayerVariable("evidence_quality", "evidence_quality_score"),
    LayerVariable("literature_support", "literature_support_score"),
    LayerVariable("literature_support", "literature_negative_score", negative_high=True),
]


def evidence_weights(config: dict[str, Any] | None = None) -> dict[str, float]:
    configured = ((config or {}).get("phase3", {}).get("evidence_quality", {}).get("source_type_weights", {}))
    weights = dict(DEFAULT_EVIDENCE_WEIGHTS)
    weights.update({str(key): float(value) for key, value in configured.items()})
    return weights


def build_layer_evidence_audit(features: pd.DataFrame, config: dict[str, Any] | None = None) -> pd.DataFrame:
    weights = evidence_weights(config)
    rows: list[dict[str, Any]] = []
    for _, candidate in features.iterrows():
        protein_id = str(candidate.get("protein_id", "") or "").strip()
        gene = str(candidate.get("gene", "") or "").strip()
        for item in LAYER_VARIABLES:
            if item.variable_name not in features.columns:
                value = pd.NA
            else:
                value = candidate.get(item.variable_name)
            if item.layer_name == "literature_support" and item.variable_name == "literature_negative_score":
                literature_score = candidate.get("literature_support_score", pd.NA)
                if _is_missing_value(literature_score):
                    value = pd.NA
            source_type = classify_layer_source(candidate, item.layer_name, item.variable_name)
            quality = float(weights.get(source_type, 0.0))
            is_missing = _is_missing_value(value)
            if is_missing and source_type not in {"default_value", "proxy_inference", "demo_data"}:
                source_type = "missing"
                quality = float(weights["missing"])
            negative = _is_negative_evidence(value, item, source_type)
            rows.append(
                {
                    "protein_id": protein_id,
                    "gene": gene,
                    "layer_name": item.layer_name,
                    "variable_name": item.variable_name,
                    "value": "" if pd.isna(value) else value,
                    "evidence_source_type": source_type,
                    "evidence_quality": quality,
                    "evidence_is_missing": bool(source_type == "missing" or is_missing),
                    "evidence_is_unknown": bool(source_type == "missing" or is_missing),
                    "evidence_is_not_applicable": False,
                    "evidence_is_demo": source_type == "demo_data",
                    "evidence_is_proxy": source_type in {"proxy_inference", "controlled_provider"},
                    "evidence_is_negative": negative,
                    "negative_evidence_reason": _negative_evidence_reason(item, value, source_type, negative),
                    "missing_evidence_reason": _missing_evidence_reason(item, source_type, is_missing),
                    "source_file_or_provider": _source_file_or_provider(candidate, item.layer_name),
                    "explanation": _evidence_explanation(candidate, item.layer_name, item.variable_name, source_type, negative),
                }
            )
    return pd.DataFrame(rows)


def summarize_layer_evidence(audit: pd.DataFrame, config: dict[str, Any] | None = None) -> pd.DataFrame:
    if audit.empty:
        return pd.DataFrame()
    weights = evidence_weights(config)
    rows = []
    for protein_id, group in audit.groupby("protein_id", sort=False):
        present = group.loc[~group["evidence_is_missing"].astype(bool)].copy()
        present_mask = ~group["evidence_is_missing"].astype(bool)
        real = present_mask & group["evidence_source_type"].isin(
            ["user_curated", "literature_curated", "external_real", "computed_from_real_data"]
        )
        proxy = present_mask & group["evidence_source_type"].isin(["controlled_provider", "proxy_inference"])
        demo_or_default = present_mask & group["evidence_source_type"].isin(["demo_data", "default_value"])
        if present.empty:
            mean_present_quality = 0.0
        else:
            mean_present_quality = float(present["evidence_quality"].mean())
        coverage = float(len(present) / max(len(group), 1))
        layer_quality = mean_present_quality * (0.60 + 0.40 * coverage)
        if not bool(real.any()):
            layer_quality = min(layer_quality, max(weights["controlled_provider"] if proxy.any() else 0.0, weights["demo_data"] if demo_or_default.any() else 0.0))
        ceiling = _confidence_ceiling_from_group(group, weights)
        rows.append(
            {
                "protein_id": protein_id,
                "gene": str(group["gene"].iloc[0]),
                "phase3_layer_evidence_quality": round(max(0.0, min(layer_quality, ceiling)), 4),
                "phase3_confidence_ceiling_from_layers": round(ceiling, 4),
                "phase3_real_evidence_layer_count": int(group.loc[real, "layer_name"].nunique()),
                "phase3_literature_evidence_count": int(group["evidence_source_type"].eq("literature_curated").sum()),
                "phase3_proxy_layer_count": int(group.loc[proxy, "layer_name"].nunique()),
                "phase3_demo_default_layer_count": int(group.loc[demo_or_default, "layer_name"].nunique()),
                "phase3_missing_layer_count": int(group.loc[group["evidence_is_missing"].astype(bool), "layer_name"].nunique()),
                "phase3_negative_evidence_count": int(group["evidence_is_negative"].astype(bool).sum()),
                "phase3_evidence_category_summary": _category_summary(group),
                "phase3_evidence_gap_summary": _gap_summary(group),
                "phase3_negative_evidence_summary": _negative_summary(group),
            }
        )
    return pd.DataFrame(rows)


def apply_phase3_evidence_audit(features: pd.DataFrame, config: dict[str, Any] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit = build_layer_evidence_audit(features, config)
    summary = summarize_layer_evidence(audit, config)
    result = features.copy()
    if not summary.empty:
        result = result.merge(summary.drop(columns=["gene"], errors="ignore"), on="protein_id", how="left")
        layer_quality = pd.to_numeric(result["phase3_layer_evidence_quality"], errors="coerce").fillna(0.0)
        layer_ceiling = pd.to_numeric(result["phase3_confidence_ceiling_from_layers"], errors="coerce").fillna(0.0)
        existing_quality = _numeric_feature(result, "evidence_quality_score", 0.0)
        existing_ceiling = _numeric_feature(result, "confidence_ceiling", 0.0)
        result["evidence_quality_score"] = pd.concat([existing_quality, layer_quality], axis=1).max(axis=1).clip(0.0, 1.0)
        result["confidence_ceiling"] = pd.concat([existing_ceiling, layer_ceiling], axis=1).max(axis=1).clip(0.0, 1.0)
        result["evidence_quality_score"] = result["evidence_quality_score"].clip(upper=result["confidence_ceiling"])
        result["phase3_evidence_confidence_label"] = result.apply(assign_phase3_confidence_label, axis=1)
        result["phase3_evidence_explanation"] = result.apply(phase3_evidence_explanation, axis=1)
    return result, audit, summary


def assign_phase3_confidence_label(row: pd.Series) -> str:
    quality = float(row.get("evidence_quality_score", 0.0) or 0.0)
    real_count = int(row.get("phase3_real_evidence_layer_count", 0) or 0)
    negative_count = int(row.get("phase3_negative_evidence_count", 0) or 0)
    demo_default_count = int(row.get("phase3_demo_default_layer_count", 0) or 0)
    if negative_count and real_count:
        return "negative_evidence_present"
    if real_count >= 4 and quality >= 0.75:
        return "strong_real_convergence"
    if real_count >= 2 and quality >= 0.55:
        return "moderate_real_convergence"
    if real_count >= 1 and quality >= 0.30:
        return "partial_real_evidence"
    if demo_default_count:
        return "demo_default_limited"
    return "missing_or_uninformative"


def phase3_evidence_explanation(row: pd.Series) -> str:
    label = str(row.get("phase3_evidence_confidence_label", "missing_or_uninformative"))
    gaps = str(row.get("phase3_evidence_gap_summary", "") or "")
    negatives = str(row.get("phase3_negative_evidence_summary", "") or "")
    if label == "negative_evidence_present":
        return f"baja prioridad por evidencia biologica negativa real: {negatives}"
    if label == "strong_real_convergence":
        return "alta prioridad por evidencia real convergente en varias capas"
    if label == "moderate_real_convergence":
        return "confianza moderada por evidencia real parcial y convergente"
    if label == "partial_real_evidence":
        return "candidato exploratorio con evidencia real incompleta"
    if label == "demo_default_limited":
        return "confianza limitada porque demo/default/proxy no elevan madurez cientifica"
    return f"baja confianza por falta de datos: {gaps or 'sin capas informativas'}"


def classify_layer_source(row: pd.Series, layer_name: str, variable_name: str) -> str:
    if bool(row.get(f"{variable_name}_is_proxy", False)):
        return "proxy_inference"
    if bool(row.get(f"{layer_name}_is_user_supplied", False)):
        return "user_curated"
    source_name = _lower(row.get(f"{layer_name}_source_name", ""))
    source_type = _lower(row.get(f"{layer_name}_source_type", ""))
    retrieval = _lower(row.get(f"{layer_name}_retrieval_status", ""))
    database_text = _lower(row.get(_database_column(layer_name), ""))
    combined = " ".join([source_name, source_type, retrieval, database_text])
    explicit_source_types = {
        "user": "user_curated",
        "raw": "user_curated",
        "user_curated": "user_curated",
        "literature": "literature_curated",
        "literature_curated": "literature_curated",
        "external": "external_real",
        "external_real": "external_real",
        "cache": "computed_from_real_data",
        "computed": "computed_from_real_data",
        "computed_from_real_data": "computed_from_real_data",
        "controlled": "controlled_provider",
        "controlled_provider": "controlled_provider",
        "proxy": "proxy_inference",
        "proxy_inference": "proxy_inference",
        "default": "default_value",
        "default_value": "default_value",
        "demo": "demo_data",
        "demo_raw": "demo_data",
        "packaged_demo": "demo_data",
        "demo_data": "demo_data",
    }
    if source_type in explicit_source_types:
        return explicit_source_types[source_type]
    if any(token in database_text for token in ["curated_online_pubmed", "curated_literature", "pubmed", "doi"]):
        return "literature_curated"
    if any(token in database_text for token in ["curated_online_ncbi", "curated_online_examples"]):
        return "external_real"
    if _lower(row.get("data_realism_flag", "")) == "demo_only" and not any(
        token in combined for token in ["uniprot", "string", "vfdb", "deg", "bvbrc", "interpro", "curated", "pubmed", "ncbi", "stub", "computed", "local_reproducible"]
    ):
        return "demo_data"
    if any(token in database_text for token in ["demo", "example_"]):
        return "demo_data"
    if any(token in combined for token in ["default", "placeholder"]):
        return "default_value"
    if "proxy" in combined:
        return "proxy_inference"
    if any(token in combined for token in ["controlled", "stub"]):
        return "controlled_provider"
    if any(token in combined for token in ["literature", "doi", "pubmed", "curated_literature"]):
        return "literature_curated"
    if source_type == "raw":
        return "user_curated"
    if source_type == "cache":
        return "computed_from_real_data"
    if "local_reproducible_orthology" in combined:
        return "computed_from_real_data"
    if bool(row.get(f"{layer_name}_is_external", False)) or any(
        token in combined for token in ["uniprot", "string", "vfdb", "deg", "bvbrc", "interpro", "external", "external_real"]
    ):
        return "external_real"
    if any(token in combined for token in ["computed", "derived"]):
        return "computed_from_real_data"
    if layer_name not in TARGET_LAYER_KEYS and variable_name in row.index:
        return "computed_from_real_data"
    return "missing"


def _numeric_feature(df: pd.DataFrame, column: str, default: float) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(default).astype(float)


def _confidence_ceiling_from_group(group: pd.DataFrame, weights: dict[str, float]) -> float:
    present = group.loc[~group["evidence_is_missing"].astype(bool)]
    categories = set(present["evidence_source_type"].astype(str))
    real_count = present.loc[
        present["evidence_source_type"].isin(["user_curated", "literature_curated", "external_real", "computed_from_real_data"]),
        "layer_name",
    ].nunique()
    if real_count >= 4:
        return 1.0
    if real_count >= 2:
        return 0.85
    if "user_curated" in categories:
        return weights["user_curated"]
    if "literature_curated" in categories:
        return weights["literature_curated"]
    if "external_real" in categories:
        return weights["external_real"]
    if "computed_from_real_data" in categories:
        return weights["computed_from_real_data"]
    if "controlled_provider" in categories:
        return weights["controlled_provider"]
    if "proxy_inference" in categories:
        return weights["proxy_inference"]
    if "default_value" in categories:
        return weights["default_value"]
    if "demo_data" in categories:
        return weights["demo_data"]
    return 0.0


def _is_negative_evidence(value: object, item: LayerVariable, source_type: str) -> bool:
    if source_type in {"missing", "default_value", "demo_data", "proxy_inference"}:
        return False
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return False
    if item.negative_high and float(numeric) >= 0.70:
        return True
    if item.negative_low and float(numeric) <= 0.30:
        return True
    return False


def _is_missing_value(value: object) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip().lower()
    return text in {"", "nan", "none", "unknown", "not_reported", "not_assessed"}


def _source_file_or_provider(row: pd.Series, layer_name: str) -> str:
    return str(row.get(f"{layer_name}_source_name", "") or row.get(_database_column(layer_name), "") or "not_reported")


def _evidence_explanation(row: pd.Series, layer_name: str, variable_name: str, source_type: str, negative: bool) -> str:
    if negative:
        return f"{variable_name} aporta evidencia negativa real para {layer_name}"
    if source_type == "missing":
        return f"{variable_name} no esta disponible para {layer_name}"
    if source_type in {"demo_data", "default_value", "proxy_inference"}:
        return f"{variable_name} viene de {source_type}; limita confianza y no se interpreta como evidencia real"
    return f"{variable_name} viene de {source_type}; puede aportar confianza trazable"


def _category_summary(group: pd.DataFrame) -> str:
    counts = group.groupby("evidence_source_type")["variable_name"].count().sort_values(ascending=False)
    return "; ".join(f"{key}={int(value)}" for key, value in counts.items())


def _gap_summary(group: pd.DataFrame) -> str:
    missing = group.loc[group["evidence_is_missing"].astype(bool), ["layer_name", "variable_name"]]
    if missing.empty:
        return "none"
    return "; ".join((missing["layer_name"] + "." + missing["variable_name"]).head(8).tolist())


def _negative_summary(group: pd.DataFrame) -> str:
    negative = group.loc[group["evidence_is_negative"].astype(bool), ["layer_name", "variable_name", "value"]]
    if negative.empty:
        return "none"
    return "; ".join(
        f"{row.layer_name}.{row.variable_name}={row.value}"
        for row in negative.head(8).itertuples(index=False)
    )


def _negative_evidence_reason(item: LayerVariable, value: object, source_type: str, negative: bool) -> str:
    if not negative:
        return "none"
    return f"{item.layer_name}.{item.variable_name}={value} desde {source_type}"


def _missing_evidence_reason(item: LayerVariable, source_type: str, is_missing: bool) -> str:
    if source_type != "missing" and not is_missing:
        return "none"
    return f"{item.layer_name}.{item.variable_name} ausente; reduce confianza pero no es evidencia negativa"


def _database_column(layer_name: str) -> str:
    return {
        "human_homologs": "homology_database",
        "curated_disease_context": "disease_context_database",
        "therapy_site_context": "therapy_site_context_database",
        "strain_conservation": "conservation_database",
        "functional_network": "network_database",
    }.get(layer_name, f"{layer_name}_database")


def _lower(value: object) -> str:
    return str(value or "").strip().lower()
