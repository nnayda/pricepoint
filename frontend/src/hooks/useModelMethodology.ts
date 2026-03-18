import { useEffect, useState } from "react";
import type { AxiosError } from "axios";
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
        // Fetch independently so a 404 on methodology doesn't block the catalog
        const [methResult, catalogResult] = await Promise.allSettled([
          getModelMethodology(),
          getFeatureCatalog(),
        ]);

        if (cancelled) return;

        if (methResult.status === "fulfilled") {
          setMethodology(methResult.value);
        } else {
          const axiosErr = methResult.reason as AxiosError;
          // 404 = no champion model registered — not an error, just no model yet
          if (axiosErr?.response?.status !== 404) {
            const message =
              methResult.reason instanceof Error
                ? methResult.reason.message
                : "Failed to load model methodology";
            setError(message);
          }
        }

        if (catalogResult.status === "fulfilled") {
          setFeatureCatalog(catalogResult.value);
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
