/**
 * Analysis result persistence — in-memory + disk.
 *
 * Disk backing (db/analysis-results/{id}.json) keeps results across server
 * restarts and Next.js dev HMR reloads, so /api/result/:id never needs to
 * fall back to demo data.
 */
import { mkdirSync, writeFileSync, existsSync } from "fs";
import { join } from "path";

const RESULTS_DIR = join(process.cwd(), "db", "analysis-results");

let diskReady = false;
function ensureDir() {
  if (!diskReady) {
    try {
      mkdirSync(RESULTS_DIR, { recursive: true });
      diskReady = true;
    } catch {
      // best-effort — disk yazılamazsa sadece bellek kullanılır
    }
  }
}

/**
 * Saves a result to the in-memory store and to disk (best-effort).
 */
export function persistAnalysis(jobId: string, result: unknown): void {
  ensureDir();
  try {
    writeFileSync(join(RESULTS_DIR, `${jobId}.json`), JSON.stringify(result), "utf8");
  } catch {
    // best-effort — bellek kopyası zaten var
  }
}

export function diskResultExists(jobId: string): boolean {
  try {
    return existsSync(join(RESULTS_DIR, `${jobId}.json`));
  } catch {
    return false;
  }
}

export { RESULTS_DIR };
