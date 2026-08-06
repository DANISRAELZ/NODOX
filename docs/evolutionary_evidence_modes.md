# Evolutionary evidence modes

Stage 3 separates the historical proxy calculation from evidence-supported
evolutionary scoring without changing the default NODOX ranking.

## Output modes

- `supported`: at least the configured minimum number of evolutionary
  variables are explicit.
- `insufficient_explicit_evidence_proxy_only`: one or more variables are
  explicit, but the minimum threshold is not reached.
- `proxy_hypothesis_only`: values are derived from related layers or defaults.
- `unknown_missing_evidence`: neither explicit nor usable proxy inputs are
  available.
- `disabled`: the sublayer is disabled.

## Backward compatibility

`evolutionary_escape_risk_score`,
`evolutionary_escape_penalty_applied`, and
`evolutionary_adjusted_meta_priority_score` keep the historical proxy
semantics. Their explicit aliases are:

- `evolutionary_escape_proxy_score`
- `evolutionary_escape_proxy_penalty_applied`
- `evolutionary_proxy_adjusted_meta_priority_score`

The evidence-supported outputs are:

- `evolutionary_escape_supported_score`
- `evolutionary_escape_supported_penalty_applied`
- `evolutionary_supported_adjusted_meta_priority_score`
- `evolutionary_escape_supported_status`
- `evolutionary_escape_supported_interpretation`

When the explicit-evidence threshold is not reached, the supported score
remains missing, the supported penalty is zero, and the supported adjusted
priority remains equal to the base priority. This means that missing evidence
does not become evidence of low evolutionary risk.

## Scientific interpretation

Proxy outputs are exploratory hypotheses. Supported outputs indicate that the
minimum evidence gate was passed, but they still do not constitute experimental
or predictive validation of resistance evolution.
