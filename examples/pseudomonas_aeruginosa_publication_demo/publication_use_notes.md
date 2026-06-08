# Publication use notes

This demo is intended to make the software easier to review as a reproducible
research artifact.

## Manuscript Uses

- Flow figure: show input package, layer preparation, scoring/reporting entry
  points, audit tables, and conservative interpretation.
- Variables table: document `therapeutic_priority_score`,
  `evidence_confidence_score`, `evidence_quality`, `evidence_strength`,
  `evolutionary_escape_risk`, provenance, and unresolved evidence.
- Candidate table: use generated rows only after the pipeline has produced them
  from explicit inputs.
- Priority/confidence matrix: separate high priority from high confidence.
- Limits section: state that the demo is not clinical validation, not
  experimental validation, and not a predictor of clinical efficacy.
- Negative validation: show that unresolved or insufficient evidence remains
  unresolved and is not converted into low risk.

## Current Limitations

The included input package is intentionally minimal. It demonstrates traceable
user-curated structure and conservative interpretation, but it does not contain
all layers required for a full therapeutic ranking. Missing layers should be
reported as incomplete rather than replaced with proxy claims.

## Future Steps

- Add reviewed organism-specific layers when available.
- Generate the publication tables from a full offline workspace.
- Add stable snapshot tests only after outputs are generated from reviewed
  inputs.
- Keep online providers optional and routed through the existing layer resolver.

