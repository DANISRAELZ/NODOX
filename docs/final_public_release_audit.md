# Final Public Release Audit

## Purpose

This document summarizes the final public-release audit status before manual approval of `v0.1.0-publication`. It is a release-safety gate, not a scientific validation layer.

The final tag remains blocked until human approval.

## Audit Status

| Area | Status | Boundary |
| --- | --- | --- |
| Project license | Apache License 2.0 present in `LICENSE`. | Project code license is set; dependency license/security review remains required. |
| Core Snakemake boundary | Core release no longer requires Snakemake. | Snakemake remains optional workflow dependency only. |
| Optional workflow dependencies | Separate review required before public workflow distribution. | UNKNOWN Snakemake transitive metadata does not block core release by default. |
| Core dependency license review status | Pending completion or explicit human acceptance. | Do not claim dependency license review is complete. |
| Core dependency security review status | Pending completion or explicit human acceptance. | Do not claim dependency security review is complete. |
| Sensitive data/secrets scan status | Lightweight repository-level scan documented; final human review remains required. | No full external secret scanner is claimed. |
| Internal prompts/logs scan status | Review required for prompts, raw transcripts, internal planning notes and unreviewed logs. | These must be excluded or intentionally scrubbed before public release. |
| Generated results/data directory review status | `results/`, `data_sessions/`, `data_processed/`, caches and temporary outputs require review. | Public release should include only safe fixtures, safe demos and documented examples. |
| AI-use transparency | `docs/ai_use_transparency_statement.md` present. | AI assistance does not replace authorship, validation, licensing or scientific responsibility. |

## Interpretation Boundaries

- No clinical validation is claimed.
- No experimental validation is claimed.
- No claims that therapeutic targets are validated are made.
- Workflow validation is not biological validation.
- Scoring remains computational prioritization only.

## Final Decision

The project is technically close to `v0.1.0-publication`, but the final tag remains blocked until:

- core dependency license review is completed or explicitly accepted by human approval;
- core dependency security review is completed or explicitly accepted by human approval;
- sensitive data/secrets and internal prompt/log review is completed;
- generated results/data inclusion is reviewed;
- optional workflow dependency review is completed before public workflow distribution;
- final human approval is given.

Do not create `v0.1.0-publication` automatically.
