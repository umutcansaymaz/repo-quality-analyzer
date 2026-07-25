import { NextResponse } from "next/server";
import { runRealValidation, loadRealValidationSummary, loadExecutionLog } from "@/lib/real-analysis-engine";

/**
 * Validation API endpoint — Sprint 15: Real Execution Engine.
 *
 * POST /api/validate — runs REAL analysis on repository catalog.
 *   body: { batch_size?: number, pilot_mode?: boolean }
 *   Default: pilot_mode=true, batch_size=5 (gradual scale-up per user recommendation)
 *
 * GET /api/validate — loads existing real validation summary from disk.
 *   Returns "no_analysis" status if no real analysis has been executed.
 */
export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const batchSize = body.batch_size || 5;
    const pilotMode = body.pilot_mode !== false;

    const result = runRealValidation(batchSize, pilotMode);
    return NextResponse.json({
      status: result.status,
      summary: result.summary,
      execution_log: result.executionLog,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function GET() {
  // Load existing real validation summary
  const summary = loadRealValidationSummary();
  const executionLog = loadExecutionLog();

  if (!summary) {
    return NextResponse.json({
      status: "no_analysis",
      message: "No real analysis has been executed yet. POST to /api/validate to start.",
      execution_log: executionLog,
    });
  }

  return NextResponse.json({
    status: "completed",
    summary,
    execution_log: executionLog,
  });
}
