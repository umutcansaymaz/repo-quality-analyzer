# Legacy: repo-analyzer-py

This directory contains the **legacy Python reference implementation** of the
analyzer (FastAPI + tree-sitter based, ~600 files).

## Status: NOT USED

- The active analysis engine is the TypeScript one in `src/lib/local-analysis.ts`.
- It is deterministic, black-box audited (417 synthetic repos, 0 FP / 0 FN),
  runs in the browser (privacy-first) and covers TS / Python / Go / Ruby / Java.
- The Python backend was never wired into the product UI and is kept here for
  reference only. It is **not maintained** and may not run on current
  dependencies.

## Why it was replaced

| | Python (legacy) | TypeScript (active) |
|---|---|---|
| Execution | Server-side (FastAPI) | In-browser, zero upload |
| Audit | None | 417 repos, 0 FP/FN, severity-calibrated |
| Languages | Python-focused | TS / Py / Go / Ruby / Java |
| Multi-finding | Single finding per file | All findings, per-file cap |

## Removal

You can safely delete this directory (`rm -rf repo-analyzer-py`) — it is not
imported by the application. Git history keeps it available.
