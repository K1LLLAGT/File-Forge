"use client";

import { useCallback, useState } from "react";

export default function DropZone({ onFileSelected }: { onFileSelected: (file: File) => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) {
        setFileName(file.name);
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setFileName(file.name);
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  return (
    <div className="space-y-2">
      <div
        className={`border-2 border-dashed rounded-fileforge p-6 text-center cursor-pointer transition ${
          isDragging ? "border-fileforgeAccent bg-fileforgeCard" : "border-fileforgeBorder bg-fileforgeBg"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragging(false);
        }}
        onDrop={handleDrop}
        onClick={() => document.getElementById("ff-file-input")?.click()}
      >
        <p className="text-sm text-fileforgeMuted">Drag &amp; drop a file here, or click to browse.</p>
        {fileName && <p className="text-xs text-fileforgeAccent mt-2">Selected: {fileName}</p>}
      </div>

      <input id="ff-file-input" type="file" className="hidden" onChange={handleChange} />
    </div>
  );
}
