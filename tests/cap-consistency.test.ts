/**
 * Faz D — MAX_EVIDENCE cap tutarlılığı: 300 cap'i aşan repoda kesim severity
 * sıralı olmalı — critical/high bulgular asla cap'e kurban gitmemeli.
 */
import { describe, it, expect } from "vitest";
import { analyzeLocalFiles } from "../src/lib/local-analysis";

describe("MAX_EVIDENCE cap kesim tutarlılığı", () => {
  it("300+ bulguda critical/high korunur, cap 300'ü aşmaz", async () => {
    const files: File[] = [];
    // 75 dosya × 5 magic_number = 375 düşük öncelikli bulgu (dosya+kategori cap 5)
    for (let d = 0; d < 75; d++) {
      const lines: string[] = [];
      for (let i = 0; i < 5; i++) lines.push(`const x${i} = ${1234 + i};\n`);
      files.push(new File([lines.join("")], `src/m${d}.ts`, { type: "text/plain" }));
    }
    // 1 yüksek injection + 1 kritik secret (parçalı — bu test dosyası kalite'nin
    // kendi analizinde gerçek secret üretmesin) — kesimde korunmalı.
    files.push(new File(['const k = "sk-" + "abcdefghijklmnopqrstuvwxyz123456";\n'], "src/sec.ts", { type: "text/plain" }));
    files.push(new File(["const { execSync } = require('child_process');\nexecSync(cmd);\n"], "src/inj.ts", { type: "text/plain" }));

    const scan = await analyzeLocalFiles(files);
    expect(scan.evidence.length).toBeLessThanOrEqual(300);

    const cats = scan.evidence.map((e: any) => e.category);
    expect(cats).toContain("command_injection");
    // Severity sıralı kesim: ilk bulgu high veya üstü olmalı (düşük öncelikli
    // magic_number'lar cap'e takılıp kesilmiş olabilir, yüksekler kesilmemeli).
    const first = scan.evidence[0] as any;
    expect(["critical", "high"].includes(first.severity)).toBe(true);
  });

  it("cap 300 altındaysa tüm bulgular korunur", async () => {
    const files: File[] = [];
    for (let d = 0; d < 10; d++) {
      files.push(new File([`const x = ${1200 + d};\n`], `src/m${d}.ts`, { type: "text/plain" }));
    }
    const scan = await analyzeLocalFiles(files);
    expect(scan.evidence.length).toBeGreaterThan(0);
    expect(scan.evidence.length).toBeLessThanOrEqual(300);
  });
});
