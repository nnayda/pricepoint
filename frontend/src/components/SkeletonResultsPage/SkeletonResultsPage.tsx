function SkeletonBlock({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-status-vacant/40 ${className ?? ""}`} />;
}

function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8">
      <SkeletonBlock className="mb-4 h-5 w-40" />
      {Array.from({ length: lines }, (_, i) => (
        <SkeletonBlock key={i} className={`mb-2 h-4 ${i === lines - 1 ? "w-3/4" : "w-full"}`} />
      ))}
    </div>
  );
}

function SkeletonResultsPage() {
  return (
    <div
      className="mx-auto max-w-4xl space-y-grid p-4 sm:p-8"
      aria-label="Loading property data"
      role="status"
    >
      <span className="sr-only">Loading property data...</span>

      {/* Header skeleton */}
      <div className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8">
        <div className="flex items-start gap-4">
          <SkeletonBlock className="h-16 w-16 sm:h-20 sm:w-20" />
          <div className="flex-1">
            <SkeletonBlock className="mb-2 h-6 w-64" />
            <SkeletonBlock className="h-4 w-40" />
          </div>
        </div>
        <div className="mt-4 flex gap-6">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="text-center">
              <SkeletonBlock className="mx-auto mb-1 h-5 w-10" />
              <SkeletonBlock className="mx-auto h-3 w-8" />
            </div>
          ))}
        </div>
      </div>

      {/* Value section skeleton */}
      <SkeletonCard lines={4} />

      {/* Description skeleton */}
      <SkeletonCard lines={5} />

      {/* Schools skeleton */}
      <SkeletonCard lines={4} />

      {/* Details skeleton */}
      <SkeletonCard lines={6} />

      {/* Chart skeleton */}
      <div className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8">
        <SkeletonBlock className="mb-4 h-5 w-48" />
        <SkeletonBlock className="h-64 w-full" />
      </div>

      {/* Climate skeleton */}
      <SkeletonCard lines={2} />

      {/* Mortgage skeleton */}
      <SkeletonCard lines={4} />
    </div>
  );
}

export default SkeletonResultsPage;
