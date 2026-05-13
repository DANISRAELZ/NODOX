from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from .layer_registry import TARGET_LAYER_KEYS
from .layer_resolver import load_layer_resolution_manifest


HOST_ANNOTATION_AUDIT_COLUMNS = [
    "domain_overlap_score",
    "host_criticality_penalty",
    "interpro_bacterial_accession",
    "interpro_human_accession",
    "interpro_bacterial_entries",
    "interpro_human_entries",
    "interpro_shared_entries",
    "human_essentiality_score",
    "human_essentiality_status",
    "human_essentiality_lookup_status",
    "interpro_rule",
    "interpro_missing_flags",
    "host_annotation_rule",
    "host_annotation_inputs",
    "host_annotation_confidence_reason",
    "host_annotation_missing_flags",
]

PHASE3_CONTEXTUAL_COLUMNS = [
    "contextual_essentiality_score",
    "pleiotropy_score",
    "functional_node_theory_score",
    "therapeutic_role_v3",
    "phase3_notes",
]

PHASE3_EVOLUTIONARY_COLUMNS = [
    "known_escape_mutation_score",
    "inferred_functional_tolerance_score",
    "module_participation_score",
    "paralog_count_score",
    "alternative_pathway_score",
    "mutational_tolerance_score",
    "fitness_cost_score",
    "compensation_difficulty_score",
    "biofilm_escape_penalty",
    "horizontal_transfer_penalty",
    "evolutionary_escape_risk_score",
    "evolutionary_space_constraint_score",
]

EVOLUTIONARY_ESCAPE_RISK_COLUMNS = [
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
    "evolutionary_escape_risk_evidence_source",
    "evolutionary_escape_risk_input_source_type",
    "evolutionary_escape_risk_input_confidence",
    "evolutionary_escape_risk_notes",
    "mutation_tolerance",
    "pathway_redundancy",
    "mobile_context",
    "hgt_context",
    "recombination_context",
    "resistance_association",
    "evidence_level",
    "provenance_status",
    "retrieval_mode",
    "cache_status",
    "source_version",
    "updated_at",
]

PHASE3_REDUNDANCY_COLUMNS = [
    "paralog_count",
    "pathway_alternative_count",
    "functional_backup_score",
    "metabolic_bypass_score",
    "regulatory_bypass_score",
    "paralog_evidence_reference",
    "pathway_evidence_reference",
    "redundancy_evidence_type",
    "redundancy_evidence_source_type",
    "redundancy_evidence_quality_score",
    "redundancy_confidence_ceiling",
    "redundancy_evidence_notes",
    "redundancy_audit_flags",
    "redundancy_phase3_notes",
]

PHASE3_COLLATERAL_COLUMNS = [
    "collateral_sensitivity_score",
    "combination_opportunity_score",
    "recommended_combination_class",
    "combination_partner",
    "combination_evidence_reference",
    "combination_rationale",
]

PHASE3_EVIDENCE_COLUMNS = [
    "evidence_quality_score",
    "confidence_ceiling",
    "evidence_source_type",
    "evidence_notes",
    "audit_flags",
]


def _read_optional(processed_dir: Path, filename: str) -> pd.DataFrame | None:
    path = processed_dir / filename
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return None


def _merge_optional_feature_table(
    merged: pd.DataFrame,
    table: pd.DataFrame | None,
    feature_columns: list[str],
    database_column_name: str,
) -> pd.DataFrame:
    if table is None:
        return merged

    available = ["protein_id_canonical"] + [column for column in feature_columns if column in table.columns]
    if "source_database" in table.columns:
        available.append("source_database")
    subset = table[available].copy()
    if "source_database" in subset.columns:
        subset = subset.rename(columns={"source_database": database_column_name})

    return merged.merge(subset, on="protein_id_canonical", how="outer")


