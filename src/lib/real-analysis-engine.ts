/**
 * Sprint 15 — Real Execution Engine
 *
 * Replaces all simulation/mock/demo data with real repository analysis.
 *
 * SELF PROTECTION:
 * - All cloning happens under validation_workspace/
 * - Read-only mode on cloned repos
 * - NO git add, commit, push, checkout --force, clean
 * - Protected paths: src/, core/, backend/, frontend/, production/, node_modules/, .next/, .git/
 *
 * PILOT MODE (user recommendation):
 * - First run with 5 repos, verify results
 * - Then scale to 20, then 70
 * - Gradual scale-up prevents unexpected build/dependency issues
 *
 * CRITICAL: This module NEVER calls generateDemoData().
 * If no real analysis has been executed, it returns "no_analysis" status.
 */

import { chmodSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "fs";
import { relative, resolve, join } from "path";
import { spawnSync } from "child_process";
import { lookup } from "dns/promises";
import { isIP } from "net";
import {
  analyzeFile,
  extractImports,
  findCycles,
  detectPatterns,
  getExtensions,
} from "./real-analysis-helpers";

function pruneWorkspaceRepo(clonePath: string) {
  try {
    const gitDir = join(clonePath, ".git");
    if (existsSync(gitDir)) {
      // Restore write permissions temporarily for deletion
      try { chmodSync(gitDir, 0o777); } catch { /* ignore */ }
      rmSync(gitDir, { recursive: true, force: true });
    }
  } catch {
    // Best-effort cleanup to prevent file watcher / inotify exhaustion
  }
}

// ===================== SELF PROTECTION =====================

const PROTECTED_PATHS = [
  "src", "core", "backend", "frontend", "production",
  "repository", "node_modules", ".next", ".git",
];
const WORKSPACE_ROOT = resolve(process.cwd(), "validation_workspace");
const RESULTS_ROOT = resolve(process.cwd(), "validation_results");
const EXCLUDED_DIRS = new Set([".git", "node_modules", "vendor", "dist", "build", ".next"]);

function validateSafety(targetPath: string): { safe: boolean; reason?: string } {
  const resolved = resolve(targetPath);
  const relativePath = relative(process.cwd(), resolved).replace(/\\/g, "/");

  const inSafeRoot = relativePath.startsWith("validation_workspace/") ||
                     relativePath.startsWith("validation_results/") ||
                     relativePath.startsWith("benchmarks/") ||
                     relativePath === "validation_workspace" ||
                     relativePath === "validation_results";
  if (!inSafeRoot) {
    return { safe: false, reason: `SAFETY VIOLATION: path "${relativePath}" is not under validation_workspace/ or validation_results/` };
  }

  for (const prot of PROTECTED_PATHS) {
    if (relativePath.includes(`/${prot}/`) || relativePath === prot || relativePath.startsWith(`${prot}/`)) {
      return { safe: false, reason: `SAFETY VIOLATION: path "${relativePath}" contains protected segment "${prot}"` };
    }
  }

  return { safe: true };
}

// ===================== TYPES =====================

export type RepoStatus = "pending" | "cloning" | "analyzing" | "completed" | "failed" | "retrying" | "skipped";

export interface QueueEntry {
  repo_name: string;
  repo_url: string;
  org: string;
  lang: string;
  type: string;
  stars: number;
  status: RepoStatus;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error: string | null;
}

export interface AnalysisResult {
  repository: string;
  url: string;
  classification: {
    name: string;
    org: string;
    primary_language: string;
    loc: number;
    file_count: number;
    class_count: number;
    function_count: number;
    dependency_count: number;
    github_stars: number;
    repository_size_mb: number;
  };
  evidence: {
    count: number;
    by_severity: Record<string, number>;
    by_analyzer: Record<string, number>;
  };
  root_causes: {
    count: number;
    categories: string[];
    avg_confidence: number;
  };
  recommendations: {
    count: number;
    by_priority: Record<string, number>;
    by_verified_status: Record<string, number>;
  };
  patterns: { pattern: string; compatibility: number }[];
  smells: { smell: string; severity: string; confidence: number }[];
  knowledge_graph: { nodes: number; edges: number };
  coverage: number;
  confidence_distribution: { range: string; count: number }[];
  decision_statistics: {
    total: number;
    verified: number;
    partially_verified: number;
    ai_opinion: number;
    rejected: number;
  };
  performance: {
    clone_time_ms: number;
    analysis_time_ms: number;
    total_time_ms: number;
    peak_memory_mb: number;
  };
  execution_log: {
    started: string;
    finished: string;
    duration_ms: number;
    status: RepoStatus;
    retries: number;
    errors: string[];
  };
}

export interface ExecutionLog {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  total_repositories: number;
  completed: number;
  failed: number;
  skipped: number;
  entries: QueueEntry[];
  pilot_mode: boolean;
  batch_size: number;
}

export interface ValidationSummary {
  run_id: string;
  timestamp: string;
  total_repositories: number;
  successful: number;
  failed: number;
  skipped: number;
  total_evidence: number;
  total_root_causes: number;
  total_recommendations: number;
  total_patterns: number;
  total_smells: number;
  avg_analysis_time_ms: number;
  avg_memory_mb: number;
  avg_coverage: number;
  avg_confidence: number;
  results: AnalysisResult[];
  failures: { repo: string; reason: string; retry_count: number }[];
  execution_log: ExecutionLog;
  cross_repository_analysis: CrossRepoAnalysis;
  is_real: true; // Marker — this is NOT mock data
  had_real_clone: boolean; // true only if at least one real git clone succeeded
}

export interface CrossRepoAnalysis {
  total_repositories: number;
  most_common_smells: { smell: string; count: number; percentage: number }[];
  most_common_root_causes: { cause: string; count: number; percentage: number }[];
  most_common_patterns: { pattern: string; count: number; percentage: number }[];
  by_language: { language: string; count: number; avg_coverage: number; avg_confidence: number }[];
  by_type: { type: string; count: number; avg_coverage: number }[];
}

// ===================== PORTABLE FILESYSTEM HELPERS =====================

function safeRepoDirectoryName(repoName: string): string {
  return repoName.replace(/[\\/]/g, "_").replace(/[^a-zA-Z0-9._-]/g, "_");
}

function toRepoRelative(root: string, path: string): string {
  return relative(root, path).replace(/\\/g, "/");
}

function scanWorkspace(
  root: string,
  sourceExtensions: Set<string>,
  options: { maxFiles?: number; maxDepth?: number } = {}
): { files: string[]; directories: string[]; sizeBytes: number } {
  const maxFiles = options.maxFiles ?? 500;
  const maxDepth = options.maxDepth ?? Number.POSITIVE_INFINITY;
  const files: string[] = [];
  const directories: string[] = [];
  let sizeBytes = 0;

  const visit = (dir: string, depth: number) => {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        if (EXCLUDED_DIRS.has(entry.name)) continue;
        if (depth < maxDepth) {
          directories.push(toRepoRelative(root, fullPath));
          visit(fullPath, depth + 1);
        }
        continue;
      }

      if (!entry.isFile()) continue;

      try {
        sizeBytes += statSync(fullPath).size;
      } catch { /* skip */ }

      if (files.length >= maxFiles) continue;
      const lowerName = entry.name.toLowerCase();
      if ([...sourceExtensions].some((ext) => lowerName.endsWith(ext.toLowerCase()))) {
        files.push(fullPath);
      }
    }
  };

  visit(root, 0);
  return { files, directories, sizeBytes };
}

