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
      className="mx-auto max-w-7xl space-y-grid p-4 sm:p-8"
      aria-label="Loading property data"
      role="status"
    >
      <span className="sr-only">Loading property data...</span>

      {/* Zone A: Hero header skeleton */}
      <div className="overflow-hidden rounded-lg bg-bg-card/80 shadow-soft backdrop-blur-md">
        <SkeletonBlock className="h-48 w-full sm:h-64 md:h-72 lg:h-80" />
        <div className="p-5 sm:p-8">
          <SkeletonBlock className="mb-2 h-6 w-64" />
          <SkeletonBlock className="h-4 w-40" />
          <div className="mt-4 flex gap-6">
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="text-center">
                <SkeletonBlock className="mx-auto mb-1 h-5 w-10" />
                <SkeletonBlock className="mx-auto h-3 w-8" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Zone B: Dashboard grid skeleton */}
      <div className="grid grid-cols-1 gap-grid lg:grid-cols-12">
        <div className="space-y-grid lg:col-span-5">
          <SkeletonCard lines={4} />
          <SkeletonCard lines={5} />
          <SkeletonCard lines={4} />
          <SkeletonCard lines={6} />
          <SkeletonCard lines={2} />
        </div>
        <div className="lg:col-span-7">
          <div className="rounded-lg bg-bg-card/80 shadow-soft backdrop-blur-md">
            <SkeletonBlock className="h-10 w-full" />
            <SkeletonBlock className="h-[400px] w-full lg:h-[500px] xl:h-[600px]" />
            <div className="p-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {Array.from({ length: 4 }, (_, i) => (
                  <div key={i}>
                    <SkeletonBlock className="mb-1 h-3 w-16" />
                    <SkeletonBlock className="h-4 w-12" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Zone C: Full-width bottom skeletons */}
      <div className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8">
        <SkeletonBlock className="mb-4 h-5 w-48" />
        <SkeletonBlock className="h-64 w-full" />
      </div>

      <SkeletonCard lines={4} />
    </div>
  );
}

export default SkeletonResultsPage;
