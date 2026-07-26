export default function HomePage() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-10">
      <div>
        <h1 className="ff-hero-title mb-4">FileForge 2.0</h1>
        <p className="ff-hero-subtitle mb-6">
          Unified file conversion: single, batch, and queued conversions, thumbnails,
          and video compression — one FastAPI backend, one Next.js dashboard, one CLI.
        </p>
        <div className="flex flex-wrap gap-4">
          <a href="/conversion-dashboard" className="ff-btn-primary">
            Open Conversion Dashboard
          </a>
          <a href="/docs" className="ff-btn-secondary">
            View Documentation
          </a>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <FeatureCard
          title="Single & Batch Conversion"
          description="Convert one file or many at once through the same ffmpeg / ImageMagick / Pandoc abstraction layer."
        />
        <FeatureCard
          title="Redis-Backed Queue"
          description="Hand off large jobs to a background worker and poll for status instead of blocking on the request."
        />
        <FeatureCard
          title="Thumbnails & Compression"
          description="Generate image and video thumbnails, or re-encode video with configurable preset and CRF."
        />
      </div>

      <div className="ff-card">
        <h2 className="ff-card-title mb-3">Quick CLI Preview</h2>
        <pre className="ff-code">
{`fileforge convert input.png jpg
fileforge queue input.mp4 mp4
fileforge queue-status ff-q-a1b2c3d4
fileforge compress input.mp4 medium 23`}
        </pre>
      </div>
    </section>
  );
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="ff-card">
      <h2 className="ff-card-title">{title}</h2>
      <p className="ff-card-body">{description}</p>
    </div>
  );
}
