from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .organism_profile import write_organism_profile_validation
from .provenance_user_summary import write_provenance_user_summary
from .ranking_snapshots import write_ranking_snapshot_outputs
from .user_explanations import (
    build_simple_candidate_explanations,
    build_simple_candidate_explanations_markdown,
    explain_theory_v3_assessment_note,
)

from .layer_registry import TARGET_LAYER_KEYS


OPTIONAL_SOURCE_COLUMNS = {
    "conservation_database": "conservation",
    "network_database": "network",
    "host_annotation_database": "host_annotation",
    "clinical_impact_database": "clinical_impact",
    "disease_context_database": "disease_context",
    "therapy_site_context_database": "therapy_site_context",
}

STRATEGY_LABELS = {
    "antibiotic_target": "antibiotic",
    "antivirulence_target": "antivirulence",
    "functional_node": "functional_node",
    "meta_priority": "hybrid",
}

HOST_RISK_REPORT_COLUMNS = [
    "host_risk_audit_summary",
    "domain_overlap_score",
    "host_criticality_penalty",
    "host_safety_score",
    "host_annotation_source_name",
    "host_annotation_retrieval_status",
    "interpro_rule",
    "interpro_missing_flags",
    "interpro_shared_entries",
    "human_essentiality_score",
    "human_essentiality_status",
    "host_annotation_rule",
    "host_annotation_missing_flags",
]

HUMAN_HOMOLOGY_REPORT_COLUMNS = [
    "human_homology_audit_summary",
    "homology_lookup_status",
    "homology_query_strategy",
    "homology_evidence_tier",
    "homology_confidence_score",
    "homology_missing_flags",
    "human_uniprot_accession",
    "human_uniprot_id",
]

THERAPY_SITE_CONTEXT_REPORT_COLUMNS = [
    "infection_site",
    "access_evidence_type",
    "access_evidence_reference",
    "access_evidence_note",
    "disease_context",
    "syndrome",
    "disease_site_context_source",
    "therapy_site_context_audit_summary",
]

THERAPEUTIC_SEPARATION_REPORT_COLUMNS = [
    "host_direct_damage_score",
    "virulence_associated_severity_score",
    "clinical_impact_catalog_source",
    "clinical_impact_evidence_type",
    "clinical_impact_evidence_reference",
    "clinical_impact_evidence_note",
]

EVOLUTIONARY_ESCAPE_RISK_REPORT_COLUMNS = [
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
    "evolutionary_escape_risk_score",
    "evolutionary_robustness_score",
    "reduced_evolutionary_space_score",
    "evolutionary_escape_penalty_applied",
    "evolutionary_adjusted_meta_priority_score",
    "evolutionary_escape_risk_confidence",
    "evolutionary_escape_risk_status",
    "evolutionary_escape_risk_source_type",
    "evolutionary_escape_risk_evidence_source",
    "evolutionary_escape_risk_missing_variables",
    "evolutionary_escape_risk_available_variables",
    "evolutionary_escape_risk_interpretation",
    "evolutionary_escape_risk_audit_summary",
]

THERAPEUTIC_PRIORITY_CONTRIBUTION_COLUMNS = [
    "therapeutic_priority_contribution_summary",
    "therapeutic_priority_components",
    "therapeutic_priority_meta_priority_score_contribution",
    "therapeutic_priority_host_safety_score_contribution",
    "therapeutic_priority_host_damage_score_contribution",
    "therapeutic_priority_infection_site_access_score_contribution",
    "therapeutic_priority_infection_context_score_contribution",
]


def _display_df(df: pd.DataFrame) -> pd.DataFrame:
    display = df.copy()
    if display.columns.duplicated().any():
        display = display.loc[:, ~display.columns.duplicated()].copy()
    float_columns = display.select_dtypes(include=["float", "float64"]).columns
    if len(float_columns):
        display[float_columns] = display[float_columns].round(4)
    return display


def _fmt_optional_score(value: object) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value or "not_reported")
    if pd.isna(numeric):
        return "not_assessed"
    return f"{numeric:.4f}"


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin datos_"
    display = _display_df(df)
    columns = [str(column) for column in display.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for _, row in display.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in display.columns) + " |")
    return "\n".join([header, separator] + rows)


def _load_workspace_metadata(base_dir: Path) -> dict:
    profile_path = base_dir / "results" / "organism_profile.json"
    manifest_path = base_dir / "results" / "acquisition_manifest.json"
    metadata = {
        "organism": "not_reported",
        "strain": "not_reported",
        "workspace": str(base_dir),
        "taxon_id": "not_reported",
        "analysis_support_level": "preliminary",
        "available_layers": [],
        "missing_layers": [],
        "user_layers": [],
        "external_layers": [],
        "demo_or_proxy_layers": [],
    }
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        metadata["organism"] = profile.get("organism_canonical_name") or profile.get("organism_input_name") or "not_reported"
        metadata["strain"] = profile.get("strain_canonical") or profile.get("strain_input") or "not_reported"
        metadata["taxon_id"] = profile.get("taxon_id") or "not_reported"
        metadata["workspace"] = profile.get("workspace") or str(base_dir)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        datasets = manifest.get("datasets", [])
        metadata["available_layers"] = [item["table_key"] for item in datasets if item.get("usable")]
        metadata["missing_layers"] = [item["table_key"] for item in datasets if item.get("required") and not item.get("usable")]
        metadata["user_layers"] = [
            item["table_key"]
            for item in datasets
            if item.get("generated_by") == "user_provided"
            and item.get("usable")
            and item.get("source_type") not in {"demo", "proxy", "controlled", "missing"}
        ]
        metadata["external_layers"] = [
            item["table_key"]
            for item in datasets
            if item.get("source_type") in {"external", "computed", "curated", "experimental"} and item.get("usable")
        ]
        metadata["demo_or_proxy_layers"] = [
            item["table_key"]
            for item in datasets
            if item.get("source_type") in {"demo", "proxy", "controlled"} or item.get("generated_by") == "packaged_demo"
        ]
        if metadata["missing_layers"]:
            metadata["analysis_support_level"] = "preliminary_incomplete"
        elif metadata["demo_or_proxy_layers"] and not metadata["user_layers"]:
            metadata["analysis_support_level"] = "exploratory_demo_or_proxy_supported"
        elif metadata["user_layers"] or metadata["external_layers"]:
            metadata["analysis_support_level"] = "partially_supported"
        else:
            metadata["analysis_support_level"] = "preliminary"
    return metadata


def _metadata_lines(metadata: dict) -> list[str]:
    return [
        "## Analisis multiorganismo",
        "",
        f"- Organismo analizado: `{metadata.get('organism', 'not_reported')}`",
        f"- Cepa: `{metadata.get('strain', 'not_reported')}`",
        f"- Taxon id: `{metadata.get('taxon_id', 'not_reported')}`",
        f"- Workspace: `{metadata.get('workspace', 'not_reported')}`",
        f"- Nivel de respaldo global: `{metadata.get('analysis_support_level', 'preliminary')}`",
        f"- Capas disponibles: `{', '.join(metadata.get('available_layers', [])) or 'none'}`",
        f"- Capas obligatorias faltantes: `{', '.join(metadata.get('missing_layers', [])) or 'none'}`",
        f"- Capas de usuario: `{', '.join(metadata.get('user_layers', [])) or 'none'}`",
        f"- Capas externas/curadas/computadas: `{', '.join(metadata.get('external_layers', [])) or 'none'}`",
        f"- Capas demo/proxy/controladas: `{', '.join(metadata.get('demo_or_proxy_layers', [])) or 'none'}`",
        "",
    ]


