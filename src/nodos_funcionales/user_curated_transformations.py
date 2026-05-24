from __future__ import annotations

from pathlib import Path

import pandas as pd


USER_CURATED_CONSERVATION_REQUIRED_COLUMNS = [
    "organism",
    "strain",
    "protein_id",
    "gene",
    "conservation_scope",
    "core_genome_presence",
    "strain_coverage_score",
    "allelic_conservation",
    "variant_burden",
    "source_database",
    "evidence_status",
    "curator_notes",
]

STRAIN_CONSERVATION_TEMPLATE_COLUMNS = [
    "protein_id",
    "gene",
    "core_genome_presence",
    "strain_coverage_score",
    "allelic_conservation",
    "variant_burden",
    "database",
]


def transform_user_curated_conservation_to_strain_conservation(input_path: str | Path) -> pd.DataFrame:
    """Transform a user-curated conservation CSV into strain_conservation shape.

    The transformation is deliberately conservative: it preserves observed
    conservation values and traceability metadata, but does not compute scores,
    infer risk, import a layer, or write files.
    """
    source = Path(input_path)
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    _validate_user_curated_conservation_columns(df.columns)

    rows: list[dict[str, str]] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "protein_id": _clean(row["protein_id"]),
                "gene": _clean(row["gene"]),
                "core_genome_presence": _normalize_core_genome_presence(row["core_genome_presence"]),
                "strain_coverage_score": _clean(row["strain_coverage_score"]),
                "allelic_conservation": _clean(row["allelic_conservation"]),
                "variant_burden": _clean(row["variant_burden"]),
                "database": _build_traceable_database_field(row),
            }
        )

    return pd.DataFrame(rows, columns=STRAIN_CONSERVATION_TEMPLATE_COLUMNS)


def _validate_user_curated_conservation_columns(columns: pd.Index) -> None:
    present = {str(column) for column in columns}
    missing = [column for column in USER_CURATED_CONSERVATION_REQUIRED_COLUMNS if column not in present]
    if missing:
        raise ValueError(
            "user_curated conservation CSV is missing required columns: "
            + ", ".join(missing)
        )


def _normalize_core_genome_presence(value: object) -> str:
    cleaned = _clean(value)
    lowered = cleaned.casefold()
    if lowered in {"true", "yes", "y"}:
        return "1"
    if lowered in {"false", "no", "n"}:
        return "0"
    return cleaned


def _build_traceable_database_field(row: pd.Series) -> str:
    metadata = [
        ("source_database", row["source_database"]),
        ("source_type", "user_curated"),
        ("organism", row["organism"]),
        ("strain", row["strain"]),
        ("conservation_scope", row["conservation_scope"]),
        ("evidence_status", row["evidence_status"]),
        ("curator_notes", row["curator_notes"]),
    ]
    return "; ".join(f"{key}={_clean(value)}" for key, value in metadata)


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()
