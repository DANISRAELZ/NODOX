# START_HERE — NODOX

**NODOX** is a reproducible, multi-organism bioinformatics platform for the
explainable prioritization of bacterial therapeutic targets through the
**Functional Node Theory** framework.

NODOX integrates traceable evidence layers including essentiality, virulence,
subcellular localization, human homology, functional networks, strain
conservation, therapeutic context, curated literature, provenance and
exploratory evolutionary-escape risk.

> NODOX prioritizes computational hypotheses. It does not establish therapeutic
> efficacy, clinical validity or experimental confirmation.

## 1. What problem does NODOX address?

Candidate-gene and candidate-protein lists frequently combine strong evidence,
incomplete evidence, proxies, demonstrations and missing values without clearly
separating them. NODOX is designed to:

- integrate heterogeneous evidence through a common data contract;
- distinguish user-curated, external, cached, controlled, proxy, demo and
  missing evidence;
- explain why each candidate rises or falls in the ranking;
- compare antibacterial, antivirulence, sensitization and functional-node
  strategies;
- audit evidence provenance, coverage and confidence independently from the
  therapeutic-priority score.

## 2. Scientific scope

The conceptual core of the project is Functional Node Theory. Organisms used in
demos, cached snapshots or tests are validation examples and do not define the
scope of the platform.

The project is intended for bacterial organisms for which compatible evidence
layers can be supplied or resolved. A high score means that a candidate merits
further review under the configured model; it does not mean that the candidate
has been experimentally or clinically validated.

## 3. Requirements

- Python 3.10 or newer.
- Write access to the selected project workspace.
- Internet access only for optional online providers.
- DIAMOND installed separately when the executable human-homology provider is
  enabled.

## 4. Installation

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

Development and test dependencies are installed separately:

```bash
python -m pip install -r requirements-dev.txt
```

## 5. Reproducible demonstration

Use the included Pseudomonas aeruginosa PAO1 case only to confirm that the
pipeline runs:

```bash
python run_pipeline.py \
  --organism "Pseudomonas aeruginosa" \
  --strain PAO1 \
  --allow-demo-data \
  --mode compare
```

Demo data are intended for software verification and should not be interpreted
as final biological evidence.

## 6. Start a workspace for another organism

Prepare a generic offline dry run:

```bash
python run_pipeline.py \
  --organism "Organism name" \
  --strain "Strain name" \
  --workspace data_sessions/my_organism_workspace \
  --dry-run \
  --offline-only
```

For an exploratory run with curated or previously resolved evidence:

```bash
python run_pipeline.py \
  --organism "Organism name" \
  --strain "Strain name" \
  --workspace data_sessions/my_organism_workspace \
  --mode compare \
  --taxon-resolution-mode cache_first
```

Do not use `--allow-demo-data` for a real organism analysis. If mandatory layers
are missing, review the generated discovery and provenance reports before
continuing.

## 7. Evidence types

Interpret every run according to its provenance:

1. user-curated, organism-specific and traceable evidence;
2. verifiable external evidence;
3. internally computed evidence derived from user inputs;
4. local or raw evidence;
5. general external evidence;
6. controlled providers or explicit proxies;
7. demonstration data;
8. missing or unresolved evidence.

Cached evidence improves reproducibility but is not automatically equivalent to
a fresh external query. Absence of evidence is not negative evidence.

## 8. Main outputs

Review these outputs first after a run:

- `results/ranking_nodos.csv`: principal candidate ranking;
- `results/report_phase2.md`: technical scoring and provenance report;
- `results/top10_scientific_audit.md`: scientific audit of prioritized
  candidates;
- `results/phase_comparison.csv`: comparison between implemented phases;
- `results/sensitivity_analysis.csv`: ranking sensitivity;
- `results/data_provenance_summary.csv`: dataset provenance summary;
- `results/evidence_strength_audit.csv`: evidence-strength assessment;
- `data_processed/scored_nodes.csv`: calculated scores by candidate.

Output paths may be located inside the selected organism workspace.

## 9. Interpreting a candidate

Do not interpret a ranking position alone. Review it together with:

- therapeutic-priority score;
- evidence-confidence and evidence-coverage scores;
- essentiality and virulence evidence;
- human-homology and host-risk evidence;
- localization and therapeutic accessibility;
- conservation, network and redundancy evidence;
- evolutionary-escape variables;
- provenance status, retrieval mode and audit flags.

A highly ranked candidate supported mainly by demo data, defaults or proxies is
a weaker hypothesis than a candidate supported by convergent, traceable and
organism-specific evidence.

## 10. Tests

Recommended offline suite:

```bash
python -m pytest -p no:cacheprovider -m "not online" -q
```

Online tests should be executed separately because they depend on external
provider availability and can change independently of the NODOX source code.

## 11. Documentation map

- `README.md`: complete project documentation.
- `docs/methodology.md`: methodology.
- `docs/scoring.md`: scoring framework.
- `docs/user_friendly_onboarding.md`: user-curated onboarding.
- `docs/theory_of_functional_nodes.md`: conceptual framework.
- `docs/human_homology_diamond_phase.md`: DIAMOND human-homology layer.
- `docs/public_release_checklist.md`: public-release review checklist.
- `SECURITY.md`: security and disclosure policy.

## 12. Final interpretation warning

NODOX is an advanced scientific prototype for exploratory computational
prioritization. Its outputs require external biological review and experimental
validation before any therapeutic claim. It is not a clinical decision system,
a diagnostic tool or a treatment recommendation.