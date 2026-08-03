# Security Policy

## Reporting a vulnerability

If you find a security issue, **do not open a public issue**. Please report it
privately by opening a GitHub Security Advisory at:

https://github.com/USERNAME/repo-quality-analyzer/security/advisories/new

or contact the maintainers directly.

Please include:

- a description of the issue
- the affected version / commit
- steps to reproduce (minimal example preferred)
- any suggested fix, if you have one

You will receive a response within 7 days. We ask that you do not disclose
the issue publicly until a fix has been released.

## Security model

- **File contents are analyzed in the browser** — repository code never
  reaches the server for local-folder scans.
- **API keys are never sent to the server** — they live in the browser's
  localStorage and are used client-side only.
- **SSRF protection**: `/api/analyze` accepts only public http/https URLs;
  localhost, private IP ranges and DNS-rebinding targets are rejected
  (`validateRepositoryUrl`).
- **Scoped cloning**: clones happen under `validation_workspace/` with
  read-only reuse; no git write operations are performed.
- The audit suite (`npm run audit`) tracks false positives and false
  negatives as a regression guard for the analysis engine.
