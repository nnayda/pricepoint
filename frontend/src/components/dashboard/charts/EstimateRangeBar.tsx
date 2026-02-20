import type { DashboardValuation } from "../../../types";

interface EstimateRangeBarProps {
  valuation: DashboardValuation;
}

function EstimateRangeBar({ valuation }: EstimateRangeBarProps) {
  const {
    tax_assessment,
    confidence_low,
    predicted_value,
    confidence_high,
    listed_price,
  } = valuation;

  const min = Math.min(tax_assessment, confidence_low) * 0.95;
  const max = Math.max(listed_price, confidence_high) * 1.05;
  const range = max - min;

  const pct = (v: number) => ((v - min) / range) * 100;

  const markers = [
    { label: "Tax Assess.", value: tax_assessment, color: "var(--color-db-text-muted)" },
    { label: "CI Low", value: confidence_low, color: "var(--color-db-yellow)" },
    { label: "Estimate", value: predicted_value, color: "var(--color-db-accent)" },
    { label: "CI High", value: confidence_high, color: "var(--color-db-yellow)" },
    { label: "List Price", value: listed_price, color: "var(--color-db-cyan)" },
  ];

  return (
    <div className="flex flex-col gap-1">
      {/* Bar with markers */}
      <div className="relative h-3 rounded-full bg-[var(--color-db-surface-alt)]">
        {/* Confidence interval range */}
        <div
          className="absolute top-0 h-full rounded-full opacity-30"
          style={{
            left: `${pct(confidence_low)}%`,
            width: `${pct(confidence_high) - pct(confidence_low)}%`,
            backgroundColor: "var(--color-db-accent)",
          }}
        />
        {/* Markers */}
        {markers.map((m) => (
          <div
            key={m.label}
            className="absolute top-1/2 h-5 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{ left: `${pct(m.value)}%`, backgroundColor: m.color }}
          />
        ))}
      </div>

      {/* Labels positioned directly below their markers */}
      <div className="relative h-10">
        {markers.map((m) => (
          <div
            key={m.label}
            className="absolute flex -translate-x-1/2 flex-col items-center gap-0"
            style={{ left: `${pct(m.value)}%` }}
          >
            <span className="text-[9px] font-medium text-[var(--color-db-text-muted)] whitespace-nowrap">
              {m.label}
            </span>
            <span
              className="text-[11px] font-semibold whitespace-nowrap"
              style={{ color: m.color, fontFamily: "var(--font-db-mono)" }}
            >
              ${(m.value / 1000).toFixed(0)}k
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default EstimateRangeBar;