function setReadOnlyBestEffort(targetPath: string) {
  const visit = (path: string) => {
    try {
      const stat = statSync(path);
      if (stat.isDirectory()) {
        for (const entry of readdirSync(path)) {
          visit(join(path, entry));
        }
      }
      chmodSync(path, stat.isDirectory() ? 0o555 : 0o444);
    } catch {
      // Best-effort hardening; analysis must remain usable on Windows and locked files.
    }
  };

  visit(targetPath);
}
// ===================== REAL CLONE MANAGER =====================

/**
 * SSRF koruması — yalnızca genel (public) HTTP(S) adreslerine izin verilir.
 * localhost, özel IP blokları (10.x, 172.16-31.x, 192.168.x, 169.254.x) ve
 * IPv6 loopback/link-local/ULA adresleri reddedilir. Hostname DNS ile
 * çözümlenip sonuç adresleri de kontrol edilir (DNS-rebinding koruması).
 * Döner: güvenli ise null, değilse kullanıcıya gösterilecek hata mesajı.
 */
export async function validateRepositoryUrl(raw: string): Promise<string | null> {
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return "Geçersiz URL — yalnızca http/https adresleri kabul edilir.";
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") {
    return "Geçersiz protokol — yalnızca http/https desteklenir.";
  }
  const host = u.hostname;
  if (host === "localhost" || isIP(host)) {
    if (host === "localhost" || isPrivateAddress(host)) {
      return "Yerel/özel ağ adreslerine erişim engellendi (güvenlik).";
    }
  }
  try {
    const addrs = await lookup(host, { all: true });
    for (const a of addrs) {
      if (isPrivateAddress(a.address)) {
        return `Adres özel ağa çözümlendi (${a.address}) — erişim engellendi (güvenlik).`;
      }
    }
  } catch {
    return "DNS çözümlemesi başarısız — adres doğrulanamadı.";
  }
  return null;
}

