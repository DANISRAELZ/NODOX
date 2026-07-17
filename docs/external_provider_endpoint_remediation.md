# External provider endpoint remediation (Phase 7H)

## Objective

Phase 7H reviews and corrects provider routes before adding format adapters. All observations are operational provenance with `affects_score=false`. A missing record, HTML page, HTTP error or empty response is never biological evidence.

## BV-BRC

Priority review succeeded using the official API:

1. `https://www.bv-brc.org/api/genome/?eq(taxon_id,562)&limit(2)` with `Accept: application/json` returned explicit genome records, including `genome_id=562.6961`.
2. `https://www.bv-brc.org/api/genome_feature/?eq(genome_id,562.6961)&limit(2)` with the same Accept header returned HTTP 200 JSON with two CDS records.

The endpoint is now `verified_structured_payload`. The earlier empty CSV was caused by the tested `genome_id=562.1`, not by biological absence. Correct use is two-stage: resolve a real genome ID, then request features. The sanitized response is `bvbrc_real_capture_sanitized_002.json`.

## DEG

The query-style URL with `format=json` still returns HTML and is not a JSON API. Manual review of the official download page identified:

`https://tubic.org/deg/public/download/deg_annotation_p.csv.zip`

The download returned HTTP 200 `application/zip`; it contains a non-empty `deg_annotation_p.csv` entry with semicolon-delimited protein records and no header. The endpoint is `requires_format_adapter`, because safe use requires explicit ZIP handling, a documented positional schema and validation of record identifiers. The sanitized metadata and three sample lines are stored in `deg_real_capture_sanitized_002.json`.

## VFDB

The old configured `VFs.tsv.gz` route returned HTTP 404. The current official portal at `http://www.mgc.ac.cn/cgi-bin/VFs/v5/main.cgi` responded, but manual HTML inspection did not expose a stable programmatic download URL that could be verified. VFDB is therefore `requires_manual_download`.

No alternative FASTA, TSV or archive URL was guessed. Any future correction requires an official published route, license review and a sanitized non-empty capture. The portal review is stored in `vfdb_real_capture_sanitized_002.json`.

## Versioned decision

`config/external_provider_endpoints.json` version `7H-2026-06-22` is the auditable registry:

- BV-BRC: `verified_structured_payload`, JSON, two-stage genome resolution.
- DEG: `requires_format_adapter`, ZIP containing semicolon-delimited CSV.
- VFDB: `requires_manual_download`, no verified stable programmatic download.

These changes do not modify scoring, ranking or therapeutic interpretation. Before publication, review the original provider response, query semantics, identifiers, terms of use and capture timestamp.
