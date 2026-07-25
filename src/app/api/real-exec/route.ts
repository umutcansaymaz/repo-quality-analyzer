import { NextRequest, NextResponse } from "next/server";
import {
  runRealValidation,
  loadRealValidationSummary,
  loadExecutionLog,
} from "@/lib/real-analysis-engine";

/**
 * Sprint 15 — Real Execution API
 *
 * GET  /api/real-exec — load existing REAL results (no mock).
 *                        Returns { status: "no_data" } if no analysis executed.
 * POST /api/real-exec — run a real analysis batch (5 / 20 / 70 repos).
 *                        Body: { batch_size: number }
 *
 * CRITICAL: This endpoint NEVER returns mock data.
 * The marker `is_real: true` guarantees real data.
 */
export async function GET() {
  try {
    const summary = loadRealValidationSummary();
    const executionLog = loadExecutionLog();

    if (!summary) {
      return NextResponse.json({
        status: "no_data",
        message: "No real analysis executed yet. POST with batch_size to start.",
        has_checkpoint: executionLog !== null,
        execution_log: executionLog,
      });
    }

    return NextResponse.json({
      status: "ok",
      summary,
      execution_log: executionLog,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const batchSize: number = Math.min(Math.max(Number(body.batch_size) || 5, 1), 70);
    const pilotMode = batchSize <= 20;

    const result = runRealValidation(batchSize, pilotMode);

    return NextResponse.json({
      status: result.status,
      summary: result.summary,
      execution_log: result.executionLog,
      is_real: result.summary?.is_real === true,
      batch_size: batchSize,
      pilot_mode: pilotMode,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
