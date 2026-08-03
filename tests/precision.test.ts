/**
 * Hassasiyet testleri — Aşama A (yanlış pozitif temizliği) + Aşama B (derinlik).
 * Her tarayıcı için gerçek/yanlış pozitif çiftleri.
 */
import { describe, it, expect } from "vitest";
import { scanRepo, evidenceIn, categoriesOf } from "./helpers";
import { shouldSkip } from "../src/lib/local-analysis";

// ---------------------------------------------------------------------------
// A1: large_file yalnızca kaynak koda
// ---------------------------------------------------------------------------
describe("A1 — large_file yalnızca kaynak kod", () => {
  const bigBody = () => {
    const lines: string[] = [];
    for (let i = 0; i < 700; i++) lines.push(`const v${i} = ${i};`);
    return lines.join("\n");
  };

  it("700 satırlık .md → large_file YOK", async () => {
    const scan = await scanRepo([{ path: "docs/guide.md", content: bigBody() }]);
    expect(evidenceIn(scan, "large_file")).toHaveLength(0);
  });

  it("700 satırlık .json → large_file YOK", async () => {
    const scan = await scanRepo([{ path: "data/catalog.json", content: `{${bigBody()}}` }]);
    expect(evidenceIn(scan, "large_file")).toHaveLength(0);
  });

  it("700 satırlık .ts → large_file VAR", async () => {
    const scan = await scanRepo([{ path: "src/app.ts", content: bigBody() }]);
    expect(evidenceIn(scan, "large_file")).toHaveLength(1);
  });

  it("700 satırlık .py → large_file VAR", async () => {
    const scan = await scanRepo([{ path: "src/main.py", content: bigBody() }]);
    expect(evidenceIn(scan, "large_file")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// A2: üretilmiş dosya imzaları
// ---------------------------------------------------------------------------
describe("A2 — üretilmiş dosya skip", () => {
  it("tailwind-gen.css → skip", () => {
    expect(shouldSkip("src/app/tailwind-gen.css")).toBe(true);
  });
  it("app.min.js → skip", () => {
    expect(shouldSkip("dist/app.min.js")).toBe(true);
  });
  it("generated/models.ts → skip", () => {
    expect(shouldSkip("generated/models.ts")).toBe(true);
  });
  it("app.ts → skip DEĞİL", () => {
    expect(shouldSkip("src/app.ts")).toBe(false);
  });
  it("styles.css → skip DEĞİL (elle yazılmış)", () => {
    expect(shouldSkip("src/styles.css")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// A3: TODO yorum-farkındalıklı
// ---------------------------------------------------------------------------
describe("A3 — TODO tespiti", () => {
  it("String literal içindeki TODO → YOK", async () => {
    const scan = await scanRepo([{ path: "src/q.ts", content: 'const queueName = "TODO_QUEUE";\nconst x = 1;\n' }]);
    expect(evidenceIn(scan, "todo_debt")).toHaveLength(0);
  });

  it("Yorum içindeki TODO → VAR", async () => {
    const scan = await scanRepo([{ path: "src/t.ts", content: "// TODO: refactor this\nconst x = 1;\n" }]);
    expect(evidenceIn(scan, "todo_debt")).toHaveLength(1);
  });

  it("Python yorum TODO → VAR", async () => {
    const scan = await scanRepo([{ path: "src/t.py", content: "# FIXME: fix this\nx = 1\n" }]);
    expect(evidenceIn(scan, "todo_debt")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// B1: high_complexity
// ---------------------------------------------------------------------------
describe("B1 — high_complexity", () => {
  it("30 dallı fonksiyon → VAR", async () => {
    const lines = ["function big() {"];
    for (let i = 0; i < 30; i++) lines.push(`  if (x${i} > ${i}) { y += ${i}; }`);
    lines.push("  return y;");
    lines.push("}");
    const scan = await scanRepo([{ path: "src/big.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "high_complexity")).toHaveLength(1);
  });

  it("5 dallı fonksiyon → YOK", async () => {
    const lines = ["function small() {"];
    for (let i = 0; i < 5; i++) lines.push(`  if (x${i} > ${i}) { y += ${i}; }`);
    lines.push("  return y;");
    lines.push("}");
    const scan = await scanRepo([{ path: "src/small.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "high_complexity")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// B2: deep_nesting
// ---------------------------------------------------------------------------
describe("B2 — deep_nesting", () => {
  it("7 seviye iç içe → VAR", async () => {
    const lines = ["function deep() {"];
    for (let i = 0; i < 7; i++) lines.push(`${"  ".repeat(i + 1)}if (a${i}) {`);
    for (let i = 6; i >= 0; i--) lines.push(`${"  ".repeat(i + 1)}}`);
    lines.push("}");
    const scan = await scanRepo([{ path: "src/deep.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "deep_nesting")).toHaveLength(1);
  });

  it("3 seviye → YOK", async () => {
    const lines = ["function ok() {"];
    for (let i = 0; i < 3; i++) lines.push(`${"  ".repeat(i + 1)}if (a${i}) {`);
    for (let i = 2; i >= 0; i--) lines.push(`${"  ".repeat(i + 1)}}`);
    lines.push("}");
    const scan = await scanRepo([{ path: "src/ok.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "deep_nesting")).toHaveLength(0);
  });

  it("Python 7 girinti seviyesi → VAR", async () => {
    const lines = ["def deep():", "    if a0:"];
    for (let i = 1; i < 7; i++) lines.push(`${"    ".repeat(i + 1)}if a${i}:`);
    lines.push(`${"    ".repeat(8)}pass`);
    const scan = await scanRepo([{ path: "src/deep.py", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "deep_nesting")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// B3: empty_handler
// ---------------------------------------------------------------------------
describe("B3 — empty_handler", () => {
  it("catch {} → VAR", async () => {
    const scan = await scanRepo([{ path: "src/e.ts", content: "try { x(); } catch {}\n" }]);
    expect(evidenceIn(scan, "empty_handler")).toHaveLength(1);
  });

  it("catch (e) {} → VAR", async () => {
    const scan = await scanRepo([{ path: "src/e.ts", content: "try { x(); } catch (e) {}\n" }]);
    expect(evidenceIn(scan, "empty_handler")).toHaveLength(1);
  });

  it("catch (e) { return x; } → YOK", async () => {
    const scan = await scanRepo([{ path: "src/e.ts", content: "try { x(); } catch (e) { return 0; }\n" }]);
    expect(evidenceIn(scan, "empty_handler")).toHaveLength(0);
  });

  it("Python except: pass → VAR", async () => {
    const scan = await scanRepo([{ path: "src/e.py", content: "try:\n    x()\nexcept Exception:\n    pass\n" }]);
    expect(evidenceIn(scan, "empty_handler")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// B4: magic_number (evidence-only)
// ---------------------------------------------------------------------------
describe("B4 — magic_number", () => {
  it("= 3600 ataması → VAR", async () => {
    const scan = await scanRepo([{ path: "src/m.ts", content: "const limit = 3600;\n" }]);
    expect(evidenceIn(scan, "magic_number")).toHaveLength(1);
  });

  it("= 0 / = 1 / = 100 / = 42 → YOK (yaygın değerler)", async () => {
    const scan = await scanRepo([
      { path: "src/m.ts", content: "const a = 0;\nconst b = 1;\nconst c = 100;\nconst d = 42;\n" },
    ]);
    expect(evidenceIn(scan, "magic_number")).toHaveLength(0);
  });

  it("string içindeki sayı → YOK", async () => {
    const scan = await scanRepo([{ path: "src/m.ts", content: 'const msg = "error 404";\n' }]);
    expect(evidenceIn(scan, "magic_number")).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Skor entegrasyonu
// ---------------------------------------------------------------------------
describe("Skor entegrasyonu", () => {
  it("high_complexity + empty_handler dosyaları codeQuality'yi düşürür", async () => {
    const bad: { path: string; content: string }[] = [];
    for (let i = 0; i < 20; i++) {
      const lines = ["function f() {"];
      for (let j = 0; j < 30; j++) lines.push(`  if (x${j} > ${j}) { y += ${j}; }`);
      lines.push("  try { z(); } catch {}");
      lines.push("  return y;");
      lines.push("}");
      bad.push({ path: `src/mod${i}.ts`, content: lines.join("\n") });
    }
    bad.push({ path: "src/clean.ts", content: "export const ok = 1;\n" });
    const scan = await scanRepo(bad);
    const cats = categoriesOf(scan);
    expect(cats.high_complexity).toBeGreaterThan(0);
    expect(cats.empty_handler).toBeGreaterThan(0);
    // Problematic set'e girip girmediğini skor üzerinden doğrula:
    const { buildLocalReport } = await import("../src/lib/local-analysis");
    const report = buildLocalReport(scan, "test", { useLLM: false });
    const h = report.ai_review.health_score;
    expect(h.code_quality).toBeLessThan(80); // 20/21 dosya sorunlu → ceza uygulanmalı
  });
});
