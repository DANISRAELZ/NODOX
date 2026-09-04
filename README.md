# NODOX: A Computational Model Based on Functional Node Theory for the Identification and Prioritization of Bacterial Drug Targets

**Explainable, evidence-aware prioritization of bacterial therapeutic targets through Functional Node Theory.**

NODOX is a multiorganism bioinformatics research platform for the computational prioritization of bacterial therapeutic targets. It integrates heterogeneous evidence about essentiality, virulence, human homology, subcellular localization, conservation, functional networks, clinical context, literature support, provenance, redundancy, and evolutionary escape risk.

The purpose of NODOX is not to produce a definitive list of validated drug targets. Its purpose is to organize complex and incomplete biological evidence into an auditable, interpretable, and reproducible prioritization workflow that helps researchers decide which candidates deserve deeper review, curation, and experimental validation.

> NODOX generates ranked research hypotheses. It does not establish therapeutic efficacy, clinical validity, safety, or experimental confirmation.
>
> **Theoretical model status:** The theoretical model underlying NODOX remains under active review by our team of collaborators. Its concepts, assumptions, variables, and scoring interpretation should be considered provisional and may change as that review progresses. Passing software tests confirms implementation consistency and reproducibility; it does not constitute scientific validation of the theoretical model.

## Why NODOX exists

Therapeutic-target discovery often produces long lists of genes or proteins based on a single criterion, such as essentiality, virulence, differential expression, pathway participation, network centrality, or absence of human homologs. These approaches are valuable, but they can become difficult to interpret when evidence comes from different databases, experimental conditions, organisms, strains, proxies, cached queries, manually curated files, or incomplete datasets.

NODOX addresses this problem by treating target prioritization as an evidence-integration and decision-audit problem. Instead of hiding uncertainty inside a single score, the platform preserves:

- where each evidence layer came from;
- whether it is user-curated, external, cached, controlled, inferred, proxy-based, demo, unresolved, or missing;
- how much evidence supports each candidate;
- which variables increased or decreased its ranking;
- whether a high therapeutic-priority score is supported by strong or weak evidence;
- which biological and methodological questions remain unresolved.

The result is an explainable ranking that can be inspected, challenged, compared, and reproduced.

## Functional Node Theory

The conceptual center of NODOX is the **Theory of Functional Nodes**.

A functional node is not defined only by whether a gene is essential. It is interpreted as a biological point whose perturbation may affect one or more relevant dimensions of pathogen survival, pathogenicity, adaptability, transmission, or therapeutic vulnerability.

Under this framework, a candidate may be relevant because it acts as:

- a direct antibacterial target;
- an antivirulence target;
- a sensitizing target that increases susceptibility to another intervention;
- a functional bottleneck;
- a network dependency;
- a low-redundancy biological node;
- a candidate for combination therapy;
- a node with a favorable or unfavorable evolutionary escape profile.

NODOX therefore does not assume that all promising candidates must fit the same therapeutic strategy. It calculates and reports multiple complementary interpretations rather than forcing every candidate into a single biological category.

## What NODOX does

NODOX can:

- initialize an analysis from an organism and optional strain;
- create an isolated workspace for each analysis;
- validate and normalize user-supplied evidence files;
- resolve evidence layers from local, cached, curated, controlled, or online providers;
- integrate heterogeneous protein-level evidence;
- calculate legacy, therapeutic-strategy, functional-node, confidence, and evolutionary-risk scores;
- distinguish missing evidence from negative evidence;
- generate candidate-level explanations and audit flags;
- compare analysis phases and scoring strategies;
- preserve provenance and retrieval metadata;
- produce publication-oriented tables, reports, figures, manifests, and audit files;
- run offline for reproducibility or use optional online enrichment when explicitly enabled.

## Scientific architecture

The platform is organized around independent evidence layers that are resolved, validated, integrated, scored, and audited.

### Core layers

The minimum core evidence layers are:

- `essentiality`
- `virulence`
- `human_homologs`
- `localization`

These layers support the basic interpretation of whether a candidate is important to the pathogen, relevant to pathogenicity, potentially selective against the pathogen, and physically accessible or biologically positioned for therapeutic intervention.

