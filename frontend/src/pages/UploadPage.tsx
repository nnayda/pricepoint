import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import DashboardNav from "../components/dashboard/DashboardNav";
import { uploadRedfinFiles } from "../services/upload";
import type { UploadResult } from "../services/upload";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function UploadPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  if (isLoading) return null;
  if (!isAuthenticated) return <Navigate to="/signin" replace />;

  function addFiles(incoming: File[]) {
    const htmlFiles = incoming.filter((f) => f.name.endsWith(".html"));
    setSelectedFiles((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...htmlFiles.filter((f) => !names.has(f.name))];
    });
    setResult(null);
    setError(null);
  }

  function handleFileInput(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
  }

  function removeFile(name: string) {
    setSelectedFiles((prev) => prev.filter((f) => f.name !== name));
  }

  async function handleUpload() {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setProgress(0);
    setResult(null);
    setError(null);
    try {
      const res = await uploadRedfinFiles(selectedFiles, setProgress);
      setResult(res);
      setSelectedFiles([]);
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="font-db-sans min-h-screen" style={{ backgroundColor: "var(--color-db-bg)" }}>
      <DashboardNav />
      <div className="flex min-h-screen items-center justify-center px-4 pt-16">
        <div
          className="w-full max-w-lg rounded-xl p-8"
          style={{
            backgroundColor: "var(--th-bg-surface)",
            boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
          }}
        >
          <h1 className="mb-6 text-2xl font-bold" style={{ color: "var(--color-db-text-primary)" }}>
            Upload Redfin Listings
          </h1>

          {result && result.saved.length > 0 && (
            <div
              className="mb-4 rounded-lg px-4 py-3 text-sm"
              role="status"
              style={{
                backgroundColor: "rgba(34, 197, 94, 0.1)",
                color: "#16a34a",
              }}
            >
              <p className="font-medium">
                {result.saved.length} file{result.saved.length > 1 ? "s" : ""} uploaded successfully
              </p>
              <ul className="mt-1 list-inside list-disc">
                {result.saved.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
              {result.dag_triggered ? (
                <p className="mt-2 font-medium">Processing pipeline started automatically.</p>
              ) : (
                <p
                  className="mt-2 font-medium"
                  style={{ color: "var(--color-db-text-secondary)" }}
                >
                  Files saved. Automatic processing could not be started — listings will be
                  processed on the next scheduled run.
                </p>
              )}
            </div>
          )}

          {result && result.errors.length > 0 && (
            <div
              className="mb-4 rounded-lg px-4 py-3 text-sm"
              role="alert"
              style={{
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                color: "#ef4444",
              }}
            >
              <p className="font-medium">Some files had errors</p>
              <ul className="mt-1 list-inside list-disc">
                {result.errors.map((err) => (
                  <li key={err}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {error && (
            <div
              className="mb-4 rounded-lg px-4 py-3 text-sm"
              role="alert"
              style={{
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                color: "#ef4444",
              }}
            >
              {error}
            </div>
          )}

          {/* Drop zone */}
          <div
            role="button"
            tabIndex={0}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
            }}
            data-testid="drop-zone"
            className="mb-4 flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 transition-colors"
            style={{
              borderColor: dragOver
                ? "var(--color-db-accent)"
                : "var(--color-db-border, rgba(0,0,0,0.15))",
              backgroundColor: dragOver ? "rgba(59, 130, 246, 0.05)" : "transparent",
            }}
          >
            <svg
              className="h-10 w-10"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
              style={{ color: "var(--color-db-text-tertiary)" }}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
            <p className="text-sm" style={{ color: "var(--color-db-text-secondary)" }}>
              Drag &amp; drop .html files here, or{" "}
              <span style={{ color: "var(--color-db-accent)" }} className="font-medium">
                Browse Files
              </span>
            </p>
            <p className="text-xs" style={{ color: "var(--color-db-text-muted)" }}>
              Only Redfin .html listing pages are accepted
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".html"
              multiple
              className="hidden"
              onChange={handleFileInput}
              data-testid="file-input"
            />
          </div>

          {/* File list */}
          {selectedFiles.length > 0 && (
            <div className="mb-4 flex flex-col gap-2">
              {selectedFiles.map((file) => (
                <div
                  key={file.name}
                  className="flex items-center justify-between rounded-lg px-3 py-2"
                  style={{
                    backgroundColor: "var(--color-db-surface, rgba(0,0,0,0.03))",
                    border: "1px solid var(--color-db-border, rgba(0,0,0,0.08))",
                  }}
                >
                  <div className="min-w-0 flex-1">
                    <p
                      className="truncate text-sm font-medium"
                      style={{ color: "var(--color-db-text-primary)" }}
                    >
                      {file.name}
                    </p>
                    <p className="text-xs" style={{ color: "var(--color-db-text-muted)" }}>
                      {formatSize(file.size)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(file.name);
                    }}
                    aria-label={`Remove ${file.name}`}
                    className="ml-2 rounded p-1 transition-colors hover:bg-black/5"
                    style={{ color: "var(--color-db-text-tertiary)" }}
                  >
                    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Progress bar */}
          {uploading && (
            <div className="mb-4">
              <div
                className="h-2 overflow-hidden rounded-full"
                style={{ backgroundColor: "var(--color-db-border, rgba(0,0,0,0.1))" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${progress}%`,
                    backgroundColor: "var(--color-db-accent)",
                  }}
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
              <p
                className="mt-1 text-center text-xs"
                style={{ color: "var(--color-db-text-muted)" }}
              >
                Uploading... {progress}%
              </p>
            </div>
          )}

          {/* Upload button */}
          <button
            type="button"
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || uploading}
            className="w-full font-semibold text-white transition-opacity disabled:opacity-60"
            style={{
              height: "40px",
              borderRadius: "8px",
              backgroundColor: "var(--color-db-accent)",
            }}
          >
            {uploading
              ? "Uploading..."
              : `Upload ${selectedFiles.length || ""} File${selectedFiles.length !== 1 ? "s" : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}

export default UploadPage;
