from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.run_online_only_multiorganism_batch import (
    DEFAULT_VALIDATION_ORGANISMS,
    _recommend_demo,
    run_online_only_multiorganism_batch,
)
from tests.helpers import PROJECT_ROOT


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "config").mkdir(parents=True)
    (project / "src" / "nodos_funcionales").mkdir(parents=True)
    shutil.copy2(PROJECT_ROOT / "config" / "online_only_organisms.json", project / "config" / "online_only_organisms.json")
    (project / "src" / "nodos_funcionales" / "scoring.py").write_text("SCORING_VERSION = 1\n", encoding="utf-8")
    (project / "src" / "nodos_funcionales" / "scoring_components.py").write_text(
        "COMPONENT_VERSION = 1\n", encoding="utf-8"
    )
    return project


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fake_runner(**kwargs: Any) -> dict[str, Any]:
    run_dir = Path(kwargs["run_dir"])
    package = run_dir / "review_package"
    package.mkdir(parents=True, exist_ok=True)
    organism = kwargs["organism"]
    taxon_id = kwargs["taxon_id"]
    seed = {
        "retrieval_status": "api_real",
        "source_used": "api_real",
        "candidate_count": 2,
        "api_attempted": True,
        "api_success": True,
        "provider_name": "uniprot_rest",
        "fallback_reason": "",
    }
    (package / "online_only_candidate_seed_manifest.json").write_text(json.dumps(seed), encoding="utf-8")
    _write_csv(
        package / "online_only_provider_audit.csv",
        [
            {
                "layer_key": "candidate_seed",
                "provider_name": "uniprot_rest",
                "api_attempted": True,
                "api_success": True,
                "retrieval_status": "api_real",
                "evidence_level": "computational_online_annotation",
            },
            {
                "layer_key": "virulence",
                "provider_name": "vfdb",
                "api_attempted": False,
                "api_success": False,
                "retrieval_status": "provider_not_implemented",
                "evidence_level": "unresolved",
            },
        ],
    )
    _write_csv(
        package / "layer_resolution_summary.csv",
        [
            {"layer_key": "essentiality", "source_type": "external", "retrieval_status": "resolved_from_external"},
            {"layer_key": "virulence", "source_type": "missing", "retrieval_status": "missing_optional_layer"},
        ],
    )
    _write_csv(
        package / "online_only_provenance_summary.csv",
        [
            {
                "layer_key": "essentiality",
                "source_type": "external",
                "is_user_supplied": False,
                "online_evidence_availability": "online_provider_success",
            }
        ],
    )
    _write_csv(
        package / "ranking_nodos_phase3.csv",
        [
            {
                "protein_id": f"{taxon_id}_A",
                "therapeutic_priority_score": 0.7,
                "evidence_confidence_score": 0.4,
                "therapeutic_role": "mixed_strategy_candidate",
            },
            {
                "protein_id": f"{taxon_id}_B",
                "therapeutic_priority_score": 0.5,
                "evidence_confidence_score": 0.3,
                "therapeutic_role": "low_priority_candidate",
            },
        ],
    )
    (package / "online_only_candidate_interpretation.csv").write_text(
        "protein_id,online_only_validation_status\nA,computational_hypothesis_only\n", encoding="utf-8"
    )
    (package / "ONLINE_ONLY_REVIEW.md").write_text(f"# {organism} Online-Only Validation Review\n", encoding="utf-8")
    return {
        "run_dir": str(run_dir),
        "pipeline_status": "completed",
        "pipeline_error": "",
        "seed_result": seed,
        "package": {},
    }


def test_default_batch_organisms_are_loaded_from_registry() -> None:
    registry = json.loads((PROJECT_ROOT / "config" / "online_only_organisms.json").read_text(encoding="utf-8"))

    assert set(DEFAULT_VALIDATION_ORGANISMS) == {
        "pseudomonas_aeruginosa",
        "escherichia_coli",
        "mycobacterium_tuberculosis",
        "mycobacterium_tuberculosis_h37rv",
    }
    assert set(DEFAULT_VALIDATION_ORGANISMS).issubset(registry)


