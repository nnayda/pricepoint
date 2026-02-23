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
  CartesianGrid,
  AreaChart,
  Area,
  LineChart,
  Line,
  Legend,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from "recharts";
import { GeoJSON, useMap, useMapEvents } from "react-leaflet";
import type { Layer } from "leaflet";
import type { DashboardData, DemographicContext, DemographicSubTab, DemographicData } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import ChoroplethLegend from "../maps/ChoroplethLegend";
import SemiCircularGauge from "../charts/SemiCircularGauge";
import { MOCK_CHOROPLETH_MAP } from "../../../data/mockDemographicGeo";
import { getChoroplethStyle, getTooltipText, getLegendConfig } from "../../../utils/choroplethColors";
import { useChoropleth, type Bbox } from "../../../hooks/useChoropleth";
import {
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  AXIS_TICK_MONO,
  AXIS_TICK_MONO_SM,
  AXIS_LINE_STYLE,
  GRID_STYLE,
  CURSOR_BAR,
  CURSOR_LINE_CYAN,
  CURSOR_LINE,
  COLOR_INDIGO,
  COLOR_CYAN,
  COLOR_GREEN,
  COLOR_AMBER,
  COLOR_RED,
  COLOR_BLUE,
  COLOR_PURPLE,
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
  const [mapBbox, setMapBbox] = useState<Bbox | null>(null);

  const d = demographics.contexts[context];

  const initialChoropleth =
    demographics.choropleth?.[context] ?? MOCK_CHOROPLETH_MAP[context];

  const { data: choroplethData } = useChoropleth(
    context,
    mapBbox,
    property.lat,
    property.lon,
    initialChoropleth,
  );

  // Key must change when data, context, or subTab changes to force GeoJSON remount
  const choroplethKey = useMemo(
    () => `choropleth-${context}-${subTab}-${choroplethData.features.length}`,
    [context, subTab, choroplethData],
  );
  const legendConfig = useMemo(() => getLegendConfig(subTab), [subTab]);

  const handleBoundsChange = useCallback((bbox: Bbox) => {
    setMapBbox(bbox);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* Context pill selector — right-aligned */}
      <div className="flex justify-end">
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

      {/* Two-column layout: charts left, map right */}
      <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
        {/* Left column — sub-tabs + snapshot + trend */}
        <div className="flex flex-col gap-4">
          {/* Sub-tab pills */}
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

          {/* Snapshot card */}
          {subTab === "population" && <PopulationSnapshot d={d} />}
          {subTab === "race" && <RaceSnapshot d={d} />}
          {subTab === "age" && <AgeSnapshot d={d} />}
          {subTab === "income" && <IncomeSnapshot d={d} />}
          {subTab === "ownership" && <OwnershipSnapshot d={d} />}

          {/* Race comparison radial chart */}
          {subTab === "race" && (
            <RaceComparison demographics={demographics} context={context} />
          )}

          {/* Trend card */}
          {subTab === "population" && <PopulationTrend d={d} />}
          {subTab === "race" && <RaceTrend d={d} />}
          {subTab === "age" && <AgeTrend d={d} />}
          {subTab === "income" && <IncomeTrend d={d} />}
          {subTab === "ownership" && <OwnershipTrend d={d} />}
        </div>

        {/* Right column — map (sticky) */}
        <div className="lg:sticky lg:top-[calc(64px+36px+12px)] lg:h-[calc(100vh-64px-36px-44px-40px-24px)]">
          <DashboardCard className="flex h-full flex-col">
            <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
              Demographics Map
            </h3>
            <div className="flex-1">
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
                minHeight="400px"
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
                  style={(feature) => getChoroplethStyle(feature, subTab)}
                  onEachFeature={(feature: GeoJSON.Feature, layer: Layer) => {
                    const text = getTooltipText(
                      (feature.properties ?? {}) as Record<string, unknown>,
                      subTab,
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

function PopulationSnapshot({ d }: SubTabProps) {
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Population
      </h3>
      <div className="flex flex-col items-center gap-2 py-4">
        <span
          className="rounded-full font-db-mono px-4 py-1.5 text-lg font-semibold"
          style={{ backgroundColor: `${COLOR_CYAN}26`, color: COLOR_CYAN }}
        >
          {d.population.toLocaleString()}
        </span>
        <span className="text-xs text-[var(--color-db-text-tertiary)]">
          Current estimated population
        </span>
      </div>
    </DashboardCard>
  );
}

function RaceSnapshot({ d }: SubTabProps) {
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Race & Ethnicity
      </h3>
      <div className="flex flex-col items-center gap-4">
        <div className="w-40 shrink-0">
          <ResponsiveContainer width="100%" height={160}>
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
                contentStyle={TOOLTIP_CONTENT_STYLE}
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
              <span className="text-xs text-[var(--color-db-text-secondary)]">
                {entry.label}
              </span>
              <span className="font-db-mono text-xs font-medium text-[var(--color-db-text-primary)]">
                {entry.value}%
              </span>
            </div>
          ))}
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

const GEO_LABELS = ["National", "State (NC)", "County", "Town", "Neighborhood", "Block Group", "Subdivision"] as const;

interface RaceComparisonProps {
  demographics: DemographicData;
  context: DemographicContext;
}

function RaceComparison({ demographics, context }: RaceComparisonProps) {
  const { contexts } = demographics;

  const geoRows = useMemo(() => {
    const nationalRace = demographics.benchmarks?.national?.race_ethnicity ?? RACE_NATIONAL_FALLBACK;
    const stateRace = demographics.benchmarks?.state?.race_ethnicity ?? RACE_STATE_FALLBACK;
    const rows = [
      { name: "National", data: nationalRace },
      { name: "State (NC)", data: stateRace },
      { name: "County", data: contexts.county.race_ethnicity },
      { name: "Town", data: contexts.town.race_ethnicity },
      { name: "Neighborhood", data: contexts.neighborhood.race_ethnicity },
      { name: "Block Group", data: contexts.block_group.race_ethnicity },
      { name: "Subdivision", data: contexts.subdivision.race_ethnicity },
    ];
    // Build radial bar data: one entry per geography, one RadialBar per race
    return rows.map((row) => {
      const obj: Record<string, string | number> = { name: row.name };
      for (const entry of row.data) {
        obj[entry.label] = entry.value;
      }
      return obj;
    });
  }, [contexts, demographics.benchmarks]);

  const raceKeys = ["White", "Black", "Hispanic", "Asian", "Other"];
  const raceColors: Record<string, string> = {
    White: COLOR_INDIGO,
    Black: COLOR_CYAN,
    Hispanic: COLOR_GREEN,
    Asian: COLOR_AMBER,
    Other: COLOR_PURPLE,
  };

  // Highlight the active context row
  const activeGeoName: Record<DemographicContext, string> = {
    subdivision: "Subdivision",
    block_group: "Block Group",
    neighborhood: "Neighborhood",
    town: "Town",
    county: "County",
  };

  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Race by Geography
      </h3>
      <div className="flex items-center gap-2">
        {/* Radial bar chart */}
        <div className="flex-1">
          <ResponsiveContainer width="100%" height={240}>
            <RadialBarChart
              data={geoRows}
              cx="50%"
              cy="50%"
              innerRadius="18%"
              outerRadius="95%"
              startAngle={90}
              endAngle={-270}
              barGap={2}
            >
              <PolarAngleAxis type="number" domain={[0, 100]} tick={false} axisLine={false} />
              {raceKeys.map((key) => (
                <RadialBar
                  key={key}
                  dataKey={key}
                  stackId="race"
                  fill={raceColors[key]}
                  cornerRadius={2}
                  background={{ fill: "var(--color-db-surface-alt)", opacity: 0.3 }}
                />
              ))}
              <Tooltip
                contentStyle={TOOLTIP_CONTENT_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={((v: number, name: string) => [`${v}%`, name]) as any}
              />
            </RadialBarChart>
          </ResponsiveContainer>
        </div>
        {/* Geography labels — aligned to rings from bottom (outer) to top (inner) */}
        <div className="flex flex-col justify-between gap-1.5 py-3">
          {[...GEO_LABELS].reverse().map((label) => (
            <span
              key={label}
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium whitespace-nowrap transition-colors ${
                label === activeGeoName[context]
                  ? "bg-[var(--color-db-accent)]/20 text-[var(--color-db-accent)]"
                  : "text-[var(--color-db-text-tertiary)]"
              }`}
            >
              {label}
            </span>
          ))}
        </div>
      </div>
      {/* Legend */}
      <div className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1">
        {raceKeys.map((key) => (
          <div key={key} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: raceColors[key] }} />
            <span className="text-[10px] text-[var(--color-db-text-tertiary)]">{key}</span>
          </div>
        ))}
      </div>
    </DashboardCard>
  );
}

function AgeSnapshot({ d }: SubTabProps) {
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Age Distribution
      </h3>
      <ResponsiveContainer width="100%" height={170}>
        <BarChart
          data={d.age_distribution}
          margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
        >
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis
            dataKey="range"
            tick={AXIS_TICK_MONO}
            axisLine={{ stroke: COLOR_GRID_LINE }}
            tickLine={false}
          />
          <YAxis
            tick={AXIS_TICK_MONO}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${v}%`}
            width={40}
          />
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={CURSOR_BAR}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={((v: number, name: string) => [`${v}%`, name]) as any}
          />
          <Bar dataKey="male" name="Male" fill={COLOR_INDIGO} radius={[2, 2, 0, 0]} barSize={16} />
          <Bar dataKey="female" name="Female" fill={COLOR_CYAN} radius={[2, 2, 0, 0]} barSize={16} />
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-1 flex justify-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: COLOR_INDIGO }} />
          <span className="text-xs text-[var(--color-db-text-tertiary)]">Male</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: COLOR_CYAN }} />
          <span className="text-xs text-[var(--color-db-text-tertiary)]">Female</span>
        </div>
      </div>
    </DashboardCard>
  );
}

