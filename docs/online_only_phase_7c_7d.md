# Online-only Phases 7C and 7D

## Separation of responsibilities

Phase 7C asks whether providers are technically reachable and records auditable provenance. Phase 7D describes the retrieved or unresolved state in one common evidence schema. Neither phase changes ranking, therapeutic interpretation or existing scores.

Run both packages with:

```powershell
python scripts/run_online_only_multiorganism_batch.py --all-default-validation-organisms --run-label phase7cd --continue-on-error --check-provider-connectivity --normalize-external-evidence
```

`--normalize-external-evidence` also performs the 7C audit because normalization needs its provenance. Secondary provider failures do not stop the batch. A local inability to create required artifacts remains a real execution failure.

## Limits and future work

Online-only evidence depends on provider availability, query coverage, identifiers and changing schemas. `not_found` is query-limited; `unresolved` means no interpretable answer. These outputs support audit and comparison, not experimental validation. A later phase may add provider-specific record adapters incrementally, with fixtures and documented stable identifiers, while keeping scoring opt-in and separately reviewed.
