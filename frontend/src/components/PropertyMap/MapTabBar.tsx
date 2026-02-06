import type { MapTab } from "../../types";

interface MapTabBarProps {
  tabs: MapTab[];
  activeTab: MapTab;
  onTabChange: (tab: MapTab) => void;
}

const TAB_LABELS: Record<MapTab, string> = {
  "crime-density": "Crime Density",
  "crime-incidents": "Crime Incidents",
  pois: "Points of Interest",
  greenspace: "Greenspace",
  utilities: "Utilities",
};

function MapTabBar({ tabs, activeTab, onTabChange }: MapTabBarProps) {
  return (
    <div
      className="flex gap-1 overflow-x-auto rounded-t-lg bg-bg-main p-1"
      role="tablist"
      aria-label="Map layers"
    >
      {tabs.map((tab) => (
        <button
          key={tab}
          role="tab"
          aria-selected={activeTab === tab}
          aria-controls={`map-panel-${tab}`}
          onClick={() => onTabChange(tab)}
          className={`whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            activeTab === tab
              ? "bg-brand-blue text-white"
              : "text-text-sec hover:bg-bg-card hover:text-text-pri"
          }`}
        >
          {TAB_LABELS[tab]}
        </button>
      ))}
    </div>
  );
}

export default MapTabBar;
