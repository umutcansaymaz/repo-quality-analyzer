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
  it.skipIf(!existsSync(TUSLA))("67.1 skor, 1 Firebase secret medium, 0 komut enjeksiyonu", async () => {
    const report = await scanDir(TUSLA, "TUSLA");
    const hs = report.ai_review.health_score;
    expect(hs.overall).toBeGreaterThanOrEqual(66.1);
    expect(hs.overall).toBeLessThanOrEqual(68.1);

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
    "80.2 skor ve 0 komut enjeksiyonu FP'si (kendi motoru dahil)",
    async () => {
      const report = await scanDir(KALITE, "kalite");
      const hs = report.ai_review.health_score;
      expect(hs.overall).toBeGreaterThanOrEqual(79.2);
      expect(hs.overall).toBeLessThanOrEqual(81.2);

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

// ---------------------------------------------------------------------------
// Go + Java gerçek repo golden'ları (fixtures/repos — klonlanmış gerçek projeler)
// ---------------------------------------------------------------------------
const GO_REPO = process.cwd().replace(/\\/g, "/") + "/tests/fixtures/repos/go-sample";
const JAVA_REPO = process.cwd().replace(/\\/g, "/") + "/tests/fixtures/repos/java-sample";
const PY_REPO = process.cwd().replace(/\\/g, "/") + "/tests/fixtures/repos/py-sample";
const RB_REPO = process.cwd().replace(/\\/g, "/") + "/tests/fixtures/repos/rb-sample";

describe("Gerçek-dünya golden — Go (gorilla/mux)", () => {
  it.skipIf(!existsSync(GO_REPO + "/mux.go"))(
    "74.7 skor, 0 secret, 0 komut enjeksiyonu, markdown bulgusu yok",
    async () => {
      const report = await scanDir(GO_REPO, "go-sample");
      const hs = report.ai_review.health_score;
      expect(hs.overall).toBeGreaterThanOrEqual(73.7);
      expect(hs.overall).toBeLessThanOrEqual(75.7);

      const ev = report.evidence.evidence;
      expect(ev.filter((e: any) => e.category === "hardcoded_secret")).toHaveLength(0);
      expect(ev.filter((e: any) => e.category === "command_injection")).toHaveLength(0);
      // Markdown/JSON gibi kod dışı dosyalarda yapısal bulgu üretilmemeli
      expect(ev.filter((e: any) => e.file_path.endsWith(".md"))).toHaveLength(0);
    }
  );
});

describe("Gerçek-dünya golden — Java (square/javapoet)", () => {
  it.skipIf(!existsSync(JAVA_REPO + "/pom.xml"))(
    "65.6 skor, 0 secret, 0 komut enjeksiyonu, markdown bulgusu yok",
    async () => {
      const report = await scanDir(JAVA_REPO, "java-sample");
      const hs = report.ai_review.health_score;
      expect(hs.overall).toBeGreaterThanOrEqual(64.6);
      expect(hs.overall).toBeLessThanOrEqual(66.6);

      const ev = report.evidence.evidence;
      expect(ev.filter((e: any) => e.category === "hardcoded_secret")).toHaveLength(0);
      expect(ev.filter((e: any) => e.category === "command_injection")).toHaveLength(0);
      expect(ev.filter((e: any) => e.file_path.endsWith(".md"))).toHaveLength(0);
    }
  );
});

describe("Gerçek-dünya golden — Python (pallets/click)", () => {
  it.skipIf(!existsSync(PY_REPO + "/src/click/core.py"))(
    "68.8 skor, 0 secret, 0 komut enjeksiyonu, markdown bulgusu yok",
    async () => {
      const report = await scanDir(PY_REPO, "py-sample");
      const hs = report.ai_review.health_score;
      expect(hs.overall).toBeGreaterThanOrEqual(67.8);
      expect(hs.overall).toBeLessThanOrEqual(69.8);

      const ev = report.evidence.evidence;
      expect(ev.filter((e: any) => e.category === "hardcoded_secret")).toHaveLength(0);
      expect(ev.filter((e: any) => e.category === "command_injection")).toHaveLength(0);
      expect(ev.filter((e: any) => e.file_path.endsWith(".md"))).toHaveLength(0);
    }
  );
});

describe("Gerçek-dünya golden — Ruby (jnunemaker/httparty)", () => {
  it.skipIf(!existsSync(RB_REPO + "/lib/httparty.rb"))(
    "66.8 skor, 0 secret, 0 komut enjeksiyonu, markdown bulgusu yok",
    async () => {
      const report = await scanDir(RB_REPO, "rb-sample");
      const hs = report.ai_review.health_score;
      expect(hs.overall).toBeGreaterThanOrEqual(65.8);
      expect(hs.overall).toBeLessThanOrEqual(67.8);

      const ev = report.evidence.evidence;
      expect(ev.filter((e: any) => e.category === "hardcoded_secret")).toHaveLength(0);
      expect(ev.filter((e: any) => e.category === "command_injection")).toHaveLength(0);
      expect(ev.filter((e: any) => e.file_path.endsWith(".md"))).toHaveLength(0);
    }
  );
});
