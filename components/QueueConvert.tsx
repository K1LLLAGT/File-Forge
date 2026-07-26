"use client";

import { useState } from "react";

type QueueStatus = { jobId?: string; status: string; error?: string };

export default function QueueConvert() {
  const [file, setFile] = useState<File | null>(null);
  const [targetExt, setTargetExt] = useState("mp4");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<QueueStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);

  async function enqueue(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return setError("Select a file first");
    setLoading(true);
    setError(null);
    setStatus(null);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("targetExt", targetExt);
      const res = await fetch("/api/queue-convert", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) setError(data.error || "Failed to enqueue job");
      else setJobId(data.jobId);
    } catch {
      setError("Network error contacting the dashboard API");
    } finally {
      setLoading(false);
    }
  }

  async function checkStatus() {
    if (!jobId) return;
    setPolling(true);
    try {
      const res = await fetch(`/api/queue-status/${jobId}`);
      const data = (await res.json()) as QueueStatus;
      setStatus(data);
    } catch {
      setError("Network error checking status");
    } finally {
      setPolling(false);
    }
  }

  return (
    <form className="ff-card space-y-3" onSubmit={enqueue}>
      <h2 className="ff-card-title">Queued Conversion</h2>
      <input
        type="file"
        className="text-sm text-fileforgeMuted"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <input
        className="ff-input"
        value={targetExt}
        onChange={(e) => setTargetExt(e.target.value.replace(/^\./, ""))}
        placeholder="Target extension"
      />
      <button type="submit" className="ff-btn-primary" disabled={loading}>
        {loading ? "Enqueuing..." : "Enqueue"}
      </button>
      {error && <p className="ff-status-error text-xs">{error}</p>}

      {jobId && (
        <div className="space-y-2">
          <p className="ff-status-ok text-xs">Job ID: {jobId}</p>
          <button type="button" className="ff-btn-secondary" onClick={checkStatus} disabled={polling}>
            {polling ? "Checking..." : "Check Status"}
          </button>
        </div>
      )}
      {status && (
        <p className="text-xs text-fileforgeMuted">
          Status:{" "}
          <span className={status.status === "completed" ? "ff-status-ok" : "ff-status-error"}>
            {status.status}
          </span>
        </p>
      )}
    </form>
  );
}
