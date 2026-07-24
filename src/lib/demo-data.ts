/**
 * Shared demo-data generator.
 *
 * Used by:
 *  - Mock API routes  (src/app/api/analyze, /api/result/[id], /api/report)
 *  - Client-side fallback (src/app/page.tsx `getDemoData`)
 *
 * Produces a deterministic-but-varied analysis result for any repository URL
 * so the app works end-to-end without the real Python backend.
 */

// Lightweight deterministic hash so the same URL always yields the same numbers.
function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

function seeded(n: number, min: number, max: number): number {
  // Map the seed to [min, max) deterministically.
  return min + (n % 1000) / 1000 * (max - min);
}

function pick<T>(arr: T[], n: number): T {
  return arr[n % arr.length];
}

export interface DemoResult {
  id: string;
  status: string;
  repository: { url: string; owner: string; name: string; host: string; access: string };
  repository_metadata: Record<string, unknown>;
  ai_review: { health_score: Record<string, number>; security_review: Record<string, unknown> };
  root_causes: Record<string, unknown>;
  engineering_plan: Record<string, unknown>;
  evidence: Record<string, unknown>;
  knowledge_graph: Record<string, unknown>;
  file_inventory: Record<string, unknown>;
  engineering_review: Record<string, unknown>;
  analyzed_at: string;
}

