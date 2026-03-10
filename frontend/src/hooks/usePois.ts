import { useEffect, useState } from "react";
import { getPois } from "../services/property";
import type { PoisResponse } from "../types";

interface UsePoisResult {
  data: PoisResponse | null;
  loading: boolean;
  error: string | null;
}

export function usePois(lat: number | null, lon: number | null): UsePoisResult {
  const [data, setData] = useState<PoisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lat == null || lon == null) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    getPois(lat, lon)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        if (!cancelled) setError("Failed to load POI data");
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
