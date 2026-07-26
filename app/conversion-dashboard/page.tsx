import SingleConvert from "@/components/SingleConvert";
import BatchConvert from "@/components/BatchConvert";
import QueueConvert from "@/components/QueueConvert";
import Thumbnails from "@/components/Thumbnails";
import Compression from "@/components/Compression";

export default function ConversionDashboard() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-10 space-y-6">
      <h1 className="ff-title">FileForge Conversion Dashboard</h1>
      <p className="ff-card-body mb-6">
        Single, batch, and queued conversions, thumbnails, and video compression — all talking
        to the same FastAPI backend.
      </p>
      <div className="grid md:grid-cols-2 gap-6">
        <SingleConvert />
        <BatchConvert />
        <QueueConvert />
        <Thumbnails />
        <Compression />
      </div>
    </section>
  );
}
