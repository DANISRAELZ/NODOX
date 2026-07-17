# Phase 7I.1 Windows SSL remediation for InterPro tests

## Purpose

Phase 7I.1 closes the Windows-specific `OPENSSL_Applink` failure observed while validating the InterPro-backed `host_annotation` provider in mocked tests.

The change is operational only. It does not modify scoring, ranking, weights, GUI behavior, biological interpretation, or provider priority.

## Root cause

`interpro_api.py` created an SSL context before the mocked `urlopen` object was reached. On this Windows runtime, creating the OpenSSL-backed context could fail with:

`OPENSSL_Uplink(...): no OPENSSL_Applink`

That made a mocked offline test depend on a real SSL runtime detail.

During the full offline suite, the same mechanical pattern was also found in the UniProt-backed `localization` and `human_homologs` provider helpers. Those paths were adjusted in the same conservative way so offline tests remain network-free and do not create SSL contexts before mocks.

## Correction

The provider request path now uses `provider_response_audit.request_provider_payload()` for InterPro, STRING, UniProt localization, and UniProt human-homolog lookup calls that need structured JSON handling.

This helper:

- creates a real SSL context only for the real default opener;
- skips SSL-context creation when tests inject a mocked opener;
- classifies payloads before provider-specific parsing;
- treats SSL, network, empty, HTML, ZIP, and unexpected-text responses as unresolved provider degradation, not biological evidence.

Compatibility symbols used by existing tests, such as `get_ssl_context` imports and `string_api._request_json`, were preserved without reintroducing SSL construction before mocked calls.

## Conservative interpretation

For InterPro degradation states:

- SSL failures are recorded as `retrieval_status=ssl_error`.
- Network failures are recorded as `retrieval_status=network_error`.
- HTML, free text, or other unexpected payloads are recorded as `retrieval_status=invalid_payload`.
- Missing accessions do not open the network and remain unresolved.
- `affects_score=false`.
- `blocks_ranking=false`.
- `evidence_inferred=false` unless structured InterPro JSON produces comparable domain rows.

InterPro remains optional and non-blocking. It does not become a strict validation layer.

## Scope intentionally unchanged

No changes were made to:

- `scoring.py`
- `scoring_components.py`
- scoring weights
- ranking rules
- GUI files
- `config/params.yaml`

`candidate_seed` remains the only strict blocking layer in the online-only validation flow.

## Validation

Focused validation added:

- `tests/test_interpro_api.py`

Coverage includes:

- structured JSON materializes InterPro domain overlap;
- SSL errors are non-blocking unresolved provider status;
- network errors are non-blocking unresolved provider status;
- unexpected text payloads are not converted into domain evidence;
- missing accessions do not call the network.

Related validation was run for:

- InterPro layer resolution;
- STRING regression;
- VFDB, DEG, BV-BRC conservative provider behavior;
- provider audit and endpoint tests;
- online-only validation;
- multi-organism online-only runner;
- offline suite.
