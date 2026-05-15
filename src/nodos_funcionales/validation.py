from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .io_errors import ensure_dir, read_csv, write_csv


@dataclass
class Schema:
    required: list[str]
    optional: list[str]
    numeric_columns: list[str]
    binary_columns: list[str]
    range_constraints: dict[str, tuple[float, float]]


@dataclass
class DatasetSpec:
    filename: str
    table_key: str
    required: bool


PHASE3_NUMERIC_COLUMNS = [
    "contextual_essentiality_score",
    "pleiotropy_score",
    "conservation_score",
    "functional_node_theory_score",
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
    "paralog_count_score",
    "alternative_pathway_score",
    "functional_backup_score",
    "metabolic_bypass_score",
    "regulatory_bypass_score",
    "mutational_tolerance_score",
    "known_escape_mutation_score",
    "inferred_functional_tolerance_score",
    "module_participation_score",
    "redundancy_penalty",
    "fitness_cost_score",
    "compensation_difficulty_score",
    "collateral_sensitivity_score",
    "combination_opportunity_score",
    "biofilm_escape_penalty",
    "horizontal_transfer_penalty",
    "evolutionary_escape_risk_score",
    "evolutionary_space_constraint_score",
    "evidence_quality_score",
    "confidence_ceiling",
]

PHASE3_RANGE_CONSTRAINTS = {column: (0.0, 1.0) for column in PHASE3_NUMERIC_COLUMNS}


