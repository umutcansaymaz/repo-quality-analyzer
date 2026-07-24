import { NextRequest, NextResponse } from "next/server";
import { generateDemoData } from "@/lib/demo-data";

/**
 * Mock analyze endpoint.
 *
 * Accepts { repository_url, use_cache } and returns { job_id, status }.
 * Generates a deterministic demo result immediately so the frontend can
 * poll /api/result/:id without needing the real Python backend.
 *
 * (This specific route takes precedence over the catch-all [...path] proxy.)
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const repoUrl: string = body.repository_url || "";
    if (!repoUrl) {
      return NextResponse.json({ error: "repository_url is required" }, { status: 400 });
    }

    // Generate the demo result synchronously and stash it in a module-level
    // map keyed by job_id, so /api/result/:id can return it on the next request.
    const result = generateDemoData(repoUrl);
    const jobId = result.id;
    jobStore.set(jobId, result);

    // Simulate a tiny bit of pipeline latency so the progress view feels real.
    await new Promise((r) => setTimeout(r, 200));

    return NextResponse.json({ job_id: jobId, status: "completed", repository_url: repoUrl });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

// In-memory job store (per server instance). For a real backend this would be
// a database; for the mock it's fine to keep results in process memory.
export const jobStore: Map<string, unknown> = new Map();
