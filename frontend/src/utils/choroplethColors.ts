import type { DemographicSubTab } from "../types";

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

const CYAN_RAMP = ["#cffafe", "#67e8f9", "#22d3ee", "#0891b2", "#155e75"];
const GREEN_RAMP = ["#dcfce7", "#86efac", "#22c55e", "#16a34a", "#14532d"];
const AGE_RAMP = ["#22d3ee", "#67e8f9", "#e5e7eb", "#fbbf24", "#f59e0b"]; // cyan→neutral→amber
const OWN_RAMP = ["#ef4444", "#fca5a5", "#e5e7eb", "#86efac", "#22c55e"]; // red→neutral→green

function interpolateRamp(ramp: string[], t: number): string {
  const idx = Math.min(Math.floor(t * (ramp.length - 1)), ramp.length - 2);
  return ramp[Math.min(idx + (t * (ramp.length - 1) - idx >= 0.5 ? 1 : 0), ramp.length - 1)];
}

function quantilePosition(value: number, min: number, max: number): number {
  if (max <= min) return 0.5;
  return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

/**
 * Return a Leaflet-compatible style object for a choropleth feature.
 */
export function getChoroplethStyle(
  feature: GeoJSON.Feature | undefined,
  subTab: DemographicSubTab,
): Record<string, string | number> {
  const props = feature?.properties ?? {};
  const isHome = props.is_home === true;

  let fillColor: string;

  switch (subTab) {
    case "population": {
      const t = quantilePosition(props.population ?? 0, 1000, 10000);
      fillColor = interpolateRamp(CYAN_RAMP, t);
      break;
    }
    case "income": {
      const t = quantilePosition(props.median_income ?? 0, 30000, 150000);
      fillColor = interpolateRamp(GREEN_RAMP, t);
      break;
    }
    case "age": {
      // Diverging around 38 (national median)
      const age = props.median_age ?? 38;
      const t = quantilePosition(age, 25, 55);
      fillColor = interpolateRamp(AGE_RAMP, t);
      break;
    }
    case "ownership": {
      const rate = props.home_ownership_rate ?? 65;
      const t = quantilePosition(rate, 30, 90);
      fillColor = interpolateRamp(OWN_RAMP, t);
      break;
    }
    case "race": {
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

/**
 * Format a tooltip string for the hovered feature.
 */
export function getTooltipText(
  props: Record<string, unknown>,
  subTab: DemographicSubTab,
): string {
  const name = (props.name as string) ?? (props.geoid as string) ?? "";
  switch (subTab) {
    case "population":
      return `${name}\nPop: ${((props.population as number) ?? 0).toLocaleString()}`;
    case "income":
      return `${name}\nMedian Income: $${((props.median_income as number) ?? 0).toLocaleString()}`;
    case "age":
      return `${name}\nMedian Age: ${props.median_age ?? 0}`;
    case "ownership":
      return `${name}\nOwnership: ${props.home_ownership_rate ?? 0}%`;
    case "race":
      return `${name}\n${props.dominant_race ?? "Unknown"}: ${props.dominant_race_pct ?? 0}%`;
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

export function getLegendConfig(subTab: DemographicSubTab): LegendConfig {
  switch (subTab) {
    case "population":
      return {
        type: "sequential",
        title: "Population",
        colors: CYAN_RAMP,
        labels: ["1k", "10k+"],
      };
    case "income":
      return {
        type: "sequential",
        title: "Median Income",
        colors: GREEN_RAMP,
        labels: ["$30k", "$150k+"],
      };
    case "age":
      return {
        type: "diverging",
        title: "Median Age",
        colors: AGE_RAMP,
        labels: ["25", "38", "55+"],
      };
    case "ownership":
      return {
        type: "diverging",
        title: "Ownership Rate",
        colors: OWN_RAMP,
        labels: ["30%", "65%", "90%+"],
      };
    case "race":
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
