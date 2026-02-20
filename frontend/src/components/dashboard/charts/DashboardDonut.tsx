import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";

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
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={((value: number, name: string) => [`$${Math.round(value).toLocaleString()}`, name]) as any}
          />
        </PieChart>
      </ResponsiveContainer>
      {centerLabel && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-lg font-bold text-[var(--color-db-text-primary)]"
            style={{ fontFamily: "var(--font-db-mono)" }}
          >
            {centerValue}
          </span>
          <span className="text-[10px] text-[var(--color-db-text-muted)]">{centerLabel}</span>
        </div>
      )}
    </div>
  );
}

export default DashboardDonut;
