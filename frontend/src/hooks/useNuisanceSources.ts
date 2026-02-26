import { useEffect, useState } from "react";
import { getNuisanceSources } from "../services/property";
import type { NuisanceSourceItem } from "../types";

interface UseNuisanceSourcesResult {
  sources: NuisanceSourceItem[];
  loading: boolean;
  error: string | null;
}

export function useNuisanceSources(lat: number | null, lon: number | null): UseNuisanceSourcesResult {
  const [sources, setSources] = useState<NuisanceSourceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (lat == null || lon == null) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchSources() {
      setLoading(true);
      setError(null);

      try {
        const result = await getNuisanceSources(lat!, lon!);
        if (!cancelled) {
          setSources(result.sources);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load nuisance sources");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchSources();
    return () => {
      cancelled = true;
    };
  }, [lat, lon]);

  return { sources, loading, error };
}
