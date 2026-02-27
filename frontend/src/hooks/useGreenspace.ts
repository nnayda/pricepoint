import { useEffect, useState } from "react";
import type { GreenspaceResponse } from "../types";
import { getGreenspace } from "../services/property";

const EMPTY_RESPONSE: GreenspaceResponse = {
  features: [],
  metrics: {
    parks_within_1mi: 0,
    nearest_park_miles: 0,
    nearest_greenway_miles: 0,
    total_green_acres_1mi: 0,
    greenspace_z_score: 0,
  },
};

export function useGreenspace(lat: number, lon: number, radiusMiles = 7) {
  const [data, setData] = useState<GreenspaceResponse>(EMPTY_RESPONSE);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);

    getGreenspace(lat, lon, radiusMiles)
      .then((resp) => {
        if (!controller.signal.aborted) {
          setData(resp);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          console.error("Failed to load greenspace data:", err);
          setData(EMPTY_RESPONSE);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [lat, lon, radiusMiles]);

  return { data, loading };
}
