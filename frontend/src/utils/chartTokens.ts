/**
 * Shared Recharts styling constants — single source of truth for all chart
 * tooltip, axis, grid, cursor, and semantic color tokens.
 */

/* ------------------------------------------------------------------ */
/*  Semantic color constants                                          */
/* ------------------------------------------------------------------ */

export const COLOR_INDIGO = "#6366F1";
export const COLOR_CYAN = "#22D3EE";
export const COLOR_GREEN = "#34D399";
export const COLOR_AMBER = "#FBBF24";
export const COLOR_RED = "#F87171";
export const COLOR_BLUE = "#5B7FFF";
export const COLOR_PURPLE = "#A78BFA";
export const COLOR_ORANGE = "#FB923C";

/** Ordered palette per design guidelines Section 7.3 */
export const CHART_PALETTE = [
  COLOR_INDIGO,
  COLOR_CYAN,
  COLOR_GREEN,
  COLOR_AMBER,
  COLOR_RED,
  COLOR_PURPLE,
  COLOR_ORANGE,
] as const;

/* ------------------------------------------------------------------ */
/*  Surface / text colors used in chart chrome                        */
/* ------------------------------------------------------------------ */

export const COLOR_TOOLTIP_BG = "#1C2333";
export const COLOR_TOOLTIP_BORDER = "#2E3553";
export const COLOR_TEXT_PRIMARY = "#E8ECF4";
export const COLOR_TEXT_SECONDARY = "#9BA3BF";
export const COLOR_GRID_LINE = "#2E3553";

/* ------------------------------------------------------------------ */
/*  Tooltip styles                                                     */
/* ------------------------------------------------------------------ */

export const TOOLTIP_CONTENT_STYLE: React.CSSProperties = {
  backgroundColor: COLOR_TOOLTIP_BG,
  border: `1px solid ${COLOR_TOOLTIP_BORDER}`,
  borderRadius: "8px",
  fontFamily: "var(--font-db-sans)",
  fontSize: 12,
  color: COLOR_TEXT_PRIMARY,
};

export const TOOLTIP_ITEM_STYLE: React.CSSProperties = { color: COLOR_TEXT_PRIMARY };
export const TOOLTIP_LABEL_STYLE: React.CSSProperties = { color: COLOR_TEXT_SECONDARY };

/* ------------------------------------------------------------------ */
/*  Axis tick styles                                                   */
/* ------------------------------------------------------------------ */

export const AXIS_TICK_MONO = {
  fill: COLOR_TEXT_SECONDARY,
  fontSize: 11,
  fontFamily: "var(--font-db-mono)",
} as const;

export const AXIS_TICK_SANS = {
  fill: COLOR_TEXT_SECONDARY,
  fontSize: 11,
  fontFamily: "var(--font-db-sans)",
} as const;

/** Smaller variant for dense charts */
export const AXIS_TICK_MONO_SM = {
  ...AXIS_TICK_MONO,
  fontSize: 10,
} as const;

/* ------------------------------------------------------------------ */
/*  Axis line & grid styles                                            */
/* ------------------------------------------------------------------ */

export const AXIS_LINE_STYLE = { stroke: COLOR_GRID_LINE } as const;

export const GRID_STYLE = {
  stroke: COLOR_GRID_LINE,
  strokeDasharray: "3 3",
  opacity: 0.25,
} as const;

/* ------------------------------------------------------------------ */
/*  Cursor styles                                                      */
/* ------------------------------------------------------------------ */

/** Bar-chart hover cursor */
export const CURSOR_BAR = { fill: "rgba(99, 102, 241, 0.08)" } as const;
export const CURSOR_BAR_LIGHT = { fill: "rgba(99, 102, 241, 0.1)" } as const;

/** Line/area-chart hover cursor */
export const CURSOR_LINE = { stroke: "rgba(99, 102, 241, 0.3)", strokeWidth: 1 } as const;

/** Cyan variant for population / secondary area charts */
export const CURSOR_LINE_CYAN = { stroke: "rgba(34, 211, 238, 0.3)", strokeWidth: 1 } as const;

/* ------------------------------------------------------------------ */
/*  Gauge helpers (extracted from SemiCircularGauge)                   */
/* ------------------------------------------------------------------ */

export function getGradeLabel(value: number): { text: string; color: string } {
  if (value >= 80) return { text: "Excellent", color: COLOR_GREEN };
  if (value >= 60) return { text: "Good", color: COLOR_BLUE };
  if (value >= 40) return { text: "Fair", color: COLOR_AMBER };
  return { text: "Poor", color: COLOR_RED };
}

