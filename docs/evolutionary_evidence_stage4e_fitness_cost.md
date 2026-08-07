# Stage 4E — Experimental fitness cost of evolutionary escape

## Purpose

Stage 4E adds `fitness_cost_of_escape` as a third explicit evolutionary variable without pretending that a universal public fitness-cost database exists. The evidence source is therefore a traceable, organism-specific local catalog of experimentally measured resistance/escape mutants.

This stage does **not** change the Stage 4A evidence contract, the Stage 4B supported-score gate, the Stage 4C BV-BRC transformation, the Stage 4D AMRFinderPlus transformation, or any Functional Node Theory / therapeutic / evolutionary weights.

## Why fitness cost is a separate evolutionary dimension

BV-BRC asks whether a candidate is conserved across genomes/strains. AMRFinderPlus asks whether a documented target-site mutational resistance route exists. Fitness-cost evidence asks a different question: if an escape mutation exists, how costly is that route for the bacterium under a measured assay context?

A resistance mutation with low fitness cost may be easier to maintain than a route with severe biological cost. This is not equivalent to conservation and it is not equivalent to simply knowing that a resistance mutation has been reported.

## Catalog location

The default catalog path is:

```text
data_curated/organisms/<organism>/evolutionary_fitness_cost.csv
```

For example:

```text
data_curated/organisms/helicobacter_pylori/evolutionary_fitness_cost.csv
```

No catalog is bundled as biological truth by Stage 4E. The catalog must be curated from traceable experimental literature or validated user evidence.

## Required schema

Each record must contain:

| Column | Meaning |
| --- | --- |
| `gene` | Candidate gene associated with the measured escape mutation |
| `taxon_id` | Organism taxon ID |
| `mutation` | Specific resistance/escape mutation |
| `escape_association` | Direct relationship between mutation and resistance/escape |
| `relative_fitness` | WT-normalized measured fitness ratio |
| `measurement_type` | Supported relative-fitness measurement class |
| `assay_context` | Experimental context in which fitness was measured |
| `source_type` | `experimental`, `literature_curated`, or `user_curated` |
| `source_database` | Database/publication collection used for provenance |
| `source_record` | Stable record identifier, preferably PMID/DOI-derived |
| `source_version` | Publication/catalog/snapshot version |
| `retrieved_at` | Timezone-aware ISO timestamp for curation/retrieval |
| `mapping_method` | How the record was linked to the candidate |
| `mapping_status` | Direct Stage 4A-compatible mapping status |
| `evidence_status` | Must be `observed` for Stage 4E explicit evidence |
| `evidence_confidence` | `low`, `moderate`, or `high` |
| `method_scope` | What the experiment actually measured |

At least one of `pmid`, `doi`, or `reference` must also be present.

## Accepted semantics

Stage 4E currently accepts WT-normalized relative-fitness ratios such as:

```text
relative_fitness_ratio
competition_relative_fitness_ratio
```

and direct escape associations such as:

```text
direct_resistance_mutation
target_site_resistance_mutation
```

Other measurements are not silently converted. They remain rejected/unresolved until an explicit, validated transformation is added.

## Transformation

For an eligible record:

```text
fitness_cost_of_escape = max(0, min(1, 1 - relative_fitness))
```

Examples:

| Relative fitness | Fitness cost |
| ---: | ---: |
| 0.60 | 0.40 |
| 0.82 | 0.18 |
| 0.95 | 0.05 |
| 1.00 | 0.00 |
| 1.05 | 0.00 |

A measured cost of `0.0` is valid when the experimental ratio indicates no detectable cost or a relative advantage. This is fundamentally different from missing evidence: an absent or rejected record is never converted into zero.

## Multiple escape routes

If several valid mutations are available for the same candidate, Stage 4E selects:

```text
minimum_cost_across_valid_escape_routes
```

This is deliberately conservative for escape-risk analysis. If the bacterium has several documented routes, the least costly measured route is the most permissive known route and therefore the relevant one when asking whether escape space remains available.

The full set of source records remains visible in audit fields and the Stage 4E summary.

## Independence and AMRFinderPlus

A literature study is not automatically independent merely because AMRFinderPlus and the local fitness-cost catalog expose different variables.

If the selected Stage 4E record shares a PMID with AMRFinderPlus evidence already attached to the same candidate, Stage 4E assigns:

```text
ncbi_amrfinderplus_curated_point_mutations
```

as the same independence group used by Stage 4D. This prevents one paper from becoming two independent evidence groups simply because one observation says that a mutation causes resistance and another observation quantifies its fitness cost.

If there is no AMRFinderPlus PMID overlap, the independence group is derived deterministically from the study identifier: PMID first, DOI second, and `source_record` only as a final fallback. A free-text `independence_group` column does not control the contract count. This prevents manual labels from inflating evidence independence. BV-BRC comparative-genomic evidence remains a separate group.

## Contract behavior

The intended three-variable path is now:

```text
BV-BRC
  -> evolutionary_constraint_score

AMRFinderPlus
  -> resistance_emergence_risk

Experimental fitness-cost catalog
  -> fitness_cost_of_escape
```

With all three variables valid, the existing Stage 4A default contract can be satisfied when there are at least two genuinely independent evidence groups.

Example with shared AMRFinder/fitness literature:

```text
evolutionary_constraint_score      group = bvbrc_strain_conservation_taxon_210
resistance_emergence_risk          group = ncbi_amrfinderplus_curated_point_mutations
fitness_cost_of_escape             group = ncbi_amrfinderplus_curated_point_mutations

explicit_variable_count = 3
independent_evidence_group_count = 2
supported_by_contract = True
```

No threshold is lowered to obtain this result.

## Source-mode policy

`online_strict` and its `online_only` alias cannot consume this local curated catalog. In those modes Stage 4E writes a disabled manifest and leaves the candidate frame unchanged.

`hybrid_curated` explicitly permits the catalog with full provenance. Legacy configured modes may also use it according to existing NODOX policy. Setting the global `curated_real_evidence.enabled` flag to false also disables Stage 4E, even if the Stage 4E-specific flag is enabled.

## Fail-closed rules

Stage 4E rejects or leaves unresolved records when any of the following applies:

- gene or taxon does not match the candidate;
- the source type is not explicitly allowed;
- mapping is not direct;
- evidence status is not `observed`;
- confidence is invalid;
- the measurement type has no approved transformation;
- the mutation is not directly associated with resistance/escape;
- assay context or method scope is absent;
- retrieval timestamp is absent or not timezone-aware;
- literature identifier is absent;
- relative fitness is invalid;
- required provenance fields are missing.

Rejected records never create a default biological score.

## Outputs

Stage 4E writes:

```text
results/evolutionary_fitness_cost_manifest.json
results/evolutionary_fitness_cost_summary.csv
```

Candidate-level audit columns include eligibility, rejection counts, selected mutation, selected relative fitness, aggregation rule, source records and the independence decision.

## Interpretation limitations

`fitness_cost_of_escape` is **mutation-, strain-, environment-, and assay-specific**. A value measured for one resistant mutant cannot be generalized to every mutation in the same gene or to every strain of the organism.

A high fitness cost does not prove that resistance cannot evolve: compensation, epistasis, environmental dependence and alternative mutations may change the effective cost. A low measured cost does not prove rapid clinical emergence. Stage 4E records a documented evolutionary constraint dimension; it does not replace experimental evolution, longitudinal surveillance, pharmacodynamic validation or clinical resistance data.

Absence of curated fitness-cost evidence means only that NODOX cannot evaluate this variable from the supplied catalog. It does not mean zero cost, low risk, or evolutionary safety.
