import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  AreaChart,
  Area,
  LineChart,
  Line,
  Legend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import { GeoJSON, useMap, useMapEvents } from "react-leaflet";
import type { Layer } from "leaflet";
import type {
  DashboardData,
  DemographicContext,
  DemographicSubTab,
  DemographicData,
} from "../../../types";
import DashboardCard, { useCardExpanded } from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import ChoroplethLegend from "../maps/ChoroplethLegend";
import SemiCircularGauge from "../charts/SemiCircularGauge";
import { MOCK_CHOROPLETH_MAP } from "../../../data/mockDemographicGeo";
import {
  getChoroplethStyle,
  getTooltipText,
  getLegendConfig,
  computeDataRange,
} from "../../../utils/choroplethColors";
import { useChoropleth, type Bbox } from "../../../hooks/useChoropleth";
import {
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  AXIS_TICK_MONO,
  AXIS_TICK_MONO_SM,
  AXIS_LINE_STYLE,
  CURSOR_BAR,
  CURSOR_LINE,
  COLOR_INDIGO,
  COLOR_CYAN,
  COLOR_GREEN,
  COLOR_AMBER,
  COLOR_RED,
  COLOR_BLUE,
  COLOR_PURPLE,
  COLOR_PINK,
  COLOR_GRID_LINE,
} from "../../../utils/chartTokens";

interface DemographicsTabProps {
  data: DashboardData;
}

const CONTEXT_OPTIONS: { value: DemographicContext; label: string }[] = [
  { value: "subdivision", label: "Subdivision" },
  { value: "block_group", label: "Block Group" },
  { value: "neighborhood", label: "Neighborhood" },
  { value: "town", label: "Town" },
  { value: "county", label: "County" },
];

const SUB_TAB_OPTIONS: { value: DemographicSubTab; label: string }[] = [
  { value: "population", label: "Population" },
  { value: "race", label: "Race" },
  { value: "age", label: "Age" },
  { value: "income", label: "Income" },
  { value: "ownership", label: "Ownership" },
];

const CONTEXT_ZOOM: Record<DemographicContext, number> = {
  subdivision: 15,
  block_group: 15,
  neighborhood: 14,
  town: 12,
  county: 10,
};

const RACE_FILTER_OPTIONS = [
  { value: "all", label: "All" },
  { value: "white", label: "White" },
  { value: "black", label: "Black" },
  { value: "hispanic", label: "Hispanic" },
  { value: "asian", label: "Asian" },
  { value: "other", label: "Other" },
];

