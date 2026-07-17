from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ORGANISM_METADATA_COLUMNS = ["organism", "strain", "taxon_id"]
NOT_REPORTED = "not_reported"
_EMPTY_TOKENS = {"", "null", "none", "nan"}


def normalize_metadata_value(value: Any) -> Any:
    """Return an explicit missing marker for empty organism metadata values."""
    if value is None:
        return NOT_REPORTED
    if pd.isna(value):
        return NOT_REPORTED
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.casefold() in _EMPTY_TOKENS:
            return NOT_REPORTED
        return stripped
    return value


def load_organism_metadata(base_dir: Path) -> dict[str, Any]:
    """Load organism identity from the known workspace profile locations.

    The online-only multi-organism runner writes the profile under
    `workspace/results/organism_profile.json`; older or manually assembled
    workspaces can keep it in the workspace root or config directory.
    """
    profile = _load_first_profile(base_dir)
    return {
        "organism": _first_available(
            profile,
            [
                "run_organism",
                "registry_organism",
                "organism",
                "organism_input_name",
                "name",
                "organism_canonical_name",
            ],
        ),
        "strain": _first_available(
            profile,
            [
                "run_strain",
                "registry_strain",
                "strain",
                "strain_input",
                "strain_canonical",
            ],
        ),
        "taxon_id": _first_available(
            profile,
            [
                "run_taxon_id",
                "registry_taxon_id",
                "taxon_id",
                "ncbi_taxon_id",
                "provider_taxon_id",
            ],
        ),
    }


def apply_organism_metadata(
    df: pd.DataFrame,
    metadata: dict[str, Any],
    *,
    overwrite_not_reported: bool,
) -> pd.DataFrame:
    """Ensure organism metadata columns exist and optionally repair missing markers."""
    result = df.copy()
    for column in ORGANISM_METADATA_COLUMNS:
        value = normalize_metadata_value(metadata.get(column))
        if column not in result.columns:
            result[column] = pd.Series([str(value)] * len(result), index=result.index, dtype="string")
            continue
        result[column] = result[column].astype("string")
        if overwrite_not_reported:
            missing_mask = result[column].map(_is_missing_metadata_value)
            result.loc[missing_mask, column] = str(value)
    return result


def _load_first_profile(base_dir: Path) -> dict[str, Any]:
    for path in [
        base_dir / "results" / "organism_profile.json",
        base_dir / "organism_profile.json",
        base_dir / "config" / "organism_profile.json",
    ]:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    return {}


def _first_available(profile: dict[str, Any], fields: list[str]) -> Any:
    for field in fields:
        value = normalize_metadata_value(profile.get(field))
        if value != NOT_REPORTED:
            return value
    return NOT_REPORTED


def _is_missing_metadata_value(value: Any) -> bool:
    return normalize_metadata_value(value) == NOT_REPORTED
