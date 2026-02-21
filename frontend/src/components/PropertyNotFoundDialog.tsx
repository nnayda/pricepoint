import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitDataRequest } from "../services/property";

interface PropertyNotFoundDialogProps {
  address: string;
  lat: number;
  lon: number;
}

function PropertyNotFoundDialog({ address, lat, lon }: PropertyNotFoundDialogProps) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      await submitDataRequest({
        address,
        lat,
        lon,
        email: email.trim() || undefined,
      });
      setSubmitted(true);
    } catch {
      setError("Failed to submit request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-[var(--radius-db-lg)] border border-[var(--color-db-border)] bg-[var(--color-db-surface)] p-6 shadow-lg">
        {submitted ? (
          <>
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-db-green-muted)]">
              <svg
                className="h-6 w-6 text-[var(--color-db-green)]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-semibold text-[var(--color-db-text-primary)]">
              Request submitted
            </h2>
            <p className="mb-6 text-sm text-[var(--color-db-text-secondary)]">
              We'll process this property soon.
              {email.trim() ? " You'll receive a notification when the data is ready." : ""}
            </p>
            <button
              onClick={() => navigate("/")}
              className="w-full rounded-[var(--radius-db-sm)] bg-[var(--color-db-accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-db-accent-hover)]"
            >
              Back to Search
            </button>
          </>
        ) : (
          <>
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-db-yellow-muted)]">
              <svg
                className="h-6 w-6 text-[var(--color-db-yellow)]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-semibold text-[var(--color-db-text-primary)]">
              Property not in our database
            </h2>
            <p className="mb-1 text-sm text-[var(--color-db-text-secondary)]">
              We don't have data for this property yet. Submit a request and we'll collect and
              analyze it.
            </p>
            <p className="mb-4 text-xs text-[var(--color-db-text-muted)] break-all">{address}</p>

            <label className="mb-1 block text-xs font-medium text-[var(--color-db-text-secondary)]">
              Email for notification (optional)
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="mb-4 w-full rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] px-3 py-2 text-sm text-[var(--color-db-text-primary)] outline-none placeholder:text-[var(--color-db-text-muted)] focus:border-[var(--color-db-accent)]"
            />

            {error && (
              <p className="mb-3 text-sm text-[var(--color-db-red)]">{error}</p>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => navigate("/")}
                className="flex-1 rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] px-4 py-2.5 text-sm font-medium text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-alt)]"
              >
                Go Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 rounded-[var(--radius-db-sm)] bg-[var(--color-db-accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-db-accent-hover)] disabled:opacity-50"
              >
                {submitting ? "Submitting..." : "Submit Request"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default PropertyNotFoundDialog;
