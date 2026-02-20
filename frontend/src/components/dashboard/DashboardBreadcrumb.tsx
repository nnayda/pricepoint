interface DashboardBreadcrumbProps {
  city: string;
  neighborhood: string;
  address: string;
}

function DashboardBreadcrumb({ city, neighborhood, address }: DashboardBreadcrumbProps) {
  const crumbs = [city, neighborhood, address];

  return (
    <div
      className="sticky top-16 z-40 flex h-9 items-center gap-2 border-b border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] px-6"
      style={{ fontFamily: "var(--font-db-sans)", marginTop: "64px" }}
    >
      {crumbs.map((crumb, i) => (
        <span key={crumb} className="flex items-center gap-2">
          {i > 0 && (
            <svg
              className="h-3 w-3 text-[var(--color-db-text-muted)]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          )}
          <span
            className={`text-xs ${i === crumbs.length - 1 ? "font-medium text-[var(--color-db-text-primary)]" : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"} cursor-pointer`}
          >
            {crumb}
          </span>
        </span>
      ))}
    </div>
  );
}

export default DashboardBreadcrumb;