export function generateDemoData(repoUrl: string): DemoResult {
  const owner = repoUrl.split("/").slice(-2)[0] || "example";
  const name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
  const h = hashString(repoUrl);

  // Vary scores deterministically by URL so different repos feel different.
  const overall = Number(seeded(h, 58, 88).toFixed(1));
  const grade = overall >= 80 ? "A" : overall >= 70 ? "B" : overall >= 60 ? "B-" : overall >= 50 ? "C" : "D";
  const security = Number(seeded(h + 1, 65, 95).toFixed(1));
  const architecture = Number(seeded(h + 2, 50, 82).toFixed(1));
  const maintainability = Number(seeded(h + 3, 55, 85).toFixed(1));
  const performance = Number(seeded(h + 4, 60, 88).toFixed(1));
  const documentation = Number(seeded(h + 5, 40, 78).toFixed(1));
  const testing = Number(seeded(h + 6, 35, 80).toFixed(1));
  const developerExperience = Number(seeded(h + 7, 55, 82).toFixed(1));
  const scalability = Number(seeded(h + 8, 58, 85).toFixed(1));
  const codeQuality = Number(seeded(h + 9, 55, 84).toFixed(1));

  const totalCommits = 80 + (h % 400);
  const contributors = ["alice", "bob", "charlie", "dave", "eve"].slice(0, 2 + (h % 4));
  const sizeBytes = 120000 + (h % 800000);
  const license = pick(["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0", "ISC"], h);

  return {
    id: `demo-${h.toString(36)}`,
    status: "completed",
    repository: { url: repoUrl, owner, name, host: "github.com", access: "public" },
    repository_metadata: {
      name, owner,
      description: `${owner}/${name} — analyzed by AI Software Architect (demo mode)`,
      default_branch: "main",
      license,
      total_commits: totalCommits,
      total_branches: 2 + (h % 5),
      contributors,
      size_bytes: sizeBytes,
    },
    ai_review: {
      health_score: {
        overall, grade, security, architecture, maintainability, performance,
        documentation, testing, developer_experience: developerExperience,
        scalability, code_quality: codeQuality,
      },
      security_review: { security_score: security, findings: [], overall_severity: "info" },
    },
    root_causes: {
      root_causes: [
        { id: "rc-1", category: "god_class", title: `God Class: ${pick(["UserService", "OrderManager", "ApiClient", "DataProcessor"], h)}`, severity: "high", confidence: 0.85, description: "A single class accumulates multiple responsibilities.", technical_rationale: "4 distinct symptom types detected from 3 analyzers.", root_cause_origin: "Organic growth without refactoring.", affected_files: ["src/services/user_service.py", "src/api/user_routes.py"], affected_classes: ["UserService"], affected_modules: ["services.user"], evidence_count: 8, evidence_links: [{ evidence_id: "ev-1", contribution: 0.9, reason: "High complexity" }, { evidence_id: "ev-2", contribution: 0.8, reason: "Long method" }, { evidence_id: "ev-3", contribution: 0.7, reason: "Large file" }] },
        { id: "rc-2", category: "circular_dependency", title: "Circular Dependency: auth \u2194 user", severity: "high", confidence: 0.92, description: "Circular dependency between auth and user modules.", technical_rationale: "Import graph contains a cycle.", root_cause_origin: "Modules added without checking import direction.", affected_files: ["src/auth/service.py", "src/user/service.py"], affected_modules: ["auth", "user"], evidence_count: 3, evidence_links: [{ evidence_id: "ev-4", contribution: 1.0, reason: "Direct cycle" }] },
        { id: "rc-3", category: "tight_coupling", title: "Tight Coupling: Database Layer", severity: "medium", confidence: 0.75, description: "Multiple services directly depend on the database client.", technical_rationale: "Graph analysis shows excessive dependency edges.", root_cause_origin: "Direct dependencies instead of abstractions.", affected_files: ["src/services/user_service.py", "src/services/order_service.py"], affected_modules: ["services"], evidence_count: 5, evidence_links: [{ evidence_id: "ev-5", contribution: 0.8, reason: "measures coupling" }] },
        { id: "rc-4", category: "shotgun_surgery", title: "Shotgun Surgery: logging changes", severity: "low", confidence: 0.68, description: "Logging changes require modifications across 8 files.", technical_rationale: "Finding appears in 8 different files.", root_cause_origin: "Copy-paste without extracting a utility.", affected_files: ["src/api/users.py", "src/api/orders.py", "src/api/products.py", "src/api/payments.py", "src/services/user_service.py"], affected_modules: ["api", "services"], evidence_count: 8, evidence_links: [{ evidence_id: "ev-6", contribution: 0.7, reason: "systemic pattern" }] },
      ],
      relationships: [{ source_root_cause_id: "rc-1", target_root_cause_id: "rc-3", relationship_type: "causes", detail: "God Class causes tight coupling" }],
      statistics: { total_root_causes: 4, average_confidence: 0.80, by_category_counts: { god_class: 1, circular_dependency: 1, tight_coupling: 1, shotgun_surgery: 1 }, by_severity_counts: { high: 2, medium: 1, low: 1 } },
    },
    engineering_plan: {
      steps: [
        { id: "step-1", step_number: 1, title: "Split God Class into focused services", technical_description: "Extract auth, profile, notifications, and settings into separate services.", root_cause_id: "rc-1", root_cause_category: "god_class", priority: "high", roi: 2.25, estimate: { hours: 40, display: "5 days", developers: 2, confidence: 0.5 }, risk: "high", risk_reason: "Large-scale refactoring.", expected_outcomes: ["Improved maintainability (+90%)", "Improved testability (+80%)"], prerequisites: [], alternatives: [{ id: "alt-1", name: "Extract Class", description: "Split into focused classes.", advantages: ["Clear responsibilities", "Easier to test"], disadvantages: ["More files to manage"], risk: "medium", maintenance_cost: "low", performance_impact: "neutral", migration_difficulty: "medium" }, { id: "alt-2", name: "Facade + Delegate", description: "Keep as facade, delegate internally.", advantages: ["Backward compatible", "Gradual migration"], disadvantages: ["Facade still exists"], risk: "low", maintenance_cost: "medium", performance_impact: "neutral", migration_difficulty: "low" }], affected_files: ["src/services/user_service.py"] },
        { id: "step-2", step_number: 2, title: "Break circular dependency: auth \u2194 user", technical_description: "Extract shared logic into a new lower-level module.", root_cause_id: "rc-2", root_cause_category: "circular_dependency", priority: "high", roi: 3.54, estimate: { hours: 24, display: "3 days", developers: 1, confidence: 0.5 }, risk: "high", risk_reason: "Changes affect critical paths.", expected_outcomes: ["Improved maintainability (+85%)", "Improved testability (+80%)"], prerequisites: ["step-1"], alternatives: [], affected_files: ["src/auth/service.py", "src/user/service.py"] },
        { id: "step-3", step_number: 3, title: "Introduce repository interface for database access", technical_description: "Create an abstract repository interface and use DI.", root_cause_id: "rc-3", root_cause_category: "tight_coupling", priority: "medium", roi: 1.88, estimate: { hours: 24, display: "3 days", developers: 1, confidence: 0.5 }, risk: "medium", risk_reason: "Moderate changes.", expected_outcomes: ["Improved testability (+70%)", "Improved maintainability (+75%)"], prerequisites: ["step-1"], alternatives: [], affected_files: ["src/services/user_service.py", "src/services/order_service.py"] },
        { id: "step-4", step_number: 4, title: "Extract shared logging utility", technical_description: "Create a centralized logging wrapper.", root_cause_id: "rc-4", root_cause_category: "shotgun_surgery", priority: "low", roi: 5.42, estimate: { hours: 4, display: "4 hours", developers: 1, confidence: 0.7 }, risk: "low", risk_reason: "Low risk; isolated changes.", expected_outcomes: ["Reduced technical debt", "Consistent logging"], prerequisites: [], alternatives: [], affected_files: ["src/api/users.py", "src/api/orders.py"] },
      ],
      roadmap: { sprints: [{ sprint_number: 1, title: "Sprint 1: Critical Refactoring", step_ids: ["step-1"], total_estimated_hours: 40, goals: ["Split God Class"], steps: [] }, { sprint_number: 2, title: "Sprint 2: Architecture Fixes", step_ids: ["step-2", "step-3"], total_estimated_hours: 48, goals: ["Break circular dependency", "Introduce repository interface"], steps: [] }, { sprint_number: 3, title: "Sprint 3: Cleanup & Maintenance", step_ids: ["step-4"], total_estimated_hours: 4, goals: ["Extract shared logging utility"], steps: [] }], total_estimated_hours: 92, total_steps: 4, summary: "3 sprint(s) covering 4 step(s), ~92 engineer-hours total." },
      quick_wins: [{ id: "qw-1", title: "Extract shared logging utility", description: "Create a centralized logging wrapper.", effort_minutes: 240, benefit: "Benefit score: 65/100", planning_step_id: "step-4", root_cause_id: "rc-4" }, { id: "qw-2", title: "Remove unused imports", description: "5 unused imports detected.", effort_minutes: 15, benefit: "Quick fix: dead_code", planning_step_id: null, root_cause_id: null }],
      blockers: [{ id: "blk-1", blocker_root_cause_id: "rc-1", blocked_root_cause_ids: ["rc-3"], reason: "God Class must be addressed first.", planning_step_id: "step-1" }],
      statistics: { total_steps: 4, total_quick_wins: 2, total_blockers: 1, average_roi: 3.27, priority_counts: { high: 2, medium: 1, low: 1 }, risk_counts: { high: 2, medium: 1, low: 1 } },
    },
    evidence: {
      evidence: [
        { id: "ev-1", analyzer: "complexity-analyzer", finding_type: "complexity", severity: "high", confidence: 1.0, category: "cyclomatic_complexity", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "High complexity: process_user (CC=41)", tags: ["complexity", "E"], metrics: { complexity: 41, rank: "E" } },
        { id: "ev-2", analyzer: "code-quality-engine", finding_type: "code_quality", severity: "medium", confidence: 0.8, category: "long_method", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "Long method: process_user", tags: ["long_method", "high"] },
        { id: "ev-3", analyzer: "metrics-engine", finding_type: "metric", severity: "medium", confidence: 1.0, category: "large_file", file_path: "src/services/user_service.py", message: "Large file (650 SLOC)", tags: ["large_file"], metrics: { sloc: 650 } },
        { id: "ev-4", analyzer: "import-analyzer", finding_type: "import", severity: "high", confidence: 1.0, category: "circular_import", message: "Circular import: auth \u2192 user \u2192 auth", tags: ["circular_import"] },
        { id: "ev-5", analyzer: "architecture-review-engine", finding_type: "architecture", severity: "medium", confidence: 0.7, category: "high_coupling", file_path: "src/services/user_service.py", message: "High coupling (0.85)", tags: ["high_coupling"] },
        { id: "ev-6", analyzer: "import-analyzer", finding_type: "import", severity: "low", confidence: 0.9, category: "unused_import", file_path: "src/api/users.py", message: "Unused import: os", tags: ["unused_import", "dead_code"] },
        { id: "ev-7", analyzer: "security-engine", finding_type: "security", severity: "critical", confidence: 0.9, category: "hardcoded_password", file_path: "src/config.py", line: 10, message: "Hardcoded Password", tags: ["hardcoded_password"] },
        { id: "ev-8", analyzer: "test-coverage-analyzer", finding_type: "test", severity: "medium", confidence: 0.9, category: "low_coverage", message: "Low test coverage: 35%", tags: ["testing", "low_coverage"], metrics: { estimated_coverage: 35 } },
      ],
      relationships: [],
      statistics: { total_evidence: 8, by_type_counts: { complexity: 1, code_quality: 1, metric: 1, import: 2, architecture: 1, security: 1, test: 1 }, by_severity_counts: { critical: 1, high: 2, medium: 3, low: 2 }, by_analyzer_counts: { "complexity-analyzer": 1, "code-quality-engine": 1, "metrics-engine": 1, "import-analyzer": 2, "architecture-review-engine": 1, "security-engine": 1, "test-coverage-analyzer": 1 } },
    },
    knowledge_graph: {
      nodes: [
        { id: "n1", node_type: "repository", label: `${owner}/${name}`, key: "repo:1" },
        { id: "n2", node_type: "file", label: "src/services/user_service.py", key: "file:1", file_path: "src/services/user_service.py" },
        { id: "n3", node_type: "file", label: "src/api/users.py", key: "file:2", file_path: "src/api/users.py" },
        { id: "n4", node_type: "class", label: "UserService", key: "class:1", file_path: "src/services/user_service.py", class_name: "UserService" },
        { id: "n5", node_type: "function", label: "process_user", key: "func:1", file_path: "src/services/user_service.py", function_name: "process_user" },
        { id: "n6", node_type: "module", label: "services.user", key: "module:1", module: "services.user" },
        { id: "n7", node_type: "module", label: "auth", key: "module:2", module: "auth" },
        { id: "n8", node_type: "security_finding", label: "Hardcoded Password", key: "ev:7", file_path: "src/config.py", severity: "critical", evidence_id: "ev-7", metadata: { analyzer: "security-engine" } },
        { id: "n9", node_type: "metric_finding", label: "High complexity: process_user", key: "ev:1", file_path: "src/services/user_service.py", severity: "high", evidence_id: "ev-1", metadata: { analyzer: "complexity-analyzer" } },
        { id: "n10", node_type: "dependency", label: "requests", key: "dep:1", metadata: {} },
      ],
      edges: [
        { id: "e1", source_id: "n2", target_id: "n1", edge_type: "belongs_to" },
        { id: "e2", source_id: "n3", target_id: "n1", edge_type: "belongs_to" },
        { id: "e3", source_id: "n4", target_id: "n2", edge_type: "belongs_to" },
        { id: "e4", source_id: "n5", target_id: "n2", edge_type: "belongs_to" },
        { id: "e5", source_id: "n9", target_id: "n5", edge_type: "affects" },
        { id: "e6", source_id: "n8", target_id: "n2", edge_type: "affects" },
      ],
      total_nodes: 10, total_edges: 6,
    },
    file_inventory: { total_files: 24, total_directories: 8, total_bytes: sizeBytes, files: ["src/services/user_service.py", "src/api/users.py", "src/api/orders.py", "src/auth/service.py", "src/user/service.py", "src/config.py", "src/models/user.py", "src/utils/helpers.py", "tests/test_user_service.py", "README.md"] },
    engineering_review: {
      offline: true,
      sections: [
        { section_type: "executive_summary", title: "Executive Summary", body: `Root cause analysis identified 4 architectural root cause(s) with an average confidence of 80%. The engineering plan proposes 4 refactoring step(s) across 3 sprint(s), totaling approximately 92 engineer-hours. 2 quick win(s) identified. Overall health: ${overall}/100 (${grade}).`, confidence: "high" },
        { section_type: "top_root_causes", title: "Top Root Causes", body: "- God Class (high, 85%)\n- Circular Dependency: auth \u2194 user (high, 92%)\n- Tight Coupling: Database Layer (medium, 75%)\n- Shotgun Surgery: logging changes (low, 68%)", confidence: "high" },
        { section_type: "highest_roi_refactoring", title: "Highest ROI Refactoring", body: "Step 4: Extract shared logging utility\nROI: 5.42\nPriority: low\nEstimate: 4 hours", confidence: "high" },
        { section_type: "long_term_vision", title: "Long-term Vision", body: "The team should aim to decompose large classes/services into focused, single-responsibility components over the next 6 months.", confidence: "low" },
      ],
      challenges: [],
      recommendations: [],
      model_info: { provider: "offline", model: "deterministic-fallback" },
      prompt_tokens: 0, completion_tokens: 0,
      statistics: { total_sections: 4, total_challenges: 0, offline: true },
    },
    analyzed_at: new Date().toISOString(),
  };
}

