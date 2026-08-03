import { NextRequest, NextResponse } from "next/server";
import { jobStore } from "../analyze/route";
import { persistAnalysis } from "@/lib/analysis-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Local analysis endpoint — receives the client-side analysis report JSON.
 *
 * All file content is analyzed in the browser (src/lib/local-analysis.ts),
 * so there is NO upload size limit here. This route only persists the
 * compact report and returns a job id for retrieval.
 *
 * Body: { repo_name, report } — report is the full DemoResult-shaped object
 * built client-side from real file scans.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => null);
    if (!body) {
      return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
    }

    const repoName = String(body.repo_name || "local-repository")
      .replace(/[^\w.-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "local-repository";
    const report = body.report;
    if (!report || typeof report !== "object") {
      return NextResponse.json({ error: "report is required" }, { status: 400 });
    }

    const jobId = `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    const localUrl = `local://${repoName}`;

    report.id = jobId;
    report.repository = { url: localUrl, owner: "local", name: repoName, host: "local-folder", access: "uploaded-folder" };

    jobStore.set(jobId, report);
    persistAnalysis(jobId, report);
    return NextResponse.json({ job_id: jobId, status: "completed", repository_url: localUrl, local: true });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || "Local analysis failed" }, { status: 500 });
  }
}
