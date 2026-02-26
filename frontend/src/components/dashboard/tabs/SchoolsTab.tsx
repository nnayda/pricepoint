import { useState, useMemo, useCallback, useEffect } from "react";
import { GeoJSON, useMapEvents } from "react-leaflet";
import type { DashboardData, DashboardSchool, SchoolNearby, SchoolDistrictInfo } from "../../../types";
import { useSchoolsNearby } from "../../../hooks/useSchoolsNearby";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { MapPinIcon, CarIcon, WalkIcon, UsersIcon } from "../ui/Icons";
import { getSchoolMarkerColor, COLOR_INDIGO } from "../../../utils/chartTokens";
import type { Layer, PathOptions } from "leaflet";

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

interface SchoolsTabProps {
  data: DashboardData;
}

function mapSchool(s: SchoolNearby): DashboardSchool {
  return {
    name: s.name,
    address: s.address ?? "",
    school_type: (s.school_level ?? s.school_type ?? "Elementary") as
      | "Elementary"
      | "Middle"
      | "High"
      | "K-8"
      | "Charter",
    rating: s.rating != null && s.rating > 0 ? s.rating : null,
    grades: s.grades ?? "",
    distance_miles: s.distance_miles,
    drive_minutes: s.drive_minutes,
    walk_minutes: s.walk_minutes,
    student_teacher_ratio: s.student_teacher_ratio ?? 0,
    enrollment: s.enrollment,
    test_scores: 0,
    assigned: s.assigned ?? false,
    lat: s.lat ?? 0,
    lon: s.lon ?? 0,
    pct_frl_eligible: s.pct_frl_eligible,
    in_district: s.in_district ?? false,
  };
}

function ratingColor(rating: number | null): string {
  if (rating == null || rating === 0) return "#94A3B8";
  if (rating >= 8) return "var(--color-db-green)";
  if (rating >= 6) return "var(--color-db-yellow)";
  return "var(--color-db-red)";
}

function RatingGauge({ rating }: { rating: number | null }) {
  const size = 52;
  const stroke = 4;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  if (rating == null || rating === 0) {
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
        </svg>
        <span
          className="absolute inset-0 flex items-center justify-center font-db-mono text-base font-bold"
          style={{ color: "#94A3B8" }}
        >
          ?
        </span>
      </div>
    );
  }

  const pct = rating / 10;
  const dashOffset = circumference * (1 - pct);
  const color = ratingColor(rating);

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
      <span
        className="absolute inset-0 flex items-center justify-center font-db-mono text-base font-bold"
        style={{ color }}
      >
        {rating}
      </span>
    </div>
  );
}

