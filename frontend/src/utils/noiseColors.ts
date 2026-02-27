import type { LegendConfig } from "./choroplethColors";

/**
 * dB → color mapping for transportation noise polygons.
 * Green (quiet) → Yellow → Orange → Red (loud).
 */
const NOISE_STOPS: { minDb: number; color: string; label: string }[] = [
  { minDb: 0, color: "#4ade80", label: "< 45 dB" },
  { minDb: 45, color: "#a3e635", label: "45-50 dB" },
  { minDb: 50, color: "#facc15", label: "50-55 dB" },
  { minDb: 55, color: "#fb923c", label: "55-60 dB" },
  { minDb: 60, color: "#f97316", label: "60-65 dB" },
  { minDb: 65, color: "#ef4444", label: "65-70 dB" },
  { minDb: 70, color: "#dc2626", label: "70-75 dB" },
  { minDb: 75, color: "#991b1b", label: "75+ dB" },
];

export function getNoiseColor(noiseMinDb: number): string {
  for (let i = NOISE_STOPS.length - 1; i >= 0; i--) {
    if (noiseMinDb >= NOISE_STOPS[i].minDb) {
      return NOISE_STOPS[i].color;
    }
  }
  return NOISE_STOPS[0].color;
}

export function getNoiseLegendConfig(): LegendConfig {
  return {
    type: "categorical",
    title: "Noise Level (dB)",
    colors: NOISE_STOPS.map((s) => s.color),
    labels: NOISE_STOPS.map((s) => s.label),
  };
}

