import { NextRequest, NextResponse } from "next/server";

const API_BASE = "http://localhost:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const searchParams = req.nextUrl.searchParams;
  // Remove XTransformPort if present
  searchParams.delete("XTransformPort");
  const queryString = searchParams.toString();
  const url = `${API_BASE}/${path.join("/")}${queryString ? `?${queryString}` : ""}`;

  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const searchParams = req.nextUrl.searchParams;
  searchParams.delete("XTransformPort");
  const queryString = searchParams.toString();
  const url = `${API_BASE}/${path.join("/")}${queryString ? `?${queryString}` : ""}`;

  try {
    const body = await req.text();
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": req.headers.get("Content-Type") || "application/json",
      },
      body: body || undefined,
    });
    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("Content-Type") || "application/json" },
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 502 });
  }
}
