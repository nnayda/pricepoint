interface NoDataOverlayProps {
  message?: string;
}

function NoDataOverlay({
  message = "Data not yet available for this property.",
}: NoDataOverlayProps) {
  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-[var(--radius-db-md)] bg-[var(--th-bg-surface)]/80 backdrop-blur-[2px]">
      <div className="flex flex-col items-center gap-2 px-4 text-center">
        <svg
          className="h-8 w-8 text-[var(--color-db-text-muted)]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605"
          />
        </svg>
        <p className="text-sm font-medium text-[var(--color-db-text-secondary)]">{message}</p>
        <p className="text-xs text-[var(--color-db-text-muted)]">
          Request data collection to populate this section.
        </p>
      </div>
    </div>
  );
}

export default NoDataOverlay;
