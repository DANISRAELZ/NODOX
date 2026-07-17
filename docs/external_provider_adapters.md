# External provider adapters (Phase 7E)

## Purpose

Phase 7E converts already obtained VFDB, DEG and BV-BRC records into the common Phase 7D evidence schema. The adapters are deterministic transformations: they do not query the internet, read curator-provided datasets or change scoring.

## Provider mappings

- VFDB can map an explicit record to `virulence_association`.
- DEG can map an explicit record to `essentiality_association`.
- BV-BRC can map explicit fields to `protein_annotation`, `resistance_association` and, when explicitly supplied, `taxonomy_resolution`.
- A technical failure maps to `unresolved_provider` rather than a biological association.

`supported` means that an explicit external record was present. It does not mean that this pipeline experimentally validated the association. `not_found` means a valid, limited query returned an empty recognized container. `unresolved` means the payload or provider could not be interpreted. `provider_failed` records a technical provider error.

No status may be used to infer absence of virulence, essentiality, resistance or genomic evidence. Every normalized row has `affects_score=false` and `experimental_validation_supported=false`.

## Controlled fixtures

Versioned examples live in `tests/fixtures/external_providers/`. They cover minimal explicit records, valid empty responses and schema errors. They can be loaded as JSON and passed to `normalize_vfdb_records`, `normalize_deg_records` or `normalize_bvbrc_records` with organism, query, URL and timestamp provenance.

`write_external_evidence_package(..., provider_payloads=...)` optionally combines these provider rows with Phase 7D and writes provider-specific CSV files plus a review report. Omitting `provider_payloads` preserves the existing Phase 7D behavior.

## Manual review

Review `source_record_id`, `source_url`, `query_used`, `checked_at`, the original provider record and `interpretation_warning` before making any scientific statement. Confirm identifier mapping and provider scope independently. These adapters normalize metadata; they do not establish causality, in-vivo relevance, therapeutic efficacy or experimental reproducibility.
