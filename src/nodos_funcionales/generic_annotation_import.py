from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd


PROVENANCE_STATUSES = {
    "real_external",
    "user_supplied",
    "curated_snapshot",
    "controlled_provider",
    "inferred_proxy",
    "demo",
    "missing_input",
    "insufficient_evidence",
}

VIRULENCE_GENES = {
    "pld",
    "faga",
    "fagb",
    "fagc",
    "fagd",
    "hmut",
    "hmuu",
    "hmuv",
    "ciua",
    "ciub",
    "ciuc",
    "ciud",
    "ciue",
    "dtxr",
    "sodc",
    "spaa",
    "spac",
    "spad",
    "srta",
    "srtb",
    "srtc",
    "sapa",
}

PROVENANCE_COLUMNS = [
    "evidence_source",
    "evidence_level",
    "retrieval_mode",
    "cache_status",
    "source_version",
    "generated_at_utc",
    "provenance_status",
    "notes",
]

LAYER_COLUMNS = {
    "essentiality": [
        "protein_id",
        "gene",
        "essential",
        "evidence",
        "database",
        "essentiality_status",
        *PROVENANCE_COLUMNS,
    ],
    "virulence": [
        "protein_id",
        "gene",
        "virulence_score",
        "virulence_factor",
        "database",
        "gene_id",
        "gene_name",
        "product",
        "virulence_factor_name",
        "virulence_category",
        *PROVENANCE_COLUMNS,
    ],
    "strain_conservation": [
        "protein_id",
        "gene",
        "core_genome_presence",
        "strain_coverage_score",
        "allelic_conservation",
        "variant_burden",
        "database",
        "gene_id",
        "gene_name",
        "presence_count",
        "total_strains",
        "conservation_fraction",
        "core_status",
        *PROVENANCE_COLUMNS,
    ],
    "functional_network": [
        "protein_id",
        "gene",
        "network_centrality",
        "pathway_bottleneck_score",
        "redundancy_penalty",
        "functional_dependency_score",
        "database",
        "source_gene",
        "target_gene",
        "interaction_score",
        "interaction_type",
        *PROVENANCE_COLUMNS,
    ],
    "localization": [
        "protein_id",
        "gene",
        "localization",
        "database",
        "gene_id",
        "gene_name",
        "membrane_associated",
        "secreted",
        "surface_exposed",
        *PROVENANCE_COLUMNS,
    ],
    "evolutionary_escape_risk": [
        "protein_id",
        "gene",
        "candidate_id",
        "organism",
        "strain",
        "mutation_tolerance_score",
        "functional_redundancy_escape_score",
        "compensatory_pathway_score",
        "fitness_cost_of_escape",
        "evolutionary_constraint_score",
        "resistance_emergence_risk",
        "multi_node_dependency_score",
        "evolutionary_escape_risk_score",
        "evidence_source",
        "source_type",
        "confidence",
        "notes",
        "paralog_count",
        "pathway_redundancy",
        "mutation_tolerance",
        "conservation_fraction",
        "mobile_context",
        "hgt_context",
        "recombination_context",
        "resistance_association",
        "retrieval_mode",
        "cache_status",
        "source_version",
        "generated_at_utc",
        "provenance_status",
        "database",
    ],
    "literature_support": [
        "protein_id",
        "gene",
        "literature_support_score",
        "gene_id",
        "topic",
        "evidence_summary",
        "reference",
        "doi_or_url",
        "evidence_level",
        "provenance_status",
        "evidence_type",
        "notes",
        "source_quality",
        "database",
        "generated_at_utc",
    ],
}


@dataclass(frozen=True)
class ImportSummary:
    layer: str
    path: Path
    rows: int
    provenance_status: str
    warnings: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_layer_table(layer: str, provenance_status: str = "missing_input", notes: str = "") -> pd.DataFrame:
    if provenance_status not in PROVENANCE_STATUSES:
        raise ValueError(f"provenance_status no permitido: {provenance_status}")
    df = pd.DataFrame(columns=LAYER_COLUMNS[layer])
    df.attrs["provenance_status"] = provenance_status
    df.attrs["notes"] = notes
    return df


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".tsv", ".txt"}:
        return pd.read_csv(path, sep="\t")
    return pd.read_csv(path)


def _first_existing(input_dir: Path, names: Iterable[str]) -> Path | None:
    for name in names:
        path = input_dir / name
        if path.exists():
            return path
    return None


