import { NextRequest, NextResponse } from "next/server";
import { generateDemoData, buildReport } from "@/lib/demo-data";
import { jobStore } from "../analyze/route";

/**
 * Mock report endpoint.
 *
 * POST /api/report with { job_id, format } — returns a downloadable report
 * in the requested format (md, json, html, text).
 *
 * If the job_id isn't found in the in-memory store, we regenerate a demo
 * result on the fly.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const jobId: string = body.job_id || "latest";
    const format: string = (body.format || "md").toLowerCase();

    let result = jobStore.get(jobId) as ReturnType<typeof generateDemoData> | undefined;
    if (!result) {
      // Regenerate — for "latest" or unknown ids, use a placeholder repo.
      const repoUrl = body.repository_url || `https://github.com/example/${jobId}`;
      result = generateDemoData(repoUrl);
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
