import { useEffect, useState } from "react";
import type { RiskFeature } from "../types";
import { getRisksData } from "../services/property";

interface RisksData {
  features: RiskFeature[];
}

const EMPTY_DATA: RisksData = {
  features: [],
};

/** Module-level cache keyed by "lat,lon,radius" */
const promiseCache = new Map<string, Promise<RisksData>>();
const dataCache = new Map<string, RisksData>();

function cacheKey(lat: number, lon: number, radiusMiles: number): string {
  return `${lat},${lon},${radiusMiles}`;
}

function fetchAndCache(lat: number, lon: number, radiusMiles: number): Promise<RisksData> {
  const key = cacheKey(lat, lon, radiusMiles);
  const existing = promiseCache.get(key);
  if (existing) return existing;

  const promise = getRisksData(lat, lon, radiusMiles).then((resp) => {
    const data: RisksData = { features: resp.features };
    dataCache.set(key, data);
    return data;
  });
  promiseCache.set(key, promise);
  return promise;
}

/** @internal — exposed for test cleanup only */
export function _clearRisksCache(): void {
  promiseCache.clear();
  dataCache.clear();
}

/**
 * Fire-and-forget preload — call early (e.g. when dashboard mounts)
 * so the data is ready when the Risks tab is opened.
 */
export function preloadRisks(lat: number | null, lon: number | null, radiusMiles = 3): void {
  if (lat == null || lon == null) return;
  fetchAndCache(lat, lon, radiusMiles);
}

export function useRisks(lat: number, lon: number, radiusMiles = 3) {
  const key = cacheKey(lat, lon, radiusMiles);
  const cached = dataCache.get(key);

  const [data, setData] = useState<RisksData>(cached ?? EMPTY_DATA);
  const [loading, setLoading] = useState(!cached);

  useEffect(() => {
    const alreadyCached = dataCache.get(cacheKey(lat, lon, radiusMiles));
    if (alreadyCached) {
      setData(alreadyCached);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    fetchAndCache(lat, lon, radiusMiles)
      .then((result) => {
        if (!cancelled) {
          setData(result);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error("Failed to load risks data:", err);
          setData(EMPTY_DATA);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [lat, lon, radiusMiles]);

  return { data, loading };
}