### Extended layers

NODOX can also integrate:

- `strain_conservation`
- `functional_network`
- `host_annotation`
- `clinical_impact`
- `curated_disease_context`
- `therapy_site_context`
- `literature_support`
- `redundancy`
- `collateral_sensitivity`
- `evolutionary_escape_risk`
- `contextual_essentiality`
- curated therapeutic catalogs
- organism and taxonomic metadata

Not every layer is required for every analysis. Missing layers remain visible and reduce interpretive confidence rather than being silently converted into favorable evidence.

## Evidence provenance

NODOX separates biological values from evidence provenance.

A layer may be resolved from:

1. user-curated, organism-specific evidence;
2. reproducible local calculations;
3. curated snapshots;
4. real external online providers;
5. cache from previous external resolution;
6. controlled reference providers;
7. inferred proxies;
8. demonstration data;
9. unresolved or missing evidence.

A high score built mainly from proxies or demonstration data is not interpreted in the same way as a high score supported by convergent, organism-specific evidence.

The recommended interpretive hierarchy is:

```text
user_curated
  > organism_specific_external
  > reproducible_local_calculation
  > curated_snapshot
  > general_external
  > controlled_provider
  > inferred_proxy
  > demo
  > missing
```

This hierarchy is not used to claim that external evidence is automatically superior. Its purpose is to make provenance explicit and auditable.

## Analysis workflow

A typical NODOX analysis follows these stages:

```text
Organism / strain
        |
        v
Workspace initialization
        |
        v
Evidence acquisition or import
        |
        v
Validation and normalization
        |
        v
Layer resolution and provenance audit
        |
        v
Evidence integration by protein or gene
        |
        v
Feature derivation
        |
        v
Scoring and sensitivity analysis
        |
        v
Candidate explanations and audits
        |
        v
Rankings, reports, tables, figures, and manifests
```

Each workspace is designed to preserve the inputs, configuration, intermediate tables, resolved layers, outputs, and provenance associated with one organism-specific analysis.

## Scoring model

NODOX separates therapeutic priority from evidence confidence.

### Therapeutic priority

Therapeutic-priority scores summarize how strongly a candidate fits the biological rules of a particular prioritization strategy. Depending on the execution mode, the platform can report:

- `legacy_score_final`
- `antibiotic_target_score`
- `antivirulence_target_score`
- `functional_node_score`
- `meta_priority_score`
- `therapeutic_priority_score`
- `functional_node_theory_score`
- `meta_priority_score_v3`
- `evolutionary_adjusted_meta_priority_score`

### Evidence confidence

Evidence-confidence outputs evaluate how much traceable evidence supports the interpretation. They may include:

- `evidence_confidence_score`
- `evidence_coverage_score`
- evidence-strength classifications;
- provenance status;
- missing-evidence flags;
- confidence ceilings;
- unresolved-layer indicators;
- demo, proxy, cache, or controlled-provider flags.

A candidate can therefore have high therapeutic priority and low evidence confidence. Such a candidate may be interesting, but it requires additional evidence before stronger conclusions can be made.

## Evolutionary escape risk

NODOX includes an explicit evolutionary-risk layer intended to estimate how easily a pathogen might escape or compensate for perturbation of a candidate node.

Potential factors include:

- known resistance-associated mutations;
- sequence conservation;
- functional constraint;
- mutation tolerance;
- paralogs and pathway redundancy;
- alternative pathways;
- recombination context;
- horizontal gene-transfer context;
- mobile genetic context;
- biofilm-related adaptability;
- collateral sensitivity or combination opportunities.

The resulting `evolutionary_escape_risk_score` is interpreted as a risk dimension, not as proof that resistance will or will not emerge. When explicit evidence is unavailable, NODOX can use conservative proxies and lowers confidence accordingly.

## Candidate-level explainability

NODOX produces explanations for individual candidates rather than only a final ranking.

Depending on the analysis mode, outputs can include:

- positive ranking drivers;
- negative ranking drivers;
- missing evidence;
- evidence-confidence summaries;
- therapeutic-role classification;
- functional-node classification;
- provenance summaries;
- contribution of each scoring component;
- evolutionary-risk interpretation;
- confidence ceilings;
- audit flags;
- reasons for ranking changes between phases or scenarios.

