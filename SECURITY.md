# Security Policy

## Supported version

NODOX is currently an early scientific software release. Security fixes are applied to the latest version on the default branch and to the most recent tagged release when practical.

## Reporting a vulnerability

Do not publish credentials, private datasets, personal information, or exploitable vulnerabilities in a public issue.

Until a dedicated private security-reporting address is published, report security concerns through GitHub's private vulnerability reporting feature when it is enabled for this repository. Include:

- the affected file, component, or version;
- steps to reproduce the problem;
- the potential impact;
- any suggested mitigation;
- whether credentials or personal data may have been exposed.

## Secrets and local data

NODOX must not require committed credentials. API keys, tokens, passwords, private certificates, local `.env` files, user-curated private datasets, generated workspaces, caches, logs, and result directories must remain outside version control.

If a secret is committed, removing it from the latest file is not sufficient. Revoke or rotate the secret immediately and remove it from Git history before making the repository public.

## Scientific and clinical scope

NODOX produces exploratory computational prioritizations. A software defect, incomplete external dataset, provider outage, or configuration error can change rankings. Outputs do not establish therapeutic efficacy, safety, clinical validity, or medical recommendations and require independent review and experimental validation.
