import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { PriceHistoryPoint } from "../../../types";
import {
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  AXIS_TICK_MONO,
  AXIS_LINE_STYLE,
  GRID_STYLE,
  CURSOR_LINE,
  COLOR_INDIGO,
  COLOR_CYAN,
} from "../../../utils/chartTokens";

interface PriceHistoryChartProps {
  data: PriceHistoryPoint[];
  showNeighborhood?: boolean;
}

function PriceHistoryChart({ data, showNeighborhood = true }: PriceHistoryChartProps) {
  return (
    <div className="flex flex-col">
      {/* Legend */}
      <div className="mb-2 flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 rounded-full" style={{ backgroundColor: COLOR_INDIGO }} />
          <span className="text-[11px] text-[var(--color-db-text-secondary)]">Property</span>
        </div>
        {showNeighborhood && (
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block h-0.5 w-4"
              style={{ backgroundImage: `repeating-linear-gradient(to right, ${COLOR_CYAN} 0, ${COLOR_CYAN} 3px, transparent 3px, transparent 6px)` }}
            />
            <span className="text-[11px] text-[var(--color-db-text-secondary)]">Neighborhood Median</span>
          </div>
        )}
      </div>
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={COLOR_INDIGO} stopOpacity={0.3} />
            <stop offset="100%" stopColor={COLOR_INDIGO} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid {...GRID_STYLE} vertical={false} />
        <XAxis
          dataKey="date"
          tick={AXIS_TICK_MONO}
          axisLine={AXIS_LINE_STYLE}
          tickLine={false}
          interval={2}
        />
        <YAxis
          tick={AXIS_TICK_MONO}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
          width={55}
        />
        <Tooltip
          contentStyle={TOOLTIP_CONTENT_STYLE}
          itemStyle={TOOLTIP_ITEM_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
          cursor={CURSOR_LINE}
          formatter={
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ((value: number, name: string) => [`$${value.toLocaleString()}`, name === "price" ? "Property" : "Neighborhood"]) as any
          }
        />
        <Area
          type="monotone"
          dataKey="price"
          stroke={COLOR_INDIGO}
          strokeWidth={2}
          fill="url(#priceGradient)"
        />
        {showNeighborhood && (
          <Line
            type="monotone"
            dataKey="neighborhood_median"
            stroke={COLOR_CYAN}
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
    </div>
  );
}

export default PriceHistoryChart;