function SchoolCard({
  school,
  isSelected,
  onHover,
  onLeave,
  onClick,
}: {
  school: DashboardSchool;
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
      <RatingGauge rating={school.rating} />

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-[15px] font-semibold leading-snug text-[var(--color-db-text-primary)]">
              {school.name}
            </h4>
            <p className="text-[13px] text-[var(--color-db-text-muted)]">
              {school.school_type} · {school.grades}
            </p>
          </div>
          {school.assigned && (
            <span className="rounded-full bg-[var(--color-db-accent-muted)] px-2 py-0.5 text-[11px] font-semibold text-[var(--color-db-accent)]">
              Assigned
            </span>
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-[13px] text-[var(--color-db-text-tertiary)]">
          <span className="inline-flex items-center gap-1">
            <MapPinIcon size={14} /> {school.distance_miles} mi
          </span>
          {school.drive_minutes > 0 && (
            <span className="inline-flex items-center gap-1">
              <CarIcon size={14} /> {school.drive_minutes} min
            </span>
          )}
          {school.walk_minutes != null && school.walk_minutes > 0 && (
            <span className="inline-flex items-center gap-1">
              <WalkIcon size={14} /> {school.walk_minutes} min
            </span>
          )}
        </div>
        {/* Extra stats row */}
        <div className="mt-1 flex flex-wrap gap-4 text-[12px] text-[var(--color-db-text-tertiary)]">
          {school.student_teacher_ratio > 0 && (
            <span className="inline-flex items-center gap-1">
              <UsersIcon size={13} /> 1:{Math.round(school.student_teacher_ratio)}
            </span>
          )}
          {school.enrollment != null && school.enrollment > 0 && (
            <span>{school.enrollment.toLocaleString()} students</span>
          )}
          {school.pct_frl_eligible != null && school.pct_frl_eligible > 0 && (
            <span>{Math.round(school.pct_frl_eligible)}% FRL</span>
          )}
        </div>
      </div>
    </div>
  );
}

function schoolId(s: DashboardSchool) {
  return `school-${s.lat}-${s.lon}`;
}

/* ── District boundary styles ── */

const HOME_DISTRICT_STYLE: PathOptions = {
  color: "#6366F1",
  weight: 3,
  fillColor: "#6366F1",
  fillOpacity: 0.08,
};

const NEIGHBOR_DISTRICT_STYLE: PathOptions = {
  color: "#94A3B8",
  weight: 1.5,
  dashArray: "6 4",
  fillColor: "#94A3B8",
  fillOpacity: 0.03,
};

function districtTypeLabel(districtType: string | null): string {
  if (!districtType) return "";
  if (districtType === "elementary") return "Elementary";
  if (districtType === "secondary") return "Secondary";
  if (districtType === "unified") return "Unified";
  return districtType;
}

/** Renders a single district boundary with an optional permanent label. */
function DistrictBoundary({ district }: { district: SchoolDistrictInfo }) {
  const isHome = district.is_home;
  const typeTag = districtTypeLabel(district.district_type);
  const label = typeTag ? `${district.name} (${typeTag})` : district.name;

  const onEachFeature = useCallback(
    (_feature: GeoJSON.Feature, layer: Layer) => {
      if (!isHome) {
        layer.bindTooltip(label, {
          permanent: true,
          direction: "center",
          className: "district-label",
        });
      }
    },
    [label, isHome],
  );

  if (!district.geojson) return null;

  return (
    <GeoJSON
      key={district.geoid}
      data={district.geojson}
      style={isHome ? HOME_DISTRICT_STYLE : NEIGHBOR_DISTRICT_STYLE}
      onEachFeature={onEachFeature}
    />
  );
}

function SchoolsTab({ data }: SchoolsTabProps) {
  const { property } = data;
  const {
    schools: apiSchools,
    schoolDistricts,
    loading,
    error,
  } = useSchoolsNearby(property.lat, property.lon);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mapBounds, setMapBounds] = useState<Bbox | null>(null);

  type SchoolLevel = "Elementary" | "Middle" | "High";
  const LEVEL_OPTIONS: { value: SchoolLevel; label: string }[] = [
    { value: "Elementary", label: "Elementary" },
    { value: "Middle", label: "Middle" },
    { value: "High", label: "High" },
  ];
  const ALL_LEVELS = new Set<SchoolLevel>(LEVEL_OPTIONS.map((o) => o.value));
  const [activeLevels, setActiveLevels] = useState<Set<SchoolLevel>>(ALL_LEVELS);

  const toggleLevel = useCallback((level: SchoolLevel) => {
    setActiveLevels((prev) => {
      const next = new Set(prev);
      if (next.has(level)) {
        next.delete(level);
      } else {
        next.add(level);
      }
      return next;
    });
  }, []);

  const matchesLevel = useCallback(
    (schoolType: string) => {
      if (activeLevels.size === ALL_LEVELS.size) return true;
      const t = schoolType.toLowerCase();
      if (t === "k-8") return activeLevels.has("Elementary") || activeLevels.has("Middle");
      if (t === "charter") return true; // always include charters
      if (t.includes("elementary")) return activeLevels.has("Elementary");
      if (t.includes("middle")) return activeLevels.has("Middle");
      if (t.includes("high")) return activeLevels.has("High");
      return true;
    },
    [activeLevels, ALL_LEVELS.size],
  );

  const homeDistrict = useMemo(
    () => schoolDistricts.find((d) => d.is_home) ?? null,
    [schoolDistricts],
  );

  // Filter districts by active school level toggles
  const filteredDistricts = useMemo(() => {
    if (activeLevels.size === ALL_LEVELS.size) return schoolDistricts;
    return schoolDistricts.filter((d) => {
      // Always show unified districts (they cover all levels)
      if (d.district_type === "unified") return true;
      // Show elementary districts when Elementary is active
      if (d.district_type === "elementary") return activeLevels.has("Elementary");
      // Show secondary districts when Middle or High is active
      if (d.district_type === "secondary")
        return activeLevels.has("Middle") || activeLevels.has("High");
      // Unknown type — always show
      return true;
    });
  }, [schoolDistricts, activeLevels, ALL_LEVELS.size]);

  // Use API schools if available, fall back to bundled data
  const allSchools = useMemo(() => {
    if (apiSchools.length > 0) {
      return apiSchools.map(mapSchool);
    }
    return data.schools;
  }, [apiSchools, data.schools]);

  // Filter to in-district schools for cards; fall back to all if none match
  const cardSchools = useMemo(() => {
    const inDistrict = allSchools.filter((s) => s.in_district);
    const base = inDistrict.length > 0 ? inDistrict : allSchools;
    // Sort assigned schools first
    return [...base].sort((a, b) => {
      if (a.assigned !== b.assigned) return a.assigned ? -1 : 1;
      return a.distance_miles - b.distance_miles;
    });
  }, [allSchools]);

  // Apply level filter to cards, then filter by map viewport bounds
  const levelFilteredCards = useMemo(
    () => cardSchools.filter((s) => matchesLevel(s.school_type)),
    [cardSchools, matchesLevel],
  );

  const visibleCards = useMemo(() => {
    if (!mapBounds) return levelFilteredCards;
    return levelFilteredCards.filter((s) => {
      if (s.assigned) return true; // always show assigned
      return (
        s.lat >= mapBounds.swLat &&
        s.lat <= mapBounds.neLat &&
        s.lon >= mapBounds.swLon &&
        s.lon <= mapBounds.neLon
      );
    });
  }, [levelFilteredCards, mapBounds]);

  // All schools go on the map, filtered by level
  const mapMarkers = useMemo(
    () =>
      allSchools
        .filter((s) => matchesLevel(s.school_type))
        .map((s) => ({
          id: schoolId(s),
          lat: s.lat,
          lon: s.lon,
          label: `${s.name} (${s.rating != null ? `${s.rating}/10` : "N/R"})`,
          color: getSchoolMarkerColor(s.rating),
        })),
    [allSchools, matchesLevel],
  );

  const headerText = homeDistrict ? `${homeDistrict.name} Schools` : "Schools";

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div
            className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent"
            role="status"
          >
            <span className="sr-only">Loading schools...</span>
          </div>
          <p className="text-sm text-[var(--color-db-text-secondary)]">Loading nearby schools...</p>
        </div>
      </div>
    );
  }

  if (error && allSchools.length === 0) {
    return (
      <DashboardCard>
        <p className="py-8 text-center text-sm text-[var(--color-db-text-muted)]">
          Unable to load nearby schools. Please try again later.
        </p>
      </DashboardCard>
    );
  }

  if (allSchools.length === 0) {
    return (
      <DashboardCard>
        <p className="py-8 text-center text-sm text-[var(--color-db-text-muted)]">
          No schools found near this property.
        </p>
      </DashboardCard>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
      {/* Left column — school details */}
      <div className="flex flex-col gap-4">
        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            {headerText}
          </h3>
          <div className="flex flex-col gap-2">
            {visibleCards.map((s) => {
              const id = schoolId(s);
              return (
                <SchoolCard
                  key={s.name}
                  school={s}
                  isSelected={selectedId === id}
                  onHover={() => setHoveredId(id)}
                  onLeave={() => setHoveredId(null)}
                  onClick={() => setSelectedId(selectedId === id ? null : id)}
                />
              );
            })}
          </div>
        </DashboardCard>
      </div>

      {/* Right column — map (sticky, fills viewport) */}
      <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
        <DashboardCard className="flex h-full flex-col">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Schools Map
            </h3>
            <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
              {LEVEL_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleLevel(opt.value)}
                  className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                    activeLevels.has(opt.value)
                      ? "bg-[var(--color-db-accent)] text-white"
                      : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
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
                ...mapMarkers,
              ]}
              height="100%"
              minHeight="400px"
              highlightedId={hoveredId}
              selectedId={selectedId}
            >
              <MapBoundsTracker onBoundsChange={setMapBounds} />
              {/* Render neighbor districts first (below), then home district on top */}
              {filteredDistricts
                .filter((d) => !d.is_home)
                .map((d) => (
                  <DistrictBoundary key={d.geoid} district={d} />
                ))}
              {filteredDistricts
                .filter((d) => d.is_home)
                .map((d) => (
                  <DistrictBoundary key={d.geoid} district={d} />
                ))}
            </DashboardMap>
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default SchoolsTab;
