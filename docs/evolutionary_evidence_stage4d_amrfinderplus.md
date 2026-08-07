# Stage 4D — AMRFinderPlus mutational resistance evidence

## Purpose

Stage 4D adds a second biologically independent provider-derived evidence source to the strict Stage 4A evolutionary evidence contract.

Stage 4C connected BV-BRC comparative-genomic conservation to the canonical `evolutionary_constraint_score`. Stage 4D connects NCBI AMRFinderPlus curated resistance-associated point mutations to the canonical `resistance_emergence_risk` variable.

The objective is not to turn AMR annotations into a generic resistance score. The objective is narrower: record whether the curated AMRFinderPlus Reference Gene Catalog documents at least one target-site point-mutation route associated with antimicrobial resistance for the exact candidate gene in the relevant organism group.

## Source

Stage 4D uses the public NCBI AMRFinderPlus database:

- `version.txt` for the database release;
- `ReferenceGeneCatalog.txt` as the canonical tab-delimited Reference Gene Catalog source.

NCBI documents `ReferenceGeneCatalog.txt` as the recommended source for accessing the data behind AMRFinderPlus. The catalog includes point mutations, gene family, organism whitelist, scope, type, subtype, phenotype class/subclass, reference accessions, PubMed reference and per-entry database version.

Provider base:

```text
https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/AMRFinderPlus/database/latest
```

## Biological eligibility

Only catalog entries satisfying all of the following are considered:

```text
scope   = core
type    = AMR
subtype = POINT
```

The point mutation must additionally match:

1. the candidate gene exactly against the catalog `gene_family`;
2. the AMRFinderPlus organism/taxonomic group against `whitelisted_taxa`.

Non-POINT AMR genes are not promoted to Stage 4D evolutionary evidence.

## Canonical Stage 4D signal

For a positive candidate-level match:

```text
resistance_emergence_risk = 1.0
```

This is a categorical positive signal, not a calibrated probability.

Its meaning is:

> at least one curated target-site AMR point-mutation route is documented for this gene and organism group.

It does **not** mean:

- the candidate sequence currently carries the mutation;
- resistance will necessarily emerge prospectively;
- the probability of resistance emergence is 100%;
- every possible resistance mechanism is represented in the catalog.

The number of catalog mutations is retained for audit but is not used to scale the score. Mutation counts can reflect publication and curation intensity and are therefore not treated as a quantitative probability of evolutionary escape.

## Positive-only policy

Stage 4D is deliberately asymmetric.

A positive curated match can contribute explicit evidence. Absence of a catalog match never creates:

```text
resistance_emergence_risk = 0
```

Instead, no match produces no explicit AMRFinderPlus evidence for that candidate.

This distinction is critical because organism-specific mutation curation is incomplete for some taxa. NCBI currently lists both *Helicobacter pylori* and *Pseudomonas aeruginosa* as having mutational-resistance curation; NCBI specifically notes that point mutations for *H. pylori* are not fully curated. Therefore a negative lookup must not be interpreted as evidence of low evolutionary risk.

## Provenance contract

Every positive provider row records:

- candidate protein identifier;
- gene;
- AMRFinderPlus release version;
- SHA-256 of the downloaded `ReferenceGeneCatalog.txt`;
- original provider retrieval timestamp;
- source record identifier;
- exact mapping method/status;
- evidence status/confidence;
- organism group and taxon ID;
- mutation symbols;
- mutation count;
- antimicrobial class/subclass;
- PubMed references when available;
- provider URL;
- one fixed AMRFinderPlus independence group.

The Stage 4D adapter requires this original provenance before a numeric value can request explicit status from the Stage 4A contract.

## Independence

All Stage 4D AMRFinderPlus point-mutation evidence uses:

```text
ncbi_amrfinderplus_curated_point_mutations
```

as its biological independence group.

Multiple mutations, multiple drug classes or repeated catalog records do not create additional independent groups.

BV-BRC and AMRFinderPlus are treated as independent evidence groups because they represent different underlying biological observations:

```text
BV-BRC
  comparative genomic conservation / allelic conservation
  -> evolutionary_constraint_score

AMRFinderPlus
  literature-curated resistance-associated point mutations
  -> resistance_emergence_risk
```

Cache reuse does not create a new biological source or independence group.

## Stage 4A/4B gate behavior

The default contract remains unchanged:

```text
minimum_explicit_variables = 3
minimum_independent_evidence_groups = 2
```

Therefore:

```text
BV-BRC alone
  1 variable / 1 group
  -> unsupported

AMRFinderPlus alone
  1 variable / 1 group
  -> unsupported

BV-BRC + AMRFinderPlus
  2 variables / 2 groups
  -> still unsupported because only 2 variables are explicit
```

A third genuinely supported evolutionary variable is still required before `evolutionary_escape_supported_score` becomes evaluable.

Stage 4D does not lower the gate merely because a second source has been added.

## Caching and reproducibility

The provider stores candidate-level positive results in a query-specific cache derived from:

- taxon;
- organism;
- candidate gene set.

A cached row preserves the original:

- AMRFinderPlus release;
- catalog SHA-256;
- retrieval timestamp;
- mutation records;
- evidence mapping;
- independence group.

Serving the same evidence from cache changes the delivery path, not the biological source.

## Fail-closed conditions

AMRFinderPlus evidence is not promoted when any required condition fails, including:

- missing candidate gene;
- missing organism/taxon context;
- provider disabled;
- network/provider failure without usable cache;
- invalid catalog schema;
- non-POINT entries;
- wrong organism whitelist;
- no candidate gene match;
- missing release, hash or original retrieval metadata;
- taxon mismatch;
- non-direct mapping;
- non-observed evidence status;
- missing mutation symbol/count;
- demo/proxy/mixed-demo provenance;
- inconsistent external/cache provenance flags.

## What Stage 4D does not change

Stage 4D does not change:

- Functional Node Theory weights;
- therapeutic strategy weights;
- the historical proxy evolutionary calculation;
- Stage 4A minimum evidence thresholds;
- Stage 4B supported-score formula;
- experimental-validation claims.

The patch adds evidence and provenance. It does not recalibrate NODOX.

## Next evidence requirement

After Stage 4D, a candidate can have two real independent evolutionary variables:

1. BV-BRC `evolutionary_constraint_score`;
2. AMRFinderPlus `resistance_emergence_risk`.

The next scientifically meaningful step is therefore not to add another correlated AMR database simply to satisfy the threshold. Stage 4E should seek a third evolutionary dimension with a defensible biological interpretation, such as experimentally or literature-supported fitness cost, mutation tolerance, or compensatory-pathway evidence, while preserving source independence.
