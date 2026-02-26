import { useState, useMemo, useEffect, useCallback } from "react";
import { useMapEvents } from "react-leaflet";
import type { DashboardData, GreenspaceFeature } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { TreesIcon, FootprintsIcon, MapPinIcon } from "../ui/Icons";
import { useGreenspace } from "../../../hooks/useGreenspace";

interface Bbox {
  swLat: number;
  swLon: number;
  neLat: number;
  neLon: number;
}

/** Reports map viewport bounds on mount and on every moveend. */
function MapBoundsTracker({ onBoundsChange }: { onBoundsChange: (bbox: Bbox) => void }) {
  const map = useMapEvents({
    moveend: () => {
      const b = map.getBounds();
      onBoundsChange({
        swLat: b.getSouth(),
        swLon: b.getWest(),
        neLat: b.getNorth(),
        neLon: b.getEast(),
      });
    },
  });

  useEffect(() => {
    const timer = setTimeout(() => {
      const b = map.getBounds();
      onBoundsChange({
        swLat: b.getSouth(),
        swLon: b.getWest(),
        neLat: b.getNorth(),
        neLon: b.getEast(),
      });
    }, 100);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

interface GreenspaceTabProps {
  data: DashboardData;
}

type MapScope = "subdivision" | "neighborhood" | "town";

interface DisplayFeature {
  id: string;
  name: string;
  type: string;
  lat: number;
  lon: number;
  distance_miles: number;
  acreage: number;
}

function mapApiFeature(f: GreenspaceFeature): DisplayFeature {
  return {
    id: f.id,
    name: f.name,
    type: f.feature_type === "park" ? "Park" : "Trail",
    lat: f.lat,
    lon: f.lon,
    distance_miles: f.distance_miles,
    acreage: f.acreage ?? 0,
  };
}

function FeatureCard({
  feature,
  isSelected,
  onHover,
  onLeave,
  onClick,
}: {
  feature: DisplayFeature;
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
        borderColor: isSelected ? "var(--color-db-accent)" : "var(--color-db-border-subtle)",
      }}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      onClick={onClick}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-db-surface)]">
        <span
          style={{
            color: feature.type === "Park" ? "var(--color-db-green)" : "var(--color-db-cyan)",
          }}
        >
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
  const { property } = data;
  const { data: greenspaceData, loading } = useGreenspace(property.lat, property.lon);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mapScope, setMapScope] = useState<MapScope>("neighborhood");
  const [mapBounds, setMapBounds] = useState<Bbox | null>(null);

  const handleBoundsChange = useCallback((bbox: Bbox) => setMapBounds(bbox), []);

  const allFeatures = useMemo(
    () => greenspaceData.features.map(mapApiFeature),
    [greenspaceData.features],
  );

  const displayFeatures = useMemo(() => {
    if (!mapBounds) return allFeatures;
    return allFeatures.filter(
      (f) =>
        f.lat >= mapBounds.swLat &&
        f.lat <= mapBounds.neLat &&
        f.lon >= mapBounds.swLon &&
        f.lon <= mapBounds.neLon,
    );
  }, [allFeatures, mapBounds]);

  const parkCount = useMemo(
    () => displayFeatures.filter((f) => f.type === "Park").length,
    [displayFeatures],
  );

  const trailCount = useMemo(
    () => displayFeatures.filter((f) => f.type === "Trail").length,
    [displayFeatures],
  );

  const markers = allFeatures.map((f) => ({
    id: f.id,
    lat: f.lat,
    lon: f.lon,
    label: `${f.name} (${f.type})`,
    color: f.type === "Park" ? "#34D399" : "#22D3EE",
  }));

  const { metrics } = greenspaceData;

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — feature list */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Green Features
          </h3>
          {loading ? (
            <div className="flex flex-col gap-2">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-20 animate-pulse rounded-[var(--radius-db-sm)] bg-[var(--color-db-surface-alt)]"
                />
              ))}
            </div>
          ) : displayFeatures.length === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--color-db-text-muted)]">
              No greenspaces or trails found nearby.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {displayFeatures.map((f) => {
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
          )}
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
              { label: "Parks", value: String(parkCount) },
              { label: "Trails", value: String(trailCount) },
              {
                label: "Nearest Park",
                value: metrics.nearest_park_miles > 0 ? `${metrics.nearest_park_miles} mi` : "—",
              },
              {
                label: "Nearest Trail",
                value:
                  metrics.nearest_greenway_miles > 0 ? `${metrics.nearest_greenway_miles} mi` : "—",
              },
              {
                label: "Green Acres",
                value: metrics.total_green_acres_1mi > 0 ? `${metrics.total_green_acres_1mi}` : "—",
              },
            ].map((stat) => (
              <div
                key={stat.label}
                className="flex flex-col gap-0.5 rounded-[var(--radius-db-sm)] bg-[var(--color-db-surface-alt)] px-3 py-1.5"
              >
                <span className="font-db-sans text-[9px] font-medium uppercase tracking-wider text-[var(--color-db-text-tertiary)]">
                  {stat.label}
                </span>
                <span className="font-db-mono text-xs font-semibold text-[var(--color-db-text-primary)]">
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
                {
                  lat: property.lat,
                  lon: property.lon,
                  label: "Property",
                  color: "#6366F1",
                  isProperty: true,
                },
                ...markers,
              ]}
              height="100%"
              minHeight="400px"
              highlightedId={hoveredId}
              selectedId={selectedId}
            >
              <MapBoundsTracker onBoundsChange={handleBoundsChange} />
            </DashboardMap>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default GreenspaceTab;
