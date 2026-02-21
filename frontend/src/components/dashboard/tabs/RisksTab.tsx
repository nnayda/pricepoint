import { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";
import type { DashboardData } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { RISK_ICONS } from "../ui/Icons";

interface RisksTabProps {
  data: DashboardData;
}

const levelColors: Record<string, string> = {
  Low: "var(--color-db-green)",
  Moderate: "var(--color-db-yellow)",
  High: "var(--color-db-orange)",
  "Very High": "var(--color-db-red)",
};

const HIDDEN_RISK_IDS = new Set(["earthquake", "air"]);

function RisksTab({ data }: RisksTabProps) {
  const { risks, crime, property } = data;
  const [mapMode, setMapMode] = useState<"density" | "incidents">("incidents");

  const crimeMarkers = crime.incidents.map((inc) => ({
    lat: inc.lat,
    lon: inc.lon,
    label: `${inc.incident_type} — ${inc.date}`,
    color: "#F87171",
  }));

  const visibleCategories = risks.categories.filter((c) => !HIDDEN_RISK_IDS.has(c.id));

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — risks + crime stats + breakdown */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Risk Assessment
          </h3>
          <div className="grid grid-cols-1 gap-3">
            {visibleCategories.map((cat) => {
              const IconComponent = RISK_ICONS[cat.icon] || RISK_ICONS.flood;
              return (
                <div
                  key={cat.id}
                  className="flex flex-col gap-1.5 rounded-[var(--radius-db-sm)] bg-[var(--color-db-surface-alt)] p-3"
                >
                  <div className="flex items-center justify-between">
                    <span style={{ color: levelColors[cat.level] }}>
                      <IconComponent size={16} />
                    </span>
                    <span
                      className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
                      style={{
                        color: levelColors[cat.level],
                        backgroundColor: `${levelColors[cat.level]}20`,
                      }}
                    >
                      {cat.level}
                    </span>
                  </div>
                  <h4 className="text-xs font-medium text-[var(--color-db-text-primary)]">
                    {cat.label}
                  </h4>
                  <div className="h-1 rounded-full bg-[var(--color-db-surface)]">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${cat.score}%`,
                        backgroundColor: levelColors[cat.level],
                      }}
                    />
                  </div>
                  <p className="text-[10px] leading-tight text-[var(--color-db-text-muted)]">
                    {cat.detail}
                  </p>
                </div>
              );
            })}
          </div>
        </DashboardCard>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Crime Breakdown
          </h3>
          <ResponsiveContainer width="100%" height={crime.breakdown.length * 36 + 10}>
            <BarChart
              data={crime.breakdown}
              layout="vertical"
              margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
            >
              <CartesianGrid
                stroke="#2E3553"
                strokeDasharray="3 3"
                horizontal={false}
                opacity={0.25}
              />
              <XAxis
                type="number"
                tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-mono)" }}
                axisLine={{ stroke: "#2E3553" }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="category"
                tick={{ fill: "#9BA3BF", fontSize: 10, fontFamily: "var(--font-db-sans)" }}
                axisLine={false}
                tickLine={false}
                width={80}
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
                cursor={{ fill: "rgba(99, 102, 241, 0.1)" }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={20}>
                {crime.breakdown.map((_, i) => (
                  <Cell
                    key={i}
                    fill={["#6366F1", "#F87171", "#FB923C", "#FBBF24", "#A78BFA"][i % 5]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </DashboardCard>
      </div>

      {/* Right column — Crime Map (sticky, fills viewport) */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">Crime Map</h3>
            <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
              {(["incidents", "density"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setMapMode(mode)}
                  className={`rounded px-3 py-1 text-xs font-medium capitalize transition-colors ${
                    mapMode === mode
                      ? "bg-[var(--color-db-accent)] text-white"
                      : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>
          <div className="mb-3 flex justify-center gap-2">
            {[
              { label: "Z-Score", value: crime.z_score.toFixed(2), raw: crime.z_score },
              { label: "Growth", value: `${crime.growth_rate}%`, raw: crime.growth_rate },
              { label: "Incidents", value: String(crime.total_incidents), raw: null },
            ].map((stat) => (
              <div
                key={stat.label}
                className="flex flex-col gap-0.5 rounded-[var(--radius-db-sm)] bg-[var(--color-db-surface-alt)] px-3 py-1.5"
              >
                <span
                  className="text-[9px] font-medium uppercase tracking-wider text-[var(--color-db-text-tertiary)]"
                  style={{ fontFamily: "var(--font-db-sans)" }}
                >
                  {stat.label}
                </span>
                <span
                  className="text-xs font-semibold"
                  style={{
                    fontFamily: "var(--font-db-mono)",
                    color:
                      stat.raw === null
                        ? "var(--color-db-text-primary)"
                        : stat.raw < 0
                          ? "var(--color-db-green)"
                          : stat.raw > 0
                            ? "var(--color-db-red)"
                            : "var(--color-db-text-primary)",
                  }}
                >
                  {stat.value}
                </span>
              </div>
            ))}
          </div>
          <div className="flex-1">
            <DashboardMap
              center={[property.lat, property.lon]}
              zoom={14}
              markers={[
                { lat: property.lat, lon: property.lon, label: "Property", color: "#6366F1", isProperty: true },
                ...(mapMode === "incidents" ? crimeMarkers : []),
              ]}
              height="100%"
              minHeight="400px"
            />
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default RisksTab;
