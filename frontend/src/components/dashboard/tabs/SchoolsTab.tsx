import { useState, useMemo } from "react";
import type { DashboardData, DashboardSchool } from "../../../types";
import { useSchoolsNearby } from "../../../hooks/useSchoolsNearby";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { MapPinIcon, CarIcon, WalkIcon } from "../ui/Icons";
import { getSchoolMarkerColor, COLOR_INDIGO } from "../../../utils/chartTokens";

interface SchoolsTabProps {
  data: DashboardData;
}

function mapSchool(s: {
  name: string;
  address?: string;
  school_type: string;
  school_level?: string;
  rating: number;
  grades?: string;
  distance_miles: number;
  drive_minutes: number;
  walk_minutes?: number;
  student_teacher_ratio?: number;
  enrollment?: number;
  assigned?: boolean;
  lat?: number;
  lon?: number;
}): DashboardSchool {
  return {
    name: s.name,
    address: s.address ?? "",
    school_type: (s.school_level ?? s.school_type ?? "Elementary") as
      | "Elementary"
      | "Middle"
      | "High"
      | "K-8"
      | "Charter",
    rating: s.rating,
    grades: s.grades ?? "",
    distance_miles: s.distance_miles,
    drive_minutes: s.drive_minutes,
    walk_minutes: s.walk_minutes,
    student_teacher_ratio: s.student_teacher_ratio ?? 0,
    test_scores: 0,
    assigned: s.assigned ?? false,
    lat: s.lat ?? 0,
    lon: s.lon ?? 0,
  };
}

function ratingColor(rating: number): string {
  if (rating >= 8) return "var(--color-db-green)";
  if (rating >= 6) return "var(--color-db-yellow)";
  return "var(--color-db-red)";
}

function RatingGauge({ rating }: { rating: number }) {
  const size = 52;
  const stroke = 4;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
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
          {school.walk_minutes && (
            <span className="inline-flex items-center gap-1">
              <WalkIcon size={14} /> {school.walk_minutes} min
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function schoolId(s: DashboardSchool) {
  return `school-${s.lat}-${s.lon}`;
}

function SchoolsTab({ data }: SchoolsTabProps) {
  const { property } = data;
  const { schools: apiSchools, loading, error } = useSchoolsNearby(property.lat, property.lon);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Use API schools if available, fall back to bundled data
  const schools = useMemo(() => {
    if (apiSchools.length > 0) {
      return apiSchools.map(mapSchool);
    }
    return data.schools;
  }, [apiSchools, data.schools]);

  const mapMarkers = schools.map((s) => ({
    id: schoolId(s),
    lat: s.lat,
    lon: s.lon,
    label: `${s.name} (${s.rating}/10)`,
    color: getSchoolMarkerColor(s.rating),
  }));

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

  if (error && schools.length === 0) {
    return (
      <DashboardCard>
        <p className="py-8 text-center text-sm text-[var(--color-db-text-muted)]">
          Unable to load nearby schools. Please try again later.
        </p>
      </DashboardCard>
    );
  }

  if (schools.length === 0) {
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
            Schools
          </h3>
          <div className="flex flex-col gap-2">
            {schools.map((s) => {
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
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Schools Map
          </h3>
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
            />
          </div>
        </DashboardCard>
      </div>
    </div>
  );
}

export default SchoolsTab;
