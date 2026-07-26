import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.FILEFORGE_BACKEND_URL || "http://127.0.0.1:8091";

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const file = form.get("file") as File | null;
    if (!file) {
      return NextResponse.json({ error: "Missing file" }, { status: 400 });
    }

    const backendForm = new FormData();
    backendForm.append("file", file);

    const res = await fetch(`${BACKEND_URL}/thumbnail/image`, { method: "POST", body: backendForm });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return NextResponse.json({ error: data.error || "Thumbnail generation failed" }, { status: res.status });
    }

    return new NextResponse(res.body, { headers: { "Content-Type": "image/png" } });
  } catch (err) {
    return NextResponse.json({ error: "Internal error contacting backend" }, { status: 500 });
  }
}