function IncomeSnapshot({ d }: SubTabProps) {
  return (
    <DashboardCard className="flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">Income</h3>
        <span className="group relative rounded-full font-db-mono bg-[var(--color-db-accent)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--color-db-accent)]">
          ${d.median_income.toLocaleString()}
          <span className="pointer-events-none absolute bottom-full left-1/2 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-md bg-[var(--color-db-surface-alt)] px-2.5 py-1 text-[11px] font-medium text-[var(--color-db-text-secondary)] opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
            Median household income
          </span>
        </span>
      </div>
      <div className="flex flex-1 flex-col justify-evenly">
        {d.income_brackets.map((b) => (
          <div key={b.label} className="flex items-center gap-2">
            <span className="w-14 text-[11px] text-[var(--color-db-text-muted)]">
              {b.label}
            </span>
            <div className="flex-1">
              <div className="h-1.5 rounded-full bg-[var(--color-db-surface-alt)]">
                <div
                  className="h-full rounded-full bg-[var(--color-db-accent)]"
                  style={{ width: `${(b.value / 25) * 100}%` }}
                />
              </div>
            </div>
            <span className="w-10 text-right font-db-mono text-[11px] text-[var(--color-db-text-secondary)]">
              {b.value}%
            </span>
          </div>
        ))}
      </div>
    </DashboardCard>
  );
}

