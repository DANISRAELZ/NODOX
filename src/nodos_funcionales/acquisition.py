from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from .config import load_config
from .validation import DATASET_SPECS, SCHEMAS


DATASET_FILENAMES = {spec.table_key: spec.filename for spec in DATASET_SPECS}


def _alias_list(mapping: dict, key: str) -> list[str]:
    values = mapping.get(key, {})
    if isinstance(values, dict):
        return list(values.keys())
    if isinstance(values, list):
        return list(values)
    return []


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    lowered = {column.casefold(): column for column in df.columns}
    for alias in aliases:
        if alias.casefold() in lowered:
            return lowered[alias.casefold()]
    return None


def map_source_dataframe(df: pd.DataFrame, dataset_key: str, config: dict) -> tuple[pd.DataFrame, dict[str, str]]:
    if dataset_key not in SCHEMAS:
        raise ValueError(f"dataset_key no soportado: {dataset_key}")

    common_aliases = config["dataset_import"]["required_common_columns"]
    dataset_aliases = config["dataset_import"]["dataset_column_aliases"].get(dataset_key, {})
    schema = SCHEMAS[dataset_key]
    renamed = {}

    for canonical in ["protein_id", "gene", "database"]:
        source = _find_column(df, _alias_list(common_aliases, canonical))
        if source:
            renamed[source] = canonical

    for canonical in schema.required + schema.optional:
        if canonical in {"protein_id", "gene", "database"}:
            continue
        source = _find_column(df, _alias_list(dataset_aliases, canonical))
        if source:
            renamed[source] = canonical

    mapped = df.rename(columns=renamed).copy()
    keep = [column for column in ["protein_id", "gene"] + schema.required + schema.optional if column in mapped.columns]
    keep = list(dict.fromkeys(keep))
    return mapped[keep], renamed


def import_user_dataset(
    workspace: Path,
    dataset_key: str,
    input_path: Path,
    project_root: Path,
    copy_source_export: bool = True,
) -> dict[str, object]:
    config = load_config(workspace / "config" / "params.yaml")
    if dataset_key not in DATASET_FILENAMES:
        raise ValueError(f"dataset_key no soportado: {dataset_key}")
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"No se encontro {source}")

    df = pd.read_csv(source)
    mapped, renamed = map_source_dataframe(df, dataset_key, config)

    target = workspace / "data_raw" / DATASET_FILENAMES[dataset_key]
    target.parent.mkdir(parents=True, exist_ok=True)
    mapped.to_csv(target, index=False)

    copied_source = None
    if copy_source_export:
        source_dir = workspace / "data_raw" / "source_exports"
        source_dir.mkdir(parents=True, exist_ok=True)
        copied_source = source_dir / source.name
        shutil.copy2(source, copied_source)

    return {
        "dataset_key": dataset_key,
        "target_path": target,
        "source_rows": len(df),
        "mapped_rows": len(mapped),
        "renamed_columns": renamed,
        "copied_source": copied_source,
    }