export function getGaugeColor(pct: number): string {
  if (pct <= 0.25) return COLOR_RED;
  if (pct <= 0.5) return COLOR_AMBER;
  if (pct <= 0.75) return COLOR_BLUE;
  return COLOR_GREEN;
}

/* ------------------------------------------------------------------ */
/*  DOM (days-on-market) color helper                                  */
/* ------------------------------------------------------------------ */

export function getDomColor(days: number): { bg: string; text: string } {
  if (days < 30) return { bg: `rgba(52, 211, 153, 0.15)`, text: COLOR_GREEN };
  if (days <= 90) return { bg: `rgba(251, 191, 36, 0.15)`, text: COLOR_AMBER };
  return { bg: `rgba(248, 113, 113, 0.15)`, text: COLOR_RED };
}

/* ------------------------------------------------------------------ */
/*  Category color maps                                                */
/* ------------------------------------------------------------------ */

export const CATEGORY_COLORS: Record<string, string> = {
  Grocery: COLOR_GREEN,
  Healthcare: COLOR_RED,
  Recreation: COLOR_INDIGO,
  Dining: COLOR_AMBER,
  Shopping: COLOR_CYAN,
  Services: COLOR_PURPLE,
};

/** Crime breakdown bar palette (cycles through 5 colors) */
export const CRIME_PALETTE = [
  COLOR_INDIGO,
  COLOR_RED,
  COLOR_ORANGE,
  COLOR_AMBER,
  COLOR_PURPLE,
] as const;

/** Mortgage donut segment colors */
export const MORTGAGE_COLORS = {
  principal: COLOR_INDIGO,
  interest: COLOR_CYAN,
  tax: COLOR_AMBER,
  insurance: COLOR_GREEN,
  hoa: COLOR_PURPLE,
} as const;

/** School marker color based on rating */
export function getSchoolMarkerColor(rating: number): string {
  if (rating >= 8) return COLOR_GREEN;
  if (rating >= 6) return COLOR_AMBER;
  return COLOR_RED;
}

/* ------------------------------------------------------------------ */
/*  useChartTokens hook — resolves --th-* tokens at runtime            */
/* ------------------------------------------------------------------ */

import { useMemo, useSyncExternalStore } from "react";

/** Subscribes to theme changes via data-theme attribute mutations. */
function subscribeToTheme(cb: () => void): () => void {
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.attributeName === "data-theme") {
        cb();
        return;
      }
    }
  });
  observer.observe(document.documentElement, { attributes: true });
  return () => observer.disconnect();
}

function getThemeSnapshot(): string {
  return document.documentElement.dataset.theme ?? "dark";
}

function getThemeServerSnapshot(): string {
  return "dark";
}

function resolveCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export interface ChartThemeTokens {
  tooltipBg: string;
  tooltipBorder: string;
  textPrimary: string;
  textSecondary: string;
  surfaceAlt: string;
  border: string;
  tooltipContentStyle: React.CSSProperties;
  tooltipItemStyle: React.CSSProperties;
  tooltipLabelStyle: React.CSSProperties;
}

/**
 * Hook that resolves `--th-*` CSS variables to concrete values,
 * re-computing when `data-theme` attribute changes.
 */
export function useChartTokens(): ChartThemeTokens {
  const themeKey = useSyncExternalStore(subscribeToTheme, getThemeSnapshot, getThemeServerSnapshot);

  return useMemo<ChartThemeTokens>(() => {
    const tooltipBg = resolveCSSVar("--th-tooltip-bg") || COLOR_TOOLTIP_BG;
    const tooltipBorder = resolveCSSVar("--th-tooltip-border") || COLOR_TOOLTIP_BORDER;
    const textPrimary = resolveCSSVar("--th-text-primary") || COLOR_TEXT_PRIMARY;
    const textSecondary = resolveCSSVar("--th-text-secondary") || COLOR_TEXT_SECONDARY;
    const surfaceAlt = resolveCSSVar("--th-bg-surface-alt") || "#1C2333";
    const border = resolveCSSVar("--th-border") || COLOR_GRID_LINE;

    return {
      tooltipBg,
      tooltipBorder,
      textPrimary,
      textSecondary,
      surfaceAlt,
      border,
      tooltipContentStyle: {
        backgroundColor: tooltipBg,
        border: `1px solid ${tooltipBorder}`,
        borderRadius: "8px",
        fontFamily: "var(--font-db-sans)",
        fontSize: 12,
        color: textPrimary,
      },
      tooltipItemStyle: { color: textPrimary },
      tooltipLabelStyle: { color: textSecondary },
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [themeKey]);
}
