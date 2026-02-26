import { useEffect, useState } from "react";
import { getNoiseData, getNuisanceGeometries } from "../services/property";

const EMPTY_COLLECTION: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

export function useNuisances(lat: number, lon: number, radiusMiles = 2) {
  const [data, setData] = useState<GeoJSON.FeatureCollection>(EMPTY_COLLECTION);
  const [infraData, setInfraData] = useState<GeoJSON.FeatureCollection>(EMPTY_COLLECTION);
  const [loading, setLoading] = useState(true);
  const [infraLoading, setInfraLoading] = useState(true);

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

  useEffect(() => {
    const controller = new AbortController();
    setInfraLoading(true);

    getNuisanceGeometries(lat, lon, radiusMiles)
      .then((resp) => {
        if (!controller.signal.aborted) {
          setInfraData(resp);
          setInfraLoading(false);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          console.error("Failed to load infrastructure geometries:", err);
          setInfraData(EMPTY_COLLECTION);
          setInfraLoading(false);
        }
      });

    return () => controller.abort();
  }, [lat, lon, radiusMiles]);

  return { data, infraData, loading, infraLoading };
}
