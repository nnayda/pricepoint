import type { DashboardData, DashboardSchool } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { MapPinIcon, CarIcon, WalkIcon, UsersIcon, ChartBarIcon } from "../ui/Icons";

interface SchoolsTabProps {
  data: DashboardData;
}

function ratingColor(rating: number): string {
  if (rating >= 8) return "var(--color-db-green)";
  if (rating >= 6) return "var(--color-db-yellow)";
  return "var(--color-db-red)";
}

function SchoolCard({ school }: { school: DashboardSchool }) {
  return (
    <div className="flex gap-3 rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface-alt)] p-4">
      {/* Rating circle */}
      <div
        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl"
        style={{ backgroundColor: `${ratingColor(school.rating)}20` }}
      >
        <span
          className="text-lg font-bold"
          style={{ color: ratingColor(school.rating), fontFamily: "var(--font-db-mono)" }}
        >
          {school.rating}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              {school.name}
            </h4>
            <p className="text-xs text-[var(--color-db-text-muted)]">
              {school.school_type} · {school.grades}
            </p>
          </div>
          {school.assigned && (
            <span className="rounded-full bg-[var(--color-db-accent-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-db-accent)]">
              Assigned
            </span>
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-[var(--color-db-text-tertiary)]">
          <span className="inline-flex items-center gap-1">
            <MapPinIcon size={12} /> {school.distance_miles} mi
          </span>
          <span className="inline-flex items-center gap-1">
            <CarIcon size={12} /> {school.drive_minutes} min
          </span>
          {school.walk_minutes && (
            <span className="inline-flex items-center gap-1">
              <WalkIcon size={12} /> {school.walk_minutes} min
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <UsersIcon size={12} /> {school.student_teacher_ratio}:1
          </span>
          <span className="inline-flex items-center gap-1">
            <ChartBarIcon size={12} /> {school.test_scores}%
          </span>
        </div>
      </div>
    </div>
  );
}

function SchoolsTab({ data }: SchoolsTabProps) {
  const { schools, property } = data;
  const assigned = schools.filter((s) => s.assigned);
  const nearby = schools.filter((s) => !s.assigned);

  const mapMarkers = schools.map((s) => ({
    lat: s.lat,
    lon: s.lon,
    label: `${s.name} (${s.rating}/10)`,
    color: s.rating >= 8 ? "#34D399" : s.rating >= 6 ? "#FBBF24" : "#F87171",
  }));

  return (
    <div className="flex flex-col gap-5">
      {/* Schools in columns */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Assigned Schools
          </h3>
          <div className="flex flex-col gap-2">
            {assigned.map((s) => (
              <SchoolCard key={s.name} school={s} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Nearby Schools
          </h3>
          <div className="flex flex-col gap-2">
            {nearby.map((s) => (
              <SchoolCard key={s.name} school={s} />
            ))}
          </div>
        </div>
      </div>

      {/* Map */}
      <DashboardCard>
        <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
          Schools Map
        </h3>
        <DashboardMap
          center={[property.lat, property.lon]}
          zoom={13}
          markers={[
            { lat: property.lat, lon: property.lon, label: "Property", color: "#6366F1" },
            ...mapMarkers,
          ]}
          height="320px"
        />
      </DashboardCard>
    </div>
  );
}

export default SchoolsTab;
