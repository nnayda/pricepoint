import { describe, it, expect } from "vitest";
import {
  computeDataRange,
  getChoroplethStyle,
  getLegendConfig,
  type DataRange,
} from "../choroplethColors";
import type { DemographicSubTab } from "../../types";

/* ── helpers ── */

function makeFeature(props: Record<string, unknown>): GeoJSON.Feature {
  return { type: "Feature", geometry: { type: "Point", coordinates: [0, 0] }, properties: props };
}

/* ── computeDataRange ── */

describe("computeDataRange", () => {
  it("returns null for race subTab", () => {
    const features = [makeFeature({ population: 5000 })];
    expect(computeDataRange(features, "race")).toBeNull();
  });

  it("returns fallback { min: 0, max: 1 } for empty features", () => {
    expect(computeDataRange([], "population")).toEqual({ min: 0, max: 1 });
  });

  it("returns fallback when features have no matching property", () => {
    const features = [makeFeature({ unrelated: 42 })];
    expect(computeDataRange(features, "population")).toEqual({ min: 0, max: 1 });
  });

  it("computes correct min/max for population", () => {
    const features = [
      makeFeature({ population: 2000 }),
      makeFeature({ population: 8000 }),
      makeFeature({ population: 5000 }),
    ];
    expect(computeDataRange(features, "population")).toEqual({ min: 2000, max: 8000 });
  });

  it("computes correct min/max for income", () => {
    const features = [
      makeFeature({ median_income: 45000 }),
      makeFeature({ median_income: 120000 }),
    ];
    expect(computeDataRange(features, "income")).toEqual({ min: 45000, max: 120000 });
  });

  it("computes correct min/max for age", () => {
    const features = [makeFeature({ median_age: 28 }), makeFeature({ median_age: 52 })];
    expect(computeDataRange(features, "age")).toEqual({ min: 28, max: 52 });
  });

  it("computes correct min/max for ownership", () => {
    const features = [
      makeFeature({ home_ownership_rate: 40 }),
      makeFeature({ home_ownership_rate: 85 }),
    ];
    expect(computeDataRange(features, "ownership")).toEqual({ min: 40, max: 85 });
  });

  it("handles uniform values with epsilon spread", () => {
    const features = [makeFeature({ population: 5000 }), makeFeature({ population: 5000 })];
    const range = computeDataRange(features, "population")!;
    expect(range.min).toBeLessThan(5000);
    expect(range.max).toBeGreaterThan(5000);
    expect(range.min).not.toEqual(range.max);
  });

  it("handles uniform zero values", () => {
    const features = [makeFeature({ population: 0 }), makeFeature({ population: 0 })];
    const range = computeDataRange(features, "population")!;
    expect(range.min).not.toEqual(range.max);
  });

  it("skips features with missing or non-numeric property values", () => {
    const features = [
      makeFeature({ population: 2000 }),
      makeFeature({ population: null }),
      makeFeature({ population: "bad" }),
      makeFeature({}),
      makeFeature({ population: 8000 }),
    ];
    expect(computeDataRange(features, "population")).toEqual({ min: 2000, max: 8000 });
  });
});

/* ── getLegendConfig ── */

describe("getLegendConfig", () => {
  it("uses hardcoded fallback labels when no dataRange is provided", () => {
    const config = getLegendConfig("population");
    expect(config.labels).toEqual(["1k", "10k"]);
  });

  it("generates dynamic labels from dataRange for population", () => {
    const range: DataRange = { min: 500, max: 2500000 };
    const config = getLegendConfig("population", undefined, range);
    expect(config.labels[0]).toBe("500");
    expect(config.labels[1]).toBe("2.5M");
  });

  it("generates dynamic labels from dataRange for income", () => {
    const range: DataRange = { min: 25000, max: 200000 };
    const config = getLegendConfig("income", undefined, range);
    expect(config.labels[0]).toBe("$25k");
    expect(config.labels[1]).toBe("$200k");
  });

  it("generates dynamic labels from dataRange for ownership", () => {
    const range: DataRange = { min: 45, max: 92 };
    const config = getLegendConfig("ownership", undefined, range);
    expect(config.labels[0]).toBe("45%");
    expect(config.labels[1]).toBe("92%");
  });

  it("generates dynamic labels from dataRange for age", () => {
    const range: DataRange = { min: 22, max: 65 };
    const config = getLegendConfig("age", undefined, range);
    expect(config.labels[0]).toBe("22");
    expect(config.labels[1]).toBe("65");
  });

  it("race subtab is unaffected by dataRange", () => {
    const config = getLegendConfig("race");
    expect(config.type).toBe("categorical");
    expect(config.labels).toContain("White");
  });

  it("race filter subtab is unaffected by dataRange", () => {
    const config = getLegendConfig("race", "black");
    expect(config.type).toBe("sequential");
    expect(config.labels).toEqual(["0%", "100%"]);
  });
});

/* ── getChoroplethStyle backward compatibility ── */

describe("getChoroplethStyle", () => {
  const subTabs: DemographicSubTab[] = ["population", "income", "age", "ownership"];

  it("works without dataRange (backward compatible)", () => {
    for (const tab of subTabs) {
      const style = getChoroplethStyle(makeFeature({ population: 5000 }), tab);
      expect(style).toHaveProperty("fillColor");
      expect(style).toHaveProperty("fillOpacity");
    }
  });

  it("accepts dataRange and produces valid style", () => {
    const range: DataRange = { min: 100, max: 50000 };
    const style = getChoroplethStyle(makeFeature({ population: 25000 }), "population", undefined, range);
    expect(style).toHaveProperty("fillColor");
    expect(typeof style.fillColor).toBe("string");
  });

  it("race subtab ignores dataRange entirely", () => {
    const style = getChoroplethStyle(
      makeFeature({ dominant_race: "White", dominant_race_pct: 60 }),
      "race",
      undefined,
      null,
    );
    expect(style).toHaveProperty("fillColor");
  });
});
