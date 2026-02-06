import { useEffect, useRef } from "react";
import { useApi } from "./useApi";
import { getProperty } from "../services/property";
import type { PropertyResponse } from "../types";

export function usePropertyData(lat: number, lon: number, address: string) {
  const { data, loading, error, execute } = useApi<PropertyResponse, [number, number, string]>(
    getProperty,
  );
  const lastKey = useRef<string>("");

  useEffect(() => {
    const key = `${lat},${lon},${address}`;
    if (address && key !== lastKey.current) {
      lastKey.current = key;
      execute(lat, lon, address);
    }
  }, [lat, lon, address, execute]);

  return { data, loading, error };
}
