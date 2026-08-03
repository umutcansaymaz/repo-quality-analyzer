/**
 * Gerçek-dünya golden testleri — motorun bilinen gerçek repolardaki davranışını
 * kilitler. Motor değişikliği bu beklentileri bozarsa regresyon anında yakalanır.
 *
 * NOT: Bu testler makine bağımlıdır (klasör yolları). Yol yoksa test atlanır —
 * CI/başka makinede zararsız, geliştirici makinesinde koruma sağlar.
 */
import { describe, it, expect } from "vitest";
import { existsSync } from "fs";
import { analyzeLocalFiles, buildLocalReport } from "../src/lib/local-analysis";
import { generateRepos } from "../audit/generator.mjs";

const DESKTOP = "C:/Users/Umut/OneDrive/Masaüstü";
const TUSLA = `${DESKTOP}/TUSLA`;
const KALITE = process.cwd().replace(/\\/g, "/");

async function scanDir(dir: string, repoName: string) {
  const { collectFiles } = await import("../src/lib/cli");
  // cli.ts collectFiles'ı dışa aktarmıyorsa, analiz için dosyaları topla
  const files = await import("../src/lib/cli").then(async (m) => {
    if (typeof m.collectFiles === "function") return m.collectFiles(dir);
    throw new Error("collectFiles export yok");
  });
  const scan = await analyzeLocalFiles(files);
  return buildLocalReport(scan, repoName, { useLLM: false });
}

describe("Gerçek-dünya golden — TUSLA", () => {
  it.skipIf(!existsSync(TUSLA))("62.6 skor, 1 Firebase secret medium, 0 komut enjeksiyonu", async () => {
    const report = await scanDir(TUSLA, "TUSLA");
    const hs = report.ai_review.health_score;
    expect(hs.overall).toBeGreaterThanOrEqual(61.6);
    expect(hs.overall).toBeLessThanOrEqual(63.6);

    const ev = report.evidence.evidence;
    const secrets = ev.filter((e: any) => e.category === "hardcoded_secret");
    expect(secrets).toHaveLength(1);
    expect(secrets[0].severity).toBe("medium");

    const injections = ev.filter((e: any) => e.category === "command_injection");
    expect(injections).toHaveLength(0);
  });
});

describe("Gerçek-dünya golden — kalite (kendi kodu)", () => {
  it.skipIf(!existsSync(KALITE + "/src/lib/local-analysis.ts"))(
    "68.7 skor ve 0 komut enjeksiyonu FP'si (kendi motoru dahil)",
    async () => {
      const report = await scanDir(KALITE, "kalite");
      const hs = report.ai_review.health_score;
      expect(hs.overall).toBeGreaterThanOrEqual(67.7);
      expect(hs.overall).toBeLessThanOrEqual(69.7);

      const ev = report.evidence.evidence;
      const injections = ev.filter((e: any) => e.category === "command_injection");
      expect(injections).toHaveLength(0);
    }
  );
});

describe("Çoklu bulgu — aynı dosyada 3 enjeksiyon = 3 kanıt", () => {
  it("injection-multi-ts 3 ayrı kanıt üretir (ilk-bulgu saklama yok)", async () => {
    const repos = generateRepos();
    const repo = repos.find((r: any) => r.name === "injection-multi-ts");
    expect(repo).toBeDefined();
    const files = repo!.files.map(
      (f: any) => new File([f.content], f.path, { type: "text/plain" })
    );
    const scan = await analyzeLocalFiles(files);
    const injections = scan.rawEvidence.filter((e: any) => e.category === "command_injection");
    expect(injections.length).toBeGreaterThanOrEqual(3);
  });
});