def _find_column(df: pd.DataFrame, aliases: Iterable[str]) -> str | None:
    lowered = {str(column).casefold(): column for column in df.columns}
    for alias in aliases:
        if alias.casefold() in lowered:
            return lowered[alias.casefold()]
    return None


def _norm_gene(value: object) -> str:
    text = str(value or "").strip()
    return text if text and text.lower() != "nan" else "unknown"


def _gene_key(value: object) -> str:
    return _norm_gene(value).replace("_", "").replace("-", "").casefold()


def _base_provenance(
    source: str,
    status: str,
    evidence_level: str = "annotation",
    retrieval_mode: str = "local_file",
    notes: str = "",
) -> dict[str, object]:
    return {
        "evidence_source": source,
        "evidence_level": evidence_level,
        "retrieval_mode": retrieval_mode,
        "cache_status": "not_cached",
        "source_version": "not_reported",
        "generated_at_utc": utc_now(),
        "provenance_status": status,
        "notes": notes,
    }


def parse_prokka_annotations(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["protein_id", "gene", "product", "source_file"])
    df = _read_table(path)
    locus_col = _find_column(df, ["locus_tag", "protein_id", "gene_id", "feature_id"])
    gene_col = _find_column(df, ["gene", "gene_name", "name"])
    product_col = _find_column(df, ["product", "annotation", "description"])
    rows = []
    for _, row in df.iterrows():
        protein_id = str(row.get(locus_col, "")).strip() if locus_col else ""
        gene = _norm_gene(row.get(gene_col, protein_id)) if gene_col else protein_id
        rows.append(
            {
                "protein_id": protein_id or gene,
                "gene": gene or protein_id,
                "product": str(row.get(product_col, "")).strip() if product_col else "",
                "source_file": str(path),
            }
        )
    return pd.DataFrame(rows)


def parse_roary_gene_presence_absence(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def parse_vfdb_results(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return empty_layer_table("virulence", notes="No VFDB/VFanalyzer file found.")
    df = _read_table(path)
    gene_col = _find_column(df, ["gene", "gene_name", "vf_gene", "query", "locus_tag"])
    id_col = _find_column(df, ["protein_id", "gene_id", "locus_tag", "query", "feature_id"])
    product_col = _find_column(df, ["product", "function", "description", "vf_name"])
    category_col = _find_column(df, ["virulence_category", "category", "vf_category"])
    score_col = _find_column(df, ["virulence_score", "score", "identity", "bit_score"])
    rows = []
    for _, row in df.iterrows():
        gene = _norm_gene(row.get(gene_col, row.get(id_col, "unknown")))
        protein_id = str(row.get(id_col, gene)).strip() or gene
        raw_score = pd.to_numeric(pd.Series([row.get(score_col, 1.0)]), errors="coerce").fillna(1.0).iloc[0]
        score = float(raw_score) / 100.0 if float(raw_score) > 1 else float(raw_score)
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "virulence_score": max(0.0, min(1.0, score)),
                "virulence_factor": 1,
                "database": "vfdb_or_vfanalyzer_local",
                "gene_id": protein_id,
                "gene_name": gene,
                "product": str(row.get(product_col, "")).strip() if product_col else "",
                "virulence_factor_name": str(row.get(product_col, gene)).strip() if product_col else gene,
                "virulence_category": str(row.get(category_col, "not_reported")).strip() if category_col else "not_reported",
                **_base_provenance(str(path), "real_external", "database_match"),
            }
        )
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["virulence"])


def parse_card_rgi_results(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["protein_id", "gene", "resistance_association"])
    df = _read_table(path)
    id_col = _find_column(df, ["protein_id", "orf_id", "query", "locus_tag"])
    gene_col = _find_column(df, ["gene", "best_hit_aro", "model_name", "aro"])
    return pd.DataFrame(
        {
            "protein_id": df[id_col].astype(str) if id_col else df.index.astype(str),
            "gene": df[gene_col].astype(str) if gene_col else "unknown",
            "resistance_association": 1.0,
        }
    )


def parse_mobileog_results(path: Path | None) -> pd.DataFrame:
    return _parse_context_table(path, "mobile_context")


def parse_phastest_results(path: Path | None) -> pd.DataFrame:
    return _parse_context_table(path, "mobile_context")


def parse_alienhunter_results(path: Path | None) -> pd.DataFrame:
    return _parse_context_table(path, "hgt_context")


