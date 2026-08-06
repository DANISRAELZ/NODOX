#!/usr/bin/env python3
"""Audit readiness for NODOX integrated biological/computational validation.

The auditor is deliberately read-only with respect to production code and
historical results. It writes only to the requested output directory.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

BASELINE_COMMIT = "b7b86769d5cf9a69d01959cab328332d1f0aff84"

RUN_MARKERS = {
    "online_only_run_manifest.json",
    "ranking_nodos.csv",
    "ranking_nodos_phase3.csv",
    "ranking_nodos_phase3_real_candidates.csv",
    "layer_resolution_manifest.json",
    "online_only_provider_audit.csv",
    "human_homology_diamond_manifest.json",
}

PROVIDERS: tuple[dict[str, Any], ...] = (
    {"provider": "uniprot", "layers": "candidate_seed; localization; annotation"},
    {"provider": "string", "layers": "functional_network"},
    {"provider": "interpro", "layers": "protein_annotation"},
    {"provider": "bvbrc", "layers": "strain_conservation; specialized_genes"},
    {"provider": "vfdb", "layers": "virulence"},
    {"provider": "deg", "layers": "essentiality; contextual_essentiality"},
    {"provider": "diamond", "layers": "human_homology"},
    {"provider": "literature", "layers": "literature_support"},
)

POSTULATES: tuple[dict[str, Any], ...] = (
    {
        "postulate_id": "P1",
        "postulate": "Nodo funcional, no entidad aislada",
        "question": "¿La perturbación afecta dependencias, módulos o procesos conectados?",
        "variables": ("functional_node_score", "network_centrality", "pathway_bottleneck_score", "functional_dependency_score"),
        "expected_modules": ("functional_node_theory.py", "scoring_components.py", "string_api.py"),
    },
    {
        "postulate_id": "P2",
        "postulate": "Prioridad terapéutica multicapa",
        "question": "¿Convergen esencialidad, virulencia, localización, conservación, selectividad y contexto?",
        "variables": ("essentiality_score", "virulence_score", "localization_score", "conservation_score", "host_safety_score", "contextual_essentiality_score"),
        "expected_modules": ("integration.py", "scoring.py", "functional_node_theory.py"),
    },
    {
        "postulate_id": "P3",
        "postulate": "Impacto sistémico sujeto a selectividad y redundancia",
        "question": "¿El impacto sistémico persiste después de considerar compensación y riesgo al hospedero?",
        "variables": ("pleiotropy_score", "network_centrality", "redundancy_penalty", "host_similarity_penalty"),
        "expected_modules": ("functional_node_theory.py", "redundancy_and_compensation.py", "human_homology_diamond.py"),
    },
    {
        "postulate_id": "P4",
        "postulate": "Evidencia ponderada por procedencia y calidad",
        "question": "¿Qué tan confiable es cada inferencia?",
        "variables": ("evidence_quality_score", "evidence_confidence_score", "evidence_coverage_score", "confidence_ceiling"),
        "expected_modules": ("evidence_quality.py", "layer_resolver.py", "online_only_validation.py"),
    },
    {
        "postulate_id": "P5",
        "postulate": "Robustez evolutiva y restricción del escape",
        "question": "¿Puede el patógeno mutar, compensar, reemplazar o adquirir una ruta de escape?",
        "variables": ("evolutionary_escape_risk_score", "evolutionary_constraint_score", "mutation_tolerance_score", "functional_redundancy_escape_score", "compensatory_pathway_score", "fitness_cost_of_escape"),
        "expected_modules": ("evolutionary_escape_risk.py", "functional_node_theory.py"),
    },
    {
        "postulate_id": "P6",
        "postulate": "Ausencia de evidencia no equivale a evidencia negativa",
        "question": "¿La señal fue buscada o simplemente falta información?",
        "variables": ("missing_input", "insufficient_evidence", "not_detected_with_method", "detected", "unresolved"),
        "expected_modules": ("layer_resolver.py", "online_only_validation.py", "reporting.py"),
    },
)

EVOLUTIONARY_VARIABLES: tuple[str, ...] = (
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
    "host_similarity_penalty",
    "alternative_pathway_score",
    "metabolic_bypass_score",
    "regulatory_bypass_score",
    "pathway_alternative_count",
    "variant_burden",
    "low_redundancy_score",
    "functional_backup_score",
)

TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".csv", ".txt", ".toml"}


@dataclass(frozen=True)
class RepositoryState:
    repo_root: str
    branch: str
    head_sha: str
    baseline_commit: str
    baseline_matches: bool
    dirty: bool
    status_porcelain: str
    generated_at_utc: str


def _run_git(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def collect_repository_state(repo_root: Path) -> RepositoryState:
    head_sha = _run_git(repo_root, "rev-parse", "HEAD") or "not_available"
    branch = _run_git(repo_root, "branch", "--show-current") or "not_available"
    status = _run_git(repo_root, "status", "--porcelain")
    return RepositoryState(
        repo_root=str(repo_root.resolve()),
        branch=branch,
        head_sha=head_sha,
        baseline_commit=BASELINE_COMMIT,
        baseline_matches=head_sha == BASELINE_COMMIT,
        dirty=bool(status),
        status_porcelain=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def _iter_files(root: Path, *, suffixes: set[str] | None = None) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", ".venv", ".venv-wsl", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if suffixes is not None and path.suffix.lower() not in suffixes:
            continue
        yield path


def _safe_read_text(path: Path, limit: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _safe_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _flatten_json(value: Any, prefix: str = "") -> dict[str, Any]:
    output: dict[str, Any] = {}
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            output.update(_flatten_json(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            output.update(_flatten_json(child, f"{prefix}[{index}]"))
    else:
        output[prefix] = value
    return output


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _run_root(path: Path, repo_root: Path) -> Path:
    relative = path.resolve().relative_to(repo_root.resolve())
    parts = relative.parts
    if len(parts) >= 2 and parts[0] in {"results", "data_sessions"}:
        return repo_root / parts[0] / parts[1]
    return path.parent


def discover_runs(repo_root: Path) -> list[dict[str, Any]]:
    grouped: dict[str, set[str]] = {}
    for base_name in ("results", "data_sessions"):
        base = repo_root / base_name
        for path in _iter_files(base):
            if path.name not in RUN_MARKERS:
                continue
            root = _run_root(path, repo_root)
            key = _relative(root, repo_root)
            grouped.setdefault(key, set()).add(_relative(path, repo_root))

    rows: list[dict[str, Any]] = []
    for run_id, artifacts in sorted(grouped.items()):
        run_path = repo_root / run_id
        manifest_values: dict[str, Any] = {}
        for artifact in sorted(artifacts):
            artifact_path = repo_root / artifact
            if artifact_path.suffix.lower() == ".json":
                data = _safe_json(artifact_path)
                if data is not None:
                    manifest_values.update(_flatten_json(data))
        rows.append(
            {
                "run_id": run_id,
                "artifact_count": len(artifacts),
                "artifacts": "; ".join(sorted(artifacts)),
                "organism": _first_flat_value(manifest_values, ("organism", "organism_name")),
                "taxon_id": _first_flat_value(manifest_values, ("taxon_id", "requested_taxon_id")),
                "candidate_count": _first_numeric_flat_value(manifest_values, ("candidate_count", "candidate_sequence_count", "final_candidate_count")),
                "source_mode": _first_flat_value(manifest_values, ("online_source_mode", "provider_mode", "mode")),
                "has_ranking": any(Path(item).name.startswith("ranking_nodos") for item in artifacts),
                "has_provider_audit": any(Path(item).name == "online_only_provider_audit.csv" for item in artifacts),
                "has_diamond_manifest": any(Path(item).name == "human_homology_diamond_manifest.json" for item in artifacts),
                "modified_time_utc": datetime.fromtimestamp(run_path.stat().st_mtime, timezone.utc).isoformat() if run_path.exists() else "",
            }
        )
    return rows


def _first_flat_value(flat: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        for flat_key, value in flat.items():
            tail = re.sub(r"\[\d+\]", "", flat_key).split(".")[-1]
            if tail == key and value not in {None, ""}:
                return str(value)
    return "not_reported"


def _first_numeric_flat_value(flat: Mapping[str, Any], keys: Sequence[str]) -> str:
    value = _first_flat_value(flat, keys)
    if value == "not_reported":
        return value
    try:
        return str(int(float(value)))
    except ValueError:
        return value


def classify_source(path: Path, text: str = "") -> str:
    haystack = f"{path.as_posix()}\n{text[:50_000]}".lower()
    if "tests/fixtures" in haystack or "synthetic" in haystack:
        return "synthetic_fixture"
    if "versioned_snapshot" in haystack or "online_seed_snapshots" in haystack or "snapshot_manifest" in haystack:
        return "versioned_snapshot"
    if re.search(r"(?:^|[/_\s])demo(?:_only|_data|_run)?(?:$|[/_\s])|packaged_demo", haystack):
        return "demo"
    if "unresolved" in haystack or "api_failed" in haystack or "provider_not_found" in haystack:
        return "unresolved"
    if "api_real" in haystack or "computed_online" in haystack or "real_external_online" in haystack:
        return "real_external_online"
    if "curated" in haystack:
        return "curated"
    if "cache_hit" in haystack or "cache_reused" in haystack or "/cache" in haystack:
        return "cache"
    if "proxy" in haystack or "derived" in haystack or "inferred" in haystack:
        return "proxy"
    return "unknown"


def inventory_evidence_sources(repo_root: Path) -> list[dict[str, Any]]:
    roots = [repo_root / "data_external", repo_root / "results", repo_root / "data_sessions", repo_root / "tests" / "fixtures"]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        for path in _iter_files(root, suffixes=TEXT_SUFFIXES):
            relative = _relative(path, repo_root)
            if relative in seen:
                continue
            seen.add(relative)
            text = _safe_read_text(path, limit=1_000_000)
            source_class = classify_source(path, text)
            if source_class == "unknown" and "manifest" not in path.name.lower() and path.suffix.lower() not in {".csv", ".json"}:
                continue
            rows.append(
                {
                    "path": relative,
                    "source_class": source_class,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                    "notes": _source_note(source_class),
                }
            )
    return sorted(rows, key=lambda item: item["path"])


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return "unavailable"
    return digest.hexdigest()


def _source_note(source_class: str) -> str:
    return {
        "real_external_online": "Recuperación externa declarada; verificar mapeo, utilidad y efecto sobre score.",
        "versioned_snapshot": "Entrada reproducible congelada; no debe describirse como nueva consulta live.",
        "curated": "Evidencia curada; requiere alcance, versión y referencias.",
        "cache": "Reutilización reproducible; conservar fecha y origen de adquisición.",
        "proxy": "Inferencia o derivación; no equivale a evidencia observada.",
        "synthetic_fixture": "Sólo pruebas automatizadas; sin interpretación biológica.",
        "demo": "Demostración técnica; sin valor como evidencia real.",
        "unresolved": "No permite inferencia positiva ni negativa.",
        "unknown": "Clasificación automática insuficiente; requiere revisión.",
    }[source_class]


def _manifest_candidates(repo_root: Path) -> Iterable[Path]:
    for base_name in ("results", "data_sessions", "data_external"):
        for path in _iter_files(repo_root / base_name, suffixes={".json", ".csv"}):
            lower = path.name.lower()
            if any(token in lower for token in ("manifest", "provider_audit", "provenance", "resolution_summary")):
                yield path


def build_provider_coverage(repo_root: Path) -> list[dict[str, Any]]:
    observations: dict[str, list[tuple[Path, dict[str, Any], str]]] = {item["provider"]: [] for item in PROVIDERS}
    for path in _manifest_candidates(repo_root):
        text = _safe_read_text(path, limit=3_000_000)
        lower = text.lower()
        flat: dict[str, Any] = {}
        if path.suffix.lower() == ".json":
            data = _safe_json(path)
            if data is not None:
                flat = _flatten_json(data)
        for item in PROVIDERS:
            provider = item["provider"]
            aliases = {provider}
            if provider == "diamond":
                aliases.add("human_homology_diamond")
            if provider == "bvbrc":
                aliases.update({"bv-brc", "bv_brc"})
            if any(alias in lower or alias in path.as_posix().lower() for alias in aliases):
                observations[provider].append((path, flat, text))

    rows: list[dict[str, Any]] = []
    for item in PROVIDERS:
        provider = item["provider"]
        provider_obs = observations[provider]
        flat_joined: dict[str, Any] = {}
        text_joined = "\n".join(text[:200_000] for _, _, text in provider_obs)
        for _, flat, _ in provider_obs:
            flat_joined.update(flat)
        rows.append(
            {
                "provider": provider,
                "layers": item["layers"],
                "observation_count": len(provider_obs),
                "provider_attempted": _bool_summary(flat_joined, text_joined, ("provider_attempted", "api_attempted", "attempted")),
                "provider_success": _bool_summary(flat_joined, text_joined, ("provider_success", "api_success", "retrieval_success", "success")),
                "mapping_success": _bool_summary(flat_joined, text_joined, ("mapping_success",)),
                "usable_evidence": _bool_summary(flat_joined, text_joined, ("usable_evidence",)),
                "affects_score": _bool_summary(flat_joined, text_joined, ("affects_score",)),
                "retrieved_record_count": _max_numeric(flat_joined, ("retrieved_record_count", "retrieved_count", "record_count", "raw_edge_count")),
                "matched_candidate_count": _max_numeric(flat_joined, ("matched_candidate_count", "mapped_candidate_count", "candidate_count")),
                "usable_count": _max_numeric(flat_joined, ("usable_edge_count", "usable_mapping_count", "usable_record_count")),
                "source_classes": "; ".join(sorted({classify_source(path, text) for path, _, text in provider_obs})) or "not_observed",
                "evidence_files": "; ".join(sorted({_relative(path, repo_root) for path, _, _ in provider_obs})) or "none",
            }
        )
    return rows


def _bool_summary(flat: Mapping[str, Any], text: str, keys: Sequence[str]) -> str:
    values: list[bool] = []
    for flat_key, value in flat.items():
        tail = re.sub(r"\[\d+\]", "", flat_key).split(".")[-1]
        if tail not in keys:
            continue
        parsed = _as_bool(value)
        if parsed is not None:
            values.append(parsed)
    if values:
        if any(values) and not all(values):
            return "mixed"
        return "true" if all(values) else "false"
    for key in keys:
        match = re.search(rf"[\"']?{re.escape(key)}[\"']?\s*[:=]\s*(true|false)", text, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return "not_reported"


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return None


def _max_numeric(flat: Mapping[str, Any], keys: Sequence[str]) -> str:
    values: list[float] = []
    for flat_key, value in flat.items():
        tail = re.sub(r"\[\d+\]", "", flat_key).split(".")[-1]
        if tail not in keys:
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    if not values:
        return "not_reported"
    maximum = max(values)
    return str(int(maximum)) if maximum.is_integer() else f"{maximum:.6g}"


def _source_corpus(repo_root: Path) -> dict[str, str]:
    corpus: dict[str, str] = {}
    for base in (repo_root / "src" / "nodos_funcionales", repo_root / "scripts", repo_root / "docs", repo_root / "config"):
        for path in _iter_files(base, suffixes=TEXT_SUFFIXES):
            corpus[_relative(path, repo_root)] = _safe_read_text(path)
    return corpus


def build_postulate_coverage(repo_root: Path) -> list[dict[str, Any]]:
    corpus = _source_corpus(repo_root)
    rows: list[dict[str, Any]] = []
    for postulate in POSTULATES:
        found_variables: list[str] = []
        paths: set[str] = set()
        for variable in postulate["variables"]:
            for path, text in corpus.items():
                if variable in text:
                    found_variables.append(variable)
                    paths.add(path)
                    break
        modules_found = [module for module in postulate["expected_modules"] if any(Path(path).name == module for path in corpus)]
        variable_ratio = len(set(found_variables)) / max(len(postulate["variables"]), 1)
        if variable_ratio >= 0.75 and modules_found:
            status = "implemented_requires_evidence_audit"
        elif found_variables or modules_found:
            status = "partially_operationalized"
        else:
            status = "not_detected"
        rows.append(
            {
                "postulate_id": postulate["postulate_id"],
                "postulate": postulate["postulate"],
                "question": postulate["question"],
                "expected_variables": "; ".join(postulate["variables"]),
                "detected_variables": "; ".join(sorted(set(found_variables))) or "none",
                "detected_variable_count": len(set(found_variables)),
                "expected_variable_count": len(postulate["variables"]),
                "modules_found": "; ".join(modules_found) or "none",
                "evidence_paths": "; ".join(sorted(paths)) or "none",
                "status": status,
                "interpretation": _postulate_interpretation(status),
            }
        )
    return rows


def _postulate_interpretation(status: str) -> str:
    if status == "implemented_requires_evidence_audit":
        return "La estructura computacional está presente; la suficiencia biológica depende de las fuentes y salidas de cada corrida."
    if status == "partially_operationalized":
        return "Existen módulos o variables parciales; faltan contratos, evidencia o exposición consistente en outputs."
    return "No se detectó operacionalización suficiente mediante la inspección estática."


def build_evolutionary_variable_inventory(repo_root: Path, runs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    corpus = _source_corpus(repo_root)
    run_artifacts = "\n".join(str(run.get("artifacts", "")) for run in runs)
    rows: list[dict[str, Any]] = []
    for variable in EVOLUTIONARY_VARIABLES:
        code_paths = sorted(path for path, text in corpus.items() if variable in text)
        output_paths: list[str] = []
        for base_name in ("results", "data_sessions"):
            for path in _iter_files(repo_root / base_name, suffixes={".csv", ".json"}):
                if variable in _safe_read_text(path, limit=1_000_000):
                    output_paths.append(_relative(path, repo_root))
                    if len(output_paths) >= 20:
                        break
        if code_paths and output_paths:
            status = "implemented_and_observed_in_outputs"
        elif code_paths:
            status = "implemented_not_observed_in_scanned_outputs"
        elif variable in run_artifacts:
            status = "output_reference_without_code_detection"
        else:
            status = "not_detected"
        derivation = "explicit_or_derived_requires_row_audit"
        if variable in {"variant_burden", "alternative_pathway_score", "metabolic_bypass_score", "regulatory_bypass_score", "low_redundancy_score", "functional_backup_score"}:
            derivation = "supporting_or_proxy_variable"
        rows.append(
            {
                "variable": variable,
                "status": status,
                "code_paths": "; ".join(code_paths) or "none",
                "output_paths": "; ".join(sorted(set(output_paths))) or "none",
                "evidence_interpretation": derivation,
                "scientific_guard": "Ausencia o derivación no equivale a medición experimental del escape.",
            }
        )
    return rows


def build_claims(
    repo_root: Path,
    state: RepositoryState,
    runs: Sequence[Mapping[str, Any]],
    provider_rows: Sequence[Mapping[str, Any]],
    postulate_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    supported: list[dict[str, str]] = []
    unsupported: list[dict[str, str]] = [
        {
            "claim": "NODOX valida experimentalmente blancos terapéuticos.",
            "status": "unsupported",
            "basis": "Las corridas computacionales generan hipótesis; no sustituyen validación genética, bioquímica, farmacológica o clínica.",
            "source": "scientific_scope_guard",
        },
        {
            "claim": "Un no-hit de DIAMOND demuestra seguridad frente al hospedero.",
            "status": "unsupported",
            "basis": "El resultado depende del método, referencia y umbrales; sólo informa similitud no detectada bajo esas condiciones.",
            "source": "scientific_scope_guard",
        },
        {
            "claim": "NODOX es superior a métodos alternativos.",
            "status": "unsupported",
            "basis": "Se requiere benchmark preespecificado, conjunto independiente y métricas comparables.",
            "source": "scientific_scope_guard",
        },
        {
            "claim": "El riesgo de escape bajo está demostrado cuando faltan variables.",
            "status": "unsupported",
            "basis": "Riesgo desconocido y riesgo bajo son estados diferentes.",
            "source": "scientific_scope_guard",
        },
    ]

    theory_path = repo_root / "src" / "nodos_funcionales" / "functional_node_theory.py"
    escape_path = repo_root / "src" / "nodos_funcionales" / "evolutionary_escape_risk.py"
    if theory_path.exists():
        supported.append(
            {
                "claim": "NODOX contiene una implementación computacional auditable de la Teoría de Nodos Funcionales.",
                "status": "supported_software_claim",
                "basis": "Se detectó el módulo de scoring, componentes, confianza, etiquetas y auditoría.",
                "source": _relative(theory_path, repo_root),
            }
        )
    if escape_path.exists():
        supported.append(
            {
                "claim": "NODOX modela explícitamente el riesgo de escape evolutivo como dimensión separada.",
                "status": "supported_software_claim",
                "basis": "Se detectó el módulo y sus variables de riesgo, restricción y procedencia.",
                "source": _relative(escape_path, repo_root),
            }
        )
    if any(run.get("has_ranking") for run in runs):
        supported.append(
            {
                "claim": "Existen corridas con rankings trazables disponibles para auditoría.",
                "status": "supported_repository_claim",
                "basis": f"Se inventariaron {sum(bool(run.get('has_ranking')) for run in runs)} corridas con archivos de ranking.",
                "source": "available_runs_inventory.csv",
            }
        )
    if any("versioned_snapshot" in str(row.get("source_classes")) for row in provider_rows):
        supported.append(
            {
                "claim": "Existe al menos una fuente congelada y versionada para reproducibilidad.",
                "status": "supported_repository_claim",
                "basis": "La auditoría detectó evidencia clasificada como versioned_snapshot.",
                "source": "provider_coverage_matrix.csv",
            }
        )
    if any(row.get("postulate_id") == "P6" and row.get("status") != "not_detected" for row in postulate_rows):
        supported.append(
            {
                "claim": "El software contiene controles para separar faltantes de evidencia negativa.",
                "status": "supported_software_claim",
                "basis": "Se detectaron estados explícitos de incertidumbre asociados al Postulado 6.",
                "source": "functional_node_postulates_matrix.csv",
            }
        )
    supported.append(
        {
            "claim": "La auditoría corresponde al commit registrado en repository_state.json.",
            "status": "supported_reproducibility_claim",
            "basis": f"HEAD={state.head_sha}; baseline_match={state.baseline_matches}.",
            "source": "repository_state.json",
        }
    )
    return supported, unsupported


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    state: RepositoryState,
    runs: Sequence[Mapping[str, Any]],
    providers: Sequence[Mapping[str, Any]],
    postulates: Sequence[Mapping[str, Any]],
    evolutionary: Sequence[Mapping[str, Any]],
    supported: Sequence[Mapping[str, Any]],
    unsupported: Sequence[Mapping[str, Any]],
) -> None:
    lines = [
        "# Informe de preparación de la validación integrada",
        "",
        f"Generado: `{state.generated_at_utc}`",
        "",
        "## Estado del repositorio",
        "",
        f"- Rama: `{state.branch}`",
        f"- HEAD: `{state.head_sha}`",
        f"- Baseline Stage 1: `{state.baseline_commit}`",
        f"- Coincide con baseline: `{state.baseline_matches}`",
        f"- Árbol con cambios: `{state.dirty}`",
        "",
        "## Resumen",
        "",
        f"- Corridas inventariadas: **{len(runs)}**.",
        f"- Proveedores evaluados: **{len(providers)}**.",
        f"- Postulados con implementación o cobertura parcial: **{sum(row['status'] != 'not_detected' for row in postulates)}/{len(postulates)}**.",
        f"- Variables evolutivas detectadas en código: **{sum(row['status'] != 'not_detected' for row in evolutionary)}/{len(evolutionary)}**.",
        "",
        "## Corridas candidatas",
        "",
        "| Corrida | Organismo | Candidatos | Ranking | Auditoría de proveedor | DIAMOND |",
        "|---|---|---:|---|---|---|",
    ]
    for run in runs:
        lines.append(
            f"| `{run['run_id']}` | {run['organism']} | {run['candidate_count']} | {run['has_ranking']} | {run['has_provider_audit']} | {run['has_diamond_manifest']} |"
        )
    if not runs:
        lines.append("| No se detectaron corridas con los marcadores configurados | — | — | — | — | — |")

    lines.extend([
        "",
        "## Cobertura de proveedores",
        "",
        "| Proveedor | Observaciones | Intentado | Éxito | Mapeo | Utilizable | Afecta score |",
        "|---|---:|---|---|---|---|---|",
    ])
    for row in providers:
        lines.append(
            f"| {row['provider']} | {row['observation_count']} | {row['provider_attempted']} | {row['provider_success']} | {row['mapping_success']} | {row['usable_evidence']} | {row['affects_score']} |"
        )

    lines.extend([
        "",
        "## Estado de los postulados",
        "",
        "| ID | Postulado | Estado | Variables detectadas |",
        "|---|---|---|---:|",
    ])
    for row in postulates:
        lines.append(f"| {row['postulate_id']} | {row['postulate']} | {row['status']} | {row['detected_variable_count']}/{row['expected_variable_count']} |")

    lines.extend([
        "",
        "## Afirmaciones defendibles",
        "",
    ])
    for claim in supported:
        lines.append(f"- **{claim['claim']}** — {claim['basis']} Fuente: `{claim['source']}`.")
    lines.extend([
        "",
        "## Afirmaciones no respaldadas",
        "",
    ])
    for claim in unsupported:
        lines.append(f"- **{claim['claim']}** — {claim['basis']}")

    lines.extend([
        "",
        "## Próximo PR recomendado",
        "",
        "1. Revisar manualmente las clasificaciones `unknown` y los proveedores con estados `mixed`.",
        "2. Congelar el protocolo de benchmark y la lista de controles antes de modificar pesos.",
        "3. Añadir una salida de ablación con y sin componente evolutivo sin cambiar defaults.",
        "4. Integrar evidencia DEG/VFDB únicamente con manifiesto, licencia y mapeo auditables.",
        "5. Mantener H. pylori como caso principal y reservar al menos un organismo para validación externa.",
        "",
        "## Limitación de la auditoría",
        "",
        "La inspección estática y de artefactos no demuestra validez biológica, eficacia terapéutica ni desempeño predictivo. Los estados deben verificarse en la corrida seleccionada antes de incorporarlos al manuscrito.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def run_audit(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_dir = output_dir if output_dir.is_absolute() else repo_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    state = collect_repository_state(repo_root)
    runs = discover_runs(repo_root)
    providers = build_provider_coverage(repo_root)
    evidence = inventory_evidence_sources(repo_root)
    postulates = build_postulate_coverage(repo_root)
    evolutionary = build_evolutionary_variable_inventory(repo_root, runs)
    supported, unsupported = build_claims(repo_root, state, runs, providers, postulates)

    (output_dir / "repository_state.json").write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(output_dir / "available_runs_inventory.csv", runs)
    write_csv(output_dir / "provider_coverage_matrix.csv", providers)
    write_csv(output_dir / "evidence_source_inventory.csv", evidence)
    write_csv(output_dir / "functional_node_postulates_matrix.csv", postulates)
    write_csv(output_dir / "evolutionary_escape_variables.csv", evolutionary)
    write_csv(output_dir / "manuscript_supported_claims.csv", supported)
    write_csv(output_dir / "manuscript_unsupported_claims.csv", unsupported)
    write_report(
        output_dir / "integrated_validation_readiness_report.md",
        state,
        runs,
        providers,
        postulates,
        evolutionary,
        supported,
        unsupported,
    )
    return {
        "output_dir": str(output_dir),
        "repository_state": asdict(state),
        "run_count": len(runs),
        "provider_count": len(providers),
        "postulate_count": len(postulates),
        "evolutionary_variable_count": len(evolutionary),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("results/integrated_validation_stage1"))
    parser.add_argument("--fail-on-dirty", action="store_true", help="Exit with status 2 when the source tree is dirty before output generation.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    initial_state = collect_repository_state(args.repo_root.resolve())
    if args.fail_on_dirty and initial_state.dirty:
        print("ERROR: el árbol de trabajo contiene cambios antes de la auditoría.")
        print(initial_state.status_porcelain)
        return 2
    summary = run_audit(args.repo_root, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
