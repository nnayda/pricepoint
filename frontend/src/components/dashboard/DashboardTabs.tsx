import { useState, useCallback, useMemo, useRef, useEffect, lazy, Suspense } from "react";
import type { DashboardTab, DashboardData } from "../../types";
import { preloadSchoolsNearby } from "../../hooks/useSchoolsNearby";
import { preloadRisks } from "../../hooks/useRisks";
import { preloadNuisanceSources } from "../../hooks/useNuisanceSources";
import { preloadPoliceIncidents, usePoliceIncidents } from "../../hooks/usePoliceIncidents";
import type { CrimeIncident } from "../../types";
import TabDot from "./ui/TabDot";

const ValuationTab = lazy(() => import("./tabs/ValuationTab"));
const RisksTab = lazy(() => import("./tabs/RisksTab"));
const PoliceTab = lazy(() => import("./tabs/PoliceTab"));
const DemographicsTab = lazy(() => import("./tabs/DemographicsTab"));
const SchoolsTab = lazy(() => import("./tabs/SchoolsTab"));
const PoisTab = lazy(() => import("./tabs/PoisTab"));
const NuisancesTab = lazy(() => import("./tabs/NuisancesTab"));
const GreenspaceTab = lazy(() => import("./tabs/GreenspaceTab"));
const PropertyDetailsTab = lazy(() => import("./tabs/PropertyDetailsTab"));

interface TabDef {
  id: DashboardTab;
  label: string;
}

const TABS: TabDef[] = [
  { id: "valuation", label: "Valuation" },
  { id: "risks", label: "Risks" },
  { id: "police", label: "Crime" },
  { id: "demographics", label: "Demographics" },
  { id: "schools", label: "Schools" },
  { id: "pois", label: "Points of Interest" },
  { id: "nuisances", label: "Nuisances" },
  { id: "greenspace", label: "Greenspace" },
  { id: "property-details", label: "Property Details" },
];

const MILES_TO_RADIANS = Math.PI / 180;

/** Haversine distance in miles between two lat/lon points */
function distanceMiles(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 3958.8; // Earth radius in miles
  const dLat = (lat2 - lat1) * MILES_TO_RADIANS;
  const dLon = (lon2 - lon1) * MILES_TO_RADIANS;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * MILES_TO_RADIANS) * Math.cos(lat2 * MILES_TO_RADIANS) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** Return the worst offense class among incidents within 0.5 miles: "Group A" > "Group B" > null */
function worstOffenseWithinHalfMile(
  incidents: CrimeIncident[],
  lat: number,
  lon: number,
): "Group A" | "Group B" | null {
  let hasGroupB = false;
  for (const i of incidents) {
    if (distanceMiles(lat, lon, i.lat, i.lon) <= 0.5) {
      if (
        i.offense_class &&
        i.offense_class !== "Group B" &&
        i.offense_class !== "Animal Disturbance"
      ) {
        return "Group A"; // Severe — short-circuit
      }
      if (i.offense_class === "Group B") {
        hasGroupB = true;
      }
    }
  }
  return hasGroupB ? "Group B" : null;
}

/** Compute data-driven dot colors based on actual data */
function computeTabDots(data: DashboardData): Partial<Record<DashboardTab, string>> {
  const dots: Partial<Record<DashboardTab, string>> = {};

  // Dot color on Valuation matches outcome label (only if model estimate exists)
  const v = data.valuation;
  if (v.predicted_value != null) {
    if (v.confidence_low != null && v.listed_price < v.confidence_low) {
      dots.valuation = "#34D399"; // Bargain → green
    } else if (v.confidence_high != null && v.listed_price >= v.confidence_high) {
      dots.valuation = "#F87171"; // Overpriced → red
    } else if (v.listed_price >= v.predicted_value) {
      dots.valuation = "#FBBF24"; // Fair → amber
    }
    // Value (listed < predicted but >= CI low) → no dot
  }

  // Red dot on Risks if any risk score > 70
  if (data.risks.categories.some((c) => c.score > 70)) {
    dots.risks = "#F87171";
  }

  // Green dot on Schools if any school rated 8+
  if (data.schools.some((s) => s.rating != null && s.rating >= 8)) {
    dots.schools = "#34D399";
  }

  return dots;
}