function OwnershipSnapshot({ d }: SubTabProps) {
  return (
    <DashboardCard className="flex flex-col">
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Home Ownership
      </h3>
      <div className="flex flex-1 items-center justify-center">
        <SemiCircularGauge
          value={d.home_ownership_rate}
          label="Ownership Rate"
          color="var(--color-db-green)"
          size={140}
          suffix="%"
          showGrade={false}
        />
      </div>
    </DashboardCard>
  );
}

/* ------------------------------------------------------------------ */
/*  Trend sub-components                                               */
/* ------------------------------------------------------------------ */

function PopulationTrend({ d }: SubTabProps) {
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Population Trend
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={d.population_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <defs>
            <linearGradient id="popGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLOR_CYAN} stopOpacity={0.3} />
              <stop offset="100%" stopColor={COLOR_CYAN} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis dataKey="year" tick={AXIS_TICK_MONO_SM} axisLine={AXIS_LINE_STYLE} tickLine={false} />
          <YAxis
            tick={AXIS_TICK_MONO_SM}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
            width={35}
          />
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={CURSOR_LINE_CYAN}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={((v: number) => [v.toLocaleString(), "Population"]) as any}
          />
          <Area type="monotone" dataKey="population" stroke={COLOR_CYAN} strokeWidth={2} fill="url(#popGradient)" />
        </AreaChart>
      </ResponsiveContainer>
    </DashboardCard>
  );
}

const RACE_COLORS = {
  white: COLOR_INDIGO,
  black: COLOR_CYAN,
  hispanic: COLOR_GREEN,
  asian: COLOR_AMBER,
  other: COLOR_PURPLE,
};

