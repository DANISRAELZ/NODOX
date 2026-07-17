from pathlib import Path
import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.scoring import build_features_and_scores
from src.nodos_funcionales.reporting import export_results

workspace = Path("results/20260707_online_multiorganism_by_gene_export/organism_runs/helicobacter_pylori/workspace")
config = load_config(workspace / "config" / "params.yaml")

features, scored = build_features_and_scores(workspace, config)

features.to_csv(workspace / "data_processed" / "phase2_features.csv", index=False)
scored.to_csv(workspace / "data_processed" / "scored_nodes.csv", index=False)

export_results(workspace, config, mode="online_only")

df = pd.read_csv(workspace / "results" / "ranking_functional_nodes.csv")

print("\nfunctional_node_theory_label:")
print(df["functional_node_theory_label"].value_counts(dropna=False).to_string())

print("\nmeets_minimum_functional_node_evidence:")
print(df["meets_minimum_functional_node_evidence"].value_counts(dropna=False).to_string())

if "curated_evidence_layers" in df.columns:
    print("\ncurated_evidence_layers:")
    print(df["curated_evidence_layers"].value_counts(dropna=False).head(30).to_string())
else:
    print("\nNO existe curated_evidence_layers en ranking_functional_nodes.csv")

genes = ["ureA","ureB","cagA","vacA","flaA","napA","gyrA","gyrB","rpoB","ftsZ","dnaA"]

cols = [
    "rank",
    "gene",
    "protein_id",
    "functional_node_theory_score",
    "functional_node_theory_confidence",
    "functional_node_theory_label",
    "functional_node_therapeutic_exploitability_score",
    "meets_minimum_functional_node_evidence",
    "curated_evidence_layers",
    "curated_evidence_confidence",
    "audit_flags",
    "missing_evidence_flags",
]

cols = [c for c in cols if c in df.columns]

print("\nCurated genes in final functional ranking:")
print(df[df["gene"].astype(str).isin(genes)][cols].head(120).to_string(index=False))

print("\nOutputs:")
for rel in [
    "results/curated_real_evidence_manifest.json",
    "results/curated_real_evidence_summary.csv",
    "results/ranking_functional_nodes.csv",
    "results/functional_node_theory_audit.csv",
    "results/theory_of_nodes_report.md",
]:
    path = workspace / rel
    print(rel, path.exists(), path.stat().st_size if path.exists() else "MISSING")
