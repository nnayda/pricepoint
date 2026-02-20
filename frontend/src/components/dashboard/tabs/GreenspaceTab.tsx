import type { DashboardData } from "../../../types";
import DashboardCard from "../DashboardCard";
import StatChip from "../ui/StatChip";
import SemiCircularGauge from "../charts/SemiCircularGauge";
import DashboardMap from "../maps/DashboardMap";
import { TreesIcon, FootprintsIcon } from "../ui/Icons";

interface GreenspaceTabProps {
  data: DashboardData;
}

function GreenspaceTab({ data }: GreenspaceTabProps) {
  const { greenspace, property } = data;

  const markers = greenspace.features.map((f) => ({
    lat: f.lat,
    lon: f.lon,
    label: `${f.name} (${f.type})`,
    color: f.type === "Park" ? "#34D399" : "#22D3EE",
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* Score + Stats in a compact row */}
      <div className="grid gap-4 lg:grid-cols-[auto_1fr]">
        <DashboardCard>
          <div className="flex flex-col items-center gap-1">
            <SemiCircularGauge
              value={greenspace.composite_score}
              label="Greenspace Score"
              color="var(--color-db-green)"
              size={150}
            />
          </div>
        </DashboardCard>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Key Statistics
          </h3>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatChip label="Walk Time" value={`${greenspace.walk_minutes_nearest} min`} compact />
            <StatChip label="Parks (1mi)" value={greenspace.parks_within_1mi} compact />
            <StatChip label="Trails (1mi)" value={greenspace.trails_within_1mi} compact />
            <StatChip label="% Greenspace" value={`${greenspace.pct_greenspace}%`} compact />
            <StatChip label="Z-Score" value={greenspace.greenspace_z_score.toFixed(2)} compact />
            <StatChip label="Tree Canopy" value={`${greenspace.tree_canopy_pct}%`} compact />
            <StatChip label="Dog Park" value={greenspace.has_dog_park ? "Yes" : "No"} compact />
            <StatChip label="Features" value={greenspace.features.length} compact />
          </div>
        </DashboardCard>
      </div>

      {/* Feature List + Map side by side */}
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Nearby Green Features
          </h3>
          <div className="space-y-2">
            {greenspace.features.map((f) => (
              <div
                key={f.id}
                className="flex items-center justify-between rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-4 py-2.5"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[var(--color-db-text-muted)]">
                    {f.type === "Park" ? <TreesIcon size={16} /> : <FootprintsIcon size={16} />}
                  </span>
                  <div>
                    <span className="text-sm text-[var(--color-db-text-primary)]">{f.name}</span>
                    <span className="ml-2 text-[11px] text-[var(--color-db-text-muted)]">
                      {f.type}
                    </span>
                  </div>
                </div>
                <div className="flex gap-4 text-[11px] text-[var(--color-db-text-tertiary)]">
                  <span>{f.distance_miles} mi</span>
                  {f.acreage > 0 && <span>{f.acreage} acres</span>}
                </div>
              </div>
            ))}
          </div>
        </DashboardCard>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Greenspace Map
          </h3>
          <DashboardMap
            center={[property.lat, property.lon]}
            zoom={14}
            markers={[
              { lat: property.lat, lon: property.lon, label: "Property", color: "#6366F1" },
              ...markers,
            ]}
            height="320px"
          />
        </DashboardCard>
      </div>
    </div>
  );
}

export default GreenspaceTab;
