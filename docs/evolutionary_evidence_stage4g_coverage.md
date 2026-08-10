# Stage 4G — End-to-end evolutionary evidence coverage

## Purpose

Stage 4G reports how much evolutionary evidence is available for every NODOX candidate. It does not change Functional Node Theory weights, evolutionary-risk formulas, candidate scores, or ranking.

The report separates three scientifically different states:

1. contract-explicit quantitative evidence;
2. proxy or derived values used only for exploratory calculations;
3. qualitative or quantitative literature that remains outside scoring.

Missing evidence is never interpreted as low evolutionary risk.

## Canonical variables

Coverage is evaluated against the seven variables already defined by the Stage 4A contract:

- `mutation_tolerance_score`
- `functional_redundancy_escape_score`
- `compensatory_pathway_score`
- `fitness_cost_of_escape`
- `evolutionary_constraint_score`
- `resistance_emergence_risk`
- `multi_node_dependency_score`

The explicit-variable count is the number of distinct variables whose `<variable>_contract_explicit` field is true. Multiple mutations, studies, observations, or assay conditions for the same variable do not increase this count.

## Support gate

The default Stage 4A/4B requirements remain unchanged:

```text
minimum explicit variables = 3
minimum independent evidence groups = 2
```

Stage 4G reports both conditions separately:

- `meets_explicit_variable_threshold`
- `meets_independence_threshold`
- `evolutionary_evidence_contract_supported`

Three variables from one correlated evidence group meet the coverage threshold but do not enable the evidence-supported score.

## Evidence and scoring semantics

The long-form report distinguishes:

- `variable_scoring_eligible`: the variable passed the Stage 4A contract;
- `candidate_supported_scoring_enabled`: the candidate passed the complete variable and independence gate;
- `affects_proxy_scoring`: the numeric value participates in the exploratory proxy path;
- `affects_supported_scoring`: the contract-explicit variable can participate in the supported path for a fully supported candidate.

Stage 4F screened literature always has:

```text
affects_proxy_scoring = false
affects_supported_scoring = false
```

unless a quantitative record is explicitly curated into the Stage 4E production catalog and subsequently passes the Stage 4A contract through the normal pipeline.

## Outputs

Stage 4G writes:

```text
results/evolutionary_coverage_evidence_records.csv
results/evolutionary_coverage_by_candidate.csv
results/evolutionary_coverage_distribution.csv
results/evolutionary_coverage_manifest.json
results/evolutionary_coverage_report.md
```

### Evidence-record table

`evolutionary_coverage_evidence_records.csv` preserves candidate identity, variable, numeric or qualitative evidence form, source, mapping, confidence, method, literature identifiers, missingness, contract state and scoring eligibility.

It contains one canonical scoring-input row for each candidate and each of the seven variables. Additional Stage 4F literature rows are retained individually so that different mutations and assay contexts are not collapsed.

### Candidate table

`evolutionary_coverage_by_candidate.csv` reports:

- explicit variables and count;
- proxy variables and count;
- quantitative and qualitative evidence availability;
- independent evidence groups;
- missing variables and per-variable missingness reason;
- coverage bin;
- proxy and supported evolutionary scores and penalties already calculated by NODOX;
- complete contract support status.

### Distribution

`evolutionary_coverage_distribution.csv` always contains four rows:

```text
0_explicit_variables
1_explicit_variable
2_explicit_variables
3_or_more_explicit_variables
```

This makes empty categories visible rather than silently omitting them.

## Normalized missingness

Stage 4G recognizes states including:

- `no_experimental_literature_found`
- `literature_found_qualitative_only`
- `numeric_value_not_extractable`
- `mutation_not_mappable_to_candidate`
- `strain_context_mismatch`
- `experimental_condition_mismatch`
- `conflicting_results`
- `quantitative_evidence_available`
- `literature_screening_not_documented_for_candidate`
- `source_mode_disallows_curated_evidence`
- `provider_failed`
- `contract_validation_failed`
- `evidence_not_contract_explicit`

`no_experimental_literature_found` must only be used when a negative literature search is explicitly documented. Absence from the screening catalog is reported conservatively as `literature_screening_not_documented_for_candidate`.

The current PBP1 V374L and N562Y Stage 4F records are classified as `numeric_value_not_extractable`: real qualitative experimental findings exist, but no reusable numeric relative-fitness scalar was recovered.

Context-dependent N562Y findings are not automatically labeled `conflicting_results`. Different results under different osmotic conditions remain separate evidence records with their original assay contexts.

## Mapping behavior

Stage 4F literature currently uses gene and taxon mapping. Stage 4G maps such a record to a candidate only when `gene + taxon_id` identifies exactly one candidate in the feature table.

- one match: `unique_gene_and_taxon`;
- no match: `unmapped_gene_and_taxon`;
- multiple matches: `ambiguous_gene_and_taxon`.

Ambiguous records are retained for audit but are not fanned out across candidates and do not count as explicit evidence.

## Source-mode policy

Stage 4G reuses the Stage 4F screening audit and therefore preserves its source-mode rules:

- curated-compatible modes can report local screened literature;
- `online_strict` and `online_only` disable local Stage 4E/4F evidence;
- the coverage report itself is still generated in strict modes;
- disabled local evidence is reported as unavailable by policy, not as a negative biological result.

## Ablation readiness

The candidate output preserves the identifiers and fields required by `scripts/run_evolutionary_ablation.py`, including proxy and supported evolutionary scores, penalties, explicit-variable counts, independence counts and contract support.

This enables a later comparison of:

```text
ranking without evolutionary information
vs. ranking with proxy evolutionary information
vs. ranking with contract-supported evolutionary evidence
```

Stage 4G does not rerun or redefine the ablation formula.

## Command-line use

```bash
python scripts/report_evolutionary_coverage.py \
  --workspace results/<run>/workspace \
  --online-source-mode hybrid_curated
```

The standard pipeline also generates the Stage 4G outputs during reporting.

## Limitations

- Coverage is evidence availability, not biological validation of a therapeutic target.
- Three explicit variables do not establish prospective resistance prediction.
- Evidence support does not eliminate strain, environment, epistasis, compensation or assay dependence.
- Proxy availability does not imply that the proxy is experimentally validated.
- Qualitative literature is not converted into numeric fitness cost.
- Stage 4G reports existing scores but has no scoring effect of its own.

## Future work

Future evidence curation can add structured strain background, assay-condition matching and sequence-level mutation mapping. Those fields should remain auditable and must not be inferred from free text when the source does not report them explicitly.
