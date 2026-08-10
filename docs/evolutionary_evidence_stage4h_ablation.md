# Stage 4H — Comparative evolutionary ablation

## Purpose

Stage 4H measures how candidate scores and ranks change when evolutionary information is removed, restored through exploratory proxies, or restored only through evidence that passes the Stage 4A contract.

It is a read-only audit. It does not change Functional Node Theory weights, evolutionary-risk formulas, production scores, or the official ranking.

## Scientific question

Stage 4H separates two questions:

1. What is the operational effect of the complete proxy-based evolutionary layer?
2. Among contract-supported candidates, what changes when proxy values are replaced by explicit evidence while keeping the same candidates and evolutionary terms?

The second question cannot be answered by directly comparing the existing full proxy and supported rankings. The full proxy path includes biofilm and horizontal-transfer terms, while the supported path excludes them because they do not have a Stage 4A explicit-evidence contract.

## Scenarios

| Scenario | Evolutionary information | Use |
| --- | --- | --- |
| `no_evolution` | No evolutionary positive dimension or penalty | Reference |
| `proxy_operational` | Current full proxy layer, including biofilm and HGT | Exploratory operational effect |
| `supported_operational` | Evidence-gated escape and explicit constraint terms | Current evidence-backed policy effect |
| `proxy_matched` | Proxy values using only supported candidates and supported terms | Matched reference |
| `supported_matched` | Contract-supported values using the same candidates and terms | Evidence comparison |

No weights are changed. The matched scenarios reuse the existing theory formula and restore only the same configured terms over the existing no-evolution reconstruction.

## Eligibility

A candidate is evaluable in the paired comparison only when all conditions hold:

```text
explicit_variable_count >= 3
independent_evidence_group_count >= 2
evolutionary_evidence_contract_supported = true
supported_evolutionary_dimension_applied = true
comparison scores are finite
Stage 4G and ablation candidate IDs map one-to-one
baseline reconstruction is valid
```

Candidate identity is joined only through exact `candidate_id`. Gene fallback is forbidden because it can fan one evidence record across multiple proteins.

## Non-evaluable states

Examples include:

- `not_evaluable_no_contract_explicit_evidence`
- `not_evaluable_insufficient_explicit_variables`
- `not_evaluable_insufficient_independent_evidence`
- `not_evaluable_contract_not_supported`
- `not_evaluable_nonfinite_comparison_score`
- `not_evaluable_contract_count_mismatch`
- `not_evaluable_contract_state_mismatch`
- `not_evaluable_baseline_reconstruction_failed`

If no candidate is supported, the Stage 4H manifest reports:

```text
analysis_status = not_evaluable_no_supported_candidates
```

The supported effect is unknown in that situation. It is not reported as zero.

One supported candidate permits a paired score difference, but not a rank-correlation analysis. At least two supported candidates are required for paired rank comparisons.

## Global and paired rank effects

The operational supported ranking is evidence-gated across the full cohort. Unsupported candidates retain their no-evolution score, but their global rank can still change when supported candidates move around them. Stage 4H labels this as `indirect_cohort_rank_shift`; it is not attributed to evidence for the unsupported candidate.

The matched comparison recalculates ranks only within the contract-supported subcohort. This avoids treating indirect cohort movement as a candidate-level supported effect.

## Outputs

Stage 4H writes:

```text
evolutionary_ablation_comparison_by_candidate.csv
evolutionary_ablation_comparison_summary.csv
evolutionary_ablation_mapping_audit.csv
evolutionary_ablation_comparison_manifest.json
evolutionary_ablation_comparison_report.md
```

The candidate table preserves Stage 4G coverage, missingness, evidence counts, all scenario scores and ranks, paired deltas, evaluation status, and global-rank attribution.

The mapping audit records missing and duplicate identifiers. Any non-one-to-one mapping blocks the scientific comparison.

## Command-line use

```bash
python scripts/run_evolutionary_ablation_comparison.py \
  --repo-root . \
  --run-dir results/<run> \
  --output-dir results/<run>/evolutionary_ablation_stage4h
```

The run must contain `phase3_features.csv` and the Stage 4G `evolutionary_coverage_by_candidate.csv` output. Older runs without Stage 4G coverage produce a blocked manifest rather than silently reconstructing evidence eligibility.

## Guardrails

- Qualitative Stage 4F findings are not converted to numbers.
- Stage 4F records are not promoted automatically to Stage 4E.
- Missing supported evidence is not replaced by a proxy.
- Missing evidence is not interpreted as low evolutionary risk.
- Biofilm and HGT remain outside the matched supported comparison.
- `online_strict` and `online_only` evidence policy is inherited from the input run; Stage 4H does not load curated evidence independently.
- Stage 4H outputs declare `scoring_effect=false`, `scoring_formula_changed=false`, `theory_weights_changed=false`, and `production_ranking_changed=false`.

## Limitations

- Ablation quantifies model influence; it is not prospective resistance validation.
- Rank shifts depend on cohort composition and should not be compared across different candidate sets without a new audit.
- Small supported cohorts limit rank-based statistics.
- Agreement between proxy and explicit scores does not prove biological validity.
- Disagreement identifies a model-assumption gap but does not establish which estimate is biologically correct.
