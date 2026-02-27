import { useState } from "react";
import { submitDataRequest } from "../services/property";

interface DataRequestBannerProps {
  address: string;
  lat: number;
  lon: number;
  onDismiss: () => void;
}

function DataRequestBanner({ address, lat, lon, onDismiss }: DataRequestBannerProps) {
  const [expanded, setExpanded] = useState(false);
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
    <div
      className="border-b border-[var(--color-db-yellow-muted)] bg-[var(--color-db-yellow-muted)]"
      role="alert"
    >
      <div className="mx-auto flex max-w-[1680px] items-center gap-3 px-4 py-2.5">
        {/* Icon */}
        <svg
          className="h-5 w-5 shrink-0 text-[var(--color-db-yellow)]"
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

        {/* Message */}
        <p className="flex-1 text-sm text-[var(--color-db-text-primary)]">
          {submitted ? (
            <>
              Request submitted — we'll collect data for this property soon.
              {email.trim() ? " You'll be notified when it's ready." : ""}
            </>
          ) : (
            <>
              This property isn't in our database yet. Some data may be unavailable.
              {!expanded && (
                <button
                  onClick={() => setExpanded(true)}
                  className="ml-2 font-medium text-[var(--color-db-accent)] hover:underline"
                >
                  Request data collection
                </button>
              )}
            </>
          )}
        </p>

        {/* Dismiss */}
        <button
          onClick={onDismiss}
          className="shrink-0 rounded p-1 text-[var(--color-db-text-secondary)] transition-colors hover:bg-black/5"
          aria-label="Dismiss banner"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Expandable request form */}
      {expanded && !submitted && (
        <div className="border-t border-[var(--color-db-yellow)]/20 bg-[var(--color-db-surface)] px-4 py-3">
          <div className="mx-auto flex max-w-[1680px] flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <label className="mb-1 block text-xs font-medium text-[var(--color-db-text-secondary)]">
                Email for notification (optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] px-3 py-1.5 text-sm text-[var(--color-db-text-primary)] outline-none placeholder:text-[var(--color-db-text-muted)] focus:border-[var(--color-db-accent)]"
              />
            </div>

            {error && <p className="w-full text-sm text-[var(--color-db-red)]">{error}</p>}

            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="rounded-[var(--radius-db-sm)] bg-[var(--color-db-accent)] px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-db-accent-hover)] disabled:opacity-50"
            >
              {submitting ? "Submitting..." : "Submit Request"}
            </button>
            <button
              onClick={() => setExpanded(false)}
              className="rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] px-4 py-1.5 text-sm font-medium text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-alt)]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DataRequestBanner;
