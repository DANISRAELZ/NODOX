# NODOX

**Explainable, evidence-aware prioritization of bacterial therapeutic targets and functional nodes.**

NODOX is a multiorganism bioinformatics research platform that integrates essentiality, virulence, human-homology, localization, functional-network, conservation, clinical-context, provenance, and evolutionary-risk evidence to rank bacterial candidate targets.

NODOX is designed for transparent computational prioritization. It does **not** establish therapeutic efficacy, clinical validity, safety, or experimental confirmation. Every ranking must be interpreted together with evidence provenance, coverage, confidence, missing-data flags, and validation requirements.

## Project status

NODOX is an advanced scientific prototype intended for exploratory research, reproducible analysis, methodological evaluation, and hypothesis generation.

Current release candidate: `v0.1.0-publication`.

## Key capabilities

- Multiorganism workspaces initiated from an organism and optional strain.
- Integration of user-curated, local, cached, controlled, online, proxy, and demo evidence.
- Separate therapeutic-priority and evidence-confidence scores.
- Explainable candidate-level drivers, penalties, missing evidence, and provenance.
- Functional Node Theory and evolutionary escape-risk analysis.
- Offline reproducible execution and optional online enrichment.
- Publication-oriented tables, audits, reports, figures, and manifests.

## Start here

For installation, first execution, interpretation, and testing, read [`START_HERE.md`](START_HERE.md).

### Installation

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux or WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

## Reproducible demonstration

The publication-oriented offline demonstration is located at:

```text
examples/pseudomonas_aeruginosa_publication_demo/
```

PowerShell:

```powershell
.\examples\pseudomonas_aeruginosa_publication_demo\run_demo.ps1
```

Bash:

```bash
bash examples/pseudomonas_aeruginosa_publication_demo/run_demo.sh
```

The demonstration verifies preparation, provenance, expected output structure, and reporting behavior. It is not experimental or clinical validation.

## Basic pipeline example

```bash
python run_pipeline.py \
  --organism "Pseudomonas aeruginosa" \
  --strain PAO1 \
  --allow-demo-data \
  --mode compare
```

PAO1 is included only as a reproducible demonstration case. NODOX is not restricted to this organism.

For a new organism, use a dedicated workspace and provide or resolve the required evidence layers:

```bash
python run_pipeline.py \
  --organism "Organism name" \
  --strain "Strain name" \
  --workspace data_sessions/my_organism_workspace \
  --dry-run \
  --offline-only
```

## Required core evidence layers

- `essentiality`
- `virulence`
- `human_homologs`
- `localization`

Additional layers can include strain conservation, functional networks, host annotation, clinical impact, disease context, therapy-site context, literature support, redundancy, collateral sensitivity, and evolutionary escape evidence.

Templates are available under [`data_templates/`](data_templates/).

## Interpretation principles

A high ranking means that a candidate deserves prioritized scientific review under the current model and available evidence. It does not mean that the candidate is validated.

Always inspect:

- therapeutic priority;
- evidence confidence and coverage;
- human-homology and host-safety signals;
- provenance and retrieval mode;
- demo, proxy, cache, controlled, unresolved, and missing-evidence flags;
- evolutionary escape risk;
- candidate-level positive and negative drivers.

## Testing

Recommended offline suite:

```bash
python -m pytest -p no:cacheprovider -m "not online" -q
```

Online provider tests should be run separately because they depend on external availability and network access.

## Documentation

- [Getting started](START_HERE.md)
- [Methodology](docs/methodology.md)
- [Scoring](docs/scoring.md)
- [Theory of Functional Nodes](docs/theory_of_functional_nodes.md)
- [Evolutionary escape model](docs/evolutionary_escape_model.md)
- [User-curated validation protocol](docs/user_curated_validation_protocol.md)
- [Publication evidence index](docs/publication_evidence_index.md)
- [Public release checklist](docs/public_release_checklist.md)
- [Security policy](SECURITY.md)
- [Contribution guidelines](CONTRIBUTING.md)

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff).

Suggested software author display:

**Dan Israel Zavala Vargas, PhD**

Bibliographic metadata records the author as `Dan Israel Zavala Vargas`, without academic titles, following citation-metadata conventions.

## License

NODOX is distributed under the [Apache License 2.0](LICENSE).

## Scientific and clinical disclaimer

NODOX is a computational research workflow. It does not replace experimental validation, microbiological assessment, pharmacological evaluation, clinical judgment, or regulatory review. Ranked candidates are hypotheses requiring independent validation.