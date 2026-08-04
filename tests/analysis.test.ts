/**
 * Sentinel testler: her analizör için gerçek bulgu (doğru pozitif) ve
 * yanlış pozitif çiftleri. Dil bağımsızlığı burada kanıtlanır.
 */
import { describe, it, expect } from "vitest";
import { scanRepo, evidenceIn, categoriesOf } from "./helpers";
import { shouldSkip, parseGitignore } from "../src/lib/local-analysis";

// ---------------------------------------------------------------------------
// Uzun fonksiyon tarayıcısı
// ---------------------------------------------------------------------------
describe("long_function tarayıcı", () => {
  it("TS'te gerçek 60 satırlık fonksiyonu yakalar", async () => {
    const lines = ["function longFn() {"];
    for (let i = 0; i < 60; i++) lines.push(`  const v${i} = ${i};`);
    lines.push("  return 0;\n}");
    const scan = await scanRepo([{ path: "src/app.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "long_function").length).toBeGreaterThan(0);
  });

  it("Python'da MODÜL seviyesindeki büyük dict yanlış pozitif üretmez (brace aşaması devre dışı)", async () => {
    const lines: string[] = [];
    lines.push("def short():\n");
    lines.push("    return CONFIG[\"key_0\"]\n");
    lines.push("\n");
    lines.push("CONFIG = {\n");
    for (let i = 0; i < 60; i++) lines.push(`    "key_${i}": "value",\n`);
    lines.push("}\n");
    const scan = await scanRepo([{ path: "py/module_dict.py", content: lines.join("") }]);
    expect(evidenceIn(scan, "long_function")).toHaveLength(0);
  });

  it("Python'da gerçek 60 satırlık fonksiyonu indentation ile yakalar", async () => {
    const lines = ["def real_long():"];
    for (let i = 0; i < 60; i++) lines.push(`    step_${i} = process(${i})`);
    lines.push("    return step_59");
    const scan = await scanRepo([{ path: "py/real_long.py", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "long_function")).toHaveLength(1);
  });

  it("Go fonksiyonunu yakalar", async () => {
    const lines = ["func longFn() {"];
    for (let i = 0; i < 60; i++) lines.push(`\tv${i} := ${i}`);
    lines.push("}\n");
    const scan = await scanRepo([{ path: "go/main.go", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "long_function")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Döngüsel bağımlılık tarayıcısı
// ---------------------------------------------------------------------------
describe("circular_dependency tarayıcı", () => {
  it("Gerçek A→B→A döngüsünü yakalar", async () => {
    const scan = await scanRepo([
      { path: "src/a.ts", content: 'import { b } from "./b";\nexport const a = 1;\n' },
      { path: "src/b.ts", content: 'import { a } from "./a";\nexport const b = 2;\n' },
    ]);
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(2);
  });

  it("Aynı base ad (route.ts x4) sahte döngü üretmez", async () => {
    const scan = await scanRepo([
      { path: "src/app/api/analyze-local/route.ts", content: 'import { jobStore } from "../analyze/route";\nexport const x = jobStore;\n' },
      { path: "src/app/api/report/route.ts", content: 'import { jobStore } from "../analyze/route";\nexport const y = jobStore;\n' },
      { path: "src/app/api/result/[id]/route.ts", content: 'import { RESULTS_DIR } from "@/lib/analysis-store";\nexport const z = RESULTS_DIR;\n' },
      { path: "src/app/api/analyze/route.ts", content: 'import { clone } from "@/lib/real-analysis-engine";\nexport const c = clone;\n' },
      { path: "src/lib/analysis-store.ts", content: 'export const RESULTS_DIR = "db";\n' },
      { path: "src/lib/real-analysis-engine.ts", content: 'export function clone() { return 1; }\n' },
    ]);
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(0);
  });

  it("NPM paket adı yerel dosya adıyla çakışınca sahte döngü üretmez", async () => {
    const scan = await scanRepo([
      { path: "src/components/ui/input-otp.tsx", content: 'import { OTPInput } from "input-otp";\nexport const O = OTPInput;\n' },
      { path: "src/components/ui/sonner.tsx", content: 'import { Toaster as Sonner } from "sonner";\nexport const T = Sonner;\n' },
      { path: "src/lib/utils.ts", content: 'export function cn(...x: any[]) { return x.join(" "); }\n' },
    ]);
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(0);
  });

  it("@/ alias ile gerçek döngüyü yakalar", async () => {
    const scan = await scanRepo([
      { path: "src/consumer.ts", content: 'import { helper } from "@/lib/helper";\nexport const x = helper();\n' },
      { path: "src/lib/helper.ts", content: 'import { consumer } from "@/consumer";\nexport function helper() { return consumer; }\n' },
    ]);
    expect(evidenceIn(scan, "circular_dependency")).toContain("src/consumer.ts");
  });

  it("JSDoc yorumundaki from './x' ifadesi sahte döngü üretmez (Hedeflerim dersi)", async () => {
    // seed.js gerçek import içermez; yalnızca JSDoc kullanım örneğinde
    // "import { seed } from './seed.js'" yazar — yorum maskelenmeli.
    const scan = await scanRepo([
      {
        path: "test/e2e/seed.js",
        content: [
          "/**",
          " * Kullanım:",
          " *   import { seedTestData, clearTestData } from './seed.js';",
          " *   await seedTestData(page);",
          " */",
          "export async function seedTestData(page) { return page; }",
          "export async function clearTestData(page) { return page; }",
        ].join("\n"),
      },
      {
        path: "test/e2e/visual.spec.js",
        content: 'import { test } from "@playwright/test";\nimport { seedTestData } from "./seed.js";\n',
      },
    ]);
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(0);
  });

  it("// yorum satırındaki import ifadesi sahte döngü üretmez", async () => {
    const scan = await scanRepo([
      { path: "src/a.ts", content: '// import { b } from "./b";\nexport const a = 1;\n' },
      { path: "src/b.ts", content: 'import { a } from "./a";\nexport const b = 2;\n' },
    ]);
    // b.ts → a.ts var ama a.ts b.ts'i GERÇEKTE import etmiyor → döngü yok.
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(0);
  });

  it("Python # yorumundaki import ifadesi sahte döngü üretmez", async () => {
    const scan = await scanRepo([
      { path: "src/a.py", content: '# from b import x\nx = 1\n' },
      { path: "src/b.py", content: "from a import x\ny = 2\n" },
    ]);
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(0);
  });

  it("Self-import (A→A) döngüsel bağımlılık sayılmaz", async () => {
    const scan = await scanRepo([
      { path: "src/self.js", content: 'import { helper } from "./self.js";\nexport const helper = 1;\n' },
    ]);
    // Kendine import gerçek bir döngü değildir (iki ayrı modül arası bağımlılık gerekir).
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Secret tarayıcı
// ---------------------------------------------------------------------------
describe("hardcoded_secret tarayıcı", () => {
  // Test içindeki literal'ler gerçek secret formatı oluşturmamalı (test dosyası
  // analiz edildiğinde yanlış pozitif üretir) — parça parça birleştirilir.
  const SK = "sk-" + "abc1234567890abcdefghijklmnop";
  const GHP = "ghp_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456";
  const AKIA = "AKIA" + "ZKZNZRNTTGF4D6KQ";
  const JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0" + ".some-signature";

  it("Gerçek secret formatlarını yakalar", async () => {
    const scan = await scanRepo([
      { path: "src/keys.ts", content: `const key = '${SK}';\n` },
      { path: "src/gh.ts", content: `const token = '${GHP}';\n` },
      { path: "src/aws.ts", content: `const ak = '${AKIA}';\n` },
      { path: "src/jwt.ts", content: `const jwt = '${JWT}';\n` },
    ]);
    expect(evidenceIn(scan, "hardcoded_secret")).toHaveLength(4);
  });

  it("Masum değerleri (test/example/demo/placeholder) yakalamaz", async () => {
    const scan = await scanRepo([
      { path: "tests/config.ts", content: "const key = 'sk-test-account-1234567890abcdefghijklmnop';\n" },
      { path: "docs/api.md", content: "Use format: 'AKIAIOSFODNN7EXAMPLE' as sample.\n" },
      { path: "src/demo.ts", content: "const password = 'demo-password-12345678901234567890';\n" },
      { path: "src/template.ts", content: "const api_key = 'your-api-key-here-1234567890123456';\n" },
    ]);
    expect(evidenceIn(scan, "hardcoded_secret")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Test tespiti
// ---------------------------------------------------------------------------
describe("hasTests tespiti", () => {
  it("8 dil konvansiyonunu tanır", async () => {
    const scan = await scanRepo([
      { path: "tests/test_a.py", content: "def test_x(): pass\n" },
      { path: "src/helper_test.py", content: "def helper_test(): pass\n" },
      { path: "src/__tests__/a.test.ts", content: "test('x', () => {});\n" },
      { path: "src/a.spec.ts", content: "test('x', () => {});\n" },
      { path: "tests/unit/conftest.py", content: "import pytest\n" },
      { path: "spec/some_spec.rb", content: "RSpec.describe 'x' do; end\n" },
      { path: "src/foo.test.js", content: "it('x', () => {});\n" },
    ]);
    expect(scan.hasTests).toBe(true);
  });

  it("latest/contest/protest gibi yanlış pozitifleri tanımaz", async () => {
    const scan = await scanRepo([
      { path: "src/latest.ts", content: "export const x = 1;\n" },
      { path: "src/contest.ts", content: "export const y = 2;\n" },
      { path: "src/protest.ts", content: "export const z = 3;\n" },
      { path: "src/protect.ts", content: "export const w = 4;\n" },
    ]);
    expect(scan.hasTests).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// God class tarayıcı
// ---------------------------------------------------------------------------
describe("god_class tarayıcı", () => {
  it("25 metodlu sınıfı yakalar", async () => {
    const lines = ["class HugeService {"];
    for (let i = 0; i < 25; i++) lines.push(`  method${i}() { return ${i}; }`);
    lines.push("}");
    const scan = await scanRepo([{ path: "src/huge.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "god_class")).toHaveLength(1);
  });

  it("5 metodlu sınıfı yakalamaz", async () => {
    const lines = ["class SmallService {"];
    for (let i = 0; i < 5; i++) lines.push(`  method${i}() { return ${i}; }`);
    lines.push("}");
    const scan = await scanRepo([{ path: "src/small.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "god_class")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// shouldSkip / parseGitignore
// ---------------------------------------------------------------------------
describe("shouldSkip evrenselliği", () => {
  it("Evrensel klasörleri skip eder", () => {
    expect(shouldSkip("kalite/node_modules/x.js")).toBe(true);
    expect(shouldSkip("kalite/dist/bundle.js")).toBe(true);
    expect(shouldSkip("kalite/.venv/bin/python")).toBe(true);
    expect(shouldSkip("kalite/build/out.css")).toBe(true);
    expect(shouldSkip("kalite/coverage/lcov.info")).toBe(true);
  });

  it("Gerçek kod klasörlerini skip ETMEZ", () => {
    expect(shouldSkip("kalite/src/app/page.tsx")).toBe(false);
    expect(shouldSkip("kalite/benchmarks/perf.go")).toBe(false); // benchmarks artık evrensel değil!
    expect(shouldSkip("kalite/download/manual.md")).toBe(false); // download artık evrensel değil!
    expect(shouldSkip("kalite/db/migrations/001.sql")).toBe(false);
    expect(shouldSkip("kalite/src/tests/unit/test_x.py")).toBe(false);
  });

  it("Kök .gitignore segmentlerine saygı duyar", () => {
    const gi = parseGitignore("# dev data\n/benchmarks/\n/validation_results/\ndownload/\n");
    expect(shouldSkip("kalite/benchmarks/security-bad/app.py", gi)).toBe(true);
    expect(shouldSkip("kalite/validation_results/out.json", gi)).toBe(true);
    expect(shouldSkip("kalite/download/notes.txt", gi)).toBe(true);
    expect(shouldSkip("kalite/src/app/page.tsx", gi)).toBe(false);
  });

  it("Glob desenleri güvenle atlanır (yanlış skip üretmez)", () => {
    const gi = parseGitignore("*.log\n/tmp/**\n!keep.txt\n");
    expect(gi.size).toBe(0);
  });

  it("Çok parçalı desen prefix'li yolda ardışık segment olarak eşleşir", () => {
    const gi = parseGitignore("/audit/.work/\n");
    // Prefix'li yol (webkitRelativePath üst klasör adıyla gelir)
    expect(shouldSkip("kalite/audit/.work/command_injection-x/src/main.ts", gi)).toBe(true);
    // Prefix'siz yol
    expect(shouldSkip("audit/.work/weak_crypto-go-single/src/main.go", gi)).toBe(true);
    // Tam eşleşme de skip
    expect(shouldSkip("audit/.work", gi)).toBe(true);
    // Benzer ama farklı dizinler skip EDİLMEZ (segment sınırı korunur)
    expect(shouldSkip("kalite/my-audit/.work/notes.txt", gi)).toBe(false);
    expect(shouldSkip("kalite/audit/run.mjs", gi)).toBe(false);
    expect(shouldSkip("kalite/src/app/page.tsx", gi)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Kategori sayımı — cap sonrası ve ham veri
// ---------------------------------------------------------------------------
describe("evidence cap", () => {
  it("Aynı dosyada secret + large_file: ham listede ikisi de var", async () => {
    const big = [`const apiKey = '${"sk-" + "abc1234567890abcdefghijklmnop"}';\n`];
    for (let i = 0; i < 620; i++) big.push(`const v${i} = ${i};\n`);
    const scan = await scanRepo([{ path: "app.py", content: big.join("") }]);
    const cats = categoriesOf(scan);
    expect(cats.hardcoded_secret).toBe(1);
    expect(cats.large_file).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// 3+ seviye döngüsel bağımlılık (FN kapatma)
// ---------------------------------------------------------------------------
describe("circular_dependency — 3+ seviye", () => {
  it("A→B→C→A döngüsü tespit edilir", async () => {
    const scan = await scanRepo([
      { path: "src/a.ts", content: `import { b } from "./b";\nexport const a = b;\n` },
      { path: "src/b.ts", content: `import { c } from "./c";\nexport const b = c;\n` },
      { path: "src/c.ts", content: `import { a } from "./a";\nexport const c = a;\n` },
    ]);
    const cats = categoriesOf(scan);
    expect(cats.circular_dependency).toBeGreaterThan(0);
  });

  it("A→B→C ayrık zincir döngü DEĞİLDİR", async () => {
    const scan = await scanRepo([
      { path: "src/a.ts", content: `import { b } from "./b";\nexport const a = b;\n` },
      { path: "src/b.ts", content: `import { c } from "./c";\nexport const b = c;\n` },
      { path: "src/c.ts", content: `export const c = 1;\n` },
    ]);
    const cats = categoriesOf(scan);
    expect(cats.circular_dependency || 0).toBe(0);
  });

  it("Kendine import (A→A) döngü DEĞİLDİR", async () => {
    const scan = await scanRepo([
      { path: "src/a.ts", content: `import { a } from "./a";\nexport const a = 1;\n` },
    ]);
    const cats = categoriesOf(scan);
    expect(cats.circular_dependency || 0).toBe(0);
  });
});
