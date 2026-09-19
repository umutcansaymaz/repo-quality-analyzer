/**
 * Sürüm notları modalı — ilk ziyaret/yeni sürümde gösterilir.
 *
 * Mantık (saf, test edilebilir):
 * - showChangelog(seen, current): bayrak yoksa (ilk ziyaret) VEYA farklı sürümse göster
 * - markChangelogSeen(): kapatınca seen = CURRENT_RELEASE yazar (try/catch — gizli mod/kota hatasında sessiz)
 */
import { CURRENT_RELEASE } from "@/lib/version";

export const CHANGELOG_STORAGE_KEY = "ra-changelog-seen";

/** Modal gösterilmeli mi? Bayrak yoksa (ilk ziyaret) veya farklı sürümse evet. */
export function showChangelog(seen: string | null, current: string): boolean {
  return seen !== current;
}

/** Kapatınca bayrak yaz — localStorage erişimi try/catch (gizli mod/kota hatası → sessiz). */
export function markChangelogSeen(): void {
  try {
    window.localStorage.setItem(CHANGELOG_STORAGE_KEY, CURRENT_RELEASE);
  } catch {
    // gizli mod / kota doldu — sessizce yok say, sayfa çökmesin
  }
}

/** Bayrağı oku — localStorage erişimi try/catch; hata durumunda null (ilk ziyaret gibi). */
export function readChangelogSeen(): string | null {
  try {
    return window.localStorage.getItem(CHANGELOG_STORAGE_KEY);
  } catch {
    return null;
  }
}
