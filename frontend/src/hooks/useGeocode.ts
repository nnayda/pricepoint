import { useEffect, useRef } from "react";
import { useApi } from "./useApi";
import { useDebounce } from "./useDebounce";
import { getGeocode } from "../services/geocode";
import type { GeocodeResponse } from "../types";

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 3;

export function useGeocode(query: string) {
  const debouncedQuery = useDebounce(query, DEBOUNCE_MS);
  const { data, loading, error, execute } = useApi<GeocodeResponse, [string]>(getGeocode);
  const lastQuery = useRef<string>("");

  useEffect(() => {
    if (debouncedQuery.length >= MIN_QUERY_LENGTH && debouncedQuery !== lastQuery.current) {
      lastQuery.current = debouncedQuery;
      execute(debouncedQuery);
    }
  }, [debouncedQuery, execute]);

  const results = data?.results ?? [];

  return { results, loading, error };
}
