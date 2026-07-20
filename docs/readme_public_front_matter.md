# NODOX

**NODOX** is a reproducible, multi-organism bioinformatics platform for the
explainable prioritization of bacterial therapeutic targets using Functional
Node Theory and traceable multilayer evidence.

NODOX integrates essentiality, virulence, human homology, localization,
functional networks, strain conservation, therapeutic context, provenance and
exploratory evolutionary-escape risk. It generates interpretable rankings while
keeping therapeutic priority separate from evidence confidence and coverage.

> **Scientific-use notice:** NODOX produces computationally prioritized
> hypotheses. It does not establish therapeutic efficacy, experimental
> validation, clinical validity or treatment recommendations.

## Core capabilities

- Multi-organism workspaces initiated from organism and optional strain names.
- User-curated, cached, online, controlled and demo evidence with explicit
  provenance.
- Layer-specific validation, normalization and resolution.
- Explainable candidate scoring and therapeutic-role classification.
- Human-homology assessment with an optional DIAMOND execution provider.
- Functional-network and conservation enrichment.
- Evidence-strength, missing-evidence and candidate-level audits.
- Exploratory Functional Node Theory and evolutionary-escape analyses.
- Reproducible publication-package generation.

## Quick start

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/WSL: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run_pipeline.py --organism "Pseudomonas aeruginosa" --strain PAO1 --allow-demo-data --mode compare
```

The PAO1 command is a reproducible software demonstration. Demo data must not be
interpreted as final biological evidence.

Start with [`START_HERE.md`](../START_HERE.md) for installation, workspace and
interpretation guidance. Detailed methodology and advanced workflows remain in
the sections below and under [`docs/`](./).

## Project maturity

NODOX is an advanced scientific prototype intended for exploratory
computational prioritization and reproducible research. Every candidate requires
biological review and experimental validation before therapeutic claims are
made.

## License and citation

The source code is distributed under the Apache License 2.0. Citation metadata
is provided in `CITATION.cff`; author and release metadata must be confirmed
before the first public release.