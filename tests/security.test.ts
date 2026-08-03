/**
 * Aşama C: Güvenlik derinliği — command_injection + weak_crypto.
 * Aşama D: Assertion yoğunluğu → testing skoru.
 */
import { describe, it, expect } from "vitest";
import { scanRepo, evidenceIn } from "./helpers";
import { buildLocalReport } from "../src/lib/local-analysis";

// ---------------------------------------------------------------------------
// C1: command_injection
// ---------------------------------------------------------------------------
describe("C1 — command_injection", () => {
  it("Python exec() → VAR", async () => {
    const scan = await scanRepo([{ path: "src/run.py", content: "exec(user_input)\n" }]);
    expect(evidenceIn(scan, "command_injection")).toHaveLength(1);
  });

  it("Python os.system() → VAR", async () => {
    const scan = await scanRepo([{ path: "src/run.py", content: "import os\nos.system(cmd)\n" }]);
    expect(evidenceIn(scan, "command_injection")).toHaveLength(1);
  });

  it("Python subprocess shell=True → VAR", async () => {
    const scan = await scanRepo([{ path: "src/run.py", content: "import subprocess\nsubprocess.run(cmd, shell=True)\n" }]);
    expect(evidenceIn(scan, "command_injection")).toHaveLength(1);
  });

  it("Java Runtime.exec() → VAR", async () => {
    const scan = await scanRepo([{ path: "src/Run.java", content: "Runtime.getRuntime().exec(cmd);\n" }]);
    expect(evidenceIn(scan, "command_injection")).toHaveLength(1);
  });

  it("Node execSync → VAR", async () => {
    const scan = await scanRepo([{ path: "src/run.js", content: "const { execSync } = require('child_process');\nexecSync(cmd);\n" }]);
    expect(evidenceIn(scan, "command_injection")).toHaveLength(1);
  });

  it("Yorum içindeki exec( → YOK", async () => {
    const scan = await scanRepo([{ path: "src/run.py", content: "# exec(user_input) is dangerous\nx = 1\n" }]);
    expect(evidenceIn(scan, "command_injection")).toHaveLength(0);
  });

  it("String içindeki exec( → YOK", async () => {
    const scan = await scanRepo([{ path: "src/run.ts", content: 'const doc = "exec(something) here";\n' }]);
    expect(evidenceIn(scan, "command_injection")).toHaveLength(0);
  });

  it("Test dosyasındaki exec → severity medium (mock kullanımı)", async () => {
    const scan = await scanRepo([{ path: "src/__tests__/run.test.ts", content: "exec('ls');\n" }]);
    const ev = scan.rawEvidence.find((e) => e.category === "command_injection");
    expect(ev).toBeDefined();
    expect(ev?.severity).toBe("medium");
  });
});

// ---------------------------------------------------------------------------
// C2: weak_crypto
// ---------------------------------------------------------------------------
describe("C2 — weak_crypto", () => {
  it("Python hashlib.md5 → VAR", async () => {
    const scan = await scanRepo([{ path: "src/h.py", content: "import hashlib\nhashlib.md5(data)\n" }]);
    expect(evidenceIn(scan, "weak_crypto")).toHaveLength(1);
  });

  it("Node createHash('md5') → VAR", async () => {
    const scan = await scanRepo([{ path: "src/h.js", content: "crypto.createHash('md5').update(x)\n" }]);
    expect(evidenceIn(scan, "weak_crypto")).toHaveLength(1);
  });

  it("Java MessageDigest MD5 → VAR", async () => {
    const scan = await scanRepo([{ path: "src/H.java", content: "MessageDigest.getInstance(\"MD5\")\n" }]);
    expect(evidenceIn(scan, "weak_crypto")).toHaveLength(1);
  });

  it("sha256 → YOK", async () => {
    const scan = await scanRepo([{ path: "src/h.py", content: "import hashlib\nhashlib.sha256(data)\n" }]);
    expect(evidenceIn(scan, "weak_crypto")).toHaveLength(0);
  });

  it("checksum bağlamında md5 → severity low", async () => {
    const scan = await scanRepo([{ path: "src/h.py", content: "def checksum(f):\n    return hashlib.md5(open(f,'rb').read()).hexdigest()\n" }]);
    const ev = scan.rawEvidence.find((e) => e.category === "weak_crypto");
    expect(ev).toBeDefined();
    expect(ev?.severity).toBe("low");
  });

  it("String içindeki md5( → YOK", async () => {
    const scan = await scanRepo([{ path: "src/h.ts", content: 'const doc = "use md5(...) carefully";\n' }]);
    expect(evidenceIn(scan, "weak_crypto")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Security skor entegrasyonu
// ---------------------------------------------------------------------------
describe("Security skor — C entegrasyonu", () => {
  it("command_injection bulgusu security skorunu düşürür", async () => {
    const scan = await scanRepo([
      { path: "src/run.py", content: "import os\nos.system(cmd)\n" },
      { path: "src/ok.ts", content: "export const x = 1;\n" },
    ]);
    const report = buildLocalReport(scan, "test", { useLLM: false });
    expect(report.ai_review.health_score.security).toBeLessThan(85);
  });
});

// ---------------------------------------------------------------------------
// D1: assertion yoğunluğu → testing skoru
// ---------------------------------------------------------------------------
describe("D1 — assertion yoğunluğu", () => {
  it("10 boş test dosyası → testing ≤ 70", async () => {
    const files: { path: string; content: string }[] = [
      { path: "src/package.json", content: '{"name":"a","devDependencies":{"jest":"^29"}}\n' },
    ];
    for (let i = 0; i < 10; i++) files.push({ path: `src/m${i}.ts`, content: `export const m${i} = ${i};\n` });
    for (let i = 0; i < 10; i++) files.push({ path: `src/t${i}.test.ts`, content: `import { m0 } from "./m0";\n` });
    const scan = await scanRepo(files);
    const report = buildLocalReport(scan, "test", { useLLM: false });
    expect(report.ai_review.health_score.testing).toBeLessThanOrEqual(70);
  });

  it("10 assertion'lu 10 dosya (ratio 1) → testing 80-95 arası", async () => {
    const files: { path: string; content: string }[] = [];
    for (let i = 0; i < 10; i++) files.push({ path: `src/m${i}.ts`, content: `export const m${i} = ${i};\n` });
    for (let i = 0; i < 10; i++) files.push({ path: `src/t${i}.test.ts`, content: `import { m0 } from "./m0";\ntest("x", () => { expect(m0).toBe(0); });\n` });
    const scan = await scanRepo(files);
    const report = buildLocalReport(scan, "test", { useLLM: false });
    expect(report.ai_review.health_score.testing).toBeGreaterThanOrEqual(80);
    expect(report.ai_review.health_score.testing).toBeLessThanOrEqual(95);
  });

  it("10 yoğun test dosyası (ratio 5+) → testing ≥ 85", async () => {
    const files: { path: string; content: string }[] = [];
    for (let i = 0; i < 10; i++) files.push({ path: `src/m${i}.ts`, content: `export const m${i} = ${i};\n` });
    for (let i = 0; i < 10; i++) {
      const asserts = [];
      for (let j = 0; j < 5; j++) asserts.push(`expect(m0).toBe(${j});`);
      files.push({ path: `src/t${i}.test.ts`, content: `import { m0 } from "./m0";\ntest("x", () => { ${asserts.join(" ")} });\n` });
    }
    const scan = await scanRepo(files);
    const report = buildLocalReport(scan, "test", { useLLM: false });
    expect(report.ai_review.health_score.testing).toBeGreaterThanOrEqual(85);
  });
});
