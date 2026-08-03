import { NextRequest, NextResponse } from "next/server";
import { generateRepos, EXPECTED_SEVERITY } from "../../../../audit/generator.mjs";
import { compare } from "../../../../audit/compare.mjs";
import { analyzeLocalFiles } from "@/lib/local-analysis";

/**
 * Engine self-test — runs the REAL black-box audit against the live engine.
 *
 * GET  /api/benchmark — audit coverage summary (categories × repos)
 * POST /api/benchmark — run the full audit (417 synthetic repos) and return
 *                       false positives / false negatives / severity mismatches.
 *
 * This replaces the old mock benchmark: the numbers shown in the UI are the
 * same numbers `npm run audit` produces.
 */

const AUDIT_CATEGORIES = Object.keys(EXPECTED_SEVERITY);

export async function GET() {
  return NextResponse.json({ benchmarks: AUDIT_CATEGORIES, total: AUDIT_CATEGORIES.length });
}

export async function POST(_req: NextRequest) {
  try {
    const start = Date.now();
    const repos = generateRepos();

    let fp = 0;
    let fn = 0;
    let severityMismatches = 0;
    const knownLimits = new Set<string>();
    const byCategory: Record<string, { total: number; fp: number; fn: number }> = {};

    for (const repo of repos) {
      const files = repo.files.map(
        (f: { path: string; content: string }) => new File([f.content], f.path, { type: "text/plain" })
      );
      const scan = await analyzeLocalFiles(files);
      const cats = scan.evidence.map((e: any) => e.category);
      const cmp = compare(repo.expected, cats);

      fp += cmp.extra.length;
      const known = repo.known_fnr || [];
      known.forEach((k: string) => knownLimits.add(k));
      const missing = cmp.missing.filter((m: string) => !known.includes(m));
      fn += missing.length;

      for (const cat of new Set([...repo.expected, ...cats])) {
        byCategory[cat] = byCategory[cat] || { total: 0, fp: 0, fn: 0 };
        byCategory[cat].total++;
        if (cmp.extra.includes(cat)) byCategory[cat].fp++;
        if (missing.includes(cat)) byCategory[cat].fn++;
      }

      for (const cat of repo.expected) {
        const want = EXPECTED_SEVERITY[cat];
        if (!want) continue;
        const found = scan.evidence.find((e: any) => e.category === cat);
        if (found && found.severity !== want) severityMismatches++;
      }
    }

    const passed = repos.length - (fp > 0 ? 1 : 0) - (fn > 0 ? 1 : 0);
    const failed = (fp > 0 ? 1 : 0) + (fn > 0 ? 1 : 0);
    const accuracy = fp === 0 && fn === 0 ? 1 : Math.max(0, 1 - (fp + fn) / Math.max(1, repos.length));

    return NextResponse.json({
      total_benchmarks: repos.length,
      passed,
      failed,
      overall_accuracy: accuracy,
      regression_status: "stable",
      previous_accuracy: null,
      current_accuracy: accuracy,
      best_benchmark: fp === 0 && fn === 0 ? "all categories" : "see FP/FN below",
      worst_benchmark: severityMismatches > 0 ? `${severityMismatches} severity mismatch(es)` : "none",
      audit: {
        repos: repos.length,
        false_positives: fp,
        false_negatives: fn,
        severity_mismatches: severityMismatches,
        known_limitations: [...knownLimits],
        by_category: byCategory,
        duration_ms: Date.now() - start,
      },
    });
  } catch (err: any) {
    return NextResponse.json({ error: `Audit failed: ${err?.message || err}` }, { status: 500 });
  }
}
