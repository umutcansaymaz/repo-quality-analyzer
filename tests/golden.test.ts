/**
 * Golden dataset: beklenen/istenmeyen bulgu matrisi.
 * Her değişiklikte bu testler, motorun bilinen senaryolarda yanlış pozitif
 * üretmediğini ve gerçek bulguları kaçırmadığını doğrular (regresyon güvencesi).
 */
import { describe, it, expect } from "vitest";
import { scanRepo, categoriesOf } from "./helpers";

interface GoldenCase {
  name: string;
  files: { path: string; content: string }[];
  expect: Record<string, number>;
  notExpect: string[];
}

const GOLDEN: GoldenCase[] = [
  {
    name: "ts-secret-in-code",
    files: [{ path: "src/keys.ts", content: "const apiKey = 'sk-" + "abc1234567890abcdefghijklmnop';\n" }],
    expect: { hardcoded_secret: 1 },
    notExpect: ["command_injection"],
  },
  {
    name: "ts-secret-doc-mention",
    files: [{ path: "docs/api.md", content: "Use format: 'AKIAIOSFODNN7EXAMPLE' as sample.\n" }],
    expect: {},
    notExpect: ["hardcoded_secret"],
  },
  {
    name: "python-injection",
    files: [{ path: "src/run.py", content: "import os\nos.system(user_input)\n" }],
    expect: { command_injection: 1 },
    notExpect: ["hardcoded_secret"],
  },
  {
    name: "python-weak-crypto",
    files: [{ path: "src/hash.py", content: "import hashlib\nh = hashlib.md5(data)\n" }],
    expect: { weak_crypto: 1 },
    notExpect: ["command_injection"],
  },
  {
    name: "python-clean",
    files: [
      { path: "src/app.py", content: "def main():\n    return 1\n" },
      { path: "tests/test_app.py", content: "def test_main():\n    assert main() == 1\n" },
    ],
    expect: {},
    notExpect: ["hardcoded_secret", "command_injection", "weak_crypto", "empty_handler"],
  },
  {
    name: "ts-complex-function",
    files: [
      {
        path: "src/complex.ts",
        content: "function big() {\n" + Array.from({ length: 30 }, (_, i) => `  if (x${i} > ${i}) { y += ${i}; }`).join("\n") + "\n  return y;\n}\n",
      },
    ],
    expect: { high_complexity: 1 },
    notExpect: ["hardcoded_secret"],
  },
  {
    name: "ts-deep-nesting",
    files: [
      {
        path: "src/deep.ts",
        content: "function deep() {\n" + Array.from({ length: 7 }, (_, i) => `${"  ".repeat(i + 1)}if (a${i}) {`).join("\n") + "\n" + Array.from({ length: 7 }, (_, i) => `${"  ".repeat(7 - i)}}`).join("\n") + "\n}\n",
      },
    ],
    expect: { deep_nesting: 1 },
    notExpect: ["high_complexity"],
  },
  {
    name: "ts-empty-handler",
    files: [{ path: "src/e.ts", content: "try { risky(); } catch {}\n" }],
    expect: { empty_handler: 1 },
    notExpect: ["hardcoded_secret"],
  },
  {
    name: "ts-regex-exec-no-false-positive",
    files: [{ path: "src/re.ts", content: "const m = /ab+c/.exec(text);\n" }],
    expect: {},
    notExpect: ["command_injection"],
  },
  {
    name: "ts-comment-exec-no-false-positive",
    files: [{ path: "src/c.ts", content: "// exec(userInput) is dangerous\nexport const x = 1;\n" }],
    expect: {},
    notExpect: ["command_injection"],
  },
  {
    name: "go-simple-func",
    files: [
      { path: "src/main.go", content: "package main\n\nfunc add(a, b int) int {\n\treturn a + b\n}\n" },
      { path: "src/main_test.go", content: "package main\n\nimport \"testing\"\n\nfunc TestAdd(t *testing.T) {\n\tif add(1, 2) != 3 { t.Error(\"fail\") }\n}\n" },
    ],
    expect: {},
    notExpect: ["hardcoded_secret", "command_injection"],
  },
  {
    name: "ruby-long-def",
    files: [
      {
        path: "src/long.rb",
        content: "def long_method\n" + Array.from({ length: 55 }, (_, i) => `  puts ${i}`).join("\n") + "\nend\n",
      },
    ],
    expect: { long_function: 1 },
    notExpect: ["hardcoded_secret"],
  },
];

describe("Golden dataset — beklenen bulgular", () => {
  for (const g of GOLDEN) {
    it(`${g.name}: beklenen bulgular üretilir, yanlış pozitif yok`, async () => {
      const scan = await scanRepo(g.files);
      const cats = categoriesOf(scan);
      for (const [cat, count] of Object.entries(g.expect)) {
        expect(cats[cat] ?? 0, `${cat} bekleniyordu`).toBe(count);
      }
      for (const cat of g.notExpect) {
        expect(cats[cat] ?? 0, `${cat} üretilmemeliydi`).toBe(0);
      }
    });
  }
});

