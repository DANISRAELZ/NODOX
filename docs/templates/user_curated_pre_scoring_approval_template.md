# User-Curated Pre-Scoring Approval Template

Use this template before any future controlled scoring phase. This document is
an approval checklist, not a scoring result and not a biological or clinical
validation.

## Dataset

- project_id:
- organism:
- strain_or_isolate:
- dataset_id:
- reviewer:
- review_date:
- manifest_path:

## Checklist

- source_type_confirmed:
- evidence_status_reviewed:
- provenance_reviewed:
- raw_inputs_reviewed:
- demo_proxy_cache_absent:
- missing_fields_accepted:
- limitations_acknowledged:
- expert_review_status:

## Approval decision

Choose exactly one conservative status:

- not_ready_for_scoring
- requires_expert_review
- conditionally_ready_for_future_controlled_scoring

approval_status:

approval_notes:

## Required acknowledgements

- This approval does not execute scoring.
- This approval does not execute pipeline.
- This approval does not execute `run_pipeline.py`.
- This approval does not execute Snakemake.
- This approval does not calculate `therapeutic_priority_score`.
- This approval does not calculate `evidence_confidence_score`.
- This approval does not generate rankings.
- This approval does not generate scientific outputs.
- This approval does not validate the dataset biologically or clinically.
- Expert review and future experimental validation remain required.
