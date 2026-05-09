# Corynebacterium pseudotuberculosis biovar ovis Controlled Snapshot

This snapshot represents the project priority organism `Corynebacterium pseudotuberculosis` in a controlled biovar ovis context.

Scope:

- biovar: `ovis`;
- strain scope: generic controlled example;
- taxonomy source: project taxon resolution cache;
- network policy: no network;
- evidence status: controlled reference snapshot.

The snapshot exists to validate reproducible source contracts for a real priority organism before any fresh STRING or UniProt validation. The functional annotations are small controlled examples, not online evidence and not scoring inputs.

Files:

- `snapshot_metadata.json`: snapshot identity, acquisition mode and evidence policy;
- `taxonomy.json`: cached/local taxonomy provenance;
- `sources_manifest.json`: source-by-source evidence separation;
- `functional_annotations.json`: representative controlled nodes;
- `provenance.json`: no-network provenance and future refresh protocol;
- `README.md`: human-readable scope.

Future updates may add STRING or UniProt evidence only after a controlled online validation run with documented retrieval status, cache policy, confidence and limitations.
