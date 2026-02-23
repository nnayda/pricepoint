import { useEffect, useRef, useState, useCallback } from "react";
import { getDemographicsChoropleth } from "../services/property";
import type { DemographicContext } from "../types";

export interface Bbox {
  swLat: number;
  swLon: number;
  neLat: number;
  neLon: number;
}

interface UseChoroplethResult {
  data: GeoJSON.FeatureCollection;
  loading: boolean;
}

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const DEBOUNCE_MS = 300;

/**
 * Hook that fetches choropleth GeoJSON features for the current map viewport.
 *
 * Debounces bbox changes (300ms). When `context` changes, it immediately
 * fetches using the latest bbox so the map updates without waiting for a pan.
 */
export function useChoropleth(
  context: DemographicContext,
  bbox: Bbox | null,
  homeLat?: number,
  homeLon?: number,
  initialData?: GeoJSON.FeatureCollection,
): UseChoroplethResult {
  const [data, setData] = useState<GeoJSON.FeatureCollection>(initialData ?? EMPTY_FC);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const latestBboxRef = useRef<Bbox | null>(bbox);
  const prevContextRef = useRef(context);
  const hasFetchedRef = useRef(false);

  // Keep bbox ref current
  latestBboxRef.current = bbox;

  const fetchFeatures = useCallback(
    (b: Bbox, ctx: DemographicContext) => {
      // Cancel any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      getDemographicsChoropleth(ctx, b.swLat, b.swLon, b.neLat, b.neLon, homeLat, homeLon)
        .then((features) => {
          if (!controller.signal.aborted) {
            setData({ type: "FeatureCollection", features });
          }
        })
        .catch(() => {
          // Keep existing data on error
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        });
    },
    [homeLat, homeLon],
  );

  // When context changes, immediately fetch with current bbox
  useEffect(() => {
    if (prevContextRef.current !== context) {
      prevContextRef.current = context;
      // Cancel pending debounce
      if (timerRef.current) clearTimeout(timerRef.current);

      // Show initial data while fetching
      if (initialData && initialData.features.length > 0) {
        setData(initialData);
      }

      // Immediately fetch for new context with current bounds
      const currentBbox = latestBboxRef.current;
      if (currentBbox) {
        fetchFeatures(currentBbox, context);
      }
    }
  }, [context, initialData, fetchFeatures]);

  // When bbox changes, debounce and fetch
  useEffect(() => {
    if (!bbox) return;

    // Skip debounce for initial fetch
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      fetchFeatures(bbox, context);
      return;
    }

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => fetchFeatures(bbox, context), DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [bbox, context, fetchFeatures]);

  // Cleanup abort on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return { data, loading };
}
