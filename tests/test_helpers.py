from __future__ import annotations

from tests.helpers import PROJECT_ROOT, make_temp_project


def test_make_temp_project_isolates_mutable_repository_inputs() -> None:
    source_path = PROJECT_ROOT / "data_raw" / "contextual_essentiality.csv"
    source_before = source_path.read_bytes()

    project_dir = make_temp_project()
    isolated_path = project_dir / "data_raw" / "contextual_essentiality.csv"
    isolated_path.write_text(
        "protein_id,gene,contextual_essentiality_score\nTEST0001,test_gene,0.75\n",
        encoding="utf-8",
    )

    assert project_dir.resolve() != PROJECT_ROOT.resolve()
    assert (project_dir / "config" / "params.yaml").is_file()
    assert (project_dir / "data_processed").is_dir()
    assert (project_dir / "results").is_dir()
    assert source_path.read_bytes() == source_before