def _parse_context_table(path: Path | None, flag_column: str) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["protein_id", "gene", flag_column])
    df = _read_table(path)
    id_col = _find_column(df, ["protein_id", "gene_id", "locus_tag", "query", "feature_id"])
    gene_col = _find_column(df, ["gene", "gene_name", "name", "locus_tag"])
    return pd.DataFrame(
        {
            "protein_id": df[id_col].astype(str) if id_col else df.index.astype(str),
            "gene": df[gene_col].astype(str) if gene_col else df[id_col].astype(str) if id_col else "unknown",
            flag_column: 1.0,
        }
    )


def parse_string_network(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["source_gene", "target_gene", "interaction_score", "interaction_type"])
    df = _read_table(path)
    source_col = _find_column(df, ["source_gene", "protein1", "preferredName_A", "node1"])
    target_col = _find_column(df, ["target_gene", "protein2", "preferredName_B", "node2"])
    score_col = _find_column(df, ["interaction_score", "combined_score", "score"])
    if source_col is None or target_col is None:
        return pd.DataFrame(columns=["source_gene", "target_gene", "interaction_score", "interaction_type"])
    score = pd.to_numeric(df[score_col], errors="coerce").fillna(0.0) if score_col else pd.Series([0.0] * len(df))
    score = score.map(lambda value: float(value) / 1000.0 if float(value) > 1 else float(value))
    return pd.DataFrame(
        {
            "source_gene": df[source_col].astype(str),
            "target_gene": df[target_col].astype(str),
            "interaction_score": score.clip(0.0, 1.0),
            "interaction_type": "string_functional",
        }
    )


def parse_uniprot_localization(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return empty_layer_table("localization", notes="No UniProt/PSORTb/SignalP localization file found.")
    df = _read_table(path)
    id_col = _find_column(df, ["protein_id", "gene_id", "locus_tag", "accession", "entry"])
    gene_col = _find_column(df, ["gene", "gene_name", "genes", "locus_tag"])
    loc_col = _find_column(df, ["localization", "subcellular_location", "location"])
    rows = []
    for _, row in df.iterrows():
        loc = _normalize_localization(str(row.get(loc_col, "unknown")) if loc_col else "unknown")
        gene = _norm_gene(row.get(gene_col, row.get(id_col, "unknown")))
        protein_id = str(row.get(id_col, gene)).strip() or gene
        rows.append(
            {
                "protein_id": protein_id,
                "gene": gene,
                "localization": loc,
                "database": "uniprot_or_local_localization",
                "gene_id": protein_id,
                "gene_name": gene,
                "membrane_associated": int(loc in {"cell_wall", "outer_membrane", "inner_membrane", "periplasm"}),
                "secreted": int(loc == "extracellular"),
                "surface_exposed": int(loc in {"extracellular", "cell_wall", "outer_membrane"}),
                **_base_provenance(str(path), "real_external", "database_or_prediction"),
            }
        )
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["localization"])


def _normalize_localization(value: str) -> str:
    text = value.casefold()
    if "secret" in text or "extracellular" in text:
        return "extracellular"
    if "cell wall" in text or "cell_wall" in text:
        return "cell_wall"
    if "outer" in text:
        return "outer_membrane"
    if "peri" in text:
        return "periplasm"
    if "inner" in text or "plasma membrane" in text or "membrane" in text:
        return "inner_membrane"
    if "cyto" in text:
        return "cytoplasm"
    return "unknown"


def build_strain_conservation_table(roary: pd.DataFrame, source: str = "roary_gene_presence_absence") -> pd.DataFrame:
    if roary.empty:
        return empty_layer_table("strain_conservation", notes="No Roary gene_presence_absence.csv file found.")
    gene_col = _find_column(roary, ["Gene", "gene", "gene_name"])
    annotation_col = _find_column(roary, ["Annotation", "annotation", "product"])
    metadata = {"Gene", "Non-unique Gene name", "Annotation", "No. isolates", "No. sequences", "Avg sequences per isolate", "Genome Fragment", "Order within Fragment", "Accessory Fragment", "Accessory Order with Fragment", "QC", "Min group size nuc", "Max group size nuc", "Avg group size nuc"}
    strain_cols = [column for column in roary.columns if column not in metadata]
    total = max(1, len(strain_cols))
    rows = []
    for _, row in roary.iterrows():
        gene = _norm_gene(row.get(gene_col, "unknown")) if gene_col else "unknown"
        present = sum(1 for col in strain_cols if str(row.get(col, "")).strip() not in {"", "nan", "NaN"})
        fraction = present / total
        if fraction >= 0.95:
            status = "core"
        elif fraction >= 0.90:
            status = "soft_core"
        else:
            status = "accessory"
        rows.append(
            {
                "protein_id": gene,
                "gene": gene,
                "core_genome_presence": fraction,
                "strain_coverage_score": fraction,
                "allelic_conservation": fraction,
                "variant_burden": max(0.0, 1.0 - fraction),
                "database": source,
                "gene_id": gene,
                "gene_name": gene,
                "presence_count": present,
                "total_strains": total,
                "conservation_fraction": fraction,
                "core_status": status,
                **_base_provenance(source, "real_external", "pangenome_presence_absence", notes=str(row.get(annotation_col, "")) if annotation_col else ""),
            }
        )
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["strain_conservation"])


