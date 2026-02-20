function DashboardNav() {
  return (
    <nav
      className="fixed top-0 right-0 left-0 z-50 flex h-16 items-center justify-between border-b border-[var(--color-db-border-subtle)] px-6"
      style={{
        backgroundColor: "rgba(15, 17, 23, 0.85)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        fontFamily: "var(--font-db-sans)",
      }}
    >
      <div className="flex items-center gap-6">
        <a href="/" className="flex items-center gap-2 text-[var(--color-db-text-primary)]">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-db-accent)]">
            <span className="text-sm font-bold text-white">P</span>
          </div>
          <span className="text-base font-semibold">PricePoint</span>
        </a>
        <div className="hidden items-center gap-1 rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] bg-[var(--color-db-surface)] px-3 py-1.5 sm:flex">
          <svg
            className="h-4 w-4 text-[var(--color-db-text-tertiary)]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <span className="text-xs text-[var(--color-db-text-muted)]">Search address...</span>
          <kbd className="ml-8 rounded border border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] px-1.5 py-0.5 text-[10px] text-[var(--color-db-text-muted)]">
            /
          </kbd>
        </div>
      </div>
      <div className="flex items-center gap-1">
        {/* Upload */}
        <button
          type="button"
          aria-label="Upload listing data"
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </button>

        {/* Comparison mode toggle */}
        <button
          type="button"
          aria-label="Comparison mode"
          className="relative rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 4.5v15m6-15v15M4.5 4.5h15c.828 0 1.5.672 1.5 1.5v12c0 .828-.672 1.5-1.5 1.5h-15A1.5 1.5 0 013 18V6c0-.828.672-1.5 1.5-1.5z" />
          </svg>
        </button>

        {/* Saved listings */}
        <button
          type="button"
          aria-label="Saved listings"
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
          </svg>
        </button>

        {/* Theme toggle */}
        <button
          type="button"
          aria-label="Toggle theme"
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
          </svg>
        </button>

        {/* Notifications */}
        <button
          type="button"
          aria-label="Notifications"
          className="rounded-[var(--radius-db-sm)] p-2 text-[var(--color-db-text-tertiary)] transition-colors hover:bg-[var(--color-db-surface-hover)] hover:text-[var(--color-db-text-secondary)]"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
            />
          </svg>
        </button>

        {/* User avatar menu */}
        <button
          type="button"
          aria-label="User menu"
          className="ml-1"
        >
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[var(--color-db-accent)] to-[var(--color-db-cyan)] p-[2px]">
            <div className="flex h-full w-full items-center justify-center rounded-full bg-[var(--color-db-surface)]">
              <span className="text-xs font-semibold text-[var(--color-db-text-primary)]">JD</span>
            </div>
          </div>
        </button>
      </div>
    </nav>
  );
}

export default DashboardNav;