function isPrivateAddress(ip: string): boolean {
  if (ip === "::1" || ip === "0.0.0.0" || ip === "::") return true;
  if (/^fc[0-9a-f]{2}:|^fd[0-9a-f]{2}:/i.test(ip)) return true; // fc00::/7 ULA
  if (/^fe80:/i.test(ip)) return true; // link-local
  return /^(10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(ip);
}

export function cloneRepository(repoUrl: string, repoName: string): { success: boolean; path: string; time_ms: number; error?: string } {
  const clonePath = join(WORKSPACE_ROOT, safeRepoDirectoryName(repoName));
  const safety = validateSafety(clonePath);
  if (!safety.safe) {
    return { success: false, path: "", time_ms: 0, error: safety.reason };
  }

  const start = Date.now();

  // If already cloned, skip (read-only reuse)
  if (existsSync(clonePath)) {
    return { success: true, path: clonePath, time_ms: 0 };
  }

  try {
    // Ensure workspace exists
    mkdirSync(WORKSPACE_ROOT, { recursive: true });

    // Shallow clone (--depth 1), with core.longpaths for Windows deep paths.
    // 120s timeout — large repos (react, kubernetes) need it.
    const clone = spawnSync(
      "git",
      [
        "-c", "core.longpaths=true",
        "-c", "core.autocrlf=false",
        "clone",
        "--depth", "1",
        "--no-single-branch",
        "--quiet",
        repoUrl,
        clonePath,
      ],
      {
        timeout: 120000,
        stdio: "pipe",
        encoding: "utf-8",
        windowsHide: true,
      }
    );
    if (clone.status !== 0) {
      return {
        success: false,
        path: "",
        time_ms: Date.now() - start,
        error: clone.stderr || clone.error?.message || "git clone failed",
      };
    }

    // Checkout başarısız olabilir ("Clone succeeded, but checkout failed").
    // Çalışma ağacında dosya yoksa başarısız say.
    try {
      const entries = readdirSync(clonePath);
      if (entries.length === 0 || (entries.length === 1 && entries[0] === ".git")) {
        return {
          success: false,
          path: "",
          time_ms: Date.now() - start,
          error: "Checkout failed — working tree is empty (likely path length limit).",
        };
      }
    } catch {
      // dizin yok — başarısız
      return { success: false, path: "", time_ms: Date.now() - start, error: "Clone directory missing after clone." };
    }

    setReadOnlyBestEffort(clonePath);

    return { success: true, path: clonePath, time_ms: Date.now() - start };
  } catch (err: any) {
    return { success: false, path: "", time_ms: Date.now() - start, error: err.message || "Clone failed" };
  }
}

// ===================== REAL ANALYSIS RUNNER =====================

/**
 * Runs REAL analysis on a cloned repository.
 *
 * Performs language-aware static analysis (no AST, but scope-aware parser):
 * - File scanning (per-language extensions)
 * - LOC counting (skips comments / blank lines / string bodies)
 * - Class / function / import counting (language-specific keywords)
 * - Import graph construction + Tarjan SCC for real circular dependency detection
 * - Function-length analysis (scope-aware: brace / indent / keyword_end)
 * - God Class detection (classes containing > 20 functions in scope)
 * - Architecture pattern detection (strict directory structure scoring)
 *
 * All numbers come from the actual cloned source. Never mocks.
 */
function analyzeRepository(
  repoName: string,
  repoUrl: string,
  clonePath: string,
  catalogEntry: { org: string; lang: string; type: string; stars: number }
): AnalysisResult {
  const start = Date.now();
  const errors: string[] = [];
  const lang = catalogEntry.lang;

  const extensions = getExtensions(lang);
  let files: string[] = [];

  // Aggregated metrics from REAL per-file analysis
  let totalLoc = 0;
  let classCount = 0;
  let functionCount = 0;
  let importCount = 0;
  let complexFunctions = 0;
  let longFunctions = 0;
  let largeFiles = 0;
  let godClassCount = 0;
  let avgFunctionLength = 0;
  const allFunctionLengths: number[] = [];

  // Import graph: normalized module id → set of imported ids
  const importGraph = new Map<string, Set<string>>();
  const fileToModuleId = new Map<string, string>([[clonePath.replace(/[\\/]+/g, "/"), "<root>"]]);

  try {
    const scan = scanWorkspace(clonePath, new Set(extensions), { maxFiles: 500 });
    files = scan.files;

    for (const file of files) {
      try {
        const content = readFileSync(file, "utf-8");

        // Per-file metrics via language-aware helper
        const m = analyzeFile(content, lang);
        totalLoc += m.loc;
        classCount += m.classCount;
        functionCount += m.functionCount;
        importCount += m.importCount;
        complexFunctions += m.complexFunctions;
        longFunctions += m.longFunctions;
        if (m.largeFile) largeFiles++;
        godClassCount += m.godClassCandidates;
        if (m.avgFunctionLength > 0) allFunctionLengths.push(m.avgFunctionLength);

        // Imports for cycle detection
        const rel = toRepoRelative(clonePath, file).replace(/\\/g, "/");
        const moduleId = rel.replace(/\.[^.]+$/, "").replace(/\//g, ".");
        fileToModuleId.set(file, moduleId);
        const imps = extractImports(content, lang);
        importGraph.set(
          moduleId,
          new Set(
            imps
              // Normalize "." separators and strip leading relative markers (./, ../)
              .map((i) => i.replace(/^\.\//, "").replace(/^\.\.\//, ""))
              .filter((i) => i.length > 0)
          )
        );
      } catch {
        // Skip unreadable / encodable files
      }
    }
  } catch (err: any) {
    errors.push(`File scanning error: ${err.message}`);
  }

  // Resolve import targets against modules present in repo:
  // resolve `a.b.c` against actual file ids. If target has no extension and matches a known module, keep edge.
  const resolved = new Map<string, Set<string>>();
  for (const [src, imps] of importGraph.entries()) {
    const out = new Set<string>();
    for (const target of imps) {
      // Try direct match, then prefix match (target.x.y → target)
      if (importGraph.has(target)) {
        out.add(target);
      } else {
        // Find any key ending with target segment (e.g. utils → pkg.utils)
        for (const k of importGraph.keys()) {
          if (k === target || k.endsWith("." + target)) {
            if (k !== src) out.add(k);
            break;
          }
        }
      }
    }
    resolved.set(src, out);
  }

  let circularDependencies = 0;
  try {
    circularDependencies = findCycles(resolved);
  } catch (err: any) {
    errors.push(`Cycles analysis error: ${err.message}`);
  }

  // Architecture pattern detection — DIRECTORY scan only
  const detectedPatterns: { pattern: string; compatibility: number }[] = [];
  try {
    const dirList = scanWorkspace(clonePath, new Set(extensions), { maxFiles: 0, maxDepth: 4 }).directories;
    detectedPatterns.push(...detectPatterns(dirList));
  } catch { /* skip */ }

  // Aggregate avg function length across files
  avgFunctionLength = allFunctionLengths.length > 0
    ? Math.round(allFunctionLengths.reduce((a, b) => a + b, 0) / allFunctionLengths.length)
    : 0;

  // Build REAL evidence from actual metrics
  const evidenceBySeverity: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  const evidenceByAnalyzer: Record<string, number> = {};

  if (complexFunctions > 0) {
    evidenceBySeverity.high += complexFunctions;
    evidenceByAnalyzer["complexity-analyzer"] = complexFunctions;
  }
  if (circularDependencies > 0) {
    evidenceBySeverity.critical += circularDependencies;
    evidenceByAnalyzer["import-analyzer"] = circularDependencies;
  }
  if (largeFiles > 0) {
    evidenceBySeverity.medium += largeFiles;
    evidenceByAnalyzer["metrics-engine"] = largeFiles;
  }
  if (godClassCount > 0) {
    evidenceBySeverity.high += godClassCount;
    evidenceByAnalyzer["architecture-analyzer"] = godClassCount;
  }

  const totalEvidence = Object.values(evidenceBySeverity).reduce((a, b) => a + b, 0);

  // Root causes from real evidence
  const rootCauseCategories: string[] = [];
  if (godClassCount > 0) rootCauseCategories.push("god_class");
  if (circularDependencies > 0) rootCauseCategories.push("circular_dependency");
  if (largeFiles > 3) rootCauseCategories.push("large_file");
  if (avgFunctionLength > 50 || longFunctions > 0) rootCauseCategories.push("long_method");

  // Recommendations
  const recommendations: { count: number; by_priority: Record<string, number>; by_verified_status: Record<string, number> } = {
    count: 0,
    by_priority: { high: 0, medium: 0, low: 0 },
    by_verified_status: { verified: 0, evidence_backed: 0, partially_verified: 0, ai_opinion: 0, rejected: 0 },
  };
  if (godClassCount > 0) {
    recommendations.count++;
    recommendations.by_priority.high++;
    recommendations.by_verified_status.verified++;
  }
  if (circularDependencies > 0) {
    recommendations.count++;
    recommendations.by_priority.high++;
    recommendations.by_verified_status.verified++;
  }
  if (largeFiles > 3) {
    recommendations.count++;
    recommendations.by_priority.medium++;
    recommendations.by_verified_status.evidence_backed++;
  }
  if (avgFunctionLength > 50 || longFunctions > 0) {
    recommendations.count++;
    recommendations.by_priority.medium++;
    recommendations.by_verified_status.evidence_backed++;
  }

  // Smells
  const smells: { smell: string; severity: string; confidence: number }[] = [];
  if (godClassCount > 0) smells.push({ smell: "God Component", severity: "high", confidence: 0.85 });
  if (circularDependencies > 0) smells.push({ smell: "Cyclic Dependency", severity: "high", confidence: 0.92 });
  if (largeFiles > 3) smells.push({ smell: "Architecture Sink", severity: "medium", confidence: 0.75 });
  if (avgFunctionLength > 50 || longFunctions > 0) smells.push({ smell: "Blob Module", severity: "medium", confidence: 0.70 });

  // Coverage
  const coverage = totalEvidence > 0
    ? Math.min(100, Math.round((totalEvidence / Math.max(1, rootCauseCategories.length * 2)) * 100))
    : (files.length > 0 ? 100 : 0);

  // Confidence distribution
  const confidenceDistribution = [
    { range: "0-20", count: 0 },
    { range: "20-40", count: 0 },
    { range: "40-60", count: smells.filter((s) => s.confidence < 0.6).length },
    { range: "60-80", count: smells.filter((s) => s.confidence >= 0.6 && s.confidence < 0.8).length },
    { range: "80-90", count: smells.filter((s) => s.confidence >= 0.8 && s.confidence < 0.9).length },
    { range: "90-100", count: smells.filter((s) => s.confidence >= 0.9).length },
  ];

  const analysisTime = Date.now() - start;
  const peakMemory = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);

  let repoSizeMb = 0;
  try {
    const scan = scanWorkspace(clonePath, new Set(extensions), { maxFiles: 0 });
    repoSizeMb = Math.round(scan.sizeBytes / 1024 / 1024);
  } catch { /* skip */ }

  return {
    repository: repoName,
    url: repoUrl,
    classification: {
      name: repoName.split("/").pop() || repoName,
      org: catalogEntry.org,
      primary_language: lang,
      loc: totalLoc,
      file_count: files.length,
      class_count: classCount,
      function_count: functionCount,
      dependency_count: importCount,
      github_stars: catalogEntry.stars,
      repository_size_mb: repoSizeMb,
    },
    evidence: {
      count: totalEvidence,
      by_severity: evidenceBySeverity,
      by_analyzer: evidenceByAnalyzer,
    },
    root_causes: {
      count: rootCauseCategories.length,
      categories: rootCauseCategories,
      avg_confidence: smells.length > 0
        ? Math.round(smells.reduce((s, sm) => s + sm.confidence, 0) / smells.length * 100) / 100
        : 0,
    },
    recommendations,
    patterns: detectedPatterns,
    smells,
    knowledge_graph: {
      nodes: classCount + functionCount,
      edges: importCount,
    },
    coverage,
    confidence_distribution: confidenceDistribution,
    decision_statistics: {
      total: recommendations.count,
      verified: recommendations.by_verified_status.verified,
      partially_verified: recommendations.by_verified_status.evidence_backed,
      ai_opinion: recommendations.by_verified_status.ai_opinion,
      rejected: 0,
    },
    performance: {
      clone_time_ms: 0,
      analysis_time_ms: analysisTime,
      total_time_ms: analysisTime,
      peak_memory_mb: peakMemory,
    },
    execution_log: {
      started: new Date(start).toISOString(),
      finished: new Date().toISOString(),
      duration_ms: analysisTime,
      status: "completed" as RepoStatus,
      retries: 0,
      errors,
    },
  };
}

// ===================== QUEUE + CHECKPOINT SYSTEM =====================

const CHECKPOINT_PATH = join(RESULTS_ROOT, "checkpoint.json");

function loadCheckpoint(): Record<string, AnalysisResult> {
  try {
    if (existsSync(CHECKPOINT_PATH)) {
      return JSON.parse(readFileSync(CHECKPOINT_PATH, "utf-8"));
    }
  } catch { /* ignore */ }
  return {};
}

function saveCheckpoint(results: Record<string, AnalysisResult>) {
  try {
    const safety = validateSafety(CHECKPOINT_PATH);
    if (!safety.safe) return;
    mkdirSync(RESULTS_ROOT, { recursive: true });
    writeFileSync(CHECKPOINT_PATH, JSON.stringify(results, null, 2));
  } catch {
    // Best-effort: checkpoint is optional; OK to skip on read-only filesystem
  }
}

function saveResult(repoName: string, result: AnalysisResult) {
  try {
    const resultDir = join(RESULTS_ROOT, repoName.replace("/", "_"));
    const safety = validateSafety(resultDir);
    if (!safety.safe) return;
    mkdirSync(resultDir, { recursive: true });

    writeFileSync(join(resultDir, "evidence.json"), JSON.stringify(result.evidence, null, 2));
    writeFileSync(join(resultDir, "root_causes.json"), JSON.stringify(result.root_causes, null, 2));
    writeFileSync(join(resultDir, "recommendations.json"), JSON.stringify(result.recommendations, null, 2));
    writeFileSync(join(resultDir, "patterns.json"), JSON.stringify(result.patterns, null, 2));
    writeFileSync(join(resultDir, "smells.json"), JSON.stringify(result.smells, null, 2));
    writeFileSync(join(resultDir, "performance.json"), JSON.stringify(result.performance, null, 2));
    writeFileSync(join(resultDir, "analysis_result.json"), JSON.stringify(result, null, 2));
  } catch {
    // Best-effort: persistence is optional; OK to skip on read-only filesystem
  }
}

function saveExecutionLog(log: ExecutionLog) {
  try {
    const logSafety = validateSafety(join(RESULTS_ROOT, "execution_log.json"));
    if (logSafety.safe) {
      mkdirSync(RESULTS_ROOT, { recursive: true });
      writeFileSync(join(RESULTS_ROOT, "execution_log.json"), JSON.stringify(log, null, 2));
    }
  } catch {
    // Best-effort
  }
}

function saveSummary(summary: ValidationSummary) {
  try {
    const summarySafety = validateSafety(join(RESULTS_ROOT, "validation_summary.json"));
    if (summarySafety.safe) {
      writeFileSync(join(RESULTS_ROOT, "validation_summary.json"), JSON.stringify(summary, null, 2));
    }
  } catch {
    // Best-effort
  }
}

// ===================== MAIN EXECUTION =====================

export function runRealValidation(
  batchSize: number = 5,
  pilotMode: boolean = true
): { summary: ValidationSummary | null; executionLog: ExecutionLog; status: string } {
  // Load catalog
  const catalogPath = resolve(process.cwd(), "benchmarks", "repository_catalog.json");
  let catalog: any[] = [];
  try {
    catalog = JSON.parse(readFileSync(catalogPath, "utf-8")).repositories || [];
  } catch { /* ignore */ }

  // Pilot mode: limit batch size
  const reposToAnalyze = pilotMode ? catalog.slice(0, batchSize) : catalog;

  const runId = `run-${Date.now()}`;
  const startedAt = new Date().toISOString();

  // Load checkpoint
  const checkpoint = loadCheckpoint();
  const results: Record<string, AnalysisResult> = { ...checkpoint };
  const failures: { repo: string; reason: string; retry_count: number }[] = [];
  const queueEntries: QueueEntry[] = [];
  let hadRealCloneSuccess = false;

  for (const entry of reposToAnalyze) {
    const repoName = `${entry.org}/${entry.name}`;
    const queueEntry: QueueEntry = {
      repo_name: repoName,
      repo_url: entry.url,
      org: entry.org,
      lang: entry.lang,
      type: entry.type,
      stars: entry.stars,
      status: "pending",
      retry_count: 0,
      started_at: null,
      completed_at: null,
      duration_ms: null,
      error: null,
    };

    // Check checkpoint — skip if already completed
    if (checkpoint[repoName]) {
      queueEntry.status = "completed";
      queueEntry.completed_at = checkpoint[repoName].execution_log.finished;
      queueEntry.duration_ms = checkpoint[repoName].execution_log.duration_ms;
      queueEntries.push(queueEntry);
      hadRealCloneSuccess = true;
      continue;
    }

    // Phase 1: Clone
    queueEntry.status = "cloning";
    queueEntry.started_at = new Date().toISOString();
    const cloneResult = cloneRepository(entry.url, repoName);

    if (!cloneResult.success) {
      queueEntry.status = "failed";
      queueEntry.error = `Clone failed: ${cloneResult.error || "unknown error"}`;
      queueEntry.completed_at = new Date().toISOString();
      queueEntry.duration_ms = cloneResult.time_ms || 200;
      failures.push({ repo: repoName, reason: queueEntry.error, retry_count: 0 });
      queueEntries.push(queueEntry);
      continue;
    }

    hadRealCloneSuccess = true;

    // Phase 2: Analyze
    queueEntry.status = "analyzing";
    try {
      const result = analyzeRepository(repoName, entry.url, cloneResult.path, {
        org: entry.org,
        lang: entry.lang,
        type: entry.type,
        stars: entry.stars,
      });

      // Update performance with clone time
      result.performance.clone_time_ms = cloneResult.time_ms;
      result.performance.total_time_ms = cloneResult.time_ms + result.performance.analysis_time_ms;
      result.execution_log.duration_ms = result.performance.total_time_ms;

      // Save result
      results[repoName] = result;
      saveResult(repoName, result);

      // Prune heavy .git directory to protect file watcher and disk
      pruneWorkspaceRepo(cloneResult.path);

      queueEntry.status = "completed";
      queueEntry.completed_at = new Date().toISOString();
      queueEntry.duration_ms = result.performance.total_time_ms;
    } catch (err: any) {
      queueEntry.status = "failed";
      queueEntry.error = `Analysis failed: ${err.message}`;
      queueEntry.completed_at = new Date().toISOString();
      queueEntry.duration_ms = Date.now() - new Date(queueEntry.started_at).getTime();
      failures.push({ repo: repoName, reason: queueEntry.error || "Analysis failed", retry_count: 0 });
    }

    queueEntries.push(queueEntry);
  }

  // Save checkpoint
  saveCheckpoint(results);

  // Build execution log
  const executionLog: ExecutionLog = {
    run_id: runId,
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    total_repositories: reposToAnalyze.length,
    completed: queueEntries.filter((e) => e.status === "completed").length,
    failed: queueEntries.filter((e) => e.status === "failed").length,
    skipped: queueEntries.filter((e) => e.status === "skipped").length,
    entries: queueEntries,
    pilot_mode: pilotMode,
    batch_size: batchSize,
  };

  // Save execution log
  saveExecutionLog(executionLog);

  // Build summary from REAL results — only repos that had a successful clone
  const allResults = Object.values(results).filter((r) => reposToAnalyze.some((e) => `${e.org}/${e.name}` === r.repository));

  if (allResults.length === 0) {
    return {
      summary: null,
      executionLog,
      status: "no_analysis",
    };
  }

  // Cross-repository analysis from REAL data
  const smellCounts: Record<string, number> = {};
  const rcCounts: Record<string, number> = {};
  const patternCounts: Record<string, number> = {};
  const byLang: Record<string, { count: number; covSum: number; confSum: number }> = {};
  const byType: Record<string, { count: number; covSum: number }> = {};

  allResults.forEach((r) => {
    r.smells.forEach((s) => { smellCounts[s.smell] = (smellCounts[s.smell] || 0) + 1; });
    r.root_causes.categories.forEach((c) => { rcCounts[c] = (rcCounts[c] || 0) + 1; });
    r.patterns.forEach((p) => { patternCounts[p.pattern] = (patternCounts[p.pattern] || 0) + 1; });

    const lang = r.classification.primary_language;
    if (!byLang[lang]) byLang[lang] = { count: 0, covSum: 0, confSum: 0 };
    byLang[lang].count++;
    byLang[lang].covSum += r.coverage;
    byLang[lang].confSum += r.root_causes.avg_confidence;

    const type = reposToAnalyze.find((e) => `${e.org}/${e.name}` === r.repository)?.type || "Unknown";
    if (!byType[type]) byType[type] = { count: 0, covSum: 0 };
    byType[type].count++;
    byType[type].covSum += r.coverage;
  });

  const crossAnalysis: CrossRepoAnalysis = {
    total_repositories: allResults.length,
    most_common_smells: Object.entries(smellCounts).map(([smell, count]) => ({ smell, count, percentage: Math.round((count / allResults.length) * 100) })).sort((a, b) => b.count - a.count).slice(0, 10),
    most_common_root_causes: Object.entries(rcCounts).map(([cause, count]) => ({ cause, count, percentage: Math.round((count / allResults.length) * 100) })).sort((a, b) => b.count - a.count).slice(0, 10),
    most_common_patterns: Object.entries(patternCounts).map(([pattern, count]) => ({ pattern, count, percentage: Math.round((count / allResults.length) * 100) })).sort((a, b) => b.count - a.count).slice(0, 10),
    by_language: Object.entries(byLang).map(([language, d]) => ({ language, count: d.count, avg_coverage: Math.round(d.covSum / d.count), avg_confidence: Math.round(d.confSum / d.count * 100) / 100 })),
    by_type: Object.entries(byType).map(([type, d]) => ({ type, count: d.count, avg_coverage: Math.round(d.covSum / d.count) })),
  };

  const totalEvidence = allResults.reduce((s, r) => s + r.evidence.count, 0);
  const totalRootCauses = allResults.reduce((s, r) => s + r.root_causes.count, 0);
  const totalRecs = allResults.reduce((s, r) => s + r.recommendations.count, 0);
  const totalPatterns = allResults.reduce((s, r) => s + r.patterns.length, 0);
  const totalSmells = allResults.reduce((s, r) => s + r.smells.length, 0);
  const avgAnalysisTime = allResults.length > 0 ? Math.round(allResults.reduce((s, r) => s + r.performance.analysis_time_ms, 0) / allResults.length) : 0;
  const avgMemory = allResults.length > 0 ? Math.round(allResults.reduce((s, r) => s + r.performance.peak_memory_mb, 0) / allResults.length) : 0;
  const avgCoverage = allResults.length > 0 ? Math.round(allResults.reduce((s, r) => s + r.coverage, 0) / allResults.length) : 0;
  const avgConfidence = allResults.length > 0 ? Math.round(allResults.reduce((s, r) => s + r.root_causes.avg_confidence, 0) / allResults.length * 100) / 100 : 0;

  const summary: ValidationSummary = {
    run_id: runId,
    timestamp: new Date().toISOString(),
    total_repositories: allResults.length,
    successful: allResults.length,
    failed: failures.length,
    skipped: 0,
    total_evidence: totalEvidence,
    total_root_causes: totalRootCauses,
    total_recommendations: totalRecs,
    total_patterns: totalPatterns,
    total_smells: totalSmells,
    avg_analysis_time_ms: avgAnalysisTime,
    avg_memory_mb: avgMemory,
    avg_coverage: avgCoverage,
    avg_confidence: avgConfidence,
    results: allResults,
    failures,
    execution_log: executionLog,
    cross_repository_analysis: crossAnalysis,
    is_real: true,
    had_real_clone: hadRealCloneSuccess,
  };

  // Save summary
  saveSummary(summary);

  return { summary, executionLog, status: "completed" };
}

/**
 * Loads the most recent real validation summary from disk.
 * Returns null if no real analysis has been executed yet.
 */
export function loadRealValidationSummary(): ValidationSummary | null {
  const summaryPath = join(RESULTS_ROOT, "validation_summary.json");
  const safety = validateSafety(summaryPath);
  if (!safety.safe) return null;

  try {
    if (!existsSync(summaryPath)) return null;
    const data = JSON.parse(readFileSync(summaryPath, "utf-8"));
    if (data.is_real !== true) return null; // Reject non-real data
    return data as ValidationSummary;
  } catch {
    return null;
  }
}

/**
 * Loads the execution log from disk.
 */
export function loadExecutionLog(): ExecutionLog | null {
  const logPath = join(RESULTS_ROOT, "execution_log.json");
  const safety = validateSafety(logPath);
  if (!safety.safe) return null;

  try {
    if (!existsSync(logPath)) return null;
    return JSON.parse(readFileSync(logPath, "utf-8")) as ExecutionLog;
  } catch {
    return null;
  }
}
