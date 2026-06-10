# Manuscript Tables

These tables are generated in `results/publication_package/` from consolidated local result files. They support manuscript interpretation of computationally prioritized hypotheses and do not represent experimental, pharmacological or clinical confirmation.

## Table 1. Top Candidate Functional Nodes

- Source: `results/publication_package/publication_table_1_top_candidates.csv`
- Main columns: `final_priority_rank`, `gene`, `protein_id`, `therapeutic_role`, `meta_priority_score`, `therapeutic_priority_score`, `evidence_confidence_score`, `functional_node_score`, `evolutionary_escape_risk_score`, `interpretation_warning`.
- Manuscript interpretation: primary ranked view of candidate functional nodes.
- Conservative note: a high rank indicates computational priority, not independent confirmation.

## Table 2. Score Decomposition

- Source: `results/publication_package/publication_table_2_score_decomposition.csv`
- Main columns: `antibiotic_target_score`, `antivirulence_target_score`, `functional_node_score`, `functional_node_theory_score`, `selectivity_score`, `clinical_context_score`, `therapeutic_priority_score`, `evidence_confidence_score`, `evolutionary_escape_risk_score`, `meta_priority_score`.
- Manuscript interpretation: shows how major scoring dimensions contribute to candidate review.
- Conservative note: score decomposition improves interpretability but does not replace biological validation work.

## Table 3. Evolutionary Risk

- Source: `results/publication_package/publication_table_3_evolutionary_risk.csv`
- Main columns: `protein_id`, `gene`, `evolutionary_escape_risk_score`, `evolutionary_escape_penalty_applied`, evolutionary risk confidence and audit fields when available.
- Manuscript interpretation: reports escape, redundancy and compensation concerns alongside priority.
- Conservative note: unknown or insufficient evidence must not be interpreted as low risk.

## Table 4. Sensitivity and Stability

- Source: `results/publication_package/publication_table_4_sensitivity_stability.csv`
- Main columns: `score_name`, `scenario`, `protein_id`, `gene`, `score`, `rank`, `base_rank`, `rank_delta_vs_base`.
- Manuscript interpretation: summarizes how rankings change under configured sensitivity scenarios.
- Conservative note: stability supports internal consistency only; it is not external confirmation.

## Table 5. Evidence Provenance

- Source: `results/publication_package/publication_table_5_evidence_provenance.csv`
- Main columns: `protein_id`, `gene`, evidence strength, evidence coverage, weak and strong evidence flags, data realism and optional data source summaries when available.
- Manuscript interpretation: makes evidence support and limitation labels visible.
- Conservative note: labels such as `demo_only`, `proxy`, `missing`, `not_assessed` and `insufficient_evidence` constrain interpretation.

## Table 6. Baseline Comparison

- Source: `results/publication_package/publication_table_6_baseline_comparison.csv`
- Main columns: `baseline_name`, `gene`, `protein_id`, `nodos_rank`, `baseline_rank`, `rank_delta`, `nodos_meta_priority_score`, `baseline_score`, `therapeutic_role`, `evidence_confidence_score`, `interpretation_note`.
- Manuscript interpretation: compares the integrated Nodos ranking with simple reference rankings.
- Conservative note: rank differences are review prompts, not proof of biological superiority.
