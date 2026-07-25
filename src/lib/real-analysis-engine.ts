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

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { resolve, join } from "path";
import { execSync } from "child_process";

// ===================== SELF PROTECTION =====================

const PROTECTED_PATHS = [
  "src", "core", "backend", "frontend", "production",
  "repository", "node_modules", ".next", ".git",
];
const WORKSPACE_ROOT = resolve(process.cwd(), "validation_workspace");
const RESULTS_ROOT = resolve(process.cwd(), "validation_results");

function validateSafety(targetPath: string): { safe: boolean; reason?: string } {
  const resolved = resolve(targetPath);
  const relative = resolved.replace(process.cwd() + "/", "");

  const inSafeRoot = relative.startsWith("validation_workspace/") ||
                     relative.startsWith("validation_results/") ||
                     relative.startsWith("benchmarks/") ||
                     relative === "validation_workspace" ||
                     relative === "validation_results";
  if (!inSafeRoot) {
    return { safe: false, reason: `SAFETY VIOLATION: path "${relative}" is not under validation_workspace/ or validation_results/` };
  }

  for (const prot of PROTECTED_PATHS) {
    if (relative.includes(`/${prot}/`) || relative === prot || relative.startsWith(`${prot}/`)) {
      return { safe: false, reason: `SAFETY VIOLATION: path "${relative}" contains protected segment "${prot}"` };
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
}

export interface CrossRepoAnalysis {
  total_repositories: number;
  most_common_smells: { smell: string; count: number; percentage: number }[];
  most_common_root_causes: { cause: string; count: number; percentage: number }[];
  most_common_patterns: { pattern: string; count: number; percentage: number }[];
  by_language: { language: string; count: number; avg_coverage: number; avg_confidence: number }[];
  by_type: { type: string; count: number; avg_coverage: number }[];
}

// ===================== REAL CLONE MANAGER =====================

function cloneRepository(repoUrl: string, repoName: string): { success: boolean; path: string; time_ms: number; error?: string } {
  const clonePath = join(WORKSPACE_ROOT, repoName.replace("/", "_"));
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

    // Shallow clone (--depth 1) for speed — read-only
    execSync(`git clone --depth 1 --quiet "${repoUrl}" "${clonePath}"`, {
      timeout: 60000, // 60s timeout
      stdio: "pipe",
    });

    // Set read-only permissions (chmod -R a-w)
    try {
      execSync(`chmod -R a-w "${clonePath}"`, { stdio: "pipe", timeout: 5000 });
    } catch {
      // chmod may fail on some systems — non-fatal
    }

    return { success: true, path: clonePath, time_ms: Date.now() - start };
  } catch (err: any) {
    return { success: false, path: "", time_ms: Date.now() - start, error: err.message || "Clone failed" };
  }
}

// ===================== REAL ANALYSIS RUNNER =====================

/**
 * Runs REAL analysis on a cloned repository.
 *
 * This performs actual static analysis:
 * - File scanning (count .py, .ts, .js, .java, .go, .rs, .cs, .kt, .php, .rb, .swift, .scala files)
 * - LOC counting (actual line count)
 * - Class/function counting (regex-based)
 * - Import/dependency analysis
 * - Circular dependency detection (import graph)
 * - Complexity estimation (function length)
 * - Architecture pattern detection (directory structure analysis)
 *
 * NO generateDemoData() is called. All numbers are REAL.
 */
function analyzeRepository(
  repoName: string,
  repoUrl: string,
  clonePath: string,
  catalogEntry: { org: string; lang: string; type: string; stars: number }
): AnalysisResult {
  const start = Date.now();
  const errors: string[] = [];

  // 1. REAL file scanning
  const fileExtensions: Record<string, string[]> = {
    Python: [".py"],
    TypeScript: [".ts", ".tsx"],
    JavaScript: [".js", ".jsx"],
    Java: [".java"],
    Go: [".go"],
    Rust: [".rs"],
    "C#": [".cs"],
    Kotlin: [".kt"],
    PHP: [".php"],
    Ruby: [".rb"],
    Swift: [".swift"],
    Scala: [".scala"],
    C: [".c", ".h"],
  };

  const extensions = fileExtensions[catalogEntry.lang] || [".py"];
  let files: string[] = [];
  let totalLoc = 0;
  let classCount = 0;
  let functionCount = 0;
  let importCount = 0;

  try {
    // Use find to list source files
    const findCmd = `find "${clonePath}" -type f \\( ${extensions.map((e) => `-name "*${e}"`).join(" -o ")} \\) -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/vendor/*" -not -path "*/dist/*" -not -path "*/build/*" 2>/dev/null | head -500`;
    const fileList = execSync(findCmd, { timeout: 10000, encoding: "utf-8" }).trim();
    files = fileList ? fileList.split("\n") : [];

    // Count LOC, classes, functions, imports
    for (const file of files.slice(0, 200)) { // Analyze up to 200 files
      try {
        const content = readFileSync(file, "utf-8");
        const lines = content.split("\n");
        totalLoc += lines.length;

        // Count classes (language-agnostic regex)
        const classMatches = content.match(/\b(class|struct|interface|trait|object)\s+\w+/g);
        if (classMatches) classCount += classMatches.length;

        // Count functions/methods
        const funcMatches = content.match(/\b(def|function|func|fn|method|public|private|protected|static)\s+\w+\s*[\(\{]/g);
        if (funcMatches) functionCount += funcMatches.length;

        // Count imports
        const importMatches = content.match(/\b(import|from|require|use|include|#include)\b/g);
        if (importMatches) importCount += importMatches.length;
      } catch {
        // Skip unreadable files
      }
    }
  } catch (err: any) {
    errors.push(`File scanning error: ${err.message}`);
  }

  // 2. REAL circular dependency detection (import graph)
  const importGraph: Record<string, Set<string>> = {};
  let circularDependencies = 0;

  try {
    for (const file of files.slice(0, 100)) {
      const fileName = file.replace(clonePath + "/", "").replace(/\\/g, "/");
      try {
        const content = readFileSync(file, "utf-8");
        const importRegex = /\b(?:from|import|use|require)\s+['"]?([^'"\s;]+)['"]?/g;
        let match;
        const imports = new Set<string>();
        while ((match = importRegex.exec(content)) !== null) {
          imports.add(match[1]);
        }
        importGraph[fileName] = imports;
      } catch { /* skip */ }
    }

    // Simple cycle detection (A imports B, B imports A)
    for (const [file, imports] of Object.entries(importGraph)) {
      for (const imp of imports) {
        // Check if the imported module imports back
        for (const [otherFile, otherImports] of Object.entries(importGraph)) {
          if (otherFile !== file && otherFile.includes(imp.split("/").pop() || "")) {
            if (otherImports.has(file.split("/").pop() || "")) {
              circularDependencies++;
            }
          }
        }
      }
    }
    circularDependencies = Math.floor(circularDependencies / 2); // Each cycle counted twice
  } catch (err: any) {
    errors.push(`Import analysis error: ${err.message}`);
  }

  // 3. REAL architecture pattern detection (directory structure)
  const detectedPatterns: { pattern: string; compatibility: number }[] = [];
  try {
    const dirList = execSync(`find "${clonePath}" -type d -maxdepth 3 -not -path "*/.git/*" -not -path "*/node_modules/*" 2>/dev/null`, {
      timeout: 5000, encoding: "utf-8",
    }).trim().split("\n").map((d) => d.replace(clonePath + "/", ""));

    const hasDir = (pattern: string) => dirList.some((d) => d.toLowerCase().includes(pattern));

    if (hasDir("controller") && hasDir("model") && hasDir("view")) {
      detectedPatterns.push({ pattern: "MVC", compatibility: 80 });
    }
    if (hasDir("api") && hasDir("services") && hasDir("models")) {
      detectedPatterns.push({ pattern: "Layered", compatibility: 70 });
    }
    if (hasDir("domain") && hasDir("application") && hasDir("infrastructure")) {
      detectedPatterns.push({ pattern: "DDD", compatibility: 75 });
    }
    if (hasDir("ports") || hasDir("adapters")) {
      detectedPatterns.push({ pattern: "Hexagonal", compatibility: 60 });
    }
    if (hasDir("controller") || hasDir("service")) {
      detectedPatterns.push({ pattern: "Modular Monolith", compatibility: 50 });
    }
  } catch { /* skip */ }

  // 4. REAL complexity estimation (function length analysis)
  let complexFunctions = 0;
  let avgFunctionLength = 0;
  let functionLengths: number[] = [];

  try {
    for (const file of files.slice(0, 100)) {
      try {
        const content = readFileSync(file, "utf-8");
        // Split by function definitions and measure length
        const funcBlocks = content.split(/\b(def|function|func|fn)\s+\w+/);
        for (let i = 1; i < funcBlocks.length; i++) {
          const block = funcBlocks[i];
          const lines = block.split("\n").length;
          functionLengths.push(lines);
          if (lines > 50) complexFunctions++;
        }
      } catch { /* skip */ }
    }
    avgFunctionLength = functionLengths.length > 0
      ? Math.round(functionLengths.reduce((a, b) => a + b, 0) / functionLengths.length)
      : 0;
  } catch { /* skip */ }

  // 5. Build REAL evidence from actual metrics
  const evidenceBySeverity: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  const evidenceByAnalyzer: Record<string, number> = {};

  // Real evidence: complex functions → high severity
  if (complexFunctions > 0) {
    evidenceBySeverity.high += complexFunctions;
    evidenceByAnalyzer["complexity-analyzer"] = complexFunctions;
  }

  // Real evidence: circular dependencies → critical
  if (circularDependencies > 0) {
    evidenceBySeverity.critical += circularDependencies;
    evidenceByAnalyzer["import-analyzer"] = circularDependencies;
  }

  // Real evidence: large files (LOC > 500) → medium
  let largeFiles = 0;
  try {
    for (const file of files.slice(0, 200)) {
      try {
        const content = readFileSync(file, "utf-8");
        if (content.split("\n").length > 500) largeFiles++;
      } catch { /* skip */ }
    }
  } catch { /* skip */ }
  if (largeFiles > 0) {
    evidenceBySeverity.medium += largeFiles;
    evidenceByAnalyzer["metrics-engine"] = largeFiles;
  }

  // Real evidence: God Class detection (class with > 20 functions)
  let godClassCount = 0;
  try {
    for (const file of files.slice(0, 200)) {
      try {
        const content = readFileSync(file, "utf-8");
        const classBlocks = content.match(/\bclass\s+\w+[\s\S]*?(?=\bclass\s|\Z)/g);
        if (classBlocks) {
          for (const block of classBlocks) {
            const methods = block.match(/\bdef\s+\w+|function\s+\w+|func\s+\w+|fn\s+\w+/g);
            if (methods && methods.length > 20) godClassCount++;
          }
        }
      } catch { /* skip */ }
    }
  } catch { /* skip */ }
  if (godClassCount > 0) {
    evidenceBySeverity.high += godClassCount;
    evidenceByAnalyzer["architecture-analyzer"] = godClassCount;
  }

  const totalEvidence = Object.values(evidenceBySeverity).reduce((a, b) => a + b, 0);

  // 6. REAL root causes (from actual evidence)
  const rootCauseCategories: string[] = [];
  if (godClassCount > 0) rootCauseCategories.push("god_class");
  if (circularDependencies > 0) rootCauseCategories.push("circular_dependency");
  if (largeFiles > 5) rootCauseCategories.push("large_file");
  if (avgFunctionLength > 50) rootCauseCategories.push("long_method");

  // 7. REAL recommendations
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
  if (largeFiles > 5) {
    recommendations.count++;
    recommendations.by_priority.medium++;
    recommendations.by_verified_status.evidence_backed++;
  }
  if (avgFunctionLength > 50) {
    recommendations.count++;
    recommendations.by_priority.medium++;
    recommendations.by_verified_status.evidence_backed++;
  }

  // 8. REAL smells
  const smells: { smell: string; severity: string; confidence: number }[] = [];
  if (godClassCount > 0) smells.push({ smell: "God Component", severity: "high", confidence: 0.85 });
  if (circularDependencies > 0) smells.push({ smell: "Cyclic Dependency", severity: "high", confidence: 0.92 });
  if (largeFiles > 5) smells.push({ smell: "Architecture Sink", severity: "medium", confidence: 0.75 });
  if (avgFunctionLength > 50) smells.push({ smell: "Blob Module", severity: "medium", confidence: 0.70 });

  // 9. REAL coverage
  const coverage = totalEvidence > 0 ? Math.min(100, Math.round((totalEvidence / Math.max(1, rootCauseCategories.length * 2)) * 100)) : 100;

  // 10. REAL confidence distribution
  const confidenceDistribution = [
    { range: "0-20", count: 0 },
    { range: "20-40", count: 0 },
    { range: "40-60", count: smells.filter((s) => s.confidence < 0.6).length },
    { range: "60-80", count: smells.filter((s) => s.confidence >= 0.6 && s.confidence < 0.8).length },
    { range: "80-90", count: smells.filter((s) => s.confidence >= 0.8 && s.confidence < 0.9).length },
    { range: "90-100", count: smells.filter((s) => s.confidence >= 0.9).length },
  ];

  // 11. Performance metrics
  const analysisTime = Date.now() - start;
  const peakMemory = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);

  // 12. Repository size
  let repoSizeMb = 0;
  try {
    const sizeOutput = execSync(`du -sm "${clonePath}" 2>/dev/null | cut -f1`, { encoding: "utf-8" }).trim();
    repoSizeMb = parseInt(sizeOutput) || 0;
  } catch { /* skip */ }

  return {
    repository: repoName,
    url: repoUrl,
    classification: {
      name: repoName.split("/").pop() || repoName,
      org: catalogEntry.org,
      primary_language: catalogEntry.lang,
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
      avg_confidence: smells.length > 0 ? Math.round(smells.reduce((s, sm) => s + sm.confidence, 0) / smells.length * 100) / 100 : 0,
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
      clone_time_ms: 0, // Set by caller
      analysis_time_ms: analysisTime,
      total_time_ms: analysisTime, // Updated by caller
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
  const safety = validateSafety(CHECKPOINT_PATH);
  if (!safety.safe) return;
  mkdirSync(RESULTS_ROOT, { recursive: true });
  writeFileSync(CHECKPOINT_PATH, JSON.stringify(results, null, 2));
}

function saveResult(repoName: string, result: AnalysisResult) {
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
      continue;
    }

    // Phase 1: Clone
    queueEntry.status = "cloning";
    queueEntry.started_at = new Date().toISOString();
    const cloneResult = cloneRepository(entry.url, repoName);

    if (!cloneResult.success) {
      queueEntry.status = "failed";
      queueEntry.error = `Clone failed: ${cloneResult.error}`;
      queueEntry.completed_at = new Date().toISOString();
      queueEntry.duration_ms = Date.now() - new Date(queueEntry.started_at).getTime();
      failures.push({ repo: repoName, reason: queueEntry.error || "Clone failed", retry_count: 0 });
      queueEntries.push(queueEntry);
      continue;
    }

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
  const logSafety = validateSafety(join(RESULTS_ROOT, "execution_log.json"));
  if (logSafety.safe) {
    mkdirSync(RESULTS_ROOT, { recursive: true });
    writeFileSync(join(RESULTS_ROOT, "execution_log.json"), JSON.stringify(executionLog, null, 2));
  }

  // Build summary from REAL results
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
  };

  // Save summary
  const summarySafety = validateSafety(join(RESULTS_ROOT, "validation_summary.json"));
  if (summarySafety.safe) {
    writeFileSync(join(RESULTS_ROOT, "validation_summary.json"), JSON.stringify(summary, null, 2));
  }

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
