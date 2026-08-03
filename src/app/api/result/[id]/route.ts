import { NextRequest, NextResponse } from "next/server";
import { existsSync, readFileSync } from "fs";
import { join } from "path";
import { jobStore } from "../../analyze/route";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const RESULTS_DIR = join(process.cwd(), "db", "analysis-results");

/**
 * Result endpoint — REAL results only.
 *
 * GET /api/result/:id — returns the analysis result for the given job id.
 * Sources (in order):
 *   1. In-memory jobStore
 *   2. Disk (db/analysis-results/{id}.json) — survives server restarts
 * Never falls back to demo/synthetic data. If no real result exists → 404.
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // 1. In-memory store
  let result = jobStore.get(id);
  if (!result) {
    // 2. Disk — survives server restarts / HMR
    try {
      const diskPath = join(RESULTS_DIR, `${id}.json`);
      if (existsSync(diskPath)) {
        result = JSON.parse(readFileSync(diskPath, "utf8"));
        jobStore.set(id, result);
      }
    } catch {
      // bozuk dosya — 404 döner
    }
  }

  if (!result) {
    return NextResponse.json(
      { error: "Analiz sonucu bulunamadı. Sunucu yeniden başlatılmış olabilir — lütfen analizi tekrar çalıştırın." },
      { status: 404 }
    );
  }

  return NextResponse.json(result);
}
