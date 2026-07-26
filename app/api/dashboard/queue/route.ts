import { NextResponse } from "next/server";

const BACKEND_URL = process.env.FILEFORGE_BACKEND_URL || "http://127.0.0.1:8091";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/dashboard/queue`, { cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json({ error: "Backend unreachable" }, { status: 503 });
  }
}
