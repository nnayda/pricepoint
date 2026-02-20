import { useCallback, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import MapTabBar from "./MapTabBar";
import CrimeHeatmapLayer from "./layers/CrimeHeatmapLayer";
import CrimeIncidentsLayer from "./layers/CrimeIncidentsLayer";
import PoisLayer from "./layers/PoisLayer";
import GreenspaceLayer from "./layers/GreenspaceLayer";
import UtilitiesLayer from "./layers/UtilitiesLayer";
import { useApi } from "../../hooks/useApi";
import { usePoiPreferences } from "../../hooks/usePoiPreferences";
import { getCrime, getPois, getGreenspace, getUtilities } from "../../services/property";
import type {
  MapTab,
  CrimeResponse,
  PoisResponse,
  GreenspaceResponse,
  UtilitiesResponse,
} from "../../types";

interface PropertyMapProps {
  lat: number;
  lon: number;
  address: string;
}

const ALL_TABS: MapTab[] = ["crime-density", "crime-incidents", "pois", "greenspace", "utilities"];

const RADIUS_OPTIONS = [0.5, 1, 2, 3, 5] as const;
const DAYS_BACK_OPTIONS = [
  { value: 30, label: "Last 30 days" },
  { value: 90, label: "Last 90 days" },
  { value: 365, label: "Last 365 days" },
] as const;

function PropertyMap({ lat, lon, address }: PropertyMapProps) {
  const [activeTab, setActiveTab] = useState<MapTab>("crime-density");
  const [radiusMiles, setRadiusMiles] = useState<number>(1);
  const [daysBack, setDaysBack] = useState<number>(365);
  const fetchedTabs = useRef(new Set<string>());

  const crime = useApi<CrimeResponse, [number, number, number | undefined, number | undefined]>(
    getCrime,
  );
  const pois = useApi<PoisResponse, [number, number, number | undefined]>(getPois);
  const greenspace = useApi<GreenspaceResponse, [number, number, number | undefined]>(
    getGreenspace,
  );
  const utilities = useApi<UtilitiesResponse, [number, number, number | undefined]>(getUtilities);

  const { preferences } = usePoiPreferences();
  const enabledPoiNames = new Set(preferences.filter((p) => p.enabled).map((p) => p.name));

  const fetchTab = useCallback(
    (tab: MapTab, radius: number, days: number) => {
      switch (tab) {
        case "crime-density":
        case "crime-incidents":
          crime.execute(lat, lon, radius, days);
          break;
        case "pois":
          pois.execute(lat, lon, radius);
          break;
        case "greenspace":
          greenspace.execute(lat, lon, radius);
          break;
        case "utilities":
          utilities.execute(lat, lon, radius);
          break;
      }
    },
    [lat, lon, crime, pois, greenspace, utilities],
  );

  const handleTabChange = useCallback(
    (tab: MapTab) => {
      setActiveTab(tab);
      if (fetchedTabs.current.has(tab)) return;
      fetchedTabs.current.add(tab);

      if (tab === "crime-density" || tab === "crime-incidents") {
        if (
          !fetchedTabs.current.has("crime-density") ||
          !fetchedTabs.current.has("crime-incidents")
        ) {
          fetchedTabs.current.add("crime-density");
          fetchedTabs.current.add("crime-incidents");
        }
        if (!crime.data && !crime.loading) crime.execute(lat, lon, radiusMiles, daysBack);
      } else if (tab === "pois") {
        if (!pois.data && !pois.loading) pois.execute(lat, lon, radiusMiles);
      } else if (tab === "greenspace") {
        if (!greenspace.data && !greenspace.loading) greenspace.execute(lat, lon, radiusMiles);
      } else if (tab === "utilities") {
        if (!utilities.data && !utilities.loading) utilities.execute(lat, lon, radiusMiles);
      }
    },
    [lat, lon, radiusMiles, daysBack, crime, pois, greenspace, utilities],
  );

  // Fetch crime data on mount for the default tab
  const initialFetched = useRef(false);
  if (!initialFetched.current) {
    initialFetched.current = true;
    fetchedTabs.current.add("crime-density");
    fetchedTabs.current.add("crime-incidents");
    crime.execute(lat, lon, radiusMiles, daysBack);
  }

  const handleRadiusChange = useCallback(
    (newRadius: number) => {
      setRadiusMiles(newRadius);
      fetchedTabs.current.clear();
      fetchedTabs.current.add(activeTab);
      if (activeTab === "crime-density" || activeTab === "crime-incidents") {
        fetchedTabs.current.add("crime-density");
        fetchedTabs.current.add("crime-incidents");
      }
      fetchTab(activeTab, newRadius, daysBack);
    },
    [activeTab, daysBack, fetchTab],
  );

  const handleDaysBackChange = useCallback(
    (newDays: number) => {
      setDaysBack(newDays);
      fetchedTabs.current.delete("crime-density");
      fetchedTabs.current.delete("crime-incidents");
      fetchedTabs.current.add("crime-density");
      fetchedTabs.current.add("crime-incidents");
      crime.execute(lat, lon, radiusMiles, newDays);
    },
    [lat, lon, radiusMiles, crime],
  );

  const isCrimeTab = activeTab === "crime-density" || activeTab === "crime-incidents";

  const activeError = isCrimeTab
    ? crime.error
    : activeTab === "pois"
      ? pois.error
      : activeTab === "greenspace"
        ? greenspace.error
        : utilities.error;

  const activeLoading = isCrimeTab
    ? crime.loading
    : activeTab === "pois"
      ? pois.loading
      : activeTab === "greenspace"
        ? greenspace.loading
        : utilities.loading;

  function handleRetry() {
    fetchTab(activeTab, radiusMiles, daysBack);
  }

  const filteredPois = pois.data?.pois.filter((p) => enabledPoiNames.has(p.name)) ?? [];

  const hasEmptyResults =
    !activeLoading &&
    !activeError &&
    ((isCrimeTab && crime.data && crime.data.incidents.length === 0) ||
      (activeTab === "pois" && pois.data && pois.data.pois.length === 0) ||
      (activeTab === "greenspace" && greenspace.data && greenspace.data.features.length === 0) ||
      (activeTab === "utilities" && utilities.data && utilities.data.features.length === 0));

  return (
    <section
      aria-label="Property map"
      className="rounded-lg bg-bg-card/80 shadow-soft backdrop-blur-md"
    >
      <MapTabBar tabs={ALL_TABS} activeTab={activeTab} onTabChange={handleTabChange} />

      <div className="flex flex-wrap items-center gap-3 border-b border-bg-main px-4 py-2">
        <label className="flex items-center gap-1.5 text-xs font-medium text-text-sec">
          Radius
          <select
            value={radiusMiles}
            onChange={(e) => handleRadiusChange(Number(e.target.value))}
            className="rounded-md border border-bg-main bg-bg-card px-2 py-1 text-xs text-text-pri"
            aria-label="Search radius"
          >
            {RADIUS_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r} {r === 1 ? "mile" : "miles"}
              </option>
            ))}
          </select>
        </label>

        {isCrimeTab && (
          <label className="flex items-center gap-1.5 text-xs font-medium text-text-sec">
            Time range
            <select
              value={daysBack}
              onChange={(e) => handleDaysBackChange(Number(e.target.value))}
              className="rounded-md border border-bg-main bg-bg-card px-2 py-1 text-xs text-text-pri"
              aria-label="Crime date range"
            >
              {DAYS_BACK_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="h-[400px] lg:h-[500px] xl:h-[600px]">
        <MapContainer center={[lat, lon]} zoom={14} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Marker position={[lat, lon]}>
            <Popup>{address}</Popup>
          </Marker>

          {activeTab === "crime-density" && crime.data && (
            <CrimeHeatmapLayer data={crime.data.heatmap} />
          )}
          {activeTab === "crime-incidents" && crime.data && (
            <CrimeIncidentsLayer data={crime.data.incidents} />
          )}
          {activeTab === "pois" && pois.data && <PoisLayer data={filteredPois} />}
          {activeTab === "greenspace" && greenspace.data && (
            <GreenspaceLayer data={greenspace.data.features} />
          )}
          {activeTab === "utilities" && utilities.data && (
            <UtilitiesLayer data={utilities.data.features} />
          )}
        </MapContainer>
      </div>

      <div
        id={`map-panel-${activeTab}`}
        role="tabpanel"
        aria-label={`${activeTab} metrics`}
        className="p-4"
      >
        {activeLoading && (
          <div className="flex items-center gap-2" aria-label="Loading tab data">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-brand-blue border-t-transparent" />
            <p className="text-sm text-text-sec">Loading data...</p>
          </div>
        )}

        {activeError && (
          <div className="flex items-center gap-2">
            <p className="text-sm text-status-rented">{activeError}</p>
            <button
              onClick={handleRetry}
              className="rounded-md bg-brand-blue px-3 py-1 text-xs font-medium text-white hover:opacity-90"
              aria-label="Retry loading data"
            >
              Retry
            </button>
          </div>
        )}

        {hasEmptyResults && (
          <p className="text-sm text-text-sec" role="status">
            No data found within {radiusMiles} {radiusMiles === 1 ? "mile" : "miles"}
          </p>
        )}

        {!activeLoading && !activeError && !hasEmptyResults && (
          <>
            {isCrimeTab && crime.data && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MetricItem
                  label="Total Incidents (1mi)"
                  value={String(crime.data.metrics.total_incidents_1mi)}
                />
                <MetricItem
                  label="Per 1K People"
                  value={crime.data.metrics.incidents_per_1000_people.toFixed(1)}
                />
                <MetricItem label="Z-Score" value={crime.data.metrics.crime_z_score.toFixed(2)} />
                <MetricItem label="Trend" value={crime.data.metrics.trend} />
              </div>
            )}

            {activeTab === "pois" && pois.data && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {(() => {
                  const categories = [...new Set(pois.data.pois.map((p) => p.category))];
                  return categories.map((cat) => {
                    const inCat = pois.data!.pois.filter((p) => p.category === cat);
                    const nearest = inCat.reduce((a, b) =>
                      a.distance_miles < b.distance_miles ? a : b,
                    );
                    return (
                      <MetricItem
                        key={cat}
                        label={cat}
                        value={`${inCat.length} nearby (${nearest.distance_miles.toFixed(1)} mi)`}
                      />
                    );
                  });
                })()}
              </div>
            )}

            {activeTab === "greenspace" && greenspace.data && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MetricItem
                  label="Parks (1mi)"
                  value={String(greenspace.data.metrics.parks_within_1mi)}
                />
                <MetricItem
                  label="Nearest Park"
                  value={`${greenspace.data.metrics.nearest_park_miles.toFixed(1)} mi`}
                />
                <MetricItem
                  label="Green Acres (1mi)"
                  value={greenspace.data.metrics.total_green_acres_1mi.toFixed(1)}
                />
                <MetricItem
                  label="Z-Score"
                  value={greenspace.data.metrics.greenspace_z_score.toFixed(2)}
                />
              </div>
            )}

            {activeTab === "utilities" && utilities.data && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MetricItem
                  label="Nearest Highway"
                  value={`${utilities.data.metrics.nearest_highway_miles.toFixed(1)} mi`}
                />
                <MetricItem
                  label="Nearest Railroad"
                  value={`${utilities.data.metrics.nearest_railroad_miles.toFixed(1)} mi`}
                />
                <MetricItem
                  label="Nearest Powerline"
                  value={`${utilities.data.metrics.nearest_powerline_miles.toFixed(1)} mi`}
                />
                <MetricItem
                  label="Nuisance Score"
                  value={utilities.data.metrics.nuisance_score.toFixed(1)}
                />
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-text-sec">{label}</p>
      <p className="text-sm font-bold text-text-pri">{value}</p>
    </div>
  );
}

export default PropertyMap;