def build_virulence_table(vfdb: pd.DataFrame, prokka: pd.DataFrame | None = None) -> pd.DataFrame:
    if not vfdb.empty:
        return vfdb
    prokka = prokka if prokka is not None else pd.DataFrame()
    if prokka.empty:
        return empty_layer_table("virulence", "insufficient_evidence", "No VFDB/VFanalyzer or Prokka annotation evidence available.")
    rows = []
    for _, row in prokka.iterrows():
        gene = _norm_gene(row.get("gene"))
        product = str(row.get("product", ""))
        if _gene_key(gene) in VIRULENCE_GENES or any(token in product.casefold() for token in ["virulence", "toxin", "sortase", "hemolysin", "iron", "heme"]):
            rows.append(
                {
                    "protein_id": row.get("protein_id", gene),
                    "gene": gene,
                    "virulence_score": 0.50,
                    "virulence_factor": 1,
                    "database": "prokka_keyword_inferred_proxy",
                    "gene_id": row.get("protein_id", gene),
                    "gene_name": gene,
                    "product": product,
                    "virulence_factor_name": product or gene,
                    "virulence_category": "annotation_keyword",
                    **_base_provenance(str(row.get("source_file", "prokka")), "inferred_proxy", "annotation_keyword", notes="Proxy: requires VFDB/VFanalyzer or manual curation."),
                }
            )
    if not rows:
        return empty_layer_table("virulence", "insufficient_evidence", "Prokka was present, but no virulence-like annotation was detected.")
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["virulence"])


def build_functional_network_table(string_edges: pd.DataFrame) -> pd.DataFrame:
    if string_edges.empty:
        return empty_layer_table("functional_network", "missing_input", "No STRING or equivalent network file found.")
    genes = sorted(set(string_edges["source_gene"]).union(set(string_edges["target_gene"])))
    degree = {gene: 0 for gene in genes}
    max_score = {gene: 0.0 for gene in genes}
    for _, edge in string_edges.iterrows():
        source = str(edge["source_gene"])
        target = str(edge["target_gene"])
        score = float(edge["interaction_score"])
        degree[source] += 1
        degree[target] += 1
        max_score[source] = max(max_score[source], score)
        max_score[target] = max(max_score[target], score)
    max_degree = max(degree.values()) if degree else 1
    rows = []
    for gene in genes:
        centrality = degree[gene] / max_degree if max_degree else 0.0
        rows.append(
            {
                "protein_id": gene,
                "gene": gene,
                "network_centrality": centrality,
                "pathway_bottleneck_score": max_score[gene],
                "redundancy_penalty": 0.0,
                "functional_dependency_score": (centrality + max_score[gene]) / 2.0,
                "database": "string_local_file",
                "source_gene": gene,
                "target_gene": "",
                "interaction_score": max_score[gene],
                "interaction_type": "string_functional",
                **_base_provenance("STRING local file", "real_external", "functional_interaction"),
            }
        )
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["functional_network"])


