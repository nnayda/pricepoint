import { useState, useCallback, useMemo } from "react";
import { Source, Layer, Popup, useMap } from "react-map-gl/maplibre";
import type { MapLayerMouseEvent } from "react-map-gl/maplibre";
import type { DashboardData, NegativePoi } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import ChoroplethLegend from "../maps/ChoroplethLegend";
import { MapPinIcon } from "../ui/Icons";
import { useNuisanceSources } from "../../../hooks/useNuisanceSources";
import { getNoiseLegendConfig } from "../../../utils/noiseColors";
import { useEffect } from "react";

interface NuisancesTabProps {
  data: DashboardData;
}

const severityStyles: Record<string, { bg: string; text: string; border: string }> = {
  Safe: {
    bg: "var(--color-db-green-muted)",
    text: "var(--color-db-green)",
    border: "var(--color-db-green)",
  },
  Caution: {
    bg: "var(--color-db-yellow-muted)",
    text: "var(--color-db-yellow)",
    border: "var(--color-db-yellow)",
  },
  Concern: {
    bg: "var(--color-db-red-muted)",
    text: "var(--color-db-red)",
    border: "var(--color-db-red)",
  },
};

const severityMapColors: Record<string, string> = {
  Safe: "#34D399",
  Caution: "#FBBF24",
  Concern: "#F87171",
};

function SeverityBadge({ severity }: { severity: string }) {
  const size = 52;
  const stroke = 4;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = 0;
  const color = severityStyles[severity]?.text ?? "var(--color-db-text-muted)";

  const iconSize = 18;

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-db-border-subtle)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center">
        <svg
          width={iconSize}
          height={iconSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke={color}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {severity === "Safe" && <path d="M20 6 9 17l-5-5" />}
          {severity === "Caution" && (
            <>
              <path d="M12 5v9" />
              <path d="M12 18h.01" />
            </>
          )}
          {severity === "Concern" && (
            <>
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </>
          )}
        </svg>
      </span>
    </div>
  );
}

function NegativePoiCard({
  poi,
  isSelected,
  onHover,
  onLeave,
  onClick,
}: {
  poi: NegativePoi;
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
      <SeverityBadge severity={poi.severity} />

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-[15px] font-semibold leading-snug text-[var(--color-db-text-primary)]">
              {poi.name}
            </h4>
            <p className="text-[13px] text-[var(--color-db-text-muted)]">
              {poi.type} · {poi.severity}
            </p>
          </div>
        </div>
        <div className="mt-1 text-[12px] text-[var(--color-db-text-tertiary)]">{poi.detail}</div>
        <div className="mt-2 flex flex-wrap gap-4 text-[13px] text-[var(--color-db-text-tertiary)]">
          <span className="inline-flex items-center gap-1">
            <MapPinIcon size={14} /> {poi.distance_miles} mi
          </span>
        </div>
      </div>
    </div>
  );
}

const SEVERITY_ORDER: Record<string, number> = { Concern: 0, Caution: 1, Safe: 2 };

type NoiseSourceLayer = "aviation" | "road" | "rail";

const NOISE_SOURCE_OPTIONS: { value: NoiseSourceLayer; label: string }[] = [
  { value: "aviation", label: "Airport" },
  { value: "road", label: "Road" },
  { value: "rail", label: "Railroad" },
];

const ALL_SOURCES = new Set<NoiseSourceLayer>(NOISE_SOURCE_OPTIONS.map((o) => o.value));

type InfraLayer = "airport" | "road" | "railroad";

const INFRA_OPTIONS: { value: InfraLayer; label: string }[] = [
  { value: "road", label: "Roads" },
  { value: "railroad", label: "Rail" },
  { value: "airport", label: "Airports" },
];

const ALL_INFRA = new Set<InfraLayer>(INFRA_OPTIONS.map((o) => o.value));

const SOURCE_TYPE_LABELS: Record<string, string> = {
  aviation: "Airport",
  road: "Road",
  rail: "Railroad",
};

// Noise fill-color as a step expression on noise_min_db (numeric).
// Uses the same palette as noiseColors.ts but for MapLibre vector tile rendering.
const NOISE_FILL_COLOR: maplibregl.ExpressionSpecification = [
  "step",
  ["get", "noise_min_db"],
  "#a3e635", // < 45 dB
  45,
  "#a3e635", // 45-49
  50,
  "#facc15", // 50-54
  55,
  "#fb923c", // 55-59
  60,
  "#f97316", // 60-69
  70,
  "#ef4444", // 70-79
  80,
  "#dc2626", // 80-89
  90,
  "#991b1b", // 90+
];

