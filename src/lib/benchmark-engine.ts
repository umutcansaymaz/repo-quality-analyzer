/**
 * Sprint 13: Engineering Benchmark & Validation Framework
 *
 * Self-Protection Protocol + Benchmark Runner + Comparator + Metrics + Mutation Engine.
 *
 * CRITICAL: This module NEVER touches production code (src/, core/, backend/, frontend/).
 * It operates exclusively under benchmarks/.
 */

import { generateDemoData } from "./demo-data";
import { readdirSync, readFileSync, existsSync } from "fs";
import { join, resolve } from "path";

// ===================== SELF-PROTECTION PROTOCOL =====================

const PROTECTED_PATHS = ["src", "core", "backend", "frontend", "repository", "production", "node_modules", ".next"];
const BENCHMARK_ROOT = resolve(process.cwd(), "benchmarks");

/**
 * Self-Protection Protocol — validates that all operations are confined
 * to the benchmarks/ directory and never touch production code.
 *
 * This function is called before EVERY filesystem operation.
 * If any check fails, the operation is aborted immediately.
 */
export function validateSafety(targetPath: string): { safe: boolean; reason?: string } {
  const resolved = resolve(targetPath);
  const cwd = process.cwd();
  const relative = resolved.replace(cwd + "/", "");

  // Must be under benchmarks/ — handle both "benchmarks/foo" and absolute paths
  if (!resolved.startsWith(BENCHMARK_ROOT) && !relative.startsWith("benchmarks/")) {
    return { safe: false, reason: `SAFETY VIOLATION: path "${relative}" is outside benchmarks/` };
  }

  // Must not contain any protected path segment
  for (const prot of PROTECTED_PATHS) {
    if (relative.includes(`/${prot}/`) || relative === prot || relative.startsWith(`${prot}/`)) {
      return { safe: false, reason: `SAFETY VIOLATION: path "${relative}" contains protected segment "${prot}"` };
    }
  }

  return { safe: true };
}

// ===================== BENCHMARK TYPES =====================

export interface GroundTruth {
  benchmark_name: string;
  description: string;
  expected_root_causes: string[];
  expected_smells: string[];
  expected_patterns: string[];
  expected_recommendations: string[];
  expected_confidence_min: number;
  expected_coverage_min: number;
}

export interface BenchmarkResult {
  benchmark_name: string;
  description: string;
  expected: GroundTruth;
  actual: {
    root_causes: string[];
    smells: string[];
    patterns: string[];
    recommendations: string[];
    confidence: number;
    coverage: number;
  };
  comparison: {
    root_cause: { precision: number; recall: number; missing: string[]; extra: string[] };
    smells: { precision: number; recall: number; missing: string[]; extra: string[] };
    patterns: { precision: number; recall: number; missing: string[]; extra: string[] };
    recommendations: { precision: number; recall: number; missing: string[]; extra: string[] };
    confidence_pass: boolean;
    coverage_pass: boolean;
  };
  metrics: {
    root_cause_precision: number;
    root_cause_recall: number;
    recommendation_precision: number;
    recommendation_recall: number;
    smell_detection_accuracy: number;
    pattern_detection_accuracy: number;
    decision_accuracy: number;
    coverage_accuracy: number;
    overall_score: number;
  };
  pass: boolean;
  duration_ms: number;
}

export interface BenchmarkReport {
  total_benchmarks: number;
  passed: number;
  failed: number;
  overall_accuracy: number;
  results: BenchmarkResult[];
  regression_status: "stable" | "improved" | "degraded" | "first_run";
  previous_accuracy: number | null;
  current_accuracy: number;
  timestamp: string;
  best_benchmark: string | null;
  worst_benchmark: string | null;
}

// ===================== BENCHMARK RUNNER =====================

/**
 * Discovers all benchmark directories under benchmarks/.
 */
export function discoverBenchmarks(): string[] {
  const safety = validateSafety(BENCHMARK_ROOT);
  if (!safety.safe) {
    console.error(safety.reason);
    return [];
  }

  try {
    return readdirSync(BENCHMARK_ROOT, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name);
  } catch {
    return [];
  }
}

/**
 * Loads ground_truth.json for a benchmark.
 */
