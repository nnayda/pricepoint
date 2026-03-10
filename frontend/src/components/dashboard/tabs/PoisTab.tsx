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

/* ── Chevron icon for collapsible sections ── */
function ChevronIcon({ open, size = 14 }: { open: boolean; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        transition: "transform 150ms ease",
        transform: open ? "rotate(90deg)" : "rotate(0deg)",
        flexShrink: 0,
      }}
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

/* ── Location row (expanded detail for a single location) ── */
function LocationRow({
  poi,
  isSelected,
  onHover,
  onLeave,
  onClick,
  rowRef,
}: {
  poi: DashboardPoi;
  isSelected: boolean;
  onHover: () => void;
  onLeave: () => void;
  onClick: () => void;
  rowRef?: React.Ref<HTMLDivElement>;
}) {
  return (
    <div
      ref={rowRef}
      className="flex cursor-pointer items-center gap-3 rounded-[var(--radius-db-sm)] border px-3 py-2 transition-colors"
      style={{
        backgroundColor: isSelected
          ? "var(--color-db-accent-muted)"
          : "var(--color-db-surface)",
        borderColor: isSelected ? "var(--color-db-accent)" : "var(--color-db-border-subtle)",
      }}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      onClick={onClick}
    >
      <div className="min-w-0 flex-1">
        {poi.address && (
          <p className="truncate text-[12px] text-[var(--color-db-text-secondary)]">
            {poi.address}
          </p>
        )}
        {!poi.address && (
          <p className="truncate text-[12px] text-[var(--color-db-text-secondary)]">{poi.name}</p>
        )}
      </div>
      <div className="flex shrink-0 gap-3 text-[11px] text-[var(--color-db-text-tertiary)]">
        <span className="inline-flex items-center gap-1">
          <MapPinIcon size={11} /> {poi.distance_miles} mi
        </span>
        <span className="inline-flex items-center gap-1">
          <CarIcon size={11} /> {poi.drive_minutes} min
        </span>
      </div>
    </div>
  );
}

/* ── Saved place group: logo + name + nearest, expands to all locations ── */
interface SavedPlaceGroup {
  name: string;
  color: string;
  imageUrl?: string;
  locations: DashboardPoi[];
  nearest: DashboardPoi;
}

