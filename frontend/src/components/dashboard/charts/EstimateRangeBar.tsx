import type { DashboardValuation } from "../../../types";
import { COLOR_PURPLE } from "../../../utils/chartTokens";

interface EstimateRangeBarProps {
  valuation: DashboardValuation;
}

function fmtShort(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  return `$${(v / 1000).toFixed(0)}k`;
}

function fmtUsd(n: number): string {
  return "$" + n.toLocaleString("en-US");
}

interface TickMark {
  value: number;
  color: string;
  label: string;
  prominent: boolean;
  position: "above" | "below";
}

function EstimateRangeBar({ valuation }: EstimateRangeBarProps) {
  const {
    tax_assessment,
    confidence_low,
    predicted_value,
    confidence_high,
    listed_price,
    neighborhood_median,
    neighborhood_max,
  } = valuation;

  const allValues = [
    tax_assessment,
    confidence_low,
    predicted_value,
    confidence_high,
    listed_price,
    neighborhood_median,
    neighborhood_max,
  ];
  const min = Math.min(...allValues) * 0.95;
  const max = Math.max(...allValues) * 1.05;
  const range = max - min;

  const pct = (v: number) => ((v - min) / range) * 100;

  const delta = ((predicted_value - listed_price) / listed_price) * 100;
  const deltaStr = delta >= 0 ? `+${delta.toFixed(1)}%` : `${delta.toFixed(1)}%`;

  const tickMarks: TickMark[] = [
    { value: tax_assessment, color: "var(--color-db-orange)", label: "Assessment", prominent: false, position: "above" },
    { value: confidence_low, color: COLOR_PURPLE, label: "CI Low", prominent: false, position: "above" },
    { value: predicted_value, color: "var(--color-db-accent)", label: "Estimate", prominent: true, position: "above" },
    { value: confidence_high, color: COLOR_PURPLE, label: "CI High", prominent: false, position: "above" },
    { value: listed_price, color: "var(--color-db-cyan)", label: "Listed", prominent: false, position: "above" },
    { value: neighborhood_median, color: "var(--color-db-text-secondary)", label: "Nbhd Median", prominent: false, position: "below" },
    { value: neighborhood_max, color: "var(--color-db-text-secondary)", label: "Nbhd Max", prominent: false, position: "below" },
  ];

  const aboveTicks = tickMarks.filter((m) => m.position === "above");
  const belowTicks = tickMarks.filter((m) => m.position === "below");

  return (
    <div className="flex flex-col gap-4">
      {/* Model Estimate card (left) + Range bar (right) */}
      <div className="grid grid-cols-[auto_1fr] items-center gap-4">
        {/* Predicted Estimate — outline only */}
        <div
          className="flex flex-col justify-center rounded-[var(--radius-db-sm)] border px-5 py-3"
          style={{
            borderColor: "var(--color-db-accent)",
            backgroundColor: "transparent",
            minWidth: "200px",
          }}
        >
          <span className="mb-0.5 block text-[9px] uppercase tracking-wider text-[var(--color-db-text-secondary)]">
            Model Estimate
          </span>
          <div className="flex items-baseline gap-1.5">
            <span
              className="font-db-mono text-xl font-bold"
              style={{ color: "var(--color-db-accent)" }}
            >
              {fmtUsd(predicted_value)}
            </span>
            <span
              className="font-db-mono text-xs font-semibold"
              style={{ color: delta >= 0 ? "var(--color-db-green)" : "var(--color-db-red, #F87171)" }}
            >
              {deltaStr}
            </span>
          </div>
        </div>

        {/* Range bar with tick labels */}
        <div className="flex flex-col gap-2">
          {/* Tick labels above bar */}
          <div className="relative h-11">
            {aboveTicks.map((m) => (
              <div
                key={m.label}
                className="absolute bottom-0 -translate-x-1/2"
                style={{ left: `${pct(m.value)}%` }}
              >
                <span
                  className={`block whitespace-nowrap font-db-mono ${m.prominent ? "text-base font-bold" : "text-xs font-medium"}`}
                  style={{ color: m.color }}
                >
                  {fmtShort(m.value)}
                </span>
                <span
                  className={`block whitespace-nowrap uppercase tracking-wider ${m.prominent ? "text-[11px] font-semibold" : "text-[9px]"}`}
                  style={{ color: m.color }}
                >
                  {m.label}
                </span>
              </div>
            ))}
          </div>

          {/* Bar with tick marks */}
          <div className="relative h-2.5 rounded-full bg-[var(--color-db-surface-alt)]">
            {/* SVG hatched pattern definition */}
            <svg className="absolute" width="0" height="0">
              <defs>
                <pattern
                  id="ci-hatch"
                  patternUnits="userSpaceOnUse"
                  width="6"
                  height="6"
                  patternTransform="rotate(45)"
                >
                  <line x1="0" y1="0" x2="0" y2="6" stroke={COLOR_PURPLE} strokeWidth="1.5" strokeOpacity="0.5" />
                </pattern>
              </defs>
            </svg>
            {/* Confidence interval hatched fill */}
            <svg
              className="absolute top-0 h-full overflow-hidden rounded-full"
              style={{
                left: `${pct(confidence_low)}%`,
                width: `${pct(confidence_high) - pct(confidence_low)}%`,
              }}
              preserveAspectRatio="none"
            >
              <rect width="100%" height="100%" fill="url(#ci-hatch)" />
            </svg>
            {/* Tick marks — all ticks */}
            {tickMarks.map((m) => (
              <div
                key={m.label}
                className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full ${m.prominent ? "h-6 w-1" : "h-4 w-0.5"}`}
                style={{ left: `${pct(m.value)}%`, backgroundColor: m.color }}
              />
            ))}
          </div>

          {/* Tick labels below bar */}
          <div className="relative h-8">
            {belowTicks.map((m) => (
              <div
                key={m.label}
                className="absolute top-0 -translate-x-1/2"
                style={{ left: `${pct(m.value)}%` }}
              >
                <span
                  className="block whitespace-nowrap text-[9px] uppercase tracking-wider"
                  style={{ color: m.color }}
                >
                  {m.label}
                </span>
                <span
                  className="block whitespace-nowrap font-db-mono text-xs font-medium"
                  style={{ color: m.color }}
                >
                  {fmtShort(m.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default EstimateRangeBar;
