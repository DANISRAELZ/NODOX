from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from .validation import DATASET_SPECS


def normalize_identifier(value: object) -> str:
    return str(value).strip().upper().replace(" ", "_")


def normalize_gene_symbol(value: object, unknown_label: str) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return unknown_label
    return text.upper()


def _load_uniprot_annotations(raw_dir: Path) -> pd.DataFrame | None:
    path = raw_dir / "uniprot_annotations.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "protein_id" not in df.columns:
        return None
    df["protein_id_canonical"] = df["protein_id"].map(normalize_identifier)
    return df


def normalize_all(base_dir: Path, config: dict) -> None:
    processed_dir = base_dir / "data_processed"
    raw_dir = base_dir / "data_raw"
    unknown_gene = config["mapping"]["unknown_gene_symbol"]
    mapping_confidence = float(config["mapping"]["mapping_confidence_default"])
    uniprot = _load_uniprot_annotations(raw_dir)
    if uniprot is not None:
        uniprot.to_csv(processed_dir / "normalized_uniprot_annotations.csv", index=False)

    for spec in DATASET_SPECS:
        validated_path = processed_dir / f"validated_{spec.filename}"
        if not validated_path.exists():
            continue

        try:
            df = pd.read_csv(validated_path)
        except EmptyDataError:
            continue

        df["protein_id_original"] = df["protein_id"].astype("string")
        df["protein_id_canonical"] = df["protein_id"].map(normalize_identifier)
        df["protein_id"] = df["protein_id_canonical"]
        if uniprot is not None:
            uniprot_subset = uniprot[
                [
                    column
                    for column in [
                        "protein_id_canonical",
                        "uniprot_accession",
                        "uniprot_id",
                        "uniprot_reviewed",
                        "uniprot_protein_name",
                        "uniprot_gene_primary",
                        "uniprot_gene_names",
                        "uniprot_match_status",
                        "provider",
                        "source_used",
                    ]
                    if column in uniprot.columns
                ]
            ].drop_duplicates(subset=["protein_id_canonical"])
            df = df.merge(uniprot_subset, on="protein_id_canonical", how="left")
            if "uniprot_gene_primary" in df.columns:
                missing_gene = df["gene"].astype(str).str.strip().isin(["", "nan", "None"])
                df.loc[missing_gene, "gene"] = df.loc[missing_gene, "uniprot_gene_primary"]
        df["gene_symbol_normalized"] = df["gene"].map(lambda value: normalize_gene_symbol(value, unknown_gene))
        if "database" in df.columns:
            df["source_database"] = df["database"].fillna("unknown").astype(str)
        else:
            df["source_database"] = spec.table_key
        df["mapping_confidence"] = mapping_confidence

        output_path = processed_dir / f"normalized_{spec.filename}"
        df.to_csv(output_path, index=False)
