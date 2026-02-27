import { useState, useCallback, useMemo } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { DashboardData, NegativePoi } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import ChoroplethLegend from "../maps/ChoroplethLegend";
import { MapPinIcon } from "../ui/Icons";
import { useNuisanceSources } from "../../../hooks/useNuisanceSources";
import { getNoiseLegendConfig } from "../../../utils/noiseColors";

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

// Noise band color mapping for vector tile fill-color expression
const NOISE_BAND_COLORS: [string, string][] = [
  ["65-70", "rgba(255, 255, 0, 0.35)"],
  ["70-75", "rgba(255, 200, 0, 0.35)"],
  ["75-80", "rgba(255, 140, 0, 0.35)"],
  ["80-85", "rgba(255, 80, 0, 0.35)"],
  ["85+", "rgba(255, 0, 0, 0.35)"],
];

function NuisancesTab({ data }: NuisancesTabProps) {
  const { property } = data;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

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
  const noiseSourceFilter = useMemo(() => {
    if (activeSources.size === ALL_SOURCES.size) return undefined;
    return ["in", "source_layer", ...Array.from(activeSources)];
  }, [activeSources]);

  // Build MapLibre filter for infra types
  const infraTypeFilter = useMemo(() => {
    const types: string[] = [];
    if (activeInfra.has("road")) types.push("railroad"); // roads come from roads table
    if (activeInfra.has("railroad")) types.push("railroad");
    if (activeInfra.has("airport")) types.push("airport");
    return types.length > 0 ? ["in", "infra_type", ...types] : ["==", "infra_type", "__none__"];
  }, [activeInfra]);

  // Noise fill-color expression
  const noiseFillColor = [
    "match",
    ["get", "noise_band"],
    ...NOISE_BAND_COLORS.flatMap(([band, color]) => [band, color]),
    "rgba(200, 200, 200, 0.2)",
  ] as unknown as maplibregl.ExpressionSpecification;

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
            >
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
                  filter={noiseSourceFilter as maplibregl.FilterSpecification | undefined}
                  paint={{
                    "fill-color": noiseFillColor,
                    "fill-opacity": 0.6,
                  }}
                />
                <Layer
                  id="noises-outline"
                  type="line"
                  source-layer="noises"
                  filter={noiseSourceFilter as maplibregl.FilterSpecification | undefined}
                  paint={{
                    "line-color": noiseFillColor,
                    "line-width": 1,
                    "line-opacity": 0.8,
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
                <Layer
                  id="infra-lines"
                  type="line"
                  source-layer="v_infrastructure"
                  filter={infraTypeFilter as maplibregl.FilterSpecification}
                  paint={{
                    "line-color": [
                      "match",
                      ["get", "infra_type"],
                      "railroad",
                      "#F97316",
                      "airport",
                      "#7C3AED",
                      "#3B82F6",
                    ],
                    "line-width": 2,
                    "line-opacity": 0.7,
                  }}
                />
                <Layer
                  id="infra-points"
                  type="circle"
                  source-layer="v_infrastructure"
                  filter={
                    [
                      "all",
                      infraTypeFilter as maplibregl.FilterSpecification,
                      ["==", ["geometry-type"], "Point"],
                    ] as unknown as maplibregl.FilterSpecification
                  }
                  paint={{
                    "circle-radius": 5,
                    "circle-color": [
                      "match",
                      ["get", "infra_type"],
                      "airport",
                      "#7C3AED",
                      "#94A3B8",
                    ],
                    "circle-stroke-width": 1,
                    "circle-stroke-color": "#ffffff",
                  }}
                />
              </Source>
            </DashboardMap>
            {activeSources.size > 0 && <ChoroplethLegend config={noiseLegend} />}
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default NuisancesTab;
