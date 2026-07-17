# External provider endpoint stability (Phase 7G)

## Purpose

Phase 7G versions the endpoint and format observations produced by the controlled Phase 7F capture. Endpoint failure does not mean biological absence. This registry is operational metadata only and has `affects_score=false`.

The auditable source is `config/external_provider_endpoints.json`. Phase 7H supersedes the original `7G-2026-06-22` observations with version `7H-2026-06-22`. `external_provider_endpoints.py` validates and exposes that registry. Updating it does not update scoring, ranking or biological interpretation.

## Phase 7F observations

| Provider | Endpoint tested | Expected or usable format | Observed response | Status |
| --- | --- | --- | --- | --- |
| VFDB | `http://www.mgc.ac.cn/VFs/Down/VFs.tsv.gz` | Gzip-compressed TSV | HTTP 404 | `deprecated_or_changed` |
| DEG | `https://tubic.org/deg/public/index.php?query=562&format=json` | HTML web interface; structured export still required | HTTP 200 HTML | `html_instead_of_structured_payload` |
| BV-BRC | `https://www.bv-brc.org/api/genome_feature/?eq(genome_id,562.1)&limit(1)` | CSV | HTTP 200, header only | `verified_empty_payload` |

These rows preserve the original 7F findings. The current remediated status is documented in `external_provider_endpoint_remediation.md`.

DEG must not be treated as a functional JSON endpoint because the `format=json` query returned HTML. A dedicated, tested HTML adapter or a documented structured export is required first.

The tested VFDB path returned 404. It remains changed or deprecated until the current official download route and its licensing are manually verified. The failure is unresolved provider connectivity, not absence of virulence evidence.

BV-BRC returned a valid but empty CSV response for the limited identifier query. This can be normalized as query-limited `not_found`; it is not negative genomic or resistance evidence. CSV parsing and identifier syntax still require validation against a non-empty capture.

## Updating an endpoint

1. Run a manual, explicit request outside pytest.
2. Store a sanitized capture with URL, query, timestamp, content type and observed schema.
3. Review provider documentation and licensing.
4. Update `config/external_provider_endpoints.json`, increment `endpoint_spec_version`, and add adapter fixtures if the format changed.
5. Run endpoint, capture, adapter and runner tests.
6. Confirm score hashes and `affects_score=false` before accepting the change.

Do not mark an endpoint `verified_structured_payload` from HTTP status alone. Verification requires a recognizable, non-empty structured payload and adapter coverage.

## Interpretation limits

Endpoint validation measures technical availability and format compatibility at one time. It does not validate essentiality, virulence, resistance, therapeutic value, causality or experimental reproducibility. Manual scientific and provenance review remains mandatory before any public claim.
