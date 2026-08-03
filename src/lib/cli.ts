/**
 * CLI entry point — exposes the analysis engine to external tools (audit/).
 *
 * This is the ONLY bridge between the product and black-box auditors:
 * it runs the real engine (analyzeLocalFiles + buildLocalReport) on a
 * directory and prints the report as JSON to stdout.
 *
 * Usage:
 *   node cli.ts analyze <dir> [--repo <name>]
 *
 * The report matches exactly what the web app produces, so auditors test
 * the same behavior a user sees.
 */
import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative } from "path";
import { analyzeLocalFiles, buildLocalReport, shouldSkip, parseGitignore } from "./local-analysis";

function collectFiles(base: string): File[] {
  let gi: Set<string> | undefined;
  try { gi = parseGitignore(readFileSync(join(base, ".gitignore"), "utf8")); } catch {}
  const files: File[] = [];
  const visit = (d: string) => {
    let e: string[];
    try { e = readdirSync(d); } catch { return; }
    for (const n of e) {
      const f = join(d, n);
      try {
        const s = statSync(f);
        const rel = relative(base, f).replace(/\\/g, "/");
        if (s.isDirectory()) {
          if (["node_modules", ".git", ".next", "dist", "build", "coverage"].includes(n)) continue;
          if (shouldSkip(rel + "/x", gi)) continue;
          visit(f);
        } else if (s.isFile() && s.size < 2_000_000) {
          if (shouldSkip(rel, gi)) continue;
          try { files.push(new File([readFileSync(f, "utf8")], rel)); } catch {}
        }
      } catch {}
    }
  };
  visit(base);
  return files;
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];
  if (cmd !== "analyze" || !args[1]) {
    console.error('Usage: node cli.ts analyze <dir> [--repo <name>]');
    process.exit(1);
  }
  const dir = args[1];
  const repoName = args.indexOf("--repo") !== -1 ? args[args.indexOf("--repo") + 1] : relative(process.cwd(), dir) || dir;

  const files = collectFiles(dir);
  const scan = await analyzeLocalFiles(files);
  const report = buildLocalReport(scan, repoName, { useLLM: false });

  // Compact: auditors only need root causes, evidence categories and validation.
  process.stdout.write(JSON.stringify({
    id: report.id,
    repository: report.repository,
    scan: report.repository_metadata?.scan_summary || {},
    root_causes: report.root_causes?.root_causes || [],
    evidence: report.evidence?.evidence || [],
    validation_stats: report.evidence?.statistics || {},
    health_score: report.ai_review?.health_score || {},
  }));
}

main().catch((e) => { console.error(e?.message || e); process.exit(1); });
