import { useEffect, useState } from "react";
import { getNuisanceSources } from "../services/property";
import type { NuisanceSourceItem } from "../types";

interface UseNuisanceSourcesResult {
  sources: NuisanceSourceItem[];
  loading: boolean;
  error: string | null;
}

/** Module-level cache keyed by "lat,lon" */
const promiseCache = new Map<string, Promise<NuisanceSourceItem[]>>();
const dataCache = new Map<string, NuisanceSourceItem[]>();

function cacheKey(lat: number, lon: number): string {
  return `${lat},${lon}`;
}

function fetchAndCache(lat: number, lon: number): Promise<NuisanceSourceItem[]> {
  const key = cacheKey(lat, lon);
  const existing = promiseCache.get(key);
  if (existing) return existing;

  const promise = getNuisanceSources(lat, lon).then((result) => {
    dataCache.set(key, result.sources);
    return result.sources;
  });
  promiseCache.set(key, promise);
  return promise;
}

/** @internal — exposed for test cleanup only */
export function _clearNuisanceSourcesCache(): void {
  promiseCache.clear();
  dataCache.clear();
}

/**
 * Fire-and-forget preload — call early (e.g. when dashboard mounts)
 * so the data is ready when the Nuisances tab is opened.
 */
export function preloadNuisanceSources(lat: number | null, lon: number | null): void {
  if (lat == null || lon == null) return;
  fetchAndCache(lat, lon);
}

export function useNuisanceSources(lat: number | null, lon: number | null): UseNuisanceSourcesResult {
  const key = lat != null && lon != null ? cacheKey(lat, lon) : null;
  const cached = key ? dataCache.get(key) : undefined;

  const [sources, setSources] = useState<NuisanceSourceItem[]>(cached ?? []);
  const [loading, setLoading] = useState(!cached);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lat == null || lon == null) {
      setLoading(false);
      return;
    }

    const k = cacheKey(lat, lon);
    const alreadyCached = dataCache.get(k);
    if (alreadyCached) {
      setSources(alreadyCached);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAndCache(lat, lon)
      .then((result) => {
        if (!cancelled) {
          setSources(result);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load nuisance sources");
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
  }, [lat, lon]);

  return { sources, loading, error };
}
