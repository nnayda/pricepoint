import { useState, useMemo, useCallback } from "react";
import type { DashboardData, CrimeIncident } from "../../../types";
import { usePoliceIncidents } from "../../../hooks/usePoliceIncidents";
import DashboardCard from "../DashboardCard";
import DashboardMap, { type MapMarker } from "../maps/DashboardMap";
import { COLOR_INDIGO } from "../../../utils/chartTokens";

interface Bbox {
  swLat: number;
  swLon: number;
  neLat: number;
  neLon: number;
}

interface PoliceTabProps {
  data: DashboardData;
}

const COLOR_RED = "#F87171";
const COLOR_BLUE = "#5B7FFF";
const COLOR_GRAY = "#94A3B8";

function offenseGroupColor(offenseClass: string | null | undefined): string {
  if (!offenseClass) return COLOR_GRAY;
  if (offenseClass === "Group B" || offenseClass === "Animal Disturbance") return COLOR_BLUE;
  return COLOR_RED;
}

function offenseGroupLabel(offenseClass: string | null | undefined): string {
  if (!offenseClass) return "Unknown";
  if (offenseClass === "Group B") return "Minor";
  if (offenseClass === "Animal Disturbance") return "Animal Disturbance";
  return "Severe";
}

function incidentId(i: CrimeIncident): string {
  return `incident-${i.id}`;
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return dateStr;
  }
}

function IncidentCard({
  incident,
  isSelected,
  onClick,
}: {
  incident: CrimeIncident;
  isSelected: boolean;
  onClick: () => void;
}) {
  const color = offenseGroupColor(incident.offense_class);

  return (
    <div
      className="flex cursor-pointer gap-3 rounded-[var(--radius-db-sm)] border p-3 transition-colors"
      style={{
        backgroundColor: isSelected
          ? "var(--color-db-accent-muted)"
          : "var(--color-db-surface-alt)",
        borderColor: isSelected ? "var(--color-db-accent)" : "var(--color-db-border-subtle)",
      }}
      onClick={onClick}
      data-testid="incident-card"
    >
      <div className="mt-1 shrink-0">
        <div
          className="h-3 w-3 rounded-full"
          style={{ backgroundColor: color }}
          title={offenseGroupLabel(incident.offense_class)}
          data-testid="offense-dot"
        />
      </div>
      <div className="min-w-0 flex-1">
        <h4 className="text-[14px] font-semibold leading-snug text-[var(--color-db-text-primary)]">
          {incident.incident_type}
        </h4>
        {incident.category && (
          <p className="mt-0.5 text-[13px] text-[var(--color-db-text-secondary)]">
            {incident.category}
          </p>
        )}
        {incident.address && (
          <p className="mt-0.5 text-[12px] text-[var(--color-db-text-tertiary)]">
            {incident.address}
          </p>
        )}
        <div className="mt-1 flex items-center gap-3 text-[12px] text-[var(--color-db-text-tertiary)]">
          <span>{formatDate(incident.date)}</span>
          <span className="font-db-mono text-[11px]">{incident.id}</span>
        </div>
      </div>
    </div>
  );
}