const NOISE_OUTLINE_COLOR: maplibregl.ExpressionSpecification = [
  "step",
  ["get", "noise_min_db"],
  "#84cc16",
  50,
  "#eab308",
  55,
  "#f97316",
  60,
  "#ea580c",
  70,
  "#dc2626",
  80,
  "#b91c1c",
  90,
  "#7f1d1d",
];

// SVG airplane icon encoded as data URL for MapLibre image source
const AIRPLANE_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="%237C3AED" stroke="white" stroke-width="0.5"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg>`;

/** Loads the airplane icon image into the MapLibre map instance */
function AirplaneIconLoader() {
  const { current: map } = useMap();

  useEffect(() => {
    if (!map) return;
    const gl = map.getMap();

    function loadIcon() {
      if (gl.hasImage("airplane-icon")) return;
      const img = new Image(32, 32);
      img.onload = () => {
        if (!gl.hasImage("airplane-icon")) {
          gl.addImage("airplane-icon", img, { sdf: false });
        }
      };
      img.src = `data:image/svg+xml;charset=utf-8,${AIRPLANE_ICON_SVG}`;
    }

    loadIcon();
    // Reload icon after style changes (style switch wipes images)
    gl.on("styledata", loadIcon);
    return () => {
      gl.off("styledata", loadIcon);
    };
  }, [map]);

  return null;
}

function NuisancesTab({ data }: NuisancesTabProps) {
  const { property } = data;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [airportPopup, setAirportPopup] = useState<{
    lon: number;
    lat: number;
    name: string;
  } | null>(null);

  const { sources: apiSources, loading: sourcesLoading } = useNuisanceSources(
    property.lat,
    property.lon,
  );

  const [activeSources, setActiveSources] = useState<Set<NoiseSourceLayer>>(ALL_SOURCES);

  const toggleSource = useCallback((source: NoiseSourceLayer) => {
    setActiveSources((prev) => {
      const next = new Set(prev);
      if (next.has(source)) {
        next.delete(source);
      } else {
        next.add(source);
      }
      return next;
    });
  }, []);

  const [activeInfra, setActiveInfra] = useState<Set<InfraLayer>>(ALL_INFRA);

  const toggleInfra = useCallback((layer: InfraLayer) => {
    setActiveInfra((prev) => {
      const next = new Set(prev);
      if (next.has(layer)) {
        next.delete(layer);
      } else {
        next.add(layer);
      }
      return next;
    });
  }, []);

  // Map API nuisance sources to NegativePoi shape for cards
  const cardPois: NegativePoi[] = useMemo(() => {
    return apiSources.map((s) => ({
      id: s.id,
      name: s.name,
      type: SOURCE_TYPE_LABELS[s.source_type] ?? s.source_type,
      severity: s.severity as "Caution" | "Concern",
      distance_miles: s.distance_miles,
      lat: s.lat ?? property.lat,
      lon: s.lon ?? property.lon,
      detail: s.detail,
    }));
  }, [apiSources, property.lat, property.lon]);

  const sorted = [...cardPois].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );

  const markers = cardPois
    .filter((n) => n.lat !== property.lat || n.lon !== property.lon)
    .map((n) => ({
      id: n.id,
      lat: n.lat,
      lon: n.lon,
      label: `${n.name} (${n.severity})`,
      color: severityMapColors[n.severity],
    }));

  const noiseLegend = getNoiseLegendConfig();

  // Build MapLibre filter for noise source layers
  const noiseSourceFilter = useMemo((): maplibregl.FilterSpecification | undefined => {
    if (activeSources.size === ALL_SOURCES.size) return undefined;
    if (activeSources.size === 0) return ["==", "source_layer", "__none__"];
    return ["in", "source_layer", ...Array.from(activeSources)];
  }, [activeSources]);

  // Build MapLibre filter for infra types
  const infraTypeFilter = useMemo((): maplibregl.FilterSpecification => {
    const types: string[] = [];
    if (activeInfra.has("road")) types.push("road");
    if (activeInfra.has("railroad")) types.push("railroad");
    if (activeInfra.has("airport")) types.push("airport");
    return types.length > 0
      ? (["in", "infra_type", ...types] as unknown as maplibregl.FilterSpecification)
      : (["==", "infra_type", "__none__"] as unknown as maplibregl.FilterSpecification);
  }, [activeInfra]);

  // Airport symbol filter
  const airportFilter = useMemo((): maplibregl.FilterSpecification => {
    return [
      "all",
      ["==", "infra_type", "airport"],
      ...(activeInfra.has("airport")
        ? []
        : [["==", "infra_type", "__none__"] as unknown as maplibregl.FilterSpecification]),
    ] as unknown as maplibregl.FilterSpecification;
  }, [activeInfra]);

  // Handle click on airport icon
  const handleLayerClick = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature) return;
    if (feature.layer.id === "infra-airports" && feature.geometry.type === "Point") {
      const [lon, lat] = feature.geometry.coordinates;
      setAirportPopup({
        lon,
        lat,
        name: (feature.properties?.name as string) || "Airport",
      });
    }
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — nuisance details */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Nuisances
            {sourcesLoading && (
              <span className="ml-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent align-middle" />
            )}
          </h3>
          {!sourcesLoading && sorted.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <svg
                width={32}
                height={32}
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-db-green)"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
              <p className="text-sm font-medium text-[var(--color-db-text-primary)]">
                No nuisances found
              </p>
              <p className="text-xs text-[var(--color-db-text-tertiary)]">
                No significant noise or infrastructure concerns were detected near this property.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {sorted.map((n) => (
                <NegativePoiCard
                  key={n.id}
                  poi={n}
                  isSelected={selectedId === n.id}
                  onHover={() => setHoveredId(n.id)}
                  onLeave={() => setHoveredId(null)}
                  onClick={() => setSelectedId(selectedId === n.id ? null : n.id)}
                />
              ))}
            </div>
          )}
        </DashboardCard>
      </div>

      {/* Right column — map with noise polygons via vector tiles */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Nuisance Map
              {sourcesLoading && (
                <span className="ml-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent align-middle" />
              )}
            </h3>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-medium uppercase tracking-wide text-[var(--color-db-text-tertiary)]">
                  Noise
                </span>
                <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
                  {NOISE_SOURCE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleSource(opt.value)}
                      className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                        activeSources.has(opt.value)
                          ? "bg-[var(--color-db-accent)] text-white"
                          : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-medium uppercase tracking-wide text-[var(--color-db-text-tertiary)]">
                  Locations
                </span>
                <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
                  {INFRA_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleInfra(opt.value)}
                      className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                        activeInfra.has(opt.value)
                          ? "bg-[var(--color-db-text-secondary)] text-white"
                          : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="relative flex-1">
            <DashboardMap
              center={[property.lat, property.lon]}
              zoom={12}
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
              interactiveLayerIds={["infra-airports"]}
              onLayerClick={handleLayerClick}
            >
              <AirplaneIconLoader />

              {/* Noise polygon vector tiles */}
              <Source
                id="noises-tiles"
                type="vector"
                tiles={[`${window.location.origin}/tiles/noises/{z}/{x}/{y}`]}
                minzoom={0}
                maxzoom={14}
              >
                <Layer
                  id="noises-fill"
                  type="fill"
                  source-layer="noises"
                  {...(noiseSourceFilter ? { filter: noiseSourceFilter } : {})}
                  paint={{
                    "fill-color": NOISE_FILL_COLOR,
                    "fill-opacity": 0.35,
                  }}
                />
                <Layer
                  id="noises-outline"
                  type="line"
                  source-layer="noises"
                  {...(noiseSourceFilter ? { filter: noiseSourceFilter } : {})}
                  paint={{
                    "line-color": NOISE_OUTLINE_COLOR,
                    "line-width": 1.5,
                    "line-opacity": 0.7,
                  }}
                />
              </Source>

              {/* Infrastructure vector tiles */}
              <Source
                id="infra-tiles"
                type="vector"
                tiles={[`${window.location.origin}/tiles/v_infrastructure/{z}/{x}/{y}`]}
                minzoom={0}
                maxzoom={14}
              >
                {/* Line geometries: roads, railroads, pipelines, etc. */}
                <Layer
                  id="infra-lines"
                  type="line"
                  source-layer="v_infrastructure"
                  filter={infraTypeFilter}
                  paint={{
                    "line-color": [
                      "match",
                      ["get", "infra_type"],
                      "railroad",
                      "#F97316",
                      "road",
                      "#3B82F6",
                      "#94A3B8",
                    ],
                    "line-width": 2,
                    "line-opacity": 0.7,
                  }}
                />
                {/* Airport symbol layer — airplane icons */}
                <Layer
                  id="infra-airports"
                  type="symbol"
                  source-layer="v_infrastructure"
                  filter={airportFilter}
                  layout={{
                    "icon-image": "airplane-icon",
                    "icon-size": 0.7,
                    "icon-allow-overlap": true,
                    "icon-ignore-placement": false,
                  }}
                  paint={{
                    "icon-opacity": 0.9,
                  }}
                />
              </Source>

              {/* Airport name popup */}
              {airportPopup && (
                <Popup
                  longitude={airportPopup.lon}
                  latitude={airportPopup.lat}
                  anchor="bottom"
                  onClose={() => setAirportPopup(null)}
                  closeOnClick={false}
                  offset={16}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-db-sans)",
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--color-db-text-primary)",
                    }}
                  >
                    {airportPopup.name}
                  </span>
                </Popup>
              )}
            </DashboardMap>
            {activeSources.size > 0 && <ChoroplethLegend config={noiseLegend} />}
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default NuisancesTab;
