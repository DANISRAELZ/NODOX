# Taxonomy API Integration

## Provider

The current optional online provider is NCBI E-utilities for the `taxonomy`
database. This was chosen because it is public, documented and does not require
private credentials for basic use.

Relevant official documentation:

- NCBI APIs: https://www.ncbi.nlm.nih.gov/home/develop/api/
- E-utilities help: https://www.ncbi.nlm.nih.gov/books/NBK25501/

## Implementation notes

The integration lives in `src/nodos_funcionales/taxonomy_api.py`.

Current request flow:

1. `esearch.fcgi` searches `db=taxonomy` by organism name
2. `esummary.fcgi` retrieves metadata for the returned taxonomy ids
3. the client chooses the best match conservatively

The code handles:

- network errors
- timeouts
- HTTP errors
- empty result sets
- multiple matches
- invalid JSON responses

## Honest fallback behavior

If the provider fails or does not return a usable match, the discovery layer:

- records that the API was attempted
- records whether it succeeded
- stores a fallback reason
- keeps the local canonicalization when possible
- does not abort the whole pipeline

## Non-goals in this version

This version does not:

- require API keys
- query multiple providers
- do aggressive synonym expansion online
- claim strain-level certainty when the provider only resolves species-level taxa
