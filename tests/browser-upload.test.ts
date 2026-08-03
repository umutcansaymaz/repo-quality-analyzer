/**
 * Tarayıcı (webkitdirectory) akışı simülasyonu — dosyalar üst klasör adıyla
 * prefix'li gelir ("kalite/audit/.work/...") ve .gitignore dahil edilir.
 * Motor, prefix'e rağmen kök .gitignore'u bulup audit/.work gibi repo'ya
 * özel dizinleri skip etmelidir.
 */
import { describe, it, expect } from "vitest";
import { analyzeLocalFiles } from "../src/lib/local-analysis";

function fileWith(path: string, content: string) {
  const f = new File([content], path, { type: "text/plain" }) as any;
  f.webkitRelativePath = path;
  return f;
}

describe("Tarayıcı prefix'li yol akışı (.gitignore + audit/.work)", () => {
  it("prefix'li yollarda .gitignore bulunur ve audit/.work skip edilir", async () => {
    const files = [
      // Gerçek kod
      fileWith("kalite/src/app/page.tsx", "export const x = 1;\n"),
      fileWith("kalite/src/lib/engine.ts", "export function f(a: number) { return a + 1; }\n"),
      // Kök .gitignore — prefix'li yol
      fileWith("kalite/.gitignore", "/audit/.work/\nnode_modules/\n"),
      // Sentetik test repoları — SKIP EDİLMELİ
      // Not: değerler concat ile yazıldı ki test dosyası kalite'nin kendi
      // analizinde gerçek secret gibi yakalanmasın (regex tek parça arar).
      fileWith("kalite/audit/.work/hardcoded_secret-single/src/main.ts", "const apiKey = " + '"sk-" + "abcdefghijklmnopqrstuvwxyz123456";' + "\n"),
      fileWith("kalite/audit/.work/command_injection-single/src/main.ts", "execSync(cmd);\n"),
      fileWith("kalite/audit/.work/weak_crypto-go-single/src/main.go", "md5.Sum(data)\n"),
      // node_modules da skip
      fileWith("kalite/node_modules/pkg/index.js", "const k = " + '"sk-" + "abcdefghijklmnopqrstuvwxyz123456";' + "\n"),
    ];

    const scan = await analyzeLocalFiles(files);
    expect(scan.files).toContain("kalite/src/app/page.tsx");
    expect(scan.files).toContain("kalite/src/lib/engine.ts");
    // Sentetik repolar ve node_modules tarama listesinde OLMAMALI
    expect(scan.files.some((f) => f.includes("audit/.work"))).toBe(false);
    expect(scan.files.some((f) => f.includes("node_modules"))).toBe(false);
    // Ve hiçbir sahte bulgu üretilmemeli
    const sec = scan.evidence.filter((e: any) => e.category === "hardcoded_secret");
    expect(sec).toHaveLength(0);
  });
});
