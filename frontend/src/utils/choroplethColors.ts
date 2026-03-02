import type { DemographicContext, DemographicSubTab } from "../types";
import type { ExpressionSpecification } from "maplibre-gl";

/** Actual min/max range computed from visible GeoJSON features. */
export interface DataRange {
  min: number;
  max: number;
}

/** Race → color mapping (matches chart tokens) */
const RACE_COLORS: Record<string, string> = {
  White: "#6366f1",
  Black: "#22d3ee",
  Hispanic: "#22c55e",
  Asian: "#f59e0b",
  Other: "#a855f7",
  Unknown: "#6b7280",
};

/* ── Sequential / diverging color ramps ── */

const MAGMA_RAMP = ["#221150", "#5F187F", "#B63679", "#E8765C", "#FCFDBF"];

function interpolateRamp(ramp: string[], t: number): string {
  const idx = Math.min(Math.floor(t * (ramp.length - 1)), ramp.length - 2);
  return ramp[Math.min(idx + (t * (ramp.length - 1) - idx >= 0.5 ? 1 : 0), ramp.length - 1)];
}

function quantilePosition(value: number, min: number, max: number): number {
  if (max <= min) return 0.5;
  return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

/** Map race filter key to the property name on feature props */
const RACE_PCT_KEY: Record<string, string> = {
  white: "pct_white",
  black: "pct_black",
  hispanic: "pct_hispanic",
  asian: "pct_asian",
  other: "pct_other",
};

/** Map race filter key to the race's display color */
const RACE_FILTER_COLOR: Record<string, string> = {
  white: RACE_COLORS.White,
  black: RACE_COLORS.Black,
  hispanic: RACE_COLORS.Hispanic,
  asian: RACE_COLORS.Asian,
  other: RACE_COLORS.Other,
};

/** Property key used per subTab for numeric choropleth value. */
const SUBTAB_PROP_KEY: Record<string, string> = {
  population: "population",
  income: "median_income",
  age: "median_age",
  ownership: "home_ownership_rate",
};

/** Hardcoded fallback ranges (used when no DataRange is supplied). */
const FALLBACK_RANGES: Record<string, { min: number; max: number }> = {
  population: { min: 1000, max: 10000 },
  income: { min: 30000, max: 150000 },
  age: { min: 25, max: 55 },
  ownership: { min: 30, max: 90 },
};

/**
 * Scan GeoJSON features and return the actual min/max for the given subTab.
 * Returns `null` for the race subTab (already normalised 0-100%).
 */
export function computeDataRange(
  features: GeoJSON.Feature[],
  subTab: DemographicSubTab,
): DataRange | null {
  if (subTab === "race") return null;

  const key = SUBTAB_PROP_KEY[subTab];
  if (!key) return null;

  let min = Infinity;
  let max = -Infinity;
  for (const f of features) {
    const v = f.properties?.[key];
    if (typeof v !== "number" || !isFinite(v)) continue;
    if (v < min) min = v;
    if (v > max) max = v;
  }

  // No valid numeric values — return safe fallback
  if (!isFinite(min) || !isFinite(max)) return { min: 0, max: 1 };

  // All identical — add small epsilon so legend labels can differ
  if (min === max) {
    const eps = Math.abs(min) * 0.01 || 1;
    return { min: min - eps, max: max + eps };
  }

  return { min, max };
}


/**
 * Return a Leaflet-compatible style object for a choropleth feature.
 */
export function getChoroplethStyle(
  feature: GeoJSON.Feature | undefined,
  subTab: DemographicSubTab,
  raceFilter?: string,
  dataRange?: DataRange | null,
): Record<string, string | number> {
  const props = feature?.properties ?? {};
  const isHome = props.is_home === true;

  let fillColor: string;

  switch (subTab) {
    case "population": {
      const range = dataRange ?? FALLBACK_RANGES.population;
      const t = quantilePosition(props.population ?? 0, range.min, range.max);
      fillColor = interpolateRamp(MAGMA_RAMP, t);
      break;
    }
    case "income": {
      const range = dataRange ?? FALLBACK_RANGES.income;
      const t = quantilePosition(props.median_income ?? 0, range.min, range.max);
      fillColor = interpolateRamp(MAGMA_RAMP, t);
      break;
    }
    case "age": {
      const range = dataRange ?? FALLBACK_RANGES.age;
      const age = props.median_age ?? 38;
      const t = quantilePosition(age, range.min, range.max);
      fillColor = interpolateRamp(MAGMA_RAMP, t);
      break;
    }
    case "ownership": {
      const range = dataRange ?? FALLBACK_RANGES.ownership;
      const rate = props.home_ownership_rate ?? 65;
      const t = quantilePosition(rate, range.min, range.max);
      fillColor = interpolateRamp(MAGMA_RAMP, t);
      break;
    }
    case "race": {
      if (raceFilter && raceFilter !== "all") {
        const pctKey = RACE_PCT_KEY[raceFilter];
        const pct = (pctKey ? (props[pctKey] as number) : 0) ?? 0;
        fillColor = RACE_FILTER_COLOR[raceFilter] ?? RACE_COLORS.Unknown;
        return {
          fillColor,
          fillOpacity: 0.1 + (pct / 100) * 0.6,
          color: isHome ? "#6366f1" : "#475569",
          weight: isHome ? 3 : 1,
        };
      }
      const race = props.dominant_race ?? "Unknown";
      const pct = props.dominant_race_pct ?? 0;
      fillColor = RACE_COLORS[race] ?? RACE_COLORS.Unknown;
      return {
        fillColor,
        fillOpacity: 0.2 + (pct / 100) * 0.5,
        color: isHome ? "#6366f1" : "#475569",
        weight: isHome ? 3 : 1,
      };
    }
    default: {
      fillColor = "#e5e7eb";
    }
  }

  return {
    fillColor,
    fillOpacity: isHome ? 0.4 : 0.3,
    color: isHome ? "#6366f1" : "#475569",
    weight: isHome ? 3 : 1,
  };
}

/** Contexts where the name is just a geoid — don't display it. */
const NAMELESS_CONTEXTS = new Set<DemographicContext>(["block_group", "neighborhood"]);

/** Map race filter key to display label */
const RACE_FILTER_LABEL: Record<string, string> = {
  white: "White",
  black: "Black",
  hispanic: "Hispanic",
  asian: "Asian",
  other: "Other",
};

/**
 * Format a tooltip string for the hovered feature.
 */
export function getTooltipText(
  props: Record<string, unknown>,
  subTab: DemographicSubTab,
  context?: DemographicContext,
  raceFilter?: string,
): string {
  const rawName = (props.name as string) ?? (props.geoid as string) ?? "";
  const name = context && NAMELESS_CONTEXTS.has(context) ? "" : rawName;
  const prefix = name ? `${name}\n` : "";
  switch (subTab) {
    case "population":
      return `${prefix}Pop: ${((props.population as number) ?? 0).toLocaleString()}`;
    case "income":
      return `${prefix}Median Income: $${((props.median_income as number) ?? 0).toLocaleString()}`;
    case "age":
      return `${prefix}Median Age: ${props.median_age ?? 0}`;
    case "ownership":
      return `${prefix}Ownership: ${props.home_ownership_rate ?? 0}%`;
    case "race": {
      if (raceFilter && raceFilter !== "all") {
        const pctKey = RACE_PCT_KEY[raceFilter];
        const pct = pctKey ? (props[pctKey] as number) ?? 0 : 0;
        const label = RACE_FILTER_LABEL[raceFilter] ?? raceFilter;
        return `${prefix}${label}: ${pct}%`;
      }
      return `${prefix}${props.dominant_race ?? "Unknown"}: ${props.dominant_race_pct ?? 0}%`;
    }
    default:
      return name;
  }
}

export interface LegendConfig {
  type: "sequential" | "diverging" | "categorical";
  title: string;
  colors: string[];
  labels: string[];
}

/**
 * Legend config that matches the MapLibre fill-color expressions in DemographicsTab.
 *
 * Population / Age / Race: indigo ramp with varying opacity
 * Income / Ownership: red → yellow → green
 */
export function getLegendConfig(
  subTab: DemographicSubTab,
  raceFilter?: string,
): LegendConfig {
  switch (subTab) {
    case "population":
      return {
        type: "sequential",
        title: "Population",
        colors: [
          "rgba(99,102,241,0.05)",
          "rgba(99,102,241,0.25)",
          "rgba(99,102,241,0.4)",
          "rgba(99,102,241,0.55)",
          "rgba(99,102,241,0.7)",
        ],
        labels: ["0", "20k+"],
      };
    case "income":
      return {
        type: "sequential",
        title: "Median Income",
        colors: [
          "rgba(248,113,113,0.3)",
          "rgba(251,191,36,0.3)",
          "rgba(52,211,153,0.5)",
        ],
        labels: ["$0", "$100k+"],
      };
    case "age":
      return {
        type: "sequential",
        title: "Median Age",
        colors: [
          "rgba(99,102,241,0.05)",
          "rgba(99,102,241,0.25)",
          "rgba(99,102,241,0.4)",
          "rgba(99,102,241,0.55)",
          "rgba(99,102,241,0.7)",
        ],
        labels: ["20", "55+"],
      };
    case "ownership":
      return {
        type: "sequential",
        title: "Ownership Rate",
        colors: [
          "rgba(248,113,113,0.3)",
          "rgba(251,191,36,0.3)",
          "rgba(52,211,153,0.5)",
        ],
        labels: ["0%", "100%"],
      };
    case "race": {
      if (raceFilter && raceFilter !== "all") {
        const label = RACE_FILTER_LABEL[raceFilter] ?? raceFilter;
        const hex = RACE_FILTER_COLOR[raceFilter] ?? "#6b7280";
        return {
          type: "sequential",
          title: `% ${label}`,
          colors: [
            `${hex}0d`,
            `${hex}40`,
            `${hex}66`,
            `${hex}8c`,
            `${hex}b3`,
          ],
          labels: ["0%", "100%"],
        };
      }
      return {
        type: "categorical",
        title: "Dominant Race",
        colors: [
          RACE_COLORS.White,
          RACE_COLORS.Black,
          RACE_COLORS.Hispanic,
          RACE_COLORS.Asian,
          RACE_COLORS.Other,
        ],
        labels: ["White", "Black", "Hispanic", "Asian", "Other"],
      };
    }
  }
}

/* ── MapLibre vector-tile expressions ── */

/** Map race filter key to the tile property name */
const RACE_TILE_KEY: Record<string, string> = {
  white: "pct_white",
  black: "pct_black",
  hispanic: "pct_hispanic",
  asian: "pct_asian",
  other: "pct_other",
};

/** Property key used per subTab for numeric choropleth value (vector tiles). */
const SUBTAB_TILE_KEY: Record<string, string> = {
  population: "population",
  income: "median_income",
  age: "median_age",
  ownership: "home_ownership_rate",
};

/**
 * MapLibre fill-color expression for the demographics choropleth layer.
 *
 * Race/All: colors each region by its `dominant_race` property.
 * Race/filtered: uses the specific race color.
 * Other subTabs: sequential ramps.
 */
export function getChoroplethColorExpression(
  subTab: DemographicSubTab,
  raceFilter: string,
): ExpressionSpecification {
  if (subTab === "race") {
    if (raceFilter && raceFilter !== "all") {
      // Single-race filter — use that race's color (opacity handled separately)
      const color = RACE_FILTER_COLOR[raceFilter] ?? RACE_COLORS.Unknown;
      return color as unknown as ExpressionSpecification;
    }
    // All races — color by dominant_race
    return [
      "case",
      ["==", ["coalesce", ["get", "dominant_race"], ""], "White"],
      RACE_COLORS.White,
      ["==", ["coalesce", ["get", "dominant_race"], ""], "Black"],
      RACE_COLORS.Black,
      ["==", ["coalesce", ["get", "dominant_race"], ""], "Hispanic"],
      RACE_COLORS.Hispanic,
      ["==", ["coalesce", ["get", "dominant_race"], ""], "Asian"],
      RACE_COLORS.Asian,
      ["==", ["coalesce", ["get", "dominant_race"], ""], "Other"],
      RACE_COLORS.Other,
      RACE_COLORS.Unknown,
    ] as ExpressionSpecification;
  }

  const metric = SUBTAB_TILE_KEY[subTab] ?? "population";

  if (subTab === "population") {
    return [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", metric], 0],
      0,
      "rgba(99,102,241,0.05)",
      5000,
      "rgba(99,102,241,0.4)",
      20000,
      "rgba(99,102,241,0.7)",
    ];
  }
  if (subTab === "income") {
    return [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", metric], 0],
      0,
      "rgba(248,113,113,0.3)",
      50000,
      "rgba(251,191,36,0.3)",
      100000,
      "rgba(52,211,153,0.5)",
    ];
  }
  if (subTab === "age") {
    return [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", metric], 0],
      20,
      "rgba(99,102,241,0.05)",
      38,
      "rgba(99,102,241,0.4)",
      55,
      "rgba(99,102,241,0.7)",
    ];
  }
  // ownership
  return [
    "interpolate",
    ["linear"],
    ["coalesce", ["get", metric], 0],
    0,
    "rgba(248,113,113,0.3)",
    50,
    "rgba(251,191,36,0.3)",
    100,
    "rgba(52,211,153,0.5)",
  ];
}

/**
 * MapLibre fill-opacity expression for the demographics choropleth layer.
 *
 * Race/All: opacity scales with dominant_race_pct (0.2 – 0.8).
 * Race/filtered: opacity scales with selected race pct (0.15 – 0.75).
 * Other subTabs: fixed 0.7.
 */
export function getChoroplethOpacityExpression(
  subTab: DemographicSubTab,
  raceFilter: string,
): ExpressionSpecification | number {
  if (subTab === "race") {
    if (raceFilter && raceFilter !== "all") {
      const pctKey = RACE_TILE_KEY[raceFilter] ?? "pct_white";
      return [
        "interpolate",
        ["linear"],
        ["coalesce", ["get", pctKey], 0],
        0,
        0.15,
        100,
        0.75,
      ] as ExpressionSpecification;
    }
    // All races — opacity by dominant_race_pct
    return [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", "dominant_race_pct"], 0],
      0,
      0.2,
      100,
      0.8,
    ] as ExpressionSpecification;
  }
  return 0.7;
}
