export default function DownloadsPage() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-8">
      <h1 className="ff-title mb-2">Get FileForge</h1>
      <p className="ff-card-body mb-4">
        FileForge 2.0 runs from source — clone it, install the conversion tools, and launch
        everything with one script.
      </p>

      <div className="grid md:grid-cols-3 gap-6">
        <DownloadCard
          title="Termux (Android)"
          description="The primary supported environment."
          details={[
            "pkg install git redis nodejs python",
            "git clone https://github.com/K1LLLAGT/File-Forge.git",
            "cd File-Forge && ./scripts/install_conversion_tools.sh",
            "./fileforge-launcher.sh",
          ]}
        />
        <DownloadCard
          title="Linux / macOS"
          description="Works anywhere ffmpeg, ImageMagick, Pandoc, Redis, and Node are installed."
          details={[
            "git clone https://github.com/K1LLLAGT/File-Forge.git",
            "cd File-Forge",
            "pip install -r backend/requirements.txt",
            "npm install && npm run dev",
          ]}
        />
        <DownloadCard
          title="CLI only"
          description="Just want the command-line client against a running backend?"
          details={[
            "chmod +x cli/fileforge-cli",
            "export FILEFORGE_API=http://127.0.0.1:8090",
            "./cli/fileforge-cli convert input.png jpg",
          ]}
        />
      </div>
    </section>
  );
}

function DownloadCard({
  title,
  description,
  details,
}: {
  title: string;
  description: string;
  details: string[];
}) {
  return (
    <div className="ff-card">
      <h2 className="ff-card-title">{title}</h2>
      <p className="ff-card-body mb-3">{description}</p>
      <ul className="text-xs text-fileforgeMuted list-disc list-inside space-y-1">
        {details.map((d, i) => (
          <li key={i} className="font-mono">{d}</li>
        ))}
      </ul>
    </div>
  );
}
