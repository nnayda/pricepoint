import { useState, useMemo, useCallback } from "react";
import { Source, Layer } from "react-map-gl/maplibre";
import type { DashboardData, NegativePoi, InfrastructureType } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { MapPinIcon } from "../ui/Icons";
import { useRisks } from "../../../hooks/useRisks";

interface RisksTabProps {
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

const INFRA_TYPE_COLORS: Record<string, string> = {
  cell_tower: "#60A5FA",
  transmission_line: "#F59E0B",
  power_plant: "#EF4444",
  nat_gas_pipeline: "#F97316",
  petroleum_pipeline: "#A855F7",
};

const SEVERITY_ORDER: Record<string, number> = { Concern: 0, Caution: 1, Safe: 2 };

const INFRA_TYPE_OPTIONS: { value: InfrastructureType; label: string }[] = [
  { value: "cell_tower", label: "Cell Towers" },
  { value: "transmission_line", label: "Transmission Lines" },
  { value: "power_plant", label: "Power Plants" },
  { value: "nat_gas_pipeline", label: "Gas Pipelines" },
  { value: "petroleum_pipeline", label: "Oil Pipelines" },
];

const ALL_TYPES = new Set<InfrastructureType>(INFRA_TYPE_OPTIONS.map((o) => o.value));

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

function RisksTab({ data }: RisksTabProps) {
  const { property } = data;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<InfrastructureType>>(ALL_TYPES);

  const { data: risksData, loading } = useRisks(property.lat, property.lon, 5);

  const toggleType = useCallback((t: InfrastructureType) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) {
        next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  }, []);

  const filteredFeatures = useMemo(
    () =>
      risksData.features
        .filter((f) => activeTypes.has(f.infrastructure_type))
        .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)),
    [risksData.features, activeTypes],
  );

  const cards: NegativePoi[] = useMemo(
    () =>
      filteredFeatures.map((f) => ({
        id: f.id,
        name: f.name,
        type: f.infrastructure_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        severity: f.severity,
        distance_miles: f.distance_miles,
        lat: f.lat,
        lon: f.lon,
        detail: f.detail,
      })),
    [filteredFeatures],
  );

  const sidebarCards = useMemo(
    () => cards.filter((c) => c.severity === "Caution" || c.severity === "Concern"),
    [cards],
  );

  // All features are point features (line geometry served via tiles)
  const pointFeatures = filteredFeatures;

  const markers = useMemo(
    () =>
      pointFeatures.map((f) => ({
        id: f.id,
        lat: f.lat,
        lon: f.lon,
        label: `${f.name} (${f.severity})`,
        color: INFRA_TYPE_COLORS[f.infrastructure_type] ?? severityMapColors[f.severity],
        infrastructureType: f.infrastructure_type,
      })),
    [pointFeatures],
  );

  // Build infra type filter for vector tile layers
  const infraTypeFilter = useMemo(() => {
    const types = Array.from(activeTypes);
    if (types.length === 0) return ["==", "infra_type", "__none__"];
    return ["in", "infra_type", ...types];
  }, [activeTypes]);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — risk details */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Infrastructure Risks
            {loading && (
              <span className="ml-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent align-middle" />
            )}
          </h3>

          <div className="flex flex-col gap-2">
            {!loading && sidebarCards.length === 0 && (
              <p className="py-6 text-center text-sm text-[var(--color-db-text-muted)]">
                No infrastructure risks in property boundary
              </p>
            )}
            {sidebarCards.map((n) => (
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
        </DashboardCard>
      </div>

      {/* Right column — map with risk boundary polygons via vector tiles */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Risk Map
              {loading && (
                <span className="ml-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent align-middle" />
              )}
            </h3>
            <div className="flex items-center gap-2">
              <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
                {INFRA_TYPE_OPTIONS.map((opt) => (
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
              {/* Risk boundary vector tiles */}
              <Source
                id="risk-boundaries-tiles"
                type="vector"
                tiles={[`${window.location.origin}/tiles/risk_boundaries/{z}/{x}/{y}`]}
                minzoom={0}
                maxzoom={14}
              >
                <Layer
                  id="risk-boundaries-fill"
                  type="fill"
                  source-layer="risk_boundaries"
                  filter={infraTypeFilter as maplibregl.FilterSpecification}
                  paint={{
                    "fill-color": [
                      "match",
                      ["get", "severity"],
                      "critical",
                      "rgba(248,113,113,0.2)",
                      "caution",
                      "rgba(251,191,36,0.15)",
                      "rgba(200,200,200,0.1)",
                    ],
                    "fill-opacity": 0.8,
                  }}
                />
                <Layer
                  id="risk-boundaries-outline"
                  type="line"
                  source-layer="risk_boundaries"
                  filter={infraTypeFilter as maplibregl.FilterSpecification}
                  paint={{
                    "line-color": [
                      "match",
                      ["get", "severity"],
                      "critical",
                      "#EF4444",
                      "caution",
                      "#F59E0B",
                      "#94A3B8",
                    ],
                    "line-width": 2,
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
                      "cell_tower",
                      "#60A5FA",
                      "transmission_line",
                      "#F59E0B",
                      "power_plant",
                      "#EF4444",
                      "nat_gas_pipeline",
                      "#F97316",
                      "petroleum_pipeline",
                      "#A855F7",
                      "#94A3B8",
                    ],
                    "line-width": 3,
                    "line-opacity": 0.85,
                  }}
                />
              </Source>
            </DashboardMap>
            <div
              className="absolute bottom-3 right-3 z-[1000] rounded-lg border p-3"
              style={{
                backgroundColor: "var(--color-db-surface)",
                borderColor: "var(--color-db-border-subtle)",
              }}
            >
              <p className="mb-1.5 text-[11px] font-semibold text-[var(--color-db-text-secondary)]">
                Infrastructure
              </p>
              <div className="flex flex-col gap-1">
                {INFRA_TYPE_OPTIONS.filter((o) => activeTypes.has(o.value)).map((o) => (
                  <div key={o.value} className="flex items-center gap-2">
                    <span
                      className="inline-block h-3 w-3 rounded-sm"
                      style={{ backgroundColor: INFRA_TYPE_COLORS[o.value] }}
                    />
                    <span className="text-[11px] text-[var(--color-db-text-muted)]">{o.label}</span>
                  </div>
                ))}
              </div>
              <p className="mb-1.5 mt-2 text-[11px] font-semibold text-[var(--color-db-text-secondary)]">
                Risk Zones
              </p>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-sm border"
                    style={{
                      backgroundColor: "rgba(248,113,113,0.2)",
                      borderColor: "#EF4444",
                    }}
                  />
                  <span className="text-[11px] text-[var(--color-db-text-muted)]">Critical</span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-sm border"
                    style={{
                      backgroundColor: "rgba(251,191,36,0.15)",
                      borderColor: "#F59E0B",
                    }}
                  />
                  <span className="text-[11px] text-[var(--color-db-text-muted)]">Caution</span>
                </div>
              </div>
            </div>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default RisksTab;
