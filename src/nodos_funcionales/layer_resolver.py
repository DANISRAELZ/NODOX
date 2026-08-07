from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .acquisition import map_source_dataframe
from .amrfinderplus_provider import (
    _cache_key as amrfinder_cache_key,
    _candidate_proteins as amrfinder_candidate_proteins,
    _read_cache as read_amrfinder_cache,
    fetch_amrfinderplus_point_mutation_evidence,
)
from .layer_registry import LayerDefinition, get_layer_definition, list_layer_definitions
from .online_sources import effective_online_source_mode, fetch_layer_external_source


@dataclass
class LayerResolution:
    layer_key: str
    filename: str
    strategy: str
    resolved_from: str
    source_type: str
    source_name: str
    is_user_supplied: bool
    is_external: bool
    is_cached: bool
    is_proxy: bool
    confidence: float
    retrieval_status: str
    output_path: str | None
    selected_inputs: list[str]
    generated_by: str = "not_reported"


def _candidate_dirs(base_dir: Path, config: dict[str, Any]) -> dict[str, Path]:
    resolution_cfg = config["layer_resolution"]
    return {
        "user": base_dir / resolution_cfg["user_data_dir"],
        "cache": base_dir / resolution_cfg["cache_data_dir"],
        "external": base_dir / resolution_cfg["external_data_dir"],
        "raw": base_dir / "data_raw",
    }


