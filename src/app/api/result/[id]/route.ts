import { NextRequest, NextResponse } from "next/server";
import { generateDemoData, type DemoResult } from "@/lib/demo-data";
import { jobStore } from "../../analyze/route";

/**
 * Mock result endpoint.
 *
 * GET /api/result/:id — returns the full analysis result for the given job id.
 * If the id isn't in the in-memory store (e.g. server restarted), we regenerate
 * a fresh demo result so the endpoint never 404s.
 *
 * Optional query: ?repo=<url> — regenerate using a specific repo URL.
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  let result = jobStore.get(id) as DemoResult | undefined;
  if (!result) {
    // Not in memory — regenerate. Use the id as a fallback repo URL seed.
    // If the client passed ?repo=, prefer that.
    const repoUrl = _req.nextUrl.searchParams.get("repo") || `https://github.com/example/${id}`;
    result = generateDemoData(repoUrl);
    jobStore.set(id, result);
  }

  return NextResponse.json(result);
}
