# Stage 4F — Real H. pylori fitness-cost literature curation

## Purpose

Stage 4F moves NODOX from evolutionary-evidence infrastructure toward real biological evidence while preserving the fail-closed rules established in Stages 4A–4E.

The central distinction is:

```text
real experimental study located
        !=
quantitative record eligible for scoring
```

A paper may experimentally demonstrate a fitness defect, fitness advantage, or context-dependent phenotype without exposing a numeric value that can be safely transformed into `fitness_cost_of_escape`. Stage 4F records that literature without inventing a scalar.

## Current H. pylori evidence

The first screened source is:

- Windham IH, Merrell DS. *Analysis of fitness costs associated with metronidazole and amoxicillin resistance in Helicobacter pylori*. Helicobacter. 2020;25(5):e12724. PMID: 32677105. DOI: 10.1111/hel.12724.

The study engineered isogenic `rdxA` and `pbp1` resistance mutations and used in-vitro competition assays to assess relative fitness. The accessible article text reports that the tested metronidazole-resistance mutations did not produce a fitness cost under the tested conditions, while amoxicillin-resistant PBP1 mutants showed competition defects by 24 hours and strong environmental dependence.

Mutation/context identity is cross-checked with:

- Windham IH, Merrell DS. *Interplay between Amoxicillin Resistance and Osmotic Stress in Helicobacter pylori*. J Bacteriol. 2022;204(5):e00045-22. PMID: 35389254. DOI: 10.1128/jb.00045-22.

The follow-up explicitly identifies PBP1 V374L and N562Y as amoxicillin-resistance mutations associated with fitness defects in competition with wild-type G27 and confirms that osmotic stress changes their behavior.

## Screened registry

Stage 4F adds:

```text
data_curated/organisms/helicobacter_pylori/evolutionary_fitness_cost_screened.csv
```

The initial registry contains:

| Gene | Mutation | Experimental interpretation | Stage 4F state |
| --- | --- | --- | --- |
| `pbp1` | V374L | amoxicillin resistance; competition fitness defect | screening only |
| `pbp1` | N562Y | amoxicillin resistance; competition fitness defect under baseline/moderate-stress conditions | screening only |
| `pbp1` | N562Y | conditional fitness advantage under extreme hyperosmotic stress | screening only |

All current rows intentionally leave `relative_fitness` blank.

## Why the records are not yet Stage 4E scoring evidence

Stage 4E currently accepts WT-normalized relative-fitness ratios through explicit transformations such as:

```text
fitness_cost_of_escape = max(0, min(1, 1 - relative_fitness))
```

The accessible text for the screened H. pylori studies confirms the direction and experimental context of the fitness effects but does not expose a reusable numeric relative-fitness scalar for the V374L/N562Y competition observations.

Stage 4F therefore assigns:

```text
screening_only_missing_numeric_relative_fitness
```

A qualitative phrase such as `fitness defect` must never be converted into a guessed value such as 0.2, 0.5, or 1.0.

## Screening audit

The non-scoring audit module is:

```text
src/nodos_funcionales/evolutionary_fitness_cost_screening.py
```

It classifies screened rows into states such as:

```text
screening_only_missing_numeric_relative_fitness
screening_only_unsupported_measurement_type
screening_only_non_direct_mapping
quantitative_candidate_not_promoted
promoted_to_stage4e_catalog
```

The classification is derived from the data. A free-text `screening_status` value cannot override missing quantitative evidence.

The audit never writes or modifies `fitness_cost_of_escape`, never changes candidate ranking, and never auto-creates `evolutionary_fitness_cost.csv`.

## Explicit promotion boundary

Even if a future screened record contains a valid numeric `relative_fitness`, Stage 4F only labels it:

```text
quantitative_candidate_not_promoted
```

until a curator explicitly places the complete record in the Stage 4E production catalog:

```text
data_curated/organisms/<organism>/evolutionary_fitness_cost.csv
```

This keeps literature discovery separate from scoring authorization.

## Audit outputs

For a compatible NODOX workspace:

```text
results/evolutionary_fitness_cost_literature_screening_manifest.json
results/evolutionary_fitness_cost_literature_screening_summary.csv
```

The manifest explicitly reports:

- screened record count;
- quantitative promotion-candidate count;
- records already represented in the Stage 4E catalog;
- `scoring_effect = false`;
- `auto_promotion_enabled = false`.

## Command-line audit

From the repository root:

```bash
python scripts/audit_evolutionary_fitness_cost_literature.py \
  --workspace results/<h_pylori_run>/workspace \
  --online-source-mode hybrid_curated
```

The workspace must contain an organism profile in a location already supported by NODOX.

## Source-mode policy

The screening registry is local curated evidence. Therefore:

- `hybrid_curated`: screening audit permitted;
- legacy curated-compatible modes: permitted according to existing policy;
- `online_strict`: disabled;
- `online_only`: disabled.

Even when enabled, the screening layer itself has no scoring effect.

## Current biological conclusion

Stage 4F has located defensible experimental H. pylori fitness-cost evidence for PBP1 resistance mutations, but the currently accessible sources do not provide the numeric WT-normalized relative-fitness values required by Stage 4E.

Therefore the scientifically correct current result is:

```text
new H. pylori Stage 4F screened records: 3
new Stage 4E quantitative fitness-cost records: 0
new supported evolutionary score caused by Stage 4F: 0
```

This is not a software failure. It is an explicit representation of evidence availability.

## What would justify promotion later

Promotion requires a traceable quantitative measurement from the primary article, author manuscript, supplementary data, or another validated experimental source. The record must preserve mutation, organism/taxon, strain/background, assay context, measurement type, source identifier, direct mapping and provenance.

If the primary data become available, they should first be entered into the screened registry, audited, and only then copied explicitly into the Stage 4E production catalog after the transformation is reviewed.

## Interpretation limits

Fitness cost is mutation-, strain-, environment-, assay-, and time-dependent. The N562Y example demonstrates why a single gene-level constant can be misleading: the same resistance mutation can display a defect in one condition and an advantage in another.

Stage 4F therefore improves biological honesty even when it does not increase the number of contract-supported candidates.