/**
 * Build a human-readable report from a demo result.
 * Supports: markdown ("md"), json, html, text.
 */
export function buildReport(result: DemoResult, format: string): { content: string; contentType: string; filename: string } {
  const hs = result.ai_review.health_score as any;
  const repo = result.repository;
  const rc = result.root_causes as any;
  const plan = result.engineering_plan as any;

  if (format === "json") {
    return {
      content: JSON.stringify(result, null, 2),
      contentType: "application/json",
      filename: `${repo.owner}-${repo.name}-report.json`,
    };
  }

  if (format === "html") {
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>Report — ${repo.owner}/${repo.name}</title>
<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#222}h1{color:#1a1a1a}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:6px 8px;text-align:left}th{background:#f5f5f5}</style>
</head><body>
<h1>AI Software Architect — Report</h1>
<p><strong>Repository:</strong> ${repo.owner}/${repo.name}</p>
<p><strong>Health:</strong> ${hs.overall}/100 (Grade ${hs.grade})</p>
<h2>Health Scores</h2>
<table><tr><th>Dimension</th><th>Score</th></tr>
<tr><td>Security</td><td>${hs.security}</td></tr>
<tr><td>Architecture</td><td>${hs.architecture}</td></tr>
<tr><td>Maintainability</td><td>${hs.maintainability}</td></tr>
<tr><td>Testing</td><td>${hs.testing}</td></tr>
<tr><td>Documentation</td><td>${hs.documentation}</td></tr>
</table>
<h2>Root Causes (${rc.root_causes.length})</h2>
<ul>${rc.root_causes.map((r: any) => `<li><strong>${r.title}</strong> — ${r.severity}, ${(r.confidence * 100).toFixed(0)}% confidence</li>`).join("")}</ul>
<h2>Engineering Plan (${plan.steps.length} steps)</h2>
<ol>${plan.steps.map((s: any) => `<li><strong>${s.title}</strong> — ROI ${s.roi.toFixed(2)}, ${s.estimate.display}, risk: ${s.risk}</li>`).join("")}</ol>
</body></html>`;
    return {
      content: html,
      contentType: "text/html",
      filename: `${repo.owner}-${repo.name}-report.html`,
    };
  }

  // Default: markdown
  const lines: string[] = [];
  lines.push(`# AI Software Architect — Report`);
  lines.push("");
  lines.push(`**Repository:** ${repo.owner}/${repo.name}`);
  lines.push(`**URL:** ${repo.url}`);
  lines.push(`**Analyzed at:** ${result.analyzed_at}`);
  lines.push("");
  lines.push(`## Health Score`);
  lines.push("");
  lines.push(`| Dimension | Score |`);
  lines.push(`|---|---|`);
  lines.push(`| Overall | **${hs.overall}/100** (Grade ${hs.grade}) |`);
  lines.push(`| Security | ${hs.security} |`);
  lines.push(`| Architecture | ${hs.architecture} |`);
  lines.push(`| Maintainability | ${hs.maintainability} |`);
  lines.push(`| Testing | ${hs.testing} |`);
  lines.push(`| Documentation | ${hs.documentation} |`);
  lines.push("");
  lines.push(`## Root Causes (${rc.root_causes.length})`);
  lines.push("");
  rc.root_causes.forEach((r: any) => {
    lines.push(`### ${r.title}`);
    lines.push(`- **Severity:** ${r.severity}`);
    lines.push(`- **Confidence:** ${(r.confidence * 100).toFixed(0)}%`);
    lines.push(`- **Category:** ${r.category}`);
    lines.push(`- **Evidence count:** ${r.evidence_count}`);
    if (r.description) lines.push(`- **Description:** ${r.description}`);
    lines.push("");
  });
  lines.push(`## Engineering Plan (${plan.steps.length} steps)`);
  lines.push("");
  plan.steps.forEach((s: any) => {
    lines.push(`### ${s.step_number}. ${s.title}`);
    lines.push(`- **Priority:** ${s.priority}`);
    lines.push(`- **ROI:** ${s.roi.toFixed(2)}`);
    lines.push(`- **Estimate:** ${s.estimate.display} (${s.estimate.hours}h)`);
    lines.push(`- **Risk:** ${s.risk}`);
    if (s.technical_description) lines.push(`- **Description:** ${s.technical_description}`);
    lines.push("");
  });
  lines.push(`---`);
  lines.push(`*Generated by AI Software Architect (demo mode)*`);
  return {
    content: lines.join("\n"),
    contentType: "text/markdown",
    filename: `${repo.owner}-${repo.name}-report.md`,
  };
}