SCHEMAS: dict[str, Schema] = {
    "essentiality": Schema(
        required=["protein_id", "gene", "essential"],
        optional=["evidence", "database"],
        numeric_columns=["essential"],
        binary_columns=["essential"],
        range_constraints={"essential": (0, 1)},
    ),
    "virulence": Schema(
        required=["protein_id", "gene", "virulence_score"],
        optional=["virulence_factor", "database"],
        numeric_columns=["virulence_score", "virulence_factor"],
        binary_columns=["virulence_factor"],
        range_constraints={"virulence_score": (0.0, 1.0), "virulence_factor": (0, 1)},
    ),
    "human_homologs": Schema(
        required=["protein_id", "gene", "human_homolog", "evalue"],
        optional=[
            "human_gene",
            "human_hit_id",
            "human_hit_name",
            "percent_identity",
            "query_coverage",
            "subject_coverage",
            "bit_score",
            "shared_domain_count",
            "source_database",
            "evidence_source_type",
            "curator_notes",
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
        ],
        numeric_columns=[
            "human_homolog",
            "evalue",
            "percent_identity",
            "query_coverage",
            "subject_coverage",
            "bit_score",
            "shared_domain_count",
            "homology_confidence_score",
            "orthology_query_coverage",
            "orthology_subject_coverage",
            "orthology_percent_identity",
            "orthology_bitscore",
            "orthology_confidence_score",
        ],
        binary_columns=["human_homolog"],
        range_constraints={
            "human_homolog": (0, 1),
            "evalue": (0.0, float("inf")),
            "percent_identity": (0.0, 100.0),
            "query_coverage": (0.0, 1.0),
            "subject_coverage": (0.0, 1.0),
            "bit_score": (0.0, float("inf")),
            "shared_domain_count": (0.0, float("inf")),
            "homology_confidence_score": (0.0, 1.0),
            "orthology_query_coverage": (0.0, 1.0),
            "orthology_subject_coverage": (0.0, 1.0),
            "orthology_percent_identity": (0.0, 100.0),
            "orthology_bitscore": (0.0, float("inf")),
            "orthology_confidence_score": (0.0, 1.0),
        },
    ),
    "localization": Schema(
        required=["protein_id", "gene", "localization"],
        optional=["database"],
        numeric_columns=[],
        binary_columns=[],
        range_constraints={},
    ),
    "strain_conservation": Schema(
        required=["protein_id", "gene", "core_genome_presence", "strain_coverage_score", "allelic_conservation", "variant_burden"],
        optional=["database"],
        numeric_columns=["core_genome_presence", "strain_coverage_score", "allelic_conservation", "variant_burden"],
        binary_columns=[],
        range_constraints={
            "core_genome_presence": (0.0, 1.0),
            "strain_coverage_score": (0.0, 1.0),
            "allelic_conservation": (0.0, 1.0),
            "variant_burden": (0.0, 1.0),
        },
    ),
    "functional_network": Schema(
        required=["protein_id", "gene", "network_centrality", "pathway_bottleneck_score", "redundancy_penalty", "functional_dependency_score"],
        optional=["database"],
        numeric_columns=["network_centrality", "pathway_bottleneck_score", "redundancy_penalty", "functional_dependency_score"],
        binary_columns=[],
        range_constraints={
            "network_centrality": (0.0, 1.0),
            "pathway_bottleneck_score": (0.0, 1.0),
            "redundancy_penalty": (0.0, 1.0),
            "functional_dependency_score": (0.0, 1.0),
        },
    ),
    "host_annotation": Schema(
        required=["protein_id", "gene", "domain_overlap_score", "host_criticality_penalty"],
        optional=["database"],
        numeric_columns=["domain_overlap_score", "host_criticality_penalty"],
        binary_columns=[],
        range_constraints={
            "domain_overlap_score": (0.0, 1.0),
            "host_criticality_penalty": (0.0, 1.0),
        },
    ),
    "clinical_impact": Schema(
        required=["protein_id", "gene", "host_damage_reduction_potential", "disease_severity_association", "clinical_impact_score"],
        optional=[
            "host_damage_score",
            "host_direct_damage_score",
            "virulence_associated_severity_score",
            "clinical_impact_catalog_source",
            "clinical_impact_evidence_type",
            "clinical_impact_evidence_reference",
            "clinical_impact_evidence_note",
            "database",
        ],
        numeric_columns=[
            "host_damage_reduction_potential",
            "disease_severity_association",
            "clinical_impact_score",
            "host_damage_score",
            "host_direct_damage_score",
            "virulence_associated_severity_score",
        ],
        binary_columns=[],
        range_constraints={
            "host_damage_reduction_potential": (0.0, 1.0),
            "disease_severity_association": (0.0, 1.0),
            "clinical_impact_score": (0.0, 1.0),
            "host_damage_score": (0.0, 1.0),
            "host_direct_damage_score": (0.0, 1.0),
            "virulence_associated_severity_score": (0.0, 1.0),
        },
    ),
    "curated_disease_context": Schema(
        required=["protein_id", "gene", "infection_context_score"],
        optional=[
            "disease_context",
            "infection_stage",
            "context_evidence_type",
            "context_evidence_reference",
            "context_evidence_note",
            "database",
        ],
        numeric_columns=["infection_context_score"],
        binary_columns=[],
        range_constraints={"infection_context_score": (0.0, 1.0)},
    ),
    "therapy_site_context": Schema(
        required=["protein_id", "gene", "infection_site_access"],
        optional=[
            "infection_site",
            "access_evidence_type",
            "access_evidence_reference",
            "access_evidence_note",
            "disease_context",
            "syndrome",
            "disease_site_context_source",
            "database",
        ],
        numeric_columns=["infection_site_access"],
        binary_columns=[],
        range_constraints={"infection_site_access": (0.0, 1.0)},
    ),
    "literature_support": Schema(
        required=["protein_id", "gene", "literature_support_score"],
        optional=[
            "gene_id",
            "organism",
            "disease_context",
            "evidence_type",
            "therapeutic_relevance",
            "virulence_relevance",
            "essentiality_relevance",
            "resistance_relevance",
            "host_safety_relevance",
            "evolutionary_escape_relevance",
            "reference",
            "citation",
            "doi",
            "doi_or_url",
            "pubmed_id",
            "year",
            "evidence_strength",
            "evidence_source_type",
            "curator_notes",
            "notes",
            "source_quality",
            "database",
        ],
        numeric_columns=[
            "literature_support_score",
            "therapeutic_relevance",
            "virulence_relevance",
            "essentiality_relevance",
            "resistance_relevance",
            "host_safety_relevance",
            "evolutionary_escape_relevance",
            "year",
            "evidence_strength",
            "source_quality",
        ],
        binary_columns=[],
        range_constraints={
            "literature_support_score": (0.0, 1.0),
            "therapeutic_relevance": (-1.0, 1.0),
            "virulence_relevance": (-1.0, 1.0),
            "essentiality_relevance": (-1.0, 1.0),
            "resistance_relevance": (-1.0, 1.0),
            "host_safety_relevance": (-1.0, 1.0),
            "evolutionary_escape_relevance": (-1.0, 1.0),
            "evidence_strength": (0.0, 1.0),
            "source_quality": (0.0, 1.0),
        },
    ),
    "evolutionary_escape": Schema(
        required=["protein_id", "gene"],
        optional=[
            "known_escape_mutation_score",
            "paralog_count",
            "alternative_pathways",
            "pathway_redundancy_evidence",
            "known_escape_mutations",
            "known_escape_mutation_source",
            "fitness_cost_evidence",
            "compensatory_mechanisms",
            "module_participation_count",
            "essential_module_count",
            "mutational_tolerance_evidence",
            "inferred_functional_tolerance_score",
            "module_participation_score",
            "paralog_count_score",
            "alternative_pathway_score",
            "mutational_tolerance_score",
            "redundancy_penalty",
            "fitness_cost_score",
            "compensation_difficulty_score",
            "biofilm_escape_penalty",
            "horizontal_transfer_penalty",
            "evolutionary_escape_risk_score",
            "evolutionary_space_constraint_score",
            "evidence_source_type",
            "evidence_quality_score",
            "confidence_ceiling",
            "evidence_notes",
            "audit_flags",
            "phase3_notes",
            "database",
            "source_database_or_reference",
            "curator_notes",
        ],
        numeric_columns=[
            "paralog_count",
            "alternative_pathways",
            "known_escape_mutations",
            "module_participation_count",
            "essential_module_count",
            "known_escape_mutation_score",
            "inferred_functional_tolerance_score",
            "module_participation_score",
            "paralog_count_score",
            "alternative_pathway_score",
            "mutational_tolerance_score",
            "redundancy_penalty",
            "fitness_cost_score",
            "compensation_difficulty_score",
            "biofilm_escape_penalty",
            "horizontal_transfer_penalty",
            "evolutionary_escape_risk_score",
            "evolutionary_space_constraint_score",
            "evidence_quality_score",
            "confidence_ceiling",
        ],
        binary_columns=[],
        range_constraints=PHASE3_RANGE_CONSTRAINTS,
    ),
    "evolutionary_escape_risk": Schema(
        required=["protein_id", "gene"],
        optional=[
            "candidate_id",
            "organism",
            "strain",
            "mutation_tolerance_score",
            "functional_redundancy_escape_score",
            "compensatory_pathway_score",
            "fitness_cost_of_escape",
            "evolutionary_constraint_score",
            "resistance_emergence_risk",
            "multi_node_dependency_score",
            "evolutionary_escape_risk_score",
            "evidence_source",
            "source_type",
            "confidence",
            "notes",
            "database",
        ],
        numeric_columns=[
            "mutation_tolerance_score",
            "functional_redundancy_escape_score",
            "compensatory_pathway_score",
            "fitness_cost_of_escape",
            "evolutionary_constraint_score",
            "resistance_emergence_risk",
            "multi_node_dependency_score",
            "evolutionary_escape_risk_score",
        ],
        binary_columns=[],
        range_constraints=PHASE3_RANGE_CONSTRAINTS,
    ),
    "collateral_sensitivity": Schema(
        required=["protein_id", "gene"],
        optional=[
            "collateral_sensitivity_score",
            "combination_opportunity_score",
            "recommended_combination_class",
            "combination_rationale",
            "combination_partner",
            "combination_evidence_reference",
            "evidence_source_type",
            "evidence_quality_score",
            "confidence_ceiling",
            "evidence_notes",
            "audit_flags",
            "phase3_notes",
            "database",
        ],
        numeric_columns=["collateral_sensitivity_score", "combination_opportunity_score", "evidence_quality_score", "confidence_ceiling"],
        binary_columns=[],
        range_constraints=PHASE3_RANGE_CONSTRAINTS,
    ),
    "redundancy": Schema(
        required=["protein_id", "gene"],
        optional=[
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
            "database",
        ],
        numeric_columns=[
            "paralog_count",
            "pathway_alternative_count",
            "functional_backup_score",
            "metabolic_bypass_score",
            "regulatory_bypass_score",
            "redundancy_evidence_quality_score",
            "redundancy_confidence_ceiling",
        ],
        binary_columns=[],
        range_constraints={
            "functional_backup_score": (0.0, 1.0),
            "metabolic_bypass_score": (0.0, 1.0),
            "regulatory_bypass_score": (0.0, 1.0),
            "redundancy_evidence_quality_score": (0.0, 1.0),
            "redundancy_confidence_ceiling": (0.0, 1.0),
        },
    ),
    "contextual_essentiality": Schema(
        required=["protein_id", "gene"],
        optional=[
            "contextual_essentiality_score",
            "pleiotropy_score",
            "conservation_score",
            "functional_node_theory_score",
            "therapeutic_role_v3",
            "evidence_source_type",
            "evidence_quality_score",
            "confidence_ceiling",
            "evidence_notes",
            "audit_flags",
            "phase3_notes",
            "database",
        ],
        numeric_columns=[
            "contextual_essentiality_score",
            "pleiotropy_score",
            "conservation_score",
            "functional_node_theory_score",
            "evidence_quality_score",
            "confidence_ceiling",
        ],
        binary_columns=[],
        range_constraints=PHASE3_RANGE_CONSTRAINTS,
    ),
    "evidence_quality": Schema(
        required=["protein_id", "gene"],
        optional=[
            "evidence_quality_score",
            "confidence_ceiling",
            "evidence_source_type",
            "evidence_notes",
            "audit_flags",
            "phase3_notes",
            "database",
        ],
        numeric_columns=["evidence_quality_score", "confidence_ceiling"],
        binary_columns=[],
        range_constraints=PHASE3_RANGE_CONSTRAINTS,
    ),
}


