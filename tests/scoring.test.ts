/**
 * Puanlama modeli profil matrisi: her repo profili için beklenen skor aralığı.
 * Kurallar: iyi repo ≥75, kötü repo <50, ölçek bağımsız (küçük/dev benzer puan).
 */
import { describe, it, expect } from "vitest";
import { scanRepo, makeFile, type RepoFile } from "./helpers";
import { buildLocalReport, computeHealthScore } from "../src/lib/local-analysis";

function scoreOf(files: RepoFile[], repoName = "test") {
  return buildLocalReportFrom(files, repoName);
}

async function buildLocalReportFrom(files: RepoFile[], repoName: string) {
  const scan = await scanRepo(files);
  return buildLocalReport(scan, repoName, { useLLM: false }).ai_review.health_score;
}

function many(files: RepoFile[], n: number, gen: (i: number) => RepoFile): RepoFile[] {
  const out = [...files];
  for (let i = 0; i < n; i++) out.push(gen(i));
  return out;
}

describe("Skorlama — repo profilleri", () => {
  it("İyi küçük repo ≥75 (A/B)", async () => {
    const files: RepoFile[] = [
      { path: "src/package.json", content: '{"name":"app","devDependencies":{"jest":"^29"}}\n' },
      { path: "README.md", content: `# App\n\n## Install\n\`\`\`\nnpm i\n\`\`\`\n\n## Usage\n\`\`\`\napp run\n\`\`\`\n\n## API\n### GET /x\n### POST /y\n### PUT /z\n### DEL /w\n` },
      { path: ".github/workflows/ci.yml", content: "name: ci\non: push\n" },
    ];
    const withCode = many(files, 30, (i) => ({ path: `src/lib/mod${i}.ts`, content: `export function f${i}() { return ${i}; }\n` }));
    const withTests = many(withCode, 6, (i) => ({ path: `src/lib/__tests__/mod${i}.test.ts`, content: `import { f0 } from "../mod0";\ntest("x", () => expect(f0()).toBe(0));\n` }));
    const h = await scoreOf(withTests);
    expect(h.overall).toBeGreaterThanOrEqual(75);
  });

  it("Kötü repo <50 (secret + test yok + README yok + büyük dosya)", async () => {
    const big = [`const apiKey = '${"sk-" + "abc1234567890abcdefghijklmnop"}';\n`];
    for (let i = 0; i < 620; i++) big.push(`const v${i} = ${i};\n`);
    const files: RepoFile[] = [{ path: "app.py", content: big.join("") }];
    const withCode = many(files, 5, (i) => ({ path: `src/x${i}.ts`, content: `const a${i} = 1;\nconst b${i} = 2;\n` }));
    const h = await scoreOf(withCode);
    expect(h.overall).toBeLessThan(50);
    expect(h.security).toBeLessThan(70);
    expect(h.testing).toBeLessThan(40);
    expect(h.documentation).toBeLessThan(45);
  });

  it("Ölçek bağımsızlığı: 50 dosyalık temiz repo ≈ 950 dosyalık temiz repo", async () => {
    const makeClean = (n: number, testN: number): RepoFile[] => {
      const base: RepoFile[] = [
        { path: "README.md", content: `# R\n\n## A\n### 1\n### 2\n### 3\n### 4\n### 5\n\n\`\`\`\nx\n\`\`\`\n` },
        { path: "src/package.json", content: '{"name":"a","devDependencies":{"jest":"^29"}}\n' },
      ];
      const code = many(base, n, (i) => ({ path: `src/m${i}.ts`, content: `export const b${i} = ${i};\n` }));
      return many(code, testN, (i) => ({ path: `src/t${i}.test.ts`, content: `import { b0 } from "../m0";\ntest("t", () => 1);\n` }));
    };
    const small = await scoreOf(makeClean(50, 5));
    const big = await scoreOf(makeClean(950, 50));
    expect(Math.abs(small.overall - big.overall)).toBeLessThan(12);
  });

  it("Monorepo (çoklu paket) mantıklı puan üretir", async () => {
    const files: RepoFile[] = [
      { path: "packages/a/package.json", content: '{"name":"a"}\n' },
      { path: "packages/b/package.json", content: '{"name":"b"}\n' },
      { path: "README.md", content: `# Mono\n\n## A\n### 1\n### 2\n### 3\n### 4\n### 5\n\n\`\`\`\nx\n\`\`\`\n` },
    ];
    const code = many(files, 40, (i) => ({ path: `packages/a/src/m${i}.ts`, content: `export const m${i} = ${i};\n` }));
    const tests = many(code, 5, (i) => ({ path: `packages/a/src/t${i}.test.ts`, content: `test("t", () => 1);\n` }));
    const h = await scoreOf(tests);
    expect(h.overall).toBeGreaterThanOrEqual(50);
    expect(h.architecture).toBeGreaterThanOrEqual(50);
  });

  it("Docs-only repo düşük puan alır (kod yok)", async () => {
    const files: RepoFile[] = [
      { path: "README.md", content: "# Docs only repo\n" },
      { path: "docs/guide.md", content: "# Guide\n" },
    ];
    const h = await scoreOf(files);
    expect(h.overall).toBeLessThan(50);
  });

  it("Boş repo 0 puan alır", async () => {
    const h = await scoreOf([]);
    expect(h.overall).toBe(0);
  });

  it("Güvenlik kritik bulgusu overall'a sert yansır", async () => {
    const files: RepoFile[] = [
      { path: "src/keys.ts", content: `const k = '${"AKIA" + "ZKZNZRNTTGF4D6KQ"}';\n` },
      { path: "src/lib/a.ts", content: "export const x = 1;\n" },
    ];
    const h = await scoreOf(files);
    expect(h.security).toBeLessThan(70);
  });
});

describe("computeHealthScore — doğrudan", () => {
  it("Tüm boyutlar 0-100 aralığında, grade geçerli", async () => {
    const files: RepoFile[] = [
      { path: "src/a.ts", content: "export const x = 1;\n" },
      { path: "README.md", content: "# R\n" },
    ];
    const scan = await scanRepo(files);
    const s = computeHealthScore(scan);
    for (const v of [s.security, s.architecture, s.code_quality, s.testing, s.documentation, s.performance, s.developer_experience, s.scalability]) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(100);
    }
    expect(["A", "B", "C", "D", "F"]).toContain(s.grade);
  });
});

describe("makeFile helper", () => {
  it("File nesnesi üretir", () => {
    const f = makeFile("x", "src/a.ts");
    expect(f.name).toBe("src/a.ts");
  });
});
