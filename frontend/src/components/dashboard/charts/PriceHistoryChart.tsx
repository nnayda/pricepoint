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

interface PriceHistoryChartProps {
  data: PriceHistoryPoint[];
  showNeighborhood?: boolean;
}

const TOOLTIP_STYLE = {
  backgroundColor: "#1C2333",
  border: "1px solid #2E3553",
  borderRadius: "8px",
  fontFamily: "var(--font-db-sans)",
  fontSize: 12,
  color: "#E8ECF4",
};

function PriceHistoryChart({ data, showNeighborhood = true }: PriceHistoryChartProps) {
  return (
    <div className="flex flex-col">
      {/* Legend */}
      <div className="mb-2 flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 rounded-full" style={{ backgroundColor: "#6366F1" }} />
          <span className="text-[11px] text-[var(--color-db-text-secondary)]">Property</span>
        </div>
        {showNeighborhood && (
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block h-0.5 w-4"
              style={{ backgroundImage: "repeating-linear-gradient(to right, #22D3EE 0, #22D3EE 3px, transparent 3px, transparent 6px)" }}
            />
            <span className="text-[11px] text-[var(--color-db-text-secondary)]">Neighborhood Median</span>
          </div>
        )}
      </div>
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366F1" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#6366F1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#2E3553" strokeDasharray="3 3" vertical={false} opacity={0.25} />
        <XAxis
          dataKey="date"
          tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-mono)" }}
          axisLine={{ stroke: "#2E3553" }}
          tickLine={false}
          interval={2}
        />
        <YAxis
          tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-mono)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
          width={55}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          itemStyle={{ color: "#E8ECF4" }}
          labelStyle={{ color: "#9BA3BF" }}
          cursor={{ stroke: "rgba(99, 102, 241, 0.3)", strokeWidth: 1 }}
          formatter={
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ((value: number, name: string) => [`$${value.toLocaleString()}`, name === "price" ? "Property" : "Neighborhood"]) as any
          }
        />
        <Area
          type="monotone"
          dataKey="price"
          stroke="#6366F1"
          strokeWidth={2}
          fill="url(#priceGradient)"
        />
        {showNeighborhood && (
          <Line
            type="monotone"
            dataKey="neighborhood_median"
            stroke="#22D3EE"
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
