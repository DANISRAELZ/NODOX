# External-provider runtime contracts

## Purpose

This change makes online-only provider execution consistent from the command line through final layer resolution. It also separates live APIs from reproducible local-dataset providers.

The change does not modify scoring formulas, weights, therapeutic roles, or ranking thresholds.

## Provider modes

| Provider | Runtime mode | Contract |
| --- | --- | --- |
| UniProt | online | Candidate seed and annotation metadata. |
| STRING | online | Bounded network enrichment. |
| InterPro | online | Domain metadata and host-annotation support. |
| Europe PMC | online | Literature metadata only. |
| BV-BRC | online | Genome denominator plus candidate-gene feature query. |
| VFDB | local dataset | Versioned CSV/TSV supplied by the user; no portal scraping. |
| DEG | local dataset | Versioned CSV/TSV, optionally produced from the official manually obtained archive. |
| DIAMOND | local executable/reference | Explicit opt-in remains required. |

## Runtime switches

The generic runner accepts:

- `--disable-string`
- `--disable-interpro`
- `--disable-literature`
- `--disable-vfdb`
- `--disable-deg`
- `--disable-bvbrc`
- `--vfdb-dataset PATH`
- `--deg-dataset PATH`

The switches are written into the isolated workspace configuration. `fetch_layer_external_source()` checks the effective switch before consulting provider files, cache, or network.

## New audit fields

Provider manifests and `online_only_provider_audit.csv` use:

- `provider_mode`: `online`, `local_dataset`, or `local_executable`;
- `provider_attempted`: whether the configured contract was inspected or queried;
- `provider_success`: whether the provider contract returned a valid structured source;
- `api_attempted` and `api_success`: retained for compatibility and limited to network APIs;
- `retrieval_status`: the precise final state;
- `affects_score`: always `false` for this provider-status audit.

The final audit prefers provider-specific manifests such as `bvbrc_conservation_manifest.json`, `vfdb_virulence_manifest.json`, and `deg_essentiality_manifest.json` over preliminary online-only markers.

## Conservative evidence rules

- A missing local dataset is `local_dataset_missing`, not biological absence.
- A valid local dataset with no candidate match is `local_dataset_no_candidate_matches`.
- VFDB nonmatches are omitted; they are not emitted as `virulence_factor=0`.
- DEG nonmatches are omitted; they are not emitted as `essential=0`.
- BV-BRC candidates without matched features are omitted.
- BV-BRC paginates feature records up to the configured maximum and returns no conservation values if the genome denominator or the complete feature result would exceed its configured limit.
- Provider failures remain non-blocking and do not establish experimental, clinical, or pharmacological validation.

## DEG local adapter

`scripts/build_deg_csv.py` accepts the official headerless semicolon-delimited CSV inside a manually obtained ZIP. It writes:

- a normalized `deg.csv`;
- a `deg.version.txt` containing the adapter version and source SHA-256.

The repository must not commit the downloaded DEG database. The generated version file is provenance, not a license grant.

## Current limitations

- VFDB still requires a manually reviewed, legally usable local export; NODOX does not guess a download URL or scrape HTML.
- Identifier matching is exact and case-insensitive. Synonym, orthology, and sequence-alignment matching are separate future workflows.
- BV-BRC coverage is scoped to the exact requested `taxon_id`.
- An available provider can still return no usable candidate matches.
- These contracts improve execution and provenance; they do not validate a therapeutic target experimentally.

## Suggested next steps

1. Add a documented VFDB export normalizer after a stable official format and redistribution terms are verified.
2. Add identifier crosswalks with explicit confidence and provenance.
3. Raise BV-BRC record limits only after reviewing runtime, response size, and completeness guarantees for the target organism.
4. Keep all provider integrations behind the existing layer resolver.
