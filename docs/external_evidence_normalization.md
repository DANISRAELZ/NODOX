# External evidence normalization (Phase 7D)

## Scientific purpose

Phase 7D converts heterogeneous provider audit results into a common, traceable schema by organism and candidate. It separates biological absence, a limited search with no result, and an unresolved provider.

## Conservative rules

- `success` with records becomes `supported` only within the provider's declared evidence scope.
- `no_results` becomes `not_found` for that limited query, never total absence.
- Transport and schema failures become `unresolved` or `provider_failed`.
- UniProt seed records remain computational annotations, not experimental validation.
- VFDB, DEG and BV-BRC failures do not imply absence of virulence, essentiality or genomic evidence.
- Every row has `affects_score=false`, `experimental_validation_supported=false` and `external_evidence_normalized=true`.

Outputs are written to `results/online_only_external_evidence/<run_id>/`. This phase does not modify scoring and does not constitute experimental validation.
