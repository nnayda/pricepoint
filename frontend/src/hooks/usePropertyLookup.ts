import { useEffect, useState } from "react";
import { getProperty } from "../services/property";
import type { PropertyResponse } from "../types";

interface UsePropertyLookupResult {
  data: PropertyResponse | null;
  loading: boolean;
  notFound: boolean;
  error: string | null;
}

export function usePropertyLookup(
  lat: number | null,
  lon: number | null,
  address: string | null,
): UsePropertyLookupResult {
  const [data, setData] = useState<PropertyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lat == null || lon == null || !address) {
      setLoading(false);
      setError("Missing location parameters");
      return;
    }

    let cancelled = false;

    async function fetchProperty() {
      setLoading(true);
      setNotFound(false);
      setError(null);

      try {
        const result = await getProperty(lat!, lon!, address!);
        if (!cancelled) {
          setData(result);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        if (
          err &&
          typeof err === "object" &&
          "response" in err &&
          (err as { response?: { status?: number } }).response?.status === 404
        ) {
          setNotFound(true);
        } else {
          setError("Failed to load property data");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchProperty();
    return () => {
      cancelled = true;
    };
  }, [lat, lon, address]);

  return { data, loading, notFound, error };
}