function RaceTrend({ d }: SubTabProps) {
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Race & Ethnicity Trend
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={d.race_ethnicity_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }} stackOffset="expand">
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis dataKey="year" tick={AXIS_TICK_MONO_SM} axisLine={AXIS_LINE_STYLE} tickLine={false} />
          <YAxis
            tick={AXIS_TICK_MONO_SM}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
            width={40}
          />
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={((v: number) => [`${(v * 100).toFixed(1)}%`]) as any}
          />
          <Area type="monotone" dataKey="white" name="White" stackId="1" stroke={RACE_COLORS.white} fill={RACE_COLORS.white} fillOpacity={0.6} />
          <Area type="monotone" dataKey="black" name="Black" stackId="1" stroke={RACE_COLORS.black} fill={RACE_COLORS.black} fillOpacity={0.6} />
          <Area type="monotone" dataKey="hispanic" name="Hispanic" stackId="1" stroke={RACE_COLORS.hispanic} fill={RACE_COLORS.hispanic} fillOpacity={0.6} />
          <Area type="monotone" dataKey="asian" name="Asian" stackId="1" stroke={RACE_COLORS.asian} fill={RACE_COLORS.asian} fillOpacity={0.6} />
          <Area type="monotone" dataKey="other" name="Other" stackId="1" stroke={RACE_COLORS.other} fill={RACE_COLORS.other} fillOpacity={0.6} />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11, color: "var(--color-db-text-tertiary)" }}
          />
        </AreaChart>
      </ResponsiveContainer>
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
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Age Distribution Trend
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={d.age_distribution_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis dataKey="year" tick={AXIS_TICK_MONO_SM} axisLine={AXIS_LINE_STYLE} tickLine={false} />
          <YAxis
            tick={AXIS_TICK_MONO_SM}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${v}%`}
            width={40}
          />
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={CURSOR_LINE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={((v: number, name: string) => [`${v}%`, name]) as any}
          />
          <Line type="monotone" dataKey="under18" name="Under 18" stroke={AGE_COLORS.under18} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="age18_22" name="18–22" stroke={AGE_COLORS.age18_22} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="age23_29" name="23–29" stroke={AGE_COLORS.age23_29} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="age30_39" name="30–39" stroke={AGE_COLORS.age30_39} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="age40_49" name="40–49" stroke={AGE_COLORS.age40_49} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="age50_64" name="50–64" stroke={AGE_COLORS.age50_64} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="age65plus" name="65+" stroke={AGE_COLORS.age65plus} strokeWidth={2} dot={{ r: 3 }} />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11, color: "var(--color-db-text-tertiary)" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </DashboardCard>
  );
}

function IncomeTrend({ d }: SubTabProps) {
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Median Income Trend
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={d.income_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <defs>
            <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLOR_GREEN} stopOpacity={0.3} />
              <stop offset="100%" stopColor={COLOR_GREEN} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis dataKey="year" tick={AXIS_TICK_MONO_SM} axisLine={AXIS_LINE_STYLE} tickLine={false} />
          <YAxis
            tick={AXIS_TICK_MONO_SM}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
            width={45}
          />
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={CURSOR_LINE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={((v: number) => [`$${v.toLocaleString()}`, "Median Income"]) as any}
          />
          <Area type="monotone" dataKey="median_income" stroke={COLOR_GREEN} strokeWidth={2} fill="url(#incomeGradient)" />
        </AreaChart>
      </ResponsiveContainer>
    </DashboardCard>
  );
}

function OwnershipTrend({ d }: SubTabProps) {
  return (
    <DashboardCard>
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
        Home Ownership Trend
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={d.home_ownership_trend} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid {...GRID_STYLE} vertical={false} />
          <XAxis dataKey="year" tick={AXIS_TICK_MONO_SM} axisLine={AXIS_LINE_STYLE} tickLine={false} />
          <YAxis
            tick={AXIS_TICK_MONO_SM}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${v}%`}
            domain={[50, 100]}
            width={40}
          />
          <Tooltip
            contentStyle={TOOLTIP_CONTENT_STYLE}
            itemStyle={TOOLTIP_ITEM_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={CURSOR_LINE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={((v: number) => [`${v}%`, "Ownership Rate"]) as any}
          />
          <Line type="monotone" dataKey="ownership_rate" name="Ownership Rate" stroke={COLOR_GREEN} strokeWidth={2} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </DashboardCard>
  );
}

export default DemographicsTab;
