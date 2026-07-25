import { NextRequest, NextResponse } from "next/server";
import { runAllBenchmarks, discoverBenchmarks } from "@/lib/benchmark-engine";

/**
 * Benchmark API endpoint.
 *
 * GET  /api/benchmark — list available benchmarks
 * POST /api/benchmark — run all benchmarks and return report
 */
export async function GET() {
  const benchmarks = discoverBenchmarks();
  return NextResponse.json({ benchmarks, total: benchmarks.length });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const previousReport = body.previous_report || null;

    // Simulate benchmark execution latency
    await new Promise((r) => setTimeout(r, 500));

    const report = runAllBenchmarks(previousReport);
    return NextResponse.json(report);
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
