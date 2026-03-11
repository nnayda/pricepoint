import { useCallback, useEffect, useRef, useState } from "react";
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
  hoverOnly?: boolean;
}

interface NudgedLabel {
  tick: TickMark;
  /** Original percent position along the bar */
  originPct: number;
  /** Nudged pixel position (center of label) */
  nudgedPx: number;
  /** Measured or estimated width in pixels */
  width: number;
}

const MIN_GAP = 8;

/** Estimate label width from text content */
function estimateWidth(tick: TickMark): number {
  const valueText = fmtShort(tick.value);
  const labelText = tick.label;
  const longer = Math.max(valueText.length, labelText.length);
  const charWidth = tick.prominent ? 9.5 : 7;
  return longer * charWidth + 4;
}

/**
 * Nudge labels so none overlap. Greedy left-to-right spreading.
 * Returns nudged pixel center positions.
 */
function nudgeLabels(
  ticks: TickMark[],
  originPcts: number[],
  containerWidth: number,
  measuredWidths: Map<string, number>,
): NudgedLabel[] {
  if (ticks.length === 0 || containerWidth <= 0) return [];

  // Build items sorted by origin position
  const items: NudgedLabel[] = ticks.map((tick, i) => {
    const w = measuredWidths.get(tick.label) ?? estimateWidth(tick);
    return {
      tick,
      originPct: originPcts[i],
      nudgedPx: (originPcts[i] / 100) * containerWidth,
      width: w,
    };
  });

  items.sort((a, b) => a.nudgedPx - b.nudgedPx);

  // Forward pass: push right if overlapping
  for (let i = 1; i < items.length; i++) {
    const prev = items[i - 1];
    const curr = items[i];
    const minCenter = prev.nudgedPx + prev.width / 2 + MIN_GAP + curr.width / 2;
    if (curr.nudgedPx < minCenter) {
      curr.nudgedPx = minCenter;
    }
  }

  // Backward pass: if last item exceeds container, push everything left
  const last = items[items.length - 1];
  const maxCenter = containerWidth - last.width / 2;
  if (last.nudgedPx > maxCenter) {
    const shift = last.nudgedPx - maxCenter;
    for (const item of items) {
      item.nudgedPx -= shift;
    }
  }

  // Forward clamp: ensure nothing goes below 0
  for (let i = 0; i < items.length; i++) {
    const minCenter =
      i === 0
        ? items[i].width / 2
        : items[i - 1].nudgedPx + items[i - 1].width / 2 + MIN_GAP + items[i].width / 2;
    if (items[i].nudgedPx < minCenter) {
      items[i].nudgedPx = minCenter;
    }
  }

  return items;
}