function SavedPlaceGroupCard({
  group,
  selectedId,
  onHover,
  onLeave,
  onSelect,
  cardRefs,
}: {
  group: SavedPlaceGroup;
  selectedId: string | null;
  onHover: (id: string) => void;
  onLeave: () => void;
  onSelect: (id: string) => void;
  cardRefs: React.MutableRefObject<Map<string, HTMLDivElement>>;
}) {
  const [open, setOpen] = useState(false);
  const hasMultiple = group.locations.length > 1;

  return (
    <div>
      {/* Header row: logo + name + nearest distance/time */}
      <button
        type="button"
        className="flex w-full cursor-pointer items-center gap-3 rounded-[var(--radius-db-sm)] border p-3 text-left transition-colors"
        style={{
          backgroundColor: open ? "var(--color-db-surface)" : "var(--color-db-surface-alt)",
          borderColor: "var(--color-db-border-subtle)",
        }}
        onClick={() => {
          if (hasMultiple) {
            setOpen((prev) => !prev);
          } else {
            // Single location — toggle map selection
            const id = group.nearest.id;
            onSelect(id);
          }
        }}
        onMouseEnter={() => onHover(group.nearest.id)}
        onMouseLeave={onLeave}
      >
        {/* Logo or color swatch */}
        <div className="flex shrink-0 items-center justify-center">
          {group.imageUrl ? (
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                border: `3px solid ${group.color}`,
                overflow: "hidden",
                background: "#fff",
              }}
            >
              <img
                src={group.imageUrl}
                alt={group.name}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </div>
          ) : (
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: `${group.color}20`,
                border: `2px solid ${group.color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill={group.color}>
                <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 16.8l-6.2 4.5 2.4-7.4L2 9.4h7.6z" />
              </svg>
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold leading-snug text-[var(--color-db-text-primary)]">
            {group.name}
          </h4>
          <div className="mt-0.5 flex flex-wrap gap-3 text-[12px] text-[var(--color-db-text-tertiary)]">
            <span className="inline-flex items-center gap-1">
              <MapPinIcon size={12} /> {group.nearest.distance_miles} mi
            </span>
            <span className="inline-flex items-center gap-1">
              <CarIcon size={12} /> {group.nearest.drive_minutes} min
            </span>
            {hasMultiple && (
              <span className="text-[var(--color-db-text-muted)]">
                {group.locations.length} locations
              </span>
            )}
          </div>
        </div>

        {hasMultiple && (
          <div className="text-[var(--color-db-text-muted)]">
            <ChevronIcon open={open} />
          </div>
        )}
      </button>

      {/* Expanded locations */}
      {open && hasMultiple && (
        <div className="mt-1 flex flex-col gap-1 pl-11">
          {group.locations.map((poi) => (
            <LocationRow
              key={poi.id}
              poi={poi}
              isSelected={selectedId === poi.id}
              onHover={() => onHover(poi.id)}
              onLeave={onLeave}
              onClick={() => onSelect(poi.id)}
              rowRef={(el) => {
                if (el) cardRefs.current.set(poi.id, el);
                else cardRefs.current.delete(poi.id);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Collapsible category section ── */
function CategorySection({
  name,
  groups,
  defaultOpen,
  selectedId,
  onHover,
  onLeave,
  onSelect,
  cardRefs,
}: {
  name: string;
  groups: SavedPlaceGroup[];
  defaultOpen: boolean;
  selectedId: string | null;
  onHover: (id: string) => void;
  onLeave: () => void;
  onSelect: (id: string) => void;
  cardRefs: React.MutableRefObject<Map<string, HTMLDivElement>>;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const totalLocations = groups.reduce((n, g) => n + g.locations.length, 0);

  return (
    <div>
      <button
        type="button"
        className="flex w-full cursor-pointer items-center gap-1.5 py-1 text-left"
        onClick={() => setOpen((prev) => !prev)}
      >
        <ChevronIcon open={open} size={12} />
        <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-db-text-muted)]">
          {name}
        </span>
        <span className="text-[10px] text-[var(--color-db-text-muted)]">
          ({groups.length} {groups.length === 1 ? "place" : "places"}, {totalLocations}{" "}
          {totalLocations === 1 ? "location" : "locations"})
        </span>
      </button>

      {open && (
        <div className="mt-1 flex flex-col gap-2">
          {groups.map((group) => (
            <SavedPlaceGroupCard
              key={group.name}
              group={group}
              selectedId={selectedId}

              onHover={onHover}
              onLeave={onLeave}
              onSelect={onSelect}
              cardRefs={cardRefs}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main PoisTab ── */
function PoisTab({ data }: PoisTabProps) {
  const { pois, property } = data;

  const savedPois = useMemo(() => pois.filter((p) => p.isSaved), [pois]);

  // Build hierarchical structure: category → saved place → locations
  const { categories, allGroups } = useMemo(() => {
    // Group by saved_place_name first
    const placeMap = new Map<
      string,
      { pois: DashboardPoi[]; color: string; imageUrl?: string; category: string }
    >();
    for (const p of savedPois) {
      const placeName = p.saved_place_name || p.name;
      const existing = placeMap.get(placeName);
      if (existing) {
        existing.pois.push(p);
      } else {
        placeMap.set(placeName, {
          pois: [p],
          color: p.marker_color || SAVED_DEFAULT_COLOR,
          imageUrl: p.marker_image_url,
          category: p.category || "Saved",
        });
      }
    }

    // Build SavedPlaceGroup objects
    const groupsList: (SavedPlaceGroup & { category: string })[] = [];
    for (const [name, info] of placeMap) {
      const sorted = [...info.pois].sort((a, b) => a.distance_miles - b.distance_miles);
      groupsList.push({
        name,
        color: info.color,
        imageUrl: info.imageUrl,
        locations: sorted,
        nearest: sorted[0],
        category: info.category,
      });
    }

    // Group by category
    const catMap = new Map<string, SavedPlaceGroup[]>();
    for (const g of groupsList) {
      const arr = catMap.get(g.category);
      if (arr) arr.push(g);
      else catMap.set(g.category, [g]);
    }

    // Sort groups within each category by nearest distance
    for (const arr of catMap.values()) {
      arr.sort((a, b) => a.nearest.distance_miles - b.nearest.distance_miles);
    }

    return {
      categories: catMap,
      allGroups: groupsList,
    };
  }, [savedPois]);

  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Scroll selected card into view
  useEffect(() => {
    if (selectedId) {
      const el = cardRefs.current.get(selectedId);
      if (el) {
        el.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [selectedId]);

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedId((prev) => (prev === id ? null : id));
    },
    [],
  );

  // Build map markers
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

  const hasSingleCategory = categories.size <= 1;

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — saved cards */}
      <div className="flex flex-col gap-4">
        {savedPois.length > 0 ? (
          <DashboardCard>
            <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
              Saved Places
            </h3>

            {hasSingleCategory ? (
              /* No category headers needed — just list place groups */
              <div className="flex flex-col gap-2">
                {(allGroups as SavedPlaceGroup[])
                  .sort((a, b) => a.nearest.distance_miles - b.nearest.distance_miles)
                  .map((group) => (
                    <SavedPlaceGroupCard
                      key={group.name}
                      group={group}
                      selectedId={selectedId}
        
                      onHover={setHoveredId}
                      onLeave={() => setHoveredId(null)}
                      onSelect={handleSelect}
                      cardRefs={cardRefs}
                    />
                  ))}
              </div>
            ) : (
              /* Multiple categories — collapsible sections */
              <div className="flex flex-col gap-3">
                {[...categories.entries()].map(([catName, groups]) => (
                  <CategorySection
                    key={catName}
                    name={catName}
                    groups={groups}
                    defaultOpen={true}
                    selectedId={selectedId}
      
                    onHover={setHoveredId}
                    onLeave={() => setHoveredId(null)}
                    onSelect={handleSelect}
                    cardRefs={cardRefs}
                  />
                ))}
              </div>
            )}
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
