export default function CommunityPage() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-12 space-y-8">
      <h1 className="ff-title mb-2">Community &amp; Contributions</h1>
      <p className="ff-card-body mb-4">
        FileForge 2.0 is meant to stay a small, legible project. Use this page to link to your
        real GitHub repository, issue tracker, and contribution notes.
      </p>

      <div className="ff-card space-y-3">
        <h2 className="ff-card-title">GitHub</h2>
        <p className="ff-card-body">
          Repository: <span className="text-fileforgeAccent">github.com/K1LLLAGT/File-Forge</span>
        </p>
        <p className="ff-card-body">
          Use GitHub Issues to report bugs, request features, and discuss architecture changes.
        </p>
      </div>

      <div className="ff-card space-y-3">
        <h2 className="ff-card-title">Contribution Guidelines</h2>
        <p className="ff-card-body">Add a CONTRIBUTING.md describing:</p>
        <ul className="text-xs text-fileforgeMuted list-disc list-inside space-y-1">
          <li>How to set up a development environment</li>
          <li>Code style and linting rules</li>
          <li>How to propose new conversion routes in engine.py</li>
          <li>How to add new dashboard components</li>
        </ul>
      </div>
    </section>
  );
}
