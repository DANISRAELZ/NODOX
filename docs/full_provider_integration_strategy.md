# Full Provider Integration Strategy - Phase 7L

## Scientific objective

Phase 7L defines a conservative, reproducible integration strategy for external provider evidence. Its purpose is to record whether each provider is reachable, structured, locally available or not applicable, while preserving the strict separation between external evidence provenance and therapeutic scoring.

External provider evidence is non-blocking and does not directly alter therapeutic_priority_score.

This phase does not change the formulas or weights for:

- `therapeutic_priority_score`
- `evidence_confidence_score`
- `functional_node_score`
- `meta_priority_score`

## Online providers and local datasets

Online providers are checked as live HTTP endpoints when a caller explicitly runs the provider audit. They are allowed to fail, time out, return empty payloads or return unsupported payloads. Those outcomes are recorded as controlled statuses and must not stop the pipeline.

Versioned local datasets are expected to be managed as files under the workspace. VFDB and DEG are treated this way because previous phases found unstable or changed web routes, HTML responses, manual-download requirements or structured archives that still need explicit adapters. A missing local dataset is operational incompleteness, not biological absence.

## Provider table

| Provider | Mode | Intended role | Phase 7L behavior |
| --- | --- | --- | --- |
| UniProt | online | Candidate seed and localization metadata | Validate HTTP response and structured JSON. |
| STRING | online | Functional network metadata | Validate HTTP response and structured JSON. |
| InterPro | online | Domain overlap metadata | Validate HTTP response and structured JSON. |
| BV-BRC | online | Genome and strain metadata | Validate HTTP response and structured JSON. Empty payloads are allowed as controlled status. |
| Europe PMC | online | Literature metadata | Validate HTTP response and structured JSON. |
| Taxonomy | online | Organism identity metadata | Validate HTTP response and structured JSON. |
| VFDB | local_dataset | Virulence dataset | Prefer a versioned local file such as `data_external/vfdb.csv`; do not depend on scraping. |
| DEG | local_dataset | Essentiality dataset | Prefer a versioned local file such as `data_external/deg.csv`; do not depend on scraping. |
| Human essentiality | optional | Host context only | For bacterial organisms, may be marked `skipped_not_applicable`. |

## Status model

Every provider is normalized into one explicit state:

- `connected_structured`: online provider returned an accepted structured payload with at least one item.
- `connected_empty`: online provider returned an accepted structured or empty payload with zero items.
- `unavailable`: timeout, SSL, DNS, transport or generic network failure.
- `unsupported_payload`: HTML, ZIP without adapter, unexpected text or payload type outside the contract.
- `deprecated_or_changed`: endpoint appears changed or gone, such as a controlled 404 for a known old route.
- `local_dataset_available`: expected VFDB or DEG local dataset exists and can be checksummed.
- `local_dataset_missing`: expected VFDB or DEG local dataset is absent.
- `skipped_not_applicable`: optional provider is intentionally skipped for the run context.

## Normalized fields

Phase 7L records use a common schema:

- `provider_name`
- `provider_mode`
- `provider_status`
- `endpoint_or_path`
- `payload_type`
- `structured`
- `evidence_items_count`
- `affects_score`
- `error_category`
- `error_message_sanitized`
- `retrieved_at`
- `provenance`

For local datasets, the audit also records:

- `expected_local_path`
- `dataset_version`
- `checksum_sha256`

## Why VFDB and DEG are local datasets

VFDB and DEG contain scientifically relevant curated information, but previous endpoint checks showed changed routes, manual download requirements, HTML responses or archive formats that need explicit adapters. Treating them as local versioned datasets is more reproducible than forcing fragile scraping or assuming a stable online API.

This means:

- missing VFDB does not imply no virulence evidence;
- missing DEG does not imply no essentiality evidence;
- available files are auditable by path, version note and checksum;
- future adapters can be added incrementally after schema validation.

## Why human essentiality is optional

Human essentiality is host-context metadata. In bacterial target prioritization it is not always applicable and should not block the pipeline. When the organism domain is bacterial, Phase 7L can mark it as `skipped_not_applicable`. This avoids penalizing bacterial candidates for the absence of a host-specific optional layer.

## Non-blocking guarantee

Provider failures are represented as controlled statuses. They should be surfaced in manifests and reports, not raised as uncaught exceptions by the audit runner. The generated manifest reports `blocking_failures=0` and `affects_score=false`.

## Scoring separation guarantee

Phase 7L only records provider status, payload structure, provenance and local dataset availability. It does not write scoring inputs and does not modify score formulas, score weights or ranking semantics.

External provider evidence is non-blocking and does not directly alter therapeutic_priority_score.

## Validation commands

Use the stable test command:

```bash
python -m pytest -p no:cacheprovider tests/test_external_provider_endpoints.py
python -m pytest -p no:cacheprovider tests/test_full_provider_integration.py
python -m pytest -p no:cacheprovider
```

## Current limitations

- Live endpoint results can vary by network, TLS and provider availability.
- VFDB and DEG local schemas remain intentionally minimal until a versioned adapter is validated.
- Human essentiality remains host-context metadata and should not be overread as therapeutic safety validation.

## Suggested next steps

1. Add explicit local schema validators for versioned VFDB and DEG files.
2. Add optional report wiring so Phase 7L artifacts can be copied into review packages.
3. Add controlled fixtures for representative provider payloads from UniProt, STRING, InterPro, BV-BRC, Europe PMC and Taxonomy.
