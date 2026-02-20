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
import StatChip from "../ui/StatChip";
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

function RisksTab({ data }: RisksTabProps) {
  const { risks, crime, property } = data;
  const [mapMode, setMapMode] = useState<"density" | "incidents">("incidents");

  const crimeMarkers = crime.incidents.map((inc) => ({
    lat: inc.lat,
    lon: inc.lon,
    label: `${inc.incident_type} — ${inc.date}`,
    color: "#F87171",
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* Overall Risk Score + Risk Category Grid */}
      <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
        <DashboardCard>
          <div className="flex flex-col items-center gap-2 py-2">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--color-db-green-muted)]">
              <span
                className="text-2xl font-bold text-[var(--color-db-green)]"
                style={{ fontFamily: "var(--font-db-mono)" }}
              >
                {risks.overall_score}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Overall Risk Score
            </h3>
            <p className="text-center text-xs text-[var(--color-db-text-tertiary)]">
              Low risk — Below average for Wake County
            </p>
          </div>
        </DashboardCard>

        <DashboardCard>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {risks.categories.map((cat) => {
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
      </div>

      {/* Crime Stats + Breakdown side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Crime Statistics
          </h3>
          <div className="grid grid-cols-3 gap-2">
            <StatChip label="Z-Score" value={crime.z_score.toFixed(2)} compact />
            <StatChip
              label="Growth Rate"
              value={`${crime.growth_rate}%`}
              delta={crime.growth_rate}
              compact
            />
            <StatChip label="Incidents (1yr)" value={crime.total_incidents} compact />
          </div>
        </DashboardCard>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Crime Breakdown
          </h3>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={crime.breakdown} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid
                stroke="#2E3553"
                strokeDasharray="3 3"
                vertical={false}
                opacity={0.25}
              />
              <XAxis
                dataKey="category"
                tick={{ fill: "#9BA3BF", fontSize: 10, fontFamily: "var(--font-db-sans)" }}
                axisLine={{ stroke: "#2E3553" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#9BA3BF", fontSize: 11, fontFamily: "var(--font-db-mono)" }}
                axisLine={false}
                tickLine={false}
                width={30}
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
              <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={24}>
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

      {/* Crime Map */}
      <DashboardCard>
        <div className="mb-3 flex items-center justify-between">
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
        <DashboardMap
          center={[property.lat, property.lon]}
          zoom={14}
          markers={mapMode === "incidents" ? crimeMarkers : []}
          height="320px"
        />
      </DashboardCard>
    </div>
  );
}

export default RisksTab;
