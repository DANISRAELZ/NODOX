from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.nodos_funcionales.string_local_dataset import materialize_string_local_network


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    (workspace / "data_external").mkdir(parents=True)
    (workspace / "results").mkdir(parents=True)
    pd.DataFrame(
        [
            {"protein_id": "P1", "gene": "geneA", "locus_tag": "b0001"},
            {"protein_id": "P2", "gene": "geneB", "locus_tag": "b0002"},
            {"protein_id": "P3", "gene": "geneC", "locus_tag": "b0003"},
            {"protein_id": "P4", "gene": "geneD", "locus_tag": "b0004"},
        ]
    ).to_csv(workspace / "data_external" / "essentiality.csv", index=False)
    return workspace


def _aliases(path: Path) -> None:
    path.write_text(
        "#string_protein_id\talias\tsource\n"
        "511145.b0001\tP1\tUniProt_AC\n"
        "511145.b0001\tgeneA\tBLAST_UniProt_GN\n"
        "511145.b0002\tP2\tUniProt_AC\n"
        "511145.b0002\tgeneB\tBLAST_UniProt_GN\n"
        "511145.b0003\tP3\tUniProt_AC\n"
        "511145.b0003\tgeneC\tBLAST_UniProt_GN\n"
        "511145.b0004\tgeneD\tBLAST_UniProt_GN\n"
        "511145.other\tgeneD\tBLAST_UniProt_GN\n",
        encoding="utf-8",
    )


def _links(path: Path) -> None:
    path.write_text(
        "protein1 protein2 combined_score\n"
        "511145.b0001 511145.b0002 900\n"
        "511145.b0002 511145.b0001 900\n"
        "511145.b0002 511145.b0003 750\n"
        "511145.b0001 511145.b0003 300\n"
        "511145.b0003 511145.b0004 950\n",
        encoding="utf-8",
    )


def test_local_string_materializes_auditable_network(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    aliases = tmp_path / "511145.protein.aliases.v12.0.txt"
    links = tmp_path / "511145.protein.links.v12.0.txt"
    _aliases(aliases)
    _links(links)

    result = materialize_string_local_network(
        workspace=workspace,
        links_path=links,
        aliases_path=aliases,
        taxon_id="511145",
        required_score=400,
    )

    network = result["functional_network"]
    manifest = result["manifest"]
    assert len(network) == 4
    assert manifest["candidate_count"] == 4
    assert manifest["mapped_candidate_count"] == 3
    assert manifest["interaction_edge_count"] == 2
    assert manifest["mapping_coverage_fraction"] == 0.75
    assert manifest["affects_score"] is True
    assert len(manifest["links_sha256"]) == 64
    assert len(manifest["aliases_sha256"]) == 64
    assert (workspace / "data_external" / "functional_network.csv").is_file()
    assert (workspace / "results" / "string_local_mapping_audit.csv").is_file()

    gene_b = network.loc[network["gene"].eq("geneB")].iloc[0]
    assert gene_b["interaction_partner_count"] == 2
    assert gene_b["network_centrality"] > 0

    gene_d = network.loc[network["gene"].eq("geneD")].iloc[0]
    assert gene_d["mapping_status"] == "ambiguous_alias_match"
    assert gene_d["interaction_partner_count"] == 0


def test_local_string_deduplicates_symmetric_edges_and_respects_threshold(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    aliases = tmp_path / "aliases.txt"
    links = tmp_path / "links.txt"
    _aliases(aliases)
    _links(links)

    result = materialize_string_local_network(
        workspace=workspace,
        links_path=links,
        aliases_path=aliases,
        taxon_id="511145",
        required_score=800,
    )

    assert result["manifest"]["interaction_edge_count"] == 1
    network = result["functional_network"]
    assert int(network["interaction_partner_count"].sum()) == 2


def test_local_string_manifest_is_json_serializable(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    aliases = tmp_path / "aliases.txt"
    links = tmp_path / "links.txt"
    _aliases(aliases)
    _links(links)
    result = materialize_string_local_network(
        workspace=workspace,
        links_path=links,
        aliases_path=aliases,
        taxon_id="511145",
    )
    payload = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert payload["provider"] == "string_db"
    assert payload["access_mode"] == "versioned_local_dataset"
    assert payload["negative_evidence_inferred_count"] == 0
