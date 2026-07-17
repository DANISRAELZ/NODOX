# Online-only provider not-found handling

## Purpose

This phase makes online-only organism runs tolerant to provider-specific missing resources such as `HTTP 404` or `not_found`.

## Rule

Provider not-found errors are operational retrieval failures. They do not mean that a biological feature is absent.

When enough candidate identifiers already exist, required downstream layers may be materialized as conservative unresolved rows:

- `retrieval_status = unresolved`
- `source_database = provider_not_found`
- `evidence = unresolved`

## Audit

The fallback writes `results/online_only_unresolved_required_fallback_manifest.json` with the original seed status and fallback reason.

## Limitations

This does not improve biological evidence or scoring. It only prevents a single missing provider resource from stopping an otherwise auditable online-only run.

## Future steps

Connect additional real providers incrementally behind the existing layer resolver and keep provider-specific not-found states explicit in manifests.
