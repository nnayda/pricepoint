import { useCallback, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceArea,
} from "recharts";
import type { PriceHistoryPoint } from "../../../types";
import { useCardExpanded } from "../DashboardCard";
import {
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  AXIS_TICK_MONO,
  AXIS_LINE_STYLE,
  CURSOR_LINE,
  COLOR_INDIGO,
  COLOR_CYAN,
  COLOR_AMBER,
} from "../../../utils/chartTokens";

const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Format a "YYYY-MM" date key for display. */
function formatDateShort(d: string): string {
  const [y, m] = d.split("-");
  return `${MONTH_SHORT[parseInt(m, 10) - 1]} '${y.slice(2)}`;
}

function formatDateFull(d: string): string {
  const [y, m] = d.split("-");
  return `${MONTH_SHORT[parseInt(m, 10) - 1]} ${y}`;
}

/** Trim leading points that have neither sale nor tax data. */
function trimLeadingEmpty(data: PriceHistoryPoint[]): PriceHistoryPoint[] {
  const firstIdx = data.findIndex((d) => d.price != null || d.tax_assessed != null);
  return firstIdx <= 0 ? data : data.slice(firstIdx);
}

/**
 * Pick evenly-spaced tick indices so labels never overlap.
 * Returns a Set of data indices that should show a label.
 */
function buildTickIndices(data: PriceHistoryPoint[], maxTicks: number): Set<number> {
  const n = data.length;
  if (n <= maxTicks) {
    return new Set(Array.from({ length: n }, (_, i) => i));
  }
  const step = (n - 1) / (maxTicks - 1);
  const indices = new Set<number>();
  for (let i = 0; i < maxTicks; i++) {
    indices.add(Math.round(i * step));
  }
  return indices;
}