def test_batch_with_fake_runs_generates_all_comparison_artifacts(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = run_online_only_multiorganism_batch(
        project_root=project,
        organism_keys=["escherichia_coli", "mycobacterium_tuberculosis_h37rv"],
        run_label="fake_batch",
        max_candidates=2,
        continue_on_error=True,
        output_dir=project / "out",
        organism_runner=_fake_runner,
    )
    batch_dir = Path(result["batch_dir"])

    for filename in (
        "batch_manifest.json",
        "batch_provider_audit.csv",
        "batch_layer_resolution_summary.csv",
        "batch_candidate_seed_summary.csv",
        "batch_ranking_summary.csv",
        "batch_run_status.csv",
        "ONLINE_ONLY_MULTIORGANISM_REVIEW.md",
    ):
        assert (batch_dir / filename).exists()
    assert (batch_dir / "organism_runs" / "escherichia_coli").is_dir()
    assert (batch_dir / "organism_runs" / "mycobacterium_tuberculosis_h37rv").is_dir()

    manifest = json.loads((batch_dir / "batch_manifest.json").read_text(encoding="utf-8"))
    assert manifest["scoring_modified"] is False
    assert manifest["input_policy"] == "online_only_no_user_curated_no_hidden_snapshot_fallback"


def test_batch_status_preserves_scores_and_zero_user_curated_layers(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = run_online_only_multiorganism_batch(
        project_root=project,
        organism_keys=["escherichia_coli"],
        run_label="provenance_batch",
        output_dir=project / "out",
        organism_runner=_fake_runner,
    )

    status = result["status_rows"][0]
    assert status["user_curated_layers_detected"] == 0
    assert status["therapeutic_priority_score_present"] is True
    assert status["evidence_confidence_score_present"] is True
    assert status["scoring_modified"] is False
    assert status["candidate_seed_count"] == 2


def test_continue_on_error_records_failure_and_runs_next_organism(tmp_path: Path) -> None:
    project = _project(tmp_path)
    calls: list[str] = []

    def sometimes_fails(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs["organism"])
        if kwargs["organism"] == "Escherichia coli":
            raise TimeoutError("provider timeout")
        return _fake_runner(**kwargs)

    result = run_online_only_multiorganism_batch(
        project_root=project,
        organism_keys=["escherichia_coli", "mycobacterium_tuberculosis_h37rv"],
        run_label="continue_batch",
        continue_on_error=True,
        output_dir=project / "out",
        organism_runner=sometimes_fails,
    )

    assert calls == ["Escherichia coli", "Mycobacterium tuberculosis"]
    assert result["status_rows"][0]["pipeline_status"] == "batch_runner_exception"
    assert "provider timeout" in result["status_rows"][0]["notes"]
    assert result["status_rows"][1]["pipeline_status"] == "completed"


def test_pseudomonas_uses_the_same_generic_runner_contract(tmp_path: Path) -> None:
    project = _project(tmp_path)
    received: list[dict[str, Any]] = []

    def records_call(**kwargs: Any) -> dict[str, Any]:
        received.append(kwargs)
        return _fake_runner(**kwargs)

    run_online_only_multiorganism_batch(
        project_root=project,
        organism_keys=["pseudomonas_aeruginosa", "escherichia_coli"],
        run_label="generic_contract",
        output_dir=project / "out",
        organism_runner=records_call,
    )

    assert received[0]["organism"] == "Pseudomonas aeruginosa"
    assert received[0]["taxon_id"] == 287
    assert received[0]["materialize_unresolved_required_fallback"] is True
    assert received[1]["materialize_unresolved_required_fallback"] is True
    assert set(received[0]) == set(received[1])


def test_batch_source_has_no_hidden_default_or_scoring_write() -> None:
    source = (PROJECT_ROOT / "scripts" / "run_online_only_multiorganism_batch.py").read_text(encoding="utf-8")

    assert "run_pseudomonas_online_only_validation" not in source
    assert 'if organism_key == "pseudomonas_aeruginosa"' not in source
    assert "scoring.py\").write" not in source
    assert "online_only_organisms.json" in source


def test_batch_collects_provider_manifests_when_layer_summary_is_absent(tmp_path: Path) -> None:
    project = _project(tmp_path)

    def manifests_without_pipeline_summary(**kwargs: Any) -> dict[str, Any]:
        result = _fake_runner(**kwargs)
        package = Path(kwargs["run_dir"]) / "review_package"
        (package / "layer_resolution_summary.csv").unlink()
        (package / "online_only_host_annotation_manifest.json").write_text(
            json.dumps(
                {
                    "layer_key": "host_annotation",
                    "provider_name": "interpro_api",
                    "api_attempted": False,
                    "api_success": False,
                    "retrieval_status": "no_candidate_records",
                    "fallback_reason": "no_candidate_records",
                    "evidence_level": "unresolved",
                }
            ),
            encoding="utf-8",
        )
        return result

    result = run_online_only_multiorganism_batch(
        project_root=project,
        organism_keys=["escherichia_coli"],
        run_label="manifest_fallback",
        output_dir=project / "out",
        organism_runner=manifests_without_pipeline_summary,
    )

    provider_layers = {row["layer_key"] for row in result["provider_rows"]}
    layer_keys = {row["layer_key"] for row in result["layer_rows"]}
    assert "host_annotation" in provider_layers
    assert "host_annotation" in layer_keys


def test_demo_recommendation_does_not_default_to_first_organism_without_evidence() -> None:
    statuses = [
        {
            "organism_key": "pseudomonas_aeruginosa",
            "candidate_seed_count": 0,
            "ranking_rows": 0,
            "providers_success": "",
            "user_curated_layers_detected": 0,
        },
        {
            "organism_key": "escherichia_coli",
            "candidate_seed_count": 0,
            "ranking_rows": 0,
            "providers_success": "",
            "user_curated_layers_detected": 0,
        },
    ]

    recommendation = _recommend_demo(statuses)

    assert "No principal demo is recommended" in recommendation
    assert "pseudomonas_aeruginosa" not in recommendation
