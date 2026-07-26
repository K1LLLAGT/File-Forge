import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.FILEFORGE_BACKEND_URL || "http://127.0.0.1:8091";

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const file = form.get("file") as File | null;
    const preset = (form.get("preset") as string) || "medium";
    const crf = (form.get("crf") as string) || "23";

    if (!file) {
      return NextResponse.json({ error: "Missing file" }, { status: 400 });
    }

    const backendForm = new FormData();
    backendForm.append("file", file);
    backendForm.append("preset", preset);
    backendForm.append("crf", crf);

    const res = await fetch(`${BACKEND_URL}/compress/video`, { method: "POST", body: backendForm });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      return NextResponse.json({ error: data.error || "Compression failed" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: "Internal error contacting backend" }, { status: 500 });
  }
}
