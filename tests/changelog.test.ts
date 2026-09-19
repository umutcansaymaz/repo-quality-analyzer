/**
 * Sürüm notları mantığı testleri (critic revize planı):
 * - İlk ziyaret (bayrak yok) → göster
 * - Aynı sürüm → gösterme
 * - Farklı sürüm → göster
 * - localStorage hatasında (gizli mod/kota) sessiz yok say, çökme yok
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { showChangelog, markChangelogSeen, readChangelogSeen, CHANGELOG_STORAGE_KEY } from "../src/lib/changelog";
import { CURRENT_RELEASE } from "../src/lib/version";

// Node ortamı (vitest environment: node) — window.localStorage mock'u.
function makeStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() { return store.size; },
    clear: () => store.clear(),
    getItem: (k: string) => store.get(k) ?? null,
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (k: string) => { store.delete(k); },
    setItem: (k: string, v: string) => { store.set(k, v); },
  } as Storage;
}

describe("showChangelog — gösterim kararı", () => {
  it("bayrak yoksa (ilk ziyaret) gösterir", () => {
    expect(showChangelog(null, CURRENT_RELEASE)).toBe(true);
  });

  it("aynı sürüm bayrağı varsa göstermez", () => {
    expect(showChangelog(CURRENT_RELEASE, CURRENT_RELEASE)).toBe(false);
  });

  it("farklı sürüm bayrağı varsa gösterir", () => {
    expect(showChangelog("0.9.0", CURRENT_RELEASE)).toBe(true);
  });
});

describe("markChangelogSeen — bayrak yazma", () => {
  let storage: Storage;
  beforeEach(() => {
    storage = makeStorage();
    (globalThis as any).window = { localStorage: storage };
  });
  afterEach(() => {
    vi.restoreAllMocks();
    delete (globalThis as any).window;
  });

  it("kapatınca CURRENT_RELEASE yazar", () => {
    markChangelogSeen();
    expect(storage.getItem(CHANGELOG_STORAGE_KEY)).toBe(CURRENT_RELEASE);
  });

  it("localStorage hatasında sessizce yok sayar (çökme yok)", () => {
    const spy = vi.spyOn(storage, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });
    expect(() => markChangelogSeen()).not.toThrow();
    spy.mockRestore();
  });

  it("readChangelogSeen localStorage hatasında null döner (ilk ziyaret gibi)", () => {
    const spy = vi.spyOn(storage, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    expect(readChangelogSeen()).toBeNull();
    spy.mockRestore();
  });

  it("readChangelogSeen kayıtlı değeri döndürür (başarı yolu)", () => {
    storage.setItem(CHANGELOG_STORAGE_KEY, "0.9.0");
    expect(readChangelogSeen()).toBe("0.9.0");
  });

  it("readChangelogSeen anahtar yokken null döner", () => {
    expect(readChangelogSeen()).toBeNull();
  });

  it("round-trip: markChangelogSeen → readChangelogSeen aynı sürümü döndürür", () => {
    markChangelogSeen();
    expect(readChangelogSeen()).toBe(CURRENT_RELEASE);
  });

  it("bozuk storage değeri (boş/çöp) farklı sürüm sayılır → modal gösterilir", () => {
    // "null" gibi çöp değer CURRENT_RELEASE ile eşit değildir → göster
    expect(showChangelog("null", CURRENT_RELEASE)).toBe(true);
    expect(showChangelog("", CURRENT_RELEASE)).toBe(true);
  });
});