const TAB_COMPONENTS: Record<
  DashboardTab,
  React.LazyExoticComponent<React.ComponentType<{ data: DashboardData }>>
> = {
  valuation: ValuationTab,
  risks: RisksTab,
  police: PoliceTab,
  demographics: DemographicsTab,
  schools: SchoolsTab,
  pois: PoisTab,
  nuisances: NuisancesTab,
  greenspace: GreenspaceTab,
  "property-details": PropertyDetailsTab,
};

interface DashboardTabsProps {
  data: DashboardData;
}

function TabLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-db-accent)] border-t-transparent" />
    </div>
  );
}

function DashboardTabs({ data }: DashboardTabsProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>("valuation");
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const { incidents } = usePoliceIncidents(data.property.lat, data.property.lon);

  // Preload data so it's ready when tabs are opened
  useEffect(() => {
    preloadSchoolsNearby(data.property.lat, data.property.lon);
    preloadRisks(data.property.lat, data.property.lon);
    preloadNuisanceSources(data.property.lat, data.property.lon);
    preloadPoliceIncidents(data.property.lat, data.property.lon);
  }, [data.property.lat, data.property.lon]);

  const tabDots = useMemo(() => {
    const dots = computeTabDots(data);
    const worst = worstOffenseWithinHalfMile(incidents, data.property.lat, data.property.lon);
    if (worst === "Group A") {
      dots.police = "#F87171"; // red
    } else if (worst === "Group B") {
      dots.police = "#FBBF24"; // yellow
    }
    return dots;
  }, [data, incidents]);

  const handleTabClick = useCallback((tab: DashboardTab) => {
    setActiveTab(tab);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const currentIndex = TABS.findIndex((t) => t.id === activeTab);
      let nextIndex = currentIndex;

      if (e.key === "ArrowRight") {
        e.preventDefault();
        nextIndex = (currentIndex + 1) % TABS.length;
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        nextIndex = (currentIndex - 1 + TABS.length) % TABS.length;
      } else if (e.key === "Home") {
        e.preventDefault();
        nextIndex = 0;
      } else if (e.key === "End") {
        e.preventDefault();
        nextIndex = TABS.length - 1;
      } else {
        return;
      }

      const nextTab = TABS[nextIndex];
      handleTabClick(nextTab.id);
      tabRefs.current[nextIndex]?.focus();
    },
    [activeTab, handleTabClick],
  );

  const ActiveComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      {/* Tab Bar */}
      <div
        role="tablist"
        aria-label="Property details tabs"
        onKeyDown={handleKeyDown}
        className="scrollbar-none flex gap-1 overflow-x-auto border-b border-[var(--color-db-border-subtle)] px-1"
      >
        {TABS.map((tab, index) => {
          const isActive = activeTab === tab.id;
          const dotColor = tabDots[tab.id];
          return (
            <button
              key={tab.id}
              ref={(el) => {
                tabRefs.current[index] = el;
              }}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => handleTabClick(tab.id)}
              className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 font-db-sans text-sm font-medium transition-colors ${
                isActive
                  ? "border-[var(--color-db-accent)] text-[var(--color-db-text-primary)]"
                  : "border-transparent text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
              }`}
            >
              {dotColor && <TabDot color={dotColor} />}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content — only the active tab is mounted */}
      <div
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className="p-5"
      >
        <Suspense fallback={<TabLoader />}>
          <ActiveComponent data={data} />
        </Suspense>
      </div>
    </div>
  );
}

export default DashboardTabs;
