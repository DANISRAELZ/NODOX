from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.run_online_only_publication_multiorganism_7K import (
    DEFAULT_7K_ORGANISMS,
    run_publication_multiorganism_7k,
)
from src.nodos_funcionales.provider_contracts import PROVIDER_CONTRACTS
from tests.helpers import PROJECT_ROOT


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "src" / "nodos_funcionales").mkdir(parents=True)
    shutil.copy2(PROJECT_ROOT / "src" / "nodos_funcionales" / "scoring.py", project / "src" / "nodos_funcionales" / "scoring.py")
    shutil.copy2(
        PROJECT_ROOT / "src" / "nodos_funcionales" / "scoring_components.py",
        project / "src" / "nodos_funcionales" / "scoring_components.py",
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
    seed_success = "Mycobacterium" not in organism
    seed = {
        "api_success": seed_success,
        "candidate_count": 2 if seed_success else 0,
        "retrieval_status": "connected_structured_payload" if seed_success else "ssl_error",
        "provider": "uniprot_candidate_seed",
    }
    (package / "online_only_candidate_seed_manifest.json").write_text(json.dumps(seed), encoding="utf-8")
    _write_csv(
        package / "online_only_provider_audit.csv",
        [
            {
                "layer_key": "candidate_seed",
                "provider_name": "uniprot_candidate_seed",
                "api_attempted": True,
                "api_success": seed_success,
                "retrieval_status": seed["retrieval_status"],
                "retrieved_record_count": seed["candidate_count"],
                "matched_candidate_count": seed["candidate_count"],
            },
            {
                "layer_key": "localization",
                "provider_name": "uniprot_rest",
                "api_attempted": True,
                "api_success": seed_success,
                "retrieval_status": "connected_structured_payload" if seed_success else "network_error",
                "retrieved_record_count": 2 if seed_success else 0,
                "matched_candidate_count": 2 if seed_success else 0,
            },
            {
                "layer_key": "functional_network",
                "provider_name": "string_db",
                "api_attempted": True,
                "api_success": False,
                "retrieval_status": "ssl_error",
                "retrieved_record_count": 0,
                "matched_candidate_count": 0,
            },
            {
                "layer_key": "host_annotation",
                "provider_name": "interpro",
                "api_attempted": True,
                "api_success": False,
                "retrieval_status": "network_error",
                "retrieved_record_count": 0,
                "matched_candidate_count": 0,
            },
            {
                "layer_key": "strain_conservation",
                "provider_name": "bvbrc",
                "api_attempted": True,
                "api_success": False,
                "retrieval_status": "empty_payload",
                "retrieved_record_count": 0,
                "matched_candidate_count": 0,
            },
            {
                "layer_key": "virulence",
                "provider_name": "vfdb",
                "api_attempted": True,
                "api_success": False,
                "retrieval_status": "html_instead_of_structured_payload",
                "retrieved_record_count": 0,
                "matched_candidate_count": 0,
            },
            {
                "layer_key": "essentiality",
                "provider_name": "deg",
                "api_attempted": True,
                "api_success": False,
                "retrieval_status": "unsupported_structured_archive",
                "retrieved_record_count": 0,
                "matched_candidate_count": 0,
            },
            {
                "layer_key": "literature_support",
                "provider_name": "europe_pmc",
                "api_attempted": True,
                "api_success": True,
                "retrieval_status": "connected_structured_payload",
                "retrieved_record_count": 1,
                "matched_candidate_count": 1,
            },
        ],
    )
    _write_csv(
        package / "ranking_nodos_phase3.csv",
        [
            {"protein_id": "A", "gene": "geneA", "therapeutic_priority_score": 0.7},
            {"protein_id": "B", "gene": "geneB", "therapeutic_priority_score": 0.6},
        ],
    )
    return {"pipeline_status": "completed" if seed_success else "candidate_seed_failed", "pipeline_error": ""}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_7k_runner_includes_three_required_organisms() -> None:
    assert [(item["organism"], item["taxon_id"]) for item in DEFAULT_7K_ORGANISMS] == [
        ("Pseudomonas aeruginosa", 287),
        ("Escherichia coli", 562),
        ("Mycobacterium tuberculosis", 1773),
    ]


def test_7k_runner_uses_contracts_and_creates_required_outputs(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = run_publication_multiorganism_7k(
        project_root=project,
        output_dir=project / "out7k",
        timestamp="test_run",
        organism_runner=_fake_runner,
    )
    run_dir = Path(result["run_dir"])
    for organism in ("pseudomonas_aeruginosa", "escherichia_coli", "mycobacterium_tuberculosis"):
        organism_dir = run_dir / organism
        for filename in (
            "candidate_seed_manifest.json",
            "provider_status.csv",
            "provider_status.json",
            "accepted_evidence_summary.csv",
            "degraded_provider_summary.csv",
            "online_only_candidates.csv",
            "online_only_review.md",
            "provenance_manifest.json",
        ):
            assert (organism_dir / filename).exists()
    for filename in (
        "multiorganism_provider_matrix_7K.csv",
        "multiorganism_provider_matrix_7K.json",
        "multiorganism_candidate_summary_7K.csv",
        "multiorganism_online_only_review_7K.md",
        "publication_limitations_7K.md",
        "reproducibility_manifest_7K.json",
    ):
        assert (run_dir / filename).exists()
    manifest = json.loads((run_dir / "reproducibility_manifest_7K.json").read_text(encoding="utf-8"))
    assert set(manifest["contracts_used"]) == set(PROVIDER_CONTRACTS)


def test_candidate_seed_is_blocking_but_other_providers_are_not(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = run_publication_multiorganism_7k(project, project / "out7k", "blocking", organism_runner=_fake_runner)
    matrix = _read_csv(Path(result["run_dir"]) / "multiorganism_provider_matrix_7K.csv")
    seed_rows = [row for row in matrix if row["provider"] == "candidate_seed"]
    non_seed_rows = [row for row in matrix if row["provider"] != "candidate_seed"]
    assert any(row["blocks_ranking"] == "true" for row in seed_rows)
    assert all(row["blocks_ranking"] == "false" for row in non_seed_rows)


def test_degraded_payloads_do_not_generate_positive_or_strong_negative_evidence(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = run_publication_multiorganism_7k(project, project / "out7k", "degraded", organism_runner=_fake_runner)
    matrix = _read_csv(Path(result["run_dir"]) / "multiorganism_provider_matrix_7K.csv")
    degraded_statuses = {
        "ssl_error",
        "network_error",
        "empty_payload",
        "html_instead_of_structured_payload",
        "unsupported_structured_archive",
    }
    degraded = [row for row in matrix if row["final_status"] in degraded_statuses]
    assert degraded
    assert all(row["evidence_inferred"] == "false" for row in degraded)
    assert all(row["affects_score"] == "false" for row in degraded)
    assert any(row["payload_type"] == "empty" for row in degraded)
    assert any(row["payload_type"] == "html" for row in degraded)
    assert any(row["payload_type"] == "zip" for row in degraded)


def test_reports_include_publication_limitations_and_no_disallowed_edits(tmp_path: Path) -> None:
    project = _project(tmp_path)
    result = run_publication_multiorganism_7k(project, project / "out7k", "limitations", organism_runner=_fake_runner)
    run_dir = Path(result["run_dir"])
    text = (run_dir / "publication_limitations_7K.md").read_text(encoding="utf-8")
    assert "does not validate targets clinically" in text
    assert "Empty payloads do not imply biological absence" in text
    assert "candidate_seed is the only strict blocking layer" in text
    forbidden_organism = "coryne" + "bacterium"
    assert forbidden_organism not in text.casefold()
    git_diff = __import__("subprocess").run(
        [
            "git",
            "diff",
            "--name-only",
                "--",
                "src/nodos_funcionales/scoring_components.py",
                "gui",
                "apps",
            ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert git_diff.stdout.strip() == ""
