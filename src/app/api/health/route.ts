import { NextResponse } from "next/server";

/**
 * Mock health endpoint.
 *
 * GET /api/health — returns the status of all platform components.
 * Since we use a mock API (no real Python backend), most components
 * are "online" (the mock is working). LLM depends on whether the
 * user has configured a provider. Database is "offline" (no DB in mock).
 */
export async function GET() {
  // Simulate a tiny latency for realism.
  await new Promise((r) => setTimeout(r, 100));

  return NextResponse.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    components: {
      backend: { status: "online", detail: "Mock API running" },
      python: { status: "online", detail: "3.11.0 (simulated)" },
      analyzer: { status: "online", detail: "9 analyzers ready" },
      llm: { status: "online", detail: "Provider configured" },
      worker: { status: "online", detail: "1 worker active" },
      database: { status: "offline", detail: "No database (demo mode)" },
      api: { status: "online", detail: "REST API responding" },
    },
  });
}
