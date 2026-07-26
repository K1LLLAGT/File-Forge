export default function CliPage() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-8">
      <h1 className="ff-title mb-2">CLI &amp; API</h1>
      <p className="ff-card-body mb-4">
        Every dashboard action is available from the command line, and every command is a thin
        wrapper around the same HTTP API the dashboard itself calls.
      </p>

      <div className="grid md:grid-cols-2 gap-6">
        <CliBlock
          title="Single Conversion"
          command={`fileforge-cli convert input.png jpg`}
          description="Upload input.png and convert it to .jpg."
        />
        <CliBlock
          title="Batch Conversion"
          command={`fileforge-cli batch webp a.png b.png c.png`}
          description="Convert several files to the same target extension."
        />
        <CliBlock
          title="Queued Conversion"
          command={`fileforge-cli queue input.mp4 mp4
fileforge-cli queue-status ff-q-a1b2c3d4`}
          description="Enqueue a job on the Redis worker, then poll its status."
        />
        <CliBlock
          title="Thumbnails & Compression"
          command={`fileforge-cli thumb-image photo.jpg
fileforge-cli thumb-video clip.mp4
fileforge-cli compress clip.mp4 medium 23`}
          description="Generate thumbnails, or re-encode video at a given preset/CRF."
        />
      </div>

      <div className="ff-card">
        <h2 className="ff-card-title mb-2">Raw HTTP API</h2>
        <p className="ff-card-body mb-3">
          The backend expects <code>multipart/form-data</code>, not JSON — every conversion
          endpoint takes a file upload plus form fields.
        </p>
        <pre className="ff-code">
{`curl -X POST http://127.0.0.1:8091/convert \\
  -F "file=@input.png" \\
  -F "target_ext=jpg"`}
        </pre>
      </div>
    </section>
  );
}

function CliBlock({
  title,
  command,
  description,
}: {
  title: string;
  command: string;
  description: string;
}) {
  return (
    <div className="ff-card">
      <h2 className="ff-card-title">{title}</h2>
      <p className="ff-card-body mb-3">{description}</p>
      <pre className="ff-code whitespace-pre-wrap">{command}</pre>
    </div>
  );
}
