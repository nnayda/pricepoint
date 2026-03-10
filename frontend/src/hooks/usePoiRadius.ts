import { useState, useCallback } from "react";

const STORAGE_KEY = "pricepoint-poi-radius-miles";
const DEFAULT_RADIUS = 10;

function readStored(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw != null) {
      const n = Number(raw);
      if (Number.isFinite(n) && n >= 1 && n <= 50) return n;
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_RADIUS;
}

export function usePoiRadius() {
  const [radiusMiles, setRadiusState] = useState(readStored);

  const setRadiusMiles = useCallback((n: number) => {
    const clamped = Math.max(1, Math.min(50, n));
    setRadiusState(clamped);
    try {
      localStorage.setItem(STORAGE_KEY, String(clamped));
    } catch {
      /* ignore */
    }
  }, []);

  return { radiusMiles, setRadiusMiles };
}
