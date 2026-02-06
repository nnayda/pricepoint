import axios from "axios";
import type { GeocodeResponse } from "../types";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export async function getGeocode(q: string, limit?: number): Promise<GeocodeResponse> {
  const { data } = await client.get<GeocodeResponse>("/api/geocode", {
    params: { q, ...(limit !== undefined && { limit }) },
  });
  return data;
}
