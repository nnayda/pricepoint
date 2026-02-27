import { useState, useCallback } from "react";

export type MapRadius = 5 | 10 | 25 | 50;

export const RADIUS_ZOOM: Record<MapRadius, number> = {
  5: 12,
  10: 11,
  25: 9,
  50: 8,
};

const STORAGE_KEY = "pricepoint-map-radius";
const DEFAULT_RADIUS: MapRadius = 10;
const VALID: Set<number> = new Set([5, 10, 25, 50]);

function readStored(): MapRadius {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const n = Number(raw);
      if (VALID.has(n)) return n as MapRadius;
    }
  } catch {
    /* SSR / blocked storage */
  }
  return DEFAULT_RADIUS;
}

export function useMapRadius(): [MapRadius, (r: MapRadius) => void] {
  const [radius, setRadius] = useState<MapRadius>(readStored);

  const update = useCallback((r: MapRadius) => {
    setRadius(r);
    try {
      localStorage.setItem(STORAGE_KEY, String(r));
    } catch {
      /* ignore */
    }
  }, []);

  return [radius, update];
}
