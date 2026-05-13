from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


KEY_DOCUMENTS = [
    ROOT / "README.md",
    ROOT / "docs" / "project_boundaries.md",
    ROOT / "docs" / "functional_nodes_theory_operationalization.md",
    ROOT / "docs" / "online_organism_enrichment.md",
    ROOT / "docs" / "generic_annotation_import.md",
    ROOT / "docs" / "curated_snapshots.md",
]


PROBLEMATIC_PHRASES = [
    "project centered on " + "Corynebacterium",
    "Corynebacterium " + "project",
    "Mexican " + "isolates",
    "aislados " + "mexicanos",
    "cpseudo" + "_mexico",
    "17 " + "isolates",
    "pangenome " + "mexicano",
]


def test_theory_operationalization_document_replaces_organism_specific_plan():
    theory_doc = ROOT / "docs" / "functional_nodes_theory_operationalization.md"
    organism_plan = ROOT / "docs" / ("cpseudotuberculosis" + "_data_integration_plan.md")

    assert theory_doc.exists()
    assert not organism_plan.exists()


def test_key_docs_keep_the_functional_nodes_theory_at_the_center():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in KEY_DOCUMENTS)

    assert "Teoria de Nodos Funcionales" in combined or "Functional Nodes Theory" in combined
    assert "multi-organismo" in combined or "multi-organism" in combined


def test_key_docs_do_not_reintroduce_project_coupling_phrases():
    for path in KEY_DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        for phrase in PROBLEMATIC_PHRASES:
            assert phrase not in text, f"{phrase!r} found in {path}"


def test_theory_doc_treats_evolutionary_axis_as_central():
    text = (ROOT / "docs" / "functional_nodes_theory_operationalization.md").read_text(
        encoding="utf-8"
    )

    required_terms = [
        "Postulado 5",
        "evolutionary_escape_risk",
        "evolutionary_constraint",
        "mutation_tolerance",
        "pathway_redundancy",
        "paralog_count",
        "mobile_context",
        "hgt_context",
        "recombination_context",
        "resistance_association",
        "elementos distintivos",
        "not_detected_with_method",
    ]
    for term in required_terms:
        assert term in text
