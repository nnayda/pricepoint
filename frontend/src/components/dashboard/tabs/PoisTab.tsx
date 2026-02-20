import { useState } from "react";
import type { DashboardData, DashboardPoi } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { POI_ICONS, ShoppingCartIcon } from "../ui/Icons";

interface PoisTabProps {
  data: DashboardData;
}

const CATEGORY_COLORS: Record<string, string> = {
  Grocery: "#34D399",
  Healthcare: "#F87171",
  Recreation: "#6366F1",
  Dining: "#FBBF24",
  Shopping: "#22D3EE",
  Services: "#A78BFA",
};

function PoisTab({ data }: PoisTabProps) {
  const { pois, property } = data;

  const categories = [...new Set(pois.map((p) => p.category))];
  const grouped = categories.reduce(
    (acc, cat) => {
      acc[cat] = pois.filter((p) => p.category === cat);
      return acc;
    },
    {} as Record<string, DashboardPoi[]>,
  );

  // All categories expanded by default
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set(categories));

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

  const mapMarkers = pois.map((p) => ({
    lat: p.lat,
    lon: p.lon,
    label: `${p.name} (${p.distance_miles} mi)`,
    color: CATEGORY_COLORS[p.category] || "#6366F1",
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* POI Score Summary */}
      <DashboardCard>
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--color-db-accent-muted)]">
            <span
              className="text-lg font-bold text-[var(--color-db-accent)]"
              style={{ fontFamily: "var(--font-db-mono)" }}
            >
              {pois.length}
            </span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Points of Interest
            </h3>
            <p className="text-xs text-[var(--color-db-text-tertiary)]">
              {categories.length} categories within driving distance
            </p>
          </div>
        </div>
      </DashboardCard>

      {/* Accordion by Category — all expanded by default */}
      <div className="flex flex-col gap-2">
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
                      return (
                        <div
                          key={poi.id}
                          className="flex items-center justify-between rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-hover)] px-3 py-2"
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

      {/* POI Map */}
      <DashboardCard>
        <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">POI Map</h3>
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

export default PoisTab;
