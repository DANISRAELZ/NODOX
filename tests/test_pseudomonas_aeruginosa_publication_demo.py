from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = PROJECT_ROOT / "examples" / "pseudomonas_aeruginosa_publication_demo"
INPUT_DIR = DEMO_DIR / "input"
EXPECTED_TABLES_DIR = DEMO_DIR / "expected_tables"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def _demo_text() -> str:
    return " ".join(
        path.read_text(encoding="utf-8")
        for path in DEMO_DIR.rglob("*")
        if path.is_file()
    ).lower()


def test_publication_demo_directory_and_required_files_exist() -> None:
    assert DEMO_DIR.is_dir()
    for relative_path in [
        "README.md",
        "publication_use_notes.md",
        "run_demo.ps1",
        "run_demo.sh",
        "input/gene_list.csv",
        "input/manual_curation.csv",
        "input/evidence_quality.csv",
        "input/manifest.yaml",
        "input/provenance.yaml",
        "input/notes.md",
        "expected_tables/README.md",
    ]:
        assert (DEMO_DIR / relative_path).is_file()


def test_demo_preserves_pseudomonas_identity_and_user_curated_provenance() -> None:
    manifest = _read_text(INPUT_DIR / "manifest.yaml")
    provenance = _read_text(INPUT_DIR / "provenance.yaml")
    columns, rows = _read_csv(INPUT_DIR / "gene_list.csv")

    assert "Pseudomonas aeruginosa" in manifest
    assert 'taxon_id: "287"' in manifest
    assert "provenance_type: user_curated" in manifest
    assert "provenance_type: user_curated" in provenance
    assert "gene" in columns
    assert {row["organism_name"] for row in rows} == {"Pseudomonas aeruginosa"}
    assert {row["taxon_id"] for row in rows} == {"287"}

    for forbidden_positive_source in [
        "online_lookup_used: true",
        "controlled_reference_used: true",
        "demo_data_used: true",
        "proxy_data_used: true",
        "cache_data_used: true",
    ]:
        assert forbidden_positive_source not in _demo_text()


def test_demo_documents_conservative_publication_interpretation() -> None:
    readme = _read_text(DEMO_DIR / "README.md").lower()
    notes = _read_text(DEMO_DIR / "publication_use_notes.md").lower()
    combined = f"{readme} {notes}"

    for phrase in [
        "does not represent clinical validation",
        "experimental validation",
        "predictor of clinical efficacy",
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "evidence_quality",
        "evidence_strength",
        "not automatic validation",
        "evolutionary_escape_risk",
        "insufficient evidence does not equal low risk",
        "multiorganism",
    ]:
        assert phrase in combined


def test_demo_keeps_evidence_quality_separate_from_priority() -> None:
    columns, rows = _read_csv(INPUT_DIR / "evidence_quality.csv")
    assert "evidence_confidence_score" in columns
    assert "therapeutic_priority_score" not in columns
    assert {row["evidence_source"] for row in rows} == {"user_curated"}

    combined_rows = " ".join(" ".join(row.values()) for row in rows).lower()
    assert "therapeutic_priority_score" in combined_rows
    assert "evidence_confidence_score" in combined_rows
    assert "insufficient_evidence" in combined_rows
    assert "risk remains unresolved" in combined_rows or "unresolved risk" in combined_rows


def test_demo_expected_tables_are_structures_not_fake_results() -> None:
    expected_files = {
        "ranking_nodos.csv",
        "report_phase2.md",
        "candidate_explanations_simple.csv",
        "candidate_audit.csv",
        "evidence_strength_audit.csv",
        "layer_resolution_summary.csv",
        "publication_candidate_table.csv",
        "publication_interpretation_matrix.csv",
    }
    assert {path.name for path in EXPECTED_TABLES_DIR.iterdir() if path.is_file()} >= expected_files

    for csv_name in expected_files - {"report_phase2.md"}:
        columns, rows = _read_csv(EXPECTED_TABLES_DIR / csv_name)
        assert columns
        assert rows == []

    expected_tables_readme = _read_text(EXPECTED_TABLES_DIR / "README.md").lower()
    assert "headers-only templates" in expected_tables_readme
    assert "do not contain fabricated scores" in expected_tables_readme


def test_demo_scripts_are_safe_and_demo_scoped() -> None:
    ps1 = _read_text(DEMO_DIR / "run_demo.ps1").lower()
    sh = _read_text(DEMO_DIR / "run_demo.sh").lower()
    combined = f"{ps1} {sh}"

    for phrase in [
        "output",
        "workspace",
        "data_user",
        "source_package",
        "offline",
        "dry-run",
    ]:
        assert phrase in combined

    for forbidden_global_write in [
        "data_sessions",
        "data_processed",
        "results/ranking_nodos.csv",
        "results\\ranking_nodos.csv",
    ]:
        assert forbidden_global_write not in combined


def test_demo_does_not_use_disallowed_claims_or_other_organism_dependency() -> None:
    text = _demo_text()

    for disallowed in [
        "clinically_valid",
        "validated_experimentally",
        "safe_target",
        "definitive_target",
        "guaranteed_target",
    ]:
        assert disallowed not in text

    assert "predicts clinical efficacy" not in text
    assert "corynebacterium" not in text

