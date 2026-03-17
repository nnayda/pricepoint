import type { ModelMetadata } from "../../types";
import DashboardCard from "../dashboard/DashboardCard";

interface ModelDesignSectionProps {
  metadata: ModelMetadata;
}

function ModelDesignSection({ metadata }: ModelDesignSectionProps) {
  const trainingDate = metadata.training_date
    ? new Date(metadata.training_date).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "Unknown";

  return (
    <section aria-labelledby="model-design-heading">
      <h2
        id="model-design-heading"
        className="mb-4 text-lg font-semibold text-[var(--color-db-text-primary)]"
      >
        Model Design
      </h2>

      <DashboardCard>
        <div className="space-y-4">
          {/* Version badge and training info */}
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-[var(--color-db-accent)] px-3 py-1 text-xs font-medium text-white">
              v{metadata.model_version}
            </span>
            <span className="text-xs text-[var(--color-db-text-secondary)]">
              Trained {trainingDate}
            </span>
            <span className="text-xs text-[var(--color-db-text-secondary)]">
              {metadata.n_training_samples.toLocaleString()} training samples
            </span>
            <span className="text-xs text-[var(--color-db-text-secondary)]">
              {metadata.n_features} features
            </span>
          </div>

          {/* Approach description */}
          <div className="text-sm leading-relaxed text-[var(--color-db-text-secondary)]">
            <p>
              The PricePoint valuation model uses{" "}
              <strong className="text-[var(--color-db-text-primary)]">
                XGBoost gradient boosted trees
              </strong>{" "}
              to predict residential home values. Key design choices:
            </p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-[var(--color-db-text-secondary)]">
              <li>
                <strong>Log-transform target:</strong> log1p(sale_price) as the prediction target,
                inverse-transformed at inference
              </li>
              <li>
                <strong>Train/test split:</strong> 80/20 random split with stratification by price
                quartile
              </li>
              <li>
                <strong>Early stopping:</strong> Training stops when validation loss plateaus to
                prevent overfitting
              </li>
              <li>
                <strong>Conformal prediction intervals:</strong> 90% coverage calibrated on a
                held-out set, scaled proportionally to predicted value
              </li>
              <li>
                <strong>Cross-validation:</strong> 5-fold CV for robust metric estimation
              </li>
            </ul>
          </div>

          {/* Hyperparameters */}
          {Object.keys(metadata.hyperparameters).length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-[var(--color-db-text-primary)]">
                Hyperparameters
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-[var(--th-border-subtle)]">
                      <th className="px-3 py-1.5 text-xs font-semibold text-[var(--color-db-text-tertiary)]">
                        Parameter
                      </th>
                      <th className="px-3 py-1.5 text-xs font-semibold text-[var(--color-db-text-tertiary)]">
                        Value
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(metadata.hyperparameters).map(([key, val]) => (
                      <tr key={key} className="border-b border-[var(--th-border-subtle)]">
                        <td className="px-3 py-1.5 font-mono text-xs text-[var(--color-db-text-secondary)]">
                          {key}
                        </td>
                        <td className="px-3 py-1.5 text-xs text-[var(--color-db-text-primary)]">
                          {String(val ?? "None")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </DashboardCard>
    </section>
  );
}

export default ModelDesignSection;
