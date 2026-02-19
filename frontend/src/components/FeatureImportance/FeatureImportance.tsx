import type { FeatureAttribution } from "../../types";

interface FeatureImportanceProps {
  attributions: FeatureAttribution[];
}

function formatDollars(value: number): string {
  const abs = Math.abs(value);
  const formatted = abs >= 1000 ? `$${abs.toLocaleString()}` : `$${abs}`;
  return value >= 0 ? `+${formatted}` : `-${formatted}`;
}

export default function FeatureImportance({ attributions }: FeatureImportanceProps) {
  if (attributions.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 p-8"
        data-testid="feature-importance-empty"
      >
        <p className="text-gray-500">No feature attributions available</p>
      </div>
    );
  }

  const sorted = [...attributions]
    .sort((a, b) => Math.abs(b.impact_dollars) - Math.abs(a.impact_dollars))
    .slice(0, 10);

  const maxAbsImpact = Math.max(...sorted.map((a) => Math.abs(a.impact_dollars)));

  return (
    <div
      className="space-y-3"
      data-testid="feature-importance"
      role="list"
      aria-label="Feature importance"
    >
      {sorted.map((attr) => {
        const isPositive = attr.impact_dollars >= 0;
        const barWidth =
          maxAbsImpact > 0 ? (Math.abs(attr.impact_dollars) / maxAbsImpact) * 100 : 0;

        return (
          <div key={attr.feature} className="flex items-center gap-3" role="listitem">
            <div className="w-36 shrink-0 text-right text-sm text-gray-700">
              {attr.display_name}
            </div>
            <div className="flex flex-1 items-center">
              {!isPositive && (
                <div className="flex flex-1 justify-end">
                  <div
                    className="h-6 rounded-l bg-red-500"
                    style={{ width: `${barWidth}%` }}
                    data-testid={`bar-negative-${attr.feature}`}
                  />
                </div>
              )}
              <div className="mx-1 h-8 w-px bg-gray-400" />
              {isPositive && (
                <div className="flex flex-1 justify-start">
                  <div
                    className="h-6 rounded-r bg-green-500"
                    style={{ width: `${barWidth}%` }}
                    data-testid={`bar-positive-${attr.feature}`}
                  />
                </div>
              )}
              {!isPositive && <div className="flex-1" />}
              {isPositive && <div className="order-first flex-1" />}
            </div>
            <div
              className={`w-24 shrink-0 text-sm font-medium ${isPositive ? "text-green-700" : "text-red-700"}`}
            >
              {formatDollars(attr.impact_dollars)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