DATASET_SPECS: list[DatasetSpec] = [
    DatasetSpec(filename="essentiality.csv", table_key="essentiality", required=True),
    DatasetSpec(filename="virulence.csv", table_key="virulence", required=True),
    DatasetSpec(filename="human_homologs.csv", table_key="human_homologs", required=True),
    DatasetSpec(filename="localization.csv", table_key="localization", required=True),
    DatasetSpec(filename="strain_conservation.csv", table_key="strain_conservation", required=False),
    DatasetSpec(filename="functional_network.csv", table_key="functional_network", required=False),
    DatasetSpec(filename="host_annotation.csv", table_key="host_annotation", required=False),
    DatasetSpec(filename="clinical_impact.csv", table_key="clinical_impact", required=False),
    DatasetSpec(filename="curated_disease_context.csv", table_key="curated_disease_context", required=False),
    DatasetSpec(filename="therapy_site_context.csv", table_key="therapy_site_context", required=False),
    DatasetSpec(filename="literature_support.csv", table_key="literature_support", required=False),
    DatasetSpec(filename="evolutionary_escape.csv", table_key="evolutionary_escape", required=False),
    DatasetSpec(filename="evolutionary_escape_risk.csv", table_key="evolutionary_escape_risk", required=False),
    DatasetSpec(filename="collateral_sensitivity.csv", table_key="collateral_sensitivity", required=False),
    DatasetSpec(filename="redundancy.csv", table_key="redundancy", required=False),
    DatasetSpec(filename="contextual_essentiality.csv", table_key="contextual_essentiality", required=False),
    DatasetSpec(filename="evidence_quality.csv", table_key="evidence_quality", required=False),
]


