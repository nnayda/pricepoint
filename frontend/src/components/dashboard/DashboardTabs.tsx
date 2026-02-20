import { useState, useCallback, useMemo, useRef, lazy, Suspense } from "react";
import type { DashboardTab, DashboardData } from "../../types";
import TabDot from "./ui/TabDot";

const ValuationTab = lazy(() => import("./tabs/ValuationTab"));
const RisksTab = lazy(() => import("./tabs/RisksTab"));
const DemographicsTab = lazy(() => import("./tabs/DemographicsTab"));
const SchoolsTab = lazy(() => import("./tabs/SchoolsTab"));
const PoisTab = lazy(() => import("./tabs/PoisTab"));
const NegativePoisTab = lazy(() => import("./tabs/NegativePoisTab"));
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
  { id: "pois", label: "POIs" },
  { id: "negative-pois", label: "Negative POIs" },
  { id: "greenspace", label: "Greenspace" },
  { id: "property-details", label: "Property Details" },
];

/** Compute data-driven dot colors based on actual data */
function computeTabDots(data: DashboardData): Partial<Record<DashboardTab, string>> {
  const dots: Partial<Record<DashboardTab, string>> = {};

  // Amber dot on Valuation if confidence is not "High"
  const ciWidth = data.valuation.confidence_high - data.valuation.confidence_low;
  const ciPct = ciWidth / data.valuation.predicted_value;
  if (ciPct > 0.05) {
    dots.valuation = "#FBBF24";
  }

  // Red dot on Risks if any risk score > 70
  if (data.risks.categories.some((c) => c.score > 70)) {
    dots.risks = "#F87171";
  }

  // Green dot on Schools if any school rated 8+
  if (data.schools.some((s) => s.rating >= 8)) {
    dots.schools = "#34D399";
  }

  return dots;
}

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
  const [visited, setVisited] = useState<Set<DashboardTab>>(new Set(["valuation"]));
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const tabDots = useMemo(() => computeTabDots(data), [data]);

  const handleTabClick = useCallback((tab: DashboardTab) => {
    setActiveTab(tab);
    setVisited((prev) => {
      if (prev.has(tab)) return prev;
      const next = new Set(prev);
      next.add(tab);
      return next;
    });
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

  const tabComponents = useMemo(
    () => ({
      valuation: <ValuationTab data={data} />,
      risks: <RisksTab data={data} />,
      demographics: <DemographicsTab data={data} />,
      schools: <SchoolsTab data={data} />,
      pois: <PoisTab data={data} />,
      "negative-pois": <NegativePoisTab data={data} />,
      greenspace: <GreenspaceTab data={data} />,
      "property-details": <PropertyDetailsTab data={data} />,
    }),
    [data],
  );

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
              ref={(el) => { tabRefs.current[index] = el; }}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => handleTabClick(tab.id)}
              className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                isActive
                  ? "border-[var(--color-db-accent)] text-[var(--color-db-text-primary)]"
                  : "border-transparent text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
              }`}
              style={{ fontFamily: "var(--font-db-sans)" }}
            >
              {dotColor && <TabDot color={dotColor} />}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="p-5">
        <Suspense fallback={<TabLoader />}>
          {TABS.map((tab) => {
            if (!visited.has(tab.id)) return null;
            return (
              <div
                key={tab.id}
                role="tabpanel"
                id={`tabpanel-${tab.id}`}
                aria-labelledby={`tab-${tab.id}`}
                style={{ display: activeTab === tab.id ? "block" : "none" }}
              >
                {tabComponents[tab.id]}
              </div>
            );
          })}
        </Suspense>
      </div>
    </div>
  );
}

export default DashboardTabs;
