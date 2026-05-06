import sys
from pathlib import Path

configfile: "config/params.yaml"

PYTHON_CMD = f'"{sys.executable}"'
BASE_DIR = Path(workflow.basedir)
OPTIONAL_RAW_FILES = [
    "data_raw/strain_conservation.csv",
    "data_raw/functional_network.csv",
    "data_raw/host_annotation.csv",
]


def existing_optional(paths):
    return [path for path in paths if (BASE_DIR / path).exists()]


rule all:
    input:
        "results/ranking_nodos.csv",
        "results/ranking_nodos_legacy.csv",
        "results/phase_comparison.csv",
        "results/sensitivity_analysis.csv",
        "results/report_phase2.md",
        "results/data_provenance_summary.csv",
        "results/candidate_audit.csv",
        "results/candidate_audit.md",
        "results/top10_candidate_review.csv",
        "results/top10_candidate_review.md",


rule load_and_validate:
    input:
        "data_raw/essentiality.csv",
        "data_raw/virulence.csv",
        "data_raw/human_homologs.csv",
        "data_raw/localization.csv",
        *existing_optional(OPTIONAL_RAW_FILES),
    output:
        "data_processed/validated_essentiality.csv",
        "data_processed/validated_virulence.csv",
        "data_processed/validated_human_homologs.csv",
        "data_processed/validated_localization.csv",
        "data_processed/validation_summary.csv",
        *existing_optional(
            [
                "data_processed/validated_strain_conservation.csv",
                "data_processed/validated_functional_network.csv",
                "data_processed/validated_host_annotation.csv",
            ]
        ),
    shell:
        f"{PYTHON_CMD} scripts/01_load_and_validate.py"


rule normalize_ids:
    input:
        "data_processed/validated_essentiality.csv",
        "data_processed/validated_virulence.csv",
        "data_processed/validated_human_homologs.csv",
        "data_processed/validated_localization.csv",
        *existing_optional(
            [
                "data_processed/validated_strain_conservation.csv",
                "data_processed/validated_functional_network.csv",
                "data_processed/validated_host_annotation.csv",
            ]
        ),
    output:
        "data_processed/normalized_essentiality.csv",
        "data_processed/normalized_virulence.csv",
        "data_processed/normalized_human_homologs.csv",
        "data_processed/normalized_localization.csv",
        *existing_optional(
            [
                "data_processed/normalized_strain_conservation.csv",
                "data_processed/normalized_functional_network.csv",
                "data_processed/normalized_host_annotation.csv",
            ]
        ),
    shell:
        f"{PYTHON_CMD} scripts/02_normalize_ids.py"


rule integrate_data:
    input:
        "data_processed/normalized_essentiality.csv",
        "data_processed/normalized_virulence.csv",
        "data_processed/normalized_human_homologs.csv",
        "data_processed/normalized_localization.csv",
        *existing_optional(
            [
                "data_processed/normalized_strain_conservation.csv",
                "data_processed/normalized_functional_network.csv",
                "data_processed/normalized_host_annotation.csv",
            ]
        ),
    output:
        "data_processed/integrated_nodes.csv",
    shell:
        f"{PYTHON_CMD} scripts/03_integrate_data.py"


rule score_nodes:
    input:
        "data_processed/integrated_nodes.csv",
        "config/params.yaml",
    output:
        "data_processed/phase2_features.csv",
        "data_processed/scored_nodes.csv",
        "results/sensitivity_analysis.csv",
    shell:
        f"{PYTHON_CMD} scripts/04_score_nodes.py"


rule export_ranking:
    input:
        "data_processed/phase2_features.csv",
        "data_processed/scored_nodes.csv",
        "results/sensitivity_analysis.csv",
        "config/params.yaml",
    output:
        "results/ranking_nodos.csv",
        "results/ranking_nodos_legacy.csv",
        "results/phase_comparison.csv",
        "results/report_phase2.md",
        "results/data_provenance_summary.csv",
        "results/candidate_audit.csv",
        "results/candidate_audit.md",
        "results/top10_candidate_review.csv",
        "results/top10_candidate_review.md",
    shell:
        f"{PYTHON_CMD} scripts/05_export_ranking.py"
