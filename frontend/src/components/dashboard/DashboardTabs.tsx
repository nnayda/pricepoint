import { useState, useCallback, useMemo, useRef, lazy, Suspense } from "react";
import type { DashboardTab, DashboardData } from "../../types";
import TabDot from "./ui/TabDot";

const ValuationTab = lazy(() => import("./tabs/ValuationTab"));
const RisksTab = lazy(() => import("./tabs/RisksTab"));
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
  { id: "demographics", label: "Demographics" },
  { id: "schools", label: "Schools" },
  { id: "pois", label: "Points of Interest" },
  { id: "nuisances", label: "Nuisances" },
  { id: "greenspace", label: "Greenspace" },
  { id: "property-details", label: "Property Details" },
];

/** Compute data-driven dot colors based on actual data */
function computeTabDots(data: DashboardData): Partial<Record<DashboardTab, string>> {
  const dots: Partial<Record<DashboardTab, string>> = {};

  // Dot color on Valuation matches outcome label
  const v = data.valuation;
  if (v.listed_price < v.confidence_low) {
    dots.valuation = "#34D399"; // Bargain → green
  } else if (v.listed_price >= v.confidence_high) {
    dots.valuation = "#F87171"; // Overpriced → red
  } else if (v.listed_price >= v.predicted_value) {
    dots.valuation = "#FBBF24"; // Fair → amber
  }
  // Value (listed < predicted but >= CI low) → no dot

  // Red dot on Risks if any risk score > 70
  if (data.risks.categories.some((c) => c.score > 70)) {
    dots.risks = "#F87171";
  }

  // Green dot on Schools if any school rated 8+
  if (data.schools.some((s) => s.rating != null && s.rating >= 8)) {
    dots.schools = "#34D399";
  }

  // Red dot on Negative POIs if any Concern, yellow if any Caution
  if (data.nuisances.some((n) => n.severity === "Concern")) {
    dots["nuisances"] = "#F87171";
  } else if (data.nuisances.some((n) => n.severity === "Caution")) {
    dots["nuisances"] = "#FBBF24";
  }

  return dots;
}

const TAB_COMPONENTS: Record<
  DashboardTab,
  React.LazyExoticComponent<React.ComponentType<{ data: DashboardData }>>
> = {
  valuation: ValuationTab,
  risks: RisksTab,
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

  const tabDots = useMemo(() => computeTabDots(data), [data]);

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

      {/* Tab Content — only the active tab is mounted to avoid Leaflet re-init errors */}
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
