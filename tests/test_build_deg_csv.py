from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from scripts.build_deg_csv import build_deg_csv


def test_official_headerless_deg_archive_is_normalized_with_version_checksum(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    archive_path = raw_dir / "deg_annotation_p.csv.zip"
    row = (
        '"DEG1008";"DEG10080001";"gyrB";"15644640";"COG0187L";'
        '"DNA packaging";"DNA gyrase subunit B";"Helicobacter pylori 26695";'
        '"NC_000915";"Rich medium";"-";"GO:0003918";"P56061 K4NA78";\n'
    )
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("deg_annotation_p.csv", row)

    output_path = tmp_path / "deg.csv"
    version_path = tmp_path / "deg.version.txt"
    count = build_deg_csv(raw_dir, output_path, version_path)

    normalized = pd.read_csv(output_path)
    assert count == 1
    assert normalized.loc[0, "gene"] == "gyrB"
    assert normalized.loc[0, "organism"] == "Helicobacter pylori 26695"
    assert normalized.loc[0, "uniprot_accessions"] == "P56061 K4NA78"
    assert not bool(normalized.loc[0, "affects_score"])
    version = version_path.read_text(encoding="utf-8")
    assert "deg-local-adapter-v1" in version
    assert "sha256=" in version

    repeated_count = build_deg_csv(raw_dir, output_path, version_path)
    assert repeated_count == 1
    assert len(pd.read_csv(output_path)) == 1
