import { useEffect, useState } from "react";
import {
  getNeighborhoodValuation,
  getNeighborhoodValuationHistory,
  type NeighborhoodValuation,
} from "../services/property";
import type { NeighborhoodValuationHistory } from "../types";

interface UseNeighborhoodValuationResult {
  data: NeighborhoodValuation | null;
  loading: boolean;
}

export function useNeighborhoodValuation(
  lat: number | null,
  lon: number | null,
): UseNeighborhoodValuationResult {
  const [data, setData] = useState<NeighborhoodValuation | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (lat == null || lon == null) return;

    let cancelled = false;
    setLoading(true);

    getNeighborhoodValuation(lat, lon)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        // Silently handle — mock fallback stays in place
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [lat, lon]);

  return { data, loading };
}

interface UseNeighborhoodValuationHistoryResult {
  data: NeighborhoodValuationHistory | null;
  loading: boolean;
}

export function useNeighborhoodValuationHistory(
  lat: number | null,
  lon: number | null,
): UseNeighborhoodValuationHistoryResult {
  const [data, setData] = useState<NeighborhoodValuationHistory | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (lat == null || lon == null) return;

    let cancelled = false;
    setLoading(true);

    getNeighborhoodValuationHistory(lat, lon)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        // Silently handle — chart shows without neighborhood line
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [lat, lon]);

  return { data, loading };
}
