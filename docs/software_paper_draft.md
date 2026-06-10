# Nodos Functional: a reproducible software framework for theory-driven therapeutic target prioritization using curated evidence, functional context and evolutionary risk

## Title

Nodos Functional: a reproducible software framework for theory-driven therapeutic target prioritization using curated evidence, functional context and evolutionary risk

## Abstract

Nodos Functional is a reproducible software framework for theory-driven prioritization of bacterial candidate functional nodes. The software integrates curated evidence, functional annotation, therapeutic context, evidence provenance and evolutionary risk into auditable tabular outputs. The framework calculates rankings of candidate functional nodes while keeping `therapeutic_priority_score` separate from `evidence_confidence_score`, so that therapeutic prioritization and evidence support are interpreted as distinct model outputs. It also reports `evolutionary_escape_risk_score` and related penalties to make resistance, redundancy and compensation concerns visible during review. Nodos generates a reproducible `publication_package` containing tables, figures, baseline comparisons and internal validation summaries. The resulting rankings are computationally prioritized hypotheses requiring independent validation, not experimental, pharmacological or clinical conclusions.

## Introduction

Therapeutic prioritization in bacterial systems often requires combining heterogeneous sources of evidence. Essentiality, virulence, localization, host selectivity, functional context and evolutionary robustness can each provide useful signals, but none of these dimensions is sufficient on its own. A reproducible software framework should therefore expose the evidence used, preserve provenance limitations and report uncertainty alongside ranking.

Nodos Functional addresses this need by implementing an interpretable pipeline for bacterial candidate functional node prioritization. The project is designed for multiorganism use and avoids making any single organism, example dataset or provider the conceptual center of the software. Its outputs are intended to support review and hypothesis generation.

## Methods

The software reads local input layers, validates and normalizes identifiers, integrates evidence into a candidate-level table, computes interpretable scores and exports results. The publication workflow operates offline from consolidated CSV files in `results/` and writes a reproducible package to `results/publication_package/`.

The publication package contains candidate rankings, score decompositions, evolutionary risk tables, sensitivity summaries, evidence provenance summaries, baseline comparisons, interpretative figures and internal validation checks. Missing, proxy, demo, preliminary, not assessed and insufficient evidence labels remain visible throughout the package.

## Software Architecture

The repository is organized as a staged pipeline with separate responsibilities for discovery, acquisition, validation, normalization, integration, scoring, reporting, configuration and optional online sources. Publication-oriented functionality extends this architecture rather than replacing it.

The publication layer includes:

- `FunctionalNodeModel`, an explicit model wrapper for candidate scoring and ranking;
- `FunctionalNodeModelConfig`, an auditable configuration of default weights and thresholds;
- baseline comparison utilities;
- internal validation utilities;
- a publication package builder;
- figure generation from consolidated local tables.

## Functional Node Computational Model

The model preserves or computes the following outputs:

- `meta_priority_score`;
- `therapeutic_priority_score`;
- `evidence_confidence_score`;
- `functional_node_score`;
- `functional_node_theory_score`;
- `evolutionary_escape_risk_score`;
- `evolutionary_escape_penalty_applied`;
- `evolutionary_adjusted_meta_priority_score`;
- `final_priority_rank`;
- `interpretation_warning`.

`therapeutic_priority_score` is used to prioritize hypotheses for review. `evidence_confidence_score` describes evidence support, provenance and interpretability constraints. These variables are intentionally separated. Evidence confidence can limit interpretation but does not transform a computational hypothesis into a confirmed biological conclusion.

Evolutionary risk is also kept explicit. High `evolutionary_escape_risk_score` can apply or preserve a penalty and adds conservative interpretation warnings. This makes escape, redundancy and compensation concerns visible in the final ranking.

## Publication Demo

The publication demo is generated with:

```bash
python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package
```

The command uses local result tables and does not require internet access. It produces publication tables, figures, baseline comparisons, internal validation reports and a manifest.

## Results

The package reports top candidates, score decomposition, evolutionary risk, sensitivity stability, evidence provenance and baseline comparisons. Figures summarize the ranking, the separation between priority and evidence confidence, score decomposition, evolutionary risk in relation to priority, ranking stability and therapeutic role distribution.

These outputs demonstrate that Nodos can produce auditable, decomposable and reproducible prioritization results. They should be interpreted as computationally prioritized hypotheses requiring independent validation.

## Internal Validation

Internal validation checks that the ranking is deterministic, that therapeutic priority and evidence confidence remain separate, that limitation labels are preserved, that high evolutionary risk is warned or penalized, that insufficient evidence is not converted into low risk, that conservative language is used and that the workflow remains compatible with offline execution.

Baseline comparisons provide simple reference rankings based on antibiotic target score, functional node score and an unweighted score mean. These baselines help identify where the integrated Nodos ranking differs from simpler ranking rules.

## Discussion

Nodos Functional provides an explicit and reproducible approach for integrating heterogeneous bacterial evidence into a therapeutic prioritization workflow. Its main contribution is not a claim of biological confirmation, but a transparent software representation of how candidate functional nodes can be ranked, audited and interpreted.

The separation of `therapeutic_priority_score` and `evidence_confidence_score` is central to this design. A high therapeutic score indicates priority within the computational model, while evidence confidence indicates how cautiously that result should be read. Evolutionary escape risk further supports conservative interpretation by keeping risk signals visible.

## Limitations

The current publication package is a computational demonstration. It does not provide experimental, pharmacological or clinical confirmation. Demo, proxy, preliminary, missing, not assessed and insufficient evidence labels limit interpretation and should not be treated as negative evidence or safety evidence. Baseline comparisons are internal references rather than external biological benchmarks.

## Code Availability

The code is organized as a reproducible Python repository. Publication materials are generated from local results using the publication package builder.

## Data Availability

The publication package is generated from local CSV files under `results/`. Input provenance and limitation labels should be reviewed together with candidate rankings.

## Reproducibility Statement

The publication package can be reproduced offline with:

```bash
python -m src.nodos_funcionales.publication_package_builder --results-dir results --output-dir results/publication_package
```

The package includes a manifest, tables, figures and internal validation outputs.

## References Placeholder

- Functional node theory reference placeholder.
- Evidence integration and therapeutic prioritization reference placeholder.
- Evolutionary escape and resistance risk reference placeholder.
