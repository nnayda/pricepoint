import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import type { SaleHistoryEntry, TaxHistoryEntry } from "../../types";

interface SaleTaxHistoryChartProps {
  saleHistory: SaleHistoryEntry[];
  taxHistory: TaxHistoryEntry[];
}

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

interface ChartRow {
  year: string;
  salePrice?: number;
  assessedValue?: number;
}

function buildChartData(sales: SaleHistoryEntry[], taxes: TaxHistoryEntry[]): ChartRow[] {
  const map = new Map<string, ChartRow>();

  for (const s of sales) {
    const year = s.date.slice(0, 4);
    const existing = map.get(year) ?? { year };
    existing.salePrice = s.price;
    map.set(year, existing);
  }

  for (const t of taxes) {
    const year = String(t.year);
    const existing = map.get(year) ?? { year };
    existing.assessedValue = t.assessed_value;
    map.set(year, existing);
  }

  return Array.from(map.values()).sort((a, b) => a.year.localeCompare(b.year));
}

function formatYAxis(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

function SaleTaxHistoryChart({ saleHistory, taxHistory }: SaleTaxHistoryChartProps) {
  const data = buildChartData(saleHistory, taxHistory);

  if (data.length === 0) {
    return (
      <section
        aria-label="Sale and tax history"
        className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
      >
        <h2 className="text-lg font-bold text-text-pri">Sale &amp; Tax History</h2>
        <p className="mt-3 text-sm text-text-sec">No history data available.</p>
      </section>
    );
  }

  return (
    <section
      aria-label="Sale and tax history"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <h2 className="text-lg font-bold text-text-pri">Sale &amp; Tax History</h2>
      <div className="mt-4" style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="year" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={formatYAxis} tick={{ fontSize: 12 }} width={60} />
            <Tooltip
              formatter={(value) => currency.format(Number(value ?? 0))}
              labelFormatter={(label) => `Year: ${String(label)}`}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="assessedValue"
              name="Assessed Value"
              fill="#4f46e5"
              fillOpacity={0.1}
              stroke="#4f46e5"
              strokeWidth={2}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="salePrice"
              name="Sale Price"
              stroke="#ff5c8e"
              strokeWidth={2}
              dot={{ r: 4 }}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default SaleTaxHistoryChart;
