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
import {
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  AXIS_TICK_MONO,
  AXIS_TICK_MONO_SM,
  AXIS_LINE_STYLE,
  GRID_STYLE,
  CURSOR_BAR,
  CURSOR_LINE_CYAN,
  COLOR_INDIGO,
  COLOR_CYAN,
  COLOR_GRID_LINE,
} from "../../../utils/chartTokens";

interface DemographicsTabProps {
  data: DashboardData;
}

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
                    contentStyle={TOOLTIP_CONTENT_STYLE}
                    itemStyle={TOOLTIP_ITEM_STYLE}
                    labelStyle={TOOLTIP_LABEL_STYLE}
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
                    className="font-db-mono text-xs font-medium text-[var(--color-db-text-primary)]"
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
                {...GRID_STYLE}
                vertical={false}
              />
              <XAxis
                dataKey="range"
                tick={AXIS_TICK_MONO}
                axisLine={{ stroke: COLOR_GRID_LINE }}
                tickLine={false}
              />
              <YAxis
                tick={AXIS_TICK_MONO}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${v}%`}
                width={40}
              />
              <Tooltip
                contentStyle={TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_BAR}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number, name: string) => [`${v}%`, name]) as any}
              />
              <Bar dataKey="male" name="Male" fill={COLOR_INDIGO} radius={[2, 2, 0, 0]} barSize={16} />
              <Bar
                dataKey="female"
                name="Female"
                fill={COLOR_CYAN}
                radius={[2, 2, 0, 0]}
                barSize={16}
              />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-1 flex justify-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className={`h-2.5 w-2.5 rounded-sm`} style={{ backgroundColor: COLOR_INDIGO }} />
              <span className="text-xs text-[var(--color-db-text-tertiary)]">Male</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`h-2.5 w-2.5 rounded-sm`} style={{ backgroundColor: COLOR_CYAN }} />
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
              className="group relative rounded-full font-db-mono bg-[var(--color-db-accent)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--color-db-accent)]"
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
                  className="w-10 text-right font-db-mono text-[11px] text-[var(--color-db-text-secondary)]"
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
              className="rounded-full font-db-mono px-2.5 py-0.5 text-xs font-semibold"
              style={{ backgroundColor: `${COLOR_CYAN}26`, color: COLOR_CYAN }}
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
                  <stop offset="0%" stopColor={COLOR_CYAN} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={COLOR_CYAN} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                {...GRID_STYLE}
                vertical={false}
              />
              <XAxis
                dataKey="year"
                tick={AXIS_TICK_MONO_SM}
                axisLine={AXIS_LINE_STYLE}
                tickLine={false}
              />
              <YAxis
                tick={AXIS_TICK_MONO_SM}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                width={35}
              />
              <Tooltip
                contentStyle={TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_LINE_CYAN}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number) => [v.toLocaleString(), "Population"]) as any}
              />
              <Area
                type="monotone"
                dataKey="population"
                stroke={COLOR_CYAN}
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
