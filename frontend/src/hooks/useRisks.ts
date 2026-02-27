import { useEffect, useState } from "react";
import type { RiskFeature } from "../types";
import { getRisksData } from "../services/property";

interface RisksData {
  features: RiskFeature[];
}

const EMPTY_DATA: RisksData = {
  features: [],
};

export function useRisks(lat: number, lon: number, radiusMiles = 3) {
  const [data, setData] = useState<RisksData>(EMPTY_DATA);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);

    getRisksData(lat, lon, radiusMiles)
      .then((resp) => {
        if (!controller.signal.aborted) {
          setData({
            features: resp.features,
          });
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          console.error("Failed to load risks data:", err);
          setData(EMPTY_DATA);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [lat, lon, radiusMiles]);

  return { data, loading };
}
