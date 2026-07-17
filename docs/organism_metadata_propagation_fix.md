# Organism Metadata Propagation Fix

## Purpose

This change fixes propagation of organism identity metadata in online-only multi-organism runs. The pipeline now reads `organism_profile.json` from the workspace results directory first, which matches the run layout used by organism-specific online-only workspaces.

## Fields

The propagated fields are:

- `organism`
- `strain`
- `taxon_id`

Missing, empty, `null`, `none` or `nan` values are exported as `not_reported`.

## Profile Lookup Order

The loader checks:

1. `workspace/results/organism_profile.json`
2. `workspace/organism_profile.json`
3. `workspace/config/organism_profile.json`

## Field Fallback Rules

For `organism`, the first available value is selected from `organism_canonical_name`, `organism`, `organism_input_name` and `name`.

For `strain`, the first available value is selected from `strain_canonical`, `strain` and `strain_input`.

For `taxon_id`, the first available value is selected from `taxon_id` and `ncbi_taxon_id`.

## Scope And Limitations

This fix does not alter scores, therapeutic role classification or external evidence. It only preserves or repairs organism metadata columns in processed tables and rankings when the workspace profile contains that metadata.

## Next Step

Run the existing online-only multi-organism validation on additional organisms to confirm that each organism workspace keeps distinct metadata through integrated, feature, scored and ranking outputs.
