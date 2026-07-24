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
 * Optional query params:
 *  ?repo=<url>        — regenerate using a specific repo URL.
 *  ?use_llm=true      — generate an LLM-powered review (offline: false).
 *  ?provider=<name>   — LLM provider name (e.g. "openai").
 *  ?model=<name>      — LLM model name (e.g. "gpt-4o").
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  let result = jobStore.get(id) as DemoResult | undefined;
  if (!result) {
    const repoUrl = _req.nextUrl.searchParams.get("repo") || `https://github.com/example/${id}`;
    const useLLM = _req.nextUrl.searchParams.get("use_llm") === "true";
    const llmProvider = _req.nextUrl.searchParams.get("provider") || undefined;
    const llmModel = _req.nextUrl.searchParams.get("model") || undefined;
    result = generateDemoData(repoUrl, { useLLM, llmProvider, llmModel });
    jobStore.set(id, result);
  }

  return NextResponse.json(result);
}
