from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .organism_metadata import load_organism_metadata


CURATED_REAL_EVIDENCE_LAYERS: dict[str, dict[str, Any]] = {
    "essentiality": {
        "value_columns": ["essential", "essentiality_score"],
        "database_column": "essentiality_database",
    },
    "virulence": {
        "value_columns": ["virulence_factor", "virulence_score"],
        "database_column": "virulence_database",
    },
    "human_homologs": {
        "value_columns": ["human_homolog", "human_similarity_score", "host_similarity_penalty", "selectivity_score"],
        "database_column": "homology_database",
    },
    "functional_network": {
        "value_columns": [
            "network_centrality",
            "pathway_bottleneck_score",
            "functional_dependency_score",
            "interaction_count",
            "network_source",
        ],
        "database_column": "network_database",
    },
    "strain_conservation": {
        "value_columns": ["strain_coverage_score", "core_genome_presence", "allelic_conservation", "variant_burden"],
        "database_column": "conservation_database",
    },
    "redundancy": {
        "value_columns": ["redundancy_penalty", "low_redundancy_score", "paralog_count", "alternative_pathway_count"],
        "database_column": "redundancy_database",
    },
    "literature_support": {
        "value_columns": ["literature_support_score", "pmid", "finding", "experimental_support"],
        "database_column": "literature_support_database",
    },
}

COMMON_COLUMNS = ["gene", "protein_id", "evidence_status", "evidence_source", "source_database", "reference", "confidence", "notes"]
MATCH_COLUMNS = ["protein_id", "protein_id_canonical", "uniprot_accession", "locus_tag", "gene"]
LOW_EVIDENCE_TOKENS = {
    "unresolved",
    "provider_not_implemented",
    "provider_not_found",
    "missing_optional_layer",
    "placeholder",
    "placeholder_only",
    "demo_only",
    "controlled_context",
    "not_reported",
    "unknown",
}
TEXTUAL_CURATED_COLUMNS = {
    "virulence_factor",
    "network_source",
    "pmid",
    "finding",
    "experimental_support",
    "curated_evidence_layers",
    "curated_evidence_references",
    "curated_evidence_notes",
    "curated_evidence_conflict_flags",
    "curated_evidence_missing_layers",
    "curated_evidence_summary",
    "essentiality_context",
    "curated_essentiality_label",
    "evidence_level",
    "provenance_status",
}
NUMERIC_CURATED_COLUMNS = {
    "essential",
    "essentiality_score",
    "virulence_score",
    "network_centrality",
    "pathway_bottleneck_score",
    "functional_dependency_score",
    "interaction_count",
    "literature_support_score",
}
NUMERIC_COLUMN_SUFFIXES = (
    "_score",
    "_penalty",
    "_count",
    "_coverage",
    "_burden",
    "_conservation",
    "_confidence",
)
ESSENTIAL_TEXT_MAP = {
    "true": 1,
    "yes": 1,
    "contextual_colonization_essential": 1,
    "contextual_colonization_dependency": 1,
    "probable_core_function": 1,
    "false": 0,
    "no": 0,
    "not_viability_essential_known": 0,
}


