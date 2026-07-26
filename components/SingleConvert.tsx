"use client";

import { useState } from "react";

type ConvertResult = {
  jobId: string;
  status: string;
  downloadUrl?: string;
  error?: string;
};

export default function SingleConvert() {
  const [file, setFile] = useState<File | null>(null);
  const [targetExt, setTargetExt] = useState("mp4");
  const [result, setResult] = useState<ConvertResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return setError("Select a file first");
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("targetExt", targetExt);

      const res = await fetch("/api/convert", { method: "POST", body: form });
      const data = (await res.json()) as ConvertResult;
      if (!res.ok) setError(data.error || "Conversion failed");
      else setResult(data);
    } catch {
      setError("Network error contacting the dashboard API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="ff-card space-y-3" onSubmit={handleSubmit}>
      <h2 className="ff-card-title">Single Conversion</h2>
      <input
        type="file"
        className="text-sm text-fileforgeMuted"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <input
        className="ff-input"
        value={targetExt}
        onChange={(e) => setTargetExt(e.target.value.replace(/^\./, ""))}
        placeholder="Target extension (e.g. mp4, jpg)"
      />
      <button type="submit" className="ff-btn-primary" disabled={loading}>
        {loading ? "Converting..." : "Convert"}
      </button>
      {error && <p className="ff-status-error text-xs">{error}</p>}
      {result && (
        <p className="ff-status-ok text-xs">
          Job {result.jobId} status: {result.status}
          {result.downloadUrl && (
            <>
              {" "}
              ·{" "}
              <a href={`/api/download/${result.jobId}`} className="underline">
                download
              </a>
            </>
          )}
        </p>
      )}
    </form>
  );
}
