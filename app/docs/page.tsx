export default function DocsPage() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-6">
      <h1 className="ff-title mb-2">Documentation</h1>
      <p className="ff-card-body">
        FileForge 2.0 is one project with four moving parts. Each has one job.
      </p>

      <DocBlock
        title="backend/"
        body="FastAPI app (server.py) plus the conversion engine (engine.py), batch runner (batch.py), Redis queue (ff_queue.py), thumbnails (thumbnails.py), and compression (compression.py). Run with backend/run_backend.sh."
      />
      <DocBlock
        title="app/ + components/"
        body="The Next.js App Router frontend: marketing pages, the single-file Conversion Engine page, and the unified Conversion Dashboard (SingleConvert, BatchConvert, QueueConvert, Thumbnails, Compression). API routes under app/api/ proxy to the FastAPI backend."
      />
      <DocBlock
        title="cli/fileforge-cli"
        body="A bash CLI that wraps every dashboard action (convert, batch, queue, queue-status, thumb-image, thumb-video, compress) as a single command, talking to the Next.js API layer on port 8090."
      />
      <DocBlock
        title="fileforge-launcher.sh"
        body="Starts Redis, the FastAPI backend, the queue worker, and the Next.js dev server together, then opens the Conversion Dashboard."
      />
    </section>
  );
}

function DocBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="ff-card">
      <h2 className="ff-card-title">{title}</h2>
      <p className="ff-card-body whitespace-pre-line">{body}</p>
    </div>
  );
}
