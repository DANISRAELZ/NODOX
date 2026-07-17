# External provider real capture validation (Phase 7F)

## Purpose

A sanitized external capture is a time-bounded response obtained from a real provider endpoint and stored with query, URL, organism, timestamp, observed schema and interpretation warning. Sensitive request or response fields are redacted. Captures remain separate from curator-provided data and scoring inputs.

The versioned captures in `tests/fixtures/external_providers/real_captures_sanitized/` record the controlled 2026-06-22 endpoint check:

- BV-BRC returned HTTP 200 with a CSV header and no data rows for the limited query.
- DEG returned HTML rather than the requested JSON schema.
- VFDB returned HTTP 404 for the configured download URL.

These observations describe provider behavior at capture time. They do not establish absence of genomic, resistance, essentiality or virulence evidence.

## Validation workflow

`validate_sanitized_provider_capture()` checks required provenance, capture type, payload presence, conservative warning, forbidden automatic claims and `affects_score`. Valid captures pass through the Phase 7E provider adapter and are written beneath:

`results/online_only_external_evidence/<run_id>/real_capture_validation/`

Run the existing captures with:

```powershell
python scripts/run_online_only_multiorganism_batch.py --organism-keys escherichia_coli --run-label phase7f --validate-real-provider-captures
```

This flag reads local captures only and performs no network request. Unit tests likewise use only versioned sanitized files.

## Interpretation

- `supported` means an explicit provider record was captured, not experimental confirmation.
- `not_found` applies only to a valid captured query with no records.
- `unresolved` indicates that the payload or schema could not be interpreted.
- `provider_failed` identifies a technical provider error.

Every result has `affects_score=false`. Phase 7F validates transport, sanitization and adapter compatibility; it is not biological validation and must not change ranking. Before public use, manually compare the sanitized record with the provider, verify identifiers and licensing, record retrieval conditions, and obtain scientific review.
