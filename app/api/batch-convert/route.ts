import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.FILEFORGE_BACKEND_URL || "http://127.0.0.1:8091";

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const files = form.getAll("files") as File[];
    const targetExt = form.get("targetExt") as string | null;

    if (!files.length || !targetExt) {
      return NextResponse.json({ error: "Missing files or targetExt" }, { status: 400 });
    }

    const backendForm = new FormData();
    files.forEach((f) => backendForm.append("files", f));
    backendForm.append("target_ext", targetExt);

    const res = await fetch(`${BACKEND_URL}/batch-convert`, { method: "POST", body: backendForm });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      return NextResponse.json({ error: data.error || "Batch conversion failed" }, { status: res.status });
    }
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: "Internal error contacting backend" }, { status: 500 });
  }
}
