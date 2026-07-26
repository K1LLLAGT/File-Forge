"use client";

import { useState } from "react";

type CompressResult = { jobId: string; status: string; downloadUrl?: string; error?: string };

export default function Compression() {
  const [file, setFile] = useState<File | null>(null);
  const [preset, setPreset] = useState("medium");
  const [crf, setCrf] = useState("23");
  const [result, setResult] = useState<CompressResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return setError("Select a video file first");
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("preset", preset);
      form.append("crf", crf);
      const res = await fetch("/api/compress/video", { method: "POST", body: form });
      const data = (await res.json()) as CompressResult;
      if (!res.ok) setError(data.error || "Compression failed");
      else setResult(data);
    } catch {
      setError("Network error contacting the dashboard API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="ff-card space-y-3" onSubmit={handleSubmit}>
      <h2 className="ff-card-title">Video Compression</h2>
      <input
        type="file"
        accept="video/*"
        className="text-sm text-fileforgeMuted"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="ff-label">Preset</label>
          <input
            className="ff-input"
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
            placeholder="ultrafast, fast, medium, slow"
          />
        </div>
        <div>
          <label className="ff-label">CRF (0-51)</label>
          <input
            className="ff-input"
            value={crf}
            onChange={(e) => setCrf(e.target.value)}
            inputMode="numeric"
          />
        </div>
      </div>
      <button type="submit" className="ff-btn-primary" disabled={loading}>
        {loading ? "Compressing..." : "Compress"}
      </button>
      {error && <p className="ff-status-error text-xs">{error}</p>}
      {result && (
        <p className="ff-status-ok text-xs">
          Job {result.jobId} status: {result.status}
          {result.downloadUrl && (
            <>
              {" "}
              ·{" "}
              <a href={`/api/compress/download/${result.jobId}`} className="underline">
                download
              </a>
            </>
          )}
        </p>
      )}
    </form>
  );
}
