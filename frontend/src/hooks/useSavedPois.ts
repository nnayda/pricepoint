import { useCallback, useEffect, useState } from "react";
import type { PoiAutocompleteItem, SavedPoiNearbyGroup, SavedPoiResponse } from "../types";
import {
  autocompletePoIs,
  createSavedPoi,
  deleteSavedPoi,
  getSavedPois,
  getSavedPoisNearby,
} from "../services/savedPois";
import { useDebounce } from "./useDebounce";

const TOKEN_KEY = "pricepoint-auth-token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function useSavedPois() {
  const [pois, setPois] = useState<SavedPoiResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setIsLoading(true);
    try {
      const data = await getSavedPois(token);
      setPois(data);
    } catch {
      /* auth or network error — ignore */
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const add = useCallback(
    async (item: {
      match_type: string;
      match_value: string;
      display_name: string;
      category?: string | null;
    }) => {
      const token = getToken();
      if (!token) return;
      const created = await createSavedPoi(token, item);
      setPois((prev) => [created, ...prev]);
    },
    [],
  );

  const remove = useCallback(async (id: number) => {
    const token = getToken();
    if (!token) return;
    await deleteSavedPoi(token, id);
    setPois((prev) => prev.filter((p) => p.id !== id));
  }, []);

  return { pois, add, remove, isLoading, reload: load };
}

export function useSavedPoisNearby(lat: number | null, lon: number | null) {
  const [groups, setGroups] = useState<SavedPoiNearbyGroup[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (lat == null || lon == null) return;
    const token = getToken();
    if (!token) return;

    let cancelled = false;
    setIsLoading(true);
    getSavedPoisNearby(token, lat, lon)
      .then((res) => {
        if (!cancelled) setGroups(res.groups);
      })
      .catch(() => {
        /* ignore */
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [lat, lon]);

  return { groups, isLoading };
}

export function usePoiAutocomplete(query: string) {
  const [results, setResults] = useState<PoiAutocompleteItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setResults([]);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    autocompletePoIs(debouncedQuery)
      .then((res) => {
        if (!cancelled) setResults(res.results);
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  return { results, isLoading };
}
