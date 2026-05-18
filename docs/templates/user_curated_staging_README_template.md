# User-Curated Staging README Template

Copy this template manually into a local ignored staging folder, for example:

```text
user_curated_staging/<project_id>/README.md
```

Do not use this file to store sensitive data in the repository. The local
staging README should summarize what is present, where it came from, and what
has or has not been reviewed before any import step.

## Editable Fields

| Field | Value |
| --- | --- |
| `project_id` | `<project_id>` |
| `organism` | `<organism>` |
| `strain_or_isolate` | `<strain_or_isolate>` |
| `curator` | `<curator>` |
| `date_created` | `<YYYY-MM-DD>` |
| `manifest_path` | `<relative_or_local_manifest_path>` |
| `raw_inputs_summary` | `<short_summary_of_raw_input_files>` |
| `provenance_summary` | `<short_summary_of_sources_versions_or_references>` |
| `excluded_or_missing_data` | `<known_missing_excluded_or_unusable_data>` |
| `validation_status` | `<not_started_or_in_review_or_prevalidated_or_blocked>` |
| `notes` | `<scope_limits_decisions_or_open_questions>` |

## Staging Contents

Use this section in the local copy to list files without pasting sensitive
content.

| Local file or folder | Purpose | Source type | Review status |
| --- | --- | --- | --- |
| `<path>` | `<purpose>` | `user_curated` | `<status>` |

## Provenance Checklist

- [ ] The organism and strain/isolate/scope are explicitly declared.
- [ ] Each raw input has a matching row in the manifest.
- [ ] Each manifest row uses `source_type=user_curated` only for data reviewed
  or provided by the user.
- [ ] Demo, proxy, cache, online, and `controlled_reference` files are not
  mixed into the real `user_curated` evidence.
- [ ] Missing, excluded, weak, inferred, or proxy-like evidence is documented.
- [ ] The manifest was prevalidated before import.
- [ ] Manual review was accepted before any import step.

## Validation Log

Record commands and outcomes in the local copy. Do not paste sensitive data.

```text
<YYYY-MM-DD> <command_or_review_step> <outcome>
```

Recommended prevalidation commands:

```powershell
.\.venv\Scripts\python.exe scripts\validate_user_curated_manifest.py <ruta_manifest.csv>
powershell -ExecutionPolicy Bypass -File .\scripts\validate_user_curated_manifest.ps1 <ruta_manifest.csv>
```

Recommended prevalidated import pattern:

```powershell
.\.venv\Scripts\python.exe import_dataset.py --organism "ORGANISM_NAME" --strain "STRAIN_OR_SCOPE" --workspace <workspace_temporal_o_dedicado> --dataset <dataset> --input <archivo_real.csv> --validate-user-curated-manifest <ruta_manifest.csv>
```

## Warnings

- Do not version real, private, clinical, sensitive, or unreleased data.
- Do not run `git add .` from a directory that may include local staging data.
- Do not mix demo, proxy, cache, online, or `controlled_reference` material into
  `user_curated` evidence.
- Do not run scoring or pipeline before manual review accepts the manifest,
  files, provenance, missingness, and limitations.
- Do not interpret manifest prevalidation as biological, therapeutic, or
  clinical validation.
- Do not treat a future score as proof that a therapeutic target is clinically
  valid.
