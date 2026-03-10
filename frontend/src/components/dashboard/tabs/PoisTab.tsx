import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Source, Layer, Popup } from "react-map-gl/maplibre";
import type { MapLayerMouseEvent } from "react-map-gl/maplibre";
import type { DashboardData, DashboardPoi } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap, { type MapMarker } from "../maps/DashboardMap";
import { POI_ICONS, ShoppingCartIcon, MapPinIcon, CarIcon } from "../ui/Icons";
import { CATEGORY_COLORS, COLOR_INDIGO } from "../../../utils/chartTokens";

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

  // Separate saved vs regular POIs
  const savedPois = useMemo(() => pois.filter((p) => p.isSaved), [pois]);
  const regularPois = useMemo(() => pois.filter((p) => !p.isSaved), [pois]);

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

  // Group regular POIs by category
  const categories = useMemo(
    () => [...new Set(regularPois.map((p) => p.category))],
    [regularPois],
  );
  const grouped = useMemo(
    () =>
      categories.reduce(
        (acc, cat) => {
          acc[cat] = regularPois.filter((p) => p.category === cat);
          return acc;
        },
        {} as Record<string, DashboardPoi[]>,
      ),
    [categories, regularPois],
  );

  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set(categories));
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [vtPopup, setVtPopup] = useState<{ lat: number; lon: number; name: string } | null>(null);

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

  const toggleCat = (cat: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  };

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

  const regularMarkers = useMemo(
    (): MapMarker[] =>
      regularPois.map((p) => ({
        id: p.id,
        lat: p.lat,
        lon: p.lon,
        label: `${p.name} (${p.distance_miles} mi)`,
        color: CATEGORY_COLORS[p.category] || COLOR_INDIGO,
      })),
    [regularPois],
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

  // Handle vector tile layer clicks for places-circles
  const handleLayerClick = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature || feature.layer.id !== "places-circles") return;
    if (feature.geometry.type !== "Point") return;
    const [lon, lat] = feature.geometry.coordinates;
    const name = (feature.properties?.name as string) || "Unknown Place";
    setVtPopup({ lat, lon, name });
  }, []);

  const handleMarkerSelect = useCallback((id: string) => {
    setSelectedId(id);
    setVtPopup(null);
  }, []);

  const handleMarkerDeselect = useCallback(() => {
    setSelectedId(null);
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — saved cards + accordion */}
      <div className="flex flex-col gap-4">
        {/* Saved Places Cards */}
        {savedPois.length > 0 && (
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
        )}

        {/* General POI Accordion */}
        {categories.map((cat) => {
          const IconComponent = POI_ICONS[cat] || ShoppingCartIcon;
          return (
            <DashboardCard key={cat} padding={false}>
              <button
                type="button"
                onClick={() => toggleCat(cat)}
                className="flex w-full items-center justify-between px-5 py-3.5 text-left"
              >
                <div className="flex items-center gap-3">
                  <span
                    className="flex h-6 w-6 items-center justify-center rounded-full"
                    style={{
                      backgroundColor: `${CATEGORY_COLORS[cat]}20`,
                      color: CATEGORY_COLORS[cat],
                    }}
                  >
                    <IconComponent size={14} />
                  </span>
                  <span className="text-sm font-semibold text-[var(--color-db-text-primary)]">
                    {cat}
                  </span>
                  <span className="text-xs text-[var(--color-db-text-muted)]">
                    ({grouped[cat].length})
                  </span>
                </div>
                <svg
                  className={`h-4 w-4 text-[var(--color-db-text-tertiary)] transition-transform ${expandedCats.has(cat) ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {expandedCats.has(cat) && (
                <div className="border-t border-[var(--color-db-border-subtle)] px-5 py-3">
                  <div className="space-y-2">
                    {grouped[cat].map((poi) => {
                      const PoiIcon = POI_ICONS[poi.category] || ShoppingCartIcon;
                      const isSelected = selectedId === poi.id;
                      return (
                        <div
                          key={poi.id}
                          className="flex cursor-pointer items-center justify-between rounded-[var(--radius-db-xs)] px-3 py-2 transition-colors"
                          style={{
                            backgroundColor: isSelected
                              ? "var(--color-db-accent-muted)"
                              : "var(--color-db-surface-hover)",
                            outline: isSelected ? "1px solid var(--color-db-accent)" : "none",
                          }}
                          onMouseEnter={() => setHoveredId(poi.id)}
                          onMouseLeave={() => setHoveredId(null)}
                          onClick={() => setSelectedId(isSelected ? null : poi.id)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-[var(--color-db-text-muted)]">
                              <PoiIcon size={14} />
                            </span>
                            <div>
                              <span className="text-sm text-[var(--color-db-text-primary)]">
                                {poi.name}
                              </span>
                              <span className="ml-2 text-[11px] text-[var(--color-db-text-muted)]">
                                {poi.subcategory}
                              </span>
                            </div>
                          </div>
                          <div className="flex gap-3 text-[11px] text-[var(--color-db-text-tertiary)]">
                            <span>{poi.distance_miles} mi</span>
                            <span>{poi.drive_minutes} min</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </DashboardCard>
          );
        })}
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
                ...regularMarkers,
              ]}
              height="100%"
              minHeight="400px"
              highlightedId={hoveredId}
              selectedId={selectedId}
              interactiveLayerIds={["places-circles"]}
              onLayerClick={handleLayerClick}
              onMarkerSelect={handleMarkerSelect}
              onMarkerDeselect={handleMarkerDeselect}
              renderPopup={renderPopup}
            >
              {/* Vector tile layers for places and hospitals */}
              <Source
                id="places-tiles"
                type="vector"
                tiles={[`${window.location.origin}/tiles/places/{z}/{x}/{y}`]}
                minzoom={0}
                maxzoom={14}
              >
                <Layer
                  id="places-circles"
                  type="circle"
                  source-layer="places"
                  paint={{
                    "circle-radius": 4,
                    "circle-color": COLOR_INDIGO,
                    "circle-opacity": 0.3,
                    "circle-stroke-width": 1,
                    "circle-stroke-color": COLOR_INDIGO,
                    "circle-stroke-opacity": 0.5,
                  }}
                />
              </Source>
              <Source
                id="hospitals-tiles"
                type="vector"
                tiles={[`${window.location.origin}/tiles/hospitals/{z}/{x}/{y}`]}
                minzoom={0}
                maxzoom={14}
              >
                <Layer
                  id="hospitals-circles"
                  type="circle"
                  source-layer="hospitals"
                  paint={{
                    "circle-radius": 6,
                    "circle-color": "#EF4444",
                    "circle-opacity": 0.6,
                    "circle-stroke-width": 2,
                    "circle-stroke-color": "#ffffff",
                  }}
                />
              </Source>

              {/* Vector tile popup */}
              {vtPopup && (
                <Popup
                  longitude={vtPopup.lon}
                  latitude={vtPopup.lat}
                  anchor="bottom"
                  onClose={() => setVtPopup(null)}
                  closeOnClick={false}
                  maxWidth="240px"
                >
                  <span
                    style={{
                      fontFamily: "var(--font-db-sans)",
                      fontSize: 12,
                      color: "var(--color-db-text-primary)",
                    }}
                  >
                    {vtPopup.name}
                  </span>
                </Popup>
              )}
            </DashboardMap>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default PoisTab;
