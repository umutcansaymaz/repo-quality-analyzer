#!/usr/bin/env node
/**
 * Audit runner — black-box engine auditor.
 *
 * 1. Generates mini repos with known content (injection log = ground truth)
 * 2. Runs the REAL engine via src/lib/cli.ts (the exact path a user would use)
 * 3. Compares reported root-cause categories against expected ones
 * 4. Reports FALSE POSITIVES (extra) and FALSE NEGATIVES (missing)
 *
 * Usage: node audit/run.mjs [--workdir <dir>]
 */
import { spawnSync } from "child_process";
import { mkdirSync, writeFileSync, existsSync, rmSync } from "fs";
import { join, resolve } from "path";
import { generateRepos, EXPECTED_SEVERITY } from "./generator.mjs";
import { compare } from "./compare.mjs";

const ROOT = resolve(process.cwd());
const WORKDIR = process.argv.includes("--workdir")
  ? resolve(process.argv[process.argv.indexOf("--workdir") + 1])
  : join(ROOT, "audit", ".work");

async function main() {
  const repos = generateRepos();

  // Prepare workdir
  if (existsSync(WORKDIR)) rmSync(WORKDIR, { recursive: true, force: true });
  mkdirSync(WORKDIR, { recursive: true });

  // Write all repos to disk, then a list file for the batch engine call.
  const repoDirs = [];
  for (const repo of repos) {
    const repoDir = join(WORKDIR, repo.name);
    for (const f of repo.files) {
      const full = join(repoDir, f.path);
      mkdirSync(join(full, ".."), { recursive: true });
      writeFileSync(full, f.content, "utf8");
    }
    repoDirs.push(repoDir);
  }
  const listFile = join(WORKDIR, "repos.txt");
  writeFileSync(listFile, repoDirs.join("\n"), "utf8");

  // Run the engine ONCE for all repos (batch mode) — one process, one tsx load.
  const isWin = process.platform === "win32";
  const res = spawnSync(
    isWin ? "npx.cmd" : "npx",
    ["tsx", join(ROOT, "src/lib/cli.ts"), "batch", "--list", listFile],
    { cwd: ROOT, encoding: "utf8", timeout: 600_000, shell: isWin, maxBuffer: 1024 * 1024 * 64 }
  );

  if (res.status !== 0) {
    console.error("ENGINE FAILED:", res.stderr?.slice(0, 1000) || `exit ${res.status}`);
    process.exit(1);
  }

  let batch;
  try {
    batch = JSON.parse(res.stdout);
  } catch {
    console.error("BATCH PARSE FAILED:", res.stdout.slice(0, 500));
    process.exit(1);
  }

  // Map results back to repos by directory name
  const byName = new Map(batch.map((b) => [b.name, b.report]));

  const results = [];
  let totalExtra = 0;
  let totalMissing = 0;
  let totalExpected = 0;
  const knownFnrHits = [];
  const severityMismatches = [];

  for (const repo of repos) {
    const report = byName.get(repo.name);
    if (!report) {
      results.push({ repo: repo.name, error: "no result in batch" });
      continue;
    }

    const actual = (report.evidence || []).map((e) => e.category);
    const cmp = compare(repo.expected, actual);

    // Severity kalibrasyonu: beklenen kategori bulunduysa severity'si doğru mu?
    for (const cat of repo.expected) {
      const want = EXPECTED_SEVERITY[cat];
      if (!want) continue;
      const found = (report.evidence || []).find((e) => e.category === cat);
      if (found && found.severity !== want) {
        severityMismatches.push({ repo: repo.name, category: cat, expected: want, actual: found.severity });
      }
    }

    // Bilinen sınırlar: beklenen ama motorun bilinçli yakalayamadığı desenler
    // (ör. parçalı/base64 secret) — FN sayılmaz, ayrı raporlanır.
    const known = repo.known_fnr || [];
    const knownHit = known.filter((k) => !actual.includes(k));
    if (knownHit.length) knownFnrHits.push({ repo: repo.name, missed: knownHit });
    const fn = cmp.missing.filter((m) => !known.includes(m));

    totalExpected += repo.expected.length;
    totalExtra += cmp.extra.length;
    totalMissing += fn.length;

    results.push({
      repo: repo.name,
      expected: repo.expected,
      actual,
      precision: cmp.precision,
      recall: cmp.recall,
      fp: cmp.extra,
      fn,
    });
  }

  // ---- Report ----
  const cleanRepos = repos.filter((r) => r.expected.length === 0);
  const cleanResults = results.filter((r) => cleanRepos.some((c) => c.name === r.repo));
  const cleanFP = cleanResults.flatMap((r) => (r.fp || []).map((f) => ({ repo: r.repo, fp: f })));

  const withFindings = results.filter((r) => !r.error && (r.expected.length > 0));
  const allPrecision = withFindings.length ? withFindings.reduce((s, r) => s + r.precision, 0) / withFindings.length : 1;
  const allRecall = withFindings.length ? withFindings.reduce((s, r) => s + r.recall, 0) / withFindings.length : 1;

  const lines = [];
  lines.push("=".repeat(60));
  lines.push(`AUDIT SONUCU — ${repos.length} repo`);
  lines.push("=".repeat(60));
  lines.push(`  Toplam beklenen bulgu: ${totalExpected}`);
  lines.push(`  FALSE POSITIVE: ${totalExtra}`);
  lines.push(`  FALSE NEGATIVE: ${totalMissing}`);
  lines.push(`  Ortalama precision (FP yokluğu): %${(allPrecision * 100).toFixed(1)}`);
  lines.push(`  Ortalama recall (kaçırma yokluğu): %${(allRecall * 100).toFixed(1)}`);
  lines.push(`  Temiz repolarda FP: ${cleanFP.length} (hedef: 0)`);
  lines.push("");

  if (totalExtra > 0) {
    lines.push("FALSE POSITIVES (beklenmeyen bulgular):");
    for (const r of results) {
      if (r.fp?.length) {
        lines.push(`  [${r.repo}] expected=${JSON.stringify(r.expected)}`);
        lines.push(`              → FAZLA: ${r.fp.join(", ")}`);
      }
    }
    lines.push("");
  }
  if (totalMissing > 0) {
    lines.push("FALSE NEGATIVES (kaçırılanlar):");
    for (const r of results) {
      if (r.fn?.length) {
        lines.push(`  [${r.repo}] expected=${JSON.stringify(r.expected)}`);
        lines.push(`              → EKSİK: ${r.fn.join(", ")}`);
      }
    }
    lines.push("");
  }
  if (cleanFP.length > 0) {
    lines.push("TEMİZ REPOLARDA BULUNAN (kesin FP):");
    for (const c of cleanFP) lines.push(`  [${c.repo}] → ${c.fp}`);
    lines.push("");
  }
  if (knownFnrHits.length > 0) {
    lines.push("BİLİNEN SINIRLAR (kasıtlı FN — motor bu desenleri yakalayamaz):");
    for (const k of knownFnrHits) {
      lines.push(`  [${k.repo}] → yakalanamayan: ${k.missed.join(", ")}`);
    }
    lines.push("");
  }
  if (severityMismatches.length > 0) {
    lines.push(`SEVERITY UYUMSUZLUKLARI (kategori doğru ama severity yanlış): ${severityMismatches.length}`);
    for (const s of severityMismatches) {
      lines.push(`  [${s.repo}] ${s.category}: beklenen=${s.expected}, motor=${s.actual}`);
    }
    lines.push("");
  } else {
    lines.push(`SEVERITY UYUMSUZLUĞU: 0 (tüm kategoriler doğru severity üretiyor)`);
    lines.push("");
  }

  const errors = results.filter((r) => r.error);
  if (errors.length > 0) {
    lines.push(`HATA (${errors.length} repo çalıştırılamadı):`);
    for (const e of errors) lines.push(`  [${e.repo}] ${e.error}`);
    lines.push("");
  }

  // Per-category summary
  const catStats = {};
  for (const r of results) {
    for (const c of r.fp || []) catStats[c] = catStats[c] || { fp: 0, fn: 0, ok: 0 };
    for (const c of r.fn || []) catStats[c] = catStats[c] || { fp: 0, fn: 0, ok: 0 };
  }
  for (const r of repos) {
    for (const c of r.expected) {
      catStats[c] = catStats[c] || { fp: 0, fn: 0, ok: 0 };
      const has = !results.find((rr) => rr.repo === r.name)?.fn?.includes(c);
      if (has) catStats[c].ok++;
    }
  }
  lines.push("KATEGORİ BAZINDA:");
  for (const [cat, s] of Object.entries(catStats)) {
    lines.push(`  ${cat.padEnd(20)} ok=${s.ok} fp=${s.fp} fn=${s.fn}`);
  }

  const out = lines.join("\n");
  console.log(out);
  writeFileSync(join(ROOT, "audit", "report.txt"), out, "utf8");

  // Cleanup workdir
  if (existsSync(WORKDIR)) rmSync(WORKDIR, { recursive: true, force: true });

  process.exit(totalExtra > 0 || totalMissing > 0 ? 2 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