def _read_layer_source(path: Path, layer_key: str, config: dict[str, Any], source_kind: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if source_kind == "user":
        mapped, _ = map_source_dataframe(df, layer_key, config)
        return mapped
    return df.copy()


def _merge_with_priority(
    paths: list[tuple[str, Path]],
    layer_key: str,
    config: dict[str, Any],
) -> pd.DataFrame:
    merged: pd.DataFrame | None = None
    for source_kind, path in paths:
        current = _read_layer_source(path, layer_key, config, source_kind)
        if merged is None:
            merged = current.copy()
            continue
        combined = pd.concat([merged, current], ignore_index=True, sort=False)
        if "protein_id" in combined.columns:
            combined["protein_id"] = combined["protein_id"].astype("string").str.strip()
            combined = combined.drop_duplicates(subset=["protein_id"], keep="first")
        merged = combined
    return merged if merged is not None else pd.DataFrame()


def _priority_order(strategy: str) -> list[str]:
    if strategy == "external_preferred":
        return ["external", "cache", "user", "raw"]
    if strategy == "merge_with_priority":
        return ["user", "external", "cache", "raw"]
    return ["user", "cache", "external", "raw"]


def _source_name(path: Path | None, fallback: str) -> str:
    if path is None:
        return fallback
    return path.name


def _organism_context(base_dir: Path) -> tuple[str | None, str | None]:
    profile_path = base_dir / "results" / "organism_profile.json"
    if not profile_path.exists():
        return None, None
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None
    organism_name = str(
        profile.get("organism_canonical_name")
        or profile.get("organism_input_name")
        or ""
    ).strip() or None
    taxon_id = str(profile.get("taxon_id") or "").strip() or None
    return organism_name, taxon_id


def _looks_like_amrfinder_provider_table(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        columns = set(pd.read_csv(path, nrows=1).columns)
    except Exception:  # noqa: BLE001 - only used to classify stale provider output.
        return False
    return {
        "amrfinder_source_record",
        "amrfinder_source_version",
        "amrfinder_taxon_id",
        "amrfinder_provider_source_used",
    }.issubset(columns)


def _amrfinder_exact_query_cached(
    base_dir: Path,
    config: dict[str, Any],
    organism_name: str | None,
    taxon_id: str | None,
) -> bool:
    if not organism_name or not taxon_id:
        return False
    candidates = amrfinder_candidate_proteins(base_dir)
    key = amrfinder_cache_key(taxon_id, organism_name, candidates)
    cache = read_amrfinder_cache(base_dir, config)
    entry = cache.get("entries", {}).get(key)
    return bool(
        isinstance(entry, dict)
        and entry.get("manifest", {}).get("query_complete", False)
    )


def _remove_stale_amrfinder_provider_outputs(*paths: Path) -> None:
    for path in paths:
        if _looks_like_amrfinder_provider_table(path):
            try:
                path.unlink()
            except OSError:
                pass


def _resolve_amrfinderplus_layer(
    base_dir: Path,
    config: dict[str, Any],
    definition: LayerDefinition,
    *,
    strategy: str,
    dirs: dict[str, Path],
    online_source_mode: str,
) -> LayerResolution | None:
    """Resolve AMRFinderPlus through its query-specific cache, not generic CSV state.

    A non-provider user/raw table is deliberately left to the normal resolver. Once
    NODOX itself generated the AMRFinderPlus table, however, subsequent runs must
    re-resolve it against the current organism and candidate gene set. Otherwise a
    generic `evolutionary_escape_risk.csv` from a previous organism could suppress
    a valid query in a later multi-organism run.
    """

    user_path = dirs["user"] / definition.filename
    raw_path = dirs["raw"] / definition.filename
    external_path = dirs["external"] / definition.filename
    generic_cache_path = dirs["cache"] / definition.filename

    if user_path.exists():
        return None
    if raw_path.exists() and not _looks_like_amrfinder_provider_table(raw_path):
        return None

    organism_name, taxon_id = _organism_context(base_dir)
    exact_cache_available = _amrfinder_exact_query_cached(
        base_dir,
        config,
        organism_name,
        taxon_id,
    )

    if online_source_mode == "offline_only" and not exact_cache_available:
        _remove_stale_amrfinder_provider_outputs(
            raw_path,
            external_path,
            generic_cache_path,
        )
        return LayerResolution(
            layer_key=definition.table_key,
            filename=definition.filename,
            strategy=strategy,
            resolved_from="missing",
            source_type="missing",
            source_name="ncbi_amrfinderplus_point_mutations",
            is_user_supplied=False,
            is_external=False,
            is_cached=False,
            is_proxy=False,
            confidence=0.0,
            retrieval_status="offline_only_without_matching_query_cache",
            output_path=None,
            selected_inputs=[],
            generated_by="not_generated",
        )

    provider_result = fetch_amrfinderplus_point_mutation_evidence(
        workspace=base_dir,
        organism_name=organism_name,
        taxon_id=taxon_id,
        config=config,
        mode=online_source_mode,
    )
    provider_data = provider_result["evolutionary_escape_risk_data"]
    provider_manifest = provider_result["manifest"]

    if provider_data.empty:
        _remove_stale_amrfinder_provider_outputs(
            raw_path,
            external_path,
            generic_cache_path,
        )
        return LayerResolution(
            layer_key=definition.table_key,
            filename=definition.filename,
            strategy=strategy,
            resolved_from="missing",
            source_type="missing",
            source_name="ncbi_amrfinderplus_point_mutations",
            is_user_supplied=False,
            is_external=False,
            is_cached=False,
            is_proxy=False,
            confidence=0.0,
            retrieval_status=str(
                provider_manifest.get("retrieval_status", "unresolved")
            ),
            output_path=None,
            selected_inputs=[],
            generated_by="amrfinderplus_provider",
        )

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    external_path.parent.mkdir(parents=True, exist_ok=True)
    provider_data.to_csv(raw_path, index=False)
    provider_data.to_csv(external_path, index=False)
    _remove_stale_amrfinder_provider_outputs(generic_cache_path)

    source_used = str(provider_manifest.get("source_used", "api_real"))
    delivered_from_cache = source_used == "cache"
    confidence_cfg = config.get("online_sources", {}).get("amrfinderplus", {})
    confidence = float(confidence_cfg.get("confidence_real", 0.95))
    return LayerResolution(
        layer_key=definition.table_key,
        filename=definition.filename,
        strategy=strategy,
        resolved_from="cache" if delivered_from_cache else "external",
        source_type="cache" if delivered_from_cache else "external",
        source_name="ncbi_amrfinderplus_point_mutations",
        is_user_supplied=False,
        is_external=not delivered_from_cache,
        is_cached=delivered_from_cache,
        is_proxy=False,
        confidence=confidence,
        retrieval_status=str(
            provider_manifest.get(
                "retrieval_status",
                "cache_reused" if delivered_from_cache else "api_real",
            )
        ),
        output_path=str(raw_path),
        selected_inputs=[
            (
                "provider_cache:amrfinderplus_point_mutation_cache.json"
                if delivered_from_cache
                else "external:NCBI_AMRFinderPlus_ReferenceGeneCatalog.txt"
            )
        ],
        generated_by="amrfinderplus_provider",
    )


def _demo_raw_files(base_dir: Path) -> set[str]:
    return set(_demo_raw_metadata(base_dir).keys())


def _demo_raw_metadata(base_dir: Path) -> dict[str, dict[str, str]]:
    manifest_path = base_dir / "results" / "acquisition_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    filenames = {
        str(filename): {"generated_by": "packaged_demo", "source_type": "demo"}
        for filename in (manifest.get("demo_files_copied", []) or [])
    }
    for dataset in manifest.get("datasets", []) or []:
        filename = dataset.get("filename")
        if not filename:
            continue
        generated_by = str(dataset.get("generated_by", "") or "")
        source_type = str(dataset.get("source_type", "") or "")
        if source_type == "demo" or generated_by == "packaged_demo":
            filenames[str(filename)] = {
                "generated_by": generated_by or "not_reported",
                "source_type": source_type or "demo",
            }
    return filenames


def _raw_source_type(source_kind: str, raw_demo_meta: dict[str, str]) -> str:
    if source_kind != "raw" or not raw_demo_meta:
        return source_kind
    if raw_demo_meta.get("generated_by") == "packaged_demo":
        return "packaged_demo"
    return "demo_raw"


def _resolve_single_layer(
    base_dir: Path,
    config: dict[str, Any],
    definition: LayerDefinition,
) -> LayerResolution:
    dirs = _candidate_dirs(base_dir, config)
    resolution_cfg = config["layer_resolution"]
    layer_cfg = resolution_cfg["layers"].get(definition.table_key, {})
    strategy = str(layer_cfg.get("strategy", resolution_cfg["default_strategy"]))
    selected_inputs: list[str] = []

    raw_path = dirs["raw"] / definition.filename
    user_path = dirs["user"] / definition.filename
    cache_path = dirs["cache"] / definition.filename
    external_path = dirs["external"] / definition.filename
    external_provider = str(layer_cfg.get("external_provider", definition.external_provider or "workspace_stub"))
    raw_demo_meta = _demo_raw_metadata(base_dir).get(definition.filename, {})
    raw_is_demo = bool(raw_demo_meta)
    online_source_mode = effective_online_source_mode(config)

    if (
        external_provider == "amrfinderplus_point_mutations"
        and definition.table_key == "evolutionary_escape_risk"
    ):
        specialized = _resolve_amrfinderplus_layer(
            base_dir,
            config,
            definition,
            strategy=strategy,
            dirs=dirs,
            online_source_mode=online_source_mode,
        )
        if specialized is not None:
            return specialized

    external_result: dict[str, Any] = {
        "source_name": external_provider,
        "status": "external_not_requested",
        "confidence": None,
        "path": None,
    }

    available_paths = {
        "user": user_path if user_path.exists() else None,
        "cache": cache_path if cache_path.exists() else None,
        "external": external_path if external_path.exists() else None,
        "raw": raw_path if raw_path.exists() else None,
    }

    should_fetch_external = available_paths["external"] is None and (
        strategy in {"external_preferred", "merge_with_priority"}
        or (
            strategy == "user_preferred"
            and available_paths["user"] is None
            and available_paths["cache"] is None
            and available_paths["raw"] is None
        )
    )
    if online_source_mode in {"offline_only", "cache_first"} and available_paths["cache"] is not None:
        should_fetch_external = False
    if should_fetch_external:
        external_result = fetch_layer_external_source(
            layer_key=definition.table_key,
            workspace=base_dir,
            filename=definition.filename,
            config=config,
            provider_name=external_provider,
        )
        external_path = Path(external_result["path"]) if external_result.get("path") else None
        available_paths["external"] = external_path if external_path and external_path.exists() else None

    if strategy == "user_preferred" and raw_is_demo and available_paths["external"] is not None and available_paths["user"] is None and available_paths["cache"] is None:
        merge_inputs = [("external", available_paths["external"]), ("raw", raw_path)]
        selected_inputs = [f"{source_kind}:{path.name}" for source_kind, path in merge_inputs if path is not None]
        merged = _merge_with_priority([(kind, path) for kind, path in merge_inputs if path is not None], definition.table_key, config)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(raw_path, index=False)
        if resolution_cfg["write_cache_from_external"]:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(available_paths["external"], cache_path)
        return LayerResolution(
            layer_key=definition.table_key,
            filename=definition.filename,
            strategy=strategy,
            resolved_from="merge",
            source_type="merged",
            source_name="external+demo_raw",
            is_user_supplied=False,
            is_external=True,
            is_cached=True,
            is_proxy=False,
            confidence=float(layer_cfg.get("merged_confidence", 0.85)),
            retrieval_status="resolved_from_external_with_demo_gap_fill",
            output_path=str(raw_path),
            selected_inputs=selected_inputs,
            generated_by="mixed_external_and_demo",
        )

    if strategy == "merge_with_priority":
        merge_inputs = [(source_kind, path) for source_kind in _priority_order(strategy) if (path := available_paths[source_kind]) is not None]
        if merge_inputs:
            selected_inputs = [
                f"{_raw_source_type(source_kind, raw_demo_meta)}:{path.name}"
                for source_kind, path in merge_inputs
            ]
            merged = _merge_with_priority(merge_inputs, definition.table_key, config)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            merged.to_csv(raw_path, index=False)
            primary_kind, primary_path = merge_inputs[0]
            if primary_kind == "external" and resolution_cfg["write_cache_from_external"]:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(primary_path, cache_path)
            return LayerResolution(
                layer_key=definition.table_key,
                filename=definition.filename,
                strategy=strategy,
                resolved_from="merge",
                source_type="merged",
                source_name="+".join(_raw_source_type(kind, raw_demo_meta) for kind, _ in merge_inputs),
                is_user_supplied=any(kind == "user" for kind, _ in merge_inputs),
                is_external=any(kind == "external" for kind, _ in merge_inputs),
                is_cached=any(kind in {"cache", "raw"} for kind, _ in merge_inputs),
                is_proxy=False,
                confidence=float(layer_cfg.get("merged_confidence", 0.85)),
                retrieval_status="resolved_from_merge",
                output_path=str(raw_path),
                selected_inputs=selected_inputs,
                generated_by="merged_inputs",
            )

    for source_kind in _priority_order(strategy):
        source_path = available_paths[source_kind]
        if source_path is None:
            continue
        selected_inputs = [f"{_raw_source_type(source_kind, raw_demo_meta)}:{source_path.name}"]
        if source_kind == "user":
            mapped = _read_layer_source(source_path, definition.table_key, config, "user")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            mapped.to_csv(raw_path, index=False)
        elif source_kind != "raw":
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, raw_path)
        if source_kind == "external" and resolution_cfg["write_cache_from_external"]:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, cache_path)
        return LayerResolution(
            layer_key=definition.table_key,
            filename=definition.filename,
            strategy=strategy,
            resolved_from=source_kind,
            source_type=_raw_source_type(source_kind, raw_demo_meta),
            source_name=(
                str(external_result.get("source_name", source_kind))
                if source_kind == "external"
                else ("packaged_demo:" + source_path.name if source_kind == "raw" and raw_demo_meta.get("generated_by") == "packaged_demo" else _source_name(source_path, source_kind))
            ),
            is_user_supplied=source_kind == "user",
            is_external=source_kind == "external",
            is_cached=source_kind in {"cache", "raw"},
            is_proxy=False,
            confidence=float(
                external_result.get("confidence")
                if source_kind == "external" and external_result.get("confidence") is not None
                else layer_cfg.get(f"{source_kind}_confidence", resolution_cfg["default_confidence_by_source"].get(source_kind, 0.5))
            ),
            retrieval_status=(
                str(external_result.get("status", "resolved_from_external"))
                if source_kind == "external"
                else f"resolved_from_{source_kind}"
            ),
            output_path=str(raw_path),
            selected_inputs=selected_inputs,
            generated_by=(
                "user_provided"
                if source_kind == "user"
                else raw_demo_meta.get("generated_by", source_kind)
            ),
        )

    strict_context_unresolved = (
        online_source_mode == "online_strict"
        and definition.table_key in {"clinical_impact", "curated_disease_context", "therapy_site_context"}
        and external_provider in {"controlled_therapeutic_context_v1", "controlled_therapeutic_context_v2"}
    )
    if definition.allow_proxy_default and not strict_context_unresolved:
        return LayerResolution(
            layer_key=definition.table_key,
            filename=definition.filename,
            strategy=strategy,
            resolved_from="proxy",
            source_type="proxy",
            source_name=str(layer_cfg.get("proxy_name", "explicit_proxy_default")),
            is_user_supplied=False,
            is_external=False,
            is_cached=False,
            is_proxy=True,
            confidence=float(layer_cfg.get("proxy_confidence", resolution_cfg["proxy_confidence_default"])),
            retrieval_status="proxy_default",
            output_path=None,
            selected_inputs=[],
            generated_by="proxy_default",
        )

    if definition.required:
        raise FileNotFoundError(f"No se pudo resolver la capa requerida {definition.table_key}")

    return LayerResolution(
        layer_key=definition.table_key,
        filename=definition.filename,
        strategy=strategy,
        resolved_from="missing",
        source_type="missing",
        source_name="missing",
        is_user_supplied=False,
        is_external=False,
        is_cached=False,
        is_proxy=False,
        confidence=0.0,
        retrieval_status="missing_optional_layer",
        output_path=None,
        selected_inputs=[],
        generated_by="not_generated",
    )


def resolve_layer_inputs(base_dir: Path, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    for definition in list_layer_definitions():
        resolution = _resolve_single_layer(base_dir, config, definition)
        manifest[definition.table_key] = asdict(resolution)

    manifest_path = results_dir / config["layer_resolution"]["manifest_filename"]
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


def load_layer_resolution_manifest(base_dir: Path, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest_path = base_dir / "results" / config["layer_resolution"]["manifest_filename"]
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))
