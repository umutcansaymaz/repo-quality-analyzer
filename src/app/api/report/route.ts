import { NextRequest, NextResponse } from "next/server";
import { buildReport, type DemoResult } from "@/lib/demo-data";
import { jobStore } from "../analyze/route";
import { existsSync, readFileSync } from "fs";
import { join } from "path";
import { RESULTS_DIR } from "@/lib/analysis-store";

/**
 * Report endpoint — real results only.
 *
 * POST /api/report with { job_id, format } — returns a downloadable report
 * (md, json, html, text) from the real analysis result. Never regenerates
 * demo data.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const jobId: string = body.job_id || "";
    const format: string = (body.format || "md").toLowerCase();
    if (!jobId) {
      return NextResponse.json({ error: "job_id is required" }, { status: 400 });
    }

    let result: DemoResult | null = jobStore.get(jobId) as DemoResult | null;
    if (!result) {
      // Disk yedeğinden oku (restart/HMR dayanıklı)
      try {
        const diskPath = join(RESULTS_DIR, `${jobId}.json`);
        if (existsSync(diskPath)) {
          result = JSON.parse(readFileSync(diskPath, "utf8"));
          jobStore.set(jobId, result);
        }
      } catch {
        // bozuk/eksik — aşağıda 404
      }
    }

    if (!result) {
      return NextResponse.json(
        { error: "Analiz sonucu bulunamadı. Lütfen analizi tekrar çalıştırın." },
        { status: 404 }
      );
    }

    const report = buildReport(result, format);
    return new NextResponse(report.content, {
      status: 200,
      headers: {
        "Content-Type": report.contentType,
        "Content-Disposition": `attachment; filename="${report.filename}"`,
      },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
