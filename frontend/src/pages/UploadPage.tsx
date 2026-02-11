import { useCallback, useRef, useState } from "react";
import axios from "axios";

interface UploadResult {
  saved: string[];
  errors: string[];
}

function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const htmlFiles = Array.from(incoming).filter((f) => f.name.endsWith(".html"));
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...htmlFiles.filter((f) => !names.has(f.name))];
    });
    setResult(null);
    setError(null);
  }

  function removeFile(name: string) {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  }, []);

  async function handleUpload() {
    if (files.length === 0) return;
    setUploading(true);
    setResult(null);
    setError(null);

    const form = new FormData();
    files.forEach((f) => form.append("files", f));

    try {
      const { data } = await axios.post<UploadResult>("/api/upload/redfin", form);
      setResult(data);
      if (data.saved.length > 0) setFiles([]);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data) {
        const body = err.response.data as UploadResult;
        if (body.errors) {
          setResult(body);
        } else {
          setError("Upload failed. Please try again.");
        }
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-grid p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-text-pri">Upload Redfin Listings</h1>
      <p className="text-sm text-text-sec">
        Upload saved Redfin property HTML files. They will be picked up automatically by the
        processing pipeline.
      </p>

      <section
        aria-label="File upload"
        className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
      >
        {/* Drop zone */}
        <div
          role="button"
          tabIndex={0}
          aria-label="Drop HTML files here or click to browse"
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 transition-colors ${
            dragOver
              ? "border-brand-blue bg-brand-blue/5"
              : "border-status-vacant hover:border-brand-blue"
          }`}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="mb-3 h-10 w-10 text-text-sec"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
          <p className="text-sm font-medium text-text-pri">
            Drop .html files here or click to browse
          </p>
          <p className="mt-1 text-xs text-text-sec">Only .html files are accepted</p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".html"
          multiple
          className="hidden"
          data-testid="file-input"
          onChange={(e) => addFiles(e.target.files)}
        />

        {/* File list */}
        {files.length > 0 && (
          <ul className="mt-4 space-y-2" aria-label="Selected files">
            {files.map((f) => (
              <li
                key={f.name}
                className="flex items-center justify-between rounded-md bg-bg-main px-3 py-2 text-sm"
              >
                <span className="truncate text-text-pri">{f.name}</span>
                <button
                  onClick={() => removeFile(f.name)}
                  aria-label={`Remove ${f.name}`}
                  className="ml-2 shrink-0 text-xs text-status-rented hover:underline"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Upload button */}
        <button
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
          className="mt-4 w-full rounded-md bg-brand-blue px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {uploading
            ? "Uploading..."
            : `Upload ${files.length} file${files.length !== 1 ? "s" : ""}`}
        </button>

        {/* Result feedback */}
        {result && result.saved.length > 0 && (
          <div
            role="status"
            className="mt-4 rounded-md bg-green-50 px-4 py-3 text-sm text-green-800"
          >
            Successfully uploaded {result.saved.length} file
            {result.saved.length !== 1 ? "s" : ""}.
          </div>
        )}
        {result && result.errors.length > 0 && (
          <div role="alert" className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">
            <p className="font-medium">Some files had errors:</p>
            <ul className="mt-1 list-inside list-disc">
              {result.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </div>
        )}
        {error && (
          <div role="alert" className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        )}
      </section>
    </div>
  );
}

export default UploadPage;
