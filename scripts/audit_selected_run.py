#!/usr/bin/env python3
"""Build a run-specific evidence and provenance audit for NODOX.

Stage 4B separates historical/proxy evolutionary information from evidence that
has passed the Stage 4A explicit-evidence contract. Legacy explicit flags remain
visible for audit, but they do not become supported evidence by themselves.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.nodos_funcionales.config import parse_simple_yaml

DEFAULT_STAGE2_CONFIG = {
    "version": 2,
    "selected_run": {
        "expected_candidate_count": 25,
        "ranking_table_priority": [
            "ranking_nodos_phase3_real_candidates.csv",
            "ranking_nodos_phase3.csv",
            "ranking_nodos.csv",
        ],
        "feature_table_priority": ["phase3_features.csv"],
        "provider_audit_names": ["online_only_provider_audit.csv"],
        "diamond_manifest_names": ["human_homology_diamond_manifest.json"],
    },
}
DEFAULT_RANKING_PRIORITY = tuple(
    DEFAULT_STAGE2_CONFIG["selected_run"]["ranking_table_priority"]
)
DEFAULT_FEATURE_PRIORITY = ("phase3_features.csv",)
DEFAULT_PROVIDER_AUDITS = ("online_only_provider_audit.csv",)
DEFAULT_DIAMOND_MANIFESTS = ("human_homology_diamond_manifest.json",)
IDENTITY_COLUMNS = (
    "protein_id",
    "accession",
    "entry",
    "uniprot_accession",
    "gene",
    "gene_name",
    "locus_tag",
)
EVOLUTIONARY_COLUMNS = (
    "mutation_tolerance_score",
    "mutational_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "evolutionary_space_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
    "evolutionary_escape_risk_score",
    "evolutionary_robustness_score",
    "reduced_evolutionary_space_score",
    "redundancy_penalty",
    "biofilm_escape_penalty",
    "horizontal_transfer_penalty",
    "alternative_pathway_score",
    "metabolic_bypass_score",
    "regulatory_bypass_score",
    "pathway_alternative_count",
    "variant_burden",
    "low_redundancy_score",
    "functional_backup_score",
)
CONTRACT_VARIABLES = (
    "mutation_tolerance_score",
    "functional_redundancy_escape_score",
    "compensatory_pathway_score",
    "fitness_cost_of_escape",
    "evolutionary_constraint_score",
    "resistance_emergence_risk",
    "multi_node_dependency_score",
)
TRUE_VALUES = {
    "1",
    "true",
    "yes",
    "y",
    "success",
    "succeeded",
    "available",
    "supported",
}
FALSE_VALUES = {
    "0",
    "false",
    "no",
    "n",
    "failed",
    "failure",
    "unavailable",
}
UNKNOWN_EVOLUTIONARY_STATUSES = {
    "unknown_missing_evidence",
    "unknown",
    "missing",
    "not_reported",
    "unresolved",
    "insufficient_evidence",
    "insufficient_independent_evidence",
    "derived_from_related_layers",
}
PROVIDER_LAYER_MAP = {
    "candidate_seed": ("uniprot", "candidate_seed"),
    "functional_network": ("string", "functional_network"),
    "protein_annotation": ("interpro", "protein_annotation", "host_annotation"),
    "strain_conservation": ("bvbrc", "strain_conservation"),
    "virulence": ("vfdb", "virulence"),
    "essentiality": ("deg", "essentiality", "contextual_essentiality"),
    "human_homology": ("diamond", "human_homology"),
}


@dataclass(frozen=True)
class SelectedArtifact:
    kind: str
    path: str
    size_bytes: int
    sha256: str


def _deep_merge(
    base: Mapping[str, Any],
    override: Mapping[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_stage2_config(path: Path) -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_STAGE2_CONFIG)
    if not path.exists():
        return config
    try:
        raw = path.read_text(encoding="utf-8")
        loaded = (
            json.loads(raw)
            if path.suffix.lower() == ".json"
            else parse_simple_yaml(raw)
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return config
    return _deep_merge(config, loaded) if isinstance(loaded, Mapping) else config


def _git(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "not_available"
    return completed.stdout.strip() or "not_available"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path_priority(
    path: Path,
    ordered_names: Sequence[str],
) -> tuple[int, int, str]:
    name_rank = (
        list(ordered_names).index(path.name)
        if path.name in ordered_names
        else len(ordered_names)
    )
    lowered = path.as_posix().lower()
    if "workspace/data_processed" in lowered:
        location_rank = 0
    elif "workspace/results" in lowered:
        location_rank = 1
    elif "review_package" in lowered:
        location_rank = 2
    else:
        location_rank = 3
    return name_rank, location_rank, lowered


def find_best_artifact(
    run_dir: Path,
    ordered_names: Sequence[str],
) -> Path | None:
    matches = [
        path
        for name in ordered_names
        for path in run_dir.rglob(name)
        if path.is_file()
    ]
    return (
        sorted(set(matches), key=lambda path: _path_priority(path, ordered_names))[0]
        if matches
        else None
    )


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise RuntimeError(f"No se pudo leer {path}: {exc}") from exc


def _normalize_bool(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "not_reported"
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return "true"
    if text in FALSE_VALUES:
        return "false"
    return "not_reported" if not text or text == "nan" else text


def _bool_mask(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    return frame[column].map(_normalize_bool).eq("true")


def _first_existing(
    columns: Iterable[str],
    candidates: Sequence[str],
) -> str | None:
    available = set(columns)
    return next((column for column in candidates if column in available), None)


def _candidate_identifier(frame: pd.DataFrame) -> pd.Series:
    id_columns = [column for column in IDENTITY_COLUMNS if column in frame.columns]
    if not id_columns:
        return pd.Series(
            [f"candidate_{index + 1}" for index in range(len(frame))],
            index=frame.index,
            dtype="string",
        )
    values = frame[id_columns].astype("string").replace(
        {"<NA>": pd.NA, "nan": pd.NA, "": pd.NA}
    )
    fallback = pd.Series(
        [f"candidate_{index + 1}" for index in range(len(frame))],
        index=frame.index,
        dtype="string",
    )
    return values.bfill(axis=1).iloc[:, 0].fillna(fallback)


def _common_identity(left: pd.DataFrame, right: pd.DataFrame) -> str | None:
    return next(
        (
            column
            for column in IDENTITY_COLUMNS
            if column in left.columns and column in right.columns
        ),
        None,
    )


def select_candidate_features(
    feature_frame: pd.DataFrame,
    ranking_frame: pd.DataFrame,
) -> pd.DataFrame:
    key = _common_identity(feature_frame, ranking_frame)
    if key is None:
        if len(feature_frame) == len(ranking_frame):
            return feature_frame.copy().reset_index(drop=True)
        raise ValueError(
            "No se pudo alinear la tabla de características con el ranking"
        )
    ranked_ids = ranking_frame[key].astype(str)
    features = feature_frame.copy()
    features[key] = features[key].astype(str)
    features = features.drop_duplicates(subset=[key], keep="first").set_index(key)
    missing = [value for value in ranked_ids if value not in features.index]
    if missing:
        raise ValueError(
            f"Faltan {len(missing)} candidatos del ranking en phase3_features: "
            f"{missing[:5]}"
        )
    return features.loc[ranked_ids].reset_index()


def _source_state(frame: pd.DataFrame, variable: str) -> pd.Series:
    """Return an audit state without upgrading legacy flags to contract evidence."""

    contract_flag = f"{variable}_contract_explicit"
    requested_flag = f"{variable}_is_explicit"
    source_column = f"{variable}_source_type"

    if contract_flag in frame.columns:
        contract = _bool_mask(frame, contract_flag)
        requested = _bool_mask(frame, requested_flag)
        state = pd.Series("derived_or_not_contract_explicit", index=frame.index)
        state.loc[requested & ~contract] = "requested_explicit_rejected_by_contract"
        state.loc[contract] = "contract_explicit"
        return state

    if requested_flag in frame.columns:
        requested = _bool_mask(frame, requested_flag)
        return requested.map(
            {
                True: "legacy_explicit_unvalidated",
                False: "derived_or_not_contract_explicit",
            }
        )
    if source_column in frame.columns:
        source = (
            frame[source_column]
            .fillna("not_reported")
            .astype(str)
            .str.strip()
            .str.lower()
            .replace({"": "not_reported", "nan": "not_reported"})
        )
        return source.map(
            lambda value: (
                "missing"
                if value in {"missing", "not_reported", "unknown", "unresolved"}
                else "source_reported_unvalidated"
            )
        )
    if variable in frame.columns:
        numeric = pd.to_numeric(frame[variable], errors="coerce")
        return numeric.notna().map(
            {True: "value_present_source_unknown", False: "missing"}
        )
    return pd.Series(["missing"] * len(frame), index=frame.index)


def build_candidate_audit(frame: pd.DataFrame) -> pd.DataFrame:
    output = pd.DataFrame(index=frame.index)
    output["candidate_id"] = _candidate_identifier(frame)
    for column in (*IDENTITY_COLUMNS, "organism", "taxon_id"):
        if column in frame.columns and column not in output.columns:
            output[column] = frame[column]

    numeric_columns = (
        "functional_node_theory_score",
        "functional_node_theory_confidence",
        "meta_priority_score",
        "meta_priority_score_v3",
        "priority_score",
        "evolutionary_escape_risk_score",
        "evolutionary_escape_proxy_score",
        "evolutionary_escape_supported_score",
        "evolutionary_constraint_score",
        "evolutionary_space_constraint_score",
        "evidence_quality_score",
        "evidence_coverage_score",
        "host_similarity_penalty",
        "host_similarity_risk",
    )
    for column in numeric_columns:
        if column in frame.columns:
            output[column] = pd.to_numeric(frame[column], errors="coerce")

    contract_explicit_counts = pd.Series(0, index=frame.index, dtype=int)
    legacy_requested_counts = pd.Series(0, index=frame.index, dtype=int)
    derived_counts = pd.Series(0, index=frame.index, dtype=int)
    missing_counts = pd.Series(0, index=frame.index, dtype=int)

    for variable in EVOLUTIONARY_COLUMNS:
        state = _source_state(frame, variable)
        if (
            variable in frame.columns
            or f"{variable}_is_explicit" in frame.columns
            or f"{variable}_contract_explicit" in frame.columns
            or f"{variable}_source_type" in frame.columns
        ):
            output[f"{variable}__evidence_state"] = state
        if variable in CONTRACT_VARIABLES:
            contract_explicit_counts += state.eq("contract_explicit").astype(int)
            legacy_requested_counts += state.isin(
                {
                    "legacy_explicit_unvalidated",
                    "requested_explicit_rejected_by_contract",
                }
            ).astype(int)
        derived_counts += state.isin(
            {
                "derived_or_not_contract_explicit",
                "value_present_source_unknown",
                "source_reported_unvalidated",
                "legacy_explicit_unvalidated",
                "requested_explicit_rejected_by_contract",
            }
        ).astype(int)
        missing_counts += state.eq("missing").astype(int)

    if "evolutionary_escape_risk_explicit_variable_count" in frame.columns:
        contract_explicit_counts = pd.to_numeric(
            frame["evolutionary_escape_risk_explicit_variable_count"],
            errors="coerce",
        ).fillna(0).clip(lower=0).astype(int)
    if "evolutionary_escape_risk_available_variable_count" in frame.columns:
        available = pd.to_numeric(
            frame["evolutionary_escape_risk_available_variable_count"],
            errors="coerce",
        ).fillna(0).clip(lower=0).astype(int)
        derived_counts = (available - contract_explicit_counts).clip(lower=0)

    group_counts = (
        pd.to_numeric(
            frame["evolutionary_escape_risk_independent_evidence_group_count"],
            errors="coerce",
        ).fillna(0).clip(lower=0).astype(int)
        if "evolutionary_escape_risk_independent_evidence_group_count"
        in frame.columns
        else pd.Series(0, index=frame.index, dtype=int)
    )
    contract_supported = _bool_mask(
        frame,
        "evolutionary_evidence_contract_supported",
    )

    output["evolutionary_explicit_variable_count"] = contract_explicit_counts
    output["evolutionary_legacy_requested_explicit_variable_count"] = (
        legacy_requested_counts
    )
    output["evolutionary_independent_evidence_group_count"] = group_counts
    output["evolutionary_evidence_contract_supported"] = contract_supported
    output["evolutionary_derived_or_proxy_variable_count"] = derived_counts
    output["evolutionary_missing_variable_count"] = missing_counts

    passthrough_columns = (
        "evolutionary_escape_risk_explicit_variables",
        "evolutionary_escape_risk_independence_groups",
        "evolutionary_escape_evidence_mode",
        "evolutionary_escape_supported_status",
        "evolutionary_evidence_contract_record_count",
        "evolutionary_evidence_contract_valid_record_count",
        "evolutionary_evidence_contract_explicit_record_count",
        "evolutionary_evidence_contract_rejected_explicit_record_count",
        "evolutionary_evidence_contract_errors",
        "evolutionary_evidence_contract_warnings",
    )
    for column in passthrough_columns:
        if column in frame.columns:
            output[column] = frame[column]

    status_column = _first_existing(
        frame.columns,
        (
            "evolutionary_escape_risk_status",
            "evolutionary_escape_status",
            "evolutionary_risk_status",
        ),
    )
    if status_column:
        output["evolutionary_escape_risk_status"] = frame[status_column].fillna(
            "not_reported"
        )
    else:
        output["evolutionary_escape_risk_status"] = "not_reported"

    output["scientific_interpretation_guard"] = output[
        "evolutionary_escape_risk_status"
    ].map(
        lambda status: (
            "unknown_is_not_low_risk"
            if str(status).strip().lower() in UNKNOWN_EVOLUTIONARY_STATUSES
            else "contract_supported_interpretation_allowed"
            if str(status).strip().lower() == "sufficient_evidence"
            else "interpret_with_reported_evidence"
        )
    )
    output.loc[
        ~contract_supported,
        "scientific_interpretation_guard",
    ] = "not_contract_supported_do_not_treat_as_supported_risk"
    return output


def build_provider_summary(frame: pd.DataFrame | None) -> pd.DataFrame:
    columns = [
        "provider",
        "retrieval_status",
        "connectivity_success",
        "retrieval_success",
        "mapping_success",
        "usable_evidence",
        "affects_score",
        "matched_candidate_count",
        "usable_candidate_count",
        "updated_cell_count",
        "notes",
    ]
    if frame is None or frame.empty:
        return pd.DataFrame(
            [
                {
                    "provider": "not_available",
                    "retrieval_status": "provider_audit_not_found",
                }
            ],
            columns=columns,
        )
    provider_column = _first_existing(
        frame.columns,
        ("provider", "source", "provider_name", "layer"),
    )
    output = pd.DataFrame(index=frame.index)
    output["provider"] = (
        frame[provider_column].astype(str)
        if provider_column
        else "not_reported"
    )
    boolean_columns = {
        "connectivity_success",
        "retrieval_success",
        "mapping_success",
        "usable_evidence",
        "affects_score",
    }
    for column in columns[1:]:
        if column in frame.columns:
            output[column] = (
                frame[column].map(_normalize_bool)
                if column in boolean_columns
                else frame[column]
            )
        else:
            output[column] = "not_reported"
    return output[columns]


def _numeric_max(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns or frame.empty:
        return 0
    values = pd.to_numeric(frame[column], errors="coerce")
    return int(values.max()) if values.notna().any() else 0


def build_layer_coverage(
    candidate_frame: pd.DataFrame,
    provider_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total = len(candidate_frame)
    providers = provider_summary.copy()
    providers["provider_lower"] = providers["provider"].astype(str).str.lower()

    for layer, tokens in PROVIDER_LAYER_MAP.items():
        related = providers[
            providers["provider_lower"].map(
                lambda value: any(token in value for token in tokens)
            )
        ]
        mapped = _numeric_max(related, "matched_candidate_count")
        usable = _numeric_max(related, "usable_candidate_count")
        if (
            usable == 0
            and not related.empty
            and related["usable_evidence"].astype(str).str.lower().eq("true").any()
        ):
            usable = mapped
        if layer == "candidate_seed":
            mapped = max(mapped, total)
            usable = max(usable, total)
        rows.append(
            {
                "layer": layer,
                "candidate_count": total,
                "mapped_candidate_count": min(mapped, total) if total else mapped,
                "usable_candidate_count": min(usable, total) if total else usable,
                "usable_fraction": (min(usable, total) / total) if total else 0.0,
                "provider_rows": (
                    "; ".join(related["provider"].astype(str).tolist()) or "none"
                ),
                "interpretation": (
                    "provider_audit_usable_evidence"
                    if usable > 0
                    else "no_usable_candidate_evidence_reported"
                ),
            }
        )

    available = pd.to_numeric(
        candidate_frame.get("evolutionary_escape_risk_available_variable_count", 0),
        errors="coerce",
    )
    if not isinstance(available, pd.Series):
        available = pd.Series([0] * total, index=candidate_frame.index)
    proxy_available_count = int(available.fillna(0).gt(0).sum())
    contract_supported = _bool_mask(
        candidate_frame,
        "evolutionary_evidence_contract_supported",
    )
    supported_count = int(contract_supported.sum())
    partial_explicit = pd.to_numeric(
        candidate_frame.get("evolutionary_escape_risk_explicit_variable_count", 0),
        errors="coerce",
    )
    if not isinstance(partial_explicit, pd.Series):
        partial_explicit = pd.Series([0] * total, index=candidate_frame.index)
    partial_count = int(partial_explicit.fillna(0).gt(0).sum())

    rows.append(
        {
            "layer": "evolutionary_escape",
            "candidate_count": total,
            "mapped_candidate_count": proxy_available_count,
            "usable_candidate_count": supported_count,
            "usable_fraction": supported_count / total if total else 0.0,
            "provider_rows": "phase3_features",
            "interpretation": (
                "contract_supported_explicit_evidence"
                if supported_count
                else "proxy_or_partial_explicit_only_unknown_is_not_low"
                if proxy_available_count or partial_count
                else "no_evolutionary_evidence_reported"
            ),
        }
    )
    return pd.DataFrame(rows)


def _artifact(kind: str, path: Path, repo_root: Path) -> SelectedArtifact:
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        relative = path.resolve().as_posix()
    return SelectedArtifact(
        kind=kind,
        path=relative,
        size_bytes=path.stat().st_size,
        sha256=_sha256(path),
    )


def write_report(
    output_path: Path,
    *,
    run_dir: Path,
    ranking_path: Path,
    feature_path: Path,
    candidate_audit: pd.DataFrame,
    provider_summary: pd.DataFrame,
    layer_coverage: pd.DataFrame,
    expected_candidates: int | None,
    artifacts: Sequence[SelectedArtifact],
) -> None:
    candidate_count = len(candidate_audit)
    exact_expected = expected_candidates is None or candidate_count == expected_candidates
    unknown_risk = int(
        candidate_audit["scientific_interpretation_guard"]
        .ne("contract_supported_interpretation_allowed")
        .sum()
    )
    contract_supported = int(
        candidate_audit["evolutionary_evidence_contract_supported"].sum()
    )
    usable_providers = int(
        provider_summary["usable_evidence"].astype(str).str.lower().eq("true").sum()
    )
    score_providers = int(
        provider_summary["affects_score"].astype(str).str.lower().eq("true").sum()
    )
    lines = [
        "# Auditoría específica de la corrida seleccionada",
        "",
        f"Generado: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Identificación",
        "",
        f"- Corrida: `{run_dir.as_posix()}`",
        f"- Ranking seleccionado: `{ranking_path.as_posix()}`",
        f"- Tabla completa de características: `{feature_path.as_posix()}`",
        f"- Candidatos observados: **{candidate_count}**",
        (
            "- Candidatos esperados: "
            f"**{expected_candidates if expected_candidates is not None else 'not_configured'}**"
        ),
        f"- Coincide con el conteo esperado: **{exact_expected}**",
        "",
        "## Procedencia y cobertura",
        "",
        f"- Filas de proveedor: **{len(provider_summary)}**",
        f"- Proveedores con evidencia utilizable declarada: **{usable_providers}**",
        f"- Proveedores que declaran afectar score: **{score_providers}**",
        f"- Candidatos respaldados por contrato evolutivo: **{contract_supported}**",
        (
            "- Candidatos sin respaldo contractual suficiente para interpretar "
            f"riesgo evolutivo: **{unknown_risk}**"
        ),
        "",
        "## Cobertura por capa",
        "",
        (
            "| Capa | Mapeados/derivados | Utilizables/respaldados | Total | "
            "Fracción utilizable | Interpretación |"
        ),
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in layer_coverage.to_dict(orient="records"):
        lines.append(
            f"| {row['layer']} | {row['mapped_candidate_count']} | "
            f"{row['usable_candidate_count']} | {row['candidate_count']} | "
            f"{row['usable_fraction']:.3f} | {row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "## Controles de interpretación",
            "",
            "- La recuperación o el mapeo no equivalen automáticamente a evidencia utilizable.",
            "- Una bandera `_is_explicit` histórica no equivale a evidencia respaldada por Stage 4A.",
            "- Sólo `evolutionary_evidence_contract_supported=True` habilita la etiqueta de evidencia evolutiva respaldada.",
            "- `unknown`, `missing`, `unresolved`, evidencia parcial y evidencia derivada no deben interpretarse como riesgo bajo.",
            "- Un no-hit de DIAMOND no demuestra seguridad frente al hospedero.",
            "- Esta auditoría usa `phase3_features.csv` para variables y el ranking real para delimitar candidatos.",
            "",
            "## Artefactos congelados por hash",
            "",
            "| Tipo | Ruta | Tamaño | SHA-256 |",
            "|---|---|---:|---|",
        ]
    )
    for artifact in artifacts:
        lines.append(
            f"| {artifact.kind} | `{artifact.path}` | {artifact.size_bytes} | "
            f"`{artifact.sha256}` |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit(
    *,
    repo_root: Path,
    run_dir: Path,
    output_dir: Path,
    config_path: Path | None = None,
    expected_candidates: int | None = None,
) -> dict[str, Any]:
    config = (
        load_stage2_config(config_path)
        if config_path
        else copy.deepcopy(DEFAULT_STAGE2_CONFIG)
    )
    selected = (
        config.get("selected_run", {})
        if isinstance(config.get("selected_run"), Mapping)
        else {}
    )
    ranking_names = tuple(
        selected.get("ranking_table_priority", DEFAULT_RANKING_PRIORITY)
    )
    feature_names = tuple(
        selected.get("feature_table_priority", DEFAULT_FEATURE_PRIORITY)
    )
    provider_names = tuple(
        selected.get("provider_audit_names", DEFAULT_PROVIDER_AUDITS)
    )
    diamond_names = tuple(
        selected.get("diamond_manifest_names", DEFAULT_DIAMOND_MANIFESTS)
    )
    if expected_candidates is None:
        configured = selected.get("expected_candidate_count")
        expected_candidates = int(configured) if configured is not None else None
    if not run_dir.exists():
        raise FileNotFoundError(f"No existe la corrida: {run_dir}")

    ranking_path = find_best_artifact(run_dir, ranking_names)
    feature_path = find_best_artifact(run_dir, feature_names)
    if ranking_path is None:
        raise FileNotFoundError("No se encontró ranking de candidatos reales")
    if feature_path is None:
        feature_path = ranking_path
    provider_path = find_best_artifact(run_dir, provider_names)
    diamond_path = find_best_artifact(run_dir, diamond_names)

    ranking_frame = read_csv(ranking_path)
    feature_frame = read_csv(feature_path)
    candidate_frame = (
        select_candidate_features(feature_frame, ranking_frame)
        if feature_path != ranking_path
        else ranking_frame.copy().reset_index(drop=True)
    )
    provider_frame = read_csv(provider_path) if provider_path else None
    candidate_audit = build_candidate_audit(candidate_frame)
    provider_summary = build_provider_summary(provider_frame)
    layer_coverage = build_layer_coverage(candidate_frame, provider_summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_audit.to_csv(
        output_dir / "selected_run_candidate_audit.csv",
        index=False,
    )
    provider_summary.to_csv(
        output_dir / "selected_run_provider_audit.csv",
        index=False,
    )
    layer_coverage.to_csv(
        output_dir / "selected_run_layer_coverage.csv",
        index=False,
    )

    artifacts = [
        _artifact("ranking_table", ranking_path, repo_root),
        _artifact("phase3_features", feature_path, repo_root),
    ]
    if provider_path:
        artifacts.append(_artifact("provider_audit", provider_path, repo_root))
    if diamond_path:
        artifacts.append(_artifact("diamond_manifest", diamond_path, repo_root))

    contract_supported_count = int(
        candidate_audit["evolutionary_evidence_contract_supported"].sum()
    )
    manifest = {
        "schema_version": 3,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_head": _git(repo_root, "rev-parse", "HEAD"),
        "repo_branch": _git(repo_root, "branch", "--show-current"),
        "run_dir": run_dir.resolve().as_posix(),
        "candidate_count": len(candidate_frame),
        "expected_candidate_count": expected_candidates,
        "candidate_count_matches_expected": (
            expected_candidates is None
            or len(candidate_frame) == expected_candidates
        ),
        "evolutionary_contract_supported_candidate_count": contract_supported_count,
        "evolutionary_contract_fail_closed": True,
        "artifacts": [asdict(item) for item in artifacts],
        "scientific_guards": {
            "missing_is_not_negative": True,
            "diamond_no_hit_is_not_host_safety": True,
            "unknown_escape_is_not_low_escape": True,
            "legacy_explicit_flag_is_not_contract_support": True,
        },
    }
    (output_dir / "selected_run_audit_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_report(
        output_dir / "selected_run_audit_report.md",
        run_dir=run_dir,
        ranking_path=ranking_path,
        feature_path=feature_path,
        candidate_audit=candidate_audit,
        provider_summary=provider_summary,
        layer_coverage=layer_coverage,
        expected_candidates=expected_candidates,
        artifacts=artifacts,
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/integrated_validation_stage2.json"),
    )
    parser.add_argument("--expected-candidates", type=int, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    run_dir = (
        args.run_dir
        if args.run_dir.is_absolute()
        else repo_root / args.run_dir
    )
    output_dir = (
        args.output_dir
        if args.output_dir.is_absolute()
        else repo_root / args.output_dir
    )
    config_path = (
        args.config
        if args.config.is_absolute()
        else repo_root / args.config
    )
    manifest = run_audit(
        repo_root=repo_root,
        run_dir=run_dir,
        output_dir=output_dir,
        config_path=config_path,
        expected_candidates=args.expected_candidates,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
