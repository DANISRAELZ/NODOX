# NODOX integrated validation Stage 2.1

This repair updates only the read-only evolutionary ablation tooling.

It does not change:

- core scoring modules;
- default Functional Node Theory weights;
- historical result directories;
- provider behavior;
- the selected v10g run.

It adds an evidence gate that separates proxy hypotheses from
evidence-supported evolutionary scoring, plus gene-level aggregation and an
automatic proxy decomposition table.
