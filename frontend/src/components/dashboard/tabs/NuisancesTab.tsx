import { useState, useCallback } from "react";
import { GeoJSON } from "react-leaflet";
import type { DashboardData, NegativePoi } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import ChoroplethLegend from "../maps/ChoroplethLegend";
import { MapPinIcon } from "../ui/Icons";
import { useNuisances } from "../../../hooks/useNuisances";
import { getNoiseLegendConfig, getNoisePolygonStyle } from "../../../utils/noiseColors";

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

function NuisancesTab({ data }: NuisancesTabProps) {
  const { nuisances, property } = data;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: noiseData, loading: noiseLoading } = useNuisances(property.lat, property.lon);

  const sorted = [...nuisances].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );

  const markers = nuisances.map((n) => ({
    id: n.id,
    lat: n.lat,
    lon: n.lon,
    label: `${n.name} (${n.severity})`,
    color: severityMapColors[n.severity],
  }));

  const onEachFeature = useCallback((feature: GeoJSON.Feature, layer: L.Layer) => {
    const props = feature.properties;
    if (props) {
      layer.bindTooltip(`<strong>${props.noise_band}</strong><br/>Source: ${props.source_layer}`, {
        sticky: true,
      });
    }
    layer.on({
      mouseover: (e: L.LeafletMouseEvent) => {
        const target = e.target as L.Path;
        target.setStyle({ fillOpacity: 0.6, weight: 2 });
      },
      mouseout: (e: L.LeafletMouseEvent) => {
        const target = e.target as L.Path;
        target.setStyle({ fillOpacity: 0.35, weight: 1 });
      },
    });
  }, []);

  const noiseLegend = getNoiseLegendConfig();

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — nuisance details */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Nuisances
          </h3>
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
        </DashboardCard>
      </div>

      {/* Right column — map with noise polygons */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Nuisance Map
            {noiseLoading && (
              <span className="ml-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent align-middle" />
            )}
          </h3>
          <div className="relative flex-1">
            <DashboardMap
              center={[property.lat, property.lon]}
              zoom={13}
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
              {noiseData.features.length > 0 && (
                <GeoJSON
                  key={`noise-${noiseData.features.length}`}
                  data={noiseData}
                  style={getNoisePolygonStyle}
                  onEachFeature={onEachFeature}
                />
              )}
            </DashboardMap>
            {noiseData.features.length > 0 && <ChoroplethLegend config={noiseLegend} />}
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default NuisancesTab;