This makes it possible to understand not only which candidate ranked highly, but why.

## Multiorganism design

NODOX is not limited to a specific bacterial species.

The examples involving *Pseudomonas aeruginosa*, *Helicobacter pylori*, *Mycobacterium tuberculosis*, or *Corynebacterium pseudotuberculosis* are demonstration and validation cases. They do not define the conceptual scope of the platform.

A new analysis can be initialized from any bacterial organism for which compatible evidence can be supplied or resolved.

## Execution modes

NODOX supports several complementary modes:

- `legacy`: reproduces the interpretable baseline model;
- `phase2`: applies the multicriteria therapeutic-prioritization model;
- `phase3`: adds Functional Node Theory and evolutionary-robustness analysis;
- `compare`: preserves and compares legacy and newer models;
- `dry-run`: prepares and audits a workspace without running the full scoring workflow.

The platform can also operate in:

- offline-only mode;
- cache-first mode;
- optional online mode;
- user-curated workflows;
- controlled reproducible demonstration workflows.

## Online and offline evidence

The core workflow can run without network access when the required inputs or caches are available.

Optional providers can be used for evidence enrichment, including sources such as:

- UniProt;
- STRING;
- InterPro;
- NCBI taxonomy services;
- DEG;
- VFDB;
- BV-BRC;
- public human-essentiality resources;
- DIAMOND-based comparison against a human reference proteome.

Online access is explicit and auditable. Provider failures, empty responses, fallback behavior, cache use, and unresolved layers are recorded rather than hidden.

### External-provider runtime controls

The universal online-only runner now propagates every provider switch into the isolated pipeline configuration. A disabled provider is stopped before local-file, cache, or network lookup:

```bash
python scripts/run_online_only_validation.py \
  --organism-key helicobacter_pylori \
  --disable-string \
  --disable-interpro \
  --disable-literature \
  --disable-vfdb \
  --disable-deg \
  --disable-bvbrc
```

STRING, InterPro, literature metadata, VFDB, DEG, and BV-BRC are enabled by default for an online-only run. “Enabled” means that NODOX may attempt the configured contract; it does not guarantee that a remote service is available or that a candidate matches.

BV-BRC uses its structured API with `eq(taxon_id,...)`, a bounded candidate-gene filter, and a separate genome query for the coverage denominator. A truncated or malformed response remains unresolved.

VFDB and DEG use versioned local datasets because their public delivery routes are not equivalent to stable query APIs. Supply them per run:

```bash
python scripts/run_online_only_validation.py \
  --organism-key helicobacter_pylori \
  --vfdb-dataset /path/to/vfdb.csv \
  --deg-dataset /path/to/deg.csv
```

For DEG, place the manually obtained official archive under a temporary raw directory and normalize it without committing the third-party database:

```bash
python scripts/build_deg_csv.py \
  --raw-dir /path/to/deg_raw \
  --output /path/to/deg.csv \
  --version-output /path/to/deg.version.txt
```

A local VFDB or DEG table needs at least one supported identifier (`gene`, `protein_id`, `locus_tag`, or provider ID); organism or taxon columns are used when present. Missing datasets and unmatched candidates stay unresolved. They are never converted to `virulence_factor=0` or `essential=0`.

`online_only_provider_audit.csv` preserves both API-specific fields and provider-neutral fields: `provider_mode`, `provider_attempted`, `provider_success`, and `affects_score=false`. Final dedicated manifests take precedence over preliminary “disabled” or “deferred” markers. See [external-provider runtime contracts](docs/external_provider_runtime_controls.md).

### DIAMOND human-homology safety

The DIAMOND provider is integrated but intentionally disabled in the repository defaults. A normal NODOX run does not probe the DIAMOND executable, download a human reference, build a database, or run `blastp`. The provider manifest reports `diamond_provider_disabled` until the user opts in.

The repository contains only small synthetic DIAMOND inputs under `tests/fixtures/human_homology_synthetic/`. They exist solely for deterministic automated tests. They are not a human reference proteome and must not be interpreted as biological, clinical, or therapeutic evidence.