def integrate_tables(base_dir: Path) -> pd.DataFrame:
    processed_dir = base_dir / "data_processed"
    config_path = base_dir / "config" / "params.yaml"
    manifest = {}
    if config_path.exists():
        from .config import load_config

        manifest = load_layer_resolution_manifest(base_dir, load_config(config_path))

    essentiality = pd.read_csv(processed_dir / "normalized_essentiality.csv")
    virulence = pd.read_csv(processed_dir / "normalized_virulence.csv")
    homologs = pd.read_csv(processed_dir / "normalized_human_homologs.csv")
    localization = pd.read_csv(processed_dir / "normalized_localization.csv")
    conservation = _read_optional(processed_dir, "normalized_strain_conservation.csv")
    network = _read_optional(processed_dir, "normalized_functional_network.csv")
    host_annotation = _read_optional(processed_dir, "normalized_host_annotation.csv")
    clinical_impact = _read_optional(processed_dir, "normalized_clinical_impact.csv")
    disease_context = _read_optional(processed_dir, "normalized_curated_disease_context.csv")
    therapy_site_context = _read_optional(processed_dir, "normalized_therapy_site_context.csv")
    evolutionary_escape = _read_optional(processed_dir, "normalized_evolutionary_escape.csv")
    evolutionary_escape_risk = _read_optional(processed_dir, "normalized_evolutionary_escape_risk.csv")
    collateral_sensitivity = _read_optional(processed_dir, "normalized_collateral_sensitivity.csv")
    redundancy = _read_optional(processed_dir, "normalized_redundancy.csv")
    contextual_essentiality = _read_optional(processed_dir, "normalized_contextual_essentiality.csv")
    evidence_quality = _read_optional(processed_dir, "normalized_evidence_quality.csv")
    literature_support = _read_optional(processed_dir, "normalized_literature_support.csv")
    if literature_support is not None:
        literature_support = literature_support.rename(
            columns={
                "evidence_type": "literature_evidence_type",
                "evidence_source_type": "literature_evidence_source_type",
                "source_quality": "literature_source_quality",
            }
        )

    homolog_columns = [
        column
        for column in [
            "protein_id_canonical",
            "human_homolog",
            "evalue",
            "human_gene",
            "homology_lookup_status",
            "homology_query_strategy",
            "homology_evidence_note",
            "human_uniprot_accession",
            "human_uniprot_id",
            "homology_evidence_tier",
            "homology_confidence_score",
            "homology_missing_flags",
            "orthology_method",
            "orthology_tool",
            "orthology_version",
            "orthology_reference",
            "orthology_query_coverage",
            "orthology_subject_coverage",
            "orthology_percent_identity",
            "orthology_bitscore",
            "orthology_confidence_score",
            "orthology_evidence_note",
            "source_database",
        ]
        if column in homologs.columns
    ]

    merged = (
        essentiality.merge(
            virulence[
                [
                    "protein_id_canonical",
                    "virulence_factor",
                    "virulence_score",
                    "source_database",
                ]
            ].rename(columns={"source_database": "virulence_database"}),
            on="protein_id_canonical",
            how="outer",
        )
        .merge(
            homologs[homolog_columns].rename(columns={"source_database": "homology_database"}),
            on="protein_id_canonical",
            how="outer",
        )
        .merge(
            localization[
                [
                    "protein_id_canonical",
                    "localization",
                    "source_database",
                ]
            ].rename(columns={"source_database": "localization_database"}),
            on="protein_id_canonical",
            how="outer",
        )
    )

    if "source_database" in merged.columns:
        merged = merged.rename(columns={"source_database": "essentiality_database"})

    merged = _merge_optional_feature_table(
        merged,
        conservation,
        ["core_genome_presence", "strain_coverage_score", "allelic_conservation", "variant_burden"],
        "conservation_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        network,
        ["network_centrality", "pathway_bottleneck_score", "redundancy_penalty", "functional_dependency_score"],
        "network_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        host_annotation,
        HOST_ANNOTATION_AUDIT_COLUMNS,
        "host_annotation_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        clinical_impact,
        [
            "host_damage_reduction_potential",
            "disease_severity_association",
            "clinical_impact_score",
            "host_damage_score",
            "host_direct_damage_score",
            "virulence_associated_severity_score",
            "clinical_impact_catalog_source",
            "clinical_impact_evidence_type",
            "clinical_impact_evidence_reference",
            "clinical_impact_evidence_note",
        ],
        "clinical_impact_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        disease_context,
        [
            "infection_context_score",
            "disease_context",
            "infection_stage",
            "context_evidence_type",
            "context_evidence_reference",
            "context_evidence_note",
        ],
        "disease_context_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        therapy_site_context,
        [
            "infection_site_access",
            "infection_site",
            "access_evidence_type",
            "access_evidence_reference",
            "access_evidence_note",
            "disease_context",
            "syndrome",
            "disease_site_context_source",
        ],
        "therapy_site_context_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        contextual_essentiality,
        PHASE3_CONTEXTUAL_COLUMNS,
        "contextual_essentiality_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        evolutionary_escape,
        PHASE3_EVOLUTIONARY_COLUMNS,
        "evolutionary_escape_database",
    )
    if evolutionary_escape_risk is not None:
        evolutionary_escape_risk = evolutionary_escape_risk.rename(
            columns={
                "evidence_source": "evolutionary_escape_risk_evidence_source",
                "source_type": "evolutionary_escape_risk_input_source_type",
                "confidence": "evolutionary_escape_risk_input_confidence",
                "notes": "evolutionary_escape_risk_notes",
            }
        )
    merged = _merge_optional_feature_table(
        merged,
        evolutionary_escape_risk,
        EVOLUTIONARY_ESCAPE_RISK_COLUMNS,
        "evolutionary_escape_risk_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        redundancy,
        PHASE3_REDUNDANCY_COLUMNS,
        "redundancy_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        collateral_sensitivity,
        PHASE3_COLLATERAL_COLUMNS,
        "collateral_sensitivity_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        evidence_quality,
        PHASE3_EVIDENCE_COLUMNS,
        "phase3_evidence_quality_database",
    )
    merged = _merge_optional_feature_table(
        merged,
        literature_support,
        [
            "literature_support_score",
            "literature_evidence_type",
            "therapeutic_relevance",
            "virulence_relevance",
            "essentiality_relevance",
            "resistance_relevance",
            "host_safety_relevance",
            "evolutionary_escape_relevance",
            "citation",
            "doi",
            "pubmed_id",
            "year",
            "evidence_strength",
            "literature_evidence_source_type",
            "curator_notes",
            "literature_source_quality",
            "catalog_protein_id",
            "catalog_gene",
            "curated_online_catalog_source",
            "curated_online_match_status",
        ],
        "literature_support_database",
    )

    for maybe_column in [
        "protein_id_original",
        "gene",
        "gene_symbol_normalized",
        "mapping_confidence",
        "uniprot_accession",
        "uniprot_id",
        "uniprot_reviewed",
        "uniprot_protein_name",
        "uniprot_gene_primary",
        "uniprot_gene_names",
        "uniprot_match_status",
        "provider",
    ]:
        related_columns = [col for col in merged.columns if col == maybe_column or col.startswith(f"{maybe_column}_")]
        if not related_columns and maybe_column in essentiality.columns:
            merged[maybe_column] = essentiality.set_index("protein_id_canonical")[maybe_column].reindex(merged["protein_id_canonical"]).values

    gene_candidates = [col for col in merged.columns if col.startswith("gene")]
    merged["gene"] = merged[gene_candidates].bfill(axis=1).iloc[:, 0]
    normalized_gene_candidates = [col for col in merged.columns if col.startswith("gene_symbol_normalized")]
    if normalized_gene_candidates:
        merged["gene_symbol_normalized"] = merged[normalized_gene_candidates].bfill(axis=1).iloc[:, 0]

    original_id_candidates = [col for col in merged.columns if col.startswith("protein_id_original")]
    if original_id_candidates:
        merged["protein_id_original"] = merged[original_id_candidates].bfill(axis=1).iloc[:, 0]

    mapping_candidates = [col for col in merged.columns if col.startswith("mapping_confidence")]
    if mapping_candidates:
        merged["mapping_confidence"] = pd.to_numeric(merged[mapping_candidates].bfill(axis=1).iloc[:, 0], errors="coerce").fillna(1.0)

    merged["protein_id"] = merged["protein_id_canonical"]

    source_columns = [col for col in merged.columns if col.endswith("_database")]
    merged["source_database"] = merged[source_columns].fillna("").agg(";".join, axis=1).str.strip(";")

    layer_provenance_defaults = [
        ("source_type", "missing"),
        ("source_name", "missing"),
        ("is_user_supplied", False),
        ("is_external", False),
        ("is_cached", False),
        ("is_proxy", False),
        ("confidence", 0.0),
        ("retrieval_status", "missing"),
    ]
    layer_provenance = {
        f"{layer_key}_{suffix}": manifest.get(layer_key, {}).get(suffix, default)
        for layer_key in TARGET_LAYER_KEYS
        for suffix, default in layer_provenance_defaults
    }
    if layer_provenance:
        merged = pd.concat([merged, pd.DataFrame(layer_provenance, index=merged.index)], axis=1).copy()

    keep_columns = [
        "protein_id",
        "protein_id_original",
        "protein_id_canonical",
        "gene",
        "gene_symbol_normalized",
        "mapping_confidence",
        "uniprot_accession",
        "uniprot_id",
        "uniprot_reviewed",
        "uniprot_protein_name",
        "uniprot_gene_primary",
        "uniprot_gene_names",
        "uniprot_match_status",
        "provider",
        "source_database",
        "essential",
        "evidence",
        "essentiality_database",
        "virulence_factor",
        "virulence_score",
        "virulence_database",
        "human_homolog",
        "evalue",
        "human_gene",
        "homology_lookup_status",
        "homology_query_strategy",
        "homology_evidence_note",
        "human_uniprot_accession",
        "human_uniprot_id",
        "homology_evidence_tier",
        "homology_confidence_score",
        "homology_missing_flags",
        "orthology_method",
        "orthology_tool",
        "orthology_version",
        "orthology_reference",
        "orthology_query_coverage",
        "orthology_subject_coverage",
        "orthology_percent_identity",
        "orthology_bitscore",
        "orthology_confidence_score",
        "orthology_evidence_note",
        "homology_database",
        *HOST_ANNOTATION_AUDIT_COLUMNS,
        "host_annotation_database",
        "host_damage_reduction_potential",
        "disease_severity_association",
        "clinical_impact_score",
        "host_damage_score",
        "host_direct_damage_score",
        "virulence_associated_severity_score",
        "clinical_impact_catalog_source",
        "clinical_impact_evidence_type",
        "clinical_impact_evidence_reference",
        "clinical_impact_evidence_note",
        "clinical_impact_database",
        "localization",
        "localization_database",
        "infection_context_score",
        "disease_context",
        "infection_stage",
        "context_evidence_type",
        "context_evidence_reference",
        "context_evidence_note",
        "disease_context_database",
        "infection_site_access",
        "infection_site",
        "access_evidence_type",
        "access_evidence_reference",
        "access_evidence_note",
        "disease_context",
        "syndrome",
        "disease_site_context_source",
        "therapy_site_context_database",
        "core_genome_presence",
        "strain_coverage_score",
        "allelic_conservation",
        "variant_burden",
        "conservation_database",
        "network_centrality",
        "pathway_bottleneck_score",
        "redundancy_penalty",
        "functional_dependency_score",
        "network_database",
        *PHASE3_CONTEXTUAL_COLUMNS,
        "contextual_essentiality_database",
        *PHASE3_EVOLUTIONARY_COLUMNS,
        "evolutionary_escape_database",
        *EVOLUTIONARY_ESCAPE_RISK_COLUMNS,
        "evolutionary_escape_risk_database",
        *PHASE3_REDUNDANCY_COLUMNS,
        "redundancy_database",
        *PHASE3_COLLATERAL_COLUMNS,
        "collateral_sensitivity_database",
        *PHASE3_EVIDENCE_COLUMNS,
        "phase3_evidence_quality_database",
        "literature_support_score",
        "literature_evidence_type",
        "therapeutic_relevance",
        "virulence_relevance",
        "essentiality_relevance",
        "resistance_relevance",
        "host_safety_relevance",
        "evolutionary_escape_relevance",
        "citation",
        "doi",
        "pubmed_id",
        "year",
        "evidence_strength",
        "literature_evidence_source_type",
        "curator_notes",
        "literature_source_quality",
        "catalog_protein_id",
        "catalog_gene",
        "curated_online_catalog_source",
        "curated_online_match_status",
        "literature_support_database",
    ]
    for layer_key in TARGET_LAYER_KEYS:
        keep_columns.extend(
            [
                f"{layer_key}_source_type",
                f"{layer_key}_source_name",
                f"{layer_key}_is_user_supplied",
                f"{layer_key}_is_external",
                f"{layer_key}_is_cached",
                f"{layer_key}_is_proxy",
                f"{layer_key}_confidence",
                f"{layer_key}_retrieval_status",
            ]
        )
    integrated = merged[[column for column in keep_columns if column in merged.columns]].copy()
    integrated.to_csv(processed_dir / "integrated_nodes.csv", index=False)
    return integrated
