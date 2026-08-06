# NODOX integrated validation Stage 3

This patch moves the evidence separation from the read-only ablation tools into
the NODOX evolutionary escape risk core.

It preserves the historical proxy score and default ranking while adding:

- explicit evidence masks for every evolutionary input;
- a supported score gated by a minimum number of explicit variables;
- separate proxy and supported penalties;
- separate proxy and supported adjusted priorities;
- evidence mode and supported-status fields;
- exports in Phase 2 and Phase 3 scored tables;
- regression tests protecting the rule that missing evidence is not low risk.

It does not change Functional Node Theory weights, provider behavior, or
historical result directories.
