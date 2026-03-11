import { useEffect, useState } from "react";
import { getFeatureAttributions } from "../services/property";
import type { FeatureAttribution } from "../types";

interface UseFeatureAttributionsResult {
  data: FeatureAttribution[] | null;
  loading: boolean;
}

export function useFeatureAttributions(propertyId: number | null): UseFeatureAttributionsResult {
  const [data, setData] = useState<FeatureAttribution[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (propertyId == null) return;

    let cancelled = false;
    setLoading(true);

    getFeatureAttributions(propertyId)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        // Silently fall back — dashboard will use mock SHAP data
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [propertyId]);

  return { data, loading };
}
