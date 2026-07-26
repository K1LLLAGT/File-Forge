import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.FILEFORGE_BACKEND_URL || "http://127.0.0.1:8091";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;
    const targetExt = formData.get("targetExt") as string | null;

    if (!file || !targetExt) {
      return NextResponse.json({ error: "Missing file or targetExt" }, { status: 400 });
    }

    const backendForm = new FormData();
    backendForm.append("file", file);
    backendForm.append("target_ext", targetExt);

    const res = await fetch(`${BACKEND_URL}/convert`, {
      method: "POST",
      body: backendForm,
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json({ error: data.error || "Backend conversion failed" }, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: "Internal error contacting backend" }, { status: 500 });
  }
}
