import { describe, it, expect } from "vitest";
import {
  computeDataRange,
  getChoroplethStyle,
  getLegendConfig,
  getChoroplethColorExpression,
  getChoroplethOpacityExpression,
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
  it("returns fixed labels for population", () => {
    const config = getLegendConfig("population");
    expect(config.type).toBe("sequential");
    expect(config.labels).toEqual(["0", "20k+"]);
  });

  it("returns fixed labels for income", () => {
    const config = getLegendConfig("income");
    expect(config.type).toBe("sequential");
    expect(config.labels).toEqual(["$0", "$100k+"]);
  });

  it("returns fixed labels for ownership", () => {
    const config = getLegendConfig("ownership");
    expect(config.type).toBe("sequential");
    expect(config.labels).toEqual(["0%", "100%"]);
  });

  it("returns fixed labels for age", () => {
    const config = getLegendConfig("age");
    expect(config.type).toBe("sequential");
    expect(config.labels).toEqual(["20", "55+"]);
  });

  it("returns categorical legend for race (all)", () => {
    const config = getLegendConfig("race");
    expect(config.type).toBe("categorical");
    expect(config.labels).toContain("White");
  });

  it("returns sequential legend for race filter (non-Asian)", () => {
    const config = getLegendConfig("race", "black");
    expect(config.type).toBe("sequential");
    expect(config.labels).toEqual(["0%", "100%"]);
  });

  it("returns categorical legend for Asian race filter with subgroup labels", () => {
    const config = getLegendConfig("race", "asian");
    expect(config.type).toBe("categorical");
    expect(config.title).toBe("Dominant Asian Sub-Group");
    expect(config.labels).toContain("Asian Indian");
    expect(config.labels).toContain("Chinese");
    expect(config.labels).toContain("Other Asian");
    expect(config.colors.length).toBe(config.labels.length);
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
    const style = getChoroplethStyle(
      makeFeature({ population: 25000 }),
      "population",
      undefined,
      range,
    );
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

/* ── getChoroplethColorExpression ── */

describe("getChoroplethColorExpression", () => {
  it("returns a case expression for race/all using dominant_race", () => {
    const expr = getChoroplethColorExpression("race", "all");
    expect(Array.isArray(expr)).toBe(true);
    expect((expr as unknown[])[0]).toBe("case");
    // Should contain race names
    const flat = JSON.stringify(expr);
    expect(flat).toContain("dominant_race");
    expect(flat).toContain("White");
    expect(flat).toContain("Black");
    expect(flat).toContain("Hispanic");
    expect(flat).toContain("Asian");
  });

  it("returns a solid color string for a filtered race (non-Asian)", () => {
    const expr = getChoroplethColorExpression("race", "black");
    expect(typeof expr).toBe("string");
    expect(expr).toBe("#22d3ee"); // Cyan for Black
  });

  it("returns a case expression for Asian filter using dominant_asian_subgroup", () => {
    const expr = getChoroplethColorExpression("race", "asian");
    expect(Array.isArray(expr)).toBe(true);
    expect((expr as unknown[])[0]).toBe("case");
    const flat = JSON.stringify(expr);
    expect(flat).toContain("dominant_asian_subgroup");
    expect(flat).toContain("Asian Indian");
    expect(flat).toContain("Chinese");
    expect(flat).toContain("Vietnamese");
  });

  it("returns an interpolate expression for non-race subTabs", () => {
    for (const tab of ["population", "income", "age", "ownership"] as const) {
      const expr = getChoroplethColorExpression(tab, "all");
      expect(Array.isArray(expr)).toBe(true);
      expect((expr as unknown[])[0]).toBe("interpolate");
    }
  });
});

/* ── getChoroplethOpacityExpression ── */

describe("getChoroplethOpacityExpression", () => {
  it("returns an interpolate expression for race/all based on dominant_race_pct", () => {
    const expr = getChoroplethOpacityExpression("race", "all");
    expect(Array.isArray(expr)).toBe(true);
    const flat = JSON.stringify(expr);
    expect(flat).toContain("dominant_race_pct");
  });

  it("returns an interpolate expression for a filtered race based on that race pct", () => {
    const expr = getChoroplethOpacityExpression("race", "hispanic");
    expect(Array.isArray(expr)).toBe(true);
    const flat = JSON.stringify(expr);
    expect(flat).toContain("pct_hispanic");
  });

  it("returns an interpolate expression for Asian filter based on dominant_asian_subgroup_pct", () => {
    const expr = getChoroplethOpacityExpression("race", "asian");
    expect(Array.isArray(expr)).toBe(true);
    const flat = JSON.stringify(expr);
    expect(flat).toContain("dominant_asian_subgroup_pct");
  });

  it("returns a fixed number for non-race subTabs", () => {
    expect(getChoroplethOpacityExpression("population", "all")).toBe(0.7);
    expect(getChoroplethOpacityExpression("income", "all")).toBe(0.7);
  });
});
