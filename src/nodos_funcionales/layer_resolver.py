from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .acquisition import map_source_dataframe
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
    online_source_mode = effective_online_source_mode(config)

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

    if definition.allow_proxy_default:
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
