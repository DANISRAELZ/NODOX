# Online-only provider publication readiness 7J

## Purpose

Phase 7J documents the provider contracts used by the online-only workflow and converts them into a publicable status matrix. This phase is interpretive and auditable only. It does not modify scoring, ranking, weights, GUI behavior, configuration, or biological interpretation.

## Providers with structured evidence

The following providers can contribute structured computational metadata when required fields and provenance are present:

- UniProt: candidate seed and localization annotations.
- STRING: functional network metadata from structured JSON.
- InterPro: domain overlap metadata from structured JSON.
- BV-BRC: genome or strain metadata when the query resolves to structured JSON.
- Europe PMC: literature metadata from structured JSON.
- Taxonomy: organism identity metadata from structured JSON.
- Human essentiality: local or structured table context for host annotation.

These sources provide computational or contextual metadata. They do not create experimental validation claims by themselves.

## Providers currently degraded

VFDB and DEG remain degraded for automatic evidence use:

- VFDB lacks a stable programmatic route verified by this workflow. HTML, 404, network errors, or unexpected payloads remain unresolved.
- DEG has an official ZIP/download route, but ZIP archives are `unsupported_structured_archive` until a formal adapter is declared and tested.

BV-BRC is conditionally ready. It can use structured JSON, but empty payloads, permission failures, unresolved genome IDs, and 404 responses must not become strong negative evidence.

## Meaning of degraded

Degraded means the transport, endpoint, permission state, payload type, or parser contract was not sufficient to accept structured evidence. It does not mean that the biological feature is absent.

Examples:

- HTML is a page response, not virulence or essentiality evidence.
- Unsupported ZIP is a format gap, not evidence.
- SSL and network errors are transport failures.
- Empty payloads are unresolved or verified-empty provider states, not strong negative evidence.
- Invalid payloads are parser failures, not biological facts.

All provider degradations have `affects_score=false`, `blocks_ranking=false`, and `evidence_inferred=false`, except the `candidate_seed` unresolved state, which blocks online-only ranking because no candidate universe exists.

## Why partial ranking remains valid

The ranking can remain valid as a computational prioritization when:

- the candidate universe is present;
- accepted provider evidence is structured and provenance-bearing;
- degraded providers are clearly marked unresolved;
- missing external enrichment is not interpreted as absence;
- all non-blocking degradation states avoid score effects.

This preserves traceability without overstating evidence.

## Blocking rule

`candidate_seed` is the only strict blocking layer. It defines the online-only candidate universe. Without it, downstream provider enrichment would not have a stable set of candidates to annotate.

STRING, InterPro, VFDB, DEG, BV-BRC, Europe PMC, Taxonomy, UniProt downstream localization, and Human essentiality are not strict blockers. Their failures are provider-status findings.

## Manuscript limitations

A manuscript using this workflow should state:

- Online providers contribute computational metadata, not experimental validation.
- Degraded providers are unresolved and are not evidence of biological absence.
- VFDB requires a stable programmatic route before automatic virulence evidence can be claimed.
- DEG requires a formal ZIP/download adapter before automatic essentiality evidence can be claimed.
- BV-BRC structured JSON should be validated with real queries if strain-level claims are needed.
- STRING and InterPro may degrade on SSL or network failures, especially in Windows environments.
- Candidate seed availability defines the computable online-only universe.

## Future work

The next technical work should focus on:

- VFDB: identify and validate a stable programmatic route.
- DEG: implement a formal, versioned adapter for ZIP or structured downloads.
- BV-BRC: validate real-query behavior for publication-grade strain or genome claims.
- STRING and InterPro: continue conservative Windows SSL and network degradation handling.
