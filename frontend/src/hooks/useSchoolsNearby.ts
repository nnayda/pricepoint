import { useEffect, useState } from "react";
import { getSchoolsNearby } from "../services/property";
import type { SchoolDistrictInfo, SchoolNearby, SchoolsNearbyResponse } from "../types";

interface UseSchoolsNearbyResult {
  schools: SchoolNearby[];
  schoolDistricts: SchoolDistrictInfo[];
  loading: boolean;
  error: string | null;
}

/** Module-level cache keyed by "lat,lon" */
const promiseCache = new Map<string, Promise<SchoolsNearbyResponse>>();
const dataCache = new Map<
  string,
  { schools: SchoolNearby[]; schoolDistricts: SchoolDistrictInfo[] }
>();

function cacheKey(lat: number, lon: number): string {
  return `${lat},${lon}`;
}

function fetchAndCache(lat: number, lon: number): Promise<SchoolsNearbyResponse> {
  const key = cacheKey(lat, lon);
  const existing = promiseCache.get(key);
  if (existing) return existing;

  const promise = getSchoolsNearby(lat, lon, 25, 200).then((result) => {
    dataCache.set(key, {
      schools: result.schools,
      schoolDistricts: result.school_districts,
    });
    return result;
  });
  promiseCache.set(key, promise);
  return promise;
}

/**
 * Fire-and-forget preload — call early (e.g. when dashboard mounts)
 * so the data is ready when the Schools tab is opened.
 */
export function preloadSchoolsNearby(lat: number | null, lon: number | null): void {
  if (lat == null || lon == null) return;
  fetchAndCache(lat, lon);
}

export function useSchoolsNearby(lat: number | null, lon: number | null): UseSchoolsNearbyResult {
  const key = lat != null && lon != null ? cacheKey(lat, lon) : null;
  const cached = key ? dataCache.get(key) : undefined;

  const [schools, setSchools] = useState<SchoolNearby[]>(cached?.schools ?? []);
  const [schoolDistricts, setSchoolDistricts] = useState<SchoolDistrictInfo[]>(
    cached?.schoolDistricts ?? [],
  );
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
      setSchools(alreadyCached.schools);
      setSchoolDistricts(alreadyCached.schoolDistricts);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAndCache(lat, lon)
      .then((result) => {
        if (!cancelled) {
          setSchools(result.schools);
          setSchoolDistricts(result.school_districts);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load nearby schools");
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

  return { schools, schoolDistricts, loading, error };
}