def apply_curated_real_evidence(base_dir: Path, df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Enrich candidates with traceable local curated evidence when available.

    Curated evidence is not treated as automatically experimental. It can replace
    unresolved, provider-failed, demo, placeholder, or lower-confidence values,
    while preserving stronger online/user evidence unless configured otherwise.
    """
    cfg = _curated_config(config)
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    if not cfg["enabled"]:
        _write_outputs(results_dir, _empty_summary(), _manifest(base_dir, cfg, [], status="disabled"))
        return df.copy()

    organism_keys = _organism_keys(base_dir)
    curated_root = _resolve_curated_root(base_dir, cfg["base_dir"])
    layer_tables = _load_curated_tables(curated_root, organism_keys, cfg)
    if not layer_tables:
        _write_outputs(
            results_dir,
            _empty_summary(missing_layers=list(CURATED_REAL_EVIDENCE_LAYERS)),
            _manifest(base_dir, cfg, organism_keys, status="no_curated_tables", curated_root=curated_root),
        )
        return _ensure_curated_tracking_columns(df.copy(), missing_layers=list(CURATED_REAL_EVIDENCE_LAYERS))

    result = _prepare_curated_result_dtypes(_ensure_curated_tracking_columns(df.copy()))
    summary_rows = []
    manifest_layers = []
    for layer_name, table_info in layer_tables.items():
        table = table_info["table"]
        stats = _apply_layer(result, table, layer_name, cfg)
        summary_rows.append(
            {
                "layer": layer_name,
                "status": "loaded",
                "source_path": str(table_info["path"]),
                "curated_rows": int(len(table)),
                **stats,
            }
        )
        manifest_layers.append(
            {
                "layer": layer_name,
                "status": "loaded",
                "path": str(table_info["path"]),
                "rows": int(len(table)),
                "columns": list(table.columns),
                "matched_candidate_count": int(stats["matched_rows"]),
                "updated_cell_count": int(stats["updated_cells"]),
            }
        )

    missing_layers = [layer for layer in CURATED_REAL_EVIDENCE_LAYERS if layer not in layer_tables]
    for layer in missing_layers:
        summary_rows.append(
            {
                "layer": layer,
                "status": "missing_curated_layer",
                "source_path": "",
                "curated_rows": 0,
                "matched_rows": 0,
                "updated_cells": 0,
                "preserved_existing_cells": 0,
                "conflict_cells": 0,
            }
        )
    result["curated_evidence_missing_layers"] = _append_token_series(result["curated_evidence_missing_layers"], missing_layers)
    _refresh_curated_aggregate_scores(result)
    _write_outputs(
        results_dir,
        pd.DataFrame(summary_rows),
        _manifest(
            base_dir,
            cfg,
            organism_keys,
            status="loaded",
            curated_root=curated_root,
            layers=manifest_layers,
            missing_layers=missing_layers,
        ),
    )
    return result


def _curated_config(config: dict) -> dict[str, Any]:
    cfg = config.get("curated_real_evidence", {}) if isinstance(config, dict) else {}
    precedence = cfg.get("precedence", {}) if isinstance(cfg.get("precedence", {}), dict) else {}
    requested_mode = str(
        config.get("online_sources", {}).get("source_mode_effective")
        or config.get("online_sources", {}).get("source_mode")
        or config.get("online_sources", {}).get("source_mode_default")
        or ""
    ).strip()
    strict_policy = requested_mode in {"online_strict", "online_only"}
    return {
        "enabled": bool(cfg.get("enabled", True)) and not strict_policy,
        "reason": "disabled_by_online_strict_policy" if strict_policy else ("enabled_by_configuration" if cfg.get("enabled", True) else "disabled_by_configuration"),
        "evidence_policy": "online_strict" if strict_policy else ("hybrid_curated" if requested_mode == "hybrid_curated" else "legacy_configured"),
        "base_dir": str(cfg.get("base_dir", "data_curated/organisms")),
        "minimum_confidence": float(cfg.get("minimum_confidence", 0.5)),
        "replace_unresolved": bool(precedence.get("replace_unresolved", True)),
        "preserve_online_real": bool(precedence.get("preserve_online_real", True)),
    }


def _resolve_curated_root(base_dir: Path, configured: str) -> Path:
    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path
    candidates = [
        base_dir / configured_path,
        Path.cwd() / configured_path,
        Path(__file__).resolve().parents[2] / configured_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _organism_keys(base_dir: Path) -> list[str]:
    metadata = load_organism_metadata(base_dir)
    keys = []
    for value in [
        metadata.get("organism"),
        f"{metadata.get('organism', '')}_{metadata.get('strain', '')}",
    ]:
        slug = _slugify(value)
        if slug and slug not in keys:
            keys.append(slug)
    return keys or ["not_reported"]


def _slugify(value: object) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _load_curated_tables(curated_root: Path, organism_keys: list[str], cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    loaded = {}
    for organism_key in organism_keys:
        organism_dir = curated_root / organism_key
        for layer_name in CURATED_REAL_EVIDENCE_LAYERS:
            if layer_name in loaded:
                continue
            path = organism_dir / f"{layer_name}.csv"
            if not path.exists():
                continue
            table = _normalize_curated_table(pd.read_csv(path), layer_name, cfg)
            loaded[layer_name] = {"path": path, "table": table}
    return loaded


def _normalize_curated_table(table: pd.DataFrame, layer_name: str, cfg: dict[str, Any]) -> pd.DataFrame:
    normalized = table.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]
    for column in COMMON_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""
    for column in CURATED_REAL_EVIDENCE_LAYERS[layer_name]["value_columns"]:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized["confidence"] = pd.to_numeric(normalized["confidence"], errors="coerce").fillna(float(cfg["minimum_confidence"]))
    normalized["evidence_status"] = normalized["evidence_status"].fillna("curated_fixture").astype(str)
    normalized["source_database"] = normalized["source_database"].fillna("curated_real_evidence").astype(str)
    normalized["evidence_source"] = normalized["evidence_source"].fillna("curated_real_evidence").astype(str)
    return normalized


def _ensure_curated_tracking_columns(df: pd.DataFrame, missing_layers: list[str] | None = None) -> pd.DataFrame:
    result = df.copy()
    for column in [
        "curated_evidence_layers",
        "curated_evidence_references",
        "curated_evidence_notes",
        "curated_evidence_conflict_flags",
        "curated_evidence_missing_layers",
        "curated_evidence_summary",
    ]:
        if column not in result.columns:
            result[column] = "none"
        else:
            result[column] = result[column].fillna("none").astype(str).replace({"": "none"})
    if "curated_evidence_confidence" not in result.columns:
        result["curated_evidence_confidence"] = 0.0
    else:
        result["curated_evidence_confidence"] = pd.to_numeric(result["curated_evidence_confidence"], errors="coerce").fillna(0.0)
    if "curated_real_evidence_layer_count" not in result.columns:
        result["curated_real_evidence_layer_count"] = 0
    if missing_layers:
        result["curated_evidence_missing_layers"] = _append_token_series(result["curated_evidence_missing_layers"], missing_layers)
    return result


def _prepare_curated_result_dtypes(result: pd.DataFrame) -> pd.DataFrame:
    """Keep curated text fields writable while preserving numeric scoring fields."""
    for layer, spec in CURATED_REAL_EVIDENCE_LAYERS.items():
        TEXTUAL_CURATED_COLUMNS.add(spec["database_column"])
        TEXTUAL_CURATED_COLUMNS.update(
            {
                f"{layer}_source_type",
                f"{layer}_source_name",
                f"{layer}_retrieval_status",
                f"{layer}_database",
            }
        )
        NUMERIC_CURATED_COLUMNS.add(f"{layer}_confidence")

    for column in list(result.columns):
        if _is_textual_curated_column(column):
            result[column] = result[column].astype(object)
        elif _is_numeric_curated_column(column):
            result[column] = pd.to_numeric(result[column], errors="coerce")

    for column in ["essentiality_context", "curated_essentiality_label"]:
        if column not in result.columns:
            result[column] = "none"
        result[column] = result[column].fillna("none").astype(object).replace({"": "none"})
    return result


def _apply_layer(result: pd.DataFrame, table: pd.DataFrame, layer_name: str, cfg: dict[str, Any]) -> dict[str, int]:
    spec = CURATED_REAL_EVIDENCE_LAYERS[layer_name]
    matched_rows = 0
    updated_cells = 0
    preserved_cells = 0
    conflict_cells = 0
    for _, curated_row in table.iterrows():
        matches = _match_candidates(result, curated_row)
        if not matches.any():
            continue
        matched_rows += int(matches.sum())
        for idx in result.index[matches]:
            row_updated = False
            confidence = float(curated_row.get("confidence", cfg["minimum_confidence"]) or cfg["minimum_confidence"])
            for column in spec["value_columns"]:
                value = curated_row.get(column, pd.NA)
                if _is_blank(value):
                    continue
                if _should_replace(result.loc[idx], column, confidence, cfg):
                    assigned = _safe_assign_curated_value(result, idx, column, value, layer_name, curated_row)
                    if not assigned:
                        conflict_cells += 1
                        continue
                    updated_cells += 1
                    row_updated = True
                else:
                    preserved_cells += 1
                    if not _same_value(result.loc[idx].get(column), value):
                        conflict_cells += 1
                        result.at[idx, "curated_evidence_conflict_flags"] = _append_token(
                            result.at[idx, "curated_evidence_conflict_flags"],
                            f"{layer_name}:{column}:preserved_existing",
                        )
            if row_updated:
                _annotate_curated_row(result, idx, curated_row, layer_name, spec, confidence)
    return {
        "matched_rows": matched_rows,
        "updated_cells": updated_cells,
        "preserved_existing_cells": preserved_cells,
        "conflict_cells": conflict_cells,
    }


def _safe_assign_curated_value(
    result: pd.DataFrame,
    idx: Any,
    column: str,
    value: object,
    layer_name: str,
    curated_row: pd.Series,
) -> bool:
    """Assign curated values without letting pandas dtype inference hide evidence."""
    if column == "essential":
        value = _coerce_essential_value(result, idx, value, layer_name)

    if _is_textual_curated_column(column):
        _ensure_object_column(result, column, default="none")
        result.at[idx, column] = str(value)
        return True

    if _is_numeric_curated_column(column):
        if column not in result.columns:
            result[column] = float("nan")
        numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(numeric):
            text = str(value).strip()
            result.at[idx, "curated_evidence_conflict_flags"] = _append_token(
                result.at[idx, "curated_evidence_conflict_flags"],
                f"{layer_name}:{column}:non_numeric_curated_value",
            )
            note = f"{layer_name}:{column}:non_numeric_curated_value={text}"
            result.at[idx, "curated_evidence_notes"] = _append_token(result.at[idx, "curated_evidence_notes"], note)
            result.at[idx, "curated_evidence_summary"] = _append_token(
                result.at[idx, "curated_evidence_summary"],
                note,
            )
            return False
        result.at[idx, column] = numeric
        return True

    if column not in result.columns:
        result[column] = pd.NA
    result.at[idx, column] = value
    return True


def _coerce_essential_value(result: pd.DataFrame, idx: Any, value: object, layer_name: str) -> object:
    if _is_blank(value):
        return value
    text = str(value).strip()
    key = text.casefold()
    if key in ESSENTIAL_TEXT_MAP:
        _preserve_essentiality_label(result, idx, text)
        return ESSENTIAL_TEXT_MAP[key]
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if not pd.isna(numeric):
        return numeric
    result.at[idx, "curated_evidence_conflict_flags"] = _append_token(
        result.at[idx, "curated_evidence_conflict_flags"],
        f"{layer_name}:essential:unrecognized_textual_essential",
    )
    _preserve_essentiality_label(result, idx, text)
    return value


def _preserve_essentiality_label(result: pd.DataFrame, idx: Any, label: str) -> None:
    for column in ["essentiality_context", "curated_essentiality_label"]:
        _ensure_object_column(result, column, default="none")
        result.at[idx, column] = _append_token(result.at[idx, column], label)


def _is_textual_curated_column(column: str) -> bool:
    if column in TEXTUAL_CURATED_COLUMNS:
        return True
    return (
        column.endswith("_context")
        or column.endswith("_label")
        or column.endswith("_source")
        or column.endswith("_source_type")
        or column.endswith("_source_name")
        or column.endswith("_retrieval_status")
        or column.endswith("_database")
        or column.endswith("_notes")
        or column.endswith("_flags")
        or column.endswith("_summary")
        or column in {"reference", "notes", "source_database", "evidence_source", "evidence_status"}
    )


def _is_numeric_curated_column(column: str) -> bool:
    if _is_textual_curated_column(column):
        return False
    return column in NUMERIC_CURATED_COLUMNS or column.endswith(NUMERIC_COLUMN_SUFFIXES)


def _ensure_object_column(result: pd.DataFrame, column: str, default: object = "") -> None:
    if column not in result.columns:
        result[column] = default
    result[column] = result[column].astype(object)


def _match_candidates(df: pd.DataFrame, curated_row: pd.Series) -> pd.Series:
    mask = pd.Series([False] * len(df), index=df.index)
    for column in MATCH_COLUMNS:
        if column not in df.columns or column not in curated_row.index:
            continue
        value = _norm_key(curated_row.get(column))
        if not value:
            continue
        mask = mask | df[column].map(_norm_key).eq(value)
    return mask


def _should_replace(row: pd.Series, column: str, curated_confidence: float, cfg: dict[str, Any]) -> bool:
    current_value = row.get(column, pd.NA)
    if _is_blank(current_value):
        return True
    current_confidence = _row_existing_confidence(row, column)
    if cfg["replace_unresolved"] and _row_has_low_evidence(row):
        return True
    if cfg["preserve_online_real"] and _row_has_real_online_evidence(row) and current_confidence >= curated_confidence:
        return False
    return curated_confidence >= current_confidence


def _row_existing_confidence(row: pd.Series, column: str) -> float:
    layer = _layer_for_column(column)
    candidates = [
        f"{layer}_confidence",
        f"{layer}_layer_confidence",
        f"{layer}_input_confidence",
        "evidence_confidence_score",
    ]
    for candidate in candidates:
        if candidate in row.index:
            value = pd.to_numeric(pd.Series([row.get(candidate)]), errors="coerce").fillna(0.0).iloc[0]
            return float(value)
    return 0.0


def _row_has_low_evidence(row: pd.Series) -> bool:
    text = " ".join(
        str(row.get(column, "") or "").casefold()
        for column in [
            "evidence_level",
            "source_used",
            "retrieval_status",
            "provenance_status",
            "data_realism_flag",
            "audit_flags",
            "missing_evidence_flags",
            "candidate_record_type",
        ]
    )
    return any(token in text for token in LOW_EVIDENCE_TOKENS)


def _row_has_real_online_evidence(row: pd.Series) -> bool:
    text = " ".join(
        str(row.get(column, "") or "").casefold()
        for column in [
            "source_type",
            "essentiality_source_type",
            "virulence_source_type",
            "human_homologs_source_type",
            "functional_network_source_type",
            "strain_conservation_source_type",
            "redundancy_source_type",
            "evidence_source_type",
            "confidence_source_class",
        ]
    )
    return any(token in text for token in ["external", "experimental", "curated", "user"]) and not _row_has_low_evidence(row)


def _annotate_curated_row(
    result: pd.DataFrame,
    idx: Any,
    curated_row: pd.Series,
    layer_name: str,
    spec: dict[str, Any],
    confidence: float,
) -> None:
    source = str(curated_row.get("source_database", "") or curated_row.get("evidence_source", "") or "curated_real_evidence")
    reference = str(curated_row.get("reference", "") or curated_row.get("pmid", "") or "not_reported")
    notes = str(curated_row.get("notes", "") or curated_row.get("finding", "") or "not_reported")
    result.at[idx, "curated_evidence_layers"] = _append_token(result.at[idx, "curated_evidence_layers"], layer_name)
    result.at[idx, "curated_evidence_references"] = _append_token(result.at[idx, "curated_evidence_references"], f"{layer_name}:{reference}")
    result.at[idx, "curated_evidence_notes"] = _append_token(result.at[idx, "curated_evidence_notes"], f"{layer_name}:{notes}")
    result.at[idx, "curated_evidence_confidence"] = max(float(result.at[idx, "curated_evidence_confidence"]), confidence)
    result.at[idx, "curated_real_evidence_layer_count"] = len(_split_tokens(result.at[idx, "curated_evidence_layers"]))
    database_column = spec["database_column"]
    result.at[idx, database_column] = _append_token(str(result.at[idx, database_column]) if database_column in result.columns else "", source)
    for prefix in [layer_name, _layer_for_column(database_column)]:
        result.at[idx, f"{prefix}_source_type"] = "curated_fixture" if "fixture" in source.casefold() else "curated"
        result.at[idx, f"{prefix}_source_name"] = source
        result.at[idx, f"{prefix}_confidence"] = confidence
        result.at[idx, f"{prefix}_retrieval_status"] = "resolved_from_curated_real_evidence"
    result.at[idx, "evidence_level"] = _replace_low_or_append(
        str(result.at[idx, "evidence_level"]) if "evidence_level" in result.columns else "",
        "curated_fixture",
    )
    result.at[idx, "provenance_status"] = _replace_low_or_append(
        str(result.at[idx, "provenance_status"]) if "provenance_status" in result.columns else "",
        "curated_real_evidence",
    )


def _refresh_curated_aggregate_scores(result: pd.DataFrame) -> None:
    if "evidence_quality_score" not in result.columns:
        result["evidence_quality_score"] = 0.0
    result["evidence_quality_score"] = pd.concat(
        [
            pd.to_numeric(result["evidence_quality_score"], errors="coerce").fillna(0.0),
            pd.to_numeric(result["curated_evidence_confidence"], errors="coerce").fillna(0.0),
        ],
        axis=1,
    ).max(axis=1)
    if "confidence_ceiling" not in result.columns:
        result["confidence_ceiling"] = 1.0
    result["confidence_ceiling"] = pd.to_numeric(result["confidence_ceiling"], errors="coerce").fillna(1.0).clip(lower=0.0, upper=1.0)
    if "real_evidence_layer_count" not in result.columns:
        result["real_evidence_layer_count"] = 0
    result["real_evidence_layer_count"] = (
        pd.to_numeric(result["real_evidence_layer_count"], errors="coerce").fillna(0).astype(int)
        + pd.to_numeric(result["curated_real_evidence_layer_count"], errors="coerce").fillna(0).astype(int)
    )
    result["curated_evidence_summary"] = result.apply(_curated_summary, axis=1)


def _curated_summary(row: pd.Series) -> str:
    layers = str(row.get("curated_evidence_layers", "") or "none")
    refs = str(row.get("curated_evidence_references", "") or "none")
    missing = str(row.get("curated_evidence_missing_layers", "") or "none")
    return f"curated_layers={layers}; references={refs}; missing_curated_layers={missing}"


def _layer_for_column(column: str) -> str:
    for layer, spec in CURATED_REAL_EVIDENCE_LAYERS.items():
        if column in spec["value_columns"] or column == spec["database_column"]:
            return layer
    return "curated_real_evidence"


def _write_outputs(results_dir: Path, summary: pd.DataFrame, manifest: dict[str, Any]) -> None:
    summary.to_csv(results_dir / "curated_real_evidence_summary.csv", index=False)
    (results_dir / "curated_real_evidence_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _empty_summary(missing_layers: list[str] | None = None) -> pd.DataFrame:
    if not missing_layers:
        return pd.DataFrame(
            columns=["layer", "status", "source_path", "curated_rows", "matched_rows", "updated_cells", "preserved_existing_cells", "conflict_cells"]
        )
    return pd.DataFrame(
        [
            {
                "layer": layer,
                "status": "missing_curated_layer",
                "source_path": "",
                "curated_rows": 0,
                "matched_rows": 0,
                "updated_cells": 0,
                "preserved_existing_cells": 0,
                "conflict_cells": 0,
            }
            for layer in missing_layers
        ]
    )


def _manifest(
    base_dir: Path,
    cfg: dict[str, Any],
    organism_keys: list[str],
    status: str,
    curated_root: Path | None = None,
    layers: list[dict[str, Any]] | None = None,
    missing_layers: list[str] | None = None,
) -> dict[str, Any]:
    loaded_layers = layers or []
    return {
        "phase": "phase9A_curated_real_evidence",
        "workspace": str(base_dir),
        "status": status,
        "enabled": bool(cfg["enabled"]),
        "reason": str(cfg["reason"]),
        "evidence_policy": str(cfg["evidence_policy"]),
        "matched_candidate_count": sum(int(layer.get("matched_candidate_count", 0)) for layer in loaded_layers),
        "updated_cell_count": sum(int(layer.get("updated_cell_count", 0)) for layer in loaded_layers),
        "curated_root": str(curated_root or _resolve_curated_root(base_dir, cfg["base_dir"])),
        "organism_keys": organism_keys,
        "minimum_confidence": float(cfg["minimum_confidence"]),
        "precedence": {
            "replace_unresolved": bool(cfg["replace_unresolved"]),
            "preserve_online_real": bool(cfg["preserve_online_real"]),
        },
        "layers": loaded_layers,
        "missing_layers": missing_layers or [],
        "interpretation_warning": "Curated fixture/user evidence is traceable input, not automatically experimental validation.",
    }


def _norm_key(value: object) -> str:
    if _is_blank(value):
        return ""
    return str(value).strip().casefold()


def _is_blank(value: object) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.casefold() in {"nan", "none", "null", "not_reported"}


def _same_value(left: object, right: object) -> bool:
    return str(left).strip().casefold() == str(right).strip().casefold()


def _append_token(current: object, token: object) -> str:
    tokens = _split_tokens(current)
    text = str(token or "").strip()
    if text and text not in tokens:
        tokens.append(text)
    return ";".join(tokens)


def _replace_low_or_append(current: object, token: str) -> str:
    tokens = [item for item in _split_tokens(current) if item.casefold() not in LOW_EVIDENCE_TOKENS]
    if token not in tokens:
        tokens.append(token)
    return ";".join(tokens)


def _append_token_series(series: pd.Series, tokens: list[str]) -> pd.Series:
    return series.fillna("").astype(str).map(lambda value: ";".join(_split_tokens(value) + [token for token in tokens if token not in _split_tokens(value)]))


def _split_tokens(value: object) -> list[str]:
    text = str(value or "").strip()
    if not text or text.casefold() in {"none", "not_reported", "nan", "null"}:
        return []
    return [token.strip() for token in text.split(";") if token.strip()]
