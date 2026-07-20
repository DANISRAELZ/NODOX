# Third-party data terms and redistribution review

Last reviewed: 2026-07-20

This document records an engineering review of the public terms associated with external data providers used or anticipated by NODOX. It is not legal advice. Provider terms can change, and users remain responsible for confirming that their intended use is permitted.

## Release policy

NODOX source code is distributed under Apache License 2.0. External biological database content is not automatically covered by the NODOX software license.

The public repository must therefore follow these rules:

1. Do not commit downloaded provider databases, private workspaces, API responses, or user-curated research datasets unless redistribution rights have been confirmed.
2. Prefer runtime retrieval, user-supplied files, reproducible local calculations, or small synthetic fixtures.
3. Preserve provider names, retrieval dates, versions, citations, and provenance in manifests and reports.
4. Keep network caches and downloaded reference databases outside version control.
5. Treat a provider's availability through an API as distinct from permission to redistribute its data.
6. Require users to review provider terms for commercial, clinical, regulated, or large-scale use.

## Provider review

| Provider | Public terms identified | NODOX release treatment |
|---|---|---|
| UniProt | Copyrightable database content is offered under Creative Commons Attribution 4.0 International (CC BY 4.0). UniProt requests attribution and notes that patents or other rights may still apply to some content. | Runtime access and attributed derived tables are permitted under the stated license. Preserve source, version, retrieval date, and citation. Do not imply that UniProt validates NODOX conclusions. |
| STRING | STRING states that its data and download files are available under CC BY 4.0. It requests appropriate credit and disclosure of changes. The API is intended for limited or occasional access; bulk retrieval should use official downloads. | Permit runtime/API access with attribution, conservative request rates, caching, and provenance. Avoid screen scraping. Large-scale users should use official downloads and comply with current access guidance. |
| InterPro | InterPro states that downloadable InterPro, Pfam, PRINTS, and SFLD data provided through its site are available under CC0 1.0. InterProScan is Apache-licensed, while included tools and member signature collections can have different terms. | InterPro API or downloadable data can be used with provenance and citation. Do not assume every member-database tool or signature collection has the same license; review those separately before redistribution. |
| NCBI | NCBI places no restrictions on use or distribution of its molecular data, but warns that submitters or source jurisdictions may assert patent, copyright, or other rights. NCBI requests acknowledgment and publishes scripting limits and identification requirements. | Permit runtime use and attributed molecular-data identifiers. Respect current E-utilities limits, identify the tool where required, and do not redistribute third-party copyrighted literature or restricted linked resources. |
| VFDB | VFDB states that its data are available under CC BY-NC 4.0 for non-commercial research or academic use. Commercial users must contact VFDB. | Do not bundle VFDB data in the Apache-2.0 source release. Support runtime retrieval or user-supplied files only. Mark VFDB-derived evidence and retain attribution. Commercial users must obtain separate permission. |
| BV-BRC | BV-BRC states that its public data are freely available without restriction on use. Private workspace data remain under the user's control and responsibility. | Permit runtime access to public records with provenance and citation. Never access, commit, or redistribute a user's private BV-BRC workspace data without explicit authorization and verified rights. |
| DEG | DEG publications and the DEG 15 data-availability statement describe the database as freely accessible and downloadable. A clear standalone database license was not located during this review. | Apply the conservative rule: do not redistribute DEG database snapshots in the NODOX repository. Use runtime retrieval or user-supplied files, cite DEG, retain provenance, and re-check terms before commercial redistribution. |

## Repository-specific assessment

The publication branch uses small synthetic or controlled fixtures for testing. Files labeled as synthetic fixtures must not be represented as full provider databases or biological validation datasets.

Provider-derived caches, complete proteomes, downloaded database snapshots, local DIAMOND databases, private workspaces, and unrestricted user-curated data must remain ignored by Git.

The following are allowed in the public repository when clearly labeled:

- schemas and empty templates;
- small synthetic test fixtures;
- controlled demonstration records with explicit non-biological status;
- identifiers, citations, and retrieval manifests;
- code that calls public APIs while respecting provider limits;
- instructions for users to download external resources themselves.

## Required attribution behavior

NODOX reports should preserve, when available:

- provider name;
- database or release version;
- retrieval date;
- accession or stable identifier;
- retrieval mode, including live API, cache, local calculation, or user-curated input;
- transformations or derived calculations applied by NODOX;
- relevant provider citation.

## Unresolved or conditional items

- DEG redistribution remains conservative because a clear database-content license was not located.
- InterPro member databases and tools may carry terms different from the integrated InterPro downloadable data.
- VFDB data are non-commercial and must not be silently relicensed under Apache-2.0.
- NCBI records can include third-party rights or linked copyrighted material despite NCBI's general molecular-data policy.
- Provider terms must be rechecked immediately before each public release.

## Official sources reviewed

- UniProt: `https://www.uniprot.org/help/license`
- STRING licensing and access: `https://string-db.org/cgi/access?footer_active_subpage=licensing`
- InterPro license: `https://www.ebi.ac.uk/interpro/about/license/`
- NCBI policies and molecular-data usage: `https://www.ncbi.nlm.nih.gov/home/about/policies/`
- VFDB terms: `https://www.mgc.ac.cn/VFs/main.htm`
- BV-BRC data management and sharing: `https://www.bv-brc.org/docs/system_documentation/data_management_sharing.html`
- DEG 15 data availability: `https://pmc.ncbi.nlm.nih.gov/articles/PMC7779065/`
