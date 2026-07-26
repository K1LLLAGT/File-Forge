export default function FeaturesPage() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-8">
      <h1 className="ff-title mb-2">Features</h1>
      <p className="ff-card-body mb-4">
        FileForge 2.0 is one FastAPI backend, one Redis-backed worker, and one Next.js
        dashboard, sharing a single ffmpeg / ImageMagick / Pandoc conversion engine.
      </p>

      <FeatureBlock
        title="Single Conversion"
        body="Upload a file, choose a target extension, and convert it through the shared engine.py dispatcher — images, video, audio, and documents all route through one call."
      />
      <FeatureBlock
        title="Batch Conversion"
        body="Convert several files to the same target extension concurrently, with per-file success/error reporting."
      />
      <FeatureBlock
        title="Queued Conversion"
        body="Hand a job to the Redis queue and poll /queue-status/{jobId} instead of holding the request open — ideal for large video files on a phone-class CPU."
      />
      <FeatureBlock
        title="Thumbnails"
        body="Generate a PNG thumbnail from an image or a video's first frame."
      />
      <FeatureBlock
        title="Video Compression"
        body="Re-encode video with libx264/aac at a configurable preset and CRF."
      />
      <FeatureBlock
        title="CLI & Launcher"
        body="The fileforge-cli wraps every endpoint in a single command, and fileforge-launcher.sh brings up Redis, the backend, the worker, and the dashboard in one shot — all with Termux-safe shebangs and paths."
      />
    </section>
  );
}

function FeatureBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="ff-card">
      <h2 className="ff-card-title">{title}</h2>
      <p className="ff-card-body whitespace-pre-line">{body}</p>
    </div>
  );
}
