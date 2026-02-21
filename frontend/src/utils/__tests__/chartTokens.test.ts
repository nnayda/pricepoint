import { describe, it, expect } from "vitest";
import {
  COLOR_INDIGO,
  COLOR_CYAN,
  COLOR_GREEN,
  COLOR_AMBER,
  COLOR_RED,
  COLOR_BLUE,
  COLOR_PURPLE,
  COLOR_ORANGE,
  CHART_PALETTE,
  TOOLTIP_CONTENT_STYLE,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  AXIS_TICK_MONO,
  AXIS_TICK_SANS,
  AXIS_TICK_MONO_SM,
  AXIS_LINE_STYLE,
  GRID_STYLE,
  CURSOR_BAR,
  CURSOR_BAR_LIGHT,
  CURSOR_LINE,
  CURSOR_LINE_CYAN,
  getGradeLabel,
  getGaugeColor,
  getDomColor,
  CATEGORY_COLORS,
  CRIME_PALETTE,
  MORTGAGE_COLORS,
  getSchoolMarkerColor,
} from "../chartTokens";

describe("chartTokens", () => {
  describe("semantic color constants", () => {
    it("exports valid hex colors", () => {
      const hexPattern = /^#[0-9A-Fa-f]{6}$/;
      expect(COLOR_INDIGO).toMatch(hexPattern);
      expect(COLOR_CYAN).toMatch(hexPattern);
      expect(COLOR_GREEN).toMatch(hexPattern);
      expect(COLOR_AMBER).toMatch(hexPattern);
      expect(COLOR_RED).toMatch(hexPattern);
      expect(COLOR_BLUE).toMatch(hexPattern);
      expect(COLOR_PURPLE).toMatch(hexPattern);
      expect(COLOR_ORANGE).toMatch(hexPattern);
    });

    it("CHART_PALETTE contains all 7 semantic colors in order", () => {
      expect(CHART_PALETTE).toHaveLength(7);
      expect(CHART_PALETTE[0]).toBe(COLOR_INDIGO);
      expect(CHART_PALETTE[6]).toBe(COLOR_ORANGE);
    });
  });

  describe("tooltip styles", () => {
    it("TOOLTIP_CONTENT_STYLE has required properties", () => {
      expect(TOOLTIP_CONTENT_STYLE).toHaveProperty("backgroundColor");
      expect(TOOLTIP_CONTENT_STYLE).toHaveProperty("border");
      expect(TOOLTIP_CONTENT_STYLE).toHaveProperty("borderRadius", "8px");
      expect(TOOLTIP_CONTENT_STYLE).toHaveProperty("fontSize", 12);
      expect(TOOLTIP_CONTENT_STYLE).toHaveProperty("color");
    });

    it("TOOLTIP_ITEM_STYLE has color", () => {
      expect(TOOLTIP_ITEM_STYLE).toHaveProperty("color");
    });

    it("TOOLTIP_LABEL_STYLE has color", () => {
      expect(TOOLTIP_LABEL_STYLE).toHaveProperty("color");
    });
  });

  describe("axis styles", () => {
    it("AXIS_TICK_MONO has fill, fontSize, fontFamily", () => {
      expect(AXIS_TICK_MONO.fill).toBeDefined();
      expect(AXIS_TICK_MONO.fontSize).toBe(11);
      expect(AXIS_TICK_MONO.fontFamily).toContain("mono");
    });

    it("AXIS_TICK_SANS has sans fontFamily", () => {
      expect(AXIS_TICK_SANS.fontFamily).toContain("sans");
      expect(AXIS_TICK_SANS.fontSize).toBe(11);
    });

    it("AXIS_TICK_MONO_SM has smaller font size", () => {
      expect(AXIS_TICK_MONO_SM.fontSize).toBe(10);
    });

    it("AXIS_LINE_STYLE has stroke", () => {
      expect(AXIS_LINE_STYLE).toHaveProperty("stroke");
    });
  });

  describe("grid styles", () => {
    it("GRID_STYLE has stroke and dasharray", () => {
      expect(GRID_STYLE).toHaveProperty("stroke");
      expect(GRID_STYLE).toHaveProperty("strokeDasharray", "3 3");
      expect(GRID_STYLE).toHaveProperty("opacity", 0.25);
    });
  });

  describe("cursor styles", () => {
    it("exports bar and line cursor variants", () => {
      expect(CURSOR_BAR).toHaveProperty("fill");
      expect(CURSOR_BAR_LIGHT).toHaveProperty("fill");
      expect(CURSOR_LINE).toHaveProperty("stroke");
      expect(CURSOR_LINE).toHaveProperty("strokeWidth");
      expect(CURSOR_LINE_CYAN).toHaveProperty("stroke");
    });
  });

  describe("getGradeLabel", () => {
    it("returns Excellent for values >= 80", () => {
      const result = getGradeLabel(85);
      expect(result.text).toBe("Excellent");
      expect(result.color).toBe(COLOR_GREEN);
    });

    it("returns Good for values >= 60", () => {
      const result = getGradeLabel(65);
      expect(result.text).toBe("Good");
      expect(result.color).toBe(COLOR_BLUE);
    });

    it("returns Fair for values >= 40", () => {
      const result = getGradeLabel(45);
      expect(result.text).toBe("Fair");
      expect(result.color).toBe(COLOR_AMBER);
    });

    it("returns Poor for values < 40", () => {
      const result = getGradeLabel(20);
      expect(result.text).toBe("Poor");
      expect(result.color).toBe(COLOR_RED);
    });
  });

  describe("getGaugeColor", () => {
    it("returns red for pct <= 0.25", () => {
      expect(getGaugeColor(0.1)).toBe(COLOR_RED);
    });

    it("returns amber for pct <= 0.5", () => {
      expect(getGaugeColor(0.4)).toBe(COLOR_AMBER);
    });

    it("returns blue for pct <= 0.75", () => {
      expect(getGaugeColor(0.6)).toBe(COLOR_BLUE);
    });

    it("returns green for pct > 0.75", () => {
      expect(getGaugeColor(0.9)).toBe(COLOR_GREEN);
    });
  });

  describe("getDomColor", () => {
    it("returns green for < 30 days", () => {
      const result = getDomColor(10);
      expect(result.text).toBe(COLOR_GREEN);
    });

    it("returns amber for 30-90 days", () => {
      const result = getDomColor(60);
      expect(result.text).toBe(COLOR_AMBER);
    });

    it("returns red for > 90 days", () => {
      const result = getDomColor(120);
      expect(result.text).toBe(COLOR_RED);
    });
  });

  describe("category maps", () => {
    it("CATEGORY_COLORS covers standard POI categories", () => {
      expect(CATEGORY_COLORS).toHaveProperty("Grocery");
      expect(CATEGORY_COLORS).toHaveProperty("Healthcare");
      expect(CATEGORY_COLORS).toHaveProperty("Recreation");
      expect(CATEGORY_COLORS).toHaveProperty("Dining");
      expect(CATEGORY_COLORS).toHaveProperty("Shopping");
      expect(CATEGORY_COLORS).toHaveProperty("Services");
    });

    it("CRIME_PALETTE has 5 colors", () => {
      expect(CRIME_PALETTE).toHaveLength(5);
    });

    it("MORTGAGE_COLORS has all 5 segments", () => {
      expect(MORTGAGE_COLORS).toHaveProperty("principal");
      expect(MORTGAGE_COLORS).toHaveProperty("interest");
      expect(MORTGAGE_COLORS).toHaveProperty("tax");
      expect(MORTGAGE_COLORS).toHaveProperty("insurance");
      expect(MORTGAGE_COLORS).toHaveProperty("hoa");
    });
  });

  describe("getSchoolMarkerColor", () => {
    it("returns green for rating >= 8", () => {
      expect(getSchoolMarkerColor(9)).toBe(COLOR_GREEN);
    });

    it("returns amber for rating >= 6", () => {
      expect(getSchoolMarkerColor(7)).toBe(COLOR_AMBER);
    });

    it("returns red for rating < 6", () => {
      expect(getSchoolMarkerColor(4)).toBe(COLOR_RED);
    });
  });
});