// Doğrulama durumu + kanıt şeffaflığı
describe("Doğrulama ve kanıt", () => {
  it("hardcoded_secret → verified + evidence_snippet içerir", async () => {
    const scan = await scanRepo([{ path: "src/keys.ts", content: "const k = 'sk-" + "abc1234567890abcdefghijklmnop';\n" }]);
    const ev = scan.rawEvidence.find((e) => e.category === "hardcoded_secret");
    expect(ev).toBeDefined();
    expect(ev?.validation_status).toBe("verified");
    expect(ev?.validated_by?.length).toBeGreaterThan(1);
    expect(ev?.evidence_snippet).toContain("sk-");
    expect(ev?.line).toBe(1);
  });

  it("Kaynak kod snippet'i + line her kategori için üretilir", async () => {
    const scan = await scanRepo([
      { path: "src/run.py", content: "import os\nos.system(cmd)\n" },
      { path: "src/e.ts", content: "try { x(); } catch {}\n" },
    ]);
    for (const e of scan.rawEvidence) {
      expect(e.evidence_snippet, `${e.category} snippet olmalı`).toBeTruthy();
      expect(typeof e.line).toBe("number");
    }
  });

  it("statsForEvidence: passed/warning/failed gerçek dağılımı yansıtır", async () => {
    const { buildLocalReport } = await import("../src/lib/local-analysis");
    const scan = await scanRepo([{ path: "src/keys.ts", content: "const k = 'sk-" + "abc1234567890abcdefghijklmnop';\n" }]);
    const report = buildLocalReport(scan, "test", { useLLM: false });
    const stats = report.evidence.statistics;
    expect(stats.passed).toBeGreaterThanOrEqual(1);
    expect(stats.passed + stats.warning + stats.failed).toBe(stats.total_evidence);
  });

  it("Root cause validation: gerçek konsensüs bilgisi taşır", async () => {
    const { buildLocalReport } = await import("../src/lib/local-analysis");
    const scan = await scanRepo([
      { path: "src/keys.ts", content: `const k = '${"sk-" + "abc1234567890abcdefghijklmnop"}';\n` },
      { path: "src/ok.ts", content: "export const x = 1;\n" },
    ]);
    const report = buildLocalReport(scan, "test", { useLLM: false });
    const rc = report.root_causes.root_causes.find((r: any) => r.category === "security");
    expect(rc).toBeDefined();
    expect(rc.verified_evidence).toBeGreaterThanOrEqual(1);
    const validation = report.root_causes.validation[rc.id];
    expect(validation.analyzer_consensus).toBeGreaterThanOrEqual(1);
  });

  it("Claim verification: gerçek doğrulama durumlarını yansıtır (verified/opinion/rejected)", async () => {
    const { buildLocalReport } = await import("../src/lib/local-analysis");
    // Yüksek entropy'li gerçek secret → verified claim
    const scanVerified = await scanRepo([
      { path: "src/keys.ts", content: `const k = '${"sk-" + "abc1234567890abcdefghijklmnop"}';\n` },
      { path: "src/ok.ts", content: "export const x = 1;\n" },
    ]);
    const reportVerified = buildLocalReport(scanVerified, "test", { useLLM: false });
    const cv1 = reportVerified.engineering_review.claim_verification;
    expect(cv1.verified).toBeGreaterThanOrEqual(1);
    expect(cv1.verified + cv1.opinion + cv1.rejected).toBe(cv1.total_claims);

    // Düşük entropy'li (tekrar eden) secret → partial evidence → opinion claim
    const scanPartial = await scanRepo([
      { path: "src/keys.ts", content: `const k = '${"sk-" + "aaaaaaaaaaaaaaaaaaaaaaaa"}';\n` },
      { path: "src/ok.ts", content: "export const x = 1;\n" },
    ]);
    const reportPartial = buildLocalReport(scanPartial, "test", { useLLM: false });
    const cv2 = reportPartial.engineering_review.claim_verification;
    expect(cv2.opinion + cv2.rejected).toBeGreaterThanOrEqual(1);
    // Her claim'in text/status/evidence_ids alanları dolu
    for (const c of cv2.claims) {
      expect(c.text).toBeTruthy();
      expect(["verified", "opinion", "rejected"]).toContain(c.status);
      expect(Array.isArray(c.evidence_ids)).toBe(true);
    }
  });

  it("Knowledge graph: mimari bulgular dependency node'ları üretir (pipeline fazı)", async () => {
    const { buildLocalReport } = await import("../src/lib/local-analysis");
    // Sıkı bağlılık üreten repo: çok sayıda import içeren dosya
    const imports: string[] = [];
    for (let i = 0; i < 20; i++) imports.push(`import { a${i} } from "./mod${i}";`);
    const complexLines = ["function big() {"];
    for (let i = 0; i < 30; i++) complexLines.push(`  if (x${i} > ${i}) { y += ${i}; }`);
    complexLines.push("  return y;", "}");
    const scan = await scanRepo([
      { path: "src/hub.ts", content: imports.join("\n") + "\nexport const hub = 1;\n" },
      { path: "src/complex.ts", content: complexLines.join("\n") },
      ...Array.from({ length: 20 }, (_, i) => ({ path: `src/mod${i}.ts`, content: `export const a${i} = ${i};\n` })),
    ]);
    const report = buildLocalReport(scan, "test", { useLLM: false });
    const depNodes = report.knowledge_graph.nodes.filter((n: any) => n.node_type === "dependency");
    expect(depNodes.length).toBeGreaterThan(0);
    // Pipeline faz kontrolü UI ile aynı mantıkla
    const dependencyPhase = report.knowledge_graph.nodes.some((n: any) => n.node_type === "dependency");
    expect(dependencyPhase).toBe(true);
    const metricsPhase = report.evidence.evidence.some((e: any) => ["metric", "complexity"].includes(e.finding_type));
    expect(metricsPhase).toBe(true);
  });
});
