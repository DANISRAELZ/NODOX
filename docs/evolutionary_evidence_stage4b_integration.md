# Stage 4B — integration of explicit evolutionary evidence into scoring

## Purpose

Stage 4B connects the strict evolutionary evidence contract introduced in Stage 4A to the evolutionary escape-risk scoring path.

The scientific objective is to preserve two clearly separated products:

1. **Proxy evolutionary score** — the historical hypothesis-generating calculation based on direct inputs and derived biological layers.
2. **Evidence-supported evolutionary score** — a score that is evaluable only when explicit evolutionary observations pass the Stage 4A evidence contract.

A missing or unresolved observation is never converted into low evolutionary risk.

## Core rule

A numeric value, an `_is_explicit=True` flag, or an unrecognized source label is not sufficient to create evidence-supported scoring.

For a variable to count as explicit evidence, the flattened scoring input must be convertible into an `EvolutionaryEvidenceRecord` accepted by `validate_evidence_record()`.

The standard Stage 4B gate requires:

- at least 3 contract-valid explicit evolutionary variables; and
- at least 2 independent evidence groups.

Both thresholds are configurable, but the defaults mirror the Stage 4A contract.

## Flattened scoring metadata

For each evolutionary variable `<variable>`, Stage 4B recognizes the value column plus the following metadata columns:

- `<variable>_is_explicit`
- `<variable>_source_type`
- `<variable>_source_database`
- `<variable>_source_record`
- `<variable>_source_version`
- `<variable>_retrieved_at`
- `<variable>_mapping_method`
- `<variable>_mapping_status`
- `<variable>_evidence_status`
- `<variable>_evidence_confidence`
- `<variable>_independence_group`
- `<variable>_method_scope`
- `<variable>_taxon_id`
- `<variable>_notes`

Candidate identity is resolved from existing candidate columns such as `candidate_id`, `protein_id`, `accession`, `uniprot_accession`, `entry`, or `locus_tag`.

`mutational_tolerance_score` remains accepted as an alias for `mutation_tolerance_score`.

## Supported evidence semantics

The Stage 4A validator remains the single authority for whether a record is eligible as explicit evidence.

Consequently:

- unknown source types are not explicit;
- derived, proxy, demo, placeholder, unresolved, and missing source types are not explicit;
- ambiguous or unmapped records are not explicit;
- family or ortholog mapping is supporting rather than direct evidence by default;
- `not_detected_with_method` requires an explicit method scope;
- incomplete provenance can remain visible for audit but cannot enable the supported score.

## Independence requirement

Multiple variables derived from the same biological dataset do not automatically represent independent evidence.

Example:

- `mutation_tolerance_score` from dataset A
- `evolutionary_constraint_score` from dataset A
- `fitness_cost_of_escape` from dataset A

This may produce three contract-valid variables but only one independence group. With the default Stage 4B gate the candidate therefore remains **not supported**.

A candidate with three eligible variables distributed across at least two independent groups can become evidence-supported.

## Scoring behavior

### Proxy path

The historical proxy formula and historical alias are preserved:

- `evolutionary_escape_risk_score`
- `evolutionary_escape_proxy_score`

Direct numeric inputs may still influence the proxy calculation even when their provenance is insufficient for explicit evidence.

This preserves backward comparability of the hypothesis-generating layer.

### Supported path

Only values whose records pass the Stage 4A contract enter `evolutionary_escape_supported_score`.

The supported score remains `NaN` when the full contract gate is not satisfied. Its supported penalty is therefore zero in that case, and missing evidence is not interpreted as biological protection.

## Audit outputs

Stage 4B adds or standardizes the following diagnostics in the evolutionary-risk result:

- `evolutionary_escape_risk_explicit_variable_count`
- `evolutionary_escape_risk_independent_evidence_group_count`
- `evolutionary_escape_risk_explicit_variables`
- `evolutionary_escape_risk_independence_groups`
- `evolutionary_evidence_contract_supported`
- `evolutionary_evidence_contract_record_count`
- `evolutionary_evidence_contract_valid_record_count`
- `evolutionary_evidence_contract_explicit_record_count`
- `evolutionary_evidence_contract_rejected_explicit_record_count`
- `evolutionary_evidence_contract_errors`
- `evolutionary_evidence_contract_warnings`

Each evolutionary variable also receives a `<variable>_contract_explicit` boolean in the scoring result.

## Scientific guardrails

Stage 4B does not:

- claim prospective resistance prediction;
- treat absence of evidence as low escape risk;
- make STRING, DEG, VFDB, UniProt, DIAMOND, or BV-BRC evidence automatically evolutionary;
- change Functional Node Theory weights;
- change the historical proxy formula;
- make the supported evolutionary penalty the default main ranking penalty.

External providers must be integrated separately and must produce candidate-level provenance that passes the same contract.

## Regression expectations

The Stage 4B regression suite must verify at least the following cases:

1. proxy-only inputs never generate a supported penalty;
2. numeric values without complete provenance are not explicit evidence;
3. `_is_explicit=True` alone is insufficient;
4. three valid variables from two independent groups can enable supported scoring;
5. three valid variables from one group cannot enable supported scoring;
6. unknown source types are rejected as explicit;
7. ambiguous mapping is rejected as explicit;
8. the historical proxy alias remains numerically unchanged.

The full repository test suite remains required before merging the Stage 4B pull request.
