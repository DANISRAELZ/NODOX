# Contributing to NODOX

Thank you for considering a contribution to NODOX.

NODOX is a scientific research codebase. Contributions should preserve
reproducibility, evidence provenance, conservative interpretation and the clear
separation between computational prioritization and biological validation.

## Before contributing

- Open an issue describing the proposed change when it affects methodology,
  scoring, evidence interpretation, public APIs or output schemas.
- Do not include credentials, access tokens, private datasets, patient
  information, institutional documents or personally identifiable information.
- Do not commit generated workspaces, caches, results, logs or local virtual
  environments.
- Confirm that any dataset, figure, text or code you contribute may legally be
  redistributed under compatible terms.

## Development setup

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/WSL: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Testing

Run the recommended offline suite before submitting changes:

```bash
python -m pytest -p no:cacheprovider -m "not online" -q
```

Online-provider tests should be reported separately because external service
availability is not controlled by the repository.

## Scientific and methodological changes

Changes to scoring, evidence confidence, thresholds, provenance rules,
Functional Node Theory variables or evolutionary-risk calculations should
include:

- a clear rationale;
- updated documentation;
- focused tests;
- backward-compatibility notes;
- an explanation of how uncertainty and missing evidence remain visible;
- confirmation that the change does not imply clinical or experimental
  validation.

## Data contributions

Do not place private or unpublished user data in the repository. Public example
or reference data must include source, license, retrieval date, organism and
strain context, transformation steps and an explicit statement of whether the
data are demo, controlled reference, external evidence or experimentally
validated evidence.

## Pull requests

Keep pull requests focused. Describe:

- what changed;
- why the change is needed;
- which tests were run;
- whether output schemas or rankings changed;
- any limitations or unresolved issues.

By submitting a contribution, you agree that it may be distributed under the
repository's Apache License 2.0 unless a separate written agreement applies.