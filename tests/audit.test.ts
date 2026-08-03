/**
 * Audit smoke test — verifies the audit pipeline itself works:
 * 1. It can detect a deliberately injected false positive (a broken rule
 *    that reports something on clean code would be caught).
 * 2. The generator produces 48 repos and the comparator computes
 *    precision/recall correctly on a known case.
 *
 * This guards the auditor, not the engine — if the auditor stops catching
 * FP/FN, this test fails.
 */
import { describe, it, expect } from "vitest";
import { generateRepos } from "../audit/generator.mjs";
import { compare } from "../audit/compare.mjs";

describe("audit generator", () => {
  it("48 repo üretir (8 kategori × 6 varyant)", () => {
    const repos = generateRepos();
    expect(repos.length).toBe(48);
  });

  it("Temiz varyantlar boş beklenti içerir", () => {
    const repos = generateRepos();
    const clean = repos.filter((r) => r.name.endsWith("-clean"));
    expect(clean.length).toBe(8);
    for (const c of clean) expect(c.expected).toEqual([]);
  });

  it("Enjekte edilen kategoriler beklentide yansır", () => {
    const repos = generateRepos();
    const single = repos.filter((r) => r.name.endsWith("-single"));
    expect(single.length).toBe(8);
    for (const s of single) {
      const cat = s.name.replace("-single", "");
      expect(s.expected).toContain(cat);
    }
  });

  it("Gerçek dosyalar üretir (boş değil)", () => {
    const repos = generateRepos();
    for (const r of repos.slice(0, 6)) {
      expect(r.files.length).toBeGreaterThan(0);
      for (const f of r.files) expect(f.content.length).toBeGreaterThan(10);
    }
  });
});

describe("audit comparator", () => {
  it("FP tespit eder (fazla bulgu)", () => {
    const cmp = compare(["hardcoded_secret"], ["hardcoded_secret", "magic_number"]);
    expect(cmp.extra).toEqual(["magic_number"]);
    expect(cmp.missing).toEqual([]);
    expect(cmp.precision).toBeCloseTo(0.5);
    expect(cmp.recall).toBe(1);
  });

  it("FN tespit eder (kaçırılan bulgu)", () => {
    const cmp = compare(["hardcoded_secret", "large_file"], ["hardcoded_secret"]);
    expect(cmp.missing).toEqual(["large_file"]);
    expect(cmp.extra).toEqual([]);
    expect(cmp.recall).toBeCloseTo(0.5);
    expect(cmp.precision).toBe(1);
  });

  it("Temiz kod + bulgu = FP (kesin yanlış pozitif)", () => {
    const cmp = compare([], ["deep_nesting"]);
    expect(cmp.extra).toEqual(["deep_nesting"]);
    expect(cmp.precision).toBe(0);
  });

  it("Doğru eşleşme = FP/FN yok", () => {
    const cmp = compare(["secret", "secret"], ["secret"]);
    expect(cmp.extra).toEqual([]);
    expect(cmp.missing).toEqual([]);
  });
});
