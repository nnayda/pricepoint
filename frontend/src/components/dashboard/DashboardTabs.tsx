import { useState, useCallback, useMemo, lazy, Suspense } from "react";
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
  dotColor: string;
}

const TABS: TabDef[] = [
  { id: "valuation", label: "Valuation", dotColor: "#6366F1" },
  { id: "risks", label: "Risks", dotColor: "#F87171" },
  { id: "demographics", label: "Demographics", dotColor: "#22D3EE" },
  { id: "schools", label: "Schools", dotColor: "#34D399" },
  { id: "pois", label: "POIs", dotColor: "#FBBF24" },
  { id: "negative-pois", label: "Negative POIs", dotColor: "#FB923C" },
  { id: "greenspace", label: "Greenspace", dotColor: "#34D399" },
  { id: "property-details", label: "Property Details", dotColor: "#A78BFA" },
];

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

  const handleTabClick = useCallback((tab: DashboardTab) => {
    setActiveTab(tab);
    setVisited((prev) => {
      if (prev.has(tab)) return prev;
      const next = new Set(prev);
      next.add(tab);
      return next;
    });
  }, []);

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
      <div className="scrollbar-none flex gap-1 overflow-x-auto border-b border-[var(--color-db-border-subtle)] px-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => handleTabClick(tab.id)}
            className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-[var(--color-db-accent)] text-[var(--color-db-text-primary)]"
                : "border-transparent text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
            }`}
            style={{ fontFamily: "var(--font-db-sans)" }}
          >
            <TabDot color={tab.dotColor} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-5">
        <Suspense fallback={<TabLoader />}>
          {TABS.map((tab) => {
            if (!visited.has(tab.id)) return null;
            return (
              <div
                key={tab.id}
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
