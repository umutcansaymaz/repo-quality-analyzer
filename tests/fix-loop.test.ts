/**
 * Düzeltme döngüsü testi (Hedeflerim dersi):
 *
 * Kullanıcı beklentisi: analiz motoru bir sorun bulur → düzelt → sonraki
 * analizde bulgu KAYBOLUR + puan ARTAR. Bu döngü kalıcı olarak korunmalıdır.
 *
 * Senaryo: aynı repo'nun iki varyantı —
 *   broken:   26 dallı tek fonksiyon (eşik 25) → high_complexity + düşük skor
 *   fixed:    aynı mantık 10 dallı 3 fonksiyona bölünmüş → bulgu yok + skor yüksek
 *
 * Doğrulama: evidence diff, root cause diff, skor diff — üçü de kanıtlanır.
 */
import { describe, it, expect } from "vitest";
import { analyzeLocalFiles, buildLocalReport } from "../src/lib/local-analysis";

function makeFiles(indexJs: string): File[] {
  return [new File([indexJs], "src/index.js", { type: "text/javascript" })];
}

const brokenIndex = `export function processUser(u) { if (u.a) return 1; if (u.b) return 2; if (u.c) return 3; if (u.d) return 4; if (u.e) return 5; if (u.f) return 6; if (u.g) return 7; if (u.h) return 8; if (u.i) return 9; if (u.j) return 10; if (u.k) return 11; if (u.l) return 12; if (u.m) return 13; if (u.n) return 14; if (u.o) return 15; if (u.p) return 16; if (u.q) return 17; if (u.r) return 18; if (u.s) return 19; if (u.t) return 20; if (u.u) return 21; if (u.v) return 22; if (u.w) return 23; if (u.x) return 24; if (u.y) return 25; if (u.z) return 26; }\n`;

const fixedIndex = `export function processUser(u) { return routeA(u) || routeB(u) || routeC(u); }\nfunction routeA(u) { if (u.a) return 1; if (u.b) return 2; if (u.c) return 3; if (u.d) return 4; if (u.e) return 5; if (u.f) return 6; if (u.g) return 7; if (u.h) return 8; if (u.i) return 9; if (u.j) return 10; return null; }\nfunction routeB(u) { if (u.k) return 11; if (u.l) return 12; if (u.m) return 13; if (u.n) return 14; if (u.o) return 15; if (u.p) return 16; if (u.q) return 17; if (u.r) return 18; if (u.s) return 19; if (u.t) return 20; return null; }\nfunction routeC(u) { if (u.u) return 21; if (u.v) return 22; if (u.w) return 23; if (u.x) return 24; if (u.y) return 25; if (u.z) return 26; return null; }\n`;

describe("Düzeltme döngüsü — bulgu kaybolur, skor artar", () => {
  it("bozuk varyant high_complexity üretir, düzeltilmiş varyant üretmez", async () => {
    const broken = await analyzeLocalFiles(makeFiles(brokenIndex));
    const fixed = await analyzeLocalFiles(makeFiles(fixedIndex));

    const brokenComplex = broken.rawEvidence.filter((e: any) => e.category === "high_complexity");
    const fixedComplex = fixed.rawEvidence.filter((e: any) => e.category === "high_complexity");
    expect(brokenComplex.length).toBeGreaterThan(0);
    expect(fixedComplex).toEqual([]);
  });

  it("root cause da kaybolur — raporda high_complexity bulgusu kalmaz", async () => {
    const brokenScan = await analyzeLocalFiles(makeFiles(brokenIndex));
    const fixedScan = await analyzeLocalFiles(makeFiles(fixedIndex));
    const brokenReport = buildLocalReport(brokenScan, "demo-repo", { useLLM: false });
    const fixedReport = buildLocalReport(fixedScan, "demo-repo", { useLLM: false });

    const brokenCats = (brokenReport.root_causes?.root_causes || []).map((r: any) => r.category);
    const fixedCats = (fixedReport.root_causes?.root_causes || []).map((r: any) => r.category);
    expect(brokenCats).toContain("complexity");
    expect(fixedCats).not.toContain("complexity");
  });

  it("skor artar — düzeltilmiş varyantın sağlık skoru yüksektir", async () => {
    const broken = await analyzeLocalFiles(makeFiles(brokenIndex));
    const fixed = await analyzeLocalFiles(makeFiles(fixedIndex));

    const brokenReport = buildLocalReport(broken, "demo-repo", { useLLM: false });
    const fixedReport = buildLocalReport(fixed, "demo-repo", { useLLM: false });
    const brokenScore = brokenReport.ai_review?.health_score?.overall ?? 0;
    const fixedScore = fixedReport.ai_review?.health_score?.overall ?? 0;

    expect(fixedScore).toBeGreaterThan(brokenScore);
  });

  it("KADEMELİLİK: her dosya düzeltmesi codeQuality'yi anında artırır (monoton)", async () => {
    // 30 dosyalık repo, kademeli problemli dosya sayısı:
    //   9/30 = 0.30 → tavan ceza −45 → cq 47
    //   6/30 = 0.20 → ceza −30 → cq 62
    //   3/30 = 0.10 → ceza −15 → cq 77
    //   0/30 = 0.00 → ceza 0  → cq 92
    // Doğrusal modelin özü: band atlamaya gerek yok, her iyileştirme görünür.
    async function cqWith(problemCount: number): Promise<number> {
      const files: File[] = [];
      for (let i = 0; i < 30; i++) {
        const problematic = i < problemCount;
        const content = problematic
          ? `function f() {\n${Array.from({ length: 30 }, (_, j) => `  if (x${j} > ${j}) { y += ${j}; }`).join("\n")}\n  try { z(); } catch {}\n  return y;\n}\n`
          : `export const ok${i} = ${i};\n`;
        files.push(new File([content], `src/mod${i}.ts`, { type: "text/javascript" }));
      }
      const scan = await analyzeLocalFiles(files);
      const report = buildLocalReport(scan, "demo-repo", { useLLM: false });
      return report.ai_review?.health_score?.code_quality ?? 0;
    }

    const cq9 = await cqWith(9); // 0.30 → 47
    const cq6 = await cqWith(6); // 0.20 → 62
    const cq3 = await cqWith(3); // 0.10 → 77
    const cq0 = await cqWith(0); // 0.00 → 92

    expect(cq0).toBe(92);
    expect(cq3).toBeGreaterThan(cq6);
    expect(cq6).toBeGreaterThan(cq9);
    // Doğrusal çözünürlük: 6 dosya düzeltmesi 3 kademe artış = her dosya görünür
    expect(cq0 - cq9).toBeGreaterThanOrEqual(40);
  });
});
