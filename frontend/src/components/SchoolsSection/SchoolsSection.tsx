import type { SchoolNearby } from "../../types";

interface SchoolsSectionProps {
  schools: SchoolNearby[];
}

function ratingColor(rating: number): string {
  if (rating >= 7) return "bg-status-maint text-white";
  if (rating >= 4) return "bg-yellow-400 text-text-pri";
  return "bg-status-rented text-white";
}

function SchoolsSection({ schools }: SchoolsSectionProps) {
  if (schools.length === 0) {
    return (
      <section
        aria-label="Nearby schools"
        className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
      >
        <h2 className="text-lg font-bold text-text-pri">Nearby Schools</h2>
        <p className="mt-3 text-sm text-text-sec">No school data available.</p>
      </section>
    );
  }

  return (
    <section
      aria-label="Nearby schools"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <h2 className="text-lg font-bold text-text-pri">Nearby Schools</h2>
      <ul className="mt-4 space-y-3" aria-label="School list">
        {schools.map((school, i) => (
          <li key={i} className="flex items-center gap-3">
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${ratingColor(school.rating)}`}
              aria-label={`Rating ${school.rating} out of 10`}
            >
              {school.rating}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold text-text-pri">{school.name}</p>
              <p className="text-xs text-text-sec">
                <span className="inline-block rounded bg-bg-main px-1.5 py-0.5 text-xs font-medium">
                  {school.school_type}
                </span>
                <span className="ml-2">{school.distance_miles.toFixed(1)} mi</span>
                <span className="ml-2">{school.drive_minutes} min drive</span>
                {school.walk_minutes != null && (
                  <span className="ml-2">{school.walk_minutes} min walk</span>
                )}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default SchoolsSection;
