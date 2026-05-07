# PAO1 Demo Controlled Snapshot

This directory contains a small, offline curated snapshot for `Pseudomonas aeruginosa` PAO1.

Purpose:

- validate the curated snapshot file contract;
- keep provenance auditable without fresh network calls;
- distinguish controlled fixtures, cached external references, fallback contracts and real external evidence.

This snapshot does not include raw STRING or UniProt payloads. It references the documented PAO1 online validation closure and stores only small representative fixture records needed for offline tests.

Do not replace these files with generated outputs from `data_sessions/`.