def build_localization_table(localization: pd.DataFrame, prokka: pd.DataFrame | None = None) -> pd.DataFrame:
    if not localization.empty:
        return localization
    prokka = prokka if prokka is not None else pd.DataFrame()
    if prokka.empty:
        return empty_layer_table("localization", "missing_input", "No localization or Prokka file found.")
    rows = []
    for _, row in prokka.iterrows():
        product = str(row.get("product", ""))
        loc = _normalize_localization(product)
        if loc == "unknown":
            continue
        gene = _norm_gene(row.get("gene"))
        rows.append(
            {
                "protein_id": row.get("protein_id", gene),
                "gene": gene,
                "localization": loc,
                "database": "prokka_keyword_inferred_proxy",
                "gene_id": row.get("protein_id", gene),
                "gene_name": gene,
                "membrane_associated": int(loc in {"cell_wall", "outer_membrane", "inner_membrane", "periplasm"}),
                "secreted": int(loc == "extracellular"),
                "surface_exposed": int(loc in {"extracellular", "cell_wall", "outer_membrane"}),
                **_base_provenance(str(row.get("source_file", "prokka")), "inferred_proxy", "annotation_keyword", notes="Proxy localization from product text."),
            }
        )
    if not rows:
        return empty_layer_table("localization", "insufficient_evidence", "Prokka was present, but localization could not be inferred safely.")
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["localization"])


def build_evolutionary_escape_risk_table(
    conservation: pd.DataFrame,
    resistance: pd.DataFrame | None = None,
    mobile: pd.DataFrame | None = None,
    hgt: pd.DataFrame | None = None,
    organism: str = "",
    strain: str = "",
) -> pd.DataFrame:
    if conservation.empty:
        return empty_layer_table("evolutionary_escape_risk", "insufficient_evidence", "Requires at least conservation evidence.")
    resistance_df = resistance if resistance is not None else pd.DataFrame()
    mobile_df = mobile if mobile is not None else pd.DataFrame()
    hgt_df = hgt if hgt is not None else pd.DataFrame()
    resistance_genes = {_gene_key(value) for value in resistance_df.get("gene", [])}
    mobile_genes = {_gene_key(value) for value in mobile_df.get("gene", [])}
    hgt_genes = {_gene_key(value) for value in hgt_df.get("gene", [])}
    rows = []
    for _, row in conservation.iterrows():
        gene = _norm_gene(row.get("gene"))
        key = _gene_key(gene)
        conservation_fraction = float(pd.to_numeric(pd.Series([row.get("conservation_fraction", row.get("core_genome_presence", 0.0))]), errors="coerce").fillna(0.0).iloc[0])
        mobile_context = 1.0 if key in mobile_genes else 0.0
        hgt_context = 1.0 if key in hgt_genes else 0.0
        resistance_association = 1.0 if key in resistance_genes else 0.0
        mutation_tolerance = 1.0 - conservation_fraction
        risk = max(0.0, min(1.0, 0.35 * mutation_tolerance + 0.25 * mobile_context + 0.20 * hgt_context + 0.20 * resistance_association))
        constraint = max(0.0, min(1.0, conservation_fraction * (1.0 - max(mobile_context, hgt_context))))
        rows.append(
            {
                "protein_id": row.get("protein_id", gene),
                "gene": gene,
                "candidate_id": row.get("protein_id", gene),
                "organism": organism,
                "strain": strain,
                "mutation_tolerance_score": mutation_tolerance,
                "functional_redundancy_escape_score": 0.0,
                "compensatory_pathway_score": 0.0,
                "fitness_cost_of_escape": conservation_fraction,
                "evolutionary_constraint_score": constraint,
                "resistance_emergence_risk": resistance_association,
                "multi_node_dependency_score": conservation_fraction,
                "evolutionary_escape_risk_score": risk,
                "evidence_source": "conservation_plus_mobile_context",
                "source_type": "computed_from_real_data",
                "confidence": 0.60,
                "notes": "Transparent heuristic; missing mobile/HGT/resistance inputs are not treated as negative evidence.",
                "paralog_count": "",
                "pathway_redundancy": "",
                "mutation_tolerance": mutation_tolerance,
                "conservation_fraction": conservation_fraction,
                "mobile_context": mobile_context,
                "hgt_context": hgt_context,
                "recombination_context": "",
                "resistance_association": resistance_association,
                "retrieval_mode": "local_file",
                "cache_status": "not_cached",
                "source_version": "heuristic_v1",
                "generated_at_utc": utc_now(),
                "provenance_status": "inferred_proxy",
                "database": "computed_evolutionary_escape_risk_v1",
            }
        )
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["evolutionary_escape_risk"])