/** Pick a tick formatter and interval that avoids overlapping labels. */
function useXAxisConfig(data: PriceHistoryPoint[]) {
  return useMemo(() => {
    const n = data.length;
    const MAX_TICKS = 8;
    const tickIndices = buildTickIndices(data, MAX_TICKS);

    if (n <= MAX_TICKS) {
      return {
        formatter: (_d: string, index: number) =>
          tickIndices.has(index) ? formatDateFull(data[index].date) : "",
      };
    }

    if (n <= 24) {
      return {
        formatter: (_d: string, index: number) =>
          tickIndices.has(index) ? formatDateShort(data[index].date) : "",
      };
    }

    // Long history — show just years at tick positions
    return {
      formatter: (_d: string, index: number) => {
        if (!tickIndices.has(index)) return "";
        return data[index].date.split("-")[0];
      },
    };
  }, [data]);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ChartMouseEvent = { activeTooltipIndex?: number | null | any };

/** Hook to manage drag-to-zoom on a categorical (index-based) recharts axis. */
function useZoom(dataLength: number) {
  const [zoomLeft, setZoomLeft] = useState<number | null>(null);
  const [zoomRight, setZoomRight] = useState<number | null>(null);
  // Visible window: [start, end) indices into the full data array
  const [window, setWindow] = useState<[number, number] | null>(null);

  const onMouseDown = useCallback(
    (e: ChartMouseEvent) => {
      const idx = typeof e.activeTooltipIndex === "number" ? e.activeTooltipIndex : null;
      if (idx != null) {
        setZoomLeft(idx);
        setZoomRight(null);
      }
    },
    [],
  );

  const onMouseMove = useCallback(
    (e: ChartMouseEvent) => {
      const idx = typeof e.activeTooltipIndex === "number" ? e.activeTooltipIndex : null;
      if (zoomLeft != null && idx != null) {
        setZoomRight(idx);
      }
    },
    [zoomLeft],
  );

  const onMouseUp = useCallback(() => {
    if (zoomLeft != null && zoomRight != null && zoomLeft !== zoomRight) {
      const lo = Math.min(zoomLeft, zoomRight);
      const hi = Math.min(Math.max(zoomLeft, zoomRight) + 1, dataLength);
      if (hi - lo >= 2) {
        setWindow((prev) => {
          // Map indices relative to current window back to full data
          const base = prev ? prev[0] : 0;
          return [base + lo, base + hi];
        });
      }
    }
    setZoomLeft(null);
    setZoomRight(null);
  }, [zoomLeft, zoomRight, dataLength]);

  const resetZoom = useCallback(() => setWindow(null), []);

  const panLeft = useCallback(() => {
    setWindow((prev) => {
      if (!prev) return null;
      const span = prev[1] - prev[0];
      const shift = Math.max(1, Math.round(span * 0.25));
      const newStart = Math.max(0, prev[0] - shift);
      return [newStart, newStart + span];
    });
  }, []);

  const panRight = useCallback(() => {
    setWindow((prev) => {
      if (!prev) return null;
      const span = prev[1] - prev[0];
      const shift = Math.max(1, Math.round(span * 0.25));
      const newEnd = Math.min(dataLength, prev[1] + shift);
      return [newEnd - span, newEnd];
    });
  }, [dataLength]);

  return { zoomLeft, zoomRight, window, onMouseDown, onMouseMove, onMouseUp, resetZoom, panLeft, panRight };
}

interface PriceHistoryChartProps {
  data: PriceHistoryPoint[];
  showNeighborhood?: boolean;
}

/** Render a filled dot with an event label at sale event points. */
function SaleDot(props: Record<string, unknown>) {
  const { cx, cy, payload } = props as {
    cx?: number;
    cy?: number;
    payload?: PriceHistoryPoint;
  };
  if (!payload?.sale_price || cx == null || cy == null) return null;
  const label = payload.sale_event ?? payload.event ?? "Sale";
  return (
    <g>
      <circle cx={cx} cy={cy} r={5} fill={COLOR_INDIGO} fillOpacity={0.2} />
      <circle cx={cx} cy={cy} r={3.5} fill={COLOR_INDIGO} stroke="#fff" strokeWidth={1.5} />
      <text
        x={cx}
        y={cy - 12}
        textAnchor="middle"
        fill="var(--color-db-text-secondary, #9BA3BF)"
        fontSize={10}
        fontFamily="var(--font-db-sans)"
      >
        {label}
      </text>
    </g>
  );
}

function formatSeriesName(name: string): string {
  if (name === "price") return "Property";
  if (name === "tax_assessed") return "Tax Assessment";
  if (name === "neighborhood_median") return "Neighborhood";
  return name;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const tooltipFormatter: any = (value: number | undefined, name: string) => {
  if (value == null) return [null, null];
  return [`$${value.toLocaleString()}`, formatSeriesName(name)];
};

function PriceHistoryChart({ data: rawData, showNeighborhood = true }: PriceHistoryChartProps) {
  const allData = useMemo(() => trimLeadingEmpty(rawData), [rawData]);
  const isExpanded = useCardExpanded();

  const zoom = useZoom(allData.length);

  // Slice data to the visible zoom window
  const data = useMemo(
    () => (zoom.window ? allData.slice(zoom.window[0], zoom.window[1]) : allData),
    [allData, zoom.window],
  );

  const hasTaxData = data.some((d) => d.tax_assessed != null);
  const hasNeighborhoodData = showNeighborhood && data.some((d) => d.neighborhood_median != null);
  const xAxis = useXAxisConfig(data);

  const chartHeight = isExpanded ? "100%" : 280;

  return (
    <div className={`flex flex-col ${isExpanded ? "h-full" : ""}`}>
      {/* Legend + zoom controls */}
      <div className="mb-2 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block h-0.5 w-4 rounded-full"
            style={{ backgroundColor: COLOR_INDIGO }}
          />
          <span className="text-[11px] text-[var(--color-db-text-secondary)]">Property</span>
        </div>
        {hasTaxData && (
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block h-0.5 w-4 rounded-full"
              style={{ backgroundColor: COLOR_AMBER }}
            />
            <span className="text-[11px] text-[var(--color-db-text-secondary)]">
              Tax Assessment
            </span>
          </div>
        )}
        {hasNeighborhoodData && (
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block h-0.5 w-4"
              style={{
                backgroundImage: `repeating-linear-gradient(to right, ${COLOR_CYAN} 0, ${COLOR_CYAN} 3px, transparent 3px, transparent 6px)`,
              }}
            />
            <span className="text-[11px] text-[var(--color-db-text-secondary)]">
              Neighborhood Median
            </span>
          </div>
        )}
        {zoom.window && (
          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              onClick={zoom.panLeft}
              disabled={zoom.window[0] === 0}
              className="flex items-center justify-center rounded-[var(--radius-db-xs)] border border-[var(--color-db-border)] px-1.5 py-0.5 text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-alt)] hover:text-[var(--color-db-text-primary)] disabled:opacity-30 disabled:pointer-events-none"
              aria-label="Pan left"
            >
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 3L5 8l5 5" />
              </svg>
            </button>
            <button
              type="button"
              onClick={zoom.panRight}
              disabled={zoom.window[1] >= allData.length}
              className="flex items-center justify-center rounded-[var(--radius-db-xs)] border border-[var(--color-db-border)] px-1.5 py-0.5 text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-alt)] hover:text-[var(--color-db-text-primary)] disabled:opacity-30 disabled:pointer-events-none"
              aria-label="Pan right"
            >
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 3l5 5-5 5" />
              </svg>
            </button>
            <button
              type="button"
              onClick={zoom.resetZoom}
              className="flex items-center gap-1 rounded-[var(--radius-db-xs)] border border-[var(--color-db-border)] px-2 py-0.5 text-[11px] text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-alt)] hover:text-[var(--color-db-text-primary)]"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M1 1v5h5" />
                <path d="M3.51 10a6 6 0 1 0 .34-5.37L1 6" />
              </svg>
              Reset zoom
            </button>
          </div>
        )}
        {!zoom.window && (
          <span className="ml-auto text-[10px] text-[var(--color-db-text-muted)]">
            Drag to zoom
          </span>
        )}
      </div>
      <div className={isExpanded ? "min-h-0 flex-1" : ""}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <ComposedChart
            data={data}
            margin={{ top: 22, right: 10, left: 10, bottom: 5 }}
            onMouseDown={zoom.onMouseDown}
            onMouseMove={zoom.onMouseMove}
            onMouseUp={zoom.onMouseUp}
          >
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={COLOR_INDIGO} stopOpacity={0.3} />
                <stop offset="100%" stopColor={COLOR_INDIGO} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={AXIS_TICK_MONO}
              axisLine={AXIS_LINE_STYLE}
              tickLine={false}
              interval={0}
              tickFormatter={xAxis.formatter}
            />
            <YAxis
              tick={AXIS_TICK_MONO}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              width={55}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={TOOLTIP_CONTENT_STYLE}
              itemStyle={TOOLTIP_ITEM_STYLE}
              labelStyle={TOOLTIP_LABEL_STYLE}
              cursor={CURSOR_LINE}
              formatter={tooltipFormatter}
              labelFormatter={(d) => {
                const s = String(d);
                const [y, m] = s.split("-");
                return `${MONTH_SHORT[parseInt(m, 10) - 1]} ${y}`;
              }}
            />
            <Area
              type="monotone"
              dataKey="price"
              stroke={COLOR_INDIGO}
              strokeWidth={2}
              fill="url(#priceGradient)"
              dot={<SaleDot />}
              activeDot={false}
              connectNulls
            />
            {hasTaxData && (
              <Line
                type="monotone"
                dataKey="tax_assessed"
                stroke={COLOR_AMBER}
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            )}
            {hasNeighborhoodData && (
              <Line
                type="monotone"
                dataKey="neighborhood_median"
                stroke={COLOR_CYAN}
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                connectNulls
              />
            )}
            {zoom.zoomLeft != null && zoom.zoomRight != null && (
              <ReferenceArea
                x1={data[zoom.zoomLeft]?.date}
                x2={data[zoom.zoomRight]?.date}
                strokeOpacity={0.3}
                fill={COLOR_INDIGO}
                fillOpacity={0.1}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default PriceHistoryChart;
