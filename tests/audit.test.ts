/**
 * Audit smoke test — verifies the audit pipeline itself works:
 * 1. Generator produces the expected repo matrix with known content.
 * 2. Comparator computes precision/recall correctly on known cases.
 *
 * This guards the auditor, not the engine — if the auditor stops catching
 * FP/FN, this test fails.
 */
import { describe, it, expect } from "vitest";
import { generateRepos } from "../audit/generator.mjs";
import { compare } from "../audit/compare.mjs";

describe("audit generator", () => {
  it("Kapsamlı repo matrisi üretir (13 kategori × 5 dil × 6 varyant + özel senaryolar)", () => {
    const repos = generateRepos();
    // 13 kategoriden 11'i düzenli matris (circular/missing özel) × 5 dil × 6 varyant
    // + circular (10) + missing (5) + boundary (12) + traps (8)
    expect(repos.length).toBeGreaterThan(300);
  });

  it("Temiz varyantlar boş beklenti içerir", () => {
    const repos = generateRepos();
    const clean = repos.filter((r) => r.name.endsWith("-clean"));
    expect(clean.length).toBeGreaterThan(50);
    for (const c of clean) expect(c.expected).toEqual([]);
  });

  it("Enjekte edilen kategoriler beklentide yansır", () => {
    const repos = generateRepos();
    const single = repos.filter((r) => r.name.endsWith("-single"));
    expect(single.length).toBeGreaterThan(50);
    for (const s of single) {
      const cat = s.name.split("-")[0];
      expect(s.expected).toContain(cat);
    }
  });

  it("Sınır eşiği repoları üretilir (alt/üst)", () => {
    const repos = generateRepos();
    const under = repos.filter((r) => r.name.startsWith("b-") && r.name.endsWith("-under"));
    const over = repos.filter((r) => r.name.startsWith("b-") && r.name.endsWith("-over"));
    expect(under.length).toBeGreaterThanOrEqual(6);
    expect(over.length).toBeGreaterThanOrEqual(6);
    // Alt eşik repoları eşik sorununu İÇERMEZ (yalnızca eşikle ilişkisiz
    // doğal bulgular olabilir — b-coupling-under'da missing_tests gibi).
    // Kategori adı: b-long-* → long_function, b-big-* → large_file, b-coupling-* → tight_coupling
    const catOf = (name: string) => {
      const seg = name.split("-")[1];
      const map: Record<string, string> = {
        long: "long_function",
        big: "large_file",
        complex: "high_complexity",
        depth: "deep_nesting",
        god: "god_class",
        coupling: "tight_coupling",
      };
      return map[seg] || seg;
    };
    for (const u of under) expect(u.expected.includes(catOf(u.name))).toBe(false);
    for (const o of over) expect(o.expected).toContain(catOf(o.name));
  });

  it("Tuzak repoları boş beklenti içerir (FP olmamalı)", () => {
    const repos = generateRepos();
    const traps = repos.filter((r) => r.name.startsWith("trap-"));
    expect(traps.length).toBeGreaterThanOrEqual(8);
    for (const t of traps) expect(t.expected).toEqual([]);
  });

  it("Gerçek dosyalar üretir (boş değil)", () => {
    const repos = generateRepos();
    for (const r of repos.slice(0, 10)) {
      expect(r.files.length).toBeGreaterThan(0);
      for (const f of r.files) expect(f.content.length).toBeGreaterThan(10);
    }
  });

  it("5 dil de temsil edilir", () => {
    const repos = generateRepos();
    const names = repos.map((r) => r.name).join(" ");
    for (const lang of ["ts", "py", "go", "rb", "java"]) {
      expect(names.includes(`-${lang}-`)).toBe(true);
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