/** Reports map viewport bounds on mount and on every moveend. */
function MapBoundsTracker({ onBoundsChange }: { onBoundsChange: (bbox: Bbox) => void }) {
  const map = useMapEvents({
    moveend: () => {
      const b = map.getBounds();
      onBoundsChange({
        swLat: b.getSouth(),
        swLon: b.getWest(),
        neLat: b.getNorth(),
        neLon: b.getEast(),
      });
    },
  });

  // Fire initial bounds after mount so the hook can fetch immediately
  useEffect(() => {
    // Small delay to let MapContainer finish initializing
    const timer = setTimeout(() => {
      const b = map.getBounds();
      onBoundsChange({
        swLat: b.getSouth(),
        swLon: b.getWest(),
        neLat: b.getNorth(),
        neLon: b.getEast(),
      });
    }, 100);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

/** Programmatically updates map center/zoom when props change (MapContainer ignores prop updates). */
function MapViewController({
  center,
  zoom,
  onBoundsChange,
}: {
  center: [number, number];
  zoom: number;
  onBoundsChange: (bbox: Bbox) => void;
}) {
  const map = useMap();
  const prevRef = useRef({ center, zoom });

  useEffect(() => {
    const prev = prevRef.current;
    if (prev.center[0] !== center[0] || prev.center[1] !== center[1] || prev.zoom !== zoom) {
      prevRef.current = { center, zoom };
      map.flyTo(center, zoom, { duration: 0.5 });

      // After the fly animation completes, report new bounds
      const onMoveEnd = () => {
        const b = map.getBounds();
        onBoundsChange({
          swLat: b.getSouth(),
          swLon: b.getWest(),
          neLat: b.getNorth(),
          neLon: b.getEast(),
        });
        map.off("moveend", onMoveEnd);
      };
      map.on("moveend", onMoveEnd);
    }
  }, [center, zoom, map, onBoundsChange]);

  return null;
}

function DemographicsTab({ data }: DemographicsTabProps) {
  const { demographics, property } = data;
  const [context, setContext] = useState<DemographicContext>("neighborhood");
  const [subTab, setSubTab] = useState<DemographicSubTab>("population");
  const [raceFilter, setRaceFilter] = useState<string>("all");
  const [mapBbox, setMapBbox] = useState<Bbox | null>(null);

  const d = demographics.contexts[context];

  const initialChoropleth = demographics.choropleth?.[context] ?? MOCK_CHOROPLETH_MAP[context];

  const { data: choroplethData } = useChoropleth(
    context,
    mapBbox,
    property.lat,
    property.lon,
    initialChoropleth,
  );

  // Reset race filter when switching away from race sub-tab
  useEffect(() => {
    if (subTab !== "race") {
      setRaceFilter("all");
    }
  }, [subTab]);

  const dataRange = useMemo(
    () => computeDataRange(choroplethData.features, subTab),
    [choroplethData.features, subTab],
  );

  // Key must change when data, context, subTab, or raceFilter changes to force GeoJSON remount
  const choroplethKey = useMemo(
    () =>
      `choropleth-${context}-${subTab}-${raceFilter}-${choroplethData.features.length}-${dataRange?.min}-${dataRange?.max}`,
    [context, subTab, raceFilter, choroplethData, dataRange],
  );
  const legendConfig = useMemo(
    () => getLegendConfig(subTab, raceFilter, dataRange),
    [subTab, raceFilter, dataRange],
  );

  const handleBoundsChange = useCallback((bbox: Bbox) => {
    setMapBbox(bbox);
  }, []);

  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-64px-36px-24px-46px-40px)] lg:overflow-hidden">
      {/* Selector row — category left, geography right */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
          {SUB_TAB_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setSubTab(opt.value)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                subTab === opt.value
                  ? "bg-[var(--color-db-accent)] text-white"
                  : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
          {CONTEXT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setContext(opt.value)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                context === opt.value
                  ? "bg-[var(--color-db-accent)] text-white"
                  : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Two-column layout: charts left (scrollable), map right (fills height) */}
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[1fr_2fr]">
        {/* Left column — snapshot + trend, scrollable when content overflows */}
        <div className="scrollbar-themed flex flex-col gap-4 lg:overflow-y-auto">
          {/* Snapshot card */}
          {subTab === "population" && <PopulationSnapshot d={d} />}
          {subTab === "race" && <RaceSnapshot d={d} />}
          {subTab === "age" && <AgeSnapshot d={d} />}
          {subTab === "income" && <IncomeSnapshot d={d} />}
          {subTab === "ownership" && <OwnershipSnapshot d={d} />}

          {/* Trend card */}
          {subTab === "population" && <PopulationTrend d={d} />}
          {subTab === "population" && <PopulationFunnel demographics={demographics} />}
          {subTab === "race" && <RaceTrend d={d} />}
          {subTab === "race" && <RaceComparison demographics={demographics} context={context} />}
          {subTab === "age" && <AgeTrend d={d} />}
          {subTab === "age" && <MedianAgeTrend d={d} />}
          {subTab === "income" && <IncomeTrend d={d} />}
          {subTab === "ownership" && <OwnershipTrend d={d} />}
        </div>

        {/* Right column — map fills grid cell */}
        <div className="min-h-[400px] lg:min-h-0">
          <DashboardCard className="flex h-full flex-col overflow-hidden">
            <div className="mb-3 flex shrink-0 items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
                Demographics Map
              </h3>
              {subTab === "race" && (
                <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
                  {RACE_FILTER_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setRaceFilter(opt.value)}
                      className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                        raceFilter === opt.value
                          ? "bg-[var(--color-db-accent)] text-white"
                          : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="relative min-h-0 flex-1">
              <DashboardMap
                center={[property.lat, property.lon]}
                zoom={CONTEXT_ZOOM[context]}
                markers={[
                  {
                    lat: property.lat,
                    lon: property.lon,
                    label: "Property",
                    color: COLOR_INDIGO,
                    isProperty: true,
                  },
                ]}
                height="100%"
              >
                <MapBoundsTracker onBoundsChange={handleBoundsChange} />
                <MapViewController
                  center={[property.lat, property.lon]}
                  zoom={CONTEXT_ZOOM[context]}
                  onBoundsChange={handleBoundsChange}
                />
                {/* Choropleth features — context + subTab aware */}
                <GeoJSON
                  key={choroplethKey}
                  data={choroplethData}
                  style={(feature) => getChoroplethStyle(feature, subTab, raceFilter, dataRange)}
                  onEachFeature={(feature: GeoJSON.Feature, layer: Layer) => {
                    const text = getTooltipText(
                      (feature.properties ?? {}) as Record<string, unknown>,
                      subTab,
                      context,
                      raceFilter,
                    );
                    layer.bindTooltip(text, {
                      sticky: true,
                      className: "leaflet-tooltip-choropleth",
                    });
                  }}
                />
              </DashboardMap>
              <ChoroplethLegend config={legendConfig} />
            </div>
          </DashboardCard>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Snapshot sub-components                                            */
/* ------------------------------------------------------------------ */

interface SubTabProps {
  d: DashboardData["demographics"]["contexts"]["neighborhood"];
}

/* Expanded-mode tick styles — larger fonts for fullscreen view */
const AXIS_TICK_EXPANDED = {
  fill: "var(--color-db-text-secondary, #9BA3BF)",
  fontSize: 14,
  fontFamily: "var(--font-db-mono)",
} as const;

const AXIS_TICK_EXPANDED_SM = {
  fill: "var(--color-db-text-secondary, #9BA3BF)",
  fontSize: 13,
  fontFamily: "var(--font-db-mono)",
} as const;

const TOOLTIP_EXPANDED: React.CSSProperties = {
  ...TOOLTIP_CONTENT_STYLE,
  fontSize: 14,
};

const LEGEND_EXPANDED = { fontSize: 14, color: "var(--color-db-text-tertiary)" };
const LEGEND_DEFAULT = { fontSize: 11, color: "var(--color-db-text-tertiary)" };

function PopulationSnapshot({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col items-center justify-center" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Population
        </h3>
        <div className="flex flex-col items-center gap-2 py-4">
          <span
            className={`rounded-full font-db-mono px-4 py-1.5 font-semibold ${expanded ? "text-3xl" : "text-lg"}`}
            style={{ backgroundColor: `${COLOR_INDIGO}26`, color: COLOR_INDIGO }}
          >
            {d.population.toLocaleString()}
          </span>
          <span
            className={`text-[var(--color-db-text-tertiary)] ${expanded ? "text-sm" : "text-xs"}`}
          >
            Current estimated population
          </span>
        </div>
      </div>
    </DashboardCard>
  );
}

interface PopulationFunnelProps {
  demographics: DemographicData;
}

function PopulationFunnel({ demographics }: PopulationFunnelProps) {
  const expanded = useCardExpanded();
  const funnelData = useMemo(() => {
    const levels: { name: string; population: number }[] = [
      { name: "State", population: demographics.benchmarks?.state?.population ?? 0 },
      { name: "County", population: demographics.contexts.county.population },
      { name: "Town", population: demographics.contexts.town.population },
      { name: "Neighborhood", population: demographics.contexts.neighborhood.population },
      { name: "Block Group", population: demographics.contexts.block_group.population },
      { name: "Subdivision", population: demographics.contexts.subdivision.population },
    ];

    const filtered = levels.filter((l) => l.population > 0);
    const maxPop = filtered.length > 0 ? filtered[0].population : 1;

    return filtered.map((level, i) => ({
      name: level.name,
      value: level.population,
      fill: FUNNEL_COLORS[i] ?? FUNNEL_COLORS[FUNNEL_COLORS.length - 1],
      pctOfParent:
        i === 0 ? null : Math.round((level.population / filtered[i - 1].population) * 100),
      parentName: i === 0 ? null : filtered[i - 1].name,
      widthPct: (level.population / maxPop) * 100,
    }));
  }, [demographics]);

  if (funnelData.length === 0) return null;

  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Population by Geography
        </h3>
        <div
          className={`flex flex-col justify-evenly ${expanded ? "flex-1 gap-4" : "gap-2.5"}`}
        >
          {funnelData.map((level) => (
            <div key={level.name} className="flex items-center gap-3">
              <span
                className={`shrink-0 text-right font-medium text-[var(--color-db-text-secondary)] ${expanded ? "w-[100px] text-sm" : "w-[72px] text-[11px]"}`}
              >
                {level.name}
              </span>
              <div className="flex flex-1 items-center gap-2">
                <div
                  className={`rounded-r-md transition-all ${expanded ? "h-10" : "h-7"}`}
                  style={{
                    width: `${Math.max(level.widthPct, 8)}%`,
                    backgroundColor: level.fill,
                  }}
                />
                <span
                  className={`font-db-mono font-bold text-[var(--color-db-text-secondary)] ${expanded ? "text-sm" : "text-[11px]"}`}
                >
                  {level.value.toLocaleString()}
                </span>
              </div>
              <span
                className={`shrink-0 text-[var(--color-db-text-tertiary)] ${expanded ? "w-[100px] text-xs" : "w-[72px] text-[10px]"}`}
              >
                {level.pctOfParent !== null ? (
                  <>
                    {level.pctOfParent}% of {level.parentName}
                  </>
                ) : (
                  "\u00A0"
                )}
              </span>
            </div>
          ))}
        </div>
      </div>
    </DashboardCard>
  );
}

function RaceSnapshot({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Race & Ethnicity
        </h3>
        <div
          className={`flex flex-col items-center gap-4 ${expanded ? "min-h-0 flex-1 justify-center" : ""}`}
        >
          <div className={expanded ? "min-h-0 flex-1 w-full max-w-md" : "w-40 shrink-0"}>
            <ResponsiveContainer width="100%" height={expanded ? "100%" : 160}>
              <PieChart>
                <Pie
                  data={d.race_ethnicity}
                  dataKey="value"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius="50%"
                  outerRadius="90%"
                  paddingAngle={2}
                  strokeWidth={0}
                >
                  {d.race_ethnicity.map((entry) => (
                    <Cell key={entry.label} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                  itemStyle={TOOLTIP_ITEM_STYLE}
                  labelStyle={TOOLTIP_LABEL_STYLE}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={((v: number, name: string) => [`${v}%`, name]) as any}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5">
            {d.race_ethnicity.map((entry) => (
              <div key={entry.label} className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span
                  className={`text-[var(--color-db-text-secondary)] ${expanded ? "text-sm" : "text-xs"}`}
                >
                  {entry.label}
                </span>
                <span
                  className={`font-db-mono font-medium text-[var(--color-db-text-primary)] ${expanded ? "text-sm" : "text-xs"}`}
                >
                  {entry.value}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardCard>
  );
}

/* Fallback race data for state (NC) and national benchmarks */
const RACE_STATE_FALLBACK: { label: string; value: number; color: string }[] = [
  { label: "White", value: 62.6, color: COLOR_INDIGO },
  { label: "Black", value: 20.8, color: COLOR_CYAN },
  { label: "Hispanic", value: 10.2, color: COLOR_GREEN },
  { label: "Asian", value: 3.3, color: COLOR_AMBER },
  { label: "Other", value: 3.1, color: COLOR_PURPLE },
];

const RACE_NATIONAL_FALLBACK: { label: string; value: number; color: string }[] = [
  { label: "White", value: 57.8, color: COLOR_INDIGO },
  { label: "Black", value: 12.1, color: COLOR_CYAN },
  { label: "Hispanic", value: 18.7, color: COLOR_GREEN },
  { label: "Asian", value: 5.9, color: COLOR_AMBER },
  { label: "Other", value: 5.5, color: COLOR_PURPLE },
];

const GEO_COLORS: Record<string, string> = {
  National: COLOR_BLUE,
  "State (NC)": COLOR_GREEN,
  County: COLOR_AMBER,
  Town: COLOR_RED,
  Neighborhood: COLOR_PURPLE,
};

interface RaceComparisonProps {
  demographics: DemographicData;
  context: DemographicContext;
}

function RaceComparison({ demographics }: RaceComparisonProps) {
  const expanded = useCardExpanded();
  const { contexts } = demographics;

  const radarData = useMemo(() => {
    const nationalRace =
      demographics.benchmarks?.national?.race_ethnicity ?? RACE_NATIONAL_FALLBACK;
    const stateRace = demographics.benchmarks?.state?.race_ethnicity ?? RACE_STATE_FALLBACK;
    const geoRows = [
      { name: "National", data: nationalRace },
      { name: "State (NC)", data: stateRace },
      { name: "County", data: contexts.county.race_ethnicity },
      { name: "Town", data: contexts.town.race_ethnicity },
      { name: "Neighborhood", data: contexts.neighborhood.race_ethnicity },
    ];

    const raceLabels = ["White", "Black", "Hispanic", "Asian", "Other"];
    return raceLabels.map((race) => {
      const obj: Record<string, string | number> = { race };
      for (const row of geoRows) {
        const entry = row.data.find((d) => d.label === race);
        obj[row.name] = entry?.value ?? 0;
      }
      return obj;
    });
  }, [contexts, demographics.benchmarks]);

  const geoKeys = ["National", "State (NC)", "County", "Town", "Neighborhood"];

  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Race by Geography
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 280}>
            <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
              <PolarGrid stroke="var(--color-db-border, #2E3553)" />
              <PolarAngleAxis
                dataKey="race"
                tick={{
                  fill: "var(--color-db-text-secondary, #9BA3BF)",
                  fontSize: expanded ? 14 : 11,
                }}
              />
              <PolarRadiusAxis
                tick={{
                  fill: "var(--color-db-text-secondary, #9BA3BF)",
                  fontSize: expanded ? 13 : 10,
                }}
                tickFormatter={(v: number) => `${v}%`}
                domain={[0, 80]}
              />
              {geoKeys.map((key) => (
                <Radar
                  key={key}
                  name={key}
                  dataKey={key}
                  stroke={GEO_COLORS[key]}
                  fill={GEO_COLORS[key]}
                  fillOpacity={0.05}
                  strokeWidth={expanded ? 2 : 1.5}
                />
              ))}
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number, name: string) => [`${v}%`, name]) as any}
              />
              <Legend
                iconType="circle"
                iconSize={expanded ? 10 : 8}
                wrapperStyle={expanded ? LEGEND_EXPANDED : { fontSize: 10, color: "var(--color-db-text-tertiary)" }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </DashboardCard>
  );
}

function AgeSnapshot({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const tickStyle = expanded ? AXIS_TICK_EXPANDED : AXIS_TICK_MONO;
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Age Distribution
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 170}>
            <BarChart
              data={d.age_distribution}
              margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
            >
              <XAxis
                dataKey="range"
                tick={tickStyle}
                axisLine={{ stroke: COLOR_GRID_LINE }}
                tickLine={false}
              />
              <YAxis
                tick={tickStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${v}%`}
                width={expanded ? 50 : 40}
              />
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_BAR}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number, name: string) => [`${v}%`, name]) as any}
              />
              <Bar dataKey="male" name="Male" fill={COLOR_BLUE} radius={[2, 2, 0, 0]} barSize={expanded ? 28 : 16} />
              <Bar dataKey="female" name="Female" fill={COLOR_PINK} radius={[2, 2, 0, 0]} barSize={expanded ? 28 : 16} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-1 flex justify-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: COLOR_BLUE }} />
            <span className={`text-[var(--color-db-text-tertiary)] ${expanded ? "text-sm" : "text-xs"}`}>Male</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: COLOR_PINK }} />
            <span className={`text-[var(--color-db-text-tertiary)] ${expanded ? "text-sm" : "text-xs"}`}>Female</span>
          </div>
        </div>
      </div>
    </DashboardCard>
  );
}

function IncomeSnapshot({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const maxBracketValue = Math.max(...d.income_brackets.map((b) => b.value));

  return (
    <DashboardCard expandable className="flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3
          className={`font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Income
        </h3>
        <div className="flex items-center gap-2">
          <span
            className={`font-medium text-[var(--color-db-text-secondary)] ${expanded ? "text-sm" : "text-[11px]"}`}
          >
            Median
          </span>
          <span
            className={`rounded-full font-db-mono bg-[var(--color-db-accent)]/15 px-2.5 py-0.5 font-semibold text-[var(--color-db-accent)] ${expanded ? "text-base" : "text-xs"}`}
          >
            ${d.median_income.toLocaleString()}
          </span>
        </div>
      </div>
      <div className={`flex flex-1 flex-col justify-evenly ${expanded ? "gap-4" : ""}`}>
        {d.income_brackets.map((b) => (
          <div key={b.label} className="flex items-center gap-2">
            <span
              className={`text-[var(--color-db-text-muted)] ${expanded ? "w-20 text-sm" : "w-14 text-[11px]"}`}
            >
              {b.label}
            </span>
            <div className="flex-1">
              <div
                className={`rounded-full bg-[var(--color-db-surface-alt)] ${expanded ? "h-3" : "h-1.5"}`}
              >
                <div
                  className="h-full rounded-full bg-[var(--color-db-accent)]"
                  style={{ width: `${(b.value / maxBracketValue) * 100}%` }}
                />
              </div>
            </div>
            <span
              className={`text-right font-db-mono text-[var(--color-db-text-secondary)] ${expanded ? "w-14 text-sm" : "w-10 text-[11px]"}`}
            >
              {b.value}%
            </span>
          </div>
        ))}
      </div>
    </DashboardCard>
  );
}

function OwnershipSnapshot({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  return (
    <DashboardCard expandable className="flex flex-col">
      <h3
        className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
      >
        Home Ownership
      </h3>
      <div className="flex flex-1 items-center justify-center">
        <SemiCircularGauge
          value={d.home_ownership_rate}
          label="Ownership Rate"
          size={expanded ? 320 : 140}
          suffix="%"
          showGrade={false}
          gradientStops={[
            { offset: "0%", color: "#221150" },
            { offset: "30%", color: "#5F187F" },
            { offset: "50%", color: "#B63679" },
            { offset: "70%", color: "#E8765C" },
            { offset: "100%", color: "#FCFDBF" },
          ]}
        />
      </div>
    </DashboardCard>
  );
}

/* ------------------------------------------------------------------ */
/*  Trend sub-components                                               */
/* ------------------------------------------------------------------ */

function PopulationTrend({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const tickStyle = expanded ? AXIS_TICK_EXPANDED_SM : AXIS_TICK_MONO_SM;
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Population Trend
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 180}>
            <AreaChart data={d.population_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="popGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={COLOR_INDIGO} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={COLOR_INDIGO} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="year" tick={tickStyle} axisLine={AXIS_LINE_STYLE} tickLine={false} />
              <YAxis
                tick={tickStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                width={expanded ? 50 : 35}
              />
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_LINE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number) => [v.toLocaleString(), "Population"]) as any}
              />
              <Area
                type="monotone"
                dataKey="population"
                stroke={COLOR_INDIGO}
                strokeWidth={expanded ? 3 : 2}
                fill="url(#popGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </DashboardCard>
  );
}

const FUNNEL_COLORS = ["#FCFDBF", "#E8765C", "#B63679", "#5F187F", "#221150", "#0D0829"];

const RACE_COLORS = {
  white: COLOR_INDIGO,
  black: COLOR_CYAN,
  hispanic: COLOR_GREEN,
  asian: COLOR_AMBER,
  other: COLOR_PURPLE,
};

function RaceTrend({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const tickStyle = expanded ? AXIS_TICK_EXPANDED_SM : AXIS_TICK_MONO_SM;
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Race & Ethnicity Trend
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 200}>
            <AreaChart
              data={d.race_ethnicity_trend}
              margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
              stackOffset="expand"
            >
              <XAxis dataKey="year" tick={tickStyle} axisLine={AXIS_LINE_STYLE} tickLine={false} />
              <YAxis
                tick={tickStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                width={expanded ? 50 : 40}
              />
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number, name: string) => [`${v.toFixed(1)}%`, name]) as any}
              />
              <Area type="monotone" dataKey="white" name="White" stackId="1" stroke={RACE_COLORS.white} fill={RACE_COLORS.white} fillOpacity={0.6} />
              <Area type="monotone" dataKey="black" name="Black" stackId="1" stroke={RACE_COLORS.black} fill={RACE_COLORS.black} fillOpacity={0.6} />
              <Area type="monotone" dataKey="hispanic" name="Hispanic" stackId="1" stroke={RACE_COLORS.hispanic} fill={RACE_COLORS.hispanic} fillOpacity={0.6} />
              <Area type="monotone" dataKey="asian" name="Asian" stackId="1" stroke={RACE_COLORS.asian} fill={RACE_COLORS.asian} fillOpacity={0.6} />
              <Area type="monotone" dataKey="other" name="Other" stackId="1" stroke={RACE_COLORS.other} fill={RACE_COLORS.other} fillOpacity={0.6} />
              <Legend
                iconType="circle"
                iconSize={expanded ? 10 : 8}
                wrapperStyle={expanded ? LEGEND_EXPANDED : LEGEND_DEFAULT}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </DashboardCard>
  );
}

const AGE_COLORS = {
  under18: COLOR_INDIGO,
  age18_22: COLOR_CYAN,
  age23_29: COLOR_GREEN,
  age30_39: COLOR_AMBER,
  age40_49: COLOR_RED,
  age50_64: COLOR_BLUE,
  age65plus: COLOR_PURPLE,
};

function AgeTrend({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const tickStyle = expanded ? AXIS_TICK_EXPANDED_SM : AXIS_TICK_MONO_SM;
  const sw = expanded ? 3 : 2;
  const dotR = expanded ? 5 : 3;
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Age Distribution Trend
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 200}>
            <LineChart
              data={d.age_distribution_trend}
              margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
            >
              <XAxis dataKey="year" tick={tickStyle} axisLine={AXIS_LINE_STYLE} tickLine={false} />
              <YAxis
                tick={tickStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${v}%`}
                width={expanded ? 50 : 40}
              />
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_LINE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number, name: string) => [`${v}%`, name]) as any}
              />
              <Line type="monotone" dataKey="under18" name="Under 18" stroke={AGE_COLORS.under18} strokeWidth={sw} dot={{ r: dotR }} />
              <Line type="monotone" dataKey="age18_22" name="18–22" stroke={AGE_COLORS.age18_22} strokeWidth={sw} dot={{ r: dotR }} />
              <Line type="monotone" dataKey="age23_29" name="23–29" stroke={AGE_COLORS.age23_29} strokeWidth={sw} dot={{ r: dotR }} />
              <Line type="monotone" dataKey="age30_39" name="30–39" stroke={AGE_COLORS.age30_39} strokeWidth={sw} dot={{ r: dotR }} />
              <Line type="monotone" dataKey="age40_49" name="40–49" stroke={AGE_COLORS.age40_49} strokeWidth={sw} dot={{ r: dotR }} />
              <Line type="monotone" dataKey="age50_64" name="50–64" stroke={AGE_COLORS.age50_64} strokeWidth={sw} dot={{ r: dotR }} />
              <Line type="monotone" dataKey="age65plus" name="65+" stroke={AGE_COLORS.age65plus} strokeWidth={sw} dot={{ r: dotR }} />
              <Legend
                iconType="circle"
                iconSize={expanded ? 10 : 8}
                wrapperStyle={expanded ? LEGEND_EXPANDED : LEGEND_DEFAULT}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </DashboardCard>
  );
}

function MedianAgeTrend({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const tickStyle = expanded ? AXIS_TICK_EXPANDED_SM : AXIS_TICK_MONO_SM;
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Median Age Trend
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 180}>
            <AreaChart data={d.median_age_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="medianAgeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={COLOR_BLUE} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={COLOR_BLUE} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="year" tick={tickStyle} axisLine={AXIS_LINE_STYLE} tickLine={false} />
              <YAxis tick={tickStyle} axisLine={false} tickLine={false} width={expanded ? 50 : 35} />
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_LINE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number) => [v.toFixed(1), "Median Age"]) as any}
              />
              <Area
                type="monotone"
                dataKey="median_age"
                stroke={COLOR_BLUE}
                strokeWidth={expanded ? 3 : 2}
                fill="url(#medianAgeGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </DashboardCard>
  );
}

function IncomeTrend({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const tickStyle = expanded ? AXIS_TICK_EXPANDED_SM : AXIS_TICK_MONO_SM;
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Median Income Trend
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 180}>
            <AreaChart data={d.income_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={COLOR_BLUE} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={COLOR_BLUE} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="year" tick={tickStyle} axisLine={AXIS_LINE_STYLE} tickLine={false} />
              <YAxis
                tick={tickStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                width={expanded ? 55 : 45}
              />
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_LINE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number) => [`$${v.toLocaleString()}`, "Median Income"]) as any}
              />
              <Area
                type="monotone"
                dataKey="median_income"
                stroke={COLOR_BLUE}
                strokeWidth={expanded ? 3 : 2}
                fill="url(#incomeGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </DashboardCard>
  );
}

function OwnershipTrend({ d }: SubTabProps) {
  const expanded = useCardExpanded();
  const tickStyle = expanded ? AXIS_TICK_EXPANDED_SM : AXIS_TICK_MONO_SM;
  return (
    <DashboardCard expandable>
      <div className={expanded ? "flex h-full flex-col" : ""}>
        <h3
          className={`mb-3 font-semibold text-[var(--color-db-text-primary)] ${expanded ? "text-lg" : "text-sm"}`}
        >
          Home Ownership Trend
        </h3>
        <div className={expanded ? "min-h-0 flex-1" : ""}>
          <ResponsiveContainer width="100%" height={expanded ? "100%" : 180}>
            <LineChart
              data={d.home_ownership_trend}
              margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
            >
              <XAxis dataKey="year" tick={tickStyle} axisLine={AXIS_LINE_STYLE} tickLine={false} />
              <YAxis
                tick={tickStyle}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${v}%`}
                domain={[50, 100]}
                width={expanded ? 50 : 40}
              />
              <Tooltip
                contentStyle={expanded ? TOOLTIP_EXPANDED : TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                cursor={CURSOR_LINE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number) => [`${v}%`, "Ownership Rate"]) as any}
              />
              <Line
                type="monotone"
                dataKey="ownership_rate"
                name="Ownership Rate"
                stroke={COLOR_INDIGO}
                strokeWidth={expanded ? 3 : 2}
                dot={{ r: expanded ? 6 : 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </DashboardCard>
  );
}

export default DemographicsTab;