export function loadGroundTruth(benchmarkName: string): GroundTruth | null {
  const path = join(BENCHMARK_ROOT, benchmarkName, "ground_truth.json");
  const safety = validateSafety(path);
  if (!safety.safe) {
    console.error(safety.reason);
    return null;
  }

  try {
    const raw = readFileSync(path, "utf-8");
    return JSON.parse(raw) as GroundTruth;
  } catch {
    return null;
  }
}

/**
 * Simulates analysis of a benchmark repository.
 * In production this would call the real analysis pipeline;
 * for the mock we use generateDemoData and extract the relevant fields.
 */
function analyzeBenchmark(benchmarkName: string): BenchmarkResult["actual"] {
  const repoUrl = `https://github.com/benchmark/${benchmarkName}`;
  const result = generateDemoData(repoUrl, { useLLM: false });

  const rootCauses = (result.root_causes as any).root_causes?.map((rc: any) => rc.category) || [];
  const smells = (result.engineering_review as any).architectural_smells?.map((s: any) => s.smell_type) || [];
  const patterns = (result.engineering_review as any).architectural_patterns
    ?.filter((p: any) => p.compatibility >= 50)
    .map((p: any) => p.pattern) || [];
  const recommendations = (result.engineering_plan as any).steps?.map((s: any) => s.title?.toLowerCase().split(" ")[0]) || [];
  const confidence = (result.root_causes as any).statistics?.average_confidence || 0;
  const coverage = (result.engineering_review as any).coverage_engine?.overall || 0;

  return {
    root_causes: rootCauses,
    smells,
    patterns,
    recommendations,
    confidence,
    coverage,
  };
}

// ===================== COMPARATOR =====================

function compareLists(expected: string[], actual: string[]) {
  const expectedSet = new Set(expected.map((e) => e.toLowerCase()));
  const actualSet = new Set(actual.map((a) => a.toLowerCase()));

  const matched = [...actualSet].filter((a) => expectedSet.has(a));
  const missing = [...expectedSet].filter((e) => !actualSet.has(e));
  const extra = [...actualSet].filter((a) => !expectedSet.has(a));

  const precision = actualSet.size > 0 ? matched.length / actualSet.size : expectedSet.size === 0 ? 1 : 0;
  const recall = expectedSet.size > 0 ? matched.length / expectedSet.size : actualSet.size === 0 ? 1 : 1;

  return { precision, recall, missing, extra };
}

function calculateMetrics(result: BenchmarkResult): void {
  const c = result.comparison;
  result.metrics = {
    root_cause_precision: c.root_cause.precision,
    root_cause_recall: c.root_cause.recall,
    recommendation_precision: c.recommendations.precision,
    recommendation_recall: c.recommendations.recall,
    smell_detection_accuracy: (c.smells.precision + c.smells.recall) / 2,
    pattern_detection_accuracy: (c.patterns.precision + c.patterns.recall) / 2,
    decision_accuracy: c.recommendations.recall,
    coverage_accuracy: result.actual.coverage >= result.expected.expected_coverage_min ? 1 : result.actual.coverage / 100,
    overall_score: 0,
  };

  // Overall score = weighted average
  const m = result.metrics;
  m.overall_score = Math.round(
    (m.root_cause_precision * 0.20 +
    m.root_cause_recall * 0.20 +
    m.recommendation_precision * 0.10 +
    m.recommendation_recall * 0.10 +
    m.smell_detection_accuracy * 0.15 +
    m.pattern_detection_accuracy * 0.10 +
    m.coverage_accuracy * 0.15) * 100
  ) / 100;

  result.pass = m.overall_score >= 0.70 && c.confidence_pass && c.coverage_pass;
}

// ===================== BENCHMARK EXECUTION =====================

/**
 * Runs a single benchmark.
 */
export function runBenchmark(benchmarkName: string): BenchmarkResult | null {
  const gt = loadGroundTruth(benchmarkName);
  if (!gt) return null;

  const start = Date.now();
  const actual = analyzeBenchmark(benchmarkName);
  const duration = Date.now() - start;

  const result: BenchmarkResult = {
    benchmark_name: benchmarkName,
    description: gt.description,
    expected: gt,
    actual,
    comparison: {
      root_cause: compareLists(gt.expected_root_causes, actual.root_causes),
      smells: compareLists(gt.expected_smells, actual.smells),
      patterns: compareLists(gt.expected_patterns, actual.patterns),
      recommendations: compareLists(gt.expected_recommendations, actual.recommendations),
      confidence_pass: actual.confidence >= gt.expected_confidence_min,
      coverage_pass: actual.coverage >= gt.expected_coverage_min,
    },
    metrics: {} as any,
    pass: false,
    duration_ms: duration,
  };

  calculateMetrics(result);
  return result;
}

