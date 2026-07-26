import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.FILEFORGE_BACKEND_URL || "http://127.0.0.1:8091";

export async function GET(req: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  try {
    const res = await fetch(`${BACKEND_URL}/compress/download/${encodeURIComponent(jobId)}`);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return NextResponse.json({ error: data.error || "File not found" }, { status: res.status });
    }
    const contentDisposition = res.headers.get("content-disposition");
    return new NextResponse(res.body, {
      headers: {
        "Content-Type": "video/mp4",
        ...(contentDisposition ? { "Content-Disposition": contentDisposition } : {}),
      },
    });
  } catch (err) {
    return NextResponse.json({ error: "Internal error contacting backend" }, { status: 500 });
  }
}
