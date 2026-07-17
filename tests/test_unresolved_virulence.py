from __future__ import annotations

import json

import pandas as pd
import pytest

from src.nodos_funcionales.unresolved_virulence import materialize_unresolved_virulence_layer


def test_materialize_unresolved_virulence_from_normalized_localization(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    processed = workspace / "data_processed"
    processed.mkdir(parents=True)
    pd.DataFrame(
        {
            "protein_id": ["A", "B", "C"],
            "gene": ["geneA", "geneB", "geneC"],
        }
    ).to_csv(processed / "normalized_localization.csv", index=False)

    materialize_unresolved_virulence_layer(workspace)

    for filename in ["normalized_virulence.csv", "validated_virulence.csv"]:
        path = processed / filename
        assert path.exists()
        virulence = pd.read_csv(path)
        assert len(virulence) == 3
        assert {
            "protein_id",
            "protein_id_original",
            "protein_id_canonical",
            "virulence_factor",
            "evidence",
            "source_database",
            "mapping_confidence",
        }.issubset(virulence.columns)
        assert virulence["protein_id"].tolist() == ["A", "B", "C"]
        assert virulence["evidence"].eq("unresolved").all()
        assert virulence["source_database"].eq("provider_not_implemented").all()
        assert virulence["mapping_confidence"].eq(0.0).all()
        assert virulence["virulence_factor"].isna().all()


def test_materialize_unresolved_virulence_does_not_overwrite_existing_files(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    processed = workspace / "data_processed"
    processed.mkdir(parents=True)
    original = pd.DataFrame(
        {
            "protein_id": ["REAL"],
            "gene": ["realGene"],
            "virulence_score": [0.8],
            "virulence_factor": [1],
        }
    )
    original.to_csv(processed / "normalized_virulence.csv", index=False)
    original.to_csv(processed / "validated_virulence.csv", index=False)
    pd.DataFrame({"protein_id": ["A", "B", "C"]}).to_csv(processed / "normalized_localization.csv", index=False)

    materialize_unresolved_virulence_layer(workspace)

    normalized = pd.read_csv(processed / "normalized_virulence.csv")
    validated = pd.read_csv(processed / "validated_virulence.csv")
    pd.testing.assert_frame_equal(normalized, original)
    pd.testing.assert_frame_equal(validated, original)


def test_materialize_unresolved_virulence_fails_without_identifiers(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "data_processed").mkdir(parents=True)

    with pytest.raises(ValueError, match="Cannot materialize unresolved virulence layer: no protein identifiers found in workspace"):
        materialize_unresolved_virulence_layer(workspace)


def test_materialize_unresolved_virulence_uses_uniprot_accession(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    raw = workspace / "data_raw"
    raw.mkdir(parents=True)
    pd.DataFrame(
        {
            "uniprot_accession": ["P12345", "Q8XYZ1"],
            "uniprot_gene_primary": ["seedA", "seedB"],
        }
    ).to_csv(raw / "uniprot_annotations.csv", index=False)

    materialize_unresolved_virulence_layer(workspace)

    virulence = pd.read_csv(workspace / "data_processed" / "normalized_virulence.csv")
    assert virulence["protein_id"].tolist() == ["P12345", "Q8XYZ1"]
    assert virulence["gene"].tolist() == ["seedA", "seedB"]


def test_materialize_unresolved_virulence_updates_manifests(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    processed = workspace / "data_processed"
    results = workspace / "results"
    processed.mkdir(parents=True)
    results.mkdir(parents=True)
    pd.DataFrame({"protein_id": ["A"]}).to_csv(processed / "normalized_localization.csv", index=False)
    (results / "online_only_virulence_manifest.json").write_text(
        json.dumps({"layer_key": "virulence", "retrieval_status": "provider_not_implemented"}),
        encoding="utf-8",
    )

    materialize_unresolved_virulence_layer(workspace)

    online_manifest = json.loads((results / "online_only_virulence_manifest.json").read_text(encoding="utf-8"))
    layer_manifest = json.loads((results / "layer_resolution_manifest.json").read_text(encoding="utf-8"))
    validation = pd.read_csv(processed / "validation_summary.csv")
    assert online_manifest["retrieval_status"] == "unresolved"
    assert online_manifest["source_database"] == "provider_not_implemented"
    assert online_manifest["evidence"] == "unresolved"
    assert layer_manifest["virulence"]["retrieval_status"] == "unresolved"
    assert layer_manifest["virulence"]["source_name"] == "provider_not_implemented"
    assert "unresolved_layer_materialized" in set(validation["issue_type"])