def _build_provenance_summary(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for database_column, label in OPTIONAL_SOURCE_COLUMNS.items():
        source_type_column = f"{label}_source_type"
        source_quality_column = f"{label}_source_quality"
        if database_column not in features.columns:
            continue
        present = features[database_column].fillna("").astype(str).str.strip().ne("")
        subset = features.loc[present].copy()
        if subset.empty:
            rows.append(
                {
                    "dataset": label,
                    "records_with_data": 0,
                    "dominant_source_type": "missing",
                    "mean_source_quality": 0.0,
                    "status": "missing",
                }
            )
            continue
        rows.append(
            {
                "dataset": label,
                "records_with_data": int(present.sum()),
                "dominant_source_type": subset[source_type_column].mode().iloc[0],
                "mean_source_quality": round(float(subset[source_quality_column].mean()), 4),
                "status": "demo_only" if subset[source_type_column].eq("demo").all() else "contains_non_demo",
            }
        )
    return pd.DataFrame(rows)


def _build_layer_resolution_summary(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame()
    first_row = features.iloc[0]
    rows = []
    for layer_key in TARGET_LAYER_KEYS:
        source_type_column = f"{layer_key}_source_type"
        if source_type_column not in features.columns:
            continue
        confidence_value = first_row.get(f"{layer_key}_layer_confidence", first_row.get(f"{layer_key}_confidence", 0.0))
        confidence_numeric = pd.to_numeric(pd.Series([confidence_value]), errors="coerce").fillna(0.0).iloc[0]
        source_type_value = first_row.get(f"{layer_key}_layer_source_type", first_row.get(source_type_column, "missing"))
        rows.append(
            {
                "layer": layer_key,
                "source_type": source_type_value,
                "source_name": first_row.get(f"{layer_key}_source_name", "missing"),
                "is_user_supplied": bool(first_row.get(f"{layer_key}_is_user_supplied", False)),
                "is_external": bool(first_row.get(f"{layer_key}_is_external", False)),
                "is_cached": bool(first_row.get(f"{layer_key}_is_cached", False)),
                "is_proxy": bool(first_row.get(f"{layer_key}_is_proxy", False)),
                "confidence": float(confidence_numeric),
                "retrieval_status": first_row.get(f"{layer_key}_retrieval_status", "missing"),
                "generated_by": first_row.get(f"{layer_key}_generated_by", "not_reported"),
            }
        )
    return pd.DataFrame(rows)


def _build_therapeutic_role_summary(phase2_ranking: pd.DataFrame) -> pd.DataFrame:
    if phase2_ranking.empty or "therapeutic_role" not in phase2_ranking.columns:
        return pd.DataFrame()
    return (
        phase2_ranking.groupby("therapeutic_role", as_index=False)
        .agg(
            candidate_count=("protein_id", "size"),
            mean_therapeutic_priority_score=("therapeutic_priority_score", "mean"),
            mean_meta_priority_score=("meta_priority_score", "mean"),
        )
        .sort_values(["candidate_count", "mean_therapeutic_priority_score"], ascending=[False, False])
        .reset_index(drop=True)
    )


def _build_therapeutic_rule_summary(phase2_ranking: pd.DataFrame) -> pd.DataFrame:
    if phase2_ranking.empty or "therapeutic_role_rule" not in phase2_ranking.columns:
        return pd.DataFrame()
    return (
        phase2_ranking.groupby(["therapeutic_role", "therapeutic_role_rule"], as_index=False)
        .agg(
            candidate_count=("protein_id", "size"),
            mean_therapeutic_priority_score=("therapeutic_priority_score", "mean"),
        )
        .sort_values(["candidate_count", "mean_therapeutic_priority_score"], ascending=[False, False])
        .reset_index(drop=True)
    )


def _build_therapeutic_role_stability_audit(phase2_ranking: pd.DataFrame) -> pd.DataFrame:
    required = {
        "protein_id",
        "gene",
        "therapeutic_role_with_controlled_provider",
        "therapeutic_role_without_controlled_provider",
        "therapeutic_role_stability",
    }
    if phase2_ranking.empty or not required.issubset(set(phase2_ranking.columns)):
        return pd.DataFrame()
    audit = phase2_ranking.copy()
    audit["rank"] = audit.index
    columns = [
        "rank",
        "protein_id",
        "gene",
        "therapeutic_role_with_controlled_provider",
        "therapeutic_role_without_controlled_provider",
        "therapeutic_role_stability",
        "therapeutic_role_stability_explanation",
        "therapeutic_priority_score",
        "therapeutic_priority_score_without_controlled_provider",
        "therapeutic_priority_controlled_delta",
        "controlled_context_max_feature_delta",
        "host_damage_score_controlled_delta",
        "infection_site_access_score_controlled_delta",
        "infection_context_score_controlled_delta",
        "therapeutic_rule_boundary_margin",
        "therapeutic_rule_boundary_proximity",
        "therapeutic_role_rule",
        "therapeutic_role_rule_without_controlled_provider",
        "controlled_dependency_flags",
        "clinical_impact_input_status",
        "curated_disease_context_input_status",
        "therapy_site_context_input_status",
        "therapeutic_context_input_summary",
        "clinical_impact_source_name",
        "curated_disease_context_source_name",
        "therapy_site_context_source_name",
        "confidence_source_class",
        "confidence_evidence_tier",
    ]
    return audit[[column for column in columns if column in audit.columns]].copy()


def _build_therapeutic_role_stability_summary(stability_audit: pd.DataFrame) -> pd.DataFrame:
    if stability_audit.empty or "therapeutic_role_stability" not in stability_audit.columns:
        return pd.DataFrame()
    return (
        stability_audit.groupby("therapeutic_role_stability", as_index=False)
        .agg(
            candidate_count=("protein_id", "size"),
            mean_therapeutic_priority_score=("therapeutic_priority_score", "mean"),
        )
        .sort_values("candidate_count", ascending=False)
        .reset_index(drop=True)
    )


def _build_human_homologs_audit(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty or "homology_evidence_tier" not in features.columns:
        return pd.DataFrame()
    audit = features.copy()
    audit["homology_evidence_tier"] = audit["homology_evidence_tier"].fillna("not_reported").astype(str)
    audit["homology_lookup_status"] = audit.get(
        "homology_lookup_status",
        pd.Series(["not_reported"] * len(audit), index=audit.index),
    ).fillna("not_reported").astype(str)
    audit["homology_confidence_score"] = pd.to_numeric(
        audit.get("homology_confidence_score", pd.Series([0.0] * len(audit), index=audit.index)),
        errors="coerce",
    ).fillna(0.0)
    return (
        audit.groupby(["homology_evidence_tier", "homology_lookup_status"], as_index=False)
        .agg(
            candidate_count=("protein_id", "size"),
            mean_homology_confidence_score=("homology_confidence_score", "mean"),
            human_homolog_positive_count=(
                "human_homolog",
                lambda series: int(pd.to_numeric(series, errors="coerce").fillna(0).eq(1).sum()),
            ),
        )
        .sort_values(["candidate_count", "mean_homology_confidence_score"], ascending=[False, False])
        .reset_index(drop=True)
    )


def _build_evolutionary_escape_risk_audit(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame()
    audit = features.copy()
    columns = [
        "protein_id",
        "gene",
        *EVOLUTIONARY_ESCAPE_RISK_REPORT_COLUMNS,
        "evolutionary_escape_risk_input_confidence",
        "evolutionary_escape_risk_notes",
        "evolutionary_escape_risk_explicit_variable_count",
        "evolutionary_escape_risk_available_variable_count",
        "evolutionary_escape_risk_source_name",
        "evolutionary_escape_risk_retrieval_status",
    ]
    return audit[[column for column in columns if column in audit.columns]].copy()


def _load_context_layer_for_audit(processed_dir: Path, filename: str, score_column: str, layer_name: str) -> pd.DataFrame:
    path = processed_dir / filename
    if not path.exists():
        return pd.DataFrame(columns=["protein_id", "layer", "score", "controlled_context_rule", "controlled_context_inputs"])
    df = pd.read_csv(path)
    protein_column = "protein_id_canonical" if "protein_id_canonical" in df.columns else "protein_id"
    if protein_column not in df.columns or score_column not in df.columns:
        return pd.DataFrame(columns=["protein_id", "layer", "score", "controlled_context_rule", "controlled_context_inputs"])
    audit = pd.DataFrame(
        {
            "protein_id": df[protein_column].astype(str),
            "layer": layer_name,
            "score": pd.to_numeric(df[score_column], errors="coerce"),
            "controlled_context_rule": df.get(
                "controlled_context_rule",
                pd.Series(["not_reported"] * len(df), index=df.index),
            ).fillna("not_reported").astype(str),
            "controlled_context_inputs": df.get(
                "controlled_context_inputs",
                pd.Series(["not_reported"] * len(df), index=df.index),
            ).fillna("not_reported").astype(str),
            "controlled_context_missing_flags": df.get(
                "controlled_context_missing_flags",
                pd.Series(["not_reported"] * len(df), index=df.index),
            ).fillna("not_reported").astype(str),
        }
    )
    return audit


def _controlled_input_keys(input_text: object) -> set[str]:
    text = str(input_text or "").strip()
    if not text or text == "not_reported":
        return set()
    keys = set()
    for chunk in text.split(";"):
        key, _, _ = chunk.strip().partition("=")
        if key:
            keys.add(key)
    return keys


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _separation_status(score_correlation: float, input_overlap: float) -> str:
    abs_corr = abs(score_correlation)
    if abs_corr >= 0.90 or input_overlap >= 0.75:
        return "high_overlap_review_needed"
    if abs_corr >= 0.70 or input_overlap >= 0.50:
        return "moderate_overlap_monitor"
    return "separated_for_current_rules"


def _build_therapeutic_context_separation_audit(base_dir: Path, features: pd.DataFrame) -> pd.DataFrame:
    processed_dir = base_dir / "data_processed"
    layer_tables = [
        _load_context_layer_for_audit(processed_dir, "normalized_clinical_impact.csv", "host_damage_score", "clinical_impact"),
        _load_context_layer_for_audit(processed_dir, "normalized_curated_disease_context.csv", "infection_context_score", "curated_disease_context"),
        _load_context_layer_for_audit(processed_dir, "normalized_therapy_site_context.csv", "infection_site_access", "therapy_site_context"),
    ]
    layers = [table for table in layer_tables if not table.empty]
    if len(layers) < 2:
        available_layers = "; ".join(str(table["layer"].iloc[0]) for table in layers) if layers else "none"
        return pd.DataFrame(
            [
                {
                    "left_layer": available_layers,
                    "right_layer": "not_available",
                    "shared_candidates": 0,
                    "score_correlation": 0.0,
                    "input_key_overlap": 0.0,
                    "left_rule": "not_enough_context_layers",
                    "right_rule": "not_enough_context_layers",
                    "separation_status": "not_enough_layers_to_compare",
                    "left_inputs": "not_reported",
                    "right_inputs": "not_reported",
                }
            ]
        )

    layer_lookup = {str(table["layer"].iloc[0]): table for table in layers}
    rows = []
    layer_names = ["clinical_impact", "curated_disease_context", "therapy_site_context"]
    for left_index, left_name in enumerate(layer_names):
        for right_name in layer_names[left_index + 1 :]:
            if left_name not in layer_lookup or right_name not in layer_lookup:
                continue
            left = layer_lookup[left_name]
            right = layer_lookup[right_name]
            paired = left[["protein_id", "score"]].rename(columns={"score": "left_score"}).merge(
                right[["protein_id", "score"]].rename(columns={"score": "right_score"}),
                on="protein_id",
                how="inner",
            )
            if len(paired) >= 2 and paired["left_score"].nunique(dropna=True) > 1 and paired["right_score"].nunique(dropna=True) > 1:
                correlation = float(paired["left_score"].corr(paired["right_score"]))
            else:
                correlation = 0.0
            left_inputs = set().union(*left["controlled_context_inputs"].map(_controlled_input_keys).tolist())
            right_inputs = set().union(*right["controlled_context_inputs"].map(_controlled_input_keys).tolist())
            input_overlap = _jaccard(left_inputs, right_inputs)
            left_rule = left["controlled_context_rule"].mode().iloc[0] if not left["controlled_context_rule"].empty else "not_reported"
            right_rule = right["controlled_context_rule"].mode().iloc[0] if not right["controlled_context_rule"].empty else "not_reported"
            rows.append(
                {
                    "left_layer": left_name,
                    "right_layer": right_name,
                    "shared_candidates": int(len(paired)),
                    "score_correlation": round(correlation, 4),
                    "input_key_overlap": round(input_overlap, 4),
                    "left_rule": left_rule,
                    "right_rule": right_rule,
                    "separation_status": _separation_status(correlation, input_overlap),
                    "left_inputs": "; ".join(sorted(left_inputs)) if left_inputs else "not_reported",
                    "right_inputs": "; ".join(sorted(right_inputs)) if right_inputs else "not_reported",
                }
            )
    audit = pd.DataFrame(rows)
    if audit.empty:
        return audit
    for layer_key in ["clinical_impact", "curated_disease_context", "therapy_site_context"]:
        source_column = f"{layer_key}_source_name"
        status_column = f"{layer_key}_retrieval_status"
        if source_column in features.columns:
            audit[f"{layer_key}_source_name"] = str(features[source_column].dropna().iloc[0]) if not features[source_column].dropna().empty else "missing"
        if status_column in features.columns:
            audit[f"{layer_key}_retrieval_status"] = str(features[status_column].dropna().iloc[0]) if not features[status_column].dropna().empty else "missing"
    return audit


def _replacement_readiness_status(source_name: str, source_type: str, rows_with_reference: int, total_rows: int) -> str:
    source_text = f"{source_name} {source_type}".lower()
    if source_type == "user" and rows_with_reference > 0:
        return "user_curated_with_traceable_references"
    if source_type == "user":
        return "user_curated_needs_reference_metadata"
    if "controlled" in source_text or source_type in {"proxy", "external"}:
        return "controlled_or_proxy_needs_real_evidence"
    if total_rows == 0:
        return "missing_layer_needs_curated_input"
    return "review_source_quality"


def _build_controlled_replacement_readiness(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame()
    rows = []
    clinical_total = len(features)
    clinical_reference = (
        features.get("clinical_impact_evidence_reference", pd.Series([""] * len(features), index=features.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .map(lambda value: value not in {"", "nan", "none", "not_reported", "not_experimental"})
        .sum()
    )
    clinical_type = (
        features.get("clinical_impact_evidence_type", pd.Series([""] * len(features), index=features.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .map(lambda value: value not in {"", "nan", "none", "not_reported", "controlled_provider"})
        .sum()
    )
    therapy_total = len(features)
    therapy_reference = (
        features.get("access_evidence_reference", pd.Series([""] * len(features), index=features.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )
    therapy_type = (
        features.get("access_evidence_type", pd.Series([""] * len(features), index=features.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )
    disease_total = len(features)
    disease_reference = (
        features.get("context_evidence_reference", pd.Series([""] * len(features), index=features.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .map(lambda value: value not in {"", "nan", "none", "not_reported", "not_experimental"})
        .sum()
    )
    disease_type = (
        features.get("context_evidence_type", pd.Series([""] * len(features), index=features.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .map(lambda value: value not in {"", "nan", "none", "not_reported", "controlled_provider"})
        .sum()
    )
    layer_guidance = {
        "clinical_impact": {
            "controlled_replacement_target": "curated clinical or experimental host damage evidence",
            "minimal_user_columns": (
                "protein_id; gene; host_direct_damage_score; virulence_associated_severity_score; "
                "clinical_impact_score; clinical_impact_evidence_type; clinical_impact_evidence_reference; database"
            ),
            "next_step": "curate organism-specific damage or severity evidence before increasing confidence",
            "rows_with_reference": int(clinical_reference),
            "rows_with_evidence_type": int(clinical_type),
            "total_rows": int(clinical_total),
        },
        "curated_disease_context": {
            "controlled_replacement_target": "curated infection-stage relevance or in vivo expression evidence",
            "minimal_user_columns": (
                "protein_id; gene; infection_context_score; disease_context; infection_stage; "
                "context_evidence_type; context_evidence_reference; database"
            ),
            "next_step": "add curated infection context evidence for the organism or disease model",
            "rows_with_reference": int(disease_reference),
            "rows_with_evidence_type": int(disease_type),
            "total_rows": int(disease_total),
        },
        "therapy_site_context": {
            "controlled_replacement_target": "curated infection site accessibility or permeability evidence",
            "minimal_user_columns": (
                "protein_id; gene; infection_site_access; infection_site; "
                "access_evidence_type; access_evidence_reference; access_evidence_note; database"
            ),
            "next_step": "populate data_user/therapy_site_context.csv with traceable site/access evidence",
            "rows_with_reference": int(therapy_reference),
            "rows_with_evidence_type": int(therapy_type),
            "total_rows": int(therapy_total),
        },
    }
    for layer_key, guidance in layer_guidance.items():
        source_type = str(features.get(f"{layer_key}_source_type", pd.Series(["missing"])).iloc[0])
        source_name = str(features.get(f"{layer_key}_source_name", pd.Series(["missing"])).iloc[0])
        retrieval_status = str(features.get(f"{layer_key}_retrieval_status", pd.Series(["missing"])).iloc[0])
        rows.append(
            {
                "layer": layer_key,
                "source_type": source_type,
                "source_name": source_name,
                "retrieval_status": retrieval_status,
                "replacement_readiness_status": _replacement_readiness_status(
                    source_name,
                    source_type,
                    int(guidance["rows_with_reference"]),
                    int(guidance["total_rows"]),
                ),
                "rows_with_reference": int(guidance["rows_with_reference"]),
                "rows_with_evidence_type": int(guidance["rows_with_evidence_type"]),
                "total_rows": int(guidance["total_rows"]),
                "controlled_replacement_target": guidance["controlled_replacement_target"],
                "minimal_user_columns": guidance["minimal_user_columns"],
                "next_step": guidance["next_step"],
            }
        )
    return pd.DataFrame(rows)


def _needs_clinical_impact_curation(row: pd.Series) -> bool:
    source_type = str(row.get("clinical_impact_source_type", "") or "").strip().lower()
    source_name = str(row.get("clinical_impact_source_name", "") or "").strip().lower()
    reference = str(row.get("clinical_impact_evidence_reference", "") or "").strip().lower()
    evidence_type = str(row.get("clinical_impact_evidence_type", "") or "").strip().lower()
    catalog_source = str(row.get("clinical_impact_catalog_source", "") or "").strip().lower()
    direct_is_proxy = bool(row.get("host_direct_damage_score_is_proxy", False))
    severity_is_proxy = bool(row.get("virulence_associated_severity_score_is_proxy", False))
    if source_type != "user" and "curated" not in source_name and "curated" not in catalog_source:
        return True
    if reference in {"", "nan", "none", "not_reported", "not_experimental"}:
        return True
    if evidence_type in {"", "nan", "none", "not_reported", "controlled_provider"}:
        return True
    return direct_is_proxy or severity_is_proxy or "controlled" in source_name or "proxy" in source_name


def _build_clinical_impact_curation_queue(phase2_ranking: pd.DataFrame, top_n: int) -> pd.DataFrame:
    columns = [
        "rank",
        "protein_id",
        "gene",
        "therapeutic_role",
        "therapeutic_priority_score",
        "current_host_direct_damage_score",
        "current_virulence_associated_severity_score",
        "current_clinical_impact_score",
        "current_clinical_impact_source",
        "current_clinical_impact_status",
        "current_clinical_impact_evidence_type",
        "current_clinical_impact_evidence_reference",
        "needs_curated_clinical_impact",
        "curated_host_direct_damage_score",
        "curated_virulence_associated_severity_score",
        "curated_clinical_impact_score",
        "curated_clinical_impact_evidence_type",
        "curated_clinical_impact_evidence_reference",
        "curated_clinical_impact_evidence_note",
        "curated_database",
    ]
    if phase2_ranking.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for rank, (_, row) in enumerate(phase2_ranking.head(top_n).iterrows(), start=1):
        current_reference = str(row.get("clinical_impact_evidence_reference", "") or "").strip()
        current_evidence_type = str(row.get("clinical_impact_evidence_type", "") or "").strip()
        rows.append(
            {
                "rank": rank,
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "therapeutic_role": row.get("therapeutic_role", "not_reported"),
                "therapeutic_priority_score": row.get("therapeutic_priority_score", 0.0),
                "current_host_direct_damage_score": row.get("host_direct_damage_score", 0.0),
                "current_virulence_associated_severity_score": row.get("virulence_associated_severity_score", 0.0),
                "current_clinical_impact_score": row.get("clinical_impact_score", 0.0),
                "current_clinical_impact_source": row.get("clinical_impact_source_name", "not_reported"),
                "current_clinical_impact_status": row.get("clinical_impact_retrieval_status", "not_reported"),
                "current_clinical_impact_evidence_type": current_evidence_type or "not_reported",
                "current_clinical_impact_evidence_reference": current_reference or "not_reported",
                "needs_curated_clinical_impact": _needs_clinical_impact_curation(row),
                "curated_host_direct_damage_score": "",
                "curated_virulence_associated_severity_score": "",
                "curated_clinical_impact_score": "",
                "curated_clinical_impact_evidence_type": "",
                "curated_clinical_impact_evidence_reference": "",
                "curated_clinical_impact_evidence_note": "",
                "curated_database": "",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _needs_disease_context_curation(row: pd.Series) -> bool:
    source_type = str(row.get("curated_disease_context_source_type", "") or "").strip().lower()
    source_name = str(row.get("curated_disease_context_source_name", "") or "").strip().lower()
    reference = str(row.get("context_evidence_reference", "") or "").strip().lower()
    evidence_type = str(row.get("context_evidence_type", "") or "").strip().lower()
    disease_context = str(row.get("disease_context", "") or "").strip().lower()
    infection_stage = str(row.get("infection_stage", "") or "").strip().lower()
    score_is_proxy = bool(row.get("infection_context_score_is_proxy", False))
    if source_type != "user" and "curated" not in source_name:
        return True
    if reference in {"", "nan", "none", "not_reported", "not_experimental"}:
        return True
    if evidence_type in {"", "nan", "none", "not_reported", "controlled_provider"}:
        return True
    if disease_context in {"", "nan", "none", "not_reported"}:
        return True
    if infection_stage in {"", "nan", "none", "not_reported"}:
        return True
    return score_is_proxy or "controlled" in source_name or "proxy" in source_name


def _build_disease_context_curation_queue(phase2_ranking: pd.DataFrame, top_n: int) -> pd.DataFrame:
    columns = [
        "rank",
        "protein_id",
        "gene",
        "therapeutic_role",
        "therapeutic_priority_score",
        "current_infection_context_score",
        "current_disease_context",
        "current_infection_stage",
        "current_context_evidence_type",
        "current_context_evidence_reference",
        "current_curated_disease_context_source",
        "current_curated_disease_context_status",
        "needs_curated_disease_context",
        "curated_infection_context_score",
        "curated_disease_context",
        "curated_infection_stage",
        "curated_context_evidence_type",
        "curated_context_evidence_reference",
        "curated_context_evidence_note",
        "curated_database",
    ]
    if phase2_ranking.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for rank, (_, row) in enumerate(phase2_ranking.head(top_n).iterrows(), start=1):
        current_reference = str(row.get("context_evidence_reference", "") or "").strip()
        current_evidence_type = str(row.get("context_evidence_type", "") or "").strip()
        rows.append(
            {
                "rank": rank,
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "therapeutic_role": row.get("therapeutic_role", "not_reported"),
                "therapeutic_priority_score": row.get("therapeutic_priority_score", 0.0),
                "current_infection_context_score": row.get("infection_context_score", 0.0),
                "current_disease_context": row.get("disease_context", "not_reported"),
                "current_infection_stage": row.get("infection_stage", "not_reported"),
                "current_context_evidence_type": current_evidence_type or "not_reported",
                "current_context_evidence_reference": current_reference or "not_reported",
                "current_curated_disease_context_source": row.get("curated_disease_context_source_name", "not_reported"),
                "current_curated_disease_context_status": row.get("curated_disease_context_retrieval_status", "not_reported"),
                "needs_curated_disease_context": _needs_disease_context_curation(row),
                "curated_infection_context_score": "",
                "curated_disease_context": "",
                "curated_infection_stage": "",
                "curated_context_evidence_type": "",
                "curated_context_evidence_reference": "",
                "curated_context_evidence_note": "",
                "curated_database": "",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _needs_site_context_curation(row: pd.Series) -> bool:
    source_type = str(row.get("therapy_site_context_source_type", "") or "").strip().lower()
    source_name = str(row.get("therapy_site_context_source_name", "") or "").strip().lower()
    reference = str(row.get("access_evidence_reference", "") or "").strip().lower()
    evidence_type = str(row.get("access_evidence_type", "") or "").strip().lower()
    if source_type != "user":
        return True
    if reference in {"", "nan", "none", "not_reported"}:
        return True
    if evidence_type in {"", "nan", "none", "not_reported"}:
        return True
    return "controlled" in source_name or "proxy" in source_name


def _build_therapy_site_context_curation_queue(phase2_ranking: pd.DataFrame, top_n: int) -> pd.DataFrame:
    if phase2_ranking.empty:
        return pd.DataFrame(
            columns=[
                "rank",
                "protein_id",
                "gene",
                "therapeutic_role",
                "therapeutic_priority_score",
                "current_infection_site_access_score",
                "current_therapy_site_context_source",
                "current_therapy_site_context_status",
                "needs_curated_site_context",
                "curated_infection_site_access",
                "curated_infection_site",
                "curated_access_evidence_type",
                "curated_access_evidence_reference",
                "curated_access_evidence_note",
                "curated_database",
            ]
        )

    rows = []
    for rank, (_, row) in enumerate(phase2_ranking.head(top_n).iterrows(), start=1):
        current_reference = str(row.get("access_evidence_reference", "") or "").strip()
        current_evidence_type = str(row.get("access_evidence_type", "") or "").strip()
        rows.append(
            {
                "rank": rank,
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "therapeutic_role": row.get("therapeutic_role", "not_reported"),
                "therapeutic_priority_score": row.get("therapeutic_priority_score", 0.0),
                "current_infection_site_access_score": row.get("infection_site_access_score", 0.0),
                "current_infection_site": row.get("infection_site", "not_reported"),
                "current_access_evidence_type": current_evidence_type or "not_reported",
                "current_access_evidence_reference": current_reference or "not_reported",
                "current_therapy_site_context_source": row.get("therapy_site_context_source_name", "not_reported"),
                "current_therapy_site_context_status": row.get("therapy_site_context_retrieval_status", "not_reported"),
                "needs_curated_site_context": _needs_site_context_curation(row),
                "curated_infection_site_access": "",
                "curated_infection_site": "",
                "curated_access_evidence_type": "",
                "curated_access_evidence_reference": "",
                "curated_access_evidence_note": "",
                "curated_database": "",
            }
        )
    return pd.DataFrame(rows)


def _build_top_candidate_review(
    phase2_ranking: pd.DataFrame,
    sensitivity: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    top_candidates = phase2_ranking.head(top_n).copy()
    rows = []
    for _, row in top_candidates.iterrows():
        protein_id = row["protein_id"]
        preferred_strategy = row.get("preferred_strategy", "unknown")
        if sensitivity.empty or not {"score_name", "protein_id", "rank_delta_vs_base"}.issubset(sensitivity.columns):
            meta_rows = pd.DataFrame()
            preferred_rows = pd.DataFrame()
        else:
            meta_rows = sensitivity.loc[
                (sensitivity["score_name"] == "meta_priority") & (sensitivity["protein_id"] == protein_id)
            ].copy()
            preferred_rows = sensitivity.loc[
                (sensitivity["score_name"] == preferred_strategy) & (sensitivity["protein_id"] == protein_id)
            ].copy()
        meta_span = int(meta_rows["rank_delta_vs_base"].abs().max()) if not meta_rows.empty else 0
        preferred_span = int(preferred_rows["rank_delta_vs_base"].abs().max()) if not preferred_rows.empty else 0
        if row.get("data_realism_flag") == "demo_only" and (meta_span >= 3 or preferred_span >= 2):
            recommendation = "promising_but_demo_sensitive"
        elif row.get("strategy_margin_score", 0.0) >= 0.15 and meta_span <= 1 and preferred_span <= 1:
            recommendation = "robust_for_current_evidence"
        elif row.get("strategy_margin_score", 0.0) < 0.05:
            recommendation = "multi_strategy_borderline"
        else:
            recommendation = "strategy_sensitive"

        rows.append(
            {
                "rank": int(row.name),
                "protein_id": protein_id,
                "gene": row["gene"],
                "therapeutic_role": row.get("therapeutic_role", "low_priority_candidate"),
                "therapeutic_role_v3": row.get("therapeutic_role_v3", "not_reported"),
                "therapeutic_role_v3_reason": row.get("therapeutic_role_v3_reason", "not_reported"),
                "phase3_evidence_confidence_label": row.get("phase3_evidence_confidence_label", "not_reported"),
                "phase3_recommendation": row.get("phase3_recommendation", "not_reported"),
                "meta_priority_score_v3": row.get("meta_priority_score_v3", 0.0),
                "functional_node_theory_confidence": row.get("functional_node_theory_confidence", 0.0),
                "functional_node_theory_label": row.get("functional_node_theory_label", "not_reported"),
                "evidence_quality_score": row.get("evidence_quality_score", 0.0),
                "confidence_ceiling": row.get("confidence_ceiling", 0.0),
                "host_similarity_risk": row.get("host_similarity_risk", 0.0),
                "phase3_real_evidence_layer_count": row.get("phase3_real_evidence_layer_count", 0),
                "phase3_demo_default_layer_count": row.get("phase3_demo_default_layer_count", 0),
                "phase3_missing_layer_count": row.get("phase3_missing_layer_count", 0),
                "phase3_negative_evidence_count": row.get("phase3_negative_evidence_count", 0),
                "phase3_evidence_gap_summary": row.get("phase3_evidence_gap_summary", "not_reported"),
                "phase3_negative_evidence_summary": row.get("phase3_negative_evidence_summary", "not_reported"),
                "phase3_evidence_explanation": row.get("phase3_evidence_explanation", "not_reported"),
                "therapeutic_priority_score": row.get("therapeutic_priority_score", 0.0),
                "preferred_strategy": preferred_strategy,
                "meta_sensitivity_span": meta_span,
                "preferred_strategy_sensitivity_span": preferred_span,
                "data_realism_flag": row.get("data_realism_flag", "unknown"),
                "recommendation": recommendation,
                "review_note": (
                    f"drivers={row['top_positive_drivers']}; "
                    f"risks={str(row['top_negative_drivers']).split(';')[0]}; "
                    f"host_risk={row.get('host_risk_audit_summary', 'not_reported')}; "
                    f"sources={row.get('optional_data_source_summary', 'none')}"
                ),
            }
        )
    return pd.DataFrame(rows)


def _parse_driver_names(driver_text: str) -> list[str]:
    if not isinstance(driver_text, str) or not driver_text.strip():
        return []
    drivers = []
    for chunk in driver_text.split(";"):
        item = chunk.strip()
        if not item or "=" not in item:
            continue
        name, _, _ = item.partition("=")
        drivers.append(name.strip())
    return drivers


def _strategy_label(preferred_strategy: str, margin: float) -> str:
    if margin < 0.05:
        return "hybrid"
    return STRATEGY_LABELS.get(preferred_strategy, preferred_strategy or "hybrid")


def _sensitivity_spans(sensitivity: pd.DataFrame, protein_id: str, preferred_strategy: str) -> tuple[int, int]:
    if sensitivity.empty or not {"score_name", "protein_id", "rank_delta_vs_base"}.issubset(sensitivity.columns):
        return 0, 0
    meta_rows = sensitivity.loc[
        (sensitivity["score_name"] == "meta_priority") & (sensitivity["protein_id"] == protein_id)
    ].copy()
    preferred_rows = sensitivity.loc[
        (sensitivity["score_name"] == preferred_strategy) & (sensitivity["protein_id"] == protein_id)
    ].copy()
    meta_span = int(meta_rows["rank_delta_vs_base"].abs().max()) if not meta_rows.empty else 0
    preferred_span = int(preferred_rows["rank_delta_vs_base"].abs().max()) if not preferred_rows.empty else 0
    return meta_span, preferred_span


def _driver_biological_text(driver_names: list[str], row: pd.Series) -> str:
    mapping = {
        "antibiotic_target_score": "el perfil favorece un uso como blanco antibiÃ³tico",
        "antivirulence_target_score": "el perfil favorece una estrategia antivirulencia",
        "functional_node_score": "el perfil sugiere impacto funcional o de red dentro del modelo",
    }
    parts = [mapping[name] for name in driver_names if name in mapping]
    if row.get("evidence_coverage_score", 0) >= 1.0:
        parts.append("la cobertura de evidencia interna es completa en las capas hoy cargadas")
    return "; ".join(parts) if parts else "la seÃ±al positiva proviene del score compuesto actual"


def _negative_biological_text(driver_names: list[str]) -> str:
    mapping = {
        "antibiotic_target_score": "la lectura como blanco antibiÃ³tico no es dominante",
        "antivirulence_target_score": "la lectura antivirulencia no es dominante",
        "functional_node_score": "la capa funcional no lo empuja con la misma fuerza",
    }
    parts = [mapping[name] for name in driver_names if name in mapping]
    return "; ".join(parts) if parts else "no se observa una debilidad dominante mÃ¡s allÃ¡ del balance entre estrategias"


def _host_risk_methodological_text(row: pd.Series) -> str:
    summary = str(row.get("host_risk_audit_summary", "") or "").strip()
    if not summary or summary.lower() in {"nan", "none", "not_reported"}:
        return "La auditoria de seguridad frente al hospedero no esta disponible para este candidato."

    retrieval_status = str(row.get("host_annotation_retrieval_status", "") or "")
    source_name = str(row.get("host_annotation_source_name", "") or "")
    rule = str(row.get("interpro_rule", "") or row.get("host_annotation_rule", "") or "")
    essentiality_status = str(row.get("human_essentiality_status", "") or "")
    missing_flags = str(row.get("interpro_missing_flags", "") or row.get("host_annotation_missing_flags", "") or "")

    host_criticality = float(row.get("host_criticality_penalty", 0.0))
    domain_overlap = float(row.get("domain_overlap_score", 0.0))
    source_note = source_name if source_name and source_name.lower() != "nan" else "fuente no especificada"
    status_note = retrieval_status if retrieval_status and retrieval_status.lower() != "nan" else "estado no especificado"

    if "interpro_shared_domain" in rule:
        evidence_note = "usa dominios InterPro comparables"
    elif "fallback" in status_note or "controlled" in source_note:
        evidence_note = "usa fallback controlado por falta de dominios comparables"
    elif "host_annotation.csv" in source_note or status_note == "resolved_from_raw":
        evidence_note = "usa la capa local de host_annotation"
    else:
        evidence_note = "usa una regla de anotacion del hospedero no clasificada"

    if host_criticality >= 0.65:
        risk_level = "riesgo alto"
    elif host_criticality >= 0.35 or domain_overlap >= 0.35:
        risk_level = "riesgo intermedio"
    else:
        risk_level = "riesgo bajo segun las senales actuales"

    extras = []
    if essentiality_status and essentiality_status.lower() not in {"nan", "not_reported", "none"}:
        extras.append(f"essentialidad humana={essentiality_status}")
    if missing_flags and missing_flags.lower() not in {"nan", "none", "not_reported"}:
        extras.append(f"faltantes={missing_flags}")
    extra_text = "; " + "; ".join(extras) if extras else ""

    return (
        f"Seguridad hospedero: {risk_level}; {evidence_note}; "
        f"fuente={source_note}; estado={status_note}; "
        f"domain_overlap={domain_overlap:.3f}; host_criticality={host_criticality:.3f}{extra_text}."
    )


def _recommended_next_evidence(strategy_label: str, row: pd.Series) -> str:
    if row.get("data_realism_flag") == "demo_only":
        if strategy_label == "antibiotic":
            return "priorizar datos curados no demo de conservaciÃ³n entre cepas y una anotaciÃ³n de seguridad del hospedero mÃ¡s realista"
        if strategy_label == "antivirulence":
            return "priorizar una mediciÃ³n menos proxy del impacto sobre daÃ±o al hospedero y accesibilidad en contexto de infecciÃ³n"
        if strategy_label == "functional_node":
            return "priorizar una red funcional no demo y medidas observadas de redundancia o dependencia"
        return "priorizar al menos una capa opcional no demo para separar mejor seÃ±ales hÃ­bridas"
    if strategy_label == "antibiotic":
        return "evaluar conservaciÃ³n multicepa y riesgo de off-target en hospedero"
    if strategy_label == "antivirulence":
        return "medir impacto sobre daÃ±o al hospedero y accesibilidad en contexto de infeccion"
    if strategy_label == "functional_node":
        return "evaluar centralidad y dependencia con una red funcional externa curada"
    return "aÃ±adir evidencia que permita discriminar mejor entre estrategias"


def _robustness_label(row: pd.Series, meta_span: int, preferred_span: int) -> str:
    margin = float(row.get("strategy_margin_score", 0.0))
    realism = str(row.get("data_realism_flag", "unknown"))
    score = float(row.get("meta_priority_score", 0.0))
    if margin < 0.05 or meta_span >= 4:
        return "strategy_dependent"
    if realism == "demo_only" and (meta_span >= 2 or preferred_span >= 2):
        return "promising_but_demo_sensitive"
    if score < 0.60 or preferred_span >= 3:
        return "borderline"
    if realism != "demo_only" and meta_span <= 1 and preferred_span <= 1:
        return "robust"
    if realism == "demo_only":
        return "promising_but_demo_sensitive"
    return "borderline"


def _audit_confidence(row: pd.Series, meta_span: int, preferred_span: int) -> str:
    quality = float(row.get("optional_data_quality_score", 0.0))
    realism = str(row.get("data_realism_flag", "unknown"))
    if realism == "demo_only" and (meta_span >= 3 or preferred_span >= 2):
        return "low"
    if quality >= 0.8 and meta_span <= 1 and preferred_span <= 1:
        return "high"
    return "medium"


TOP10_SCIENTIFIC_AUDIT_COLUMNS = [
    "rank",
    "rank_phase3_real_candidates",
    "protein_id",
    "gene",
    "meta_priority_score_v3",
    "therapeutic_priority_score",
    "therapeutic_priority_contribution_summary",
    "therapeutic_priority_components",
    "therapeutic_role_v3",
    "theory_v3_assessment_note",
    "candidate_record_type",
    "ranking_inclusion_status",
    "ranking_inclusion_reason",
    "evidence_mixture_label",
    "real_evidence_layer_count",
    "demo_or_default_layer_count",
    "proxy_layer_count",
    "missing_layer_count",
    "main_positive_drivers",
    "main_penalties",
    "recommendation",
    "therapeutic_role",
    "preferred_strategy",
    "robustness_label",
    "audit_class",
    "audit_confidence",
]


def _build_top10_scientific_audit(
    phase2_ranking: pd.DataFrame,
    comparison_output: pd.DataFrame,
    sensitivity: pd.DataFrame,
    provenance_summary: pd.DataFrame,
    literature_support: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    ranking_scope = phase2_ranking.copy()
    if "included_in_therapeutic_ranking" in ranking_scope.columns:
        ranking_scope = ranking_scope.loc[ranking_scope["included_in_therapeutic_ranking"].fillna(True).astype(bool)].copy()
    top_candidates = ranking_scope.head(top_n).copy().reset_index().rename(columns={"index": "rank"})
    if top_candidates.empty:
        return pd.DataFrame(columns=TOP10_SCIENTIFIC_AUDIT_COLUMNS)
    comparison_lookup = comparison_output.set_index("protein_id") if not comparison_output.empty else pd.DataFrame()
    provenance_note = " ".join(
        f"{item['dataset']}={item['status']}" for _, item in provenance_summary.iterrows()
    ) if not provenance_summary.empty else "sin resumen de procedencia"
    rows = []
    for _, row in top_candidates.iterrows():
        protein_id = row["protein_id"]
        comparison_row = comparison_lookup.loc[protein_id] if protein_id in comparison_lookup.index else {}
        preferred_strategy = str(row.get("preferred_strategy", "meta_priority"))
        strategy_label = _strategy_label(preferred_strategy, float(row.get("strategy_margin_score", 0.0)))
        positive_driver_names = _parse_driver_names(str(row.get("top_positive_drivers", "")))
        negative_driver_names = _parse_driver_names(str(row.get("top_negative_drivers", "")))
        meta_span, preferred_span = _sensitivity_spans(sensitivity, protein_id, preferred_strategy)
        robustness = _robustness_label(row, meta_span, preferred_span)
        confidence = _audit_confidence(row, meta_span, preferred_span)
        literature_row = _match_literature_support(row, literature_support)

        biological_interpretation = (
            f"{row['gene']} ({protein_id}) asciende sobre todo porque { _driver_biological_text(positive_driver_names, row) }. "
            f"Dentro del modelo actual su lectura dominante es `{strategy_label}`."
        )
        host_risk_interpretation = _host_risk_methodological_text(row)
        theory_v3_assessment_note = explain_theory_v3_assessment_note(row)
        evolutionary_interpretation = row.get("evolutionary_escape_risk_interpretation", "not_reported")
        methodological_risk = (
            f"El principal riesgo interpretativo es que { _negative_biological_text(negative_driver_names) }. "
            f"{host_risk_interpretation} "
            f"Riesgo evolutivo: {evolutionary_interpretation} "
            f"AdemÃ¡s, las capas opcionales quedan resumidas como: {provenance_note}."
        )
        demo_dependency = (
            "Alta dependencia de capas opcionales demo; la seÃ±al adicional de conservaciÃ³n, red y anotaciÃ³n de hospedero no debe leerse como validaciÃ³n biolÃ³gica externa."
            if str(row.get("data_realism_flag")) == "demo_only"
            else "La dependencia de datos demo no parece dominante en este candidato."
        )
        sensitivity_assessment = (
            f"Meta-score con variaciÃ³n mÃ¡xima de {meta_span} puestos; estrategia preferida con variaciÃ³n mÃ¡xima de {preferred_span} puestos."
        )

        rows.append(
            {
                "rank": int(row["rank"]),
                "rank_phase3_real_candidates": row.get("rank_phase3_real_candidates", row["rank"]),
                "protein_id": protein_id,
                "gene": row["gene"],
                "included_in_therapeutic_ranking": row.get("included_in_therapeutic_ranking", True),
                "is_template_or_demo_record": row.get("is_template_or_demo_record", False),
                "template_or_demo_reason": row.get("template_or_demo_reason", "not_demo_or_template"),
                "candidate_record_type": row.get("candidate_record_type", "not_reported"),
                "ranking_inclusion_status": row.get("ranking_inclusion_status", "not_reported"),
                "ranking_inclusion_reason": row.get("ranking_inclusion_reason", "not_reported"),
                "evidence_mixture_label": row.get("evidence_mixture_label", "not_reported"),
                "real_evidence_layer_count": row.get("real_evidence_layer_count", row.get("phase3_real_evidence_layer_count", 0)),
                "demo_or_default_layer_count": row.get("demo_or_default_layer_count", row.get("phase3_demo_default_layer_count", 0)),
                "proxy_layer_count": row.get("proxy_layer_count", row.get("phase3_proxy_layer_count", 0)),
                "missing_layer_count": row.get("missing_layer_count", row.get("phase3_missing_layer_count", 0)),
                "therapeutic_role": row.get("therapeutic_role", "low_priority_candidate"),
                "therapeutic_role_v3": row.get("therapeutic_role_v3", "not_reported"),
                "therapeutic_role_v3_reason": row.get("therapeutic_role_v3_reason", "not_reported"),
                "theory_v3_assessment_note": theory_v3_assessment_note,
                "phase3_evidence_confidence_label": row.get("phase3_evidence_confidence_label", "not_reported"),
                "phase3_recommendation": row.get("phase3_recommendation", "not_reported"),
                "therapeutic_priority_score": row.get("therapeutic_priority_score", 0.0),
                "therapeutic_priority_contribution_summary": row.get(
                    "therapeutic_priority_contribution_summary",
                    "not_reported",
                ),
                "therapeutic_priority_components": row.get(
                    "therapeutic_priority_components",
                    row.get("therapeutic_priority_contribution_summary", "not_reported"),
                ),
                "preferred_strategy": strategy_label,
                "meta_priority_score": row["meta_priority_score"],
                "meta_priority_score_v3": row.get("meta_priority_score_v3", 0.0),
                "functional_node_theory_confidence": row.get("functional_node_theory_confidence", 0.0),
                "functional_node_theory_score": row.get("functional_node_theory_score", 0.0),
                "functional_node_theory_label": row.get("functional_node_theory_label", "not_reported"),
                "evidence_quality_score": row.get("evidence_quality_score", 0.0),
                "confidence_ceiling": row.get("confidence_ceiling", 0.0),
                "antibiotic_target_score": row["antibiotic_target_score"],
                "antivirulence_target_score": row["antivirulence_target_score"],
                "functional_node_score": row["functional_node_score"],
                "evolutionary_escape_risk_score": row.get("evolutionary_escape_risk_score", 0.0),
                "evolutionary_robustness_score": row.get("evolutionary_robustness_score", 0.0),
                "reduced_evolutionary_space_score": row.get("reduced_evolutionary_space_score", 0.0),
                "evolutionary_escape_penalty_applied": row.get("evolutionary_escape_penalty_applied", 0.0),
                "evolutionary_escape_risk_confidence": row.get("evolutionary_escape_risk_confidence", "not_reported"),
                "evolutionary_escape_risk_status": row.get("evolutionary_escape_risk_status", "not_reported"),
                "evolutionary_escape_interpretation": evolutionary_interpretation,
                "phase1_rank": int(comparison_row["legacy_rank"]) if isinstance(comparison_row, pd.Series) else None,
                "phase2_rank": int(comparison_row["phase2_rank"]) if isinstance(comparison_row, pd.Series) else int(row["rank"]),
                "rank_shift_vs_legacy": int(comparison_row["rank_shift_phase2_vs_legacy"]) if isinstance(comparison_row, pd.Series) else 0,
                "robustness_label": robustness,
                "data_realism_flag": row.get("data_realism_flag", "unknown"),
                "optional_data_quality_score": row.get("optional_data_quality_score", 0.0),
                "main_positive_drivers": row.get("top_positive_drivers", ""),
                "main_negative_drivers": row.get("top_negative_drivers", ""),
                "main_penalties": row.get("top_negative_drivers", row.get("phase3_negative_evidence_summary", "")),
                "host_risk_audit_summary": row.get("host_risk_audit_summary", "not_reported"),
                "host_similarity_risk": row.get("host_similarity_risk", 0.0),
                "phase3_real_evidence_layer_count": row.get("phase3_real_evidence_layer_count", 0),
                "phase3_demo_default_layer_count": row.get("phase3_demo_default_layer_count", 0),
                "phase3_missing_layer_count": row.get("phase3_missing_layer_count", 0),
                "phase3_negative_evidence_count": row.get("phase3_negative_evidence_count", 0),
                "phase3_evidence_gap_summary": row.get("phase3_evidence_gap_summary", "not_reported"),
                "phase3_negative_evidence_summary": row.get("phase3_negative_evidence_summary", "not_reported"),
                "phase3_evidence_explanation": row.get("phase3_evidence_explanation", "not_reported"),
                "host_risk_interpretation": host_risk_interpretation,
                "biological_interpretation": biological_interpretation,
                "methodological_risk": methodological_risk,
                "demo_dependency_assessment": demo_dependency,
                "sensitivity_assessment": sensitivity_assessment,
                "literature_support_score": _literature_value(literature_row, "literature_support_score", 0.0),
                "literature_support_status": row.get("literature_support_status", "not_reported"),
                "literature_evidence_type": row.get("literature_evidence_type", _literature_value(literature_row, "evidence_type", "not_loaded")),
                "literature_reference": _literature_value(literature_row, "reference", "not_loaded"),
                "literature_source_quality": row.get("literature_source_quality", _literature_value(literature_row, "source_quality", 0.0)),
                "literature_interpretation": _candidate_literature_note(row, literature_support),
                "recommended_next_evidence": _recommended_next_evidence(strategy_label, row),
                "recommendation": row.get("phase3_recommendation", _recommended_next_evidence(strategy_label, row)),
                "audit_class": robustness,
                "audit_confidence": confidence,
            }
        )
    return pd.DataFrame(rows)


def _build_top10_scientific_markdown(
    scientific_audit: pd.DataFrame,
    provenance_summary: pd.DataFrame,
    all_candidates: pd.DataFrame | None = None,
) -> str:
    lines = [
        "# AuditorÃ­a CientÃ­fica Estricta del Top 10",
        "",
        "## Resumen Ejecutivo",
    ]
    if scientific_audit.empty:
        lines.extend(_empty_top10_scientific_lines(all_candidates))
        return "\n".join(lines)

    strategy_counts = scientific_audit["preferred_strategy"].value_counts().to_dict()
    class_counts = scientific_audit["audit_class"].value_counts().to_dict()
    lines.extend(
        [
            f"- Candidatos auditados: {len(scientific_audit)}",
            f"- Estrategias dominantes: {strategy_counts}",
            f"- Clases de auditorÃ­a: {class_counts}",
            "",
            "## Criterios de InterpretaciÃ³n y Limitaciones",
            "- Esta lectura usa solo outputs internos del proyecto y no incorpora literatura ni bases externas.",
            "- Un score alto no equivale a validaciÃ³n biolÃ³gica definitiva.",
            "- `therapeutic_priority_components` descompone la prioridad terapeutica calculada por el modelo; no es validacion experimental.",
            "- Este reporte no constituye recomendacion terapeutica ni sustituye evaluacion medica, microbiologica o farmacologica.",
            "- Toda aplicacion requiere validacion experimental y clinica externa.",
            "- Sus componentes pueden depender de evidencia real, curada, cache, proxy, demo o faltante, segun la procedencia registrada.",
            "- Las capas opcionales pueden mezclar datos demo, datos de usuario, cache local y proveedores controlados; revisar siempre la tabla de procedencia.",
            "- Las variables de impacto clÃ­nico y daÃ±o al hospedero pueden venir de capas materializadas semicuradas o de proxies internos, segÃºn la procedencia registrada.",
            "",
        ]
    )
    if not provenance_summary.empty:
        lines.extend(["## Procedencia Opcional", "", _markdown_table(provenance_summary), ""])

    for _, row in scientific_audit.iterrows():
        theory_v3_note = str(row.get("theory_v3_assessment_note", "not_reported"))
        lines.extend(
            [
                f"## {int(row['rank'])}. {row['gene']} ({row['protein_id']})",
                f"- Rol terapÃ©utico: `{row['therapeutic_role']}` con prioridad `{row['therapeutic_priority_score']:.4f}`",
                f"- Descomposicion de prioridad terapeutica: {row.get('therapeutic_priority_components', 'not_reported')}",
                f"- Fase 3: rank real `{row.get('rank_phase3_real_candidates', 'not_reported')}`, meta_priority_score_v3 `{float(row.get('meta_priority_score_v3', 0.0)):.4f}`, rol `{row.get('therapeutic_role_v3', 'not_reported')}`",
                f"- Evidencia Fase 3: calidad `{_fmt_optional_score(row.get('evidence_quality_score', 0.0))}`, techo `{_fmt_optional_score(row.get('confidence_ceiling', 0.0))}`, teoria `{_fmt_optional_score(row.get('functional_node_theory_score', 0.0))}`, escape `{_fmt_optional_score(row.get('evolutionary_escape_risk_score', 0.0))}`, similitud hospedero `{_fmt_optional_score(row.get('host_similarity_risk', 0.0))}`",
                *(
                    [f"- Nota theory-first/v3: {theory_v3_note}"]
                    if theory_v3_note != "not_reported"
                    else []
                ),
                f"- Estrategia preferida: `{row['preferred_strategy']}`",
                f"- Juicio final: `{row['audit_class']}` con confianza `{row['audit_confidence']}`",
                f"- InterpretaciÃ³n biolÃ³gica: {row['biological_interpretation']}",
                f"- Fortalezas dentro del modelo: {row['main_positive_drivers']}",
                f"- Riesgos o limitaciones: {row['methodological_risk']}",
                f"- Soporte bibliografico curado: estado `{row.get('literature_support_status', 'not_reported')}`, score `{float(row.get('literature_support_score', 0.0)):.4f}`, calidad `{float(row.get('literature_source_quality', 0.0)):.4f}`",
                f"- Explicacion de score bajo/priorizacion: {row.get('phase3_evidence_explanation', 'not_reported')}",
                f"- Dependencia de demo/proxy: {row['demo_dependency_assessment']}",
                f"- Sensibilidad: {row['sensitivity_assessment']}",
                f"- Evidencia faltante prioritaria: {row['recommended_next_evidence']}",
                "",
            ]
        )

    lines.extend(
        [
            "## ConclusiÃ³n General",
            "- El top 10 mezcla perfiles antibiÃ³ticos clÃ¡sicos con perfiles antivirulencia y algunos candidatos mÃ¡s dependientes de la capa funcional.",
            "- La ordenaciÃ³n gruesa parece Ãºtil como priorizaciÃ³n interna, pero no debe sobrerinterpretarse sin revisar procedencia y sensibilidad.",
            "- La debilidad metodolÃ³gica dominante del ranking actual estÃ¡ en la procedencia de conservaciÃ³n, red funcional y anotaciÃ³n del hospedero.",
            "- El dato adicional con mayor potencial para reordenar el top 10 serÃ­a incorporar evidencia curada externa o de usuario para contexto clÃ­nico, sitio de infecciÃ³n y conservaciÃ³n multicepa.",
        ]
    )
    return "\n".join(lines)


def _build_top10_scientific_summary(scientific_audit: pd.DataFrame) -> str:
    if scientific_audit.empty:
        return "# Resumen cientÃ­fico Top 10\n\nNo fue posible generar un resumen completo."
    top_line = scientific_audit.iloc[0]
    unstable = scientific_audit.loc[scientific_audit["audit_class"].isin(["strategy_dependent", "borderline"])]
    return "\n".join(
        [
            "# Resumen CientÃ­fico del Top 10",
            "",
            f"- El candidato lÃ­der actual es `{top_line['gene']}` (`{top_line['protein_id']}`), con rol terapÃ©utico `{top_line['therapeutic_role']}` y estrategia preferida `{top_line['preferred_strategy']}`.",
            f"- {len(unstable)} de los 10 candidatos muestran fragilidad relevante por sensibilidad estratÃ©gica o por soporte demo.",
            "- NingÃºn candidato debe considerarse validado biolÃ³gicamente solo con estos outputs internos.",
        ]
    )


def _empty_top10_scientific_lines(all_candidates: pd.DataFrame | None) -> list[str]:
    excluded = 0
    reasons = {}
    if all_candidates is not None and not all_candidates.empty:
        included = all_candidates.get(
            "included_in_therapeutic_ranking",
            pd.Series([False] * len(all_candidates), index=all_candidates.index),
        ).fillna(False).astype(bool)
        excluded = int((~included).sum())
        if "ranking_inclusion_status" in all_candidates.columns:
            reasons = all_candidates.loc[~included, "ranking_inclusion_status"].fillna("not_reported").value_counts().to_dict()
    return [
        "- No hay candidatos reales incluidos en el ranking terapeutico principal.",
        f"- Registros excluidos: {excluded}",
        f"- Motivos de exclusion: {reasons if reasons else 'no_reported'}",
        "- Revisa `results/template_or_demo_records.csv` para ver plantillas/demo excluidas.",
        "- Revisa `results/ranking_nodos_phase3.csv` y la columna `ranking_inclusion_status` para cada registro.",
        "- Revisa `results/layer_evidence_summary.csv`, `results/provenance_user_summary.md` y `results/organism_profile_validation.md` para saber que datos faltan.",
        "- Para habilitar candidatos reales, reemplaza demo/default/proxy con capas reales en `data_user/` o fuentes externas trazables.",
    ]


def _scientific_audit_report_view(scientific_audit: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "rank",
        "protein_id",
        "therapeutic_role",
        "preferred_strategy",
        "robustness_label",
        "audit_class",
        "audit_confidence",
        "therapeutic_priority_components",
        "theory_v3_assessment_note",
    ]
    if scientific_audit.empty:
        return pd.DataFrame(columns=columns)
    return scientific_audit[[column for column in columns if column in scientific_audit.columns]].copy()


def _load_literature_support(processed_dir: Path) -> pd.DataFrame:
    path = processed_dir / "normalized_literature_support.csv"
    if not path.exists():
        return pd.DataFrame()
    try:
        literature = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    if "protein_id" not in literature.columns:
        return pd.DataFrame()
    return literature


def _normalized_text(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none"}:
        return ""
    return text.upper()


def _match_literature_support(candidate: pd.Series, literature_support: pd.DataFrame) -> pd.Series | None:
    if literature_support.empty:
        return None
    candidate_ids = {
        _normalized_text(candidate.get("protein_id")),
        _normalized_text(candidate.get("protein_id_canonical")),
        _normalized_text(candidate.get("protein_id_original")),
    }
    candidate_ids.discard("")
    candidate_gene = _normalized_text(candidate.get("gene"))
    for _, literature_row in literature_support.iterrows():
        literature_ids = {
            _normalized_text(literature_row.get("protein_id")),
            _normalized_text(literature_row.get("protein_id_canonical")),
            _normalized_text(literature_row.get("protein_id_original")),
            _normalized_text(literature_row.get("gene_id")),
        }
        literature_ids.discard("")
        literature_gene = _normalized_text(literature_row.get("gene"))
        if candidate_ids & literature_ids:
            return literature_row
        if candidate_gene and literature_gene and candidate_gene == literature_gene:
            return literature_row
    return None


def _literature_value(literature_row: pd.Series | None, column: str, default: object) -> object:
    if literature_row is None or column not in literature_row.index:
        return default
    value = literature_row.get(column)
    if pd.isna(value):
        return default
    return value


def _candidate_literature_note(candidate: pd.Series, literature_support: pd.DataFrame) -> str:
    literature_row = _match_literature_support(candidate, literature_support)
    if literature_support.empty:
        return "sin archivo literature_support cargado; no afecta el ranking"
    if literature_row is None:
        return "sin soporte bibliografico curado para este candidato; no afecta el ranking"
    score = float(_literature_value(literature_row, "literature_support_score", 0.0))
    evidence_type = str(_literature_value(literature_row, "evidence_type", "not_specified"))
    reference = str(_literature_value(literature_row, "reference", "not_specified"))
    source_quality = float(_literature_value(literature_row, "source_quality", 0.0))
    if reference in {"TO_BE_CURATED", "pending_manual_curation"} or evidence_type == "pending_manual_curation":
        return f"soporte pendiente de curacion manual (score={score:.2f}, calidad={source_quality:.2f}); no afecta el ranking"
    return f"soporte interpretativo `{evidence_type}` (score={score:.2f}, calidad={source_quality:.2f}, referencia={reference}); no afecta el ranking"


def _build_literature_support_summary(
    phase2_ranking: pd.DataFrame,
    literature_support: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    rows = []
    for rank, (_, candidate) in enumerate(phase2_ranking.head(top_n).iterrows(), start=1):
        literature_row = _match_literature_support(candidate, literature_support)
        status = "not_loaded" if literature_support.empty else "matched" if literature_row is not None else "not_matched"
        rows.append(
            {
                "rank": rank,
                "protein_id": candidate.get("protein_id", ""),
                "gene": candidate.get("gene", ""),
                "literature_status": status,
                "literature_support_score": _literature_value(literature_row, "literature_support_score", 0.0),
                "evidence_type": _literature_value(literature_row, "evidence_type", "not_loaded"),
                "reference": _literature_value(literature_row, "reference", "not_loaded"),
                "doi_or_url": _literature_value(literature_row, "doi_or_url", ""),
                "source_quality": _literature_value(literature_row, "source_quality", 0.0),
                "interpretive_note": _candidate_literature_note(candidate, literature_support),
            }
        )
    return pd.DataFrame(rows)


def _evidence_strength_flags(row: pd.Series) -> tuple[list[str], list[str]]:
    strong_flags: list[str] = []
    weak_flags: list[str] = []
    if any(bool(row.get(f"{layer}_is_user_supplied", False)) for layer in TARGET_LAYER_KEYS):
        strong_flags.append("user_curated_layer_present")
    if any(bool(row.get(f"{layer}_is_external", False)) for layer in TARGET_LAYER_KEYS):
        strong_flags.append("external_real_or_materialized_layer_present")
    if float(row.get("evidence_coverage_score", 0.0)) >= 0.90:
        strong_flags.append("high_layer_coverage")
    if float(row.get("evidence_confidence_score", 0.0)) >= 0.80:
        strong_flags.append("high_evidence_confidence")
    if str(row.get("data_realism_flag", "unknown")) == "demo_only":
        weak_flags.append("demo_dependency")
    if int(row.get("proxy_feature_count", 0)) > 0:
        weak_flags.append("proxy_features_present")
    if float(row.get("evidence_coverage_score", 0.0)) < 0.60:
        weak_flags.append("low_layer_coverage")
    if float(row.get("evidence_confidence_score", 0.0)) < 0.50:
        weak_flags.append("low_evidence_confidence")
    if "proxy" in str(row.get("therapeutic_context_missingness", "")):
        weak_flags.append("therapeutic_context_proxy")
    return strong_flags, weak_flags


def _classify_evidence_strength(row: pd.Series) -> tuple[str, str, str, str, str]:
    strong_flags, weak_flags = _evidence_strength_flags(row)
    coverage = float(row.get("evidence_coverage_score", 0.0))
    confidence = float(row.get("evidence_confidence_score", 0.0))
    quality = float(row.get("optional_data_quality_score", 0.0))
    proxy_count = int(row.get("proxy_feature_count", 0))
    realism = str(row.get("data_realism_flag", "unknown"))

    if coverage < 0.40 or confidence < 0.35:
        strength = "insufficient"
        reason = "Cobertura o confianza insuficiente para interpretar el candidato con seguridad metodologica."
    elif realism == "demo_only" and proxy_count >= 3:
        strength = "weak"
        reason = "La evidencia depende de datos demo y varias senales proxy; el score debe leerse como hipotesis preliminar."
    elif proxy_count >= 3 or quality < 0.60 or len(weak_flags) >= 3:
        strength = "weak"
        reason = "La evidencia tiene dependencia relevante de proxy, demo o capas de baja calidad."
    elif coverage >= 0.90 and confidence >= 0.75 and proxy_count == 0 and ("user_curated_layer_present" in strong_flags or "external_real_or_materialized_layer_present" in strong_flags):
        strength = "strong"
        reason = "Buena cobertura, confianza alta y soporte trazable sin dependencia principal de proxy."
    else:
        strength = "moderate"
        reason = "La evidencia combina senales utiles con limitaciones de procedencia, cobertura o especificidad."

    coverage_summary = (
        f"coverage={coverage:.2f}; confidence={confidence:.2f}; "
        f"source_quality={quality:.2f}; proxy_count={proxy_count}; realism={realism}"
    )
    return (
        strength,
        reason,
        coverage_summary,
        "; ".join(weak_flags) if weak_flags else "none",
        "; ".join(strong_flags) if strong_flags else "none",
    )


def _build_evidence_strength_audit(phase2_ranking: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rank, (_, row) in enumerate(phase2_ranking.iterrows(), start=1):
        strength, reason, coverage_summary, weak_flags, strong_flags = _classify_evidence_strength(row)
        rows.append(
            {
                "rank": rank,
                "protein_id": row.get("protein_id", ""),
                "gene": row.get("gene", ""),
                "therapeutic_role": row.get("therapeutic_role", ""),
                "meta_priority_score": row.get("meta_priority_score", 0.0),
                "therapeutic_priority_score": row.get("therapeutic_priority_score", 0.0),
                "evidence_strength": strength,
                "evidence_strength_reason": reason,
                "evidence_coverage_summary": coverage_summary,
                "weak_evidence_flags": weak_flags,
                "strong_evidence_flags": strong_flags,
                "data_realism_flag": row.get("data_realism_flag", "unknown"),
                "optional_data_source_summary": row.get("optional_data_source_summary", "none"),
                "therapeutic_context_missingness": row.get("therapeutic_context_missingness", "none"),
            }
        )
    return pd.DataFrame(rows)


def _plain_missingness(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none"}:
        return "no registrada"
    if text == "none":
        return "sin faltantes marcados"
    return text.replace("_", " ")


def _source_warning(row: pd.Series) -> str:
    realism = str(row.get("data_realism_flag", "unknown"))
    missingness = str(row.get("therapeutic_context_missingness", "none"))
    source_summary = str(row.get("optional_data_source_summary", "none"))
    warnings = []
    if realism == "demo_only":
        warnings.append("usa capas demo")
    if "proxy" in missingness:
        warnings.append("incluye valores proxy")
    if "cache" in source_summary:
        warnings.append("incluye datos de cache")
    if "computed" in source_summary:
        warnings.append("incluye calculos indirectos")
    return "; ".join(warnings) if warnings else "sin advertencia dominante de procedencia"


def _build_executive_summary(
    phase2_ranking: pd.DataFrame,
    top_n: int,
    literature_support: pd.DataFrame,
    metadata: dict | None = None,
) -> str:
    metadata = metadata or {}
    lines = [
        "# Resumen Ejecutivo",
        "",
        "Este documento resume una priorizacion computacional exploratoria de blancos bacterianos. "
        "El score no confirma eficacia terapeutica, no reemplaza curacion bibliografica y requiere validacion experimental y clinica externa.",
        "",
        "## Interpretacion general",
        "",
        "- Un ranking alto indica prioridad relativa dentro de las capas cargadas, no validacion biologica definitiva.",
        "- No constituye recomendacion terapeutica ni sustituye evaluacion medica, microbiologica o farmacologica.",
        "- Los scores deben interpretarse como evidencia de soporte, no como confirmacion definitiva.",
        "- Los datos demo, proxy, cache o calculados indirectamente deben usarse solo para probar el flujo o generar hipotesis.",
        "- Antes de tomar decisiones experimentales, revisar procedencia, evidencia faltante, seguridad frente al hospedero y contexto de infeccion.",
        "",
        *_metadata_lines(metadata),
        "## Top 10 blancos priorizados",
        "",
    ]
    if phase2_ranking.empty:
        lines.append("_No hay candidatos disponibles con los filtros actuales._")
        return "\n".join(lines)

    for rank, (_, row) in enumerate(phase2_ranking.head(top_n).iterrows(), start=1):
        main_driver = str(row.get("top_positive_drivers", "no registrado")).split(";")[0].strip()
        evidence = str(row.get("confidence_summary", "sin resumen de confianza"))
        missing = _plain_missingness(row.get("therapeutic_context_missingness", row.get("missing_evidence_flags", "")))
        literature_note = _candidate_literature_note(row, literature_support)
        lines.extend(
            [
                f"### {rank}. {row.get('gene', 'unknown')} ({row.get('protein_id', 'unknown')})",
                f"- Rol sugerido: `{row.get('therapeutic_role', 'no clasificado')}`.",
                f"- Prioridad terapeutica: `{float(row.get('therapeutic_priority_score', 0.0)):.4f}`.",
                f"- Razon principal del ranking: {main_driver}.",
                f"- Evidencia disponible: {evidence}.",
                f"- Soporte bibliografico: {literature_note}.",
                f"- Evidencia faltante o incompleta: {missing}.",
                f"- Advertencia de procedencia: {_source_warning(row)}.",
                "- Siguiente validacion sugerida: evaluar experimentalmente esencialidad, accesibilidad, selectividad frente al hospedero y relevancia en el sitio de infeccion.",
                "",
            ]
        )

    lines.extend(
        [
            "## Siguiente validacion experimental sugerida",
            "",
            "Priorizar ensayos que separen tres preguntas: si el blanco es necesario para la bacteria, "
            "si una intervencion puede alcanzarlo en el contexto de infeccion y si el efecto observado no se explica por toxicidad o artefactos. "
            "Para candidatos antivirulencia, medir reduccion de dano al hospedero ademas de crecimiento bacteriano.",
        ]
    )
    return "\n".join(lines)


def export_results(base_dir: Path, config: dict, mode: str = "compare") -> None:
    processed_dir = base_dir / "data_processed"
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(processed_dir / "phase2_features.csv")
    workspace_metadata = _load_workspace_metadata(base_dir)
    literature_support = _load_literature_support(processed_dir)
    sensitivity = pd.read_csv(results_dir / "sensitivity_analysis.csv") if (results_dir / "sensitivity_analysis.csv").exists() else pd.DataFrame()
    provenance_summary = _build_provenance_summary(features)
    layer_resolution_summary = _build_layer_resolution_summary(features)
    therapeutic_role_summary = _build_therapeutic_role_summary(features)
    therapeutic_rule_summary = _build_therapeutic_rule_summary(features)
    human_homologs_audit = _build_human_homologs_audit(features)
    therapeutic_context_separation_audit = _build_therapeutic_context_separation_audit(base_dir, features)
    controlled_replacement_readiness = _build_controlled_replacement_readiness(features)
    evolutionary_escape_risk_audit = _build_evolutionary_escape_risk_audit(features)

    min_score = float(config["thresholds"]["min_score"])
    top_n = int(config["thresholds"]["top_n"])

    phase2_ranking = (
        features.loc[features["meta_priority_score"] >= min_score]
        .sort_values("meta_priority_score", ascending=False)
        .reset_index(drop=True)
    )
    phase2_ranking.index = range(1, len(phase2_ranking) + 1)
    phase2_ranking.index.name = "rank"
    if mode == "phase3":
        phase3_path = processed_dir / "phase3_features.csv"
        if phase3_path.exists():
            phase3_features = pd.read_csv(phase3_path)
            phase3_columns = [
                "protein_id",
                "meta_priority_score_v2",
                "meta_priority_score_v3",
                "rank_phase3_real_candidates",
                "rank_phase3_all_records",
                "included_in_therapeutic_ranking",
                "candidate_record_type",
                "is_template_or_demo_record",
                "template_or_demo_reason",
                "ranking_inclusion_status",
                "ranking_inclusion_reason",
                "evidence_mixture_label",
                "real_evidence_layer_count",
                "demo_or_default_layer_count",
                "proxy_layer_count",
                "missing_layer_count",
                "negative_evidence_layer_count",
                "therapeutic_role_v3",
                "therapeutic_role_v3_reason",
                "phase3_evidence_confidence_label",
                "phase3_recommendation",
                "functional_node_theory_score",
                "functional_node_theory_confidence",
                "functional_node_theory_label",
                "evidence_quality_score",
                "confidence_ceiling",
                "host_similarity_risk",
                "literature_support_score",
                "literature_support_status",
                "literature_source_quality",
                "literature_has_curated_evidence",
                "phase3_real_evidence_layer_count",
                "phase3_proxy_layer_count",
                "phase3_demo_default_layer_count",
                "phase3_missing_layer_count",
                "phase3_negative_evidence_count",
                "phase3_evidence_gap_summary",
                "phase3_negative_evidence_summary",
                "phase3_evidence_explanation",
            ]
            phase3_subset = phase3_features[[column for column in phase3_columns if column in phase3_features.columns]].drop_duplicates(
                subset="protein_id",
                keep="first",
            )
            phase3_conflicts = [column for column in phase3_subset.columns if column != "protein_id" and column in phase2_ranking.columns]
            if phase3_conflicts:
                phase2_ranking = phase2_ranking.drop(columns=phase3_conflicts)
            phase2_ranking = phase2_ranking.merge(phase3_subset, on="protein_id", how="left")
            if "included_in_therapeutic_ranking" in phase2_ranking.columns:
                phase2_ranking["included_in_therapeutic_ranking"] = phase2_ranking["included_in_therapeutic_ranking"].fillna(True).astype(bool)
                for column in ["meta_priority_score_v3", "evidence_quality_score", "functional_node_theory_score", "meta_priority_score_v2"]:
                    if column in phase2_ranking.columns:
                        phase2_ranking[column] = pd.to_numeric(phase2_ranking[column], errors="coerce").fillna(0.0)
                sort_columns = [
                    column
                    for column in [
                        "included_in_therapeutic_ranking",
                        "meta_priority_score_v3",
                        "evidence_quality_score",
                        "functional_node_theory_score",
                        "confidence_ceiling",
                        "meta_priority_score_v2",
                    ]
                    if column in phase2_ranking.columns
                ]
                phase2_ranking = phase2_ranking.sort_values(
                    sort_columns,
                    ascending=[False] * len(sort_columns),
                    kind="mergesort",
                ).reset_index(drop=True)
            phase2_ranking.index = range(1, len(phase2_ranking) + 1)
            phase2_ranking.index.name = "rank"
    clinical_impact_curation_queue = _build_clinical_impact_curation_queue(phase2_ranking, top_n)
    disease_context_curation_queue = _build_disease_context_curation_queue(phase2_ranking, top_n)
    therapy_site_context_curation_queue = _build_therapy_site_context_curation_queue(phase2_ranking, top_n)
    therapeutic_role_stability_audit = _build_therapeutic_role_stability_audit(phase2_ranking)
    therapeutic_role_stability_summary = _build_therapeutic_role_stability_summary(therapeutic_role_stability_audit)

    phase2_columns = [
        "candidate_id",
        "protein_id",
        "gene",
        "product",
        "organism",
        "strain",
        "legacy_score_final",
        "antibiotic_target_score",
        "antivirulence_target_score",
        "functional_node_score",
        "selectivity_score",
        "evolutionary_robustness_score",
        "clinical_context_score",
        "confidence_modifier",
        "meta_priority_score",
        "meta_priority_score_v2",
        "meta_priority_score_v3",
        "rank_phase3_real_candidates",
        "rank_phase3_all_records",
        "included_in_therapeutic_ranking",
        "candidate_record_type",
        "is_template_or_demo_record",
        "template_or_demo_reason",
        "ranking_inclusion_status",
        "ranking_inclusion_reason",
        "evidence_mixture_label",
        "real_evidence_layer_count",
        "demo_or_default_layer_count",
        "proxy_layer_count",
        "missing_layer_count",
        "negative_evidence_layer_count",
        "therapeutic_role_v3",
        "therapeutic_role_v3_reason",
        "functional_node_theory_score",
        "functional_node_theory_confidence",
        "functional_node_theory_label",
        "evidence_quality_score",
        "confidence_ceiling",
        "phase3_real_evidence_layer_count",
        "phase3_proxy_layer_count",
        "phase3_demo_default_layer_count",
        "phase3_missing_layer_count",
        "phase3_negative_evidence_count",
        "phase3_evidence_explanation",
        "literature_support_score",
        "literature_support_status",
        "literature_source_quality",
        "evolutionary_adjusted_meta_priority_score",
        "evolutionary_escape_penalty_applied",
        "evolutionary_escape_risk_score",
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "mutation_tolerance",
        "pathway_redundancy",
        "paralog_count",
        "mobile_context",
        "hgt_context",
        "recombination_context",
        "resistance_association",
        "evolutionary_robustness_score",
        "reduced_evolutionary_space_score",
        "evolutionary_escape_risk_confidence",
        "evolutionary_escape_risk_status",
        "therapeutic_priority_score",
        *THERAPEUTIC_PRIORITY_CONTRIBUTION_COLUMNS,
        "functional_node_types",
        "therapeutic_role",
        "therapeutic_role_with_controlled_provider",
        "therapeutic_role_without_controlled_provider",
        "therapeutic_role_stability",
        "therapeutic_role_rule",
        "host_damage_score",
        "host_direct_damage_score",
        "virulence_associated_severity_score",
        "infection_site_access_score",
        "infection_context_score",
        "evidence_confidence_score",
        "evidence_coverage_score",
        "confidence_source_class",
        "confidence_evidence_tier",
        "therapeutic_context_missingness",
        "top_positive_drivers",
        "top_negative_drivers",
        "missing_evidence_flags",
        "confidence_summary",
        "evidence_level",
        "evidence_source",
        "provenance_status",
        "retrieval_mode",
        "cache_status",
        "source_version",
        "updated_at",
        "interpretation_warning",
    ]
    phase2_columns = list(dict.fromkeys(phase2_columns))
    phase2_output = phase2_ranking[[column for column in phase2_columns if column in phase2_ranking.columns]]

    legacy_ranking = features.sort_values("legacy_score_final", ascending=False).reset_index(drop=True)
    legacy_ranking.index = range(1, len(legacy_ranking) + 1)
    legacy_ranking.index.name = "rank"
    legacy_output = legacy_ranking[["protein_id", "gene", "legacy_score_final"]]

    if mode == "legacy":
        legacy_output.to_csv(results_dir / "ranking_nodos.csv")
    else:
        phase2_output.to_csv(results_dir / "ranking_nodos.csv")
    _, ranking_snapshot_comparison_path = write_ranking_snapshot_outputs(results_dir, phase2_ranking)
    simple_explanations = build_simple_candidate_explanations(phase2_ranking, top_n)
    simple_explanations.to_csv(results_dir / "candidate_explanations_simple.csv", index=False)
    (results_dir / "candidate_explanations_simple.md").write_text(
        build_simple_candidate_explanations_markdown(simple_explanations),
        encoding="utf-8",
    )
    (results_dir / "resumen_ejecutivo.md").write_text(
        _build_executive_summary(phase2_ranking, top_n, literature_support, workspace_metadata),
        encoding="utf-8",
    )
    literature_summary = _build_literature_support_summary(phase2_ranking, literature_support, top_n)
    literature_summary.to_csv(results_dir / "literature_support_summary.csv", index=False)
    (results_dir / "literature_support_summary.md").write_text(
        "\n".join(
            [
                "# Literature Support Summary",
                "",
                "La evidencia bibliografica se reporta como soporte interpretativo. No modifica scores ni ranking.",
                "",
                _markdown_table(literature_summary),
            ]
        ),
        encoding="utf-8",
    )
    evidence_strength_audit = _build_evidence_strength_audit(phase2_ranking)
    evidence_strength_audit.to_csv(results_dir / "evidence_strength_audit.csv", index=False)
    (results_dir / "evidence_strength_audit.md").write_text(
        "\n".join(
            [
                "# Evidence Strength Audit",
                "",
                "Este reporte clasifica la fuerza interpretativa de la evidencia sin modificar scores ni ranking.",
                "",
                _markdown_table(evidence_strength_audit.head(top_n)),
            ]
        ),
        encoding="utf-8",
    )

    legacy_output.to_csv(results_dir / "ranking_nodos_legacy.csv")

    comparison = phase2_output.reset_index().merge(
        legacy_output.reset_index().rename(columns={"rank": "legacy_rank"}),
        on="protein_id",
        how="left",
        suffixes=("", "_legacy"),
    )
    comparison["phase2_rank"] = comparison["rank"]
    comparison["rank_shift_phase2_vs_legacy"] = comparison["legacy_rank"] - comparison["phase2_rank"]
    comparison_output = comparison[
        [
            "protein_id",
            "gene",
            "phase2_rank",
            "legacy_rank",
            "rank_shift_phase2_vs_legacy",
            "meta_priority_score",
            "legacy_score_final",
            "top_positive_drivers",
            "top_negative_drivers",
            "missing_evidence_flags",
        ]
    ].copy()
    comparison_output.to_csv(results_dir / "phase_comparison.csv", index=False)
    provenance_summary.to_csv(results_dir / "data_provenance_summary.csv", index=False)
    layer_resolution_summary.to_csv(results_dir / "layer_resolution_summary.csv", index=False)
    write_provenance_user_summary(base_dir, features, layer_resolution_summary)
    write_organism_profile_validation(base_dir, features)
    (results_dir / "layer_resolution_summary.md").write_text(
        "\n".join(["# Layer Resolution Summary", "", _markdown_table(layer_resolution_summary)]),
        encoding="utf-8",
    )
    therapeutic_role_summary.to_csv(results_dir / "therapeutic_role_summary.csv", index=False)
    (results_dir / "therapeutic_role_summary.md").write_text(
        "\n".join(["# Therapeutic Role Summary", "", _markdown_table(therapeutic_role_summary)]),
        encoding="utf-8",
    )
    therapeutic_rule_summary.to_csv(results_dir / "therapeutic_rule_summary.csv", index=False)
    (results_dir / "therapeutic_rule_summary.md").write_text(
        "\n".join(["# Therapeutic Rule Summary", "", _markdown_table(therapeutic_rule_summary)]),
        encoding="utf-8",
    )
    human_homologs_audit.to_csv(results_dir / "human_homologs_audit.csv", index=False)
    (results_dir / "human_homologs_audit.md").write_text(
        "\n".join(
            [
                "# Human Homologs Audit",
                "",
                "Este reporte separa evidencia real de UniProt, resultados inconclusos y backfill configurable. No modifica el ranking.",
                "",
                _markdown_table(human_homologs_audit),
            ]
        ),
        encoding="utf-8",
    )
    therapeutic_context_separation_audit.to_csv(results_dir / "therapeutic_context_separation_audit.csv", index=False)
    (results_dir / "therapeutic_context_separation_audit.md").write_text(
        "\n".join(
            [
                "# Therapeutic Context Separation Audit",
                "",
                "Este reporte verifica si las tres capas terapeuticas controladas v2 se comportan como senales separadas. No modifica scores ni ranking.",
                "",
                _markdown_table(therapeutic_context_separation_audit),
            ]
        ),
        encoding="utf-8",
    )
    controlled_replacement_readiness.to_csv(results_dir / "controlled_replacement_readiness.csv", index=False)
    (results_dir / "controlled_replacement_readiness.md").write_text(
        "\n".join(
            [
                "# Controlled Replacement Readiness",
                "",
                "Este reporte indica que capas controladas pueden reemplazarse primero con datos curados por usuario sin cambiar la arquitectura.",
                "",
                _markdown_table(controlled_replacement_readiness),
            ]
        ),
        encoding="utf-8",
    )
    evolutionary_escape_risk_audit.to_csv(results_dir / "evolutionary_escape_risk_audit.csv", index=False)
    (results_dir / "evolutionary_escape_risk_audit.md").write_text(
        "\n".join(
            [
                "# Evolutionary Escape Risk Audit",
                "",
                "Este reporte muestra variables disponibles, faltantes, procedencia, confianza y penalizacion evolutiva aplicada. Los proxies o demos no equivalen a evidencia fuerte.",
                "",
                _markdown_table(evolutionary_escape_risk_audit.head(top_n)),
            ]
        ),
        encoding="utf-8",
    )
    clinical_impact_curation_queue.to_csv(results_dir / "clinical_impact_curation_queue.csv", index=False)
    (results_dir / "clinical_impact_curation_queue.md").write_text(
        "\n".join(
            [
                "# Clinical Impact Curation Queue",
                "",
                "Esta tabla prepara campos vacios para curar dano directo al hospedero y severidad asociada a virulencia. No inventa evidencia y no modifica scores ni ranking.",
                "",
                _markdown_table(clinical_impact_curation_queue),
            ]
        ),
        encoding="utf-8",
    )
    disease_context_curation_queue.to_csv(results_dir / "disease_context_curation_queue.csv", index=False)
    (results_dir / "disease_context_curation_queue.md").write_text(
        "\n".join(
            [
                "# Disease Context Curation Queue",
                "",
                "Esta tabla prepara campos vacios para curar relevancia durante infeccion, enfermedad o estadio. No inventa evidencia y no modifica scores ni ranking.",
                "",
                _markdown_table(disease_context_curation_queue),
            ]
        ),
        encoding="utf-8",
    )
    therapy_site_context_curation_queue.to_csv(results_dir / "therapy_site_context_curation_queue.csv", index=False)
    (results_dir / "therapy_site_context_curation_queue.md").write_text(
        "\n".join(
            [
                "# Therapy Site Context Curation Queue",
                "",
                "Esta tabla prepara campos vacios para curacion manual. No inventa evidencia y no modifica scores ni ranking.",
                "",
                _markdown_table(therapy_site_context_curation_queue),
            ]
        ),
        encoding="utf-8",
    )
    therapeutic_role_stability_audit.to_csv(results_dir / "therapeutic_role_controlled_stability.csv", index=False)
    therapeutic_role_stability_summary.to_csv(results_dir / "therapeutic_role_controlled_stability_summary.csv", index=False)
    (results_dir / "therapeutic_role_controlled_stability.md").write_text(
        "\n".join(
            [
                "# Therapeutic Role Controlled Stability",
                "",
                "Este reporte compara el rol terapeutico con el proveedor controlado activo frente a un escenario conservador donde esas capas vuelven a proxies locales.",
                "La columna `therapeutic_role_stability_explanation` distingue estabilidad por baja diferencia numerica, estabilidad por estar lejos de umbrales y estabilidad que aun merece revision por sensibilidad de scores.",
                "Las columnas `*_input_status` indican si cada capa terapeutica aporto valores, quedo vacia/no normalizada o solo uso proxy.",
                "",
                "## Summary",
                "",
                _markdown_table(therapeutic_role_stability_summary),
                "",
                "## Candidate Detail",
                "",
                _markdown_table(therapeutic_role_stability_audit.head(top_n)),
            ]
        ),
        encoding="utf-8",
    )

    candidate_audit_columns = [
            "candidate_id",
            "protein_id",
            "gene",
            "product",
            "organism",
            "strain",
            "meta_priority_score",
            "legacy_score_final",
            "antibiotic_target_score",
            "antivirulence_target_score",
            "functional_node_score",
            "selectivity_score",
            "clinical_context_score",
            "confidence_modifier",
            "functional_node_types",
            "host_damage_score",
            "infection_site_access_score",
            "infection_context_score",
            "evolutionary_escape_risk_score",
            "evolutionary_escape_risk",
            "evolutionary_constraint",
            "mutation_tolerance",
            "pathway_redundancy",
            "paralog_count",
            "mobile_context",
            "hgt_context",
            "recombination_context",
            "resistance_association",
            "evolutionary_robustness_score",
            "reduced_evolutionary_space_score",
            "evolutionary_escape_penalty_applied",
            "evolutionary_adjusted_meta_priority_score",
            "evolutionary_escape_risk_confidence",
            "evolutionary_escape_risk_status",
            "evolutionary_escape_risk_interpretation",
            "therapeutic_priority_score",
            "therapeutic_priority_contribution_summary",
            "therapeutic_priority_components",
            "therapeutic_priority_meta_priority_score_contribution",
            "therapeutic_priority_host_safety_score_contribution",
            "therapeutic_priority_host_damage_score_contribution",
            "therapeutic_priority_infection_site_access_score_contribution",
            "therapeutic_priority_infection_context_score_contribution",
            "therapeutic_role",
            "therapeutic_role_with_controlled_provider",
            "therapeutic_role_without_controlled_provider",
            "therapeutic_role_stability",
            "therapeutic_role_stability_explanation",
            "therapeutic_role_rule",
            "therapeutic_role_rule_without_controlled_provider",
            "therapeutic_priority_score_without_controlled_provider",
            "therapeutic_priority_controlled_delta",
            "controlled_context_max_feature_delta",
            "host_damage_score_controlled_delta",
            "infection_site_access_score_controlled_delta",
            "infection_context_score_controlled_delta",
            "therapeutic_rule_boundary_margin",
            "therapeutic_rule_boundary_proximity",
            "controlled_dependency_flags",
            "clinical_impact_input_status",
            "curated_disease_context_input_status",
            "therapy_site_context_input_status",
            "therapeutic_context_input_summary",
            "therapeutic_context_missingness",
            "preferred_strategy",
            "strategy_margin_score",
            "optional_data_quality_score",
            "optional_data_source_summary",
            "confidence_source_class",
            "confidence_evidence_tier",
            "evidence_level",
            "evidence_source",
            "provenance_status",
            "retrieval_mode",
            "cache_status",
            "interpretation_warning",
            "data_realism_flag",
            "top_positive_drivers",
            "top_negative_drivers",
            "candidate_audit_summary",
    ]
    candidate_audit_columns = list(dict.fromkeys(candidate_audit_columns))
    candidate_audit = phase2_ranking[
        [
            column
            for column in candidate_audit_columns + THERAPEUTIC_SEPARATION_REPORT_COLUMNS
            + HOST_RISK_REPORT_COLUMNS + HUMAN_HOMOLOGY_REPORT_COLUMNS
            + THERAPY_SITE_CONTEXT_REPORT_COLUMNS
            if column in phase2_ranking.columns
        ]
    ].copy()
    candidate_audit.index = phase2_ranking.index
    candidate_audit.index.name = "rank"
    candidate_audit.reset_index().to_csv(results_dir / "candidate_audit.csv", index=False)
    candidate_audit_display = candidate_audit.reset_index()
    candidate_audit_display_columns = [
        column
        for column in [
            "rank",
            "protein_id",
            "gene",
            "therapeutic_role",
            "therapeutic_priority_score",
            "therapeutic_priority_contribution_summary",
            "therapeutic_priority_components",
            "evolutionary_escape_risk_score",
            "evolutionary_escape_risk_status",
            "preferred_strategy",
            "strategy_margin_score",
            "data_realism_flag",
            "host_risk_audit_summary",
            "therapy_site_context_audit_summary",
            "candidate_audit_summary",
        ]
        if column in candidate_audit_display.columns
    ]
    candidate_audit_lines = [
        "# Auditoria Por Candidato",
        "",
        _markdown_table(
            candidate_audit_display[candidate_audit_display_columns]
        ),
    ]
    (results_dir / "candidate_audit.md").write_text("\n".join(candidate_audit_lines), encoding="utf-8")
    top_candidate_review = _build_top_candidate_review(phase2_ranking, sensitivity, top_n)
    top_candidate_review.to_csv(results_dir / "top10_candidate_review.csv", index=False)
    (results_dir / "top10_candidate_review.md").write_text(
        "\n".join(
            [
                "# Revision Top 10",
                "",
                _markdown_table(top_candidate_review),
            ]
        ),
        encoding="utf-8",
    )
    scientific_audit = _build_top10_scientific_audit(
        phase2_ranking=phase2_ranking,
        comparison_output=comparison_output,
        sensitivity=sensitivity,
        provenance_summary=provenance_summary,
        literature_support=literature_support,
        top_n=top_n,
    )
    scientific_audit.to_csv(results_dir / "top10_scientific_audit.csv", index=False)
    (results_dir / "top10_scientific_audit.json").write_text(
        json.dumps(scientific_audit.to_dict(orient="records"), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (results_dir / "top10_scientific_audit.md").write_text(
        _build_top10_scientific_markdown(scientific_audit, provenance_summary, phase2_ranking),
        encoding="utf-8",
    )
    (results_dir / "top10_scientific_summary.md").write_text(
        _build_top10_scientific_summary(scientific_audit),
        encoding="utf-8",
    )

    theory_v3_notes = [
        note
        for note in phase2_ranking.apply(explain_theory_v3_assessment_note, axis=1).dropna().astype(str).unique()
        if note != "not_reported"
    ]
    theory_v3_report_lines = (
        [
            "- Nota theory-first/v3: "
            + theory_v3_notes[0]
            + " Revisar `functional_node_theory_score` y `therapeutic_role_v3` por candidato.",
        ]
        if theory_v3_notes
        else []
    )

    report_lines = [
        f"# Nodos Funcionales - Reporte {mode}",
        "",
        *_metadata_lines(workspace_metadata),
        "## Limites de interpretacion",
        "",
        "- Un score alto no equivale a validacion experimental.",
        "- Un score alto no implica que exista un farmaco disponible.",
        "- Un gen esencial no es automaticamente un buen blanco terapeutico.",
        "- Un factor de virulencia no es automaticamente prioritario.",
        "- Un hub no es automaticamente drogable.",
        "- La ausencia de evidencia no equivale a evidencia negativa.",
        "- La informacion online general no sustituye datos especificos del usuario.",
        "- Bajo riesgo evolutivo no significa ausencia de resistencia.",
        "- El ranking representa hipotesis terapeuticas priorizadas, no recomendaciones clinicas.",
        "- El ranking no constituye recomendacion terapeutica ni sustituye evaluacion medica, microbiologica o farmacologica.",
        "- Requiere validacion experimental y clinica externa antes de cualquier aplicacion.",
        "- `therapeutic_priority_components` muestra como se descompone la prioridad terapeutica dentro del modelo; es una interpretacion computacional, no validacion experimental.",
        "- Esta descomposicion hereda la procedencia de sus capas de entrada: evidencia real, curada, cache, proxy, demo o faltante pueden contribuir segun lo registrado.",
        *theory_v3_report_lines,
        "",
        "## Resumen",
        f"- Candidatos evaluados: {len(features)}",
        f"- Modo de pipeline: `{mode}`",
        "- Ranking principal: `results/ranking_nodos.csv`",
        "- Snapshot compacto de ranking: `results/ranking_snapshot.csv`",
        "- Ranking legacy: `results/ranking_nodos_legacy.csv`",
        "- Resumen ejecutivo: `results/resumen_ejecutivo.md`",
        "- Explicacion simple para usuarios no tecnicos: `results/candidate_explanations_simple.md`",
        "- Soporte bibliografico interpretativo: `results/literature_support_summary.csv`",
        "- Fuerza de evidencia interpretativa: `results/evidence_strength_audit.csv`",
        "- Auditoria de homologos humanos: `results/human_homologs_audit.csv`",
        "- Auditoria de separacion de contexto terapeutico: `results/therapeutic_context_separation_audit.csv`",
        "- Preparacion para reemplazo de capas controladas: `results/controlled_replacement_readiness.csv`",
        "- Auditoria de riesgo de escape evolutivo: `results/evolutionary_escape_risk_audit.csv`",
        "- Cola de curacion de impacto clinico: `results/clinical_impact_curation_queue.csv`",
        "- Cola de curacion de contexto de enfermedad: `results/disease_context_curation_queue.csv`",
        "- Cola de curacion de sitio terapeutico: `results/therapy_site_context_curation_queue.csv`",
        "- Estabilidad del rol con/sin proveedor controlado: `results/therapeutic_role_controlled_stability.csv`",
        "- Tabla de features: `data_processed/phase2_features.csv`",
        "- Tabla de scores: `data_processed/scored_nodes.csv`",
        "- Procedencia de datasets opcionales: `results/data_provenance_summary.csv`",
        "- Resumen por rol terapÃ©utico: `results/therapeutic_role_summary.csv`",
        "- Auditoria por candidato: `results/candidate_audit.csv`",
        "- Auditoria por candidato en Markdown: `results/candidate_audit.md`",
        "- Revision top 10: `results/top10_candidate_review.csv`",
        "- Auditoria cientifica top 10: `results/top10_scientific_audit.csv`",
        "",
        "## Top candidatos",
        "",
    ]
    if ranking_snapshot_comparison_path is not None:
        report_lines.insert(
            report_lines.index("## Top candidatos") - 1,
            "- Comparacion contra snapshot de referencia: `results/ranking_snapshot_comparison.csv`",
        )

    report_lines.insert(report_lines.index("## Top candidatos") - 1, "- Resumen por regla terapÃ©utica: `results/therapeutic_rule_summary.csv`")

    report_lines.insert(report_lines.index("## Top candidatos") - 1, "- Resolucion por capa: `results/layer_resolution_summary.csv`")

    if mode == "legacy":
        report_lines.append(_markdown_table(legacy_output.head(top_n).reset_index()))
    else:
        report_lines.append(_markdown_table(phase2_output.head(top_n).reset_index()))

    if mode == "compare":
        report_lines.extend(
            [
                "",
                "## Comparacion Fase 1 vs Fase 2",
                "",
                _markdown_table(
                    comparison_output[["protein_id", "phase2_rank", "legacy_rank", "rank_shift_phase2_vs_legacy"]].head(top_n)
                ),
            ]
        )

    if mode != "legacy" and not sensitivity.empty:
        report_lines.extend(
            [
                "",
                "## Resolucion Por Capa",
                "",
                _markdown_table(layer_resolution_summary),
                "",
                "## Procedencia de datos opcionales",
                "",
                _markdown_table(provenance_summary),
                "",
                "## Auditoria de homologos humanos",
                "",
                _markdown_table(human_homologs_audit),
                "",
                "## Auditoria de separacion de contexto terapeutico",
                "",
                _markdown_table(therapeutic_context_separation_audit),
                "",
                "## Preparacion para reemplazo de capas controladas",
                "",
                _markdown_table(controlled_replacement_readiness),
                "",
                "## Auditoria De Riesgo De Escape Evolutivo",
                "",
                _markdown_table(evolutionary_escape_risk_audit.head(top_n)),
                "",
                "## Cola de curacion de impacto clinico",
                "",
                _markdown_table(clinical_impact_curation_queue),
                "",
                "## Cola de curacion de contexto de enfermedad",
                "",
                _markdown_table(disease_context_curation_queue),
                "",
                "## Cola de curacion de sitio terapeutico",
                "",
                _markdown_table(therapy_site_context_curation_queue),
                "",
                "## Sensibilidad",
                "",
            ]
        )
        for score_name in ["meta_priority", "antibiotic_target", "antivirulence_target", "functional_node"]:
            scoped = sensitivity.loc[sensitivity["score_name"] == score_name].copy()
            if scoped.empty:
                continue
            top_sensitivity = scoped.sort_values(["scenario", "rank"]).groupby("scenario").head(config["sensitivity"]["top_n"])
            report_lines.extend(
                [
                    f"### {score_name}",
                    "",
                    _markdown_table(top_sensitivity[["scenario", "protein_id", "rank", "rank_delta_vs_base"]]),
                    "",
                ]
            )
        therapeutic_sensitivity = sensitivity.loc[sensitivity["score_name"] == "therapeutic_priority"].copy()
        if not therapeutic_sensitivity.empty:
            top_therapeutic = therapeutic_sensitivity.sort_values(["scenario", "rank"]).groupby("scenario").head(config["sensitivity"]["top_n"])
            role_change_summary = (
                therapeutic_sensitivity.groupby("scenario", as_index=False)["role_changed_vs_base"].sum()
                .rename(columns={"role_changed_vs_base": "role_changes_vs_base"})
            )
            report_lines.extend(
                [
                    "### therapeutic_priority",
                    "",
                    _markdown_table(
                        top_therapeutic[["scenario", "protein_id", "therapeutic_role", "rank", "rank_delta_vs_base", "role_changed_vs_base"]]
                    ),
                    "",
                    _markdown_table(role_change_summary),
                    "",
                ]
            )
        report_lines.extend(
            [
                "## Resumen Por Rol TerapÃ©utico",
                "",
                _markdown_table(therapeutic_role_summary),
                "",
                "## Auditoria Por Candidato",
                "",
                _markdown_table(
                    candidate_audit_display[
                        [
                            column
                            for column in [
                                "rank",
                                "protein_id",
                                "therapeutic_role",
                                "preferred_strategy",
                                "therapeutic_priority_components",
                                "evolutionary_escape_risk_score",
                                "strategy_margin_score",
                                "data_realism_flag",
                                "host_risk_audit_summary",
                                "candidate_audit_summary",
                            ]
                            if column in candidate_audit_display.columns
                        ]
                    ].head(top_n)
                ),
                "",
                "## Revision Top 10",
                "",
                _markdown_table(top_candidate_review),
                "",
                "## AuditorÃ­a CientÃ­fica Estricta Top 10",
                "",
                _markdown_table(_scientific_audit_report_view(scientific_audit)),
            ]
        )

    if mode != "legacy" and not sensitivity.empty:
        try:
            audit_index = report_lines.index("## Auditoria Por Candidato")
            report_lines[audit_index:audit_index] = [
                "## Resumen Por Regla TerapÃ©utica",
                "",
                _markdown_table(therapeutic_rule_summary),
                "",
            ]
        except ValueError:
            pass

    (results_dir / "report_phase2.md").write_text("\n".join(report_lines), encoding="utf-8")

