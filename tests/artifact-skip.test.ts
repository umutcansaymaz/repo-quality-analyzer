/**
 * Artefakt dizini regression testi (Hedeflerim dersi):
 *
 * Sorun: playwright-report/test-results gibi ÜRETİLMİŞ rapor dizinleri gerçek
 * kod gibi taranıyordu — 391 dallık HTML "fonksiyonu" high_complexity üretiyor,
 * refactor ne yapılırsa yapılsın bulgu asla kaybolmuyor ve puan düşük kalıyordu.
 *
 * Koruma: 1) artefakt dizinlerinden 0 evidence gelir (skip çalışıyor),
 *         2) aynı içerik gerçek kaynak yolunda (src/) high_complexity ÜRETİR
 *            — skip dizin adı bazlıdır, .html uzantısı DEĞİL. Bu duyarlılık
 *            testi, birisi skipi uzantı bazlı yaparsa veya komple kaldırırsa
 *            kırmızı yanar.
 */
import { describe, it, expect } from "vitest";
import { analyzeLocalFiles } from "../src/lib/local-analysis";

/** 400+ dallık inline script içeren "rapor" HTML'i — skip yoksa high_complexity üretir. */
function hugeReportHtml(): string {
  const ifs = Array.from({ length: 420 }, (_, i) => `    if (x${i}) { y(${i}); }`).join("\n");
  return `<!DOCTYPE html>\n<html><head><title>Test Report</title></head>\n<body>\n<script>\nfunction renderReport() {\n${ifs}\n}\n</script>\n</body>\n</html>\n`;
}

const ARTIFACT_DIRS = [
  "playwright-report",
  "playwright_report",
  "test-results",
  "test_results",
  "traces",
  ".playwright-artifacts",
  "allure-results",
  "allure_report",
  "cypress",
  "screenshots",
];

describe("Artefakt dizinleri — üretilmiş raporlar analiz dışı", () => {
  it.each(ARTIFACT_DIRS)("%s içindeki dev HTML 0 evidence üretir", async (dir) => {
    const files = [
      new File(["export const ok = 1;\n"], "src/main.ts", { type: "text/plain" }),
      new File([hugeReportHtml()], `${dir}/index.html`, { type: "text/html" }),
    ];
    const scan = await analyzeLocalFiles(files);
    const fromArtifact = scan.rawEvidence.filter((e: any) => String(e.file_path).startsWith(dir + "/"));
    expect(fromArtifact).toEqual([]);
    // Temiz kaynak da bulgu üretmemeli (hiçbir artefakt bulgusu yok)
    expect(scan.rawEvidence.filter((e: any) => String(e.file_path) === "src/main.ts")).toEqual([]);
  });

  it("DUYARLILIK: aynı dev HTML src/ altında high_complexity ÜRETİR (skip uzantı bazlı değil)", async () => {
    const files = [
      new File([hugeReportHtml()], "src/views/page.html", { type: "text/html" }),
    ];
    const scan = await analyzeLocalFiles(files);
    const complex = scan.rawEvidence.filter((e: any) => e.category === "high_complexity");
    expect(complex.length).toBeGreaterThan(0);
  });

  it("Küçük gerçek HTML kaynağı bulgu üretmez (masum dosyalar etkilenmez)", async () => {
    const files = [
      new File([`<!DOCTYPE html>\n<html><body><script>\nfunction small() { if (a) { return 1; } }\n</script></body></html>\n`], "src/views/page.html", { type: "text/html" }),
    ];
    const scan = await analyzeLocalFiles(files);
    expect(scan.rawEvidence).toEqual([]);
  });
});
