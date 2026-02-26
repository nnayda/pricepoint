import { useEffect, useState } from "react";
import { getSchoolsNearby } from "../services/property";
import type { SchoolDistrictInfo, SchoolNearby } from "../types";

interface UseSchoolsNearbyResult {
  schools: SchoolNearby[];
  schoolDistricts: SchoolDistrictInfo[];
  loading: boolean;
  error: string | null;
}

export function useSchoolsNearby(lat: number | null, lon: number | null): UseSchoolsNearbyResult {
  const [schools, setSchools] = useState<SchoolNearby[]>([]);
  const [schoolDistricts, setSchoolDistricts] = useState<SchoolDistrictInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lat == null || lon == null) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchSchools() {
      setLoading(true);
      setError(null);

      try {
        const result = await getSchoolsNearby(lat!, lon!, 25, 200);
        if (!cancelled) {
          setSchools(result.schools);
          setSchoolDistricts(result.school_districts);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load nearby schools");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchSchools();
    return () => {
      cancelled = true;
    };
  }, [lat, lon]);

  return { schools, schoolDistricts, loading, error };
}
