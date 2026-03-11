import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { DashboardData, GreenspaceFeature } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap, { type MapMarker } from "../maps/DashboardMap";
import { TreesIcon, FootprintsIcon, MapPinIcon } from "../ui/Icons";
import { useGreenspace } from "../../../hooks/useGreenspace";

interface Bbox {
  swLat: number;
  swLon: number;
  neLat: number;
  neLon: number;
}

interface GreenspaceTabProps {
  data: DashboardData;
}

type MapScope = "subdivision" | "neighborhood" | "town";
type FeatureType = "Park" | "Trail";

interface DisplayFeature {
  id: string;
  name: string;
  type: FeatureType;
  lat: number;
  lon: number;
  distance_miles: number;
  acreage: number;
  length_miles: number;
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
    length_miles: f.length_miles ?? 0,
  };
}

function FeatureCard({
  feature,
  isSelected,
  isHighlighted,
  onHover,
  onLeave,
  onClick,
  onRef,
}: {
  feature: DisplayFeature;
  isSelected: boolean;
  isHighlighted: boolean;
  onHover: () => void;
  onLeave: () => void;
  onClick: () => void;
  onRef?: (el: HTMLDivElement | null) => void;
}) {
  const active = isSelected || isHighlighted;
  return (
    <div
      ref={onRef}
      className="flex cursor-pointer gap-4 rounded-[var(--radius-db-sm)] border p-4 transition-colors"
      style={{
        backgroundColor: active ? "var(--color-db-accent-muted)" : "var(--color-db-surface-alt)",
        borderColor: isSelected
          ? "var(--color-db-accent)"
          : isHighlighted
            ? "var(--color-db-accent-muted)"
            : "var(--color-db-border-subtle)",
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
          {feature.type === "Park" && feature.acreage > 0 && (
            <span className="inline-flex items-center gap-1">{feature.acreage} acres</span>
          )}
          {feature.type === "Trail" && feature.length_miles > 0 && (
            <span className="inline-flex items-center gap-1">{feature.length_miles} mi long</span>
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

const TYPE_OPTIONS: { value: FeatureType; label: string }[] = [
  { value: "Park", label: "Parks" },
  { value: "Trail", label: "Trails" },
];

function GreenspaceTab({ data }: GreenspaceTabProps) {
  const { property } = data;
  const { data: greenspaceData, loading } = useGreenspace(property.lat, property.lon, 10);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mapScope, setMapScope] = useState<MapScope>("neighborhood");
  const [mapBounds, setMapBounds] = useState<Bbox | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<FeatureType>>(
    new Set<FeatureType>(["Park", "Trail"]),
  );
  const cardRefs = useRef<Map<string, HTMLDivElement | null>>(new Map());
  const listRef = useRef<HTMLDivElement | null>(null);

  const handleBoundsChange = useCallback((bbox: Bbox) => setMapBounds(bbox), []);

  const toggleType = useCallback((type: FeatureType) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  const allFeatures = useMemo(
    () => greenspaceData.features.map(mapApiFeature),
    [greenspaceData.features],
  );

  const typeFilteredFeatures = useMemo(
    () =>
      activeTypes.size === 2 ? allFeatures : allFeatures.filter((f) => activeTypes.has(f.type)),
    [allFeatures, activeTypes],
  );

  const displayFeatures = useMemo(() => {
    if (!mapBounds) return typeFilteredFeatures;
    return typeFilteredFeatures.filter(
      (f) =>
        f.lat >= mapBounds.swLat &&
        f.lat <= mapBounds.neLat &&
        f.lon >= mapBounds.swLon &&
        f.lon <= mapBounds.neLon,
    );
  }, [typeFilteredFeatures, mapBounds]);

  const parkCount = useMemo(
    () => displayFeatures.filter((f) => f.type === "Park").length,
    [displayFeatures],
  );

  const trailCount = useMemo(
    () => displayFeatures.filter((f) => f.type === "Trail").length,
    [displayFeatures],
  );

  const mapMarkers = useMemo(
    () =>
      typeFilteredFeatures.map((f) => ({
        id: f.id,
        lat: f.lat,
        lon: f.lon,
        label:
          f.type === "Trail" && f.length_miles > 0
            ? `${f.name} — ${f.length_miles} mi`
            : f.type === "Park" && f.acreage > 0
              ? `${f.name} — ${f.acreage} acres`
              : `${f.name} (${f.type})`,
        color: f.type === "Park" ? "#34D399" : "#22D3EE",
      })),
    [typeFilteredFeatures],
  );

  const featureById = useMemo(() => {
    const map = new Map<string, DisplayFeature>();
    for (const f of allFeatures) {
      map.set(f.id, f);
    }
    return map;
  }, [allFeatures]);

  const renderPopup = useCallback(
    (marker: MapMarker) => {
      const feature = marker.id ? featureById.get(marker.id) : undefined;
      if (!feature) return <span style={{ fontSize: 12 }}>{marker.label}</span>;
      const isPark = feature.type === "Park";
      const typeColor = isPark ? "#34D399" : "#22D3EE";
      return (
        <div style={{ fontFamily: "var(--font-db-sans)", minWidth: 180 }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{feature.name}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: `${typeColor}22`,
                color: typeColor,
              }}
            >
              {isPark ? "P" : "T"}
            </span>
            <span style={{ fontSize: 11, color: "#9BA3BF" }}>{feature.type}</span>
          </div>
          <div style={{ display: "flex", gap: 10, fontSize: 11, color: "#9BA3BF" }}>
            <span>{feature.distance_miles} mi away</span>
            {isPark && feature.acreage > 0 && <span>{feature.acreage} acres</span>}
            {!isPark && feature.length_miles > 0 && <span>{feature.length_miles} mi long</span>}
          </div>
        </div>
      );
    },
    [featureById],
  );

  const handleMarkerSelect = useCallback((id: string) => setSelectedId(id), []);
  const handleMarkerDeselect = useCallback(() => setSelectedId(null), []);

  // Scroll selected card into view when selected from the map
  useEffect(() => {
    if (selectedId) {
      const el = cardRefs.current.get(selectedId);
      if (el) {
        el.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [selectedId]);

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
            <div ref={listRef} className="flex flex-col gap-2">
              {displayFeatures.map((f) => {
                const isSelected2 = selectedId === f.id;
                const isHighlighted = hoveredId === f.id;
                return (
                  <FeatureCard
                    key={f.id}
                    feature={f}
                    isSelected={isSelected2}
                    isHighlighted={isHighlighted}
                    onHover={() => setHoveredId(f.id)}
                    onLeave={() => setHoveredId(null)}
                    onClick={() => setSelectedId(isSelected2 ? null : f.id)}
                    onRef={(el) => {
                      if (el) cardRefs.current.set(f.id, el);
                      else cardRefs.current.delete(f.id);
                    }}
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
            <div className="flex items-center gap-2">
              <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
                {TYPE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggleType(opt.value)}
                    className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                      activeTypes.has(opt.value)
                        ? "bg-[var(--color-db-accent)] text-white"
                        : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
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
                ...mapMarkers,
              ]}
              height="100%"
              minHeight="400px"
              highlightedId={hoveredId}
              selectedId={selectedId}
              onMoveEnd={handleBoundsChange}
              onMarkerSelect={handleMarkerSelect}
              onMarkerDeselect={handleMarkerDeselect}
              renderPopup={renderPopup}
            >
              {/* Vector tile layers for greenspaces and trails */}
              <Source
                id="greenspaces-tiles"
                type="vector"
                tiles={[`${window.location.origin}/tiles/greenspaces/{z}/{x}/{y}`]}
                minzoom={0}
                maxzoom={14}
              >
                <Layer
                  id="greenspaces-fill"
                  type="fill"
                  source-layer="greenspaces"
                  paint={{
                    "fill-color": "#34D399",
                    "fill-opacity": 0.2,
                  }}
                />
                <Layer
                  id="greenspaces-outline"
                  type="line"
                  source-layer="greenspaces"
                  paint={{
                    "line-color": "#34D399",
                    "line-width": 1,
                    "line-opacity": 0.5,
                  }}
                />
              </Source>
              <Source
                id="trails-tiles"
                type="vector"
                tiles={[`${window.location.origin}/tiles/trails/{z}/{x}/{y}`]}
                minzoom={0}
                maxzoom={14}
              >
                <Layer
                  id="trails-line"
                  type="line"
                  source-layer="trails"
                  paint={{
                    "line-color": "#22D3EE",
                    "line-width": 2,
                    "line-opacity": 0.7,
                  }}
                />
              </Source>
            </DashboardMap>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default GreenspaceTab;