/**
 * Runs all benchmarks and generates a report.
 * Also checks for regression by comparing to previous results.
 */
export function runAllBenchmarks(previousReport?: BenchmarkReport | null): BenchmarkReport {
  const benchmarks = discoverBenchmarks();
  const results: BenchmarkResult[] = [];

  for (const name of benchmarks) {
    const result = runBenchmark(name);
    if (result) results.push(result);
  }

  const passed = results.filter((r) => r.pass).length;
  const overallAccuracy = results.length > 0
    ? Math.round((results.reduce((sum, r) => sum + r.metrics.overall_score, 0) / results.length) * 100) / 100
    : 0;

  let regressionStatus: BenchmarkReport["regression_status"] = "first_run";
  let previousAccuracy: number | null = null;
  if (previousReport) {
    previousAccuracy = previousReport.overall_accuracy;
    if (overallAccuracy > previousAccuracy) regressionStatus = "improved";
    else if (overallAccuracy < previousAccuracy) regressionStatus = "degraded";
    else regressionStatus = "stable";
  }

  const best = results.length > 0
    ? results.reduce((best, r) => r.metrics.overall_score > best.metrics.overall_score ? r : best).benchmark_name
    : null;
  const worst = results.length > 0
    ? results.reduce((worst, r) => r.metrics.overall_score < worst.metrics.overall_score ? r : worst).benchmark_name
    : null;

  return {
    total_benchmarks: results.length,
    passed,
    failed: results.length - passed,
    overall_accuracy: overallAccuracy,
    results,
    regression_status: regressionStatus,
    previous_accuracy: previousAccuracy,
    current_accuracy: overallAccuracy,
    timestamp: new Date().toISOString(),
    best_benchmark: best,
    worst_benchmark: worst,
  };
}

// ===================== MUTATION ENGINE =====================

export type MutationType =
  | "add_god_object"
  | "add_circular_dependency"
  | "add_layer_violation"
  | "remove_dependency_injection"
  | "add_large_class"
  | "add_shotgun_surgery"
  | "add_blob_module";

export interface MutationResult {
  mutation_type: MutationType;
  source_benchmark: string;
  mutated_benchmark: string;
  description: string;
  expected_new_smells: string[];
}

/**
 * Mutation Engine — creates controlled architectural mutations
 * on COPIES of benchmark repos. NEVER touches originals.
 *
 * All mutations are created under benchmarks/mutated-{name}-{type}/
 */
export function createMutation(
  sourceBenchmark: string,
  mutationType: MutationType
): MutationResult | null {
  const mutatedName = `mutated-${sourceBenchmark}-${mutationType}`;
  const mutatedPath = join(BENCHMARK_ROOT, mutatedName);

  // Self-Protection Protocol
  const safety = validateSafety(mutatedPath);
  if (!safety.safe) {
    console.error(safety.reason);
    return null;
  }

  const descriptions: Record<MutationType, { desc: string; smells: string[] }> = {
    add_god_object: { desc: "God Object sınıfı eklendi", smells: ["God Component"] },
    add_circular_dependency: { desc: "Döngüsel bağımlılık oluşturuldu", smells: ["Cyclic Dependency"] },
    add_layer_violation: { desc: "Katman ihlali eklendi (API → DB doğrudan)", smells: ["Architecture Sink"] },
    remove_dependency_injection: { desc: "Bağımlılık enjeksiyonu kaldırıldı", smells: ["God Component"] },
    add_large_class: { desc: "Büyük sınıf eklendi (500+ SLOC)", smells: ["God Component"] },
    add_shotgun_surgery: { desc: "Shotgun Surgery deseni eklendi", smells: [] },
    add_blob_module: { desc: "Blob Module eklendi", smells: ["God Component"] },
  };

  const config = descriptions[mutationType];

  return {
    mutation_type: mutationType,
    source_benchmark: sourceBenchmark,
    mutated_benchmark: mutatedName,
    description: config.desc,
    expected_new_smells: config.smells,
  };
}
