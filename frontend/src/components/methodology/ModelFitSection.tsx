import type { ModelMetrics } from "../../types";
import MetricCard from "./MetricCard";
import PlotGallery from "./PlotGallery";
import { humanizeFilename } from "./plotUtils";

interface ModelFitSectionProps {
  metrics: ModelMetrics;
  availablePlots: string[];
}

function ModelFitSection({ metrics, availablePlots }: ModelFitSectionProps) {
  const plots = availablePlots.map((path) => ({
    path,
    title: humanizeFilename(path),
  }));

  return (
    <section aria-labelledby="model-fit-heading">
      <h2
        id="model-fit-heading"
        className="mb-4 text-lg font-semibold text-[var(--color-db-text-primary)]"
      >
        Model Fit
      </h2>

      {/* Metric summary cards */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <MetricCard name="MAE" value={metrics.mae} format="currency" subtitle="Mean Abs. Error" />
        <MetricCard name="RMSE" value={metrics.rmse} format="currency" subtitle="Root Mean Sq." />
        <MetricCard
          name="MAPE"
          value={metrics.mape != null ? metrics.mape / 100 : null}
          format="percentage"
          subtitle="Mean Abs. % Error"
        />
        <MetricCard name="R-squared" value={metrics.r2} format="number" subtitle="Variance Expl." />
        <MetricCard
          name="Median AE"
          value={metrics.median_ae}
          format="currency"
          subtitle="Median Abs. Error"
        />
      </div>

      {/* CV metrics */}
      {metrics.mae_mean != null && (
        <div className="mb-6">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Cross-Validation (5-fold)
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <MetricCard
              name="CV MAE"
              value={metrics.mae_mean}
              format="currency"
              subtitle={
                metrics.mae_std != null
                  ? `+/- $${metrics.mae_std.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                  : undefined
              }
            />
            <MetricCard
              name="CV RMSE"
              value={metrics.rmse_mean}
              format="currency"
              subtitle={
                metrics.rmse_std != null
                  ? `+/- $${metrics.rmse_std.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                  : undefined
              }
            />
            <MetricCard
              name="CV R-squared"
              value={metrics.r2_mean}
              format="number"
              subtitle={metrics.r2_std != null ? `+/- ${metrics.r2_std.toFixed(4)}` : undefined}
            />
          </div>
        </div>
      )}

      {/* Plot gallery */}
      {plots.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Evaluation Plots
          </h3>
          <PlotGallery plots={plots} columns={2} />
        </div>
      )}
    </section>
  );
}

export default ModelFitSection;
