import { NextResponse } from "next/server";
import { runExternalValidation } from "@/lib/external-validation-engine";
import { readFileSync } from "fs";
import { resolve } from "path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * External Validation API endpoint.
 *
 * POST /api/external-validate — runs external validation against
 * repository catalog, collecting independent evidence from GitHub
 * (Issues, PRs, ADRs, Discussions, Documentation).
 */
export async function POST() {
  try {
    // Load repository catalog
    const catalogPath = resolve(process.cwd(), "benchmarks", "repository_catalog.json");
    let catalog: any[] = [];
    try {
      const raw = readFileSync(catalogPath, "utf-8");
      catalog = JSON.parse(raw).repositories || [];
    } catch {
      catalog = [];
    }

    const report = runExternalValidation(catalog);
    return NextResponse.json({ ...report, is_demo: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    status: "ready",
    message: "POST to /api/external-validate to run external validation",
    provider: "GitHub (first provider — GitLab, Jira, Confluence can be added)",
  });
}
