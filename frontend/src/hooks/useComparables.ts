import { useCallback, useEffect, useRef, useState } from "react";
import type { ComparablesResponse, ComparablesSearchCriteria } from "../types";
import { getComparables } from "../services/comparables";

interface UseComparablesResult {
  data: ComparablesResponse | null;
  loading: boolean;
  error: string | null;
  search: () => void;
}

export function useComparables(
  lat: number | null,
  lon: number | null,
  address: string | null,
  criteria: ComparablesSearchCriteria,
): UseComparablesResult {
  const [data, setData] = useState<ComparablesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const criteriaRef = useRef(criteria);
  criteriaRef.current = criteria;

  const search = useCallback(() => {
    if (!lat || !lon || !address) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    getComparables(lat, lon, address, criteriaRef.current)
      .then((result) => {
        if (!controller.signal.aborted) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          const message =
            err?.response?.status === 404
              ? "Subject property not found in database"
              : err?.message || "Failed to load comparables";
          setError(message);
          setLoading(false);
        }
      });
  }, [lat, lon, address]);

  // Initial search on mount
  useEffect(() => {
    search();
    return () => {
      abortRef.current?.abort();
    };
  }, [search]);

  return { data, loading, error, search };
}