function EstimateRangeBar({ valuation }: EstimateRangeBarProps) {
  const {
    tax_assessment,
    confidence_low,
    predicted_value,
    confidence_high,
    listed_price,
    redfin_estimate,
    neighborhood_median,
    neighborhood_max,
  } = valuation;

  const hasEstimate = predicted_value != null;
  const hasCI = confidence_low != null && confidence_high != null;
  const hasNbhd = neighborhood_median != null && neighborhood_max != null;

  const allValues = [
    tax_assessment,
    listed_price,
    ...(hasEstimate ? [predicted_value] : []),
    ...(hasCI ? [confidence_low, confidence_high] : []),
    ...(redfin_estimate != null ? [redfin_estimate] : []),
    ...(hasNbhd ? [neighborhood_median, neighborhood_max] : []),
  ];
  const min = Math.min(...allValues) * 0.95;
  const max = Math.max(...allValues) * 1.05;
  const range = max - min;

  const pct = (v: number) => ((v - min) / range) * 100;

  const delta = hasEstimate ? ((predicted_value - listed_price) / listed_price) * 100 : 0;
  const deltaStr = delta >= 0 ? `+${delta.toFixed(1)}%` : `${delta.toFixed(1)}%`;

  const tickMarks: TickMark[] = [
    {
      value: tax_assessment,
      color: "var(--color-db-orange)",
      label: "Assessment",
      prominent: false,
      position: "above",
    },
    ...(hasCI
      ? [
          {
            value: confidence_low,
            color: COLOR_PURPLE,
            label: "CI Low",
            prominent: false,
            position: "above" as const,
            hoverOnly: true,
          },
        ]
      : []),
    ...(hasEstimate
      ? [
          {
            value: predicted_value,
            color: "var(--color-db-accent)",
            label: "Estimate",
            prominent: true,
            position: "above" as const,
          },
        ]
      : []),
    ...(hasCI
      ? [
          {
            value: confidence_high,
            color: COLOR_PURPLE,
            label: "CI High",
            prominent: false,
            position: "above" as const,
            hoverOnly: true,
          },
        ]
      : []),
    {
      value: listed_price,
      color: "var(--color-db-cyan)",
      label: "Listed",
      prominent: !hasEstimate,
      position: "above",
    },
    ...(redfin_estimate != null
      ? [
          {
            value: redfin_estimate,
            color: "var(--color-db-red)",
            label: "Redfin",
            prominent: false,
            position: "below" as const,
          },
        ]
      : []),
    ...(hasNbhd
      ? [
          {
            value: neighborhood_median,
            color: "var(--color-db-text-secondary)",
            label: "Nbhd Median",
            prominent: false,
            position: "below" as const,
          },
          {
            value: neighborhood_max,
            color: "var(--color-db-text-secondary)",
            label: "Nbhd Max",
            prominent: false,
            position: "below" as const,
          },
        ]
      : []),
  ];

  // Split by row, excluding hoverOnly from nudging
  const aboveTicks = tickMarks.filter((m) => m.position === "above");
  const belowTicks = tickMarks.filter((m) => m.position === "below");
  const aboveVisible = aboveTicks.filter((m) => !m.hoverOnly);
  const aboveHidden = aboveTicks.filter((m) => m.hoverOnly);

  // Refs for measuring
  const aboveContainerRef = useRef<HTMLDivElement>(null);
  const belowContainerRef = useRef<HTMLDivElement>(null);
  const aboveLabelRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const belowLabelRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const [containerWidth, setContainerWidth] = useState(0);
  const [measuredAbove, setMeasuredAbove] = useState<Map<string, number>>(new Map());
  const [measuredBelow, setMeasuredBelow] = useState<Map<string, number>>(new Map());

  // Observe container width
  useEffect(() => {
    const container = aboveContainerRef.current;
    if (!container) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Measure label widths after render
  const measureLabels = useCallback(() => {
    const aboveMap = new Map<string, number>();
    aboveLabelRefs.current.forEach((el, key) => {
      if (el) aboveMap.set(key, el.offsetWidth);
    });
    setMeasuredAbove(aboveMap);

    const belowMap = new Map<string, number>();
    belowLabelRefs.current.forEach((el, key) => {
      if (el) belowMap.set(key, el.offsetWidth);
    });
    setMeasuredBelow(belowMap);
  }, []);

  useEffect(() => {
    measureLabels();
  }, [measureLabels, containerWidth, valuation]);

  // Compute nudged positions
  const aboveNudged = nudgeLabels(
    aboveVisible,
    aboveVisible.map((m) => pct(m.value)),
    containerWidth,
    measuredAbove,
  );

  const belowNudged = nudgeLabels(
    belowTicks,
    belowTicks.map((m) => pct(m.value)),
    containerWidth,
    measuredBelow,
  );

  const setAboveRef = (label: string) => (el: HTMLDivElement | null) => {
    if (el) aboveLabelRefs.current.set(label, el);
    else aboveLabelRefs.current.delete(label);
  };

  const setBelowRef = (label: string) => (el: HTMLDivElement | null) => {
    if (el) belowLabelRefs.current.set(label, el);
    else belowLabelRefs.current.delete(label);
  };

  /** Threshold in px for showing a leader line */
  const LEADER_THRESHOLD = 2;

  return (
    <div className="flex flex-col gap-4">
      {/* Model Estimate card (left) + Range bar (right) */}
      <div
        className={`grid items-center gap-4 ${hasEstimate ? "grid-cols-[auto_1fr]" : "grid-cols-1"}`}
      >
        {/* Predicted Estimate — outline only, shown when model data exists */}
        {hasEstimate && (
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
                style={{
                  color: delta >= 0 ? "var(--color-db-green)" : "var(--color-db-red, #F87171)",
                }}
              >
                {deltaStr}
              </span>
            </div>
          </div>
        )}

        {/* Range bar with tick labels */}
        <div className="flex flex-col gap-2">
          {/* Tick labels above bar */}
          <div ref={aboveContainerRef} className="relative h-11">
            {/* Leader lines SVG for above labels */}
            {containerWidth > 0 && (
              <svg
                className="pointer-events-none absolute inset-0"
                width={containerWidth}
                height="100%"
                style={{ overflow: "visible" }}
              >
                {aboveNudged.map((item) => {
                  const originPx = (item.originPct / 100) * containerWidth;
                  const diff = Math.abs(item.nudgedPx - originPx);
                  if (diff < LEADER_THRESHOLD) return null;
                  // Line from nudged label bottom-center to tick origin at bottom
                  return (
                    <line
                      key={`leader-above-${item.tick.label}`}
                      x1={item.nudgedPx}
                      y1="75%"
                      x2={originPx}
                      y2="100%"
                      stroke={item.tick.color}
                      strokeWidth={1}
                      opacity={0.4}
                    />
                  );
                })}
              </svg>
            )}
            {/* Nudged visible labels */}
            {aboveNudged.map((item) => (
              <div
                key={item.tick.label}
                ref={setAboveRef(item.tick.label)}
                className="absolute bottom-0 -translate-x-1/2"
                style={{ left: `${item.nudgedPx}px` }}
              >
                <span
                  className={`block whitespace-nowrap font-db-mono ${item.tick.prominent ? "text-base font-bold" : "text-xs font-medium"}`}
                  style={{ color: item.tick.color }}
                >
                  {fmtShort(item.tick.value)}
                </span>
                <span
                  className={`block whitespace-nowrap uppercase tracking-wider ${item.tick.prominent ? "text-[11px] font-semibold" : "text-[9px]"}`}
                  style={{ color: item.tick.color }}
                >
                  {item.tick.label}
                </span>
              </div>
            ))}
            {/* HoverOnly labels — positioned at their true percent (not nudged) */}
            {aboveHidden.map((m) => (
              <div
                key={m.label}
                className="group absolute bottom-0 -translate-x-1/2"
                style={{ left: `${pct(m.value)}%` }}
              >
                <span
                  className="block whitespace-nowrap font-db-mono text-xs font-medium opacity-0 transition-opacity group-hover:opacity-100"
                  style={{ color: m.color }}
                >
                  {fmtShort(m.value)}
                </span>
                <span
                  className="block whitespace-nowrap text-[9px] uppercase tracking-wider opacity-0 transition-opacity group-hover:opacity-100"
                  style={{ color: m.color }}
                >
                  {m.label}
                </span>
              </div>
            ))}
          </div>

          {/* Bar with tick marks */}
          <div className="relative h-2.5 rounded-full bg-[var(--color-db-surface-alt)]">
            {/* CI hatched fill — only when confidence interval bounds exist */}
            {hasCI && (
              <>
                <svg className="absolute" width="0" height="0">
                  <defs>
                    <pattern
                      id="ci-hatch"
                      patternUnits="userSpaceOnUse"
                      width="6"
                      height="6"
                      patternTransform="rotate(45)"
                    >
                      <line
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="6"
                        stroke={COLOR_PURPLE}
                        strokeWidth="1.5"
                        strokeOpacity="0.5"
                      />
                    </pattern>
                  </defs>
                </svg>
                <svg
                  className="absolute top-0 h-full overflow-hidden rounded-full"
                  style={{
                    left: `${pct(confidence_low!)}%`,
                    width: `${pct(confidence_high!) - pct(confidence_low!)}%`,
                  }}
                  preserveAspectRatio="none"
                >
                  <rect width="100%" height="100%" fill="url(#ci-hatch)" />
                </svg>
              </>
            )}
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
          {belowTicks.length > 0 && (
            <div ref={belowContainerRef} className="relative h-8">
              {/* Leader lines SVG for below labels */}
              {containerWidth > 0 && (
                <svg
                  className="pointer-events-none absolute inset-0"
                  width={containerWidth}
                  height="100%"
                  style={{ overflow: "visible" }}
                >
                  {belowNudged.map((item) => {
                    const originPx = (item.originPct / 100) * containerWidth;
                    const diff = Math.abs(item.nudgedPx - originPx);
                    if (diff < LEADER_THRESHOLD) return null;
                    return (
                      <line
                        key={`leader-below-${item.tick.label}`}
                        x1={originPx}
                        y1="0%"
                        x2={item.nudgedPx}
                        y2="25%"
                        stroke={item.tick.color}
                        strokeWidth={1}
                        opacity={0.4}
                      />
                    );
                  })}
                </svg>
              )}
              {belowNudged.map((item) => (
                <div
                  key={item.tick.label}
                  ref={setBelowRef(item.tick.label)}
                  className="absolute top-0 -translate-x-1/2"
                  style={{ left: `${item.nudgedPx}px` }}
                >
                  <span
                    className="block whitespace-nowrap text-[9px] uppercase tracking-wider"
                    style={{ color: item.tick.color }}
                  >
                    {item.tick.label}
                  </span>
                  <span
                    className="block whitespace-nowrap font-db-mono text-xs font-medium"
                    style={{ color: item.tick.color }}
                  >
                    {fmtShort(item.tick.value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default EstimateRangeBar;
