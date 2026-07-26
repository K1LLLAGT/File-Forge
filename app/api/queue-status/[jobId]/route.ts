import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.FILEFORGE_BACKEND_URL || "http://127.0.0.1:8091";

export async function GET(req: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  try {
    const res = await fetch(`${BACKEND_URL}/queue-status/${encodeURIComponent(jobId)}`);
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: "Internal error contacting backend" }, { status: 500 });
  }
}
