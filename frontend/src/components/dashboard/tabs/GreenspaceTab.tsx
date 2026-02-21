import { useState } from "react";
import type { DashboardData } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { TreesIcon, FootprintsIcon, MapPinIcon } from "../ui/Icons";

interface GreenspaceTabProps {
  data: DashboardData;
}

type MapScope = "subdivision" | "neighborhood" | "town";

function FeatureCard({
  feature,
  isSelected,
  onHover,
  onLeave,
  onClick,
}: {
  feature: DashboardData["greenspace"]["features"][number];
  isSelected: boolean;
  onHover: () => void;
  onLeave: () => void;
  onClick: () => void;
}) {
  return (
    <div
      className="flex cursor-pointer gap-4 rounded-[var(--radius-db-sm)] border p-4 transition-colors"
      style={{
        backgroundColor: isSelected
          ? "var(--color-db-accent-muted)"
          : "var(--color-db-surface-alt)",
        borderColor: isSelected
          ? "var(--color-db-accent)"
          : "var(--color-db-border-subtle)",
      }}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      onClick={onClick}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-db-surface)]">
        <span style={{ color: feature.type === "Park" ? "var(--color-db-green)" : "var(--color-db-cyan)" }}>
          {feature.type === "Park" ? <TreesIcon size={18} /> : <FootprintsIcon size={18} />}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-[15px] font-semibold leading-snug text-[var(--color-db-text-primary)]">
              {feature.name}
            </h4>
            <p className="text-[13px] text-[var(--color-db-text-muted)]">{feature.type}</p>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-[13px] text-[var(--color-db-text-tertiary)]">
          <span className="inline-flex items-center gap-1">
            <MapPinIcon size={14} /> {feature.distance_miles} mi
          </span>
          {feature.acreage > 0 && (
            <span className="inline-flex items-center gap-1">{feature.acreage} acres</span>
          )}
        </div>
      </div>
    </div>
  );
}

const SCOPE_ZOOM: Record<MapScope, number> = {
  subdivision: 15,
  neighborhood: 14,
  town: 12,
};

function GreenspaceTab({ data }: GreenspaceTabProps) {
  const { greenspace, property } = data;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mapScope, setMapScope] = useState<MapScope>("neighborhood");

  const markers = greenspace.features.map((f) => ({
    id: f.id,
    lat: f.lat,
    lon: f.lon,
    label: `${f.name} (${f.type})`,
    color: f.type === "Park" ? "#34D399" : "#22D3EE",
  }));

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — feature list */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Green Features
          </h3>
          <div className="flex flex-col gap-2">
            {greenspace.features.map((f) => {
              const isSelected2 = selectedId === f.id;
              return (
                <FeatureCard
                  key={f.id}
                  feature={f}
                  isSelected={isSelected2}
                  onHover={() => setHoveredId(f.id)}
                  onLeave={() => setHoveredId(null)}
                  onClick={() => setSelectedId(isSelected2 ? null : f.id)}
                />
              );
            })}
          </div>
        </DashboardCard>
      </div>

      {/* Right column — map (sticky, fills viewport) */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Greenspace Map
            </h3>
            <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
              {(["subdivision", "neighborhood", "town"] as const).map((scope) => (
                <button
                  key={scope}
                  type="button"
                  onClick={() => setMapScope(scope)}
                  className={`rounded px-3 py-1 text-xs font-medium capitalize transition-colors ${
                    mapScope === scope
                      ? "bg-[var(--color-db-accent)] text-white"
                      : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
                  }`}
                >
                  {scope}
                </button>
              ))}
            </div>
          </div>
          <div className="mb-3 flex justify-center gap-2">
            {[
              { label: "Walk Time", value: `${greenspace.walk_minutes_nearest} min` },
              { label: "Parks (1mi)", value: String(greenspace.parks_within_1mi) },
              { label: "Trails (1mi)", value: String(greenspace.trails_within_1mi) },
              { label: "% Green", value: `${greenspace.pct_greenspace}%` },
              { label: "Tree Canopy", value: `${greenspace.tree_canopy_pct}%` },
              { label: "Dog Park", value: greenspace.has_dog_park ? "Yes" : "No" },
            ].map((stat) => (
              <div
                key={stat.label}
                className="flex flex-col gap-0.5 rounded-[var(--radius-db-sm)] bg-[var(--color-db-surface-alt)] px-3 py-1.5"
              >
                <span
                  className="font-db-sans text-[9px] font-medium uppercase tracking-wider text-[var(--color-db-text-tertiary)]"
                >
                  {stat.label}
                </span>
                <span
                  className="font-db-mono text-xs font-semibold text-[var(--color-db-text-primary)]"
                >
                  {stat.value}
                </span>
              </div>
            ))}
          </div>
          <div className="flex-1">
            <DashboardMap
              center={[property.lat, property.lon]}
              zoom={SCOPE_ZOOM[mapScope]}
              markers={[
                { lat: property.lat, lon: property.lon, label: "Property", color: "#6366F1", isProperty: true },
                ...markers,
              ]}
              height="100%"
              minHeight="400px"
              highlightedId={hoveredId}
              selectedId={selectedId}
            />
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default GreenspaceTab;
