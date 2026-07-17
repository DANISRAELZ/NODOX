# Online-only 7K vs 7K.1 connectivity comparison

Phase 7K produced an auditable technical-failure package: all three requested organisms had `candidate_seed_count=0`, and ranking was not allowed.

Phase 7K.1 diagnosed the connectivity failure. DNS resolution succeeded for UniProt, EBI and NCBI hosts, but every HTTPS probe failed in a subprocess with:

`OPENSSL_Uplink(...): no OPENSSL_Applink`

The probable cause is `openssl_applink_error`, consistent with local Windows/Python/OpenSSL runtime incompatibility rather than provider-side biological absence.

Because UniProt `candidate_seed` did not pass contract for taxon `287`, `562` or `1773`, the 7K.1 multiorganism rerun was not executed.

| organism | taxon_id | 7K candidate_seed_count | 7K ranking_allowed | 7K.1 seed diagnostic | persistent limitation |
|---|---:|---:|---|---|---|
| Pseudomonas aeruginosa | 287 | 0 | false | openssl_applink_error | openssl_applink_error |
| Escherichia coli | 562 | 0 | false | openssl_applink_error | openssl_applink_error |
| Mycobacterium tuberculosis | 1773 | 0 | false | openssl_applink_error | openssl_applink_error |

No provider degradation is interpreted as positive evidence or strong negative evidence. `candidate_seed` remains the only strict blocking layer.
