# Online HTTPS connectivity diagnostic 7K.1

- Python executable: `/mnt/c/Users/danis/OneDrive/Escritorio/nodos/.venv-wsl/bin/python`
- Python version: `3.12.3 (main, Mar 23 2026, 19:04:32) [GCC 13.3.0]`
- Platform: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39`
- OpenSSL: `OpenSSL 3.0.13 30 Jan 2024`
- certifi path: `/mnt/c/Users/danis/OneDrive/Escritorio/nodos/.venv-wsl/lib/python3.12/site-packages/certifi/cacert.pem`
- Probable cause: `partial_success`

This diagnostic does not touch scoring, ranking, GUI, user-curated evidence or biological interpretation.

| probe | endpoint | final_status | cause_classification | payload_type | records |
|---|---|---|---|---|---|
| dns | eutils.ncbi.nlm.nih.gov | success | success | dns | 2 |
| dns | rest.uniprot.org | success | success | dns | 1 |
| dns | www.ebi.ac.uk | success | success | dns | 1 |
| urllib_certifi | uniprot_taxon_287_minimal | success | success | json | 790 |
| urllib_default | uniprot_taxon_287_minimal | success | success | json | 790 |
| request_provider_payload | uniprot_taxon_287_minimal | success | success | json | 1 |
| urllib_certifi | interpro_minimal | success | success | json | 1035 |
| urllib_default | interpro_minimal | success | success | json | 1035 |
| request_provider_payload | interpro_minimal | success | success | json | 1 |
| urllib_certifi | europe_pmc_minimal | success | success | json | 987 |
| urllib_default | europe_pmc_minimal | success | success | json | 987 |
| request_provider_payload | europe_pmc_minimal | success | success | json | 0 |
| urllib_certifi | ncbi_taxonomy_minimal | success | success | json | 316 |
| urllib_default | ncbi_taxonomy_minimal | success | success | json | 316 |
| request_provider_payload | ncbi_taxonomy_minimal | success | success | json | 0 |
| candidate_seed_contract | candidate_seed_taxon_287 | success | success | json | 1 |
| candidate_seed_contract | candidate_seed_taxon_562 | success | success | json | 1 |
| candidate_seed_contract | candidate_seed_taxon_1773 | success | success | json | 1 |