function PoliceTab({ data }: PoliceTabProps) {
  const { property } = data;
  const { incidents, loading, error } = usePoliceIncidents(property.lat, property.lon);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mapBounds, setMapBounds] = useState<Bbox | null>(null);

  const visibleCards = useMemo(() => {
    const sorted = [...incidents].sort((a, b) => (b.date > a.date ? 1 : b.date < a.date ? -1 : 0));
    if (!mapBounds) return sorted;
    return sorted.filter(
      (i) =>
        i.lat >= mapBounds.swLat &&
        i.lat <= mapBounds.neLat &&
        i.lon >= mapBounds.swLon &&
        i.lon <= mapBounds.neLon,
    );
  }, [incidents, mapBounds]);

  const mapMarkers = useMemo<MapMarker[]>(
    () =>
      incidents.map((i) => ({
        id: incidentId(i),
        lat: i.lat,
        lon: i.lon,
        label: `${i.category} — ${i.description ?? ""}`,
        color: offenseGroupColor(i.offense_class),
      })),
    [incidents],
  );

  const incidentById = useMemo(() => {
    const map = new Map<string, CrimeIncident>();
    for (const i of incidents) {
      map.set(incidentId(i), i);
    }
    return map;
  }, [incidents]);

  const renderPopup = useCallback(
    (marker: MapMarker) => {
      const inc = marker.id ? incidentById.get(marker.id) : undefined;
      if (!inc) return <span style={{ fontSize: 12 }}>{marker.label}</span>;
      const color = offenseGroupColor(inc.offense_class);
      return (
        <div style={{ fontFamily: "var(--font-db-sans)", minWidth: 180 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: color,
                display: "inline-block",
                flexShrink: 0,
              }}
            />
            <span style={{ fontWeight: 600, fontSize: 13 }}>{inc.incident_type}</span>
          </div>
          {inc.category && (
            <div style={{ fontSize: 12, color: "#9BA3BF", marginBottom: 2 }}>{inc.category}</div>
          )}
          {inc.address && (
            <div style={{ fontSize: 11, color: "#9BA3BF", marginBottom: 2 }}>{inc.address}</div>
          )}
          <div style={{ fontSize: 11, color: "#9BA3BF" }}>
            {formatDate(inc.date)} · {inc.id}
          </div>
        </div>
      );
    },
    [incidentById],
  );

  const handleBoundsChange = useCallback((bbox: Bbox) => setMapBounds(bbox), []);
  const handleMarkerSelect = useCallback((id: string) => setSelectedId(id), []);
  const handleMarkerDeselect = useCallback(() => setSelectedId(null), []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div
            className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent"
            role="status"
          >
            <span className="sr-only">Loading crime incidents...</span>
          </div>
          <p className="text-sm text-[var(--color-db-text-secondary)]">
            Loading crime incidents...
          </p>
        </div>
      </div>
    );
  }

  if (error && incidents.length === 0) {
    return (
      <DashboardCard>
        <p className="py-8 text-center text-sm text-[var(--color-db-text-muted)]">
          Unable to load crime incidents. Please try again later.
        </p>
      </DashboardCard>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — incident cards */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          {incidents.length === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--color-db-text-muted)]">
              No crime incidents found near this property.
            </p>
          ) : (
            <>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
                  Crime Incidents
                </h3>
                <div className="flex items-center gap-3 text-[11px] text-[var(--color-db-text-tertiary)]">
                  <span className="inline-flex items-center gap-1">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: COLOR_RED }}
                    />
                    Severe
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: COLOR_BLUE }}
                    />
                    Minor
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: COLOR_GRAY }}
                    />
                    Unknown
                  </span>
                </div>
              </div>
              <div className="flex max-h-[calc(100vh-280px)] flex-col gap-2 overflow-y-auto">
                {visibleCards.map((i) => {
                  const id = incidentId(i);
                  return (
                    <IncidentCard
                      key={i.id}
                      incident={i}
                      isSelected={selectedId === id}
                      onClick={() => setSelectedId(selectedId === id ? null : id)}
                    />
                  );
                })}
              </div>
            </>
          )}
        </DashboardCard>
      </div>

      {/* Right column — map */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Incidents Map
          </h3>
          <div className="flex-1">
            <DashboardMap
              center={[property.lat, property.lon]}
              zoom={13}
              cluster
              markers={[
                {
                  lat: property.lat,
                  lon: property.lon,
                  label: "Property",
                  color: COLOR_INDIGO,
                  isProperty: true,
                },
                ...mapMarkers,
              ]}
              height="100%"
              minHeight="400px"
              selectedId={selectedId}
              onMoveEnd={handleBoundsChange}
              onMarkerSelect={handleMarkerSelect}
              onMarkerDeselect={handleMarkerDeselect}
              renderPopup={renderPopup}
              radiusCircle={{ radiusMiles: 0.5 }}
            />
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default PoliceTab;
