import { analyzeLocalFiles, buildLocalReport, shouldSkip, parseGitignore } from "../src/lib/local-analysis";
import { readFileSync, readdirSync, statSync } from "fs";
import { join, relative } from "path";

async function main() {
  let gi: Set<string> | undefined;
  try { gi = parseGitignore(readFileSync(join(process.cwd(), ".gitignore"), "utf8")); } catch {}

  const files: File[] = [];
  const visit = (d: string) => {
    let e: string[];
    try { e = readdirSync(d); } catch { return; }
    for (const n of e) {
      const f = join(d, n);
      try {
        const s = statSync(f);
        const rel = relative(process.cwd(), f).replace(/\\/g, "/");
        if (s.isDirectory()) {
          if (["node_modules", ".next", ".git"].includes(n)) continue;
          if (shouldSkip(rel + "/x", gi)) continue;
          visit(f);
        } else if (s.isFile() && s.size < 1000000) {
          if (shouldSkip(rel, gi)) continue;
          try { files.push(new File([readFileSync(f, "utf8")], rel)); } catch {}
        }
      } catch {}
    }
  };
  visit(".");

  console.log("toplam dosya (gitignore ile):", files.length);
  const scan = await analyzeLocalFiles(files);
  const report = buildLocalReport(scan, "kalite", { useLLM: false });
  const h = report.ai_review.health_score;
  console.log("overall:", h.overall, "| grade:", h.grade);
  console.log("güvenlik:", h.security, "| mimari:", h.architecture, "| kalite:", h.code_quality, "| test:", h.testing, "| doküman:", h.documentation);
  console.log("performans:", h.performance, "| DX:", h.developer_experience, "| ölçek:", h.scalability);
  console.log("secret:", scan.evidence.filter((e) => e.category === "hardcoded_secret").length, "| circular:", scan.evidence.filter((e) => e.category === "circular_dependency").length);
  const sec = scan.rawEvidence.filter((e) => e.category === "hardcoded_secret");
  sec.forEach((e) => console.log("  secret:", e.file_path));
}
main().catch((e) => { console.error(e); process.exit(1); });
