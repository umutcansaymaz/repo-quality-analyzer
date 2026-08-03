# repo-quality-analyzer

A privacy-first, local repository quality analyzer. Clone a repository (or
scan a local folder) and get a health score across 14 static-analysis
dimensions — all in your browser, with bring-your-own-key LLM explanations.

## Why

- **Privacy-first**: file contents are analyzed **in the browser** — your code
  never leaves your machine. The server only persists the compact report.
- **Proven engine**: every detector is black-box audited against 417 synthetic
  repos with known ground truth — **0 false positives, 0 false negatives**
  (see [Audit](#audit)).
- **Bring your own key**: if you want AI explanations, add your own
  OpenAI/Anthropic key in the UI. It is stored in your browser's localStorage
  and is **never sent to the server**.
- **Multi-language**: TypeScript, Python, Go, Ruby, Java — same thresholds,
  same rules.

## Features

| Dimension | What it detects |
|---|---|
| Security | hardcoded secrets (API keys, AWS, GitHub tokens, Firebase), command injection, weak crypto (MD5/SHA-1/DES) |
| Architecture | god classes, tight coupling, circular dependencies (2-level) |
| Quality | long functions, deep nesting, high complexity, empty exception handlers, magic numbers |
| Metrics | large files, TODO debt |
| Testing | missing test files |
| Docs | documentation presence |
| Reports | health score (A–F), root causes, evidence with line numbers, knowledge graph, roadmap, explanations (LLM or deterministic) |

## Getting started

### 1. Run it

```bash
npm install
cp .env.example .env      # optional — only DATABASE_URL for the SQLite store
npm run dev               # http://localhost:3000
```

### 2. Analyze

- **Local folder**: drag & drop or pick a folder — analyzed in your browser.
- **GitHub repo**: paste a URL — cloned shallowly on the server and scanned
  with the same engine.

### 3. (Optional) AI explanations

Open the settings in the UI, pick a provider (OpenAI, Anthropic, Azure
OpenAI, Ollama, Gemini, OpenRouter) and paste your key. After an analysis,
click **"Generate LLM explanations"** on the LLM status card — the call goes
straight from your browser to the provider; the key is **never sent to the
server**.

## Architecture

```
browser (page.tsx)
 ├─ analyzeLocalFiles()  → scans files, builds evidence  [local-analysis.ts]
 ├─ buildLocalReport()   → score + root causes + graph   [local-analysis.ts]
 └─ POST /api/analyze-local (report only, no file content)
server
 ├─ /api/analyze         → clone repo (URL) + same engine + SSRF validation
 ├─ /api/result/:id      → retrieve persisted report
 └─ db/analysis-results/ → persisted JSON reports (SQLite via Prisma optional)
```

The engine (`src/lib/local-analysis.ts`) is a deterministic, regex +
structured-scanner hybrid: every finding carries `file`, `line`, an evidence
snippet, a confidence and a second-pass validation status
(`verified`/`partial`/`unverified`).

## Known limitations

The engine is deliberately transparent about what it cannot detect — these
are tracked as **known limitations** in the audit and reported in
`npm run audit`:

- **Concatenated secrets**: `"sk-" + "abc..."` (regex finds single tokens)
- **Base64-encoded secrets**
- **Dynamic crypto algorithms**: `createHash(process.env.ALGO)`
- No taint/flow analysis: `const cmd = "ls"; exec(cmd)` is reported even
  though `cmd` is static
- 3+ level import cycles (A→B→C→A) are not detected — only 2-level
- No duplication / dead-code / CVE database analysis

## Audit

The engine ships with a black-box auditor: it generates hundreds of mini
repos with known ground truth, runs the **real** engine against them, and
reports false positives / false negatives / severity calibration.

```bash
npm run audit
```

Current result:

```
AUDIT — 417 repos | 539 expected findings
  FALSE POSITIVE: 0 | FALSE NEGATIVE: 0 | Precision 100% | Recall 100%
  SEVERITY MISMATCH: 0 (all 14 categories produce the expected severity)
  KNOWN LIMITATIONS: 11 (intentional FNs, tracked separately)
```

Categories covered: hardcoded_secret, command_injection, weak_crypto,
empty_handler, long_function, deep_nesting, high_complexity, large_file,
god_class, tight_coupling, circular_dependency, magic_number, todo_debt,
missing_tests — across TS / Python / Go / Ruby / Java, including boundary
thresholds (just below/above every limit) and benign look-alike traps.

## Development

```bash
npm run test        # 141 unit + integration + golden tests
npm run lint
npm run audit       # engine black-box audit (above)
npm run build
```

## License

MIT — see [LICENSE](LICENSE).
