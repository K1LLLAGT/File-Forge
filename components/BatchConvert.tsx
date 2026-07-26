"use client";

import { useState } from "react";

type BatchJob = { jobId: string; status: string; error?: string };
type BatchResult = { jobs?: BatchJob[]; error?: string };

export default function BatchConvert() {
  const [files, setFiles] = useState<File[]>([]);
  const [targetExt, setTargetExt] = useState("mp4");
  const [result, setResult] = useState<BatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!files.length) return setError("Select at least one file");
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      form.append("targetExt", targetExt);

      const res = await fetch("/api/batch-convert", { method: "POST", body: form });
      const data = (await res.json()) as BatchResult;
      if (!res.ok) setError(data.error || "Batch conversion failed");
      else setResult(data);
    } catch {
      setError("Network error contacting the dashboard API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="ff-card space-y-3" onSubmit={handleSubmit}>
      <h2 className="ff-card-title">Batch Conversion</h2>
      <input
        type="file"
        multiple
        className="text-sm text-fileforgeMuted"
        onChange={(e) => setFiles(Array.from(e.target.files || []))}
      />
      <input
        className="ff-input"
        value={targetExt}
        onChange={(e) => setTargetExt(e.target.value.replace(/^\./, ""))}
        placeholder="Target extension"
      />
      <button type="submit" className="ff-btn-primary" disabled={loading}>
        {loading ? "Converting..." : "Batch Convert"}
      </button>
      {error && <p className="ff-status-error text-xs">{error}</p>}
      {result?.jobs && (
        <ul className="text-xs text-fileforgeMuted space-y-1">
          {result.jobs.map((j) => (
            <li key={j.jobId}>
              {j.jobId}:{" "}
              <span className={j.status === "completed" ? "ff-status-ok" : "ff-status-error"}>
                {j.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
