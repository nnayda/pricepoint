import { describe, it, expect } from "vitest";
import { mapDemographicsResponse } from "../mapDemographicsResponse";
import type { DemographicsApiResponse } from "../../types";

function emptyApiContext() {
  return {
    race_ethnicity: [
      { label: "White", value: 60 },
      { label: "Black", value: 20 },
      { label: "Hispanic", value: 10 },
      { label: "Asian", value: 7 },
      { label: "Other", value: 3 },
    ],
    age_distribution: [],
    median_income: 50000,
    income_brackets: [],
    home_ownership_rate: 65,
    median_home_value: 300000,
    population: 10000,
    population_trend: [],
    race_ethnicity_trend: [],
    age_distribution_trend: [],
    income_trend: [],
    home_ownership_trend: [],
    median_age_trend: [],
  };
}

describe("mapDemographicsResponse", () => {
  it("passes through race_detailed with colors", () => {
    const ctx = {
      ...emptyApiContext(),
      race_detailed: {
        asian: {
          race_category: "asian",
          total: 700,
          subgroups: [
            { label: "Chinese", value: 300, percentage: 42.9 },
            { label: "Asian Indian", value: 200, percentage: 28.6 },
            { label: "Vietnamese", value: 100, percentage: 14.3 },
            { label: "Other Asian", value: 100, percentage: 14.3 },
          ],
        },
      },
    };

    const resp: DemographicsApiResponse = {
      contexts: {
        neighborhood: ctx,
        town: emptyApiContext(),
        county: emptyApiContext(),
        block_group: emptyApiContext(),
        subdivision: emptyApiContext(),
      },
      benchmarks: {
        national: emptyApiContext(),
        state: emptyApiContext(),
      },
    };

    const result = mapDemographicsResponse(resp);
    const rd = result.contexts.neighborhood.race_detailed;
    expect(rd).toBeDefined();
    expect(rd!.asian).toBeDefined();
    expect(rd!.asian.subgroups).toHaveLength(4);
    // Each subgroup should have a color assigned
    for (const sg of rd!.asian.subgroups) {
      expect(sg.color).toBeTruthy();
      expect(typeof sg.color).toBe("string");
    }
    // Chinese should get the amber color
    const chinese = rd!.asian.subgroups.find((s) => s.label === "Chinese");
    expect(chinese?.color).toBe("#d97706");
  });

  it("handles missing race_detailed gracefully", () => {
    const resp: DemographicsApiResponse = {
      contexts: {
        neighborhood: emptyApiContext(),
        town: emptyApiContext(),
        county: emptyApiContext(),
        block_group: emptyApiContext(),
        subdivision: emptyApiContext(),
      },
      benchmarks: {
        national: emptyApiContext(),
        state: emptyApiContext(),
      },
    };

    const result = mapDemographicsResponse(resp);
    expect(result.contexts.neighborhood.race_detailed).toBeUndefined();
  });

  it("assigns fallback color to unknown subgroups", () => {
    const ctx = {
      ...emptyApiContext(),
      race_detailed: {
        asian: {
          race_category: "asian",
          total: 100,
          subgroups: [{ label: "UnknownGroup", value: 50, percentage: 50 }],
        },
      },
    };

    const resp: DemographicsApiResponse = {
      contexts: {
        neighborhood: ctx,
        town: emptyApiContext(),
        county: emptyApiContext(),
        block_group: emptyApiContext(),
        subdivision: emptyApiContext(),
      },
      benchmarks: {
        national: emptyApiContext(),
        state: emptyApiContext(),
      },
    };

    const result = mapDemographicsResponse(resp);
    const sg = result.contexts.neighborhood.race_detailed?.asian.subgroups[0];
    expect(sg?.color).toBe("#9ca3af"); // fallback gray
  });
});
