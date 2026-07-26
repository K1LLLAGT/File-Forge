"use client";

import { useState } from "react";

export default function Thumbnails() {
  const [imageThumb, setImageThumb] = useState<string | null>(null);
  const [videoThumb, setVideoThumb] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function uploadImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/thumbnail/image", { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Thumbnail failed");
        return;
      }
      const blob = await res.blob();
      setImageThumb(URL.createObjectURL(blob));
    } catch {
      setError("Network error contacting the dashboard API");
    }
  }

  async function uploadVideo(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/thumbnail/video", { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Thumbnail failed");
        return;
      }
      const blob = await res.blob();
      setVideoThumb(URL.createObjectURL(blob));
    } catch {
      setError("Network error contacting the dashboard API");
    }
  }

  return (
    <div className="ff-card space-y-3">
      <h2 className="ff-card-title">Thumbnails</h2>
      {error && <p className="ff-status-error text-xs">{error}</p>}
      <div className="space-y-2">
        <label className="ff-label">Image thumbnail</label>
        <input type="file" accept="image/*" className="text-sm text-fileforgeMuted" onChange={uploadImage} />
        {imageThumb && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={imageThumb} alt="Generated thumbnail" className="w-32 h-32 object-cover rounded-fileforge border border-fileforgeBorder" />
        )}
      </div>
      <div className="space-y-2">
        <label className="ff-label">Video thumbnail (first frame)</label>
        <input type="file" accept="video/*" className="text-sm text-fileforgeMuted" onChange={uploadVideo} />
        {videoThumb && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={videoThumb} alt="Generated video thumbnail" className="w-32 h-32 object-cover rounded-fileforge border border-fileforgeBorder" />
        )}
      </div>
    </div>
  );
}
