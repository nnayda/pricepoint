import { useState } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  AreaChart,
  Area,
} from "recharts";
import type { DashboardData, DemographicContext } from "../../../types";
import DashboardCard from "../DashboardCard";
import SemiCircularGauge from "../charts/SemiCircularGauge";

interface DemographicsTabProps {
  data: DashboardData;
}

const TOOLTIP_STYLE = {
  backgroundColor: "#1C2333",
  border: "1px solid #2E3553",
  borderRadius: "8px",
  fontFamily: "var(--font-db-sans)",
  fontSize: 12,
  color: "#E8ECF4",
};

const TOOLTIP_ITEM = { color: "#E8ECF4" };
const TOOLTIP_LABEL = { color: "#9BA3BF" };
const CURSOR_STYLE = { fill: "rgba(99, 102, 241, 0.08)" };

const CONTEXT_OPTIONS: { value: DemographicContext; label: string }[] = [
  { value: "subdivision", label: "Subdivision" },
  { value: "neighborhood", label: "Neighborhood" },
  { value: "town", label: "Town" },
];

function DemographicsTab({ data }: DemographicsTabProps) {
  const { demographics } = data;
  const [context, setContext] = useState<DemographicContext>("neighborhood");

  const d = demographics.contexts[context];

  return (
    <div className="flex flex-col gap-4">
      {/* Context pill selector — right-aligned */}
      <div className="flex justify-end">
        <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
          {CONTEXT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setContext(opt.value)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                context === opt.value
                  ? "bg-[var(--color-db-accent)] text-white"
                  : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Race/Ethnicity + Age side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Race & Ethnicity
          </h3>
          <div className="flex items-center justify-center gap-6">
            <div className="w-48 shrink-0">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={d.race_ethnicity}
                    dataKey="value"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius="50%"
                    outerRadius="90%"
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {d.race_ethnicity.map((entry) => (
                      <Cell key={entry.label} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    itemStyle={TOOLTIP_ITEM}
                    labelStyle={TOOLTIP_LABEL}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={((v: number, name: string) => [`${v}%`, name]) as any}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-1.5">
              {d.race_ethnicity.map((entry) => (
                <div key={entry.label} className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="w-20 text-xs text-[var(--color-db-text-secondary)]">
                    {entry.label}
                  </span>
                  <span
                    className="text-xs font-medium text-[var(--color-db-text-primary)]"
                    style={{ fontFamily: "var(--font-db-mono)" }}
                  >
                    {entry.value}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </DashboardCard>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Age Distribution
          </h3>
          <ResponsiveContainer width="100%" height={170}>
            <BarChart
              data={d.age_distribution}
              margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
            >
              <CartesianGrid
                stroke="#2E3553"
                strokeDasharray="3 3"
                vertical={false}
                opacity={0.25}
              />
              <XAxis
                dataKey="range"
                tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-mono)" }}
                axisLine={{ stroke: "#2E3553" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-mono)" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${v}%`}
                width={40}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                itemStyle={TOOLTIP_ITEM}
                labelStyle={TOOLTIP_LABEL}
                cursor={CURSOR_STYLE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number, name: string) => [`${v}%`, name]) as any}
              />
              <Bar dataKey="male" name="Male" fill="#6366F1" radius={[2, 2, 0, 0]} barSize={16} />
              <Bar
                dataKey="female"
                name="Female"
                fill="#22D3EE"
                radius={[2, 2, 0, 0]}
                barSize={16}
              />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-1 flex justify-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-[#6366F1]" />
              <span className="text-xs text-[var(--color-db-text-tertiary)]">Male</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-[#22D3EE]" />
              <span className="text-xs text-[var(--color-db-text-tertiary)]">Female</span>
            </div>
          </div>
        </DashboardCard>
      </div>

      {/* Income + Home Ownership + Population Trend — 3-column layout */}
      <div className="grid gap-4 lg:grid-cols-3">
        <DashboardCard className="flex flex-col">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">Income</h3>
            <span
              className="group relative rounded-full bg-[var(--color-db-accent)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--color-db-accent)]"
              style={{ fontFamily: "var(--font-db-mono)" }}
            >
              ${d.median_income.toLocaleString()}
              <span className="pointer-events-none absolute bottom-full left-1/2 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-md bg-[var(--color-db-surface-alt)] px-2.5 py-1 text-[11px] font-medium text-[var(--color-db-text-secondary)] opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                Median household income
              </span>
            </span>
          </div>
          <div className="flex flex-1 flex-col justify-evenly">
            {d.income_brackets.map((b) => (
              <div key={b.label} className="flex items-center gap-2">
                <span className="w-14 text-[11px] text-[var(--color-db-text-muted)]">
                  {b.label}
                </span>
                <div className="flex-1">
                  <div className="h-1.5 rounded-full bg-[var(--color-db-surface-alt)]">
                    <div
                      className="h-full rounded-full bg-[var(--color-db-accent)]"
                      style={{ width: `${(b.value / 25) * 100}%` }}
                    />
                  </div>
                </div>
                <span
                  className="w-10 text-right text-[11px] text-[var(--color-db-text-secondary)]"
                  style={{ fontFamily: "var(--font-db-mono)" }}
                >
                  {b.value}%
                </span>
              </div>
            ))}
          </div>
        </DashboardCard>

        <DashboardCard className="flex flex-col">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Home Ownership
          </h3>
          <div className="flex flex-1 items-center justify-center">
            <SemiCircularGauge
              value={d.home_ownership_rate}
              label="Ownership Rate"
              color="var(--color-db-green)"
              size={140}
              suffix="%"
              showGrade={false}
            />
          </div>
        </DashboardCard>

        <DashboardCard>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Population Growth
            </h3>
            <span
              className="rounded-full bg-[#22D3EE]/15 px-2.5 py-0.5 text-xs font-semibold text-[#22D3EE]"
              style={{ fontFamily: "var(--font-db-mono)" }}
            >
              {d.population.toLocaleString()}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart
              data={d.population_trend}
              margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
            >
              <defs>
                <linearGradient id="popGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22D3EE" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#22D3EE" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                stroke="#2E3553"
                strokeDasharray="3 3"
                vertical={false}
                opacity={0.25}
              />
              <XAxis
                dataKey="year"
                tick={{ fill: "#9BA3BF", fontSize: 10, fontFamily: "var(--font-db-mono)" }}
                axisLine={{ stroke: "#2E3553" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#9BA3BF", fontSize: 10, fontFamily: "var(--font-db-mono)" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                width={35}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                itemStyle={TOOLTIP_ITEM}
                labelStyle={TOOLTIP_LABEL}
                cursor={{ stroke: "rgba(34, 211, 238, 0.3)", strokeWidth: 1 }}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number) => [v.toLocaleString(), "Population"]) as any}
              />
              <Area
                type="monotone"
                dataKey="population"
                stroke="#22D3EE"
                strokeWidth={2}
                fill="url(#popGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </DashboardCard>
      </div>
    </div>
  );
}

export default DemographicsTab;
