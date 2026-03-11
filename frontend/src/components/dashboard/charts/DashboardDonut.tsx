import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import {
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
} from "../../../utils/chartTokens";

interface DonutSegment {
  label: string;
  value: number;
  color: string;
}

interface DashboardDonutProps {
  data: DonutSegment[];
  centerLabel?: string;
  centerValue?: string;
  size?: number;
}

function DashboardDonut({ data, centerLabel, centerValue, size = 200 }: DashboardDonutProps) {
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="85%"
            paddingAngle={2}
            strokeWidth={0}
          >
            {data.map((d) => (
              <Cell key={d.label} fill={d.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            formatter={
              ((value: number, name: string) => [
                `$${Math.round(value).toLocaleString()}`,
                name,
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
              ]) as any
            }
          />
        </PieChart>
      </ResponsiveContainer>
      {centerLabel && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-db-mono text-lg font-bold text-[var(--color-db-text-primary)]">
            {centerValue}
          </span>
          <span className="text-[10px] text-[var(--color-db-text-muted)]">{centerLabel}</span>
        </div>
      )}
    </div>
  );
}

export default DashboardDonut;
