from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.generic_annotation_import import (
    build_evolutionary_escape_risk_table,
    build_strain_conservation_table,
    empty_layer_table,
    parse_prokka_annotations,
    parse_roary_gene_presence_absence,
    parse_vfdb_results,
    write_layer_csvs,
)
from tests.helpers import PROJECT_ROOT


FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "generic_organism_annotations"


def test_parse_prokka_annotations_extracts_gene_product() -> None:
    df = parse_prokka_annotations(FIXTURES / "prokka_sample.tsv")

    assert {"protein_id", "gene", "product"}.issubset(df.columns)
    assert df.loc[df["gene"] == "pld", "product"].iloc[0].startswith("phospholipase D")


def test_roary_conservation_uses_presence_fraction_thresholds() -> None:
    roary = parse_roary_gene_presence_absence(FIXTURES / "roary_gene_presence_absence_sample.csv")
    conservation = build_strain_conservation_table(roary)

    pld = conservation.loc[conservation["gene"] == "pld"].iloc[0]
    spa_a = conservation.loc[conservation["gene"] == "spaA"].iloc[0]
    assert float(pld["conservation_fraction"]) == 1.0
    assert pld["core_status"] == "core"
    assert round(float(spa_a["conservation_fraction"]), 2) == 0.67
    assert spa_a["core_status"] == "accessory"


def test_vfdb_generates_virulence_table_with_real_external_provenance() -> None:
    virulence = parse_vfdb_results(FIXTURES / "vfdb_sample.tsv")

    assert list(virulence[["protein_id", "gene", "virulence_score", "virulence_factor"]].columns)
    assert set(virulence["provenance_status"]) == {"real_external"}
    assert virulence["virulence_score"].between(0, 1).all()


def test_missing_input_is_not_negative_evidence() -> None:
    essentiality = empty_layer_table("essentiality", "insufficient_evidence", "No DEG input.")

    assert essentiality.empty
    assert "essential" in essentiality.columns
    assert essentiality.attrs["provenance_status"] == "insufficient_evidence"


def test_evolutionary_escape_risk_uses_available_context_without_assuming_absence() -> None:
    roary = parse_roary_gene_presence_absence(FIXTURES / "roary_gene_presence_absence_sample.csv")
    conservation = build_strain_conservation_table(roary)
    mobile = pd.DataFrame({"protein_id": ["CPS_0004"], "gene": ["spaA"], "mobile_context": [1.0]})
    hgt = pd.DataFrame({"protein_id": ["CPS_0004"], "gene": ["spaA"], "hgt_context": [1.0]})

    escape = build_evolutionary_escape_risk_table(conservation, mobile=mobile, hgt=hgt)
    spa_a = escape.loc[escape["gene"] == "spaA"].iloc[0]

    assert "evolutionary_escape_risk_score" in escape.columns
    assert float(spa_a["mobile_context"]) == 1.0
    assert float(spa_a["hgt_context"]) == 1.0
    assert spa_a["provenance_status"] == "inferred_proxy"


def test_write_layer_csvs_creates_expected_columns_when_some_files_missing(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    shutil.copy2(FIXTURES / "roary_gene_presence_absence_sample.csv", input_dir / "gene_presence_absence.csv")

    workspace = tmp_path / "workspace"
    summaries = write_layer_csvs(workspace, input_dir, "Corynebacterium pseudotuberculosis", "biovar ovis")

    summary_by_layer = {summary.layer: summary for summary in summaries}
    assert summary_by_layer["strain_conservation"].rows == 3
    assert summary_by_layer["virulence"].rows == 0
    assert summary_by_layer["virulence"].provenance_status in {"missing_input", "insufficient_evidence"}
    for filename in [
        "essentiality.csv",
        "virulence.csv",
        "strain_conservation.csv",
        "functional_network.csv",
        "localization.csv",
        "evolutionary_escape_risk.csv",
        "literature_support.csv",
    ]:
        assert (workspace / "data_raw" / filename).exists()


def test_import_does_not_modify_pao1_reference_files(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    shutil.copytree(FIXTURES, input_dir)
    workspace = tmp_path / "workspace"
    before = (PROJECT_ROOT / "data_raw" / "virulence.csv").read_text(encoding="utf-8")

    write_layer_csvs(workspace, input_dir, "Corynebacterium pseudotuberculosis", "biovar ovis")

    after = (PROJECT_ROOT / "data_raw" / "virulence.csv").read_text(encoding="utf-8")
    assert after == before
