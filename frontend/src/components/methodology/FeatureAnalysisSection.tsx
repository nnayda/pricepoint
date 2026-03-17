import type { FeatureCatalogEntry, FeatureImportanceItem } from "../../types";
import DashboardCard from "../dashboard/DashboardCard";
import FeatureCatalogTable from "./FeatureCatalogTable";
import PlotGallery from "./PlotGallery";
import { humanizeFilename } from "./plotUtils";

interface FeatureAnalysisSectionProps {
  featureImportance: FeatureImportanceItem[];
  features: FeatureCatalogEntry[];
  categories: string[];
  availableEdaPlots: string[];
}

function FeatureAnalysisSection({
  featureImportance,
  features,
  categories,
  availableEdaPlots,
}: FeatureAnalysisSectionProps) {
  const edaPlots = availableEdaPlots.map((path) => ({
    path,
    title: humanizeFilename(path),
  }));

  return (
    <section aria-labelledby="feature-analysis-heading">
      <h2
        id="feature-analysis-heading"
        className="mb-4 text-lg font-semibold text-[var(--color-db-text-primary)]"
      >
        Feature Analysis
      </h2>

      {/* Top feature importance */}
      {featureImportance.length > 0 && (
        <DashboardCard className="mb-6">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Top Feature Importances (by Gain)
          </h3>
          <div className="space-y-1.5">
            {featureImportance.map((fi) => {
              const maxGain = featureImportance[0]?.gain ?? 1;
              const pct = maxGain > 0 ? (fi.gain / maxGain) * 100 : 0;
              return (
                <div key={fi.feature} className="flex items-center gap-3">
                  <span className="w-48 shrink-0 truncate font-mono text-xs text-[var(--color-db-text-secondary)]">
                    {fi.feature}
                  </span>
                  <div className="relative h-4 flex-1 overflow-hidden rounded-full bg-[var(--color-db-surface-alt)]">
                    <div
                      className="h-full rounded-full bg-[var(--color-db-accent)]"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-16 text-right font-mono text-xs text-[var(--color-db-text-tertiary)]">
                    {fi.gain.toFixed(4)}
                  </span>
                </div>
              );
            })}
          </div>
        </DashboardCard>
      )}

      {/* EDA Plots */}
      {edaPlots.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Exploratory Data Analysis
          </h3>
          <PlotGallery plots={edaPlots} columns={2} />
        </div>
      )}

      {/* Feature catalog */}
      <DashboardCard>
        <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
          Feature Catalog ({features.length} features)
        </h3>
        <FeatureCatalogTable features={features} categories={categories} />
      </DashboardCard>
    </section>
  );
}

export default FeatureAnalysisSection;
