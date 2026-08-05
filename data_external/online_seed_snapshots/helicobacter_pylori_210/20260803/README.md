# Frozen UniProt candidate seed

This directory contains the 25-candidate UniProt seed used for the
Helicobacter pylori online-strict validation run dated 2026-08-03.

## Identity

- Organism: Helicobacter pylori
- NCBI taxon: 210
- Candidate count: 25
- Source: UniProt REST
- Snapshot role: reproducible candidate discovery input

## Scientific interpretation

The records identify candidate proteins discovered through UniProt. They do
not demonstrate essentiality, therapeutic efficacy, pharmacological activity
or experimental validation.

A run that reuses this directory must report the seed as a versioned snapshot,
not as a new successful API retrieval.

## Files

- `uniprot_seed_records.json`: original UniProt response.
- `candidate_seed.csv`: candidate layer materialized from the response.
- `candidate_proteins.faa`: protein sequences for the same accessions.
- `candidate_seed_manifest_original.json`: original live-retrieval manifest.
- `snapshot_manifest.json`: portable identity, hashes and limitations.
