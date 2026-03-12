import { useEffect, useState } from "react";
import { getPoliceIncidents } from "../services/property";
import type { CrimeIncident, CrimeResponse } from "../types";

interface UsePoliceIncidentsResult {
  incidents: CrimeIncident[];
  loading: boolean;
  error: string | null;
}

/** Module-level cache keyed by "lat,lon" */
const promiseCache = new Map<string, Promise<CrimeResponse>>();
const dataCache = new Map<string, CrimeIncident[]>();

function cacheKey(lat: number, lon: number): string {
  return `${lat},${lon}`;
}

function fetchAndCache(lat: number, lon: number): Promise<CrimeResponse> {
  const key = cacheKey(lat, lon);
  const existing = promiseCache.get(key);
  if (existing) return existing;

  const promise = getPoliceIncidents(lat, lon).then((result) => {
    dataCache.set(key, result.incidents);
    return result;
  });
  promiseCache.set(key, promise);
  return promise;
}

/**
 * Fire-and-forget preload — call early (e.g. when dashboard mounts)
 * so the data is ready when the Police tab is opened.
 */
export function preloadPoliceIncidents(lat: number | null, lon: number | null): void {
  if (lat == null || lon == null) return;
  fetchAndCache(lat, lon);
}

export function usePoliceIncidents(
  lat: number | null,
  lon: number | null,
): UsePoliceIncidentsResult {
  const key = lat != null && lon != null ? cacheKey(lat, lon) : null;
  const cached = key ? dataCache.get(key) : undefined;

  const [incidents, setIncidents] = useState<CrimeIncident[]>(cached ?? []);
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
      setIncidents(alreadyCached);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAndCache(lat, lon)
      .then((result) => {
        if (!cancelled) {
          setIncidents(result.incidents);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load police incidents");
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

  return { incidents, loading, error };
}
