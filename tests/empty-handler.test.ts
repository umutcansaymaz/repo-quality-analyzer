/**
 * Bilinçli best-effort catch regression testi (Hedeflerim dersi):
 *
 * Sorun: "catch + ignore yorumu" gibi bilinçli teardown/cleanup desenleri
 * "hata sessizce yutuluyor" diye raporlanıyordu — 14 kanıtın 4'ü focus-engine.js
 * temizliğiydi (osc.disconnect / gain.disconnect).
 *
 * Kural: gövde boşluğu tek başına bulgu değildir. Yorum içinde bilinçli işaret
 * (ignore/cleanup/best-effort/intentional/noop/swallow/fallback/benign) varsa
 * ve borç işareti (TODO/FIXME/HACK) yoksa handled sayılır → bulgu yok.
 * TODO/FIXME yorumlu boş catch gerçek borçtur → bulgu VAR.
 */
import { describe, it, expect } from "vitest";
import { analyzeLocalFiles } from "../src/lib/local-analysis";

async function scan(tsContent: string) {
  const files = [new File([tsContent], "src/main.ts", { type: "text/javascript" })];
  const s = await analyzeLocalFiles(files);
  return s.rawEvidence.filter((e: any) => e.category === "empty_handler");
}

async function scanPy(pyContent: string) {
  const files = [new File([pyContent], "src/main.py", { type: "text/x-python" })];
  const s = await analyzeLocalFiles(files);
  return s.rawEvidence.filter((e: any) => e.category === "empty_handler");
}

describe("Bilinçli best-effort catch — bulgu üretmez", () => {
  it("/* ignore */ yorumlu catch handled sayılır (focus-engine dersi)", async () => {
    const ev = await scan(`try { osc.disconnect(); } catch { /* ignore */ }\n`);
    expect(ev).toEqual([]);
  });

  it("/* cleanup: teardown */ yorumlu catch handled sayılır", async () => {
    const ev = await scan(`try { cleanup(); } catch { /* cleanup: teardown hataları sessiz */ }\n`);
    expect(ev).toEqual([]);
  });

  it("// best-effort yorumlu catch handled sayılır", async () => {
    const ev = await scan(`try { localStorage.setItem(k, v); } catch { // best-effort\n}\n`);
    expect(ev).toEqual([]);
  });

  it("Python: pass # best-effort handled sayılır", async () => {
    const ev = await scanPy(`try:\n    cleanup()\nexcept Exception:\n    pass  # best-effort: teardown\n`);
    expect(ev).toEqual([]);
  });

  it("Python: pass # ignore handled sayılır", async () => {
    const ev = await scanPy(`try:\n    risky()\nexcept Exception:\n    pass  # ignore\n`);
    expect(ev).toEqual([]);
  });

  it("Birden fazla ignore catch'i de bulgu üretmez", async () => {
    const ev = await scan(`try { osc.disconnect(); } catch { /* ignore */ }\ntry { gain.disconnect(); } catch { /* ignore */ }\n`);
    expect(ev).toEqual([]);
  });
});

describe("Borç işaretli boş catch — hâlâ bulgu", () => {
  it("// TODO yorumlu boş catch bulgu üretir", async () => {
    const ev = await scan(`try { risky(); } catch { // TODO: hata işleme eklenecek\n}\n`);
    expect(ev.length).toBe(1);
  });

  it("Python: pass # TODO bulgu üretir", async () => {
    const ev = await scanPy(`try:\n    risky()\nexcept Exception:\n    pass  # TODO: log eklenecek\n`);
    expect(ev.length).toBe(1);
  });

  it("Gerçek boş catch (yorum bile yok) bulgu üretir", async () => {
    const ev = await scan(`try { risky(); } catch {}\n`);
    expect(ev.length).toBe(1);
  });
});

describe("Kanıt şeffaflığı — snippet catch gövdesini içerir", () => {
  it("evidence_snippet tam catch bloğunu gösterir (satır dışında gövde)", async () => {
    const ev = await scan(`try {\n  risky();\n} catch { // TODO: fix\n}\n`);
    expect(ev.length).toBe(1);
    expect(String(ev[0].evidence_snippet || "")).toContain("catch { // TODO: fix");
    expect(String(ev[0].evidence_snippet || "")).toContain("}");
  });
});
