/**
 * Faz 0 — Determinizm garantisi: aynı girdi → aynı çıktı.
 * Evidence içeriği, sıralaması ve cap kesimi iki koşu arasında birebir aynı
 * olmalıdır (yalnızca id ve analyzed_at gibi zaman/kimlik alanları hariç).
 */
import { describe, it, expect } from "vitest";
import { analyzeLocalFiles } from "../src/lib/local-analysis";

const REPO = [
  // Not: secret değerleri parçalı yazıldı — bu test dosyası kalite'nin kendi
  // analizinde gerçek secret gibi tespit edilmesin (skor golden'ı korunur).
  { path: "src/app.ts", content: `const apiKey = "sk-" + "abcdefghijklmnopqrstuvwxyz123456";\n` },
  { path: "src/run.py", content: `import os\nos.system(user_input)\nos.system(f"ls {x}")\n` },
  { path: "src/big.ts", content: Array.from({ length: 620 }, (_, i) => `const v${i} = ${i};\n`).join("") },
  { path: "src/long.go", content: `package main\nfunc longFn() {\n${Array.from({ length: 60 }, (_, i) => `\tv${i} := ${i}\n`).join("")}}\n` },
  { path: "src/deep.rb", content: `def deep\n  if a\n    if b\n      if c\n        if d\n          if e\n            if f\n              puts "x"\n            end\n          end\n        end\n      end\n    end\n  end\nend\n` },
  { path: "src/empty.js", content: `try { risky(); } catch {}\n` },
];

function stripNonDeterministic(evidence: any[]) {
  return evidence.map((e: any) => {
    const { id, ...rest } = e;
    return rest;
  });
}

describe("Determinizm — aynı repo 2× analiz", () => {
  it("rawEvidence içerik + sıralama birebir aynı", async () => {
    const files = REPO.map((f) => new File([f.content], f.path, { type: "text/plain" }));
    const scan1 = await analyzeLocalFiles(files);
    const scan2 = await analyzeLocalFiles(files);

    const e1 = stripNonDeterministic(scan1.rawEvidence);
    const e2 = stripNonDeterministic(scan2.rawEvidence);
    expect(e1).toEqual(e2);
    expect(e1.length).toBeGreaterThan(0);
  });

  it("cap'lenmiş evidence sırası birebir aynı (severity sıralama deterministik)", async () => {
    const files = REPO.map((f) => new File([f.content], f.path, { type: "text/plain" }));
    const scan1 = await analyzeLocalFiles(files);
    const scan2 = await analyzeLocalFiles(files);

    const c1 = stripNonDeterministic(scan1.evidence);
    const c2 = stripNonDeterministic(scan2.evidence);
    expect(c1).toEqual(c2);
  });

  it("dosya listesi sırası birebir aynı", async () => {
    const files = REPO.map((f) => new File([f.content], f.path, { type: "text/plain" }));
    const scan1 = await analyzeLocalFiles(files);
    const scan2 = await analyzeLocalFiles(files);
    expect(scan1.files).toEqual(scan2.files);
  });
});
