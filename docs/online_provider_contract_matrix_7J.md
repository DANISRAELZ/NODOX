# Online provider contract matrix 7J

Phase 7J formalizes provider contracts for online-only execution. This matrix is operational metadata: it documents which payloads can be parsed, how degraded states are interpreted, and whether a provider can block ranking.

No scoring, ranking, weight, GUI, or biological-interpretation rule is changed by this phase.

The versioned machine-readable copies are:

- `docs/audit_artifacts/online_provider_contract_matrix_7J.csv`
- `docs/audit_artifacts/online_provider_contract_matrix_7J.json`

| Provider | Role | Current connection status | Accepted payload | Degradation statuses | Blocks ranking | Affects score when degraded | Publication readiness |
|---|---|---|---|---|---|---|---|
| candidate_seed | online-only candidate universe seed | required_seed_layer | json | candidate_seed_unresolved | true | false | contract_ready_blocking_seed |
| UniProt | candidate seed and localization enrichment | structured_json_supported | json | ssl_error; network_error; invalid_payload; empty_payload | false | false | ready_with_transport_limitations |
| STRING | functional network enrichment | structured_json_supported | json | ssl_error; network_error; invalid_payload; not_found | false | false | ready_with_transport_limitations |
| InterPro | host-annotation domain overlap enrichment | structured_json_supported | json | ssl_error; network_error; invalid_payload; unresolved | false | false | ready_with_transport_limitations |
| BV-BRC | strain conservation and genome metadata enrichment | structured_json_supported_when_query_resolves | json | empty_payload; auth_or_permission_error; not_found; network_error; invalid_payload | false | false | conditional_ready |
| VFDB | virulence provider endpoint audit | degraded_no_stable_programmatic_route_verified | json; tabular_text | html_instead_of_structured_payload; not_found; network_error; invalid_payload | false | false | not_ready_for_automatic_evidence |
| DEG | essentiality provider endpoint audit | degraded_zip_requires_adapter | json; tabular_text | html_instead_of_structured_payload; unsupported_structured_archive; network_error; invalid_payload | false | false | not_ready_for_automatic_evidence |
| Europe PMC | literature metadata enrichment | structured_json_supported | json | network_error; invalid_payload; empty_payload | false | false | ready_as_metadata_only |
| Taxonomy | organism identity and taxon resolution | structured_json_supported | json | network_error; online_no_match; invalid_payload | false | false | ready_as_identity_metadata |
| Human essentiality | host essentiality context for host annotation | local_or_structured_download_supported | tabular_text; json | network_error; not_found; empty_payload; invalid_payload | false | false | ready_as_contextual_metadata |

## Conservative reading

Accepted payload means the provider can be parsed only when required fields and provenance are present. It does not mean experimental validation.

Rejected payloads include HTML, unsupported ZIP archives, unexpected text, SSL errors, network errors, empty payloads, and invalid payloads. These states are unresolved operational degradation, not positive evidence and not strong negative evidence.

Every degradation contract records:

- `final_status`
- `conservative_reason`
- `affects_score=false`
- `blocks_ranking=false`, except `candidate_seed_unresolved`
- `evidence_inferred=false`

`candidate_seed` is the only blocking contract because online-only runs need an explicit candidate universe before downstream enrichment can be interpreted. Downstream providers may enrich or degrade, but they do not block ranking.
