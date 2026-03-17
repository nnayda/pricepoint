import { useEffect, useState } from "react";
import type { FeatureCatalogResponse, ModelMethodologyResponse } from "../types";
import { getFeatureCatalog, getModelMethodology } from "../services/model";

interface UseModelMethodologyResult {
  methodology: ModelMethodologyResponse | null;
  featureCatalog: FeatureCatalogResponse | null;
  loading: boolean;
  error: string | null;
}

export function useModelMethodology(): UseModelMethodologyResult {
  const [methodology, setMethodology] = useState<ModelMethodologyResponse | null>(null);
  const [featureCatalog, setFeatureCatalog] = useState<FeatureCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        const [methData, catalogData] = await Promise.all([
          getModelMethodology(),
          getFeatureCatalog(),
        ]);
        if (!cancelled) {
          setMethodology(methData);
          setFeatureCatalog(catalogData);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to load model methodology";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      cancelled = true;
    };
  }, []);

  return { methodology, featureCatalog, loading, error };
}
