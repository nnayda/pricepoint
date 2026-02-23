import { useEffect, useState } from "react";
import { getDemographics } from "../services/property";
import type { DemographicsApiResponse } from "../types";

interface UseDemographicsResult {
  data: DemographicsApiResponse | null;
  loading: boolean;
  error: string | null;
}

export function useDemographics(lat: number | null, lon: number | null): UseDemographicsResult {
  const [data, setData] = useState<DemographicsApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lat == null || lon == null) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    getDemographics(lat, lon)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load demographics data");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [lat, lon]);

  return { data, loading, error };
}
