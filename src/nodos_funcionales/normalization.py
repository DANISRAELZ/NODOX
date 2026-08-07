from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from .validation import DATASET_SPECS


BV_BRC_CONSERVATION_PROVENANCE_COLUMNS = (
    "conservation_source_record",
    "conservation_source_version",
    "conservation_retrieved_at",
    "conservation_mapping_method",
    "conservation_mapping_status",
    "conservation_evidence_status",
    "conservation_evidence_confidence",
    "conservation_independence_group",
    "conservation_method_scope",
    "conservation_taxon_id",
    "conservation_provider_retrieval_status",
    "conservation_provider_query_cache_key",
    "conservation_provider_source_used",
)


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


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _annotate_bvbrc_conservation_provenance(
    base_dir: Path,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Attach stable provider-query provenance to BV-BRC conservation rows.

    The BV-BRC provider manifest preserves the original `generated_at_utc` and
    query cache key when a completed query is reused from cache. Stage 4C copies
    those fields into each normalized conservation row instead of regenerating a
    scoring-time timestamp.
    """

    annotated = df.copy()
    manifest = _read_json(base_dir / "results" / "bvbrc_conservation_manifest.json")
    if not manifest:
        return annotated

    query_complete = bool(manifest.get("query_complete", False))
    provider_success = bool(manifest.get("provider_success", False))
    retrieval_status = str(manifest.get("retrieval_status") or "").strip().lower()
    source_used = str(manifest.get("source_used") or "").strip().lower()
    retrieved_at = str(manifest.get("generated_at_utc") or "").strip()
    query_cache_key = str(manifest.get("query_cache_key") or "").strip()
    taxon_id = str(manifest.get("taxon_id") or "").strip()
    genomes_retrieved = manifest.get("genomes_retrieved")

    usable_status = retrieval_status == "api_real" or (
        source_used == "cache" and retrieval_status == "api_real"
    )
    if not (
        query_complete
        and provider_success
        and usable_status
        and retrieved_at
        and query_cache_key
        and taxon_id
    ):
        return annotated

    database_series = annotated.get(
        "database",
        pd.Series([""] * len(annotated), index=annotated.index),
    ).fillna("").astype(str).str.lower()
    bvbrc_mask = database_series.str.contains("bv-brc|bvbrc|patric", regex=True)
    if not bvbrc_mask.any():
        return annotated

    for column in BV_BRC_CONSERVATION_PROVENANCE_COLUMNS:
        if column not in annotated.columns:
            annotated[column] = pd.NA

    source_version = f"bvbrc_unversioned_snapshot@{retrieved_at}"
    independence_group = f"bvbrc_strain_conservation_taxon_{taxon_id}"
    method_scope = (
        "BV-BRC candidate gene query within explicit taxon scope; "
        f"query_complete=true; genomes_retrieved={genomes_retrieved}; "
        "provider database release is not exposed by the current adapter"
    )

    for index in annotated.index[bvbrc_mask]:
        protein_id = str(annotated.at[index, "protein_id"] or "").strip()
        gene = str(annotated.at[index, "gene"] or "").strip()
        annotated.at[index, "conservation_source_record"] = (
            f"{query_cache_key};candidate={protein_id};gene={gene}"
        )
        annotated.at[index, "conservation_source_version"] = source_version
        annotated.at[index, "conservation_retrieved_at"] = retrieved_at
        annotated.at[index, "conservation_mapping_method"] = (
            "bvbrc_gene_filter_with_taxon_scope"
        )
        annotated.at[index, "conservation_mapping_status"] = "exact_gene_and_taxon"
        annotated.at[index, "conservation_evidence_status"] = "observed"
        annotated.at[index, "conservation_evidence_confidence"] = "moderate"
        annotated.at[index, "conservation_independence_group"] = independence_group
        annotated.at[index, "conservation_method_scope"] = method_scope
        annotated.at[index, "conservation_taxon_id"] = taxon_id
        annotated.at[index, "conservation_provider_retrieval_status"] = retrieval_status
        annotated.at[index, "conservation_provider_query_cache_key"] = query_cache_key
        annotated.at[index, "conservation_provider_source_used"] = source_used

    return annotated


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

        if spec.table_key == "strain_conservation":
            df = _annotate_bvbrc_conservation_provenance(base_dir, df)

        output_path = processed_dir / f"normalized_{spec.filename}"
        df.to_csv(output_path, index=False)
