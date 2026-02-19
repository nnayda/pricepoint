import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Scatter,
} from "recharts";
import type { ForecastTimeline } from "../../types";

interface ForecastChartProps {
  timeline: ForecastTimeline[];
  saleHistory?: { date: string; price: number }[];
}

function formatDollar(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  return `$${Math.round(value / 1_000)}k`;
}

function formatTooltipDollar(value: number): string {
  return `$${value.toLocaleString()}`;
}

export default function ForecastChart({ timeline, saleHistory }: ForecastChartProps) {
  const historyData = (saleHistory ?? []).map((s) => ({
    date: s.date,
    history: s.price,
  }));

  const forecastData = timeline.map((t) => ({
    date: t.date,
    forecast: t.value,
    low: t.low,
    high: t.high,
    band: [t.low, t.high] as [number, number],
  }));

  const combined = [...historyData, ...forecastData].sort((a, b) => a.date.localeCompare(b.date));

  if (combined.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 p-8"
        data-testid="forecast-chart-empty"
      >
        <p className="text-gray-500">No forecast data available</p>
      </div>
    );
  }

  return (
    <div data-testid="forecast-chart">
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={combined} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={formatDollar} tick={{ fontSize: 12 }} width={70} />
          <Tooltip
            formatter={(value?: number, name?: string) => {
              const label =
                name === "history" ? "Sale Price" : name === "forecast" ? "Forecast" : (name ?? "");
              return [formatTooltipDollar(value ?? 0), label];
            }}
          />
          <Legend />
          <Area
            type="monotone"
            dataKey="band"
            fill="#fdba74"
            fillOpacity={0.3}
            stroke="none"
            name="Confidence Band"
          />
          <Line
            type="monotone"
            dataKey="history"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 5, fill: "#3b82f6" }}
            name="Sale Price"
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#f97316"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            name="Forecast"
          />
          <Scatter dataKey="history" fill="#3b82f6" name="Sales" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
