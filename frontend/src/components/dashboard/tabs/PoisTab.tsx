import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import type { DashboardData, DashboardPoi } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap, { type MapMarker } from "../maps/DashboardMap";
import { MapPinIcon, CarIcon } from "../ui/Icons";
import { COLOR_INDIGO } from "../../../utils/chartTokens";

const SAVED_DEFAULT_COLOR = "#F59E0B";

interface PoisTabProps {
  data: DashboardData;
}

/* ── Saved Place Card ── */
function SavedPlaceCard({
  poi,
  isSelected,
  onHover,
  onLeave,
  onClick,
  cardRef,
}: {
  poi: DashboardPoi;
  isSelected: boolean;
  onHover: () => void;
  onLeave: () => void;
  onClick: () => void;
  cardRef?: React.Ref<HTMLDivElement>;
}) {
  const color = poi.marker_color || SAVED_DEFAULT_COLOR;
  return (
    <div
      ref={cardRef}
      className="flex cursor-pointer gap-3 rounded-[var(--radius-db-sm)] border p-3 transition-colors"
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
      {/* Color swatch or image */}
      <div className="flex shrink-0 items-center justify-center">
        {poi.marker_image_url ? (
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              border: `3px solid ${color}`,
              overflow: "hidden",
              background: "#fff",
            }}
          >
            <img
              src={poi.marker_image_url}
              alt={poi.name}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </div>
        ) : (
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: `${color}20`,
              border: `2px solid ${color}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill={color}>
              <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 16.8l-6.2 4.5 2.4-7.4L2 9.4h7.6z" />
            </svg>
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <h4 className="text-sm font-semibold leading-snug text-[var(--color-db-text-primary)]">
          {poi.name}
        </h4>
        {poi.address && (
          <p className="truncate text-[11px] text-[var(--color-db-text-muted)]">{poi.address}</p>
        )}
        <div className="mt-1 flex flex-wrap gap-3 text-[12px] text-[var(--color-db-text-tertiary)]">
          <span className="inline-flex items-center gap-1">
            <MapPinIcon size={12} /> {poi.distance_miles} mi
          </span>
          <span className="inline-flex items-center gap-1">
            <CarIcon size={12} /> {poi.drive_minutes} min
          </span>
        </div>
      </div>
    </div>
  );
}

function PoisTab({ data }: PoisTabProps) {
  const { pois, property } = data;

  // All POIs are saved POIs now
  const savedPois = useMemo(() => pois.filter((p) => p.isSaved), [pois]);

  // Group saved by user_category (default "Saved")
  const savedGroups = useMemo(() => {
    const groups: Record<string, DashboardPoi[]> = {};
    for (const p of savedPois) {
      const key = p.category || "Saved";
      if (!groups[key]) groups[key] = [];
      groups[key].push(p);
    }
    return groups;
  }, [savedPois]);

  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Scroll selected saved card into view
  useEffect(() => {
    if (selectedId) {
      const el = cardRefs.current.get(selectedId);
      if (el) {
        el.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [selectedId]);

  // Build map markers — saved places as distinct markers
  const savedMarkers = useMemo(
    (): MapMarker[] =>
      savedPois.map((p) => ({
        id: p.id,
        lat: p.lat,
        lon: p.lon,
        label: `${p.name} (${p.distance_miles} mi)`,
        color: p.marker_color || SAVED_DEFAULT_COLOR,
        imageUrl: p.marker_image_url,
      })),
    [savedPois],
  );

  // Lookup map for popup rendering
  const poiById = useMemo(() => {
    const map = new Map<string, DashboardPoi>();
    for (const p of pois) map.set(p.id, p);
    return map;
  }, [pois]);

  const renderPopup = useCallback(
    (marker: MapMarker) => {
      const poi = marker.id ? poiById.get(marker.id) : undefined;
      if (!poi) return <span style={{ fontSize: 12 }}>{marker.label}</span>;
      return (
        <div style={{ fontFamily: "var(--font-db-sans)", minWidth: 180 }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{poi.name}</div>
          {poi.address && (
            <div style={{ fontSize: 11, color: "#9BA3BF", marginBottom: 4 }}>{poi.address}</div>
          )}
          <div style={{ display: "flex", gap: 10, fontSize: 11, color: "#9BA3BF" }}>
            <span>{poi.distance_miles} mi</span>
            <span>{poi.drive_minutes} min drive</span>
          </div>
        </div>
      );
    },
    [poiById],
  );

  const handleMarkerSelect = useCallback((id: string) => {
    setSelectedId(id);
  }, []);

  const handleMarkerDeselect = useCallback(() => {
    setSelectedId(null);
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — saved cards */}
      <div className="flex flex-col gap-4">
        {savedPois.length > 0 ? (
          <DashboardCard>
            <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
              Saved Places
            </h3>
            <div className="flex flex-col gap-3">
              {Object.entries(savedGroups).map(([groupName, groupPois]) => (
                <div key={groupName}>
                  {Object.keys(savedGroups).length > 1 && (
                    <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-[var(--color-db-text-muted)]">
                      {groupName}
                    </p>
                  )}
                  <div className="flex flex-col gap-2">
                    {groupPois.map((poi) => {
                      const isSelected = selectedId === poi.id;
                      return (
                        <SavedPlaceCard
                          key={poi.id}
                          poi={poi}
                          isSelected={isSelected}
                          onHover={() => setHoveredId(poi.id)}
                          onLeave={() => setHoveredId(null)}
                          onClick={() => setSelectedId(isSelected ? null : poi.id)}
                          cardRef={(el) => {
                            if (el) cardRefs.current.set(poi.id, el);
                            else cardRefs.current.delete(poi.id);
                          }}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>
        ) : (
          <DashboardCard>
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-[var(--color-db-text-secondary)]">No saved places yet</p>
              <p className="text-xs text-[var(--color-db-text-muted)]">
                Add places you care about in{" "}
                <Link
                  to="/settings"
                  className="text-[var(--color-db-accent)] underline hover:opacity-80"
                >
                  Settings
                </Link>{" "}
                to see them on the map.
              </p>
            </div>
          </DashboardCard>
        )}
      </div>

      {/* Right column — map (sticky, fills viewport) */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">POI Map</h3>
          </div>
          <div className="flex-1">
            <DashboardMap
              center={[property.lat, property.lon]}
              zoom={13}
              markers={[
                {
                  lat: property.lat,
                  lon: property.lon,
                  label: "Property",
                  color: COLOR_INDIGO,
                  isProperty: true,
                },
                ...savedMarkers,
              ]}
              height="100%"
              minHeight="400px"
              highlightedId={hoveredId}
              selectedId={selectedId}
              onMarkerSelect={handleMarkerSelect}
              onMarkerDeselect={handleMarkerDeselect}
              renderPopup={renderPopup}
            />
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default PoisTab;
