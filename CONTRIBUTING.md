# Contributing

Thanks for your interest! This project is small on purpose — please read the
following before opening a PR.

## How to contribute

1. Fork the repository.
2. Create a branch: `git checkout -b feat/your-change`.
3. Make your change.
4. Run the checks:
   ```bash
   npm run lint
   npm run test
   npm run audit
   npm run build
   ```
5. Open a pull request with a clear description of the change and the
   verification you ran.

## Engine changes: the audit rule

The analysis engine (`src/lib/local-analysis.ts`) is the core of the product.
Any change to a detector **must** keep the audit green:

```
npm run audit
# must stay at: FALSE POSITIVE: 0 | FALSE NEGATIVE: 0 | SEVERITY MISMATCH: 0
```

If your change introduces a false positive or false negative that cannot be
reasonably avoided (e.g. a fundamentally undetectable pattern), add it to the
**known limitations** section in `audit/generator.mjs` (`known_fnr`) instead
of weakening a test — the audit reports it transparently.

New detectors should be added to the audit generator with:
- clean / single / double / neighbour / multi / noise variants
- boundary threshold variants (just below and above the limit)
- benign look-alike traps (comments, strings, generated files)

See `audit/generator.mjs` and `tests/audit.test.ts` for the conventions.

## Code style

- TypeScript, strict mode.
- No comments unless they explain *why* (not *what*).
- Keep the engine deterministic — no randomness, no network calls in
  `local-analysis.ts` except the optional LLM call.
- Tests live in `tests/`; real-repo golden tests in `tests/golden-real.test.ts`
  (skipped automatically when the reference repos are not present).
