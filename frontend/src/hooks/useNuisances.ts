import { useEffect, useState } from "react";
import { getNoiseData } from "../services/property";

const EMPTY_COLLECTION: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

export function useNuisances(lat: number, lon: number, radiusMiles = 2) {
  const [data, setData] = useState<GeoJSON.FeatureCollection>(EMPTY_COLLECTION);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);

    getNoiseData(lat, lon, radiusMiles)
      .then((resp) => {
        if (!controller.signal.aborted) {
          setData(resp as unknown as GeoJSON.FeatureCollection);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          console.error("Failed to load noise data:", err);
          setData(EMPTY_COLLECTION);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [lat, lon, radiusMiles]);

  return { data, loading };
}