For an isolated real run, enable DIAMOND explicitly on the command line. The reference can be plain FASTA or gzip-compressed FASTA; NODOX detects gzip from the file contents, and DIAMOND supports compressed FASTA input:

```bash
python scripts/run_online_only_validation.py \
  --organism-key helicobacter_pylori \
  --run-dir results/helicobacter_pylori_diamond \
  --max-candidates 200 \
  --enable-diamond \
  --diamond-execution-mode execute \
  --diamond-reference-fasta data_external/human_homology_real/human_reference_proteome_UP000005640.faa.gz \
  --diamond-database-prefix data_external/human_homology_real/human_reference_UP000005640
```

The command validates the required paths before creating the run, writes the DIAMOND override only into that run's isolated workspace, keeps downloads disabled, and leaves the repository defaults unchanged. A database argument ending in `.dmnd` is also accepted and normalized to the required prefix.

For deterministic cache reuse, use `--diamond-execution-mode cache_only` with `--diamond-cached-tsv` and, when needed, `--diamond-candidate-fasta`. DIAMOND paths are rejected unless `--enable-diamond` is present. See the [DIAMOND human-homology guide](docs/human_homology_diamond_phase.md) for commands, manual YAML configuration, cache behavior, provenance, and interpretation details.

For a complete *Helicobacter pylori* 26695 publication run with local DEG, VFDB and STRING inputs plus DIAMOND, follow the [publication validation procedure](docs/standard_validation_contract.md#publication-validation-with-versioned-local-datasets).

## Installation

Python 3.10 or later is required.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux or WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Development dependencies

```bash
python -m pip install -r requirements-dev.txt
```

## Start here

For a guided introduction, installation, execution, interpretation, and testing workflow, read:

- [`START_HERE.md`](START_HERE.md)

## Reproducible publication demonstration

A controlled offline demonstration is available at:

```text
examples/pseudomonas_aeruginosa_publication_demo/
```

### PowerShell

```powershell
.\examples\pseudomonas_aeruginosa_publication_demo\run_demo.ps1
```

### Bash

```bash
bash examples/pseudomonas_aeruginosa_publication_demo/run_demo.sh
```

The demonstration verifies workspace preparation, provenance handling, expected output structures, and reporting behavior. It is not experimental or clinical validation.

## Basic pipeline examples

### Reproducible demonstration case

```bash
python run_pipeline.py \
  --organism "Pseudomonas aeruginosa" \
  --strain PAO1 \
  --allow-demo-data \
  --mode compare
```

### Initialize a new organism workspace

```bash
python run_pipeline.py \
  --organism "Organism name" \
  --strain "Strain name" \
  --workspace data_sessions/my_organism_workspace \
  --dry-run \
  --offline-only
```

### Run with organism-specific data

```bash
python run_pipeline.py \
  --organism "Organism name" \
  --strain "Strain name" \
  --workspace data_sessions/my_organism_workspace \
  --mode compare \
  --taxon-resolution-mode cache_first
```

## User-curated evidence

NODOX supports real evidence supplied or reviewed by the user.

User-curated datasets should:

- be specific to the organism or analysis;
- follow the schemas in `data_templates/`;
- include provenance and quality metadata;
- avoid private or sensitive information;
- be accompanied by a dataset manifest;
- distinguish observed values from inferred or proxy values;
- be reviewed before scientific interpretation.

The recommended starting documents are:

- [`docs/user_friendly_onboarding.md`](docs/user_friendly_onboarding.md)
- [`docs/user_curated_validation_protocol.md`](docs/user_curated_validation_protocol.md)
- [`docs/user_curated_operational_flow.md`](docs/user_curated_operational_flow.md)
- [`docs/user_curated_real_dataset_readiness.md`](docs/user_curated_real_dataset_readiness.md)

## Main outputs

Depending on the execution mode, NODOX can generate:

- integrated evidence tables;
- normalized and validated layer files;
- candidate rankings;
- legacy versus updated model comparisons;
- sensitivity analyses;
- evidence-strength audits;
- candidate-level scientific audits;
- provenance summaries;
- layer-resolution manifests;
- online-source manifests;
- evolutionary-risk audits;
- functional-node reports;
- therapeutic-role stability reports;
- publication-oriented tables;
- manuscript-facing summaries;
- figures in PNG and SVG formats;
- reproducibility manifests.

Common output files include:

```text
results/ranking_nodos.csv
results/ranking_nodos_phase3.csv
results/report_phase2.md
results/theory_of_nodes_report.md
results/candidate_audit.csv
results/evidence_strength_audit.csv
results/evolutionary_escape_risk_audit.csv
results/data_provenance_summary.csv
results/layer_resolution_manifest.json
```

## Interpretation rules

A high-ranking candidate should be interpreted as a candidate for prioritized scientific review.

It should not be interpreted as:

- a validated drug target;
- proof of antibacterial efficacy;
- proof of host safety;
- proof that resistance will not emerge;
- a clinical recommendation;
- a substitute for microbiological, pharmacological, toxicological, or experimental evaluation.

Before drawing conclusions, review:

- essentiality and virulence evidence;
- human-homology and host-safety signals;
- localization and accessibility;
- strain conservation;
- network dependency and redundancy;
- disease and infection-site context;
- evolutionary escape risk;
- evidence provenance;
- evidence coverage and confidence;
- unresolved layers;
- demo, proxy, cache, and controlled-provider flags.

## Testing

Recommended offline suite:

```bash
python -m pytest -p no:cacheprovider -m "not online" -q
```

Online provider tests should be run separately because they depend on external availability, provider behavior, and network access.

## Project maturity

NODOX is an advanced scientific prototype and publication-oriented research workflow.

It already includes:

- multiorganism workspaces;
- user-curated data workflows;
- provenance-aware layer resolution;
- multiple scoring phases;
- candidate-level explainability;
- evolutionary-risk modeling;
- optional online providers;
- extensive automated tests;
- publication-package generation;
- conservative scientific disclaimers.

However, scientific maturity depends on the quality of the input evidence. The software cannot convert weak, incomplete, or proxy-based evidence into biological certainty.

## Documentation

### Core concepts

- [Methodology](docs/methodology.md)
- [Scoring](docs/scoring.md)
- [Data model](docs/data_model.md)
- [Theory of Functional Nodes](docs/theory_of_functional_nodes.md)
- [Evolutionary escape model](docs/evolutionary_escape_model.md)
- [Contextual essentiality](docs/contextual_essentiality.md)
- [Redundancy and compensation](docs/redundancy_and_compensation.md)
- [Collateral sensitivity](docs/collateral_sensitivity.md)

### Workflows and evidence

- [Getting started](START_HERE.md)
- [User-curated validation protocol](docs/user_curated_validation_protocol.md)
- [Real data ingestion](docs/real_data_ingestion.md)
- [Discovery layer](docs/discovery_layer.md)
- [Online source integration](docs/online_source_integration.md)
- [DIAMOND human-homology guide](docs/human_homology_diamond_phase.md)
- [Workspace comparison](docs/workspace_comparison.md)

### Publication and release

- [Publication evidence index](docs/publication_evidence_index.md)
- [Publication readiness master index](docs/publication_readiness_master_index.md)
- [Public release checklist](docs/public_release_checklist.md)
- [Pre-publication repository audit](docs/pre_publication_repository_audit.md)
- [Sensitive data and secret scan](docs/sensitive_data_and_secret_scan.md)
- [Security policy](SECURITY.md)
- [Contribution guidelines](CONTRIBUTING.md)

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff).

Software author:

**Dan Israel Zavala Vargas, PhD**

Bibliographic metadata records the author as `Dan Israel Zavala Vargas`, without academic titles, following citation-metadata conventions.

## License

NODOX is distributed under the [Apache License 2.0](LICENSE).

## Scientific and clinical disclaimer

NODOX is a computational research workflow. It does not replace experimental validation, microbiological assessment, pharmacological evaluation, toxicological studies, clinical judgment, or regulatory review. Ranked candidates are hypotheses that require independent validation before therapeutic claims can be made.
