import { NextResponse } from "next/server";
import { runFullValidation } from "@/lib/validation-engine";

/**
 * Validation API endpoint.
 *
 * POST /api/validate — runs full validation across all catalogued repositories.
 * Returns a comprehensive ValidationReport.
 */
export async function POST() {
  try {
    // Simulate validation execution latency
    await new Promise((r) => setTimeout(r, 800));

    const report = runFullValidation();
    if (!report) {
      return NextResponse.json({ error: "Validation failed — safety check" }, { status: 500 });
    }
    return NextResponse.json(report);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    status: "ready",
    message: "POST to /api/validate to run full validation",
    catalog: "benchmarks/repository_catalog.json",
  });
}