def build_literature_support_table(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return empty_layer_table("literature_support", "missing_input", "No curated literature table found.")
    df = _read_table(path)
    id_col = _find_column(df, ["protein_id", "gene_id", "locus_tag"])
    gene_col = _find_column(df, ["gene", "gene_name", "symbol"])
    ref_col = _find_column(df, ["reference", "citation", "doi_or_url", "doi", "url"])
    rows = []
    for _, row in df.iterrows():
        gene = _norm_gene(row.get(gene_col, row.get(id_col, "unknown")))
        ref = str(row.get(ref_col, "")).strip() if ref_col else ""
        rows.append(
            {
                "protein_id": str(row.get(id_col, gene)).strip() if id_col else gene,
                "gene": gene,
                "literature_support_score": 0.70 if ref else 0.0,
                "gene_id": str(row.get(id_col, gene)).strip() if id_col else gene,
                "topic": str(row.get("topic", "not_reported")),
                "evidence_summary": str(row.get("evidence_summary", row.get("notes", ""))),
                "reference": ref,
                "doi_or_url": str(row.get("doi_or_url", row.get("doi", ""))),
                "evidence_level": str(row.get("evidence_level", "curated_reference")),
                "provenance_status": "user_supplied",
                "evidence_type": str(row.get("evidence_type", "curated_literature")),
                "notes": str(row.get("notes", "")),
                "source_quality": 0.75 if ref else 0.0,
                "database": "curated_literature_local",
                "generated_at_utc": utc_now(),
            }
        )
    return pd.DataFrame(rows, columns=LAYER_COLUMNS["literature_support"])


def discover_annotation_files(input_dir: Path) -> dict[str, Path | None]:
    return {
        "prokka": _first_existing(input_dir, ["prokka.tsv", "prokka_sample.tsv", "annotations.tsv"]),
        "roary": _first_existing(input_dir, ["gene_presence_absence.csv", "roary_gene_presence_absence_sample.csv"]),
        "vfdb": _first_existing(input_dir, ["vfdb.tsv", "vfdb_sample.tsv", "vfanalyzer.tsv"]),
        "rgi": _first_existing(input_dir, ["rgi.txt", "rgi.tsv", "rgi_sample.txt", "rgi_sample.tsv"]),
        "mobileog": _first_existing(input_dir, ["mobileog.tsv", "mobileog_sample.tsv"]),
        "phastest": _first_existing(input_dir, ["phastest.tsv", "phastest_sample.tsv"]),
        "alienhunter": _first_existing(input_dir, ["alienhunter.txt", "alienhunter_sample.txt", "alienhunter.tsv"]),
        "string": _first_existing(input_dir, ["string.tsv", "string_sample.tsv"]),
        "uniprot_localization": _first_existing(input_dir, ["uniprot_localization.tsv", "uniprot_localization_sample.tsv"]),
        "literature": _first_existing(input_dir, ["literature_support.csv", "literature_support.tsv"]),
    }


def write_layer_csvs(workspace: Path, input_dir: Path, organism: str = "", strain: str = "") -> list[ImportSummary]:
    files = discover_annotation_files(input_dir)
    prokka = parse_prokka_annotations(files["prokka"])
    conservation = build_strain_conservation_table(parse_roary_gene_presence_absence(files["roary"]), str(files["roary"] or "missing_roary"))
    virulence = build_virulence_table(parse_vfdb_results(files["vfdb"]), prokka)
    network = build_functional_network_table(parse_string_network(files["string"]))
    localization = build_localization_table(parse_uniprot_localization(files["uniprot_localization"]), prokka)
    resistance = parse_card_rgi_results(files["rgi"])
    mobile = pd.concat([parse_mobileog_results(files["mobileog"]), parse_phastest_results(files["phastest"])], ignore_index=True)
    hgt = parse_alienhunter_results(files["alienhunter"])
    escape = build_evolutionary_escape_risk_table(conservation, resistance, mobile, hgt, organism, strain)
    literature = build_literature_support_table(files["literature"])

    layer_tables = {
        "virulence": virulence,
        "strain_conservation": conservation,
        "functional_network": network,
        "localization": localization,
        "evolutionary_escape_risk": escape,
        "literature_support": literature,
        "essentiality": empty_layer_table("essentiality", "insufficient_evidence", "No DEG/literature essentiality input found."),
    }

    raw_dir = workspace / "data_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for layer, df in layer_tables.items():
        path = raw_dir / f"{layer}.csv"
        df.to_csv(path, index=False)
        status = str(df.attrs.get("provenance_status", "real_external" if len(df) else "missing_input"))
        warning = [] if len(df) else [str(df.attrs.get("notes", "No input rows materialized."))]
        summaries.append(ImportSummary(layer, path, len(df), status, warning))
    return summaries
