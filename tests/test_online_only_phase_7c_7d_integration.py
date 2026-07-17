from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

from scripts.run_online_only_multiorganism_batch import build_parser, run_online_only_multiorganism_batch
from tests.test_online_only_multiorganism_batch import _fake_runner, _project


def test_runner_accepts_both_flags() -> None:
    args = build_parser().parse_args([
        "--organism-keys", "escherichia_coli", "--run-label", "phase7cd",
        "--check-provider-connectivity", "--normalize-external-evidence",
    ])
    assert args.check_provider_connectivity is True
    assert args.normalize_external_evidence is True


def test_both_phases_generate_packages_without_changing_scores(tmp_path) -> None:
    project = _project(tmp_path)
    scoring_before = (project / "src" / "nodos_funcionales" / "scoring.py").read_bytes()
    fake_rows = [{
        "provider_name": "UniProt", "provider_url": "https://example.test", "provider_category": "protein_annotation",
        "organism_query": "taxonomy_id:562", "query_used": "taxonomy_id:562", "taxon_id": 562,
        "organism_label": "Escherichia coli", "status": "success", "http_status": 200, "records_found": 1,
        "error_type": "", "error_message": "", "blocking": False, "checked_at": "now",
        "provenance_level": "external_connectivity_audit", "evidence_scope": "seed_candidate", "interpretation_warning": "limited",
    }]
    with patch("scripts.run_online_only_multiorganism_batch.run_provider_connectivity_audit") as audit:
        audit.return_value = {"output_dir": str(project / "results" / "online_only_provider_connectivity" / "phase7cd"), "rows": fake_rows, "manifest": {"phase": "7C"}}
        result = run_online_only_multiorganism_batch(
            project, ["escherichia_coli"], "phase7cd", output_dir=project / "batch",
            organism_runner=_fake_runner, check_provider_connectivity=True, normalize_external_evidence=True,
        )
    evidence_dir = project / "results" / "online_only_external_evidence" / "phase7cd"
    assert result["manifest"]["phase_7c_enabled"] is True
    assert result["manifest"]["phase_7d_enabled"] is True
    assert (evidence_dir / "external_evidence_manifest.json").exists()
    assert (project / "src" / "nodos_funcionales" / "scoring.py").read_bytes() == scoring_before
    source = inspect.getsource(__import__("src.nodos_funcionales.external_evidence_normalization", fromlist=["*"]))
    assert "from .scoring" not in source
    assert "import scoring" not in source
