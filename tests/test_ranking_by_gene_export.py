from __future__ import annotations

import pandas as pd
import pytest

from src.nodos_funcionales.reporting import export_ranking_by_gene


def test_export_ranking_by_gene_keeps_highest_score_per_gene(tmp_path) -> None:
    ranking = pd.DataFrame(
        {
            "gene": ["dupGene", "uniqueGene", "dupGene"],
            "protein_id": ["P1", "P2", "P3"],
            "meta_priority_score": [0.4, 0.7, 0.9],
        }
    )

    by_gene = export_ranking_by_gene(ranking, tmp_path / "ranking_nodos_by_gene.csv")

    assert by_gene["gene_collapse_key"].tolist() == ["dupGene", "uniqueGene"]
    assert by_gene.loc[0, "protein_id"] == "P3"
    assert int(by_gene.loc[0, "accessions_collapsed"]) == 2


def test_export_ranking_by_gene_preserves_unique_genes_and_metadata(tmp_path) -> None:
    ranking = pd.DataFrame(
        {
            "organism": ["Helicobacter pylori", "Helicobacter pylori"],
            "taxon_id": [210, 210],
            "strain": ["not_reported", "not_reported"],
            "gene": ["geneA", "geneB"],
            "protein_id": ["P1", "P2"],
            "meta_priority_score": [0.6, 0.5],
        }
    )

    by_gene = export_ranking_by_gene(ranking, tmp_path / "ranking_nodos_by_gene.csv")

    assert len(by_gene) == 2
    assert {"organism", "taxon_id", "strain", "gene", "protein_id", "meta_priority_score"}.issubset(by_gene.columns)
    assert by_gene["organism"].tolist() == ["Helicobacter pylori", "Helicobacter pylori"]
    assert by_gene["accessions_collapsed"].tolist() == [1, 1]


def test_export_ranking_by_gene_uses_protein_id_when_gene_is_missing(tmp_path) -> None:
    ranking = pd.DataFrame(
        {
            "protein_id": ["P1", "P2"],
            "meta_priority_score": [0.2, 0.8],
        }
    )

    by_gene = export_ranking_by_gene(ranking, tmp_path / "ranking_nodos_by_gene.csv")

    assert by_gene["gene_collapse_key"].tolist() == ["P2", "P1"]


def test_export_ranking_by_gene_cleans_multivalue_and_empty_gene_labels(tmp_path) -> None:
    ranking = pd.DataFrame(
        {
            "gene": [" geneA;alias ", "geneB,alias", "geneC|alias", "", None],
            "protein_id": ["P1", "P2", "P3", "P4", "P5"],
            "meta_priority_score": [0.5, 0.4, 0.3, 0.2, 0.1],
        }
    )

    by_gene = export_ranking_by_gene(ranking, tmp_path / "ranking_nodos_by_gene.csv")

    assert by_gene["gene_collapse_key"].tolist() == ["geneA", "geneB", "geneC", "unknown"]
    assert int(by_gene.loc[by_gene["gene_collapse_key"] == "unknown", "accessions_collapsed"].iloc[0]) == 2


def test_export_ranking_by_gene_fails_without_supported_score_column(tmp_path) -> None:
    ranking = pd.DataFrame({"gene": ["geneA"], "protein_id": ["P1"]})

    with pytest.raises(ValueError, match="no supported score column found"):
        export_ranking_by_gene(ranking, tmp_path / "ranking_nodos_by_gene.csv")
