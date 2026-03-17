import DashboardNav from "../components/dashboard/DashboardNav";
import { useModelMethodology } from "../hooks/useModelMethodology";
import ModelDesignSection from "../components/methodology/ModelDesignSection";
import ModelFitSection from "../components/methodology/ModelFitSection";
import FeatureAnalysisSection from "../components/methodology/FeatureAnalysisSection";

function SkeletonBlock({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-[var(--radius-db-md)] bg-[var(--color-db-surface-alt)] ${className}`}
    />
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6" data-testid="methodology-loading">
      <SkeletonBlock className="h-8 w-48" />
      <SkeletonBlock className="h-64" />
      <SkeletonBlock className="h-8 w-36" />
      <div className="grid grid-cols-5 gap-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <SkeletonBlock key={i} className="h-20" />
        ))}
      </div>
      <SkeletonBlock className="h-8 w-40" />
      <SkeletonBlock className="h-96" />
    </div>
  );
}

function ModelMethodologyPage() {
  const { methodology, featureCatalog, loading, error } = useModelMethodology();

  return (
    <div
      className="flex min-h-screen flex-col font-db-sans"
      style={{ backgroundColor: "var(--th-bg-base)" }}
    >
      <DashboardNav />

      <main className="mx-auto w-full max-w-6xl px-6 pb-16 pt-24">
        <h1 className="mb-8 text-2xl font-bold text-[var(--color-db-text-primary)]">
          Model Methodology
        </h1>

        {loading && <LoadingSkeleton />}

        {!loading && error && (
          <div
            className="rounded-[var(--radius-db-md)] border border-red-500/30 p-6 text-center"
            style={{ backgroundColor: "var(--th-bg-surface)" }}
            role="alert"
          >
            <p className="text-sm text-red-400">
              Unable to load model methodology. The ML service may be unavailable.
            </p>
            <p className="mt-1 text-xs text-[var(--color-db-text-tertiary)]">{error}</p>
          </div>
        )}

        {!loading && !error && !methodology && (
          <div
            className="rounded-[var(--radius-db-md)] border border-[var(--th-border-subtle)] p-6 text-center"
            style={{ backgroundColor: "var(--th-bg-surface)" }}
          >
            <p className="text-sm text-[var(--color-db-text-secondary)]">
              No model available. A champion model has not been registered yet.
            </p>
          </div>
        )}

        {!loading && methodology && (
          <div className="space-y-12">
            <ModelDesignSection metadata={methodology.metadata} />

            <ModelFitSection
              metrics={methodology.metrics}
              availablePlots={methodology.available_plots}
            />

            {featureCatalog && (
              <FeatureAnalysisSection
                featureImportance={methodology.feature_importance}
                features={featureCatalog.features}
                categories={featureCatalog.categories}
                availableEdaPlots={methodology.available_eda_plots}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default ModelMethodologyPage;
