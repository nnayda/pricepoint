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
import {
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  AXIS_TICK_MONO,
  AXIS_TICK_SANS,
  AXIS_LINE_STYLE,
  CURSOR_BAR,
  COLOR_GREEN,
  COLOR_RED,
  COLOR_GRID_LINE,
} from "../../../utils/chartTokens";

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
      <BarChart data={top10} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
        <XAxis
          type="number"
          tick={AXIS_TICK_MONO}
          axisLine={AXIS_LINE_STYLE}
          tickLine={false}
          tickFormatter={(v: number) =>
            v >= 0 ? `+$${(v / 1000).toFixed(0)}k` : `-$${(Math.abs(v) / 1000).toFixed(0)}k`
          }
        />
        <YAxis
          type="category"
          dataKey="display_name"
          tick={AXIS_TICK_SANS}
          axisLine={false}
          tickLine={false}
          width={110}
        />
        <Tooltip
          contentStyle={TOOLTIP_CONTENT_STYLE}
          itemStyle={TOOLTIP_ITEM_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
          cursor={CURSOR_BAR}
          formatter={
            ((value: number) => [
              `${value >= 0 ? "+" : ""}$${value.toLocaleString()}`,
              "Impact",
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ]) as any
          }
        />
        <ReferenceLine x={0} stroke={COLOR_GRID_LINE} />
        <Bar dataKey="impact_dollars" radius={[0, 4, 4, 0]} barSize={18}>
          {top10.map((f) => (
            <Cell
              key={f.feature}
              fill={f.impact_dollars >= 0 ? COLOR_GREEN : COLOR_RED}
              fillOpacity={0.8}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default ShapWaterfall;
