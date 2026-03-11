import { createContext, useContext, useState } from "react";
import { createPortal } from "react-dom";

const CardExpandedContext = createContext(false);

/** Returns true when this card is rendered in fullscreen expanded mode. */
// eslint-disable-next-line react-refresh/only-export-components
export function useCardExpanded(): boolean {
  return useContext(CardExpandedContext);
}

interface DashboardCardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
  expandable?: boolean;
  title?: string;
}

function DashboardCard({
  children,
  className = "",
  padding = true,
  expandable = false,
  title,
}: DashboardCardProps) {
  const [expanded, setExpanded] = useState(false);

  const card = (
    <div
      className={`relative rounded-[var(--radius-db-md)] border border-[var(--th-border-subtle)] bg-[var(--th-bg-surface)] shadow-[var(--th-shadow-card)] ${padding ? "p-5" : ""} ${className}`}
    >
      {expandable && !expanded && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="absolute right-2 top-2 z-10 rounded p-1 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-alt)] hover:text-[var(--color-db-text-secondary)]"
          aria-label="Expand"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="9 1 13 1 13 5" />
            <polyline points="5 13 1 13 1 9" />
            <line x1="13" y1="1" x2="8" y2="6" />
            <line x1="1" y1="13" x2="6" y2="8" />
          </svg>
        </button>
      )}
      {children}
    </div>
  );

  if (!expanded) return card;

  return (
    <>
      {/* Placeholder to preserve layout */}
      <div
        className={`rounded-[var(--radius-db-md)] border border-[var(--th-border-subtle)] bg-[var(--th-bg-surface)] shadow-[var(--th-shadow-card)] ${padding ? "p-5" : ""} ${className}`}
        style={{ visibility: "hidden" }}
      >
        {children}
      </div>
      {/* Portal to body so overlay is above everything including Leaflet maps */}
      {createPortal(
        <CardExpandedContext.Provider value={true}>
          <div
            className="fixed inset-0 flex items-center justify-center bg-black/60 p-8"
            style={{ zIndex: 10000 }}
          >
            <div
              className={`relative flex h-full w-full flex-col rounded-[var(--radius-db-md)] border border-[var(--th-border-subtle)] bg-[var(--th-bg-surface)] shadow-[var(--th-shadow-card)] ${padding ? "p-8" : ""}`}
            >
              <div className="mb-4 flex shrink-0 items-center justify-between">
                {title && (
                  <h3 className="text-base font-semibold text-[var(--color-db-text-primary)]">
                    {title}
                  </h3>
                )}
                <button
                  type="button"
                  onClick={() => setExpanded(false)}
                  className="ml-auto rounded p-1.5 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-alt)] hover:text-[var(--color-db-text-secondary)]"
                  aria-label="Close"
                >
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="4" y1="4" x2="12" y2="12" />
                    <line x1="12" y1="4" x2="4" y2="12" />
                  </svg>
                </button>
              </div>
              <div className="min-h-0 flex-1">{children}</div>
            </div>
          </div>
        </CardExpandedContext.Provider>,
        document.body,
      )}
    </>
  );
}

export default DashboardCard;
