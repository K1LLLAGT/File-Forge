"use client";

import { useState } from "react";
import DropZone from "@/components/DropZone";

type ConvertResult = {
  jobId: string;
  status: string;
  downloadUrl?: string;
  error?: string;
};

export default function ConversionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [targetExt, setTargetExt] = useState("jpg");
  const [result, setResult] = useState<ConvertResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Select a file first.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("targetExt", targetExt);

      const res = await fetch("/api/convert", { method: "POST", body: formData });
      const data = (await res.json()) as ConvertResult;

      if (!res.ok) {
        throw new Error(data.error || "Conversion failed");
      }
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const downloadHref = result?.downloadUrl ? `/api/download/${result.jobId}` : null;

  return (
    <section className="max-w-2xl mx-auto px-6 py-12 space-y-6">
      <div>
        <h1 className="ff-title mb-2">Conversion Engine</h1>
        <p className="ff-card-body">
          Upload a file and pick a target extension. This calls the real FileForge backend —
          not a mock.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="ff-card space-y-4">
        <DropZone onFileSelected={setFile} />

        <div>
          <label className="ff-label">Target extension</label>
          <input
            className="ff-input"
            value={targetExt}
            onChange={(e) => setTargetExt(e.target.value.replace(/^\./, ""))}
            placeholder="e.g. mp4, jpg, mp3, pdf"
          />
        </div>

        <button type="submit" className="ff-btn-primary" disabled={loading}>
          {loading ? "Converting…" : "Convert"}
        </button>

        {error && <p className="ff-status-error text-xs">{error}</p>}
      </form>

      {result && (
        <div className="ff-card space-y-2">
          <h2 className="ff-card-title">
            {result.status === "completed" ? "Conversion Completed" : "Conversion Failed"}
          </h2>
          <p className="ff-card-body">
            Job ID: <span className="ff-status-ok">{result.jobId}</span>
          </p>
          <p className="ff-card-body">
            Status: <span className={result.status === "completed" ? "ff-status-ok" : "ff-status-error"}>
              {result.status}
            </span>
          </p>
          {downloadHref && (
            <a href={downloadHref} className="ff-btn-secondary inline-block mt-2">
              Download Output
            </a>
          )}
        </div>
      )}
    </section>
  );
}
