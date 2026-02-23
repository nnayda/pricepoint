import type { FeatureCollection, Feature, Polygon } from "geojson";
import type { DemographicContext } from "../types";

function mockFeature(
  coords: number[][],
  props: Record<string, unknown>,
): Feature<Polygon> {
  return {
    type: "Feature",
    properties: props,
    geometry: { type: "Polygon", coordinates: [coords] },
  };
}

const BASE_PROPS = {
  population: 4200,
  median_income: 78000,
  median_age: 36.5,
  home_ownership_rate: 72.0,
  dominant_race: "White",
  dominant_race_pct: 62.4,
  pct_under_18: 22.0,
  pct_65_plus: 14.0,
};

/** Per-context mock choropleth data with full demographic properties */
export const MOCK_CHOROPLETH_MAP: Record<DemographicContext, FeatureCollection> = {
  neighborhood: {
    type: "FeatureCollection",
    features: [
      mockFeature(
        [[-78.81, 35.585], [-78.79, 35.585], [-78.79, 35.57], [-78.81, 35.57], [-78.81, 35.585]],
        { ...BASE_PROPS, geoid: "37183054101", name: "Tract 541.01", is_home: true, median_income: 92400, population: 3200 },
      ),
      mockFeature(
        [[-78.79, 35.585], [-78.77, 35.585], [-78.77, 35.57], [-78.79, 35.57], [-78.79, 35.585]],
        { ...BASE_PROPS, geoid: "37183054102", name: "Tract 541.02", is_home: false, median_income: 78500, population: 4100 },
      ),
      mockFeature(
        [[-78.81, 35.57], [-78.79, 35.57], [-78.79, 35.555], [-78.81, 35.555], [-78.81, 35.57]],
        { ...BASE_PROPS, geoid: "37183054201", name: "Tract 542.01", is_home: false, median_income: 65200, population: 3800, dominant_race: "Black", dominant_race_pct: 48.2 },
      ),
      mockFeature(
        [[-78.79, 35.57], [-78.77, 35.57], [-78.77, 35.555], [-78.79, 35.555], [-78.79, 35.57]],
        { ...BASE_PROPS, geoid: "37183054202", name: "Tract 542.02", is_home: false, median_income: 71800, population: 2950 },
      ),
    ],
  },

  block_group: {
    type: "FeatureCollection",
    features: [
      mockFeature(
        [[-78.805, 35.58], [-78.795, 35.58], [-78.795, 35.57], [-78.805, 35.57], [-78.805, 35.58]],
        { ...BASE_PROPS, geoid: "371830541011", name: "BG 1", is_home: true, population: 1200 },
      ),
      mockFeature(
        [[-78.795, 35.58], [-78.785, 35.58], [-78.785, 35.57], [-78.795, 35.57], [-78.795, 35.58]],
        { ...BASE_PROPS, geoid: "371830541012", name: "BG 2", is_home: false, population: 980 },
      ),
      mockFeature(
        [[-78.805, 35.57], [-78.795, 35.57], [-78.795, 35.56], [-78.805, 35.56], [-78.805, 35.57]],
        { ...BASE_PROPS, geoid: "371830541013", name: "BG 3", is_home: false, population: 1450, dominant_race: "Hispanic", dominant_race_pct: 41.3 },
      ),
    ],
  },

  subdivision: {
    type: "FeatureCollection",
    features: [
      mockFeature(
        [[-78.798, 35.575], [-78.782, 35.575], [-78.782, 35.565], [-78.798, 35.565], [-78.798, 35.575]],
        { ...BASE_PROPS, geoid: "subdiv_S001", name: "Heritage Oaks", is_home: true, median_income: 95000 },
      ),
      mockFeature(
        [[-78.802, 35.58], [-78.792, 35.58], [-78.792, 35.575], [-78.802, 35.575], [-78.802, 35.58]],
        { ...BASE_PROPS, geoid: "subdiv_S002", name: "Lakewood", is_home: false, median_income: 82000 },
      ),
    ],
  },

  town: {
    type: "FeatureCollection",
    features: [
      mockFeature(
        [[-78.84, 35.61], [-78.74, 35.61], [-78.74, 35.53], [-78.84, 35.53], [-78.84, 35.61]],
        { ...BASE_PROPS, geoid: "3725780", name: "Fuquay-Varina", is_home: true, population: 35000, median_income: 72000 },
      ),
      mockFeature(
        [[-78.74, 35.61], [-78.64, 35.61], [-78.64, 35.53], [-78.74, 35.53], [-78.74, 35.61]],
        { ...BASE_PROPS, geoid: "3727960", name: "Holly Springs", is_home: false, population: 42000, median_income: 98000 },
      ),
    ],
  },

  county: {
    type: "FeatureCollection",
    features: [
      mockFeature(
        [[-79.0, 35.9], [-78.5, 35.9], [-78.5, 35.5], [-79.0, 35.5], [-79.0, 35.9]],
        { ...BASE_PROPS, geoid: "37183", name: "Wake County", is_home: true, population: 1150000, median_income: 82000 },
      ),
      mockFeature(
        [[-79.0, 35.5], [-78.5, 35.5], [-78.5, 35.1], [-79.0, 35.1], [-79.0, 35.5]],
        { ...BASE_PROPS, geoid: "37085", name: "Harnett County", is_home: false, population: 138000, median_income: 52000 },
      ),
    ],
  },
};