def _is_optional_template_only(df: pd.DataFrame) -> bool:
    if df.empty:
        return True
    if "protein_id" in df.columns:
        protein_ids = df["protein_id"].fillna("").astype(str).str.strip().str.upper()
        if len(protein_ids) > 0 and protein_ids.ne("").all() and protein_ids.str.startswith("EXAMPLE").all():
            return True
    for marker_column in ["audit_flags", "phase3_notes", "curator_notes", "notes"]:
        if marker_column in df.columns:
            markers = df[marker_column].fillna("").astype(str).str.lower()
            non_empty = markers.str.strip().ne("")
            if non_empty.any() and markers[non_empty].str.contains("example_only|template").all():
                return True
    return False


def validate_table(df: pd.DataFrame, table_key: str, config: dict[str, Any]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    schema = SCHEMAS[table_key]
    issues: list[dict[str, Any]] = []
    validated = df.copy()

    missing_required = [col for col in schema.required if col not in validated.columns]
    if missing_required:
        present_columns = sorted(str(column) for column in validated.columns)
        raise ValueError(
            f"{table_key}: faltan columnas requeridas: {missing_required}. "
            f"Columnas presentes: {present_columns}. "
            "Compare el CSV con la plantilla correspondiente en data_templates/ y conserve los nombres de columnas."
        )
    if validated.empty:
        raise ValueError(f"{table_key}: el archivo no contiene filas")

    validated["protein_id"] = validated["protein_id"].astype("string").str.strip()
    empty_ids = int(validated["protein_id"].isna().sum() + (validated["protein_id"] == "").sum())
    if empty_ids:
        raise ValueError(f"{table_key}: hay {empty_ids} protein_id vacios")

    duplicated = validated["protein_id"].duplicated(keep=False)
    duplicated_count = int(duplicated.sum())
    if duplicated_count:
        issues.append(
            {
                "table": table_key,
                "severity": "warning",
                "issue_type": "duplicate_protein_id",
                "count": duplicated_count,
                "details": ",".join(validated.loc[duplicated, "protein_id"].astype(str).unique().tolist()),
            }
        )
        if config["validation"]["duplicate_policy"] == "keep_first":
            validated = validated.drop_duplicates(subset="protein_id", keep="first")

    for column in schema.numeric_columns:
        if column in validated.columns:
            validated[column] = pd.to_numeric(validated[column], errors="coerce")
            issues.append(
                {
                    "table": table_key,
                    "severity": "info",
                    "issue_type": "missing_numeric_values",
                    "column": column,
                    "count": int(validated[column].isna().sum()),
                    "details": "",
                }
            )

    for column in schema.binary_columns:
        if column in validated.columns:
            invalid_mask = validated[column].notna() & ~validated[column].isin([0, 1])
            if int(invalid_mask.sum()):
                raise ValueError(f"{table_key}: la columna {column} contiene valores fuera de 0/1")

    for column, (lower, upper) in schema.range_constraints.items():
        if column in validated.columns:
            mask = validated[column].notna() & ((validated[column] < lower) | (validated[column] > upper))
            if int(mask.sum()):
                raise ValueError(f"{table_key}: la columna {column} tiene valores fuera del rango [{lower}, {upper}]")

    if table_key == "localization":
        allowed = set(config["validation"]["allowed_localizations"].keys())
        validated["localization"] = validated["localization"].astype("string").str.strip().str.lower()
        invalid = validated["localization"].dropna().loc[lambda s: ~s.isin(allowed)]
        if not invalid.empty:
            raise ValueError(f"localization: etiquetas no permitidas: {sorted(invalid.unique().tolist())}")

    if table_key == "human_homologs":
        inconsistent = validated[
            (validated["human_homolog"] == 0)
            & validated.get("human_gene", pd.Series(index=validated.index, dtype="string")).fillna("none").astype(str).str.lower().ne("none")
        ]
        if not inconsistent.empty:
            issues.append(
                {
                    "table": table_key,
                    "severity": "warning",
                    "issue_type": "semantic_inconsistency",
                    "count": len(inconsistent),
                    "details": "human_homolog=0 pero human_gene distinto de 'none'",
                }
            )

    for column in schema.required + schema.optional:
        if column in validated.columns:
            issues.append(
                {
                    "table": table_key,
                    "severity": "info",
                    "issue_type": "missing_values",
                    "column": column,
                    "count": int(validated[column].isna().sum()),
                    "details": "",
                }
            )

    return validated, issues


def load_and_validate_all(base_dir: Path, config: dict[str, Any]) -> pd.DataFrame:
    from .layer_resolver import resolve_layer_inputs

    raw_dir = base_dir / "data_raw"
    processed_dir = base_dir / "data_processed"
    ensure_dir(processed_dir)

    resolve_layer_inputs(base_dir, config)

    issue_rows: list[dict[str, Any]] = []

    for spec in DATASET_SPECS:
        filepath = raw_dir / spec.filename
        if not filepath.exists():
            if spec.required:
                raise FileNotFoundError(
                    f"No se encontro {filepath}. Este dataset es obligatorio para ejecutar el pipeline. "
                    "Agregue el CSV al workspace, ejecute discovery en modo semi_auto para crear plantillas, "
                    "o use --allow-demo-data solo si desea correr un demo compatible."
                )
            continue

        df = read_csv(filepath)
        if not spec.required and _is_optional_template_only(df):
            continue
        validated, issues = validate_table(df, spec.table_key, config)
        write_csv(validated, processed_dir / f"validated_{spec.filename}", index=False)
        issue_rows.extend(issues)

    summary = pd.DataFrame(issue_rows)
    if summary.empty:
        summary = pd.DataFrame(
            [{"table": "all", "severity": "info", "issue_type": "no_issues", "count": 0, "details": ""}]
        )
    write_csv(summary, processed_dir / "validation_summary.csv", index=False)
    return summary
