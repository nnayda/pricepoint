import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ReferenceLine,
} from "recharts";
import type { ShapFeature } from "../../../types";

interface ShapWaterfallProps {
  features: ShapFeature[];
}

function ShapWaterfall({ features }: ShapWaterfallProps) {
  const sorted = [...features].sort(
    (a, b) => Math.abs(b.impact_dollars) - Math.abs(a.impact_dollars),
  );
  const top10 = sorted.slice(0, 10);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart
        data={top10}
        layout="vertical"
        margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
      >
        <XAxis
          type="number"
          tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-mono)" }}
          axisLine={{ stroke: "#2E3553" }}
          tickLine={false}
          tickFormatter={(v: number) =>
            v >= 0 ? `+$${(v / 1000).toFixed(0)}k` : `-$${(Math.abs(v) / 1000).toFixed(0)}k`
          }
        />
        <YAxis
          type="category"
          dataKey="display_name"
          tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-sans)" }}
          axisLine={false}
          tickLine={false}
          width={110}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1C2333",
            border: "1px solid #2E3553",
            borderRadius: "8px",
            fontFamily: "var(--font-db-sans)",
            fontSize: 12,
            color: "#E8ECF4",
          }}
          itemStyle={{ color: "#E8ECF4" }}
          labelStyle={{ color: "#9BA3BF" }}
          cursor={{ fill: "rgba(99, 102, 241, 0.08)" }}
          formatter={
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ((value: number) => [`${value >= 0 ? "+" : ""}$${value.toLocaleString()}`, "Impact"]) as any
          }
        />
        <ReferenceLine x={0} stroke="#2E3553" />
        <Bar dataKey="impact_dollars" radius={[0, 4, 4, 0]} barSize={18}>
          {top10.map((f) => (
            <Cell
              key={f.feature}
              fill={f.impact_dollars >= 0 ? "#34D399" : "#F87171"}
              fillOpacity={0.8}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default ShapWaterfall;
