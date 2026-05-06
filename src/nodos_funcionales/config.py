from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "runtime": {
        "pipeline_mode": "compare",
        "legacy_baseline_enabled": True,
        "report_top_n": 10,
        "literature_support_enabled": False,
    },
    "validation": {
        "allowed_localizations": {
            "extracellular": True,
            "cell_wall": True,
            "outer_membrane": True,
            "periplasm": True,
            "inner_membrane": True,
            "cytoplasm": True,
            "unknown": True,
        },
        "duplicate_policy": "keep_first",
        "strict_ranges": True,
    },
    "thresholds": {
        "min_score": 0.0,
        "top_n": 10,
        "evalue_significance": 1.0e-10,
    },
    "mapping": {
        "unknown_gene_symbol": "unknown",
        "mapping_confidence_default": 1.0,
    },
    "layer_resolution": {
        "default_strategy": "user_preferred",
        "user_data_dir": "data_user",
        "cache_data_dir": "data_cache",
        "external_data_dir": "data_external",
        "manifest_filename": "layer_resolution_manifest.json",
        "write_cache_from_external": True,
        "proxy_confidence_default": 0.20,
        "default_confidence_by_source": {
            "user": 0.95,
            "cache": 0.80,
            "raw": 0.75,
            "external": 0.70,
            "proxy": 0.20,
        },
        "layers": {
            "essentiality": {
                "strategy": "user_preferred",
                "external_provider": "curated_online_examples",
            },
            "virulence": {
                "strategy": "user_preferred",
                "external_provider": "curated_online_examples",
            },
            "human_homologs": {
                "strategy": "user_preferred",
                "external_provider": "uniprot_human_gene_lookup",
                "fallback_provider": "configurable_stub",
            },
            "localization": {
                "strategy": "user_preferred",
                "external_provider": "curated_online_examples",
            },
            "host_annotation": {
                "strategy": "user_preferred",
                "external_provider": "interpro_domain_overlap",
            },
            "strain_conservation": {
                "strategy": "user_preferred",
                "external_provider": "bvbrc_real",
            },
            "functional_network": {
                "strategy": "external_preferred",
                "external_provider": "string_real",
            },
            "clinical_impact": {
                "strategy": "user_preferred",
                "external_provider": "controlled_therapeutic_context_v2",
                "proxy_name": "scoring_proxy_default",
            },
            "curated_disease_context": {
                "strategy": "user_preferred",
                "external_provider": "controlled_therapeutic_context_v2",
                "proxy_name": "scoring_proxy_default",
            },
            "therapy_site_context": {
                "strategy": "user_preferred",
                "external_provider": "controlled_therapeutic_context_v2",
                "proxy_name": "scoring_proxy_default",
            },
            "literature_support": {
                "strategy": "external_preferred",
                "external_provider": "curated_online_examples",
            },
        },
    },
    "taxonomy": {
        "resolution_mode_default": "cache_first",
        "cache_filename": "taxon_resolution_cache.json",
        "external_api_enabled": True,
        "provider_name": "ncbi_eutils",
        "provider_base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        "provider_docs_url": "https://www.ncbi.nlm.nih.gov/home/develop/api/",
        "provider_timeout_seconds": 10,
        "provider_max_retries": 1,
        "provider_backoff_seconds": 1.0,
        "provider_user_agent": "nodos-funcionales-taxonomy/1.0 (offline-safe; contact=local-workspace)",
        "write_cache_by_default": True,
        "legacy_mode_aliases": {
            "local": "offline_only",
        },
        "accepted_resolution_modes": {
            "offline_only": True,
            "cache_first": True,
            "online_optional": True,
            "api_stub": True,
            "auto": True,
            "local": True,
        },
        "source_priority": {
            "cache": 1,
            "local_catalog": 2,
            "api_real": 3,
            "api_stub": 4,
        },
        "external_api_notes": "Integracion online opcional via API publica de NCBI E-utilities con degradacion offline segura.",
    },
    "online_sources": {
        "default_source": "string",
        "source_mode_default": "cache_first",
        "accepted_modes": {
            "offline_only": True,
            "cache_first": True,
            "online_optional": True,
        },
        "write_cache_by_default": True,
        "string": {
            "enabled": True,
            "provider_name": "string_db",
            "provider_base_url": "https://string-db.org/api",
            "provider_docs_url": "https://string-db.org/help/api/",
            "provider_timeout_seconds": 15,
            "provider_max_retries": 1,
            "provider_backoff_seconds": 1.0,
            "provider_user_agent": "nodos-funcionales-string/1.0 (offline-safe; contact=local-workspace)",
            "cache_filename": "string_network_cache.json",
            "required_score": 400,
            "network_type": "functional",
            "network_flavor": "confidence",
            "database_label": "computed_string_api_v1",
            "allow_replace_demo_dataset": True,
        },
        "deg": {
            "enabled": True,
            "provider_name": "deg_real",
            "provider_base_url": "https://tubic.org/deg/public/index.php",
            "provider_timeout_seconds": 15,
            "provider_max_retries": 1,
            "provider_backoff_seconds": 1.0,
            "provider_user_agent": "nodos-funcionales-deg/1.0 (offline-safe; contact=local-workspace)",
            "cache_filename": "deg_essentiality_cache.json",
            "database_label": "deg_real_v1",
            "confidence_real": 0.85,
            "confidence_stub_fallback": 0.40,
        },
        "vfdb": {
            "enabled": True,
            "provider_name": "vfdb_real",
            "provider_base_url": "http://www.mgc.ac.cn/VFs/Down",
            "provider_timeout_seconds": 20,
            "provider_max_retries": 1,
            "provider_backoff_seconds": 1.0,
            "provider_user_agent": "nodos-funcionales-vfdb/1.0 (offline-safe; contact=local-workspace)",
            "cache_filename": "vfdb_virulence_cache.json",
            "database_label": "vfdb_real_v1",
            "confidence_real": 0.82,
            "confidence_stub_fallback": 0.40,
        },
        "bvbrc": {
            "enabled": True,
            "provider_name": "bvbrc_real",
            "provider_base_url": "https://www.bv-brc.org/api",
            "provider_timeout_seconds": 20,
            "provider_max_retries": 1,
            "provider_backoff_seconds": 1.0,
            "provider_user_agent": "nodos-funcionales-bvbrc/1.0 (offline-safe; contact=local-workspace)",
            "cache_filename": "bvbrc_conservation_cache.json",
            "database_label": "bvbrc_real_v1",
            "confidence_real": 0.80,
            "confidence_stub_fallback": 0.35,
        },
        "uniprot": {
            "enabled": True,
            "provider_name": "uniprot_rest",
            "provider_base_url": "https://rest.uniprot.org/uniprotkb/search",
            "provider_docs_url": "https://www.uniprot.org/help/api_queries",
            "provider_timeout_seconds": 15,
            "provider_max_retries": 1,
            "provider_backoff_seconds": 1.0,
            "provider_user_agent": "nodos-funcionales-uniprot/1.0 (offline-safe; contact=local-workspace)",
            "cache_filename": "uniprot_annotation_cache.json",
            "database_label": "computed_uniprot_api_v1",
            "max_results_per_query": 5,
            "fields": "accession,id,protein_name,gene_names,reviewed,annotation_score,organism_name,cc_subcellular_location",
        },
            "human_homologs_lookup": {
                "enabled": True,
                "provider_name": "uniprot_human_gene_lookup",
            "provider_base_url": "https://rest.uniprot.org/uniprotkb/search",
            "provider_docs_url": "https://www.uniprot.org/help/api_queries",
            "provider_timeout_seconds": 15,
            "provider_max_retries": 1,
            "provider_backoff_seconds": 1.0,
            "provider_user_agent": "nodos-funcionales-human-homologs/1.0 (offline-safe; contact=local-workspace)",
            "database_label": "computed_uniprot_human_gene_lookup_v1",
            "human_taxon_id": "9606",
            "max_results_per_query": 5,
            "fields": "accession,id,protein_name,gene_names,reviewed,organism_name",
            "confidence_real_partial": 0.60,
                "confidence_hybrid": 0.55,
                "confidence_stub_fallback": 0.40,
                "confidence_local_orthology": 0.82,
                "local_orthology_enabled": True,
                "local_orthology_filename": "data_external/human_homologs_orthology.csv",
                "local_orthology_database_label": "local_reproducible_orthology_v1",
                "local_orthology_min_confidence": 0.60,
            },
            "host_annotation": {
                "enabled": True,
                "provider_name": "controlled_host_annotation_v1",
                "database_label": "computed_host_annotation_from_homology_v1",
                "confidence_controlled": 0.58,
                "notes": "Deterministic host annotation derived from the resolved human_homologs layer; not experimental domain evidence.",
            },
            "interpro": {
                "enabled": True,
                "provider_name": "interpro_domain_overlap",
                "provider_base_url": "https://www.ebi.ac.uk/interpro/api",
                "provider_docs_url": "https://interpro-documentation.readthedocs.io/en/latest/download.html",
                "provider_timeout_seconds": 20,
                "provider_max_retries": 1,
                "provider_backoff_seconds": 1.0,
                "provider_user_agent": "nodos-funcionales-interpro/1.0 (offline-safe; contact=local-workspace)",
                "cache_filename": "interpro_host_annotation_cache.json",
                "database_label": "computed_interpro_domain_overlap_v1",
                "page_size": 200,
                "confidence_real": 0.72,
                "confidence_controlled_fallback": 0.56,
            },
            "human_essentiality": {
                "enabled": True,
                "provider_name": "biosnap_human_essentiality",
                "provider_download_url": "https://snap.stanford.edu/biodata/datasets/10033/files/G-HumanEssential.tsv.gz",
                "provider_docs_url": "https://snap.stanford.edu/biodata/datasets/10033/10033-G-HumanEssential.html",
                "ncbi_gene_api_url": "https://clinicaltables.nlm.nih.gov/api/ncbi_genes/v3/search",
                "provider_timeout_seconds": 20,
                "provider_max_retries": 1,
                "provider_backoff_seconds": 1.0,
                "provider_user_agent": "nodos-funcionales-human-essentiality/1.0 (offline-safe; contact=local-workspace)",
                "cache_filename": "human_essentiality_cache.json",
                "criticality_weight": 0.20,
            },
            "therapeutic_context": {
                "enabled": True,
            "provider_name": "controlled_therapeutic_context_v1",
            "database_label": "computed_controlled_therapeutic_context_v1",
            "confidence_controlled": 0.62,
            "notes": "Deterministic semicurated therapeutic context derived from resolved workspace layers; not experimental evidence.",
        },
        "therapeutic_context_v2": {
            "enabled": True,
            "provider_name": "controlled_therapeutic_context_v2",
            "database_label": "computed_controlled_therapeutic_context_v2",
            "confidence_controlled": 0.66,
            "notes": "Deterministic semantic v2 therapeutic context with separated clinical impact, disease context, and access logic.",
        },
        "curated_therapeutic_catalogs": {
            "enabled": True,
            "base_dir": "data_external/curated_catalogs",
            "clinical_impact_catalog_dir": "clinical_impact",
            "therapy_site_context_catalog_dir": "therapy_site_context",
            "literature_support_catalog_dir": "literature_support",
            "essentiality_catalog_dir": "essentiality",
            "virulence_catalog_dir": "virulence",
            "localization_catalog_dir": "localization",
            "confidence_clinical_impact_catalog": 0.86,
            "confidence_disease_site_context": 0.84,
            "confidence_literature_support_catalog": 0.92,
            "confidence_curated_layer_catalog": 0.90,
            "default_disease_context": "not_reported",
            "default_infection_site": "not_reported",
            "notes": "Optional offline curated CSV catalogs. They are read before the controlled therapeutic provider and still pass through layer resolution.",
        },
    },
    "provenance": {
        "default_quality_by_type": {
            "demo": 0.45,
            "computed": 0.70,
            "literature": 0.85,
            "curated": 0.90,
            "experimental": 1.0,
            "controlled": 0.58,
            "unknown": 0.50,
        },
        "database_type_overrides": {
            "example_curated_demo": "demo",
            "computed_controlled_therapeutic_context_v1": "controlled",
            "computed_controlled_therapeutic_context_v2": "controlled",
            "computed_host_annotation_from_homology_v1": "controlled",
        },
        "database_prefix_types": {
            "example_": "demo",
            "demo_": "demo",
            "lit_": "literature",
            "curated_": "curated",
            "exp_": "experimental",
            "computed_": "computed",
        },
        "confidence_influence": 0.10,
        "confidence_source_classes": {
            "user": {"tier": "user_validated", "quality": 0.95},
            "curated": {"tier": "curated_literature_or_catalog", "quality": 0.86},
            "literature": {"tier": "curated_literature_or_catalog", "quality": 0.85},
            "experimental": {"tier": "external_real_stable", "quality": 0.90},
            "computed": {"tier": "external_or_computed", "quality": 0.70},
            "controlled": {"tier": "controlled_provider_moderate", "quality": 0.58},
            "proxy": {"tier": "proxy_low", "quality": 0.20},
            "unknown": {"tier": "unknown", "quality": 0.50},
        },
    },
    "localization": {
        "physical_accessibility": {
            "extracellular": 1.0,
            "cell_wall": 0.9,
            "outer_membrane": 0.85,
            "periplasm": 0.65,
            "inner_membrane": 0.55,
            "cytoplasm": 0.30,
            "unknown": 0.20,
        },
        "small_molecule_feasibility": {
            "extracellular": 0.45,
            "cell_wall": 0.60,
            "outer_membrane": 0.55,
            "periplasm": 0.75,
            "inner_membrane": 0.70,
            "cytoplasm": 0.80,
            "unknown": 0.50,
        },
        "antibody_feasibility": {
            "extracellular": 1.0,
            "cell_wall": 0.95,
            "outer_membrane": 0.90,
            "periplasm": 0.35,
            "inner_membrane": 0.25,
            "cytoplasm": 0.05,
            "unknown": 0.20,
        },
        "membrane_crossing_penalty": {
            "extracellular": 0.05,
            "cell_wall": 0.10,
            "outer_membrane": 0.15,
            "periplasm": 0.30,
            "inner_membrane": 0.45,
            "cytoplasm": 0.55,
            "unknown": 0.35,
        },
        "infection_site_access": {
            "extracellular": 0.95,
            "cell_wall": 0.90,
            "outer_membrane": 0.85,
            "periplasm": 0.55,
            "inner_membrane": 0.35,
            "cytoplasm": 0.20,
            "unknown": 0.40,
        },
    },
    "imputation": {
        "neutral_unknown_score": 0.50,
        "placeholder_defaults": {
            "network_centrality": 0.50,
            "pathway_bottleneck_score": 0.50,
            "redundancy_penalty": 0.50,
            "functional_dependency_score": 0.50,
            "core_genome_presence": 0.50,
            "strain_coverage_score": 0.50,
            "allelic_conservation": 0.50,
            "variant_burden": 0.50,
        },
    },
    "weights": {
        "legacy": {
            "essentiality": 0.30,
            "virulence": 0.25,
            "no_human_homolog": 0.25,
            "accessibility": 0.15,
            "host_risk": 0.05,
        },
        "antibiotic_target": {
            "essentiality_support": 0.28,
            "host_safety_score": 0.22,
            "conservation_score": 0.18,
            "small_molecule_feasibility": 0.16,
            "low_redundancy_score": 0.10,
            "evidence_confidence_score": 0.06,
        },
        "antivirulence_target": {
            "virulence_support": 0.30,
            "physical_accessibility": 0.18,
            "antibody_feasibility": 0.12,
            "host_damage_reduction_potential": 0.16,
            "host_safety_score": 0.18,
            "evidence_confidence_score": 0.06,
        },
        "functional_node": {
            "network_centrality": 0.26,
            "pathway_bottleneck_score": 0.24,
            "functional_dependency_score": 0.24,
            "low_redundancy_score": 0.18,
            "evidence_confidence_score": 0.08,
        },
        "meta_priority": {
            "antibiotic_target_score": 0.50,
            "antivirulence_target_score": 0.35,
            "functional_node_score": 0.15,
        },
    },
    "therapeutic_phase1": {
        "priority_weights": {
            "meta_priority_score": 0.35,
            "host_safety_score": 0.20,
            "host_damage_score": 0.15,
            "infection_site_access_score": 0.15,
            "infection_context_score": 0.15,
        },
        "classification_thresholds": {
            "high_essentiality": 0.70,
            "high_virulence": 0.70,
            "good_access": 0.65,
            "acceptable_access": 0.50,
            "critical_access_floor": 0.20,
            "low_host_risk": 0.65,
            "host_safety_floor": 0.45,
            "strong_functional": 0.60,
            "high_context": 0.60,
            "high_damage": 0.60,
            "mixed_strategy_min_score": 0.60,
            "strong_bactericidal_priority": 0.50,
            "mixed_margin_max": 0.12,
            "minimum_priority": 0.45,
            "minimum_confidence": 0.45,
            "minimum_coverage": 0.50,
        },
    },
    "evolutionary_escape_risk": {
        "enabled": True,
        "minimum_available_variables": 3,
        "penalty_weight": 0.15,
        "apply_to_meta_priority": False,
        "weights": {
            "mutation_tolerance_score": 0.20,
            "functional_redundancy_escape_score": 0.15,
            "compensatory_pathway_score": 0.15,
            "resistance_emergence_risk": 0.20,
            "inverse_fitness_cost_of_escape": 0.10,
            "inverse_evolutionary_constraint_score": 0.10,
            "inverse_multi_node_dependency_score": 0.10,
        },
        "reduced_space_weights": {
            "evolutionary_constraint_score": 0.25,
            "fitness_cost_of_escape": 0.25,
            "multi_node_dependency_score": 0.20,
            "inverse_functional_redundancy_escape_score": 0.15,
            "inverse_compensatory_pathway_score": 0.15,
        },
    },
    "sensitivity": {
        "enabled": True,
        "top_n": 5,
        "scenarios": {
            "baseline_like": {
                "meta_priority": {
                    "antibiotic_target_score": 0.55,
                    "antivirulence_target_score": 0.25,
                    "functional_node_score": 0.20,
                }
            },
            "antivirulence_focus": {
                "meta_priority": {
                    "antibiotic_target_score": 0.25,
                    "antivirulence_target_score": 0.55,
                    "functional_node_score": 0.20,
                }
            },
            "network_focus": {
                "meta_priority": {
                    "antibiotic_target_score": 0.25,
                    "antivirulence_target_score": 0.20,
                    "functional_node_score": 0.55,
                }
            },
        },
        "strategy_scenarios": {
            "antibiotic_target": {
                "safety_first": {
                    "essentiality_support": 0.22,
                    "host_safety_score": 0.30,
                    "conservation_score": 0.20,
                    "small_molecule_feasibility": 0.12,
                    "low_redundancy_score": 0.08,
                    "evidence_confidence_score": 0.08,
                },
                "penetration_first": {
                    "essentiality_support": 0.24,
                    "host_safety_score": 0.20,
                    "conservation_score": 0.14,
                    "small_molecule_feasibility": 0.24,
                    "low_redundancy_score": 0.10,
                    "evidence_confidence_score": 0.08,
                },
            },
            "antivirulence_target": {
                "accessibility_first": {
                    "virulence_support": 0.26,
                    "physical_accessibility": 0.24,
                    "antibody_feasibility": 0.16,
                    "host_damage_reduction_potential": 0.14,
                    "host_safety_score": 0.14,
                    "evidence_confidence_score": 0.06,
                },
                "damage_reduction_first": {
                    "virulence_support": 0.24,
                    "physical_accessibility": 0.14,
                    "antibody_feasibility": 0.10,
                    "host_damage_reduction_potential": 0.24,
                    "host_safety_score": 0.20,
                    "evidence_confidence_score": 0.08,
                },
            },
            "functional_node": {
                "centrality_first": {
                    "network_centrality": 0.34,
                    "pathway_bottleneck_score": 0.22,
                    "functional_dependency_score": 0.20,
                    "low_redundancy_score": 0.16,
                    "evidence_confidence_score": 0.08,
                },
                "dependency_first": {
                    "network_centrality": 0.18,
                    "pathway_bottleneck_score": 0.20,
                    "functional_dependency_score": 0.34,
                    "low_redundancy_score": 0.20,
                    "evidence_confidence_score": 0.08,
                },
            },
        },
        "therapeutic_priority_scenarios": {
            "safety_first": {
                "meta_priority_score": 0.25,
                "host_safety_score": 0.35,
                "host_damage_score": 0.10,
                "infection_site_access_score": 0.15,
                "infection_context_score": 0.15,
            },
            "context_first": {
                "meta_priority_score": 0.20,
                "host_safety_score": 0.15,
                "host_damage_score": 0.20,
                "infection_site_access_score": 0.20,
                "infection_context_score": 0.25,
            },
            "bactericidal_first": {
                "meta_priority_score": 0.45,
                "host_safety_score": 0.20,
                "host_damage_score": 0.05,
                "infection_site_access_score": 0.20,
                "infection_context_score": 0.10,
            },
            "damage_control_first": {
                "meta_priority_score": 0.10,
                "host_safety_score": 0.20,
                "host_damage_score": 0.35,
                "infection_site_access_score": 0.15,
                "infection_context_score": 0.20,
            },
        },
    },
    "dataset_import": {
        "required_common_columns": {
            "protein_id": ["protein_id", "protein", "locus_tag", "gene_id", "feature_id"],
            "gene": ["gene", "gene_name", "symbol", "preferred_name"],
            "database": ["database", "source_database", "source", "provenance"],
        },
        "dataset_column_aliases": {
            "essentiality": {
                "essential": ["essential", "is_essential", "essentiality_flag"],
                "evidence": ["evidence", "evidence_note", "comment"],
            },
            "virulence": {
                "virulence_score": ["virulence_score", "score", "virulence"],
                "virulence_factor": ["virulence_factor", "is_virulence_factor", "vf_flag"],
            },
            "human_homologs": {
                "human_homolog": ["human_homolog", "has_human_homolog", "homolog_flag"],
                "evalue": ["evalue", "blast_evalue", "best_evalue"],
                "human_gene": ["human_gene", "host_gene", "human_symbol"],
            },
            "localization": {
                "localization": ["localization", "localisation", "subcellular_location"],
            },
            "strain_conservation": {
                "core_genome_presence": ["core_genome_presence", "core_presence"],
                "strain_coverage_score": ["strain_coverage_score", "coverage_score"],
                "allelic_conservation": ["allelic_conservation", "allele_conservation"],
                "variant_burden": ["variant_burden", "variation_burden"],
            },
            "functional_network": {
                "network_centrality": ["network_centrality", "centrality"],
                "pathway_bottleneck_score": ["pathway_bottleneck_score", "bottleneck_score"],
                "redundancy_penalty": ["redundancy_penalty", "redundancy"],
                "functional_dependency_score": ["functional_dependency_score", "dependency_score"],
            },
            "host_annotation": {
                "domain_overlap_score": ["domain_overlap_score", "domain_overlap"],
                "host_criticality_penalty": ["host_criticality_penalty", "host_criticality"],
            },
            "clinical_impact": {
                "host_damage_reduction_potential": ["host_damage_reduction_potential", "damage_reduction_potential"],
                "disease_severity_association": ["disease_severity_association", "severity_association"],
                "clinical_impact_score": ["clinical_impact_score", "impact_score"],
                "host_damage_score": ["host_damage_score", "damage_score"],
            },
            "curated_disease_context": {
                "infection_context_score": ["infection_context_score", "disease_context_score", "context_score"],
            },
            "therapy_site_context": {
                "infection_site_access": ["infection_site_access", "infection_site_access_score", "site_access_score"],
                "infection_site": ["infection_site", "site_of_infection", "anatomical_site"],
                "access_evidence_type": ["access_evidence_type", "evidence_type", "accessibility_evidence_type"],
                "access_evidence_reference": ["access_evidence_reference", "reference", "citation", "doi_or_url"],
                "access_evidence_note": ["access_evidence_note", "notes", "comment"],
            },
            "literature_support": {
                "literature_support_score": ["literature_support_score", "literature_score", "support_score"],
                "evidence_type": ["evidence_type", "literature_evidence_type"],
                "reference": ["reference", "citation", "source_reference"],
                "doi_or_url": ["doi_or_url", "doi", "url"],
                "notes": ["notes", "comment"],
                "source_quality": ["source_quality", "literature_source_quality"],
            },
            "evolutionary_escape_risk": {
                "mutation_tolerance_score": ["mutation_tolerance_score", "mutational_tolerance_score"],
                "functional_redundancy_escape_score": ["functional_redundancy_escape_score", "redundancy_escape_score"],
                "compensatory_pathway_score": ["compensatory_pathway_score", "alternative_pathway_score"],
                "fitness_cost_of_escape": ["fitness_cost_of_escape", "fitness_cost_score"],
                "evolutionary_constraint_score": ["evolutionary_constraint_score", "evolutionary_space_constraint_score"],
                "resistance_emergence_risk": ["resistance_emergence_risk", "resistance_risk"],
                "multi_node_dependency_score": ["multi_node_dependency_score", "functional_dependency_score"],
                "evidence_source": ["evidence_source", "reference", "citation"],
            },
        },
    },
}


def _parse_scalar(raw_value: str) -> Any:
    value = raw_value.strip()
    if value == "":
        return {}

    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None

    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        return value[1:-1]

    try:
        if any(token in value for token in [".", "e", "E"]):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _strip_comment(line: str) -> str:
    if "#" not in line:
        return line.rstrip("\n")
    content, _, _ = line.partition("#")
    return content.rstrip()


def parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        line = _strip_comment(raw_line)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if ":" not in stripped:
            raise ValueError(f"Línea YAML no soportada: {raw_line}")

        key, value = stripped.split(":", 1)
        key = key.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]

        parsed = _parse_scalar(value)
        if parsed == {} and value.strip() == "":
            current[key] = {}
            stack.append((indent, current[key]))
        else:
            current[key] = parsed

    return root


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    user_config = parse_simple_yaml(path.read_text(encoding="utf-8"))
    return _deep_merge(DEFAULT_CONFIG, user_config)